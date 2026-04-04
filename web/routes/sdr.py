"""SDR dongle routes — RTL-SDR driver setup and HackRF firmware update.

Handles driver blacklisting (dvb_usb_rtl28xxu), udev rule installation,
and basic device detection for RTL-SDR and HackRF dongles.
"""

import subprocess
from pathlib import Path

from flask import Blueprint, jsonify, request

from web.core import Task, cmd_exists, start_task

bp = Blueprint("sdr", __name__)

# Known SDR USB VID:PID pairs
_SDR_DEVICES = {
    ("0bda", "2832"): "RTL-SDR (RTL2832U)",
    ("0bda", "2838"): "RTL-SDR Blog V3/V4",
    ("1d50", "6089"): "HackRF One",
    ("1d50", "604b"): "HackRF One (DFU mode)",
    ("1d50", "cc15"): "rad1o (CCCamp badge)",
}

_BLACKLIST_CONF = "/etc/modprobe.d/blacklist-rtlsdr.conf"
_BLACKLIST_CONTENT = """\
# Blacklist DVB-T drivers to allow RTL-SDR access
# Installed by OSmosis
blacklist dvb_usb_rtl28xxu
blacklist dvb_usb_rtl2832u
blacklist rtl2832
blacklist rtl2830
blacklist dvb_usb_v2
blacklist dvb_core
"""


def _detect_sdr_devices() -> list[dict]:
    """Detect connected SDR dongles via lsusb."""
    devices = []
    try:
        result = subprocess.run(
            ["lsusb"], capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.strip().splitlines():
            for (vid, pid), name in _SDR_DEVICES.items():
                if f"{vid}:{pid}" in line.lower():
                    devices.append({"vid": vid, "pid": pid, "name": name})
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return devices


@bp.route("/api/sdr/detect")
def api_sdr_detect():
    """Detect connected SDR dongles."""
    devices = _detect_sdr_devices()
    if not devices:
        return (
            jsonify(
                {"error": "no_device", "hint": "No SDR dongle detected on USB."}
            ),
            404,
        )
    return jsonify({"devices": devices})


@bp.route("/api/sdr/status")
def api_sdr_status():
    """Check SDR driver setup status."""
    blacklisted = Path(_BLACKLIST_CONF).exists()

    # Check if the DVB driver is currently loaded
    dvb_loaded = False
    try:
        result = subprocess.run(
            ["lsmod"], capture_output=True, text=True, timeout=5
        )
        dvb_loaded = "dvb_usb_rtl28xxu" in result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return jsonify(
        {
            "dvb_blacklisted": blacklisted,
            "dvb_loaded": dvb_loaded,
            "rtl_sdr_installed": cmd_exists("rtl_test"),
            "hackrf_installed": cmd_exists("hackrf_info"),
            "needs_setup": dvb_loaded or not blacklisted,
        }
    )


@bp.route("/api/sdr/setup-driver", methods=["POST"])
def api_setup_driver():
    """Set up RTL-SDR drivers: blacklist DVB modules, install udev rules, unload conflicting drivers.

    Requires sudo. The frontend should warn the user that this modifies system configuration.
    """

    def _run(task: Task):
        task.emit("Setting up RTL-SDR driver access...", "info")

        # Step 1: Blacklist DVB-T kernel modules
        task.emit("Blacklisting DVB-T kernel modules...", "info")
        blacklist = Path(_BLACKLIST_CONF)
        if blacklist.exists():
            task.emit("Blacklist already in place.", "info")
        else:
            rc = task.run_shell(
                [
                    "sudo",
                    "tee",
                    _BLACKLIST_CONF,
                ],
                input_data=_BLACKLIST_CONTENT,
            )
            if rc != 0:
                task.emit(
                    "Failed to write blacklist. Run with sudo access.", "error"
                )
                task.done(False)
                return
            task.emit(f"Wrote {_BLACKLIST_CONF}", "success")

        # Step 2: Unload conflicting modules if loaded
        task.emit("Unloading conflicting kernel modules...", "info")
        for mod in [
            "dvb_usb_rtl28xxu",
            "dvb_usb_rtl2832u",
            "rtl2832",
            "rtl2830",
        ]:
            task.run_shell(["sudo", "modprobe", "-r", mod])

        # Step 3: Install udev rules
        task.emit("Installing udev rules...", "info")
        udev_script = (
            Path(__file__).resolve().parent.parent.parent
            / "scripts"
            / "setup-udev.sh"
        )
        if udev_script.exists():
            rc = task.run_shell(["sudo", "bash", str(udev_script)])
            if rc != 0:
                task.emit("udev setup had warnings (non-fatal).", "warn")
        else:
            task.emit("udev setup script not found — skipping.", "warn")

        # Step 4: Reload udev
        task.emit("Reloading udev rules...", "info")
        task.run_shell(["sudo", "udevadm", "control", "--reload-rules"])
        task.run_shell(["sudo", "udevadm", "trigger"])

        # Step 5: Verify
        task.emit("Verifying setup...", "info")
        devices = _detect_sdr_devices()
        if devices:
            task.emit(
                f"SDR dongle detected: {devices[0]['name']}. Setup complete!",
                "success",
            )
        else:
            task.emit(
                "Setup complete. Replug your SDR dongle for changes to take effect.",
                "success",
            )

        task.done(True)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@bp.route("/api/sdr/hackrf-update", methods=["POST"])
def api_hackrf_update():
    """Update HackRF One firmware via hackrf_spiflash.

    JSON body: { "fw_path": "/path/to/hackrf_one_usb.bin" }
    """
    body = request.json or {}
    fw_path = body.get("fw_path", "").strip()

    if not fw_path or not Path(fw_path).is_file():
        return jsonify({"error": "Firmware file not found"}), 400

    if not cmd_exists("hackrf_spiflash"):
        return jsonify({"error": "hackrf_spiflash is not installed"}), 500

    def _run(task: Task):
        task.emit(f"Flashing HackRF firmware: {fw_path}", "info")
        rc = task.run_shell(["hackrf_spiflash", "-w", fw_path])
        if rc == 0:
            task.emit(
                "Firmware updated! Unplug and replug the HackRF.", "success"
            )
        else:
            task.emit("Flash failed. Check that HackRF is connected.", "error")
        task.done(rc == 0)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})
