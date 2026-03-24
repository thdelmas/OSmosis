"""E-bike motor controller flashing, detection, and preset routes."""

import hashlib
from pathlib import Path

from flask import Blueprint, jsonify, request

from web.core import Task, cmd_exists, start_task
from web.registry import register

bp = Blueprint("ebike", __name__)

# Path to the e-bike preset config file
_EBIKES_CFG = Path(__file__).resolve().parent.parent.parent / "ebikes.cfg"

# STM8 flash base address (shared with scooter ST-Link flashing)
_STM8_FLASH_BASE = "0x08000000"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def parse_ebikes_cfg() -> list[dict]:
    """Parse ebikes.cfg and return list of e-bike controller preset dicts.

    Fields per line (pipe-delimited):
        id|label|brand|controller|flash_method|fw_project|fw_url|support_status|notes
    """
    ebikes = []
    if not _EBIKES_CFG.exists():
        return ebikes
    for line in _EBIKES_CFG.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|")
        if len(parts) < 8:
            continue
        ebikes.append(
            {
                "id": parts[0],
                "label": parts[1],
                "brand": parts[2],
                "controller": parts[3],
                "flash_method": parts[4],
                "fw_project": parts[5],
                "fw_url": parts[6],
                "support_status": parts[7],
                "notes": parts[8] if len(parts) > 8 else "",
            }
        )
    return ebikes


def _stflash_available() -> bool:
    """Return True if st-flash is available on the system."""
    return cmd_exists("st-flash")


def _stinfo_available() -> bool:
    """Return True if st-info (part of stlink tools) is available."""
    return cmd_exists("st-info")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@bp.route("/api/ebikes")
def api_ebikes():
    """Return all e-bike controller presets from ebikes.cfg."""
    return jsonify(parse_ebikes_cfg())


@bp.route("/api/ebike/detect")
def api_ebike_detect():
    """Detect an ST-Link-connected controller. Streams via background Task."""
    if not _stinfo_available():
        return jsonify({"error": "stlink tools not installed (apt install stlink-tools)"}), 500

    def _run(task: Task):
        task.emit("Probing ST-Link for connected controller...", "info")
        rc = task.run_shell(["st-info", "--probe"])
        if rc == 0:
            task.emit("ST-Link probe complete. Check output above for chip info.", "success")
        else:
            task.emit("No ST-Link device found. Check USB connection.", "error")
        task.done(rc == 0)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@bp.route("/api/ebike/flash", methods=["POST"])
def api_ebike_flash():
    """Flash firmware to an e-bike controller via ST-Link.

    Expected JSON body:
        {
            "fw_path":     "<absolute path to firmware .bin/.hex file>",
            "controller":  "<controller id from ebikes.cfg>",
            "flash_addr":  "<optional flash address, defaults to 0x08000000>"
        }
    """
    body = request.json or {}
    fw_path = body.get("fw_path", "").strip()
    controller_id = body.get("controller", "").strip()
    flash_addr = body.get("flash_addr", _STM8_FLASH_BASE).strip()

    if not fw_path or not Path(fw_path).is_file():
        return jsonify({"error": "Firmware file not found"}), 400
    if not _stflash_available():
        return jsonify({"error": "st-flash not installed (apt install stlink-tools)"}), 500

    # Look up preset for metadata (optional — flash works without it)
    preset = None
    if controller_id:
        preset = next((e for e in parse_ebikes_cfg() if e["id"] == controller_id), None)

    def _run(task: Task):
        fw = Path(fw_path)
        label = preset["label"] if preset else controller_id or "unknown"
        task.emit(f"Controller: {label}", "info")
        task.emit(f"Firmware file: {fw_path}", "info")
        task.emit(f"Flash address: {flash_addr}", "info")
        task.emit(f"File size: {fw.stat().st_size} bytes", "info")

        h = hashlib.sha256(fw.read_bytes()).hexdigest()
        task.emit(f"SHA256: {h}")

        # Probe first to confirm ST-Link connection
        task.emit("Probing ST-Link connection...", "info")
        rc = task.run_shell(["st-info", "--probe"])
        if rc != 0:
            task.emit("No ST-Link device detected. Check USB connection and wiring.", "error")
            task.done(False)
            return

        # Flash
        task.emit("Flashing firmware via st-flash...", "info")
        rc = task.run_shell(["st-flash", "--reset", "write", fw_path, flash_addr])
        if rc != 0:
            task.emit("Flash failed. Check wiring, chip compatibility, and firmware file.", "error")
            task.done(False)
            return

        task.emit("Firmware flash complete!", "success")
        register(
            fw_path,
            device_id=controller_id or "ebike-unknown",
            device_label=label,
            component="controller",
            flash_method="stlink",
            sha256=h,
        )
        task.done(True)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@bp.route("/api/ebike/backup", methods=["POST"])
def api_ebike_backup():
    """Read current firmware from controller via ST-Link (backup before flash).

    Expected JSON body:
        {
            "controller":  "<controller id from ebikes.cfg>",
            "flash_addr":  "<optional start address>",
            "size":        "<optional read size in hex, e.g. 0x10000>"
        }
    """
    body = request.json or {}
    controller_id = body.get("controller", "").strip()
    flash_addr = body.get("flash_addr", _STM8_FLASH_BASE).strip()
    size = body.get("size", "0x10000").strip()

    if not _stflash_available():
        return jsonify({"error": "st-flash not installed (apt install stlink-tools)"}), 500

    preset = None
    if controller_id:
        preset = next((e for e in parse_ebikes_cfg() if e["id"] == controller_id), None)

    def _run(task: Task):
        label = preset["label"] if preset else controller_id or "unknown"
        backup_dir = Path.home() / "Osmosis-backups" / "ebike" / (controller_id or "unknown")
        backup_dir.mkdir(parents=True, exist_ok=True)

        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_file = backup_dir / f"{controller_id or 'ebike'}-{timestamp}.bin"

        task.emit(f"Controller: {label}", "info")
        task.emit(f"Reading {size} bytes from {flash_addr}...", "info")
        task.emit(f"Backup destination: {backup_file}", "info")

        rc = task.run_shell(["st-flash", "read", str(backup_file), flash_addr, size])
        if rc != 0:
            task.emit("Backup read failed. Check ST-Link connection.", "error")
            task.done(False)
            return

        if backup_file.exists():
            h = hashlib.sha256(backup_file.read_bytes()).hexdigest()
            task.emit(f"Backup SHA256: {h}")
            task.emit(f"Backup saved: {backup_file} ({backup_file.stat().st_size} bytes)", "success")
        task.done(True)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


# ---------------------------------------------------------------------------
# Parameter configuration presets
# ---------------------------------------------------------------------------

# TSDZ2 Open Source Firmware parameters (register map)
_TSDZ2_PARAMS = {
    "motor_type": {
        "label": "Motor type",
        "type": "select",
        "options": [
            {"value": 0, "label": "48V motor"},
            {"value": 1, "label": "36V motor"},
        ],
        "default": 0,
        "register": 0x00,
    },
    "max_current": {
        "label": "Motor current limit (A)",
        "type": "range",
        "min": 1,
        "max": 18,
        "default": 16,
        "register": 0x01,
    },
    "battery_low_voltage": {
        "label": "Battery low cutoff (V x10)",
        "type": "number",
        "min": 280,
        "max": 540,
        "default": 390,
        "register": 0x02,
    },
    "wheel_perimeter": {
        "label": "Wheel perimeter (mm)",
        "type": "number",
        "min": 750,
        "max": 2500,
        "default": 2070,
        "register": 0x03,
    },
    "assist_levels": {
        "label": "Number of assist levels",
        "type": "range",
        "min": 1,
        "max": 9,
        "default": 5,
        "register": 0x04,
    },
    "speed_limit": {
        "label": "Speed limit (km/h)",
        "type": "range",
        "min": 15,
        "max": 99,
        "default": 25,
        "register": 0x05,
    },
    "street_mode": {
        "label": "Street mode (speed-limited)",
        "type": "toggle",
        "default": True,
        "register": 0x06,
    },
    "startup_boost": {
        "label": "Startup motor boost",
        "type": "toggle",
        "default": True,
        "register": 0x07,
    },
    "torque_sensor_calibration": {
        "label": "Torque sensor calibration",
        "type": "range",
        "min": 0,
        "max": 255,
        "default": 100,
        "register": 0x08,
    },
    "regen_braking": {
        "label": "Regenerative braking level",
        "type": "range",
        "min": 0,
        "max": 8,
        "default": 0,
        "register": 0x09,
        "desc": "0 = off, 1-8 = intensity",
    },
}

# Bafang BBS02/BBSHD parameters (bbs-fw)
_BAFANG_PARAMS = {
    "max_current": {
        "label": "Max battery current (A)",
        "type": "range",
        "min": 1,
        "max": 30,
        "default": 15,
        "register": 0x00,
    },
    "low_battery_cutoff": {
        "label": "Low voltage cutoff (V)",
        "type": "number",
        "min": 36,
        "max": 60,
        "default": 42,
        "register": 0x01,
    },
    "pedal_assist_levels": {
        "label": "PAS levels",
        "type": "range",
        "min": 3,
        "max": 9,
        "default": 5,
        "register": 0x02,
    },
    "speed_limit": {
        "label": "Speed limit (km/h)",
        "type": "range",
        "min": 15,
        "max": 99,
        "default": 25,
        "register": 0x03,
    },
    "wheel_diameter": {
        "label": "Wheel diameter (inches)",
        "type": "select",
        "options": [
            {"value": 16, "label": '16"'},
            {"value": 20, "label": '20"'},
            {"value": 24, "label": '24"'},
            {"value": 26, "label": '26"'},
            {"value": 27, "label": '27.5"'},
            {"value": 29, "label": '29"'},
        ],
        "default": 26,
        "register": 0x04,
    },
    "throttle_enabled": {
        "label": "Throttle enabled",
        "type": "toggle",
        "default": False,
        "register": 0x05,
    },
}

_PARAM_PRESETS = {
    "tsdz2": {
        "name": "TSDZ2 Open Source Firmware",
        "params": _TSDZ2_PARAMS,
    },
    "bafang": {
        "name": "Bafang BBS02/BBSHD (bbs-fw)",
        "params": _BAFANG_PARAMS,
    },
}


@bp.route("/api/ebike/params/<controller_type>")
def api_ebike_params(controller_type):
    """Return parameter configuration schema for a controller type.

    Supported types: tsdz2, bafang
    """
    preset = _PARAM_PRESETS.get(controller_type)
    if not preset:
        return (
            jsonify(
                {
                    "error": f"Unknown controller type: {controller_type}",
                    "available": list(_PARAM_PRESETS.keys()),
                }
            ),
            404,
        )
    return jsonify(preset)


@bp.route("/api/ebike/params/<controller_type>/apply", methods=["POST"])
def api_ebike_params_apply(controller_type):
    """Apply parameter configuration to a connected controller via ST-Link.

    JSON body: { "params": { "speed_limit": 32, "max_current": 14, ... } }

    Writes parameter values to controller EEPROM registers via st-flash.
    """
    preset = _PARAM_PRESETS.get(controller_type)
    if not preset:
        return jsonify({"error": f"Unknown controller type: {controller_type}"}), 404

    body = request.json or {}
    params = body.get("params", {})
    if not params:
        return jsonify({"error": "No parameters provided"}), 400

    if not _stflash_available():
        return jsonify({"error": "st-flash not installed"}), 500

    schema = preset["params"]

    def _run(task: Task):
        task.emit(f"Applying {preset['name']} parameters...", "info")

        for key, value in params.items():
            if key not in schema:
                task.emit(f"Unknown parameter: {key} — skipping", "warn")
                continue

            spec = schema[key]
            task.emit(f"  {spec['label']}: {value}", "info")

        # Build binary config block
        config_bytes = bytearray(256)
        for key, value in params.items():
            if key not in schema:
                continue
            spec = schema[key]
            reg = spec["register"]
            if spec["type"] == "toggle":
                config_bytes[reg] = 1 if value else 0
            elif isinstance(value, bool):
                config_bytes[reg] = 1 if value else 0
            else:
                val = int(value)
                if val < 256:
                    config_bytes[reg] = val
                else:
                    # 16-bit value, little-endian
                    config_bytes[reg] = val & 0xFF
                    config_bytes[reg + 1] = (val >> 8) & 0xFF

        # Write config to temp file
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".bin", prefix="ebike_config_", delete=False) as f:
            f.write(config_bytes)
            config_path = f.name

        # Write to EEPROM area (typically 0x08080000 for STM8 EEPROM)
        eeprom_addr = "0x08080000"
        task.emit(f"Writing config to EEPROM at {eeprom_addr}...", "info")
        rc = task.run_shell(["st-flash", "write", config_path, eeprom_addr])

        Path(config_path).unlink(missing_ok=True)

        if rc == 0:
            task.emit("Parameters applied successfully!", "success")
        else:
            task.emit("Failed to write parameters. Check ST-Link connection.", "error")

        task.done(rc == 0)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@bp.route("/api/ebike/tools")
def api_ebike_tools():
    """Check which e-bike-related tools are installed.

    Returns:
        {
            "stlink":    bool,  # stlink CLI (st-info)
            "stflash":   bool,  # st-flash CLI
            "vesc_tool": bool,  # VESC Tool (optional)
        }
    """
    return jsonify(
        {
            "stlink": _stinfo_available(),
            "stflash": _stflash_available(),
            "vesc_tool": cmd_exists("vesc_tool"),
        }
    )
