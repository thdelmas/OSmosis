"""Safety routes: pre-flash checklist, firmware registry, recovery guides."""

from pathlib import Path

from flask import Blueprint, jsonify, request

from web.core import Task, start_task
from web.registry import all_entries, lookup, lookup_device, register, sha256_file, verify
from web.safety import RECOVERY_GUIDES, preflight_check_phone, preflight_check_scooter

bp = Blueprint("safety", __name__)


# ---------------------------------------------------------------------------
# Pre-flash checklist
# ---------------------------------------------------------------------------


@bp.route("/api/preflight/phone", methods=["POST"])
def api_preflight_phone():
    """Run pre-flash checklist for phone/tablet operations."""
    body = request.json or {}
    result = preflight_check_phone(
        fw_path=body.get("fw_path", ""),
        recovery_img=body.get("recovery_img", ""),
    )
    return jsonify(result)


@bp.route("/api/preflight/scooter", methods=["POST"])
def api_preflight_scooter():
    """Run pre-flash checklist for scooter operations."""
    body = request.json or {}
    result = preflight_check_scooter(
        address=body.get("address", ""),
        fw_path=body.get("fw_path", ""),
    )
    return jsonify(result)


# ---------------------------------------------------------------------------
# Firmware registry
# ---------------------------------------------------------------------------


@bp.route("/api/registry")
def api_registry():
    """List all firmware registry entries (newest first)."""
    return jsonify(all_entries())


@bp.route("/api/registry/device/<device_id>")
def api_registry_device(device_id: str):
    """List registry entries for a specific device."""
    return jsonify(lookup_device(device_id))


@bp.route("/api/registry/verify", methods=["POST"])
def api_registry_verify():
    """Verify a firmware file against the registry.

    JSON body: {"fw_path": "/path/to/firmware.bin"}
    """
    fw_path = (request.json or {}).get("fw_path", "")
    if not fw_path or not Path(fw_path).is_file():
        return jsonify({"error": "Firmware file not found"}), 400
    return jsonify(verify(fw_path))


@bp.route("/api/registry/lookup/<sha256>")
def api_registry_lookup(sha256: str):
    """Look up a SHA256 hash in the registry."""
    return jsonify(lookup(sha256))


@bp.route("/api/registry/add", methods=["POST"])
def api_registry_add():
    """Manually register a firmware file.

    JSON body: {
        "fw_path": "/path/to/file",
        "device_id": "...",
        "device_label": "...",
        "component": "...",
        "version": "...",
        "source_url": "...",
        "flash_method": "..."
    }
    """
    body = request.json or {}
    fw_path = body.get("fw_path", "")
    if not fw_path or not Path(fw_path).is_file():
        return jsonify({"error": "Firmware file not found"}), 400
    entry = register(
        fw_path,
        device_id=body.get("device_id", ""),
        device_label=body.get("device_label", ""),
        component=body.get("component", ""),
        version=body.get("version", ""),
        source_url=body.get("source_url", ""),
        flash_method=body.get("flash_method", ""),
    )
    return jsonify(entry), 201


# ---------------------------------------------------------------------------
# Recovery guides
# ---------------------------------------------------------------------------


@bp.route("/api/recovery")
def api_recovery_list():
    """List available recovery guides."""
    guides = []
    for key, guide in RECOVERY_GUIDES.items():
        guides.append({
            "id": key,
            "title": guide["title"],
            "device_type": guide["device_type"],
            "step_count": len(guide["steps"]),
        })
    return jsonify(guides)


@bp.route("/api/recovery/<guide_id>")
def api_recovery_guide(guide_id: str):
    """Get a specific recovery guide."""
    guide = RECOVERY_GUIDES.get(guide_id)
    if not guide:
        return jsonify({"error": f"Recovery guide '{guide_id}' not found"}), 404
    return jsonify(guide)


# ---------------------------------------------------------------------------
# Scooter firmware backup
# ---------------------------------------------------------------------------


@bp.route("/api/scooter/backup", methods=["POST"])
def api_scooter_backup():
    """Read and backup current scooter firmware before flashing.

    JSON body: {"address": "<BLE address>"}
    """
    body = request.json or {}
    address = body.get("address", "").strip()
    if not address:
        return jsonify({"error": "BLE address is required"}), 400

    try:
        import importlib
        importlib.import_module("bleak")
    except ImportError:
        return jsonify({"error": "bleak is not installed (pip install bleak)"}), 500

    def _run(task: Task):
        import asyncio
        import json
        from datetime import datetime

        backup_dir = Path.home() / ".osmosis" / "scooter-backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        task.emit(f"Connecting to scooter {address}...", "info")

        # Read scooter info (firmware versions, serial, etc.)
        try:
            from web.scooter_proto import get_scooter_info
            info = asyncio.run(get_scooter_info(address))
        except Exception as e:
            task.emit(f"Could not read scooter info: {e}", "error")
            task.done(False)
            return

        task.emit(f"Scooter: {info.get('model', 'unknown')}", "info")
        task.emit(f"Serial: {info.get('serial', 'unknown')}", "info")

        for key in ("drv_version", "ble_version", "bms_version"):
            if key in info:
                task.emit(f"  {key}: {info[key]}", "info")

        # Save info as backup metadata
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        serial = info.get("serial", "unknown").replace("/", "_")
        backup_name = f"{serial}_{timestamp}"
        backup_path = backup_dir / backup_name
        backup_path.mkdir(parents=True, exist_ok=True)

        info_file = backup_path / "scooter-info.json"
        info_file.write_text(json.dumps(info, indent=2) + "\n")
        task.emit(f"Scooter info saved to {info_file}", "success")

        # Try to read firmware registers if supported
        try:
            from web.scooter_proto import read_firmware_dump
            task.emit("Attempting to dump current firmware registers...", "info")
            dump = asyncio.run(read_firmware_dump(address))
            if dump:
                dump_file = backup_path / "firmware-dump.bin"
                dump_file.write_bytes(dump)
                h = sha256_file(dump_file)
                task.emit(f"Firmware dump saved ({len(dump)} bytes, SHA256: {h})", "success")

                register(
                    dump_file,
                    device_id=serial,
                    device_label=info.get("model", "scooter"),
                    component="esc",
                    version=info.get("drv_version", ""),
                    flash_method="ble-backup",
                )
            else:
                task.emit("Firmware dump not available for this model (info-only backup).", "warn")
        except ImportError:
            task.emit("Firmware dump not available (read_firmware_dump not implemented).", "warn")
        except Exception as e:
            task.emit(f"Firmware dump failed: {e} (info-only backup).", "warn")

        task.emit(f"Backup saved to {backup_path}", "success")
        task.done(True)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@bp.route("/api/scooter/backups")
def api_scooter_backups():
    """List available scooter backups."""
    backup_dir = Path.home() / ".osmosis" / "scooter-backups"
    if not backup_dir.exists():
        return jsonify([])

    backups = []
    for d in sorted(backup_dir.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        info_file = d / "scooter-info.json"
        info = {}
        if info_file.exists():
            try:
                import json
                info = json.loads(info_file.read_text())
            except Exception:
                pass
        has_dump = (d / "firmware-dump.bin").exists()
        backups.append({
            "name": d.name,
            "path": str(d),
            "model": info.get("model", "unknown"),
            "serial": info.get("serial", "unknown"),
            "drv_version": info.get("drv_version", ""),
            "has_firmware_dump": has_dump,
        })
    return jsonify(backups)
