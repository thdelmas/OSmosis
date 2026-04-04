"""EDL (Emergency Download / Qualcomm 9008) entry and flash routes.

Three strategies are attempted in order:

1. ADB reboot (``adb reboot edl``) — works from sideload, recovery,
   or normal ADB mode.  Does not require an unlocked bootloader.
2. Fastboot commands (``fastboot oem edl`` etc.) — works from fastboot
   mode when the bootloader is unlocked.
3. Deep flash cable — user powers off the device, holds the cable
   button (D+/D- short), and plugs USB in from a cold state.
"""

import subprocess
import time

from flask import Blueprint, jsonify, request

from web.core import Task, cmd_exists, start_task

bp = Blueprint("edl", __name__)

# Qualcomm 9008 EDL USB identifiers
EDL_VID = "05c6"
EDL_PID = "9008"


def _edl_device_present() -> bool:
    """Check if a Qualcomm 9008 EDL device is visible on USB."""
    try:
        result = subprocess.run(
            ["lsusb"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in result.stdout.splitlines():
            if f"{EDL_VID}:{EDL_PID}" in line.lower():
                return True
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return False


def _adb_device_present() -> bool:
    """Check if any ADB device is connected (any mode)."""
    if not cmd_exists("adb"):
        return False
    try:
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in result.stdout.strip().splitlines()[1:]:
            if line.strip() and not line.startswith("*"):
                return True
    except (subprocess.TimeoutExpired, OSError):
        pass
    return False


def _fastboot_device_present() -> bool:
    """Check if any device is connected in fastboot mode."""
    if not cmd_exists("fastboot"):
        return False
    try:
        result = subprocess.run(
            ["fastboot", "devices"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in result.stdout.strip().splitlines():
            if line.split():
                return True
    except (subprocess.TimeoutExpired, OSError):
        pass
    return False


def _wait_for_edl(task: Task, timeout_secs: int = 20) -> bool:
    """Poll for EDL device appearance.  Returns True if found."""
    for _ in range(timeout_secs):
        if task.cancelled:
            return False
        time.sleep(1)
        if _edl_device_present():
            return True
    return False


@bp.route("/api/edl/status", methods=["GET"])
def api_edl_status():
    """Check if a device is currently in EDL (Qualcomm 9008) mode."""
    present = _edl_device_present()
    return jsonify(
        {
            "edl_detected": present,
            "vid": EDL_VID,
            "pid": EDL_PID,
        }
    )


@bp.route("/api/edl/enter", methods=["POST"])
def api_edl_enter():
    """Start the EDL entry sequence as a streaming task.

    Accepts a device in ADB mode (sideload/recovery/normal) or
    fastboot mode.  Tries ADB reboot first, then fastboot commands,
    then guides the user through the deep flash cable method.
    """
    has_adb = _adb_device_present()
    has_fastboot = _fastboot_device_present()

    if not has_adb and not has_fastboot:
        return jsonify({"error": "No device connected (ADB or fastboot)"}), 400

    def _run(task: Task):
        # --------------------------------------------------------------
        # Strategy 1: ADB reboot edl
        # Works from sideload, recovery, or normal ADB mode.
        # Does NOT require an unlocked bootloader on most Qualcomm devices.
        # --------------------------------------------------------------
        if has_adb:
            for cmd in (
                ["adb", "reboot", "edl"],
                ["adb", "shell", "reboot", "edl"],
            ):
                task.emit(f"$ {' '.join(cmd)}", "cmd")
                try:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    combined = result.stdout + result.stderr
                    if result.returncode == 0 or "reboot" in combined.lower():
                        task.emit("ADB reboot to EDL sent.", "success")
                        task.emit("DIRECT_ACCEPTED", "info")
                        if _wait_for_edl(task, timeout_secs=15):
                            task.emit("EDL_DETECTED", "success")
                            task.done(True)
                            return
                        task.emit(
                            "ADB reboot sent but EDL device not detected.",
                            "warn",
                        )
                        # Don't give up yet — try fastboot if available
                        break
                    reason = (
                        combined.strip().splitlines()[-1]
                        if combined.strip()
                        else "failed"
                    )
                    task.emit(f"  {reason}", "info")
                except subprocess.TimeoutExpired:
                    task.emit("  timed out (device may be rebooting)", "info")
                    # Timeout on adb reboot often means it worked — check for EDL
                    if _wait_for_edl(task, timeout_secs=15):
                        task.emit("EDL_DETECTED", "success")
                        task.done(True)
                        return
                except Exception as e:
                    task.emit(f"  {e}", "info")

        # --------------------------------------------------------------
        # Strategy 2: Fastboot EDL commands
        # Works when the bootloader is unlocked.
        # --------------------------------------------------------------
        if has_fastboot or _fastboot_device_present():
            task.emit("")
            task.emit("Trying fastboot EDL commands...", "info")
            for cmd in (
                ["fastboot", "oem", "edl"],
                ["fastboot", "reboot", "edl"],
                ["fastboot", "reboot-edl"],
            ):
                task.emit(f"$ {' '.join(cmd)}", "cmd")
                try:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    combined = result.stdout + result.stderr
                    if result.returncode == 0 or "OKAY" in combined.upper():
                        task.emit("Command accepted.", "success")
                        task.emit("DIRECT_ACCEPTED", "info")
                        if _wait_for_edl(task, timeout_secs=20):
                            task.emit("EDL_DETECTED", "success")
                            task.done(True)
                            return
                        task.emit(
                            "Command accepted but EDL device not detected.",
                            "warn",
                        )
                        task.done(False)
                        return
                    lines = combined.strip().splitlines()
                    reason = lines[-1] if lines else "rejected"
                    task.emit(f"  {reason}", "info")
                except subprocess.TimeoutExpired:
                    task.emit("  timed out", "info")
                except Exception as e:
                    task.emit(f"  {e}", "info")

        # --------------------------------------------------------------
        # Strategy 3: Deep flash cable — cold boot.
        # All software methods failed.  Guide the user through
        # manual power-off and cold plug with D+/D- short.
        # --------------------------------------------------------------
        task.emit("")
        task.emit("NEED_CABLE", "warn")

        deadline = time.monotonic() + 90
        last_msg_at = 0
        while time.monotonic() < deadline:
            if task.cancelled:
                return
            if _edl_device_present():
                task.emit("EDL_DETECTED", "success")
                task.done(True)
                return
            now = time.monotonic()
            if now - last_msg_at >= 5:
                remaining = int(deadline - now)
                task.emit(f"SCANNING:{remaining}", "info")
                last_msg_at = now
            time.sleep(0.5)

        task.emit("SCAN_TIMEOUT", "error")
        task.done(False)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@bp.route("/api/edl/flash", methods=["POST"])
def api_edl_flash():
    """Flash firmware via EDL using qdl or edl.py tools.

    Expected JSON body::

        {
            "firehose": "path/to/programmer.mbn",
            "firmware_dir": "path/to/images"
        }

    This endpoint is a stub — full implementation will be added once the
    EDL flash tooling (qdl / edl.py) integration is finalized.
    """
    if not _edl_device_present():
        return jsonify({"error": "No device in EDL (Qualcomm 9008) mode"}), 400

    firehose = (request.json or {}).get("firehose", "")
    firmware_dir = (request.json or {}).get("firmware_dir", "")

    if not firehose:
        return jsonify(
            {"error": "firehose (programmer.mbn path) is required"}
        ), 400
    if not firmware_dir:
        return jsonify({"error": "firmware_dir is required"}), 400

    def _run(task: Task):
        task.emit("EDL flash is not yet implemented.", "warn")
        task.emit(f"Firehose programmer: {firehose}")
        task.emit(f"Firmware directory: {firmware_dir}")
        task.emit("")
        task.emit(
            "This will use qdl or edl.py to flash the device in a future update.",
            "info",
        )
        task.done(False)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})
