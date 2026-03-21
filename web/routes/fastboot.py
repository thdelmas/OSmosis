"""Fastboot routes for Google Pixel device flashing."""

import subprocess
from pathlib import Path

from flask import Blueprint, jsonify, request

from web.core import Task, cmd_exists, start_task
from web.registry import register, verify

bp = Blueprint("fastboot", __name__)


def _fastboot_devices() -> list[dict]:
    """Return list of devices currently in fastboot mode."""
    if not cmd_exists("fastboot"):
        return []
    try:
        result = subprocess.run(
            ["fastboot", "devices"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        devices = []
        for line in result.stdout.strip().splitlines():
            parts = line.split()
            if len(parts) >= 2:
                devices.append({"serial": parts[0], "mode": parts[1]})
        return devices
    except (subprocess.TimeoutExpired, OSError):
        return []


def _fastboot_getvar(var: str) -> str:
    """Read a fastboot variable from the connected device."""
    try:
        result = subprocess.run(
            ["fastboot", "getvar", var],
            capture_output=True,
            text=True,
            timeout=5,
        )
        # fastboot getvar outputs to stderr
        for line in (result.stderr + result.stdout).splitlines():
            if line.startswith(f"{var}:"):
                return line.split(":", 1)[1].strip()
    except (subprocess.TimeoutExpired, OSError):
        pass
    return ""


@bp.route("/api/fastboot/status", methods=["GET"])
def api_fastboot_status():
    """Check if a device is connected in fastboot mode."""
    if not cmd_exists("fastboot"):
        return jsonify({"error": "fastboot not installed", "connected": False}), 503

    devices = _fastboot_devices()
    if not devices:
        return jsonify({"connected": False, "devices": []})

    # Get device info from the first connected device
    product = _fastboot_getvar("product")
    serial = _fastboot_getvar("serialno")
    unlocked = _fastboot_getvar("unlocked")

    return jsonify(
        {
            "connected": True,
            "devices": devices,
            "product": product,
            "serial": serial,
            "unlocked": unlocked == "yes",
        }
    )


@bp.route("/api/fastboot/unlock", methods=["POST"])
def api_fastboot_unlock():
    """Unlock the bootloader on a Pixel device via fastboot."""
    if not cmd_exists("fastboot"):
        return jsonify({"error": "fastboot is not installed"}), 503

    devices = _fastboot_devices()
    if not devices:
        return jsonify({"error": "No device in fastboot mode"}), 400

    def _run(task: Task):
        task.emit("Checking device status...")

        product = _fastboot_getvar("product")
        serial = _fastboot_getvar("serialno")
        unlocked = _fastboot_getvar("unlocked")

        task.emit(f"Device: {product or 'unknown'} (serial: {serial or 'unknown'})")

        if unlocked == "yes":
            task.emit("Bootloader is already unlocked.", "success")
            task.done(True)
            return

        task.emit("Sending bootloader unlock command...", "warn")
        task.emit("WARNING: This will erase all data on the device!", "warn")

        rc = task.run_shell(["fastboot", "flashing", "unlock"])
        if rc == 0:
            task.emit(
                "Unlock command sent. Confirm on the device screen using Volume keys and Power button.",
                "success",
            )
            task.emit(
                "The device will factory reset and reboot after confirmation.",
                "info",
            )
        else:
            task.emit(
                "Unlock command failed. Make sure OEM Unlocking is enabled in Developer Options.",
                "error",
            )
        task.done(rc == 0)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@bp.route("/api/fastboot/flash", methods=["POST"])
def api_fastboot_flash():
    """Flash a factory image or custom ROM to a Pixel device via fastboot."""
    if not cmd_exists("fastboot"):
        return jsonify({"error": "fastboot is not installed"}), 503

    devices = _fastboot_devices()
    if not devices:
        return jsonify({"error": "No device in fastboot mode"}), 400

    image_zip = request.json.get("image_zip", "")
    flash_type = request.json.get("flash_type", "factory")  # "factory" or "custom"
    wipe = request.json.get("wipe", flash_type == "custom")

    if not image_zip or not Path(image_zip).is_file():
        return jsonify({"error": "Image ZIP not found"}), 400

    def _run(task: Task):
        import glob
        import shutil

        task.emit(f"Image ZIP: {image_zip}")
        task.emit(f"Flash type: {flash_type}")

        task.emit("Verifying firmware against registry...", "info")
        vr = verify(image_zip)
        h = vr["sha256"]
        task.emit(f"SHA256: {h}")
        if vr["known"]:
            task.emit("Verified: matches a known registry entry.", "success")
        else:
            task.emit("Warning: firmware not in registry. Proceeding.", "warn")
        task.emit("")

        # Check bootloader status
        unlocked = _fastboot_getvar("unlocked")
        if unlocked != "yes":
            task.emit("Bootloader is LOCKED. Unlock it first (POST /api/fastboot/unlock).", "error")
            task.done(False)
            return

        product = _fastboot_getvar("product")
        task.emit(f"Device: {product or 'unknown'}")
        task.emit("Bootloader is unlocked.", "success")

        # Extract ZIP
        work_dir = Path.home() / "Downloads" / (Path(image_zip).stem + "-fastboot-unpacked")
        if work_dir.exists():
            shutil.rmtree(work_dir)
        work_dir.mkdir(parents=True, exist_ok=True)
        task.emit(f"Working directory: {work_dir}")

        task.emit("Extracting image ZIP...", "info")
        rc = task.run_shell(["unzip", "-o", image_zip, "-d", str(work_dir)])
        if rc != 0:
            task.emit("Failed to extract ZIP.", "error")
            task.done(False)
            return

        # Look for flash-all.sh (Google factory images and GrapheneOS include one)
        flash_all_candidates = glob.glob(str(work_dir / "**/flash-all.sh"), recursive=True)
        if flash_all_candidates:
            flash_all = flash_all_candidates[0]
            flash_dir = str(Path(flash_all).parent)
            task.emit(f"Found flash-all.sh in {flash_dir}", "info")
            task.emit("Running flash-all.sh...", "info")
            # flash-all.sh must run from its own directory
            rc = task.run_shell(["bash", "-c", f"cd '{flash_dir}' && bash flash-all.sh"])
            if rc == 0:
                task.emit("Flash complete!", "success")
                register(image_zip, flash_method="fastboot-flash-all", component=flash_type, sha256=h)
            else:
                task.emit("flash-all.sh failed.", "error")
            task.done(rc == 0)
            return

        # No flash-all.sh — flash individual partitions
        task.emit("No flash-all.sh found. Flashing individual partitions.", "info")

        # Extract inner image zip if present (Google factory images)
        inner_zips = glob.glob(str(work_dir / "**/image-*.zip"), recursive=True)
        img_dir = work_dir / "images"
        if inner_zips:
            img_dir.mkdir(exist_ok=True)
            task.emit(f"Extracting inner image ZIP: {Path(inner_zips[0]).name}")
            task.run_shell(["unzip", "-o", inner_zips[0], "-d", str(img_dir)])

        # Flash bootloader if present
        bootloaders = glob.glob(str(work_dir / "**/bootloader-*.img"), recursive=True)
        if bootloaders:
            task.emit(f"Flashing bootloader: {Path(bootloaders[0]).name}")
            rc = task.run_shell(["fastboot", "flash", "bootloader", bootloaders[0]])
            if rc == 0:
                task.run_shell(["fastboot", "reboot-bootloader"])

        # Flash radio if present
        radios = glob.glob(str(work_dir / "**/radio-*.img"), recursive=True)
        if radios:
            task.emit(f"Flashing radio: {Path(radios[0]).name}")
            rc = task.run_shell(["fastboot", "flash", "radio", radios[0]])
            if rc == 0:
                task.run_shell(["fastboot", "reboot-bootloader"])

        # Determine image directory
        if not img_dir.exists():
            img_dir = work_dir

        # For custom ROMs, disable verified boot
        if flash_type == "custom":
            vbmeta_files = list(img_dir.glob("vbmeta*.img"))
            for vb in vbmeta_files:
                task.emit(f"Flashing {vb.name} with verification disabled...")
                task.run_shell(
                    [
                        "fastboot",
                        "flash",
                        vb.stem,
                        str(vb),
                        "--disable-verity",
                        "--disable-verification",
                    ]
                )

        # Flash critical partitions in order
        priority_parts = ["boot", "dtbo", "vendor_boot", "init_boot"]
        flashed = set()

        for part in priority_parts:
            img = img_dir / f"{part}.img"
            if img.exists():
                task.emit(f"Flashing {part}...")
                task.run_shell(["fastboot", "flash", part, str(img)])
                flashed.add(part)

        # Flash remaining .img files
        for img in sorted(img_dir.glob("*.img")):
            part_name = img.stem
            if part_name in flashed:
                continue
            if flash_type == "custom" and part_name.startswith("vbmeta"):
                continue  # Already handled above
            task.emit(f"Flashing {part_name}...")
            task.run_shell(["fastboot", "flash", part_name, str(img)])

        # Wipe userdata for clean installs
        if wipe:
            task.emit("Wiping userdata (factory reset)...", "warn")
            task.run_shell(["fastboot", "-w"])

        task.emit("Rebooting device...", "info")
        task.run_shell(["fastboot", "reboot"])

        task.emit("Flash complete!", "success")
        register(image_zip, flash_method="fastboot-manual", component=flash_type, sha256=h)
        task.done(True)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@bp.route("/api/fastboot/lock", methods=["POST"])
def api_fastboot_lock():
    """Re-lock the bootloader (restores verified boot, wipes data)."""
    if not cmd_exists("fastboot"):
        return jsonify({"error": "fastboot is not installed"}), 503
    devices = _fastboot_devices()
    if not devices:
        return jsonify({"error": "No device in fastboot mode"}), 400

    def _run(task: Task):
        task.emit("WARNING: Locking the bootloader will erase all data!", "warn")
        task.emit("This is required to pass SafetyNet/Play Integrity on stock ROM.", "info")
        rc = task.run_shell(["fastboot", "flashing", "lock"])
        if rc == 0:
            task.emit("Lock command sent. Confirm on device.", "success")
        else:
            task.emit("Lock failed.", "error")
        task.done(rc == 0)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


# Per-OEM bootloader unlock guidance
_UNLOCK_GUIDES = {
    "google": {
        "brand": "Google Pixel",
        "steps": [
            "Enable Developer Options: Settings > About Phone > tap Build Number 7 times",
            "Enable OEM Unlocking: Settings > Developer Options > OEM Unlocking",
            "Boot to fastboot: Power off, then hold Power + Volume Down",
            "Run: fastboot flashing unlock",
            "Confirm on device with Volume keys + Power",
        ],
        "notes": "All data will be erased. Google Pixels have no waiting period.",
    },
    "oneplus": {
        "brand": "OnePlus",
        "steps": [
            "Enable Developer Options: Settings > About Phone > tap Build Number 7 times",
            "Enable OEM Unlocking: Settings > Developer Options > OEM Unlocking",
            "Boot to fastboot: Power off, hold Power + Volume Down",
            "Run: fastboot oem unlock",
            "Confirm on device",
        ],
        "notes": "OnePlus devices unlock instantly. Data will be erased.",
    },
    "xiaomi": {
        "brand": "Xiaomi / Poco / Redmi",
        "steps": [
            "Apply for unlock at en.miui.com/unlock (requires Mi account)",
            "Wait for approval (typically 72 hours to 30 days)",
            "Download Mi Unlock tool (Windows) or use unofficial Linux tools",
            "Boot to fastboot: Power off, hold Power + Volume Down",
            "Run the unlock tool with your Mi account credentials",
        ],
        "notes": "Xiaomi enforces a waiting period. Cannot be unlocked instantly.",
    },
    "samsung": {
        "brand": "Samsung (limited fastboot)",
        "steps": [
            "Samsung uses Download Mode + Heimdall/Odin, not fastboot",
            "For Knox-tripped devices: OEM unlock is permanently disabled",
            "Check Knox status: Settings > About Phone > Status > Knox Warranty Void",
        ],
        "notes": "Most Samsung devices do not support fastboot. Use Heimdall instead.",
    },
    "fairphone": {
        "brand": "Fairphone",
        "steps": [
            "Enable Developer Options and OEM Unlocking",
            "Boot to fastboot: Power off, hold Power + Volume Down",
            "Run: fastboot flashing unlock",
            "Confirm on device",
        ],
        "notes": "Fairphone actively supports unlocking and alternative OSes.",
    },
    "motorola": {
        "brand": "Motorola",
        "steps": [
            "Apply for unlock code at motorola.com/unlocking-bootloader",
            "Enable Developer Options and OEM Unlocking",
            "Boot to fastboot, run: fastboot oem get_unlock_data",
            "Submit the unlock data on the Motorola website",
            "Receive unlock code via email",
            "Run: fastboot oem unlock <code>",
        ],
        "notes": "Requires a Motorola account and carrier approval. Not all models supported.",
    },
}


@bp.route("/api/fastboot/unlock-guide")
def api_fastboot_unlock_guide():
    """Return bootloader unlock guidance for all supported OEMs."""
    return jsonify(_UNLOCK_GUIDES)


@bp.route("/api/fastboot/unlock-guide/<oem>")
def api_fastboot_unlock_guide_oem(oem: str):
    """Return bootloader unlock guidance for a specific OEM."""
    guide = _UNLOCK_GUIDES.get(oem.lower())
    if not guide:
        return jsonify({"error": f"No unlock guide for '{oem}'"}), 404
    return jsonify(guide)
