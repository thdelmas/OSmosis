"""Xiaomi MIAssistant unlock, download, and decision-tree routes.

Split from miassistant.py to stay under the 500-line limit.
"""

import subprocess
from pathlib import Path

from flask import Blueprint, jsonify, request

from web.core import Task, cmd_exists, parse_devices_cfg, start_task
from web.miassistant_protocol import REGION_ROM_CODES, detect_region
from web.routes.miassistant import _cached_device_info

bp = Blueprint("miassistant_unlock", __name__)


# Known Xiaomi CDN mirrors, ordered by typical speed
_XIAOMI_CDN_HOSTS = [
    "cdnorg.d.miui.com",
    "bn.d.miui.com",
    "bigota.d.miui.com",
]


@bp.route("/api/miassistant/download", methods=["POST"])
def api_miassistant_download():
    """Download a specific MIUI recovery ROM version.

    Expected JSON body::

        {
            "version": "V14.0.8.0.TKIEUXM",
            "filename": "miui_RENOIREEAGlobal_V14.0.8.0.TKIEUXM_c39c64055a_13.0.zip"
        }
    """
    version = request.json.get("version", "")
    filename = request.json.get("filename", "")

    if not version or not filename:
        return jsonify({"error": "version and filename are required"}), 400

    roms_dir = Path(__file__).resolve().parent.parent.parent / "roms"
    dest = roms_dir / filename

    if dest.exists():
        return jsonify(
            {"status": "exists", "path": str(dest), "size_mb": round(dest.stat().st_size / (1024 * 1024), 1)}
        )

    def _run(task: Task):
        roms_dir.mkdir(parents=True, exist_ok=True)
        url = None

        for host in _XIAOMI_CDN_HOSTS:
            test_url = f"https://{host}/{version}/{filename}"
            task.emit(f"Checking {host}...", "info")
            try:
                result = subprocess.run(
                    [
                        "curl",
                        "-sI",
                        "-o",
                        "/dev/null",
                        "-w",
                        "%{http_code}",
                        "-A",
                        "Mozilla/5.0",
                        "-r",
                        "0-1023",
                        test_url,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.stdout.strip() in ("200", "206"):
                    url = test_url
                    task.emit(f"Found on {host}", "success")
                    break
            except Exception:  # noqa: S112 — network probe, skip unreachable hosts
                continue

        if not url:
            task.emit("ROM not found on any Xiaomi CDN mirror.", "error")
            task.done(False)
            return

        task.emit(f"Downloading {filename}...", "info")
        rc = task.run_shell(
            [
                "curl",
                "-L",
                "-o",
                str(dest),
                url,
                "-A",
                "Mozilla/5.0",
                "-f",
                "--retry",
                "5",
                "--retry-delay",
                "5",
                "--speed-limit",
                "10000",
                "--speed-time",
                "30",
            ]
        )

        if rc == 0 and dest.exists() and dest.stat().st_size > 100_000_000:
            task.emit(f"Downloaded: {round(dest.stat().st_size / (1024 * 1024), 1)} MB", "success")
            task.done(True)
        else:
            if dest.exists():
                dest.unlink()
            task.emit("Download failed or file too small.", "error")
            task.done(False)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@bp.route("/api/miassistant/decision-tree", methods=["GET"])
def api_decision_tree():
    """Evaluate the recovery decision tree for the connected device.

    Combines device info, bootloader state, available ROMs, and hardware
    identification to recommend the best recovery path.
    """
    import re as _re

    from web.decision_tree import DeviceState, evaluate

    state = DeviceState()

    # Get device mode and basic info from devices/connected
    if cmd_exists("fastboot"):
        from web.routes.fastboot import _fastboot_devices, _fastboot_getvar

        fb = _fastboot_devices()
        if fb:
            state.mode = "fastboot"
            state.serial = fb[0]["serial"]
            product = _fastboot_getvar("product")
            state.fw_codename = product
            state.bl_locked = _fastboot_getvar("unlocked") != "yes"

            # Check unlock ability
            try:
                result = subprocess.run(
                    ["fastboot", "flashing", "get_unlock_ability"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                for line in (result.stdout + result.stderr).splitlines():
                    if "get_unlock_ability" in line and ":" in line:
                        state.bl_unlock_ability = line.split(":", 1)[1].strip() == "1"
            except Exception:
                pass

            # Look up hardware name
            for dev in parse_devices_cfg():
                if dev["codename"].lower() == product.lower():
                    state.display_name = dev["label"]
                    state.hw_codename = dev["codename"]
                    state.hw_name = dev["label"]
                    break

    # Use cached MIAssistant info if available
    if _cached_device_info:
        state.fw_device = _cached_device_info.get("Device", "")
        state.fw_version = _cached_device_info.get("Version", "")
        region_code, region_label = detect_region(state.fw_device, state.fw_version)
        state.fw_region = region_code
        state.fw_region_label = region_label
        state.fw_rom_code = REGION_ROM_CODES.get(region_code, "")

        # Extract firmware codename from device string
        if state.fw_device:
            fw_cn = state.fw_device.split("_")[0]
            if fw_cn:
                state.fw_codename = fw_cn

    # Detect cross-flash: firmware codename differs from hardware codename
    if state.hw_codename and state.fw_codename:
        state.is_cross_flashed = state.hw_codename.lower() != state.fw_codename.lower()

    # Get available ROMs
    roms_dir = Path(__file__).resolve().parent.parent.parent / "roms"
    available_roms = []
    if roms_dir.exists():
        for f in sorted(roms_dir.glob("miui_*.zip"), reverse=True):
            version = ""
            m = _re.search(r"_(V\d+\.\d+\.\d+\.\d+\.[A-Z]+)_", f.name)
            if m:
                version = m.group(1)
            rom_region = ""
            for code, rom_code in REGION_ROM_CODES.items():
                if rom_code in f.name:
                    rom_region = code
                    break
            compatible = not state.fw_region or rom_region == state.fw_region
            available_roms.append(
                {
                    "name": f.name,
                    "version": version,
                    "region": rom_region,
                    "compatible": compatible,
                }
            )

    result = evaluate(state, available_roms)
    return jsonify(result)


# ---------------------------------------------------------------------------
# Bootloader unlock
# ---------------------------------------------------------------------------


@bp.route("/api/miassistant/unlock-ability", methods=["GET"])
def api_unlock_ability():
    """Check if the device's bootloader can be unlocked.

    Requires device to be in fastboot mode.
    """
    from web.routes.fastboot import _fastboot_devices, _fastboot_getvar

    if not cmd_exists("fastboot"):
        return jsonify({"error": "fastboot not installed"}), 503

    devices = _fastboot_devices()
    if not devices:
        return jsonify({"error": "No device in fastboot mode"}), 400

    unlocked = _fastboot_getvar("unlocked")
    if unlocked == "yes":
        return jsonify({"eligible": True, "already_unlocked": True, "reason": "Bootloader is already unlocked."})

    ability = _fastboot_getvar("unlock_ability")
    # Also try the flashing command
    if not ability:
        try:
            result = subprocess.run(
                ["fastboot", "flashing", "get_unlock_ability"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            for line in (result.stdout + result.stderr).splitlines():
                if "get_unlock_ability" in line and ":" in line:
                    ability = line.split(":", 1)[1].strip()
        except Exception:
            pass

    eligible = ability == "1"
    return jsonify(
        {
            "eligible": eligible,
            "already_unlocked": False,
            "reason": "Device is eligible for unlock."
            if eligible
            else "OEM unlocking is not enabled. Enable it in Developer Options (requires booting into system first).",
        }
    )


@bp.route("/api/miassistant/unlock", methods=["POST"])
def api_unlock():
    """Unlock the bootloader using a stored Mi account session.

    Expected JSON body::

        {
            "account_id": "abc123"
        }

    The device must be in fastboot mode and the account must have
    a valid session (established via the Mi Account Manager login flow).
    """
    from web.mi_unlock import mi_unlock_device
    from web.routes.fastboot import _fastboot_devices
    from web.routes.mi_accounts import _get_account

    if not cmd_exists("fastboot"):
        return jsonify({"error": "fastboot not installed"}), 503

    devices = _fastboot_devices()
    if not devices:
        return jsonify({"error": "No device in fastboot mode. Reboot to fastboot first."}), 400

    account_id = (request.json or {}).get("account_id", "")
    if not account_id:
        return jsonify({"error": "account_id is required."}), 400

    account = _get_account(account_id)
    if not account:
        return jsonify({"error": "Account not found."}), 404

    session = account.get("session")
    if not session:
        return jsonify({"error": "No active session for this account. Log in first via the account manager."}), 400

    # Mask email for display
    email = account.get("email", "")
    masked = email[:3] + "***@" + email.split("@", 1)[-1] if "@" in email else email

    def _run(task: Task):
        task.emit("Starting bootloader unlock process...")
        task.emit(f"Account: {masked}")
        task.emit("")

        try:
            task.emit("Using stored session tokens...")
            task.emit("Contacting Xiaomi unlock servers...")

            result = mi_unlock_device(session)

            if result.get("status") == "ok":
                task.emit("")
                task.emit(result.get("message", "Bootloader unlock successful!"), "success")
                task.emit("The device will reboot. You can now flash firmware via fastboot.", "info")
                task.done(True)
            else:
                task.emit("")
                msg = result.get("message", "Unlock failed.")
                code = result.get("code")

                # Check for session expiry
                if code and code in (-1, 401, 10003):
                    task.emit("Session expired. Please log in again via the account manager.", "error")
                else:
                    task.emit(msg, "error")

                task.emit("Common issues:", "info")
                task.emit("  - Session expired (log in again via account manager)", "info")
                task.emit("  - Waiting period required (try again in 7-30 days)", "info")
                task.emit("  - Account not bound to this device", "info")
                task.done(False)

        except Exception as e:
            task.emit(f"Error: {e}", "error")
            task.done(False)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})
