"""Xiaomi MIAssistant recovery sideload routes.

Handles the MIUI Recovery 5.0 "Connect with MIAssistant" flow where the
device appears in ADB sideload mode and accepts a stock ROM ZIP via
``adb sideload <rom.zip>``.
"""

import subprocess
import time
from pathlib import Path

from flask import Blueprint, jsonify, request

from web.core import Task, cmd_exists, parse_devices_cfg, start_task
from web.ipfs_helpers import ipfs_available, ipfs_pin_and_index
from web.miassistant_protocol import (
    REGION_ROM_CODES,
    XIAOMI_REGIONS,
    detect_region,
    identify_xiaomi_sideload,
    parse_device_info,
)
from web.registry import register, verify

bp = Blueprint("miassistant", __name__)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@bp.route("/api/miassistant/status")
def api_miassistant_status():
    """Detect whether a Xiaomi device is in MIAssistant (ADB sideload) mode.

    Returns device identification when possible, otherwise reports the
    raw sideload serial so the frontend can prompt the user to confirm
    the model.
    """
    if not cmd_exists("adb"):
        return jsonify({"error": "adb not installed"}), 503

    try:
        result = subprocess.run(
            ["adb", "devices", "-l"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in result.stdout.strip().splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "sideload":
                serial = parts[0]

                # Extract model: from "adb devices -l" output fields
                model_from_adb = ""
                for token in parts[2:]:
                    if token.startswith("model:"):
                        model_from_adb = token.split(":", 1)[1]
                        break

                ident = identify_xiaomi_sideload(serial)
                if not ident and model_from_adb:
                    ident = identify_xiaomi_sideload(model_from_adb)

                # Also try USB info for Xiaomi vendor ID 2717
                usb_hint = _check_xiaomi_usb()

                if ident:
                    # Match against devices.cfg for firmware URLs
                    match = None
                    for dev in parse_devices_cfg():
                        if (
                            dev["codename"].lower() == ident["codename"].lower()
                            or dev["model"].lower() == ident["model"].lower()
                        ):
                            match = dev
                            break

                    return jsonify(
                        {
                            "connected": True,
                            "mode": "miassistant_sideload",
                            "serial": serial,
                            "model": ident["model"],
                            "codename": ident["codename"],
                            "display_name": ident["display_name"],
                            "match": match,
                            "hint": (
                                f"{ident['display_name']} detected in MIAssistant sideload mode. "
                                "Ready to receive a stock ROM ZIP."
                            ),
                        }
                    )

                return jsonify(
                    {
                        "connected": True,
                        "mode": "miassistant_sideload",
                        "serial": serial,
                        "model": "",
                        "codename": "",
                        "display_name": "Xiaomi device" if usb_hint else "Unknown device",
                        "match": None,
                        "hint": (
                            "Device is in ADB sideload mode (MIAssistant). "
                            "Could not auto-detect model. Please select your device manually."
                        ),
                    }
                )

        return jsonify({"connected": False, "hint": "No device in MIAssistant sideload mode detected."})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


_MIASST_BIN = str(Path(__file__).resolve().parent.parent.parent / "tools" / "MiAssistantTool" / "miasst")

# When True, ADB commands are suppressed so MiAssistantTool can own the USB bus.
_usb_locked = False

# Cached device info from last MiAssistantTool read
_cached_device_info: dict = {}


@bp.route("/api/miassistant/sideload", methods=["POST"])
def api_miassistant_sideload():
    """Flash a stock ROM ZIP to a Xiaomi device via MiAssistantTool.

    Uses the open-source MiAssistantTool which implements Xiaomi's
    proprietary MIAssistant protocol — works on locked bootloaders.

    Expected JSON body::

        {
            "zip_path": "/path/to/miui_RENOIR_..._M2101K9G.zip",
            "codename": "renoir"
        }
    """
    if not Path(_MIASST_BIN).is_file():
        return jsonify({"error": "MiAssistantTool not installed"}), 503

    zip_path = request.json.get("zip_path", "")
    codename = request.json.get("codename", "unknown")

    if not zip_path or not Path(zip_path).is_file():
        return jsonify({"error": "ROM ZIP not found", "zip_path": zip_path}), 400

    def _run(task: Task):
        import re

        task.emit(f"Xiaomi MIAssistant flash — codename: {codename}")
        task.emit(f"ROM ZIP: {zip_path}")
        task.emit("Tool: MiAssistantTool (open-source)")
        task.emit("")

        # MiAssistantTool uses libusb directly — ADB must release the device
        # and polling must be suppressed to prevent ADB from reclaiming USB
        import web.routes.miassistant as _self

        _self._usb_locked = True
        task.emit("Releasing USB interface from ADB...", "info")
        subprocess.run(["adb", "kill-server"], capture_output=True, timeout=5)
        import time as _time

        _time.sleep(2)  # give USB time to release

        # Verify firmware integrity
        task.emit("Verifying ROM ZIP integrity...", "info")
        vr = verify(zip_path)
        h = vr["sha256"]
        task.emit(f"SHA256: {h}")
        if vr["known"]:
            task.emit("Verified: matches a known registry entry.", "success")
        else:
            task.emit("Warning: ROM not in registry. Proceeding with caution.", "warn")
        task.emit("")

        # Read device info first
        task.emit("Reading device info...", "info")
        info_proc = subprocess.run(
            [_MIASST_BIN, "1"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if info_proc.stdout.strip():
            for line in info_proc.stdout.strip().splitlines():
                task.emit(line)
        task.emit("")

        # Flash using MiAssistantTool option 3
        # The tool reads the ZIP path from stdin interactively
        task.emit("Starting MIAssistant flash...", "info")
        task.emit(
            "Do NOT unplug the USB cable or touch the device during this process.",
            "warn",
        )
        task.emit("")

        proc = subprocess.Popen(
            [_MIASST_BIN, "3"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        # Send the ZIP path via stdin
        proc.stdin.write((zip_path + "\n").encode())
        proc.stdin.flush()
        proc.stdin.close()

        # Read output byte-by-byte to handle \r-based progress
        full_output = ""
        current_line = ""
        last_pct = -1

        while True:
            if task.cancelled:
                proc.terminate()
                return

            chunk = proc.stdout.read(1)
            if not chunk:
                if proc.poll() is not None:
                    break
                continue

            ch = chunk.decode("utf-8", errors="replace")

            if ch == "\r":
                # Carriage return — parse progress from current line
                pct_match = re.search(r"(\d+)/100%", current_line)
                if pct_match:
                    pct = int(pct_match.group(1))
                    if pct != last_pct and (pct % 5 == 0 or pct >= 95 or pct == 1):
                        task.emit(f"Flash progress: {pct}%")
                        last_pct = pct
                current_line = ""
            elif ch == "\n":
                full_output += current_line + "\n"
                stripped = current_line.strip()
                if stripped and "Enter .zip" not in stripped:
                    # Don't re-emit progress lines
                    if "Flashing in progress" not in stripped:
                        task.emit(stripped)
                current_line = ""
            else:
                current_line += ch

        # Flush remaining
        if current_line.strip():
            full_output += current_line
            task.emit(current_line.strip())

        rc = proc.wait()
        full_lower = full_output.lower()

        if rc == 0 or "success" in full_lower or "complete" in full_lower:
            task.emit("")
            task.emit("Stock firmware restored successfully!", "success")
            task.emit(
                "The device will now verify and install the ROM. "
                "This may take several minutes — do not unplug the device.",
                "info",
            )
            task.emit(
                "The device will reboot automatically when installation finishes. First boot may take 5-10 minutes.",
                "info",
            )
            register(
                zip_path,
                flash_method="miassistant-tool",
                component=f"stock-{codename}",
                sha256=h,
            )

            # Pin to IPFS
            if ipfs_available():
                task.emit("")
                task.emit("Pinning ROM to IPFS for future use...", "info")
                key = f"{codename}/{Path(zip_path).name}"
                cid = ipfs_pin_and_index(
                    zip_path,
                    key=key,
                    codename=codename,
                    rom_name=Path(zip_path).stem,
                    version="stock",
                    task=task,
                )
                if cid:
                    task.emit(f"IPFS CID: {cid}", "success")
                else:
                    task.emit("IPFS pin failed — ROM is still usable locally.", "warn")

            _self._usb_locked = False
            subprocess.run(["adb", "start-server"], capture_output=True, timeout=5)
            task.done(True)
        else:
            task.emit("")
            task.emit("Flash failed.", "error")
            task.emit("")
            task.emit("To retry:", "info")
            task.emit(
                '  1. Re-enter MIUI Recovery and select "Connect with MIAssistant"',
                "info",
            )
            task.emit("  2. Click the device again to retry", "info")
            _self._usb_locked = False
            subprocess.run(["adb", "start-server"], capture_output=True, timeout=5)
            task.done(False)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@bp.route("/api/miassistant/info", methods=["GET"])
def api_miassistant_info():
    """Read device info via MiAssistantTool.

    Returns parsed device info including detected region and compatible ROM code.
    """
    if not Path(_MIASST_BIN).is_file():
        return jsonify({"error": "MiAssistantTool not installed"}), 503
    import web.routes.miassistant as _self

    try:
        _self._usb_locked = True
        subprocess.run(["adb", "kill-server"], capture_output=True, timeout=5)
        time.sleep(1)
        result = subprocess.run(
            [_MIASST_BIN, "1"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        _self._usb_locked = False
        subprocess.run(["adb", "start-server"], capture_output=True, timeout=5)

        output = result.stdout.strip()
        info = parse_device_info(output)
        _self._cached_device_info = info

        device_str = info.get("Device", "")
        version_str = info.get("Version", "")
        region_code, region_label = detect_region(device_str, version_str)
        rom_code = REGION_ROM_CODES.get(region_code, "MIXM")

        return jsonify(
            {
                "output": output,
                "rc": result.returncode,
                "parsed": info,
                "region_code": region_code,
                "region_label": region_label,
                "rom_code": rom_code,
                "compatible_pattern": f"*{rom_code}*",
            }
        )
    except Exception as e:
        _self._usb_locked = False
        subprocess.run(["adb", "start-server"], capture_output=True, timeout=5)
        return jsonify({"error": str(e)}), 500


@bp.route("/api/miassistant/roms", methods=["GET"])
def api_miassistant_roms():
    """List available recovery ROMs in the roms directory.

    Query param: ?region=MI (optional, filters to matching region code)
    """
    import re as _re

    region_filter = request.args.get("region", "")

    roms_dir = Path(__file__).resolve().parent.parent.parent / "roms"
    roms = []
    if roms_dir.exists():
        for f in sorted(roms_dir.glob("miui_*.zip"), reverse=True):
            version = ""
            m = _re.search(r"_(V\d+\.\d+\.\d+\.\d+\.[A-Z]+)_", f.name)
            if m:
                version = m.group(1)

            # Detect ROM region from filename
            rom_region = ""
            rom_region_label = ""
            for code, rom_code in REGION_ROM_CODES.items():
                if rom_code in f.name:
                    rom_region = code
                    for _, (c, label) in XIAOMI_REGIONS.items():
                        if c == code:
                            rom_region_label = label
                            break
                    break

            # When filtering, show matching region first but include all
            compatible = not region_filter or rom_region == region_filter

            roms.append(
                {
                    "path": str(f),
                    "name": f.name,
                    "version": version,
                    "size_mb": round(f.stat().st_size / (1024 * 1024), 1),
                    "region": rom_region,
                    "region_label": rom_region_label,
                    "compatible": compatible,
                }
            )

    # Sort: compatible first, then by version descending
    roms.sort(key=lambda r: (not r["compatible"], r["name"]), reverse=False)
    return jsonify({"roms": roms})


def _check_xiaomi_usb() -> bool:
    """Return True if a Xiaomi USB device (vendor 2717) is detected."""
    try:
        result = subprocess.run(["lsusb"], capture_output=True, text=True, timeout=5)
        return "2717" in result.stdout.lower()
    except Exception:
        return False
