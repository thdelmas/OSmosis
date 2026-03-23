"""Flash stock/recovery, sideload, download, and backup routes."""

import os
import subprocess
from pathlib import Path

from flask import Blueprint, jsonify, request

from web.core import BACKUP_DIR, Task, parse_devices_cfg, start_task
from web.registry import register, verify

bp = Blueprint("flash", __name__)


def _ensure_download_mode(task: Task) -> bool:
    """Make sure the device is in Samsung Download Mode.

    If the device is connected via ADB, automatically reboot it into
    Download Mode. If already in Download Mode, return immediately.
    Returns True if the device is ready, False on failure.
    """
    import time

    # Check if already in Download Mode
    try:
        detect = subprocess.run(
            ["heimdall", "detect"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if detect.returncode == 0:
            task.emit("Device is in Download Mode.", "success")
            return True
    except Exception:
        pass

    # Check if connected via ADB — if so, reboot into Download Mode
    try:
        adb_result = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        has_adb = any(
            "device" in line.split("\t")[-1:] for line in adb_result.stdout.strip().splitlines()[1:] if line.strip()
        )
    except Exception:
        has_adb = False

    if has_adb:
        task.emit("Device connected via ADB. Switching to Download Mode automatically...", "info")
        rc = task.run_shell(["adb", "reboot", "download"])
        if rc != 0:
            task.emit("Failed to reboot into Download Mode.", "error")
            return False

        task.emit("Waiting for Download Mode...", "info")
        for _i in range(20):
            time.sleep(2)
            try:
                detect = subprocess.run(
                    ["heimdall", "detect"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if detect.returncode == 0:
                    task.emit("Device is in Download Mode!", "success")
                    return True
            except Exception:
                pass

        task.emit("Device didn't enter Download Mode within 40 seconds.", "error")
        task.emit("Try manually: power off, then hold Volume Down + Home + Power.", "info")
        return False

    # Neither ADB nor Download Mode — device not found
    task.emit("No device detected.", "error")
    task.emit("Connect your device via USB and make sure it's powered on.", "info")
    return False


def _ensure_recovery_mode(task: Task) -> bool:
    """Make sure the device is in Recovery/Sideload mode.

    If connected via ADB in normal mode, reboot into recovery.
    Returns True if the device is ready.
    """
    import time

    # Check if already in sideload or recovery
    try:
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in result.stdout.strip().splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2 and parts[1] in ("sideload", "recovery"):
                task.emit("Device is in recovery/sideload mode.", "success")
                return True
    except Exception:
        pass

    # Check if in normal ADB mode — reboot to recovery
    try:
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        has_adb = any(
            "device" in line.split("\t")[-1:] for line in result.stdout.strip().splitlines()[1:] if line.strip()
        )
    except Exception:
        has_adb = False

    if has_adb:
        task.emit("Device connected via ADB. Switching to Recovery Mode automatically...", "info")
        rc = task.run_shell(["adb", "reboot", "recovery"])
        if rc != 0:
            task.emit("Failed to reboot into recovery.", "error")
            return False

        task.emit("Waiting for recovery mode...", "info")
        for _i in range(20):
            time.sleep(2)
            try:
                check = subprocess.run(
                    ["adb", "devices"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                for line in check.stdout.strip().splitlines()[1:]:
                    parts = line.split()
                    if len(parts) >= 2 and parts[1] in ("sideload", "recovery"):
                        task.emit("Device is in recovery mode!", "success")
                        return True
            except Exception:
                pass

        task.emit("Device didn't enter sideload mode within 40 seconds.", "warn")
        task.emit("In TWRP: go to Advanced > ADB Sideload > swipe to start.", "info")
        task.emit("In stock recovery: select 'Apply update from ADB'.", "info")
        task.emit("Waiting 30 more seconds for sideload mode...", "info")
        for _i in range(15):
            time.sleep(2)
            try:
                check = subprocess.run(
                    ["adb", "devices"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                for line in check.stdout.strip().splitlines()[1:]:
                    parts = line.split()
                    if len(parts) >= 2 and parts[1] in ("sideload", "recovery"):
                        task.emit("Device is in sideload mode!", "success")
                        return True
            except Exception:
                pass
        task.emit("Proceeding anyway — if the device is ready, the sideload will start.", "warn")
        return True  # Let the user proceed manually

    # No device yet — it may still be booting. Wait up to 30s for any ADB connection.
    task.emit("No device detected yet. Waiting for device to boot...", "info")
    for _i in range(15):
        time.sleep(2)
        try:
            result = subprocess.run(
                ["adb", "devices"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            for line in result.stdout.strip().splitlines()[1:]:
                parts = line.split()
                if len(parts) >= 2:
                    if parts[1] in ("sideload", "recovery"):
                        task.emit("Device is in recovery/sideload mode!", "success")
                        return True
                    if parts[1] == "device":
                        task.emit("Device connected. Switching to Recovery Mode...", "info")
                        rc = task.run_shell(["adb", "reboot", "recovery"])
                        if rc != 0:
                            task.emit("Failed to reboot into recovery.", "error")
                            return False
                        task.emit("Waiting for recovery mode...", "info")
                        for _ in range(20):
                            time.sleep(2)
                            try:
                                check = subprocess.run(
                                    ["adb", "devices"],
                                    capture_output=True,
                                    text=True,
                                    timeout=5,
                                )
                                for cl in check.stdout.strip().splitlines()[1:]:
                                    cp = cl.split()
                                    if len(cp) >= 2 and cp[1] in ("sideload", "recovery"):
                                        task.emit("Device is in recovery mode!", "success")
                                        return True
                            except Exception:
                                pass
                        task.emit("Device in recovery but not in sideload mode yet.", "warn")
                        task.emit("In TWRP: go to Advanced > ADB Sideload > swipe to start.", "info")
                        return True
        except Exception:
            pass

    task.emit("No device detected after waiting. Connect your device and try again.", "warn")
    return False


def _heimdall_flash(task: Task, args: list[str]) -> int:
    """Run a heimdall flash command with error detection and user guidance.

    Captures output and provides specific recovery instructions for
    common Heimdall failure modes.
    """
    task.emit(f"$ heimdall {' '.join(args)}", "cmd")

    proc = subprocess.Popen(
        ["heimdall"] + args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    task._proc = proc
    output_lines = []
    for line in proc.stdout:
        stripped = line.rstrip()
        if stripped:
            task.emit(stripped)
            output_lines.append(stripped.lower())
    proc.wait()
    task._proc = None
    rc = proc.returncode
    full = " ".join(output_lines)

    # Heimdall may exit non-zero when the device reboots after a successful flash
    # (USB connection drops). Detect this and treat as success.
    upload_ok = "upload successful" in full
    rebooting = "rebooting device" in full
    if rc != 0 and upload_ok and rebooting:
        task.emit("Connection lost during reboot — this is normal after flashing.", "info")
        return 0

    if rc != 0:
        if "protocol initialisation failed" in full:
            task.emit("", "error")
            task.emit("CONNECTION TO DEVICE FAILED", "error")
            task.emit("", "info")
            task.emit("The device's Download Mode session has gone stale. To fix this:", "info")
            task.emit("  1. Unplug the USB cable", "info")
            task.emit("  2. Hold Power for 10+ seconds to force restart", "info")
            task.emit("  3. Once fully off, re-enter Download Mode:", "info")
            task.emit("     Samsung: hold Volume Down + Home + Power", "info")
            task.emit("  4. Plug the USB cable back in", "info")
            task.emit("  5. Try again", "info")

        elif "claiming interface" in full and ("access" in full or "permission" in full or "libusb" in full):
            task.emit("", "error")
            task.emit("USB PERMISSION DENIED", "error")
            task.emit("", "info")
            task.emit("OSmosis cannot access the USB device. Run this once to fix:", "info")
            task.emit("  sudo bash scripts/setup-udev.sh", "cmd")
            task.emit("Then unplug and replug the device.", "info")

        elif "detecting device" in full and "failed" in full:
            task.emit("", "error")
            task.emit("NO DEVICE FOUND", "error")
            task.emit("", "info")
            task.emit("Make sure your device is:", "info")
            task.emit("  1. Connected via USB", "info")
            task.emit("  2. In Download Mode (not normal boot or recovery)", "info")
            task.emit("  3. The USB cable supports data transfer (not charge-only)", "info")

        elif "upload failed" in full or "flash failed" in full:
            task.emit("", "error")
            task.emit("FLASH FAILED", "error")
            task.emit("", "info")
            task.emit("The transfer was interrupted. Try:", "info")
            task.emit("  1. Use a different USB port (avoid hubs)", "info")
            task.emit("  2. Use a shorter/better USB cable", "info")
            task.emit("  3. Re-enter Download Mode and try again", "info")

        else:
            task.emit(f"Heimdall failed (exit {rc}).", "error")

    return rc


def _verify_before_flash(task: Task, fw_path: str) -> dict:
    """Verify a firmware file against the registry before flashing.

    Emits status messages to the task. Returns the verification result.
    """
    task.emit("Verifying firmware against registry...", "info")
    result = verify(fw_path)
    task.emit(f"SHA256: {result['sha256']}")
    if result["known"]:
        match = result["matches"][0]
        task.emit(
            f"Verified: matches registry entry "
            f"({match.get('device_label', '')} {match.get('version', '')} via {match.get('flash_method', '')})",
            "success",
        )
    else:
        task.emit(
            "Warning: this firmware is NOT in the registry. "
            "It may be safe, but it hasn't been flashed by Osmosis before. Proceeding.",
            "warn",
        )
    task.emit("")
    return result


@bp.route("/api/flash/stock", methods=["POST"])
def api_flash_stock():
    """Flash stock firmware from a ZIP path."""
    fw_zip = request.json.get("fw_zip", "")
    if not fw_zip or not Path(fw_zip).is_file():
        return jsonify({"error": "Firmware ZIP not found"}), 400

    def _run(task: Task):
        task.emit(f"Firmware ZIP: {fw_zip}")
        _verify_before_flash(task, fw_zip)

        work_dir = Path.home() / "Downloads" / (Path(fw_zip).stem + "-unpacked")
        work_dir.mkdir(parents=True, exist_ok=True)
        task.emit(f"Working directory: {work_dir}")

        task.emit("Extracting firmware ZIP...", "info")
        rc = task.run_shell(["unzip", "-o", fw_zip, "-d", str(work_dir)])
        if rc != 0:
            task.done(False)
            return

        import glob

        for pattern in ["BL_*.tar.md5", "AP_*.tar.md5", "CP_*.tar.md5", "CSC_*.tar.md5"]:
            for f in glob.glob(str(work_dir / pattern)):
                task.emit(f"Extracting {Path(f).name}")
                task.run_shell(["tar", "-xvf", f, "-C", str(work_dir)])

        images = {}
        for name in ["boot.img", "recovery.img", "system.img", "super.img", "modem.bin", "cache.img", "vbmeta.img"]:
            p = work_dir / name
            if p.exists():
                images[name.split(".")[0].upper()] = str(p)

        task.emit(f"Detected images: {', '.join(images.keys()) or 'none'}")

        flash_args = ["flash"]
        for part, path in images.items():
            flash_args.extend([f"--{part}", path])

        if not _ensure_download_mode(task):
            task.done(False)
            return

        rc = _heimdall_flash(task, flash_args)
        if rc == 0:
            task.emit("Flash complete!", "success")
            register(fw_zip, flash_method="heimdall-stock", component="stock")
        task.done(rc == 0)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@bp.route("/api/flash/recovery", methods=["POST"])
def api_flash_recovery():
    """Flash custom recovery image.

    Optional params:
        fix_boot: if true, also flash recovery image to BOOT partition
                  to fix devices stuck in Download Mode loop (corrupted boot).
    """
    img_path = request.json.get("recovery_img", "")
    fix_boot = request.json.get("fix_boot", False)
    if not img_path or not Path(img_path).is_file():
        return jsonify({"error": "Recovery image not found"}), 400

    def _run(task: Task):

        task.emit(f"Recovery image: {img_path}")
        result = _verify_before_flash(task, img_path)
        h = result["sha256"]

        # Auto-switch to Download Mode if device is in ADB mode
        if not _ensure_download_mode(task):
            task.done(False)
            return

        flash_args = ["flash", "--RECOVERY", img_path]
        if fix_boot:
            flash_args.extend(["--BOOT", img_path])
            task.emit("Also flashing to BOOT partition (boot repair).", "info")
        flash_args.append("--no-reboot")

        rc = _heimdall_flash(task, flash_args)
        if rc != 0:
            task.done(False)
            return

        task.emit("TWRP Recovery flashed successfully!", "success")
        if fix_boot:
            task.emit("Boot partition repaired — device should now boot into TWRP.", "success")
        register(img_path, flash_method="heimdall", component="recovery", sha256=h)
        task.emit("", "info")
        task.emit("Now boot into TWRP Recovery:", "info")
        task.emit("  1. Unplug the USB cable", "info")
        task.emit("  2. Remove the battery, wait 5 seconds, reinsert it", "info")
        task.emit("  3. Press Power to boot — TWRP should load automatically", "info")
        if not fix_boot:
            task.emit("     If it goes to Download Mode, hold Volume Up + Home + Power instead", "info")
        task.emit("  4. Plug USB back in once TWRP is loaded", "info")
        task.emit("  5. In TWRP: go to Advanced > ADB Sideload > swipe to start", "info")
        task.done(True)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@bp.route("/api/reboot-download", methods=["POST"])
def api_reboot_download():
    """Reboot device into Samsung Download Mode via ADB."""

    def _run(task: Task):
        task.emit("Checking device connection...")
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=5)
        if "device" not in result.stdout:
            task.emit("No device connected via ADB.", "error")
            task.emit("Connect your device with USB debugging enabled.", "info")
            task.done(False)
            return

        task.emit("Rebooting into Download Mode...")
        rc = task.run_shell(["adb", "reboot", "download"])
        if rc == 0:
            task.emit("Reboot command sent. Device should enter Download Mode shortly.", "success")
            task.emit("Waiting for device in Download Mode...", "info")
            import time

            for _ in range(15):
                time.sleep(2)
                try:
                    detect = subprocess.run(
                        ["heimdall", "detect"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if detect.returncode == 0:
                        task.emit("Device is in Download Mode!", "success")
                        task.done(True)
                        return
                except Exception:
                    pass
            task.emit("Device didn't appear in Download Mode within 30 seconds.", "warn")
            task.emit("It may still be rebooting — wait a moment and try again.", "info")
        task.done(rc == 0)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@bp.route("/api/reboot-normal", methods=["POST"])
def api_reboot_normal():
    """Reboot device to normal mode from recovery/sideload for identification."""

    def _run(task: Task):
        import time

        task.emit("Rebooting device to normal mode for identification...")

        # Try adb reboot first (works from recovery and sometimes sideload)
        rc = task.run_shell(["adb", "reboot"])
        if rc != 0:
            # Try adb shell reboot as fallback
            task.run_shell(["adb", "shell", "reboot"])

        task.emit("Reboot command sent. Waiting for device to boot...", "info")

        # Wait for device to appear in normal ADB mode
        for _i in range(30):
            time.sleep(3)
            try:
                check = subprocess.run(
                    ["adb", "devices"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                for line in check.stdout.strip().splitlines()[1:]:
                    parts = line.split("\t")
                    if len(parts) >= 2 and parts[1] == "device":
                        task.emit("Device is back in normal mode!", "success")
                        task.done(True)
                        return
            except Exception:
                pass

        task.emit("Device didn't appear in normal mode within 90 seconds.", "warn")
        task.emit("It may still be booting — wait a moment and retry detection.", "info")
        task.done(False)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@bp.route("/api/reboot-from-download", methods=["POST"])
def api_reboot_from_download():
    """Reboot a device stuck in Samsung Download Mode via Heimdall."""

    def _run(task: Task):
        import fcntl
        import time

        task.emit("Detecting device in Download Mode...")
        rc = task.run_shell(["heimdall", "detect"])
        if rc != 0:
            task.emit("No device found in Download Mode.", "error")
            task.done(False)
            return

        # Try USB reset first to recover stale Heimdall sessions
        try:
            lsusb = subprocess.run(
                ["lsusb"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            for line in lsusb.stdout.splitlines():
                if "04e8" in line:  # Samsung vendor ID
                    parts = line.split()
                    bus = parts[1]
                    dev = parts[3].rstrip(":")
                    path = f"/dev/bus/usb/{bus}/{dev}"
                    task.emit(f"Resetting USB connection ({path})...")
                    fd = os.open(path, os.O_WRONLY)
                    USBDEVFS_RESET = 0x5514
                    fcntl.ioctl(fd, USBDEVFS_RESET, 0)
                    os.close(fd)
                    time.sleep(2)
                    break
        except Exception as e:
            task.emit(f"USB reset skipped: {e}", "info")

        task.emit("Sending reboot command...")
        rc = task.run_shell(["heimdall", "close-pc-screen"])
        if rc == 0:
            task.emit("Reboot command sent! Device should restart shortly.", "success")
            task.emit("Waiting for device to boot...", "info")
            for _ in range(20):
                time.sleep(2)
                try:
                    check = subprocess.run(
                        ["adb", "devices"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if any(
                        "device" in line.split("\t")[-1:]
                        for line in check.stdout.strip().splitlines()[1:]
                        if line.strip()
                    ):
                        task.emit("Device is back in normal mode!", "success")
                        task.done(True)
                        return
                except Exception:
                    pass
            task.emit("Device may still be booting. Try detecting again in a moment.", "info")
            task.done(True)
        else:
            task.emit("", "error")
            task.emit("COULD NOT REBOOT — DEVICE SESSION IS STALE", "error")
            task.emit("", "info")
            task.emit("The Download Mode session has been open too long and is no longer responding.", "info")
            task.emit("To restart your device:", "info")
            task.emit("  1. Unplug the USB cable", "info")
            task.emit("  2. Hold Power for 10+ seconds until the screen goes black", "info")
            task.emit("  3. Wait a few seconds, then press Power to boot normally", "info")
            task.emit("  4. Once booted, plug USB back in and retry detection", "info")
            task.emit("__error_type:stale_session", "error")
            task.done(False)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@bp.route("/api/reboot-recovery", methods=["POST"])
def api_reboot_recovery():
    """Reboot the device into recovery mode via ADB."""

    def _run(task: Task):
        task.emit("Checking ADB connection...")
        rc = task.run_shell(["adb", "devices"])
        if rc != 0:
            task.emit("ADB not available.", "error")
            task.done(False)
            return

        # Check if already in sideload mode
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=5)
        if "sideload" in result.stdout:
            task.emit("Device is already in sideload mode!", "success")
            task.done(True)
            return

        task.emit("Sending reboot-recovery command...", "info")
        rc = task.run_shell(["adb", "reboot", "recovery"])
        if rc == 0:
            task.emit(
                "Reboot command sent. Device should boot into recovery shortly.",
                "success",
            )
            task.emit(
                "Once in recovery, enable ADB sideload:\n"
                "  TWRP: Advanced > ADB Sideload > Swipe to start\n"
                "  Stock recovery: Apply update from ADB",
                "info",
            )
        else:
            task.emit("Failed to send reboot command. You may need to reboot manually.", "warn")
        task.done(rc == 0)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@bp.route("/api/sideload-ready")
def api_sideload_ready():
    """Check whether a device is currently in ADB sideload mode."""
    try:
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=5)
        lines = result.stdout.strip().splitlines()
        for line in lines[1:]:  # skip header
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "sideload":
                return jsonify({"ready": True, "serial": parts[0]})
            if len(parts) >= 2 and parts[1] == "recovery":
                return jsonify({"ready": False, "recovery": True, "serial": parts[0]})
        # No ADB device — check if stuck in Download Mode
        try:
            dl = subprocess.run(
                ["heimdall", "detect"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if dl.returncode == 0:
                return jsonify({"ready": False, "recovery": False, "download_mode": True})
        except Exception:
            pass
        return jsonify({"ready": False, "recovery": False})
    except Exception:
        return jsonify({"ready": False, "recovery": False})


@bp.route("/api/sideload", methods=["POST"])
def api_sideload():
    """ADB sideload a ZIP."""
    zip_path = request.json.get("zip_path", "")
    label = request.json.get("label", "ROM")
    if not zip_path or not Path(zip_path).is_file():
        return jsonify({"error": "ZIP file not found"}), 400

    def _run(task: Task):
        task.emit(f"Sideloading {label}: {zip_path}")

        # Verify ZIP integrity — check PK header (signed Android OTA ZIPs
        # use a non-standard format that Python's zipfile module can't parse)
        try:
            with open(zip_path, "rb") as f:
                header = f.read(4)
                if header != b"PK\x03\x04":
                    task.emit("ROM file is not a valid ZIP (bad header).", "error")
                    task.emit("The download may be incomplete or corrupted. Please re-download.", "info")
                    task.done(False)
                    return
                fsize = Path(zip_path).stat().st_size
                if fsize < 1_000_000:
                    task.emit(f"ROM file is suspiciously small ({fsize} bytes).", "error")
                    task.emit("The download may be incomplete. Please re-download.", "info")
                    task.done(False)
                    return
        except OSError as e:
            task.emit(f"Cannot read ROM file: {e}", "error")
            task.done(False)
            return

        result = _verify_before_flash(task, zip_path)
        h = result["sha256"]

        # Auto-switch to recovery/sideload mode if device is in normal ADB
        if not _ensure_recovery_mode(task):
            task.emit("Could not enter recovery mode automatically.", "error")
            task.emit("Please boot into recovery manually and enable ADB sideload.", "info")
            task.done(False)
            return

        # Run sideload with stall detection.
        # adb sideload can hang forever when the phone rejects the ROM —
        # it keeps retrying the send. We detect stalls by monitoring
        # whether the progress percentage stops advancing.
        import re
        import time as _time

        proc = subprocess.Popen(
            ["adb", "sideload", zip_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        task._proc = proc

        output_lines = []
        last_pct = -1
        last_progress_time = _time.monotonic()
        stall_timeout = 30  # seconds without progress = stalled
        connection_failed = False

        import selectors

        sel = selectors.DefaultSelector()
        sel.register(proc.stdout, selectors.EVENT_READ)

        while proc.poll() is None:
            if task.cancelled:
                proc.terminate()
                break

            events = sel.select(timeout=2.0)
            if not events:
                # No output — check for stall
                elapsed = _time.monotonic() - last_progress_time
                if elapsed > stall_timeout and last_pct >= 0:
                    task.emit(f"Transfer stalled at {last_pct}% for {int(elapsed)}s — aborting.", "warn")
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                    break
                continue

            line = proc.stdout.readline()
            if not line:
                break

            stripped = line.rstrip()
            lower = stripped.lower()
            output_lines.append(lower)

            # Detect connection failure early
            if "connection failed" in lower or "closed" in lower:
                connection_failed = True

            # Parse percentage
            m = re.search(r"(\d+)%", stripped)
            if m:
                pct = int(m.group(1))
                if pct != last_pct:
                    last_pct = pct
                    last_progress_time = _time.monotonic()
                    # Only emit on percentage changes to avoid flooding
                    task.emit(stripped)
                # If same percentage repeats many times, check stall
                elif _time.monotonic() - last_progress_time > stall_timeout:
                    task.emit(f"Transfer stuck at {pct}% — phone likely rejected the ROM.", "warn")
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                    break
            else:
                task.emit(stripped)

        sel.close()

        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        task._proc = None
        rc = proc.returncode or 0

        full_output = " ".join(output_lines)

        # Detect failure patterns
        # "failed to read command: Success" is normal — TWRP disconnects
        # after accepting the full payload (often before 100%).
        # Stock recovery failures show: "sideload connection failed: closed",
        # "signature verification failed", or progress stalls at low %.
        signature_errors = [
            "signature verification failed",
            "signature failed",
            "failed to verify",
            "verification failed",
            "e:footer is wrong",
            "e:error in",
            "installation aborted",
        ]
        stock_reject = [
            "sideload connection failed",
        ]
        has_sig_error = any(kw in full_output for kw in signature_errors)
        has_stock_reject = any(kw in full_output for kw in stock_reject)
        # "failed to read command: Success" means TWRP accepted the ROM
        twrp_success_disconnect = "failed to read command: success" in full_output
        # Stall at low percentage (<50%) with stock rejection = real failure
        # TWRP often disconnects at 80-95% which is normal completion
        stalled_low = last_pct >= 0 and last_pct < 50 and (has_stock_reject or connection_failed)

        if has_sig_error or stalled_low or (has_stock_reject and not twrp_success_disconnect):
            task.emit("", "error")
            task.emit("SIDELOAD FAILED — ROM REJECTED BY RECOVERY", "error")
            task.emit("", "error")
            if connection_failed or has_stock_reject:
                task.emit("The sideload connection was closed by the device.", "error")
            if stalled_low:
                task.emit(f"Transfer stopped at {last_pct}%.", "error")
            task.emit("", "error")
            task.emit(
                "Your device's stock recovery rejected this ROM. "
                "Custom ROMs require a custom recovery (TWRP) to install.",
                "error",
            )
            task.emit("", "info")
            task.emit("To fix this:", "info")
            task.emit("  1. Install TWRP recovery (use the installer below)", "info")
            task.emit("  2. Boot into TWRP (Volume Up + Home + Power)", "info")
            task.emit("  3. In TWRP: Advanced > ADB Sideload > Swipe to start", "info")
            task.emit("  4. Try the sideload again", "info")
            task.emit("", "info")
            task.emit("Your device is safe — nothing was changed.", "success")
            task.emit("__error_type:signature_verification_failed", "error")
            task.done(False)
        elif twrp_success_disconnect or (rc == 0 and last_pct >= 50):
            # TWRP disconnects after receiving the payload. But a disconnect
            # below ~95% often means the transfer was truncated and TWRP will
            # report "zip corrupt". Check if the transfer looks complete.
            if last_pct < 95:
                task.emit("", "warn")
                task.emit(f"Transfer ended at {last_pct}% — the ROM may not have been fully received.", "warn")
                task.emit("Check your device screen:", "info")
                task.emit("  - If TWRP shows 'Install complete': the flash succeeded! Reboot your device.", "info")
                task.emit("  - If TWRP shows 'Zip corrupt' or an error: the transfer was incomplete.", "warn")
                task.emit("", "info")
                task.emit("If the transfer failed, try these fixes:", "info")
                task.emit("  1. Use a shorter, higher-quality USB cable", "info")
                task.emit("  2. Connect directly to a USB port on your computer (not a hub)", "info")
                task.emit("  3. Try again — sideload transfers can be flaky", "info")
                task.emit("", "info")
                task.emit("Or use the more reliable push method:", "info")
                task.emit("  The ROM will be copied to your device's storage, then installed from TWRP.", "info")
                task.emit("__error_type:incomplete_transfer", "warn")
                task.done(False)
            else:
                task.emit(f"{label} sideload complete!", "success")
                register(zip_path, flash_method="adb-sideload", component=label.lower(), sha256=h)
                task.done(True)
        elif rc == 0 and last_pct >= 98:
            task.emit(f"{label} sideload complete!", "success")
            register(zip_path, flash_method="adb-sideload", component=label.lower(), sha256=h)
            task.done(True)
        elif rc == 0:
            # Reached 0% or adb exited 0 but we're not sure it worked
            # Check if device is still in sideload/recovery
            _time.sleep(3)
            try:
                check = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=5)
                still_in_recovery = any(
                    p[1] in ("sideload", "recovery")
                    for line in check.stdout.strip().splitlines()[1:]
                    if len(p := line.split()) >= 2
                )
            except Exception:
                still_in_recovery = False

            if still_in_recovery:
                task.emit("", "error")
                task.emit("SIDELOAD FAILED — ROM REJECTED BY RECOVERY", "error")
                task.emit(
                    "The device is still in recovery mode, meaning the ROM was not installed.",
                    "error",
                )
                task.emit("You likely need TWRP to install custom ROMs.", "error")
                task.emit("__error_type:signature_verification_failed", "error")
                task.done(False)
            else:
                task.emit(f"{label} sideload complete!", "success")
                register(zip_path, flash_method="adb-sideload", component=label.lower(), sha256=h)
                task.done(True)
        else:
            task.emit(f"Sideload failed (exit {rc}).", "error")
            task.done(False)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@bp.route("/api/flash/push-install", methods=["POST"])
def api_push_install():
    """Push ROM to device storage and install via TWRP — fallback for flaky sideload."""
    zip_path = request.json.get("zip_path", "")
    label = request.json.get("label", "ROM")
    if not zip_path or not Path(zip_path).is_file():
        return jsonify({"error": "ROM file not found"}), 400

    def _run(task: Task):
        import time as _time

        filename = Path(zip_path).name
        device_path = f"/sdcard/{filename}"

        task.emit(f"Pushing {filename} to device storage...", "info")
        task.emit("This is more reliable than sideload — the full file is copied first, then installed.", "info")

        # Check device is in recovery mode with adb access
        try:
            check = subprocess.run(
                ["adb", "devices"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            has_recovery = "recovery" in check.stdout
            if not has_recovery:
                task.emit("Device is not in TWRP recovery mode.", "error")
                task.emit("Boot into TWRP, then try again.", "info")
                task.done(False)
                return
        except Exception:
            task.emit("Cannot reach device via ADB.", "error")
            task.done(False)
            return

        # Push file to device
        rc = task.run_shell(["adb", "push", zip_path, device_path])
        if rc != 0:
            task.emit("Failed to push ROM to device.", "error")
            task.emit("Check USB connection and try again.", "info")
            task.done(False)
            return

        task.emit(f"ROM copied to {device_path}", "success")
        task.emit("Installing via TWRP...", "info")

        # Install via TWRP's OpenRecoveryScript
        rc = task.run_shell(
            [
                "adb",
                "shell",
                f"echo 'install {device_path}' > /cache/recovery/openrecoveryscript",
            ]
        )
        if rc != 0:
            # Fallback: tell user to install manually from TWRP
            task.emit("Could not auto-install. Please install manually from TWRP:", "warn")
            task.emit(f"  In TWRP: Install > select {filename} from Internal Storage > Swipe to flash", "info")  # noqa: S608
            task.emit("__error_type:manual_twrp_install", "warn")
            task.done(False)
            return

        # Trigger install and capture output
        result = subprocess.run(
            ["adb", "shell", "twrp", "install", device_path],
            capture_output=True,
            text=True,
            timeout=600,
        )
        for line in (result.stdout + result.stderr).splitlines():
            stripped = line.strip()
            if stripped:
                task.emit(stripped)

        output_lower = (result.stdout + result.stderr).lower()

        if "zip file is corrupt" in output_lower or "zip corrupt" in output_lower:
            task.emit("", "error")
            task.emit("RECOVERY REJECTED THE ROM — ZIP CORRUPT", "error")
            task.emit("", "info")
            task.emit("This usually means the recovery isn't compatible with this ROM's format.", "info")
            task.emit("Some ROMs require their own recovery (not generic TWRP).", "info")
            task.emit("", "info")
            task.emit("Check if your ROM project provides its own recovery image.", "info")
            task.emit("__error_type:zip_corrupt_wrong_recovery", "error")
            task.done(False)
            return

        if "error installing" in output_lower or "failed" in output_lower:
            task.emit("Installation reported an error. Check your device screen.", "warn")
            task.emit("__error_type:install_error", "warn")
            task.done(False)
            return

        _time.sleep(3)
        task.emit(f"{label} installed successfully!", "success")
        task.emit("You can now reboot your device.", "info")
        register(zip_path, flash_method="adb-push", component=label.lower())
        task.done(True)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@bp.route("/api/download", methods=["POST"])
def api_download():
    """Download files for a device preset."""
    device_id = request.json.get("device_id", "")
    selected = request.json.get("selected", [])

    devices = parse_devices_cfg()
    device = next((d for d in devices if d["id"] == device_id), None)
    if not device:
        return jsonify({"error": f"Device '{device_id}' not found"}), 404

    def _run(task: Task):
        target = Path.home() / "Osmosis-downloads" / device_id
        target.mkdir(parents=True, exist_ok=True)
        task.emit(f"Download directory: {target}")

        any_failed = False
        for key in selected:
            url = device.get(key, "")
            if not url:
                task.emit(f"No URL for {key}, skipping.", "warn")
                continue

            url_clean = url.split("?")[0]
            filename = Path(url_clean).name or f"{device_id}-{key}.bin"
            dest = str(target / filename)

            task.emit(f"Downloading {key}: {filename}...")
            rc = task.run_shell(["wget", "--progress=dot:giga", "-O", dest, url])
            if rc == 0:
                import hashlib

                h = hashlib.sha256(Path(dest).read_bytes()).hexdigest()
                task.emit(f"SHA256: {h}")
            else:
                task.emit(f"Failed to download {key}.", "error")
                if Path(dest).exists():
                    Path(dest).unlink(missing_ok=True)
                any_failed = True

        task.done(not any_failed)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@bp.route("/api/backup", methods=["POST"])
def api_backup():
    """Backup device partitions via ADB."""
    partitions = request.json.get("partitions", ["boot", "recovery"])
    backup_efs = request.json.get("backup_efs", False)
    device_label = request.json.get("label", "").strip()

    def _run(task: Task):
        import hashlib
        import re
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        safe_label = re.sub(r"[^a-zA-Z0-9_-]", "-", device_label)[:40] if device_label else ""
        folder_name = f"{safe_label}-{timestamp}" if safe_label else timestamp
        backup_path = BACKUP_DIR / folder_name
        backup_path.mkdir(parents=True, exist_ok=True)
        task.emit(f"Backup directory: {backup_path}")

        rc = task.run_shell(["adb", "devices"])
        if rc != 0:
            task.emit("ADB not available.", "error")
            task.done(False)
            return

        result = subprocess.run(
            ["adb", "shell", "su", "-c", "id"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        has_root = "uid=0" in result.stdout

        if has_root:
            task.emit("Root access available.", "success")
            for part in partitions:
                task.emit(f"Backing up {part}...")
                dest = backup_path / f"{part}.img"
                try:
                    with open(dest, "wb") as f:
                        proc = subprocess.Popen(
                            [
                                "adb",
                                "shell",
                                "su",
                                "-c",
                                f"dd if=$(ls /dev/block/platform/*/by-name/{part} "
                                f"/dev/block/by-name/{part} 2>/dev/null | head -1)",
                            ],
                            stdout=f,
                            stderr=subprocess.PIPE,
                        )
                        proc.wait(timeout=120)
                    if dest.stat().st_size > 0:
                        task.emit(f"{part} saved ({dest.stat().st_size // 1024}K).", "success")
                    else:
                        task.emit(f"Failed to back up {part} (empty file).", "error")
                        dest.unlink(missing_ok=True)
                except Exception as e:
                    task.emit(f"Error backing up {part}: {e}", "error")

            if backup_efs:
                task.emit("Backing up EFS...")
                dest = backup_path / "efs.img"
                try:
                    with open(dest, "wb") as f:
                        proc = subprocess.Popen(
                            [
                                "adb",
                                "shell",
                                "su",
                                "-c",
                                "dd if=$(ls /dev/block/platform/*/by-name/efs "
                                "/dev/block/by-name/efs 2>/dev/null | head -1)",
                            ],
                            stdout=f,
                            stderr=subprocess.PIPE,
                        )
                        proc.wait(timeout=120)
                    if dest.stat().st_size > 0:
                        task.emit(f"EFS saved ({dest.stat().st_size // 1024}K).", "success")
                    else:
                        dest.unlink(missing_ok=True)
                        task.emit("EFS backup failed — trying adb pull /efs ...", "warn")
                        task.run_shell(["adb", "pull", "/efs", str(backup_path / "efs-folder")])
                except Exception as e:
                    task.emit(f"Error backing up EFS: {e}", "error")
        else:
            task.emit("No root access. Pulling /sdcard/ instead.", "warn")
            task.run_shell(["adb", "pull", "/sdcard/", str(backup_path / "sdcard")])

        checksums = []
        for f in backup_path.glob("*.img"):
            h = hashlib.sha256(f.read_bytes()).hexdigest()
            checksums.append(f"{h}  {f.name}")
        if checksums:
            (backup_path / "checksums.sha256").write_text("\n".join(checksums) + "\n")
            task.emit("Checksums saved.", "success")

        task.emit(f"Backup complete: {backup_path}", "success")
        task.done(True)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@bp.route("/api/backup/full", methods=["POST"])
def api_backup_full():
    """Full NAND backup for Samsung devices — all partitions including system.

    Requires root access (TWRP or rooted device).
    """

    def _run(task: Task):
        import hashlib
        from datetime import datetime

        backup_path = BACKUP_DIR / datetime.now().strftime("%Y%m%d-%H%M%S-full")
        backup_path.mkdir(parents=True, exist_ok=True)
        task.emit(f"Full backup directory: {backup_path}")

        rc = task.run_shell(["adb", "devices"])
        if rc != 0:
            task.emit("ADB not available.", "error")
            task.done(False)
            return

        result = subprocess.run(
            ["adb", "shell", "su", "-c", "id"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        has_root = "uid=0" in result.stdout

        if not has_root:
            task.emit("Root access required for full NAND backup.", "error")
            task.emit("Boot into TWRP recovery for root ADB access.", "warn")
            task.done(False)
            return

        task.emit("Root access confirmed.", "success")

        # Discover all partitions from the partition table
        task.emit("Discovering partitions...")
        result = subprocess.run(
            [
                "adb",
                "shell",
                "su",
                "-c",
                "ls /dev/block/platform/*/by-name/ 2>/dev/null || ls /dev/block/by-name/ 2>/dev/null",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        partitions = [p.strip() for p in result.stdout.strip().split() if p.strip()]

        if not partitions:
            task.emit("Could not discover partitions.", "error")
            task.done(False)
            return

        task.emit(
            f"Found {len(partitions)} partitions: {', '.join(partitions[:10])}{'...' if len(partitions) > 10 else ''}"
        )

        # Core partitions to always back up
        core_parts = ["boot", "recovery", "efs", "param", "modem"]
        # Large partitions
        large_parts = ["system", "super", "cache", "hidden", "userdata"]
        target_parts = [p for p in partitions if p in core_parts + large_parts]
        other_parts = [p for p in partitions if p not in core_parts + large_parts]

        task.emit(f"Backing up {len(target_parts)} core/large partitions...")

        backed_up = 0
        for part in target_parts:
            task.emit(f"Backing up {part}...")
            dest = backup_path / f"{part}.img"
            try:
                with open(dest, "wb") as f:
                    proc = subprocess.Popen(
                        [
                            "adb",
                            "shell",
                            "su",
                            "-c",
                            f"dd if=$(ls /dev/block/platform/*/by-name/{part} "
                            f"/dev/block/by-name/{part} 2>/dev/null | head -1)",
                        ],
                        stdout=f,
                        stderr=subprocess.PIPE,
                    )
                    proc.wait(timeout=600)
                if dest.stat().st_size > 0:
                    size_mb = dest.stat().st_size / (1024 * 1024)
                    task.emit(f"  {part}: {size_mb:.1f} MB", "success")
                    backed_up += 1
                else:
                    dest.unlink(missing_ok=True)
                    task.emit(f"  {part}: empty (skipped)", "warn")
            except subprocess.TimeoutExpired:
                task.emit(f"  {part}: timed out", "warn")
                dest.unlink(missing_ok=True)
            except Exception as e:
                task.emit(f"  {part}: error - {e}", "error")

        # Back up small unknown partitions
        for part in other_parts:
            dest = backup_path / f"{part}.img"
            try:
                with open(dest, "wb") as f:
                    proc = subprocess.Popen(
                        [
                            "adb",
                            "shell",
                            "su",
                            "-c",
                            f"dd if=$(ls /dev/block/platform/*/by-name/{part} "
                            f"/dev/block/by-name/{part} 2>/dev/null | head -1)",
                        ],
                        stdout=f,
                        stderr=subprocess.PIPE,
                    )
                    proc.wait(timeout=60)
                if dest.stat().st_size > 0 and dest.stat().st_size < 100 * 1024 * 1024:
                    size_mb = dest.stat().st_size / (1024 * 1024)
                    task.emit(f"  {part}: {size_mb:.1f} MB", "success")
                    backed_up += 1
                else:
                    dest.unlink(missing_ok=True)
            except Exception:
                dest.unlink(missing_ok=True)

        # Generate checksums
        checksums = []
        for f in sorted(backup_path.glob("*.img")):
            h = hashlib.sha256(f.read_bytes()).hexdigest()
            checksums.append(f"{h}  {f.name}")
        if checksums:
            (backup_path / "checksums.sha256").write_text("\n".join(checksums) + "\n")

        # Save partition list
        (backup_path / "partitions.txt").write_text("\n".join(partitions) + "\n")

        task.emit(f"Full backup complete: {backed_up} partitions saved to {backup_path}", "success")
        task.done(True)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@bp.route("/api/backup/list")
def api_backup_list():
    """List all available backups."""
    if not BACKUP_DIR.exists():
        return jsonify([])

    backups = []
    for d in sorted(BACKUP_DIR.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        images = list(d.glob("*.img"))
        total_size = sum(f.stat().st_size for f in images)
        backups.append(
            {
                "name": d.name,
                "path": str(d),
                "partition_count": len(images),
                "partitions": [f.stem for f in sorted(images)],
                "total_size_mb": round(total_size / (1024 * 1024), 1),
                "has_checksums": (d / "checksums.sha256").exists(),
                "is_full": d.name.endswith("-full"),
            }
        )
    return jsonify(backups)


@bp.route("/api/backup/restore", methods=["POST"])
def api_restore():
    """Restore partitions from a backup via Heimdall.

    JSON body: {
        "backup_name": "20240101-120000",
        "partitions": ["boot", "recovery"]   // optional, defaults to all
    }
    """
    body = request.json or {}
    backup_name = body.get("backup_name", "")
    selected_partitions = body.get("partitions")

    backup_path = BACKUP_DIR / backup_name
    if not backup_path.is_dir():
        return jsonify({"error": f"Backup '{backup_name}' not found"}), 404

    def _run(task: Task):
        import hashlib

        task.emit(f"Restoring from backup: {backup_name}")

        # Verify checksums first
        checksum_file = backup_path / "checksums.sha256"
        if checksum_file.exists():
            task.emit("Verifying checksums...")
            for line in checksum_file.read_text().strip().splitlines():
                parts = line.split("  ", 1)
                if len(parts) != 2:
                    continue
                expected_hash, filename = parts
                filepath = backup_path / filename
                if not filepath.exists():
                    task.emit(f"  {filename}: MISSING", "error")
                    task.done(False)
                    return
                actual_hash = hashlib.sha256(filepath.read_bytes()).hexdigest()
                if actual_hash != expected_hash:
                    task.emit(f"  {filename}: CHECKSUM MISMATCH", "error")
                    task.done(False)
                    return
                task.emit(f"  {filename}: OK", "success")

        images = list(backup_path.glob("*.img"))
        if selected_partitions:
            images = [f for f in images if f.stem in selected_partitions]

        if not images:
            task.emit("No partition images to restore.", "error")
            task.done(False)
            return

        task.emit(f"Restoring {len(images)} partition(s): {', '.join(f.stem for f in images)}")
        task.emit("Ensure device is in Download Mode.", "warn")

        flash_args = ["flash"]
        for img in images:
            flash_args.extend([f"--{img.stem.upper()}", str(img)])

        rc = _heimdall_flash(task, flash_args)
        if rc == 0:
            task.emit("Restore complete!", "success")
        task.done(rc == 0)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})
