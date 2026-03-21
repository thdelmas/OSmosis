"""Game console flashing routes — Switch RCM, Steam Deck, PS Vita."""

import subprocess
from pathlib import Path

from flask import Blueprint, jsonify, request

from web.core import Task, cmd_exists, start_task
from web.registry import register, verify

bp = Blueprint("console", __name__)


# ---------------------------------------------------------------------------
# Nintendo Switch — RCM payload injection
# ---------------------------------------------------------------------------


@bp.route("/api/console/switch/status")
def api_switch_status():
    """Check if a Nintendo Switch in RCM mode is connected via USB."""
    if not cmd_exists("fusee-launcher") and not cmd_exists("fusee-nano"):
        # Check for TegraRcmGUI's CLI or Python script
        fusee_py = Path.home() / ".local" / "bin" / "fusee-launcher.py"
        if not fusee_py.exists():
            return jsonify({"connected": False, "tool": None, "error": "No RCM tool found"})

    try:
        result = subprocess.run(["lsusb"], capture_output=True, text=True, timeout=5)
        # Nintendo Switch in RCM mode shows as "0955:7321 NVIDIA Corp. APX"
        rcm_detected = "0955:7321" in result.stdout
        return jsonify({"connected": rcm_detected, "tool": "fusee-launcher"})
    except Exception:
        return jsonify({"connected": False, "tool": None})


@bp.route("/api/console/switch/inject", methods=["POST"])
def api_switch_inject():
    """Inject an RCM payload into a Nintendo Switch.

    JSON body: {
        "payload_path": "/path/to/hekate.bin",
    }

    The Switch must be in RCM mode (hold Volume Up + Home/Jig while powering on).
    """
    body = request.json or {}
    payload_path = body.get("payload_path", "").strip()

    if not payload_path or not Path(payload_path).is_file():
        return jsonify({"error": "Payload file not found"}), 400

    def _run(task: Task):
        task.emit(f"Payload: {payload_path}", "info")
        task.emit(f"Size: {Path(payload_path).stat().st_size} bytes", "info")

        vr = verify(payload_path)
        task.emit(f"SHA256: {vr['sha256']}")
        task.emit("")

        # Check for RCM device
        task.emit("Checking for Switch in RCM mode...", "info")
        result = subprocess.run(["lsusb"], capture_output=True, text=True, timeout=5)
        if "0955:7321" not in result.stdout:
            task.emit("No Switch in RCM mode detected.", "error")
            task.emit("Hold Volume Up + insert RCM jig, then connect USB while powered off.", "info")
            task.done(False)
            return

        task.emit("Switch detected in RCM mode.", "success")
        task.emit("Injecting payload...", "info")

        # Try fusee-launcher variants
        for tool in ["fusee-launcher", "fusee-nano"]:
            if cmd_exists(tool):
                rc = task.run_shell([tool, payload_path], sudo=True)
                if rc == 0:
                    task.emit("Payload injected!", "success")
                    register(payload_path, flash_method="rcm-inject", component="switch-payload",
                             sha256=vr["sha256"])
                    task.done(True)
                    return

        # Try Python fusee-launcher
        fusee_py = Path.home() / ".local" / "bin" / "fusee-launcher.py"
        if fusee_py.exists():
            rc = task.run_shell(["python3", str(fusee_py), payload_path], sudo=True)
            if rc == 0:
                task.emit("Payload injected!", "success")
                register(payload_path, flash_method="rcm-inject", component="switch-payload",
                         sha256=vr["sha256"])
                task.done(True)
                return

        task.emit("No working RCM injection tool found.", "error")
        task.emit("Install fusee-launcher: pip install fusee-launcher", "info")
        task.done(False)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


# ---------------------------------------------------------------------------
# Steam Deck — dual boot / SteamOS recovery
# ---------------------------------------------------------------------------


@bp.route("/api/console/steamdeck/recovery", methods=["POST"])
def api_steamdeck_recovery():
    """Write a SteamOS recovery image to USB for the Steam Deck.

    JSON body: {
        "image_path": "/path/to/steamdeck-recovery.img.bz2",
        "device": "/dev/sdX"
    }
    """
    body = request.json or {}
    image_path = body.get("image_path", "").strip()
    device = body.get("device", "").strip()

    if not image_path or not Path(image_path).is_file():
        return jsonify({"error": "Recovery image not found"}), 400
    if not device or not device.startswith("/dev/"):
        return jsonify({"error": "Invalid device path"}), 400

    def _run(task: Task):
        task.emit(f"Image: {image_path}", "info")
        task.emit(f"Target: {device}", "info")
        task.emit("WARNING: All data on the target device will be erased!", "warn")
        task.emit("")

        # Determine decompression method
        if image_path.endswith(".bz2"):
            task.emit("Writing compressed image (bzip2 -> dd)...", "info")
            rc = task.run_shell([
                "bash", "-c",
                f"bzcat '{image_path}' | sudo dd of='{device}' bs=4M status=progress oflag=sync",
            ], sudo=True)
        elif image_path.endswith(".gz") or image_path.endswith(".xz"):
            decomp = "zcat" if image_path.endswith(".gz") else "xzcat"
            task.emit(f"Writing compressed image ({decomp} -> dd)...", "info")
            rc = task.run_shell([
                "bash", "-c",
                f"{decomp} '{image_path}' | sudo dd of='{device}' bs=4M status=progress oflag=sync",
            ], sudo=True)
        else:
            task.emit("Writing raw image (dd)...", "info")
            rc = task.run_shell([
                "dd", f"if={image_path}", f"of={device}", "bs=4M", "status=progress", "oflag=sync",
            ], sudo=True)

        if rc == 0:
            task.run_shell(["sync"])
            task.emit("Recovery USB written!", "success")
            task.emit("Boot the Steam Deck from USB: hold Volume Down + Power.", "info")
        else:
            task.emit("Write failed.", "error")
        task.done(rc == 0)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


# ---------------------------------------------------------------------------
# PS Vita — HENkaku/Enso info (no direct flash, guidance only)
# ---------------------------------------------------------------------------


_VITA_GUIDE = {
    "title": "PS Vita CFW (HENkaku/Enso)",
    "steps": [
        "Ensure your Vita is on firmware 3.60 or 3.65 (check Settings > System > System Information)",
        "Open the Vita browser and navigate to henkaku.xyz",
        "Follow the on-screen instructions to install HENkaku",
        "For permanent CFW: install Enso via VitaShell (requires 3.60 or 3.65)",
        "Install VitaShell from the HENkaku exploit for file management",
        "Optional: install SD2Vita adapter plugin for microSD storage",
    ],
    "notes": "HENkaku is a browser-based exploit. No USB flashing required. "
             "Enso makes it persistent across reboots.",
    "required_firmware": ["3.60", "3.65"],
}


@bp.route("/api/console/vita/guide")
def api_vita_guide():
    """Return the PS Vita HENkaku/Enso CFW installation guide."""
    return jsonify(_VITA_GUIDE)
