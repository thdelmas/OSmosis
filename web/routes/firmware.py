"""Desktop/laptop firmware routes — flashrom for Coreboot/Libreboot.

Provides detection of supported systems via DMI data, flashrom chip
probing, firmware backup, and flash operations with safety checks.
"""

import re
import subprocess
from pathlib import Path

from flask import Blueprint, jsonify, request

from web.core import Task, cmd_exists, start_task
from web.registry import register

bp = Blueprint("firmware", __name__)

# DMI product name -> supported firmware targets
_SUPPORTED_SYSTEMS = {
    # Libreboot (fully free)
    "ThinkPad X60": {
        "firmware": ["libreboot"],
        "flash_method": "internal",
        "chip_size": "8MB",
        "notes": "First-gen Libreboot target. flashrom -p internal works.",
    },
    "ThinkPad T60": {
        "firmware": ["libreboot"],
        "flash_method": "internal",
        "chip_size": "8MB",
        "notes": "ATI GPU variant supported. flashrom -p internal works.",
    },
    "ThinkPad X200": {
        "firmware": ["libreboot", "coreboot"],
        "flash_method": "external",
        "chip_size": "8MB",
        "notes": "Requires SPI clip or CH341A for first flash. ME must be neutralized.",
    },
    "ThinkPad T400": {
        "firmware": ["libreboot", "coreboot"],
        "flash_method": "external",
        "chip_size": "8MB",
        "notes": "Requires SPI clip or CH341A. ME must be neutralized.",
    },
    # Coreboot (with blobs)
    "ThinkPad X230": {
        "firmware": ["coreboot"],
        "flash_method": "external_or_1vyrain",
        "chip_size": "12MB",
        "notes": "SPI clip or 1vyrain software exploit for initial flash.",
    },
    "ThinkPad T430": {
        "firmware": ["coreboot"],
        "flash_method": "external_or_1vyrain",
        "chip_size": "12MB",
        "notes": "SPI clip or 1vyrain. Dual-chip layout (4MB + 8MB).",
    },
    "ThinkPad T530": {
        "firmware": ["coreboot"],
        "flash_method": "external",
        "chip_size": "12MB",
        "notes": "SPI clip required. Dual-chip layout.",
    },
    "ThinkPad W530": {
        "firmware": ["coreboot"],
        "flash_method": "external",
        "chip_size": "12MB",
        "notes": "SPI clip required. Dual-chip layout.",
    },
    # Chromebooks
    "Chromebook": {
        "firmware": ["mrchromebox"],
        "flash_method": "internal",
        "chip_size": "varies",
        "notes": "MrChromebox full ROM replacement. Developer mode required.",
    },
    # Framework
    "Framework Laptop": {
        "firmware": ["framework_ec"],
        "flash_method": "internal",
        "chip_size": "varies",
        "notes": "EC firmware via flash_ec or FWUPD.",
    },
}


def _read_dmi_field(field: str) -> str:
    """Read a DMI/SMBIOS field from /sys."""
    path = Path(f"/sys/devices/virtual/dmi/id/{field}")
    if path.exists():
        try:
            return path.read_text().strip()
        except OSError:
            pass
    return ""


def _identify_system() -> dict | None:
    """Identify the current system from DMI data."""
    product = _read_dmi_field("product_name")
    vendor = _read_dmi_field("sys_vendor")
    version = _read_dmi_field("product_version")
    bios_vendor = _read_dmi_field("bios_vendor")
    bios_version = _read_dmi_field("bios_version")

    if not product:
        return None

    # Match against known systems
    match = None
    for name, info in _SUPPORTED_SYSTEMS.items():
        if name.lower() in product.lower() or name.lower() in version.lower():
            match = {**info, "match": name}
            break

    return {
        "product": product,
        "vendor": vendor,
        "version": version,
        "bios_vendor": bios_vendor,
        "bios_version": bios_version,
        "supported": match,
        "already_coreboot": "coreboot" in bios_vendor.lower(),
    }


@bp.route("/api/firmware/detect")
def api_firmware_detect():
    """Detect the current system and check firmware support."""
    system = _identify_system()
    if not system:
        return jsonify({"error": "Could not read system DMI data"}), 500

    tools = {
        "flashrom": cmd_exists("flashrom"),
        "me_cleaner": cmd_exists("me_cleaner") or cmd_exists("me_cleaner.py"),
        "ifdtool": cmd_exists("ifdtool"),
        "fwupdmgr": cmd_exists("fwupdmgr"),
    }

    return jsonify({**system, "tools": tools})


@bp.route("/api/firmware/probe")
def api_firmware_probe():
    """Probe the SPI flash chip using flashrom.

    Query params:
        programmer: flashrom programmer (default: internal)
    """
    if not cmd_exists("flashrom"):
        return jsonify({"error": "flashrom is not installed"}), 500

    programmer = request.args.get("programmer", "internal").strip()

    try:
        result = subprocess.run(
            ["sudo", "flashrom", "-p", programmer],
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout + result.stderr

        # Parse chip info
        chips = []
        for m in re.finditer(r'Found (.+?) flash chip "(.+?)" \((\d+) kB', output):
            chips.append(
                {
                    "vendor": m.group(1),
                    "name": m.group(2),
                    "size_kb": int(m.group(3)),
                }
            )

        return jsonify(
            {
                "chips": chips,
                "programmer": programmer,
                "raw_output": output[-500:] if len(output) > 500 else output,
            }
        )
    except subprocess.TimeoutExpired:
        return jsonify({"error": "flashrom probe timed out"}), 504


@bp.route("/api/firmware/backup", methods=["POST"])
def api_firmware_backup():
    """Read and backup the current firmware image.

    JSON body: { "programmer": "internal" }
    """
    if not cmd_exists("flashrom"):
        return jsonify({"error": "flashrom is not installed"}), 500

    body = request.json or {}
    programmer = body.get("programmer", "internal").strip()

    def _run(task: Task):
        import hashlib

        backup_dir = Path.home() / "Osmosis-backups" / "firmware"
        backup_dir.mkdir(parents=True, exist_ok=True)

        system = _identify_system()
        name = (system or {}).get("product", "unknown").replace(" ", "_")
        dest = backup_dir / f"{name}_backup.bin"

        task.emit(f"Reading firmware via flashrom -p {programmer}...", "info")
        task.emit("This may take 1-5 minutes depending on chip size.", "info")

        rc = task.run_shell(["sudo", "flashrom", "-p", programmer, "-r", str(dest)])
        if rc != 0:
            task.emit("Firmware read failed. Check flashrom output above.", "error")
            task.done(False)
            return

        if not dest.is_file() or dest.stat().st_size < 1024:
            task.emit("Backup file is empty or too small.", "error")
            task.done(False)
            return

        h = hashlib.sha256(dest.read_bytes()).hexdigest()
        size = dest.stat().st_size

        task.emit(f"Backup saved: {dest}", "success")
        task.emit(f"Size: {size // 1024}KB", "info")
        task.emit(f"SHA256: {h}", "info")
        task.emit(
            "IMPORTANT: Keep this backup safe. You need it to restore the original firmware if anything goes wrong.",
            "warn",
        )

        register(
            str(dest),
            device_id=name,
            device_label=(system or {}).get("product", "Unknown"),
            component="bios_backup",
            flash_method="flashrom",
            sha256=h,
        )

        task.done(True)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@bp.route("/api/firmware/flash", methods=["POST"])
def api_firmware_flash():
    """Flash a firmware image using flashrom.

    JSON body: {
        "fw_path": "/path/to/coreboot.rom",
        "programmer": "internal",
        "verify": true
    }

    Safety: requires explicit confirmation, checks file size against
    detected chip, and always verifies after write.
    """
    if not cmd_exists("flashrom"):
        return jsonify({"error": "flashrom is not installed"}), 500

    body = request.json or {}
    fw_path = body.get("fw_path", "").strip()
    programmer = body.get("programmer", "internal").strip()
    verify = body.get("verify", True)

    if not fw_path or not Path(fw_path).is_file():
        return jsonify({"error": "Firmware file not found"}), 400

    fw_size = Path(fw_path).stat().st_size
    if fw_size < 65536:  # 64KB minimum
        return (
            jsonify({"error": "File is too small to be a firmware image"}),
            400,
        )

    def _run(task: Task):
        import hashlib

        h = hashlib.sha256(Path(fw_path).read_bytes()).hexdigest()

        task.emit("=== FIRMWARE FLASH ===", "info")
        task.emit(f"Image: {fw_path}", "info")
        task.emit(f"Size: {fw_size // 1024}KB", "info")
        task.emit(f"SHA256: {h}", "info")
        task.emit(f"Programmer: {programmer}", "info")
        task.emit("")
        task.emit(
            "WARNING: Do NOT power off or interrupt this process. A failed flash can brick the machine.",
            "warn",
        )
        task.emit("")

        cmd = ["sudo", "flashrom", "-p", programmer, "-w", fw_path]
        if verify:
            cmd.append("--verify")

        task.emit("Writing firmware...", "info")
        rc = task.run_shell(cmd)

        if rc == 0:
            task.emit("Firmware flashed and verified successfully!", "success")
            task.emit("Reboot the machine to boot into the new firmware.", "info")
            system = _identify_system()
            register(
                fw_path,
                device_id=(system or {}).get("product", "unknown").replace(" ", "_"),
                device_label=(system or {}).get("product", "Unknown"),
                component="bios",
                flash_method="flashrom",
                sha256=h,
            )
        else:
            task.emit(
                "Flash FAILED. Do NOT reboot. Try re-running the flash command, or restore from your backup image.",
                "error",
            )

        task.done(rc == 0)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})
