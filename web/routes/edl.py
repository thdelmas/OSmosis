"""EDL (Emergency Download / Qualcomm 9008) entry and flash routes.

Guides the user through entering EDL mode on Xiaomi devices with locked
bootloaders using a deep flash cable that shorts USB D+/D- pins.
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

    The device must be in fastboot mode. The flow:
    1. Verify fastboot device is connected
    2. Emit countdown messages so the user can prepare the deep flash cable
    3. Send ``fastboot reboot``
    4. Poll lsusb every 0.5s for up to 30 seconds looking for 05c6:9008
    5. Report success or timeout
    """
    if not cmd_exists("fastboot"):
        return jsonify({"error": "fastboot is not installed"}), 503

    if not _fastboot_device_present():
        return jsonify({"error": "No device in fastboot mode"}), 400

    def _run(task: Task):
        task.emit("Device detected in fastboot. Ready to enter EDL mode.")
        task.emit("")
        task.emit(
            "Make sure the EDL / deep flash cable is connected and you "
            "can reach the button that shorts the D+/D- pins.",
        )
        task.emit("")

        # Countdown
        task.emit("Get ready to press and HOLD the EDL cable button...", "warn")
        time.sleep(1.5)

        for n in (3, 2, 1):
            if task.cancelled:
                return
            task.emit(f"{n}...", "warn")
            time.sleep(1)

        task.emit("")
        task.emit("PRESS AND HOLD THE EDL BUTTON NOW — hold for 10 seconds!", "warn")

        # Send fastboot reboot
        rc = task.run_shell(["fastboot", "reboot"])
        if rc != 0:
            task.emit(
                "fastboot reboot command failed. Is the device still in fastboot?",
                "error",
            )
            task.done(False)
            return

        task.emit("")

        # 10-second hold countdown while scanning for EDL device
        found = False
        for sec in range(10, 0, -1):
            if task.cancelled:
                return
            if _edl_device_present():
                found = True
                break
            task.emit(f"Keep holding... {sec}s", "warn")
            # Check twice per second
            time.sleep(0.5)
            if _edl_device_present():
                found = True
                break
            time.sleep(0.5)

        # Continue scanning for another 20s if not found yet
        if not found:
            task.emit("")
            task.emit("You can release the button. Still scanning USB...", "info")
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                if task.cancelled:
                    return
                if _edl_device_present():
                    found = True
                    break
                time.sleep(0.5)
                remaining = int(deadline - time.monotonic())
                if remaining % 4 == 0:
                    task.emit(f"Scanning USB... ({remaining}s remaining)")

        if found:
            task.emit("")
            task.emit("EDL mode detected! Device is in Qualcomm 9008 mode.", "success")
            task.emit("You can release the cable button now.", "info")
            task.done(True)
        else:
            task.emit("")
            task.emit("Timed out — EDL device not detected after 30 seconds.", "error")
            task.emit(
                "Make sure you pressed the EDL cable button at the exact moment the device disconnected from USB.",
                "info",
            )
            task.emit(
                "If the device rebooted normally, put it back into fastboot mode and try again.",
                "info",
            )
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
        return jsonify({"error": "firehose (programmer.mbn path) is required"}), 400
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
