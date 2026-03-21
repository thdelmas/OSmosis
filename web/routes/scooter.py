"""Scooter flashing, BLE scanning, and preset routes."""

import asyncio
from pathlib import Path

from flask import Blueprint, jsonify, request

from web.core import Task, cmd_exists, start_task
from web.registry import register, verify

bp = Blueprint("scooter", __name__)

# Path to the scooter preset config file
_SCOOTERS_CFG = Path(__file__).resolve().parent.parent.parent / "scooters.cfg"

# Common BLE name prefixes used by supported scooters
_SCOOTER_PREFIXES = ("MIScooter", "Ninebot", "NB-", "Mi Electric")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def parse_scooters_cfg() -> list[dict]:
    """Parse scooters.cfg and return list of scooter preset dicts.

    Fields per line (pipe-delimited):
        id|label|brand|protocol|flash_method|cfw_url|shfw_supported|notes
    """
    scooters = []
    if not _SCOOTERS_CFG.exists():
        return scooters
    for line in _SCOOTERS_CFG.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|")
        if len(parts) < 7:
            continue
        scooters.append(
            {
                "id": parts[0],
                "label": parts[1],
                "brand": parts[2],
                "protocol": parts[3],
                "flash_method": parts[4],
                "cfw_url": parts[5],
                "shfw_supported": parts[6],
                "notes": parts[7] if len(parts) > 7 else "",
            }
        )
    return scooters


def _bleak_available() -> bool:
    """Return True if the bleak package is importable."""
    try:
        import importlib

        importlib.import_module("bleak")
        return True
    except ImportError:
        return False


async def _ble_scan(duration: float = 5.0) -> list[dict]:
    """Discover BLE devices whose names match known scooter prefixes."""
    from bleak import BleakScanner

    found = []
    devices = await BleakScanner.discover(timeout=duration, return_adv=True)
    for _addr, (device, adv) in devices.items():
        name = device.name or ""
        if any(name.startswith(prefix) for prefix in _SCOOTER_PREFIXES):
            found.append(
                {
                    "name": name,
                    "address": device.address,
                    "rssi": adv.rssi,
                }
            )
    return found


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@bp.route("/api/scooters")
def api_scooters():
    """Return all scooter presets from scooters.cfg."""
    return jsonify(parse_scooters_cfg())


@bp.route("/api/scooter/scan")
def api_scooter_scan():
    """Scan for nearby BLE scooters. Streams progress via SSE (background Task)."""
    if not _bleak_available():
        return jsonify({"error": "bleak is not installed (pip install bleak)"}), 500

    def _run(task: Task):
        task.emit("Starting BLE scan for nearby scooters...", "info")
        task.emit(f"Scanning for prefixes: {', '.join(_SCOOTER_PREFIXES)}", "info")
        try:
            results = asyncio.run(_ble_scan(duration=5.0))
        except Exception as e:
            task.emit(f"BLE scan error: {e}", "error")
            task.done(False)
            return

        if results:
            task.emit(f"Found {len(results)} scooter(s):", "success")
            for dev in results:
                task.emit(f"  {dev['name']} — {dev['address']} (RSSI {dev['rssi']} dBm)")
        else:
            task.emit("No scooters found nearby.", "warn")

        import json

        task.emit(json.dumps({"scan_results": results}), "data")
        task.done(True)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@bp.route("/api/scooter/info/<address>")
def api_scooter_info(address: str):
    """Connect to a scooter by BLE address and read device info."""
    if not _bleak_available():
        return jsonify({"error": "bleak is not installed (pip install bleak)"}), 500

    try:
        from web.scooter_proto import get_scooter_info
    except ImportError:
        return jsonify({"error": "web.scooter_proto module not found"}), 500

    try:
        info = asyncio.run(get_scooter_info(address))
        return jsonify(info)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/scooter/flash", methods=["POST"])
def api_scooter_flash():
    """Flash firmware to a scooter over BLE (and optionally STLink).

    Expected JSON body:
        {
            "address":   "<BLE address>",
            "fw_path":   "<absolute path to firmware file>",
            "component": "esc" | "ble" | "bms" | ...
        }
    """
    if not _bleak_available():
        return jsonify({"error": "bleak is not installed (pip install bleak)"}), 500

    body = request.json or {}
    address = body.get("address", "").strip()
    fw_path = body.get("fw_path", "").strip()
    component = body.get("component", "esc").strip()

    if not address:
        return jsonify({"error": "BLE address is required"}), 400
    if not fw_path or not Path(fw_path).is_file():
        return jsonify({"error": "Firmware file not found"}), 400

    def _run(task: Task):
        task.emit(f"Target device: {address}", "info")
        task.emit(f"Firmware file: {fw_path}", "info")
        task.emit(f"Component: {component}", "info")

        task.emit("Verifying firmware against registry...", "info")
        vr = verify(fw_path)
        h = vr["sha256"]
        task.emit(f"SHA256: {h}")
        if vr["known"]:
            task.emit("Verified: matches a known registry entry.", "success")
        else:
            task.emit("Warning: firmware not in registry. Proceeding.", "warn")
        task.emit("")

        try:
            from web.scooter_proto import flash_firmware

            task.emit(f"Connecting to scooter {address}...", "info")
            asyncio.run(flash_firmware(address, fw_path, component, task))
        except ImportError:
            task.emit("web.scooter_proto not available — falling back to st-flash for ESC.", "warn")
            if component == "esc":
                if not cmd_exists("st-flash"):
                    task.emit("st-flash not found. Install stlink tools.", "error")
                    task.done(False)
                    return
                task.emit("Flashing ESC via st-flash...", "info")
                rc = task.run_shell(["st-flash", "--reset", "write", fw_path, "0x08000000"])
                if rc == 0:
                    task.emit("ESC flash complete!", "success")
                task.done(rc == 0)
                return
            else:
                task.emit(f"Cannot flash component '{component}' without scooter_proto.", "error")
                task.done(False)
                return
        except Exception as e:
            task.emit(f"Flash error: {e}", "error")
            task.done(False)
            return

        task.emit(f"{component.upper()} flash complete!", "success")
        register(
            fw_path,
            device_id=address,
            component=component,
            flash_method="ble" if "st-flash" not in str(fw_path) else "stlink",
            sha256=h,
        )
        task.done(True)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@bp.route("/api/scooter/flash-cfw", methods=["POST"])
def api_scooter_flash_cfw():
    """Download and flash custom firmware (CFW) for a scooter preset.

    Expected JSON body:
        {
            "address":    "<BLE address>",
            "scooter_id": "<preset id from scooters.cfg>",
            "options":    { ... }   (optional, passed through to scooter_proto)
        }
    """
    if not _bleak_available():
        return jsonify({"error": "bleak is not installed (pip install bleak)"}), 500

    body = request.json or {}
    address = body.get("address", "").strip()
    scooter_id = body.get("scooter_id", "").strip()
    options = body.get("options", {})

    if not address:
        return jsonify({"error": "BLE address is required"}), 400
    if not scooter_id:
        return jsonify({"error": "scooter_id is required"}), 400

    preset = next((s for s in parse_scooters_cfg() if s["id"] == scooter_id), None)
    if not preset:
        return jsonify({"error": f"Scooter preset '{scooter_id}' not found"}), 404

    cfw_url = preset.get("cfw_url", "").strip()
    if not cfw_url:
        return jsonify({"error": f"No CFW URL configured for preset '{scooter_id}'"}), 400

    shfw_supported = preset.get("shfw_supported", "no").strip().lower()
    if shfw_supported not in ("yes",):
        return jsonify({"error": f"CFW not supported for '{preset['label']}' (shfw_supported={shfw_supported})"}), 400

    def _run(task: Task):
        task.emit(f"Preset: {preset['label']} ({preset['id']})", "info")
        task.emit(f"Target device: {address}", "info")
        task.emit(f"CFW source: {cfw_url}", "info")
        if options:
            task.emit(f"Options: {options}", "info")

        # Download CFW
        download_dir = Path.home() / "Osmosis-downloads" / "cfw" / scooter_id
        download_dir.mkdir(parents=True, exist_ok=True)
        task.emit(f"Download directory: {download_dir}", "info")

        url_clean = cfw_url.rstrip("/")
        filename = Path(url_clean).name or f"{scooter_id}-cfw.bin"
        dest = download_dir / filename

        task.emit(f"Downloading CFW from {cfw_url}...", "info")
        rc = task.run_shell(["wget", "--progress=dot:giga", "-O", str(dest), cfw_url])
        if rc != 0:
            task.emit("Failed to download CFW.", "error")
            if dest.exists():
                dest.unlink(missing_ok=True)
            task.done(False)
            return

        import hashlib

        h = hashlib.sha256(dest.read_bytes()).hexdigest()
        task.emit(f"SHA256: {h}")
        task.emit(f"CFW downloaded: {dest}", "success")

        # Flash CFW via scooter_proto
        try:
            from web.scooter_proto import flash_cfw

            task.emit(f"Connecting to scooter {address}...", "info")
            asyncio.run(flash_cfw(address, str(dest), preset, options, task))
        except ImportError:
            task.emit("web.scooter_proto not available — falling back to st-flash.", "warn")
            if preset.get("flash_method", "") in ("ble+stlink", "stlink"):
                if not cmd_exists("st-flash"):
                    task.emit("st-flash not found. Install stlink tools.", "error")
                    task.done(False)
                    return
                task.emit("Flashing ESC via st-flash...", "info")
                rc = task.run_shell(["st-flash", "--reset", "write", str(dest), "0x08000000"])
                if rc == 0:
                    task.emit("CFW flash complete!", "success")
                task.done(rc == 0)
                return
            else:
                task.emit("Cannot flash CFW without scooter_proto for this flash method.", "error")
                task.done(False)
                return
        except Exception as e:
            task.emit(f"CFW flash error: {e}", "error")
            task.done(False)
            return

        task.emit("CFW flash complete!", "success")
        register(
            dest,
            device_id=address,
            device_label=preset["label"],
            component="cfw",
            source_url=cfw_url,
            flash_method=preset.get("flash_method", "ble"),
            sha256=h,
        )
        task.done(True)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@bp.route("/api/scooter/tools")
def api_scooter_tools():
    """Check which scooter-related tools are installed.

    Returns:
        {
            "bleak":   bool,   # Python BLE library
            "stlink":  bool,   # stlink CLI (st-info / st-util)
            "stflash": bool,   # st-flash CLI
        }
    """
    return jsonify(
        {
            "bleak": _bleak_available(),
            "stlink": cmd_exists("st-info") or cmd_exists("stlink"),
            "stflash": cmd_exists("st-flash"),
        }
    )


# ---------------------------------------------------------------------------
# Live Dashboard
# ---------------------------------------------------------------------------


@bp.route("/api/scooter/telemetry/<address>")
def api_scooter_telemetry(address: str):
    """Read real-time telemetry from a connected scooter."""
    if not _bleak_available():
        return jsonify({"error": "bleak is not installed"}), 500

    address = address.strip()
    if not address:
        return jsonify({"error": "BLE address is required"}), 400

    try:
        from web.scooter_proto import read_telemetry

        data = asyncio.run(read_telemetry(address))
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/scooter/telemetry-stream/<address>")
def api_scooter_telemetry_stream(address: str):
    """Stream telemetry readings as Server-Sent Events (SSE).

    The client connects once; the server reads telemetry every ~2 seconds
    and pushes JSON payloads.

    Usage: const es = new EventSource("/api/scooter/telemetry-stream/<addr>");
           es.onmessage = (e) => { const data = JSON.parse(e.data); ... };
    """
    if not _bleak_available():
        return jsonify({"error": "bleak is not installed"}), 500

    import time

    from flask import Response

    address = address.strip()

    def generate():
        import json

        from web.scooter_proto import read_telemetry

        while True:
            try:
                data = asyncio.run(read_telemetry(address))
                yield f"data: {json.dumps(data)}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                break
            time.sleep(2)

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@bp.route("/api/scooter/register/write", methods=["POST"])
def api_scooter_register_write():
    """Write a value to a scooter register.

    JSON body: {"address": "XX:XX:...", "register": 0x75, "value": [0x01]}
    """
    if not _bleak_available():
        return jsonify({"error": "bleak is not installed"}), 500

    body = request.json or {}
    address = body.get("address", "").strip()
    reg = body.get("register", 0)
    value = body.get("value", [])

    if not address:
        return jsonify({"error": "BLE address is required"}), 400
    if not isinstance(reg, int) or not value:
        return jsonify({"error": "register (int) and value (byte array) are required"}), 400

    try:
        from web.scooter_proto import write_scooter_register

        ok = asyncio.run(write_scooter_register(address, reg, bytes(value)))
        if ok:
            return jsonify({"ok": True})
        return jsonify({"error": "Write failed"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Common register shortcuts for the dashboard
_DASHBOARD_REGISTERS = {
    "speed_mode": {"register": 0x75, "desc": "Speed mode (0=eco, 1=drive, 2=sport)"},
    "lock": {"register": 0x70, "desc": "Lock (0=unlocked, 1=locked)"},
    "tail_light": {"register": 0x73, "desc": "Tail light (0=off, 1=on)"},
}


@bp.route("/api/scooter/dashboard/actions")
def api_scooter_dashboard_actions():
    """List available dashboard actions (writable registers)."""
    return jsonify(_DASHBOARD_REGISTERS)
