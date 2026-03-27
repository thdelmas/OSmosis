"""Fastboot extra routes — ROM listing, lock, reboot, unlock guides.

Split from fastboot.py to keep modules under the 500-line limit.
"""

import subprocess
from pathlib import Path

from flask import Blueprint, jsonify, request

from web.core import Task, cmd_exists, start_task
from web.fastboot_guides import UNLOCK_GUIDES

bp = Blueprint("fastboot_extra", __name__)


def _fastboot_devices() -> list[dict]:
    """List fastboot-connected devices (duplicated helper for independence)."""
    if not cmd_exists("fastboot"):
        return []
    try:
        r = subprocess.run(
            ["fastboot", "devices", "-l"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        devices = []
        for line in r.stdout.strip().splitlines():
            parts = line.split()
            if len(parts) >= 2:
                devices.append({"serial": parts[0], "mode": "fastboot"})
        return devices
    except Exception:
        return []


@bp.route("/api/fastboot/roms", methods=["GET"])
def api_fastboot_roms():
    """List available fastboot ROM directories and tgz files.

    Query param: ?codename=courbet (optional, filters by codename)
    """
    import re as _re

    codename_filter = request.args.get("codename", "")
    roms_dir = Path(__file__).resolve().parent.parent.parent / "roms"
    roms = []

    if roms_dir.exists():
        # Look for extracted fastboot ROM directories (contain flash_all.sh)
        for d in sorted(roms_dir.iterdir(), reverse=True):
            if d.is_dir() and (d / "flash_all.sh").exists():
                version = ""
                m = _re.search(r"(V\d+\.\d+\.\d+\.\d+\.[A-Z]+)", d.name)
                if m:
                    version = m.group(1)
                codename = ""
                for part in d.name.lower().split("_"):
                    if part in ("renoir", "courbet", "lisa", "vayu", "beryllium", "spes", "ruby", "garnet"):
                        codename = part
                        break
                if codename_filter and codename != codename_filter:
                    continue
                roms.append(
                    {
                        "path": str(d),
                        "name": d.name,
                        "version": version,
                        "codename": codename,
                        "type": "extracted",
                        "flash_script": str(d / "flash_all.sh"),
                    }
                )

        # Look for fastboot .tgz files
        for f in sorted(roms_dir.glob("*_images_*.tgz"), reverse=True):
            version = ""
            m = _re.search(r"(V\d+\.\d+\.\d+\.\d+\.[A-Z]+)", f.name)
            if m:
                version = m.group(1)
            codename = ""
            for part in f.stem.lower().split("_"):
                if part in ("renoir", "courbet", "lisa", "vayu", "beryllium", "spes", "ruby", "garnet"):
                    codename = part
                    break
            if codename_filter and codename != codename_filter:
                continue
            roms.append(
                {
                    "path": str(f),
                    "name": f.name,
                    "version": version,
                    "codename": codename,
                    "size_mb": round(f.stat().st_size / (1024 * 1024), 1),
                    "type": "tgz",
                }
            )

    return jsonify({"roms": roms})


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


@bp.route("/api/fastboot/reboot", methods=["POST"])
def api_fastboot_reboot():
    """Reboot the device from fastboot into a specified target.

    Expected JSON body::

        {
            "target": "recovery"   // "recovery", "system", or "bootloader"
        }

    - ``recovery``: boots into MIUI Recovery / stock recovery
    - ``system``: normal boot into the OS
    - ``bootloader``: re-enters fastboot/bootloader mode
    """
    if not cmd_exists("fastboot"):
        return jsonify({"error": "fastboot is not installed"}), 503

    devices = _fastboot_devices()
    if not devices:
        return jsonify({"error": "No device in fastboot mode"}), 400

    target = (request.json or {}).get("target", "system")
    if target not in ("recovery", "system", "bootloader"):
        return jsonify({"error": f"Invalid reboot target: {target}"}), 400

    cmd = ["fastboot", "reboot"]
    if target == "recovery":
        cmd.append("recovery")
    elif target == "bootloader":
        cmd.append("bootloader")
    # "system" is just `fastboot reboot` with no extra arg

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        ok = result.returncode == 0
        return jsonify(
            {
                "ok": ok,
                "target": target,
                "message": f"Rebooting to {target}..." if ok else "Reboot command failed.",
                "stderr": result.stderr.strip() if not ok else "",
            }
        )
    except subprocess.TimeoutExpired:
        return jsonify({"ok": False, "message": "Reboot command timed out."}), 504
    except OSError as e:
        return jsonify({"ok": False, "message": str(e)}), 500


@bp.route("/api/fastboot/unlock-guide")
def api_fastboot_unlock_guide():
    """Return bootloader unlock guidance for all supported OEMs."""
    return jsonify(UNLOCK_GUIDES)


@bp.route("/api/fastboot/unlock-guide/<oem>")
def api_fastboot_unlock_guide_oem(oem: str):
    """Return bootloader unlock guidance for a specific OEM."""
    guide = UNLOCK_GUIDES.get(oem.lower())
    if not guide:
        return jsonify({"error": f"No unlock guide for '{oem}'"}), 404
    return jsonify(guide)
