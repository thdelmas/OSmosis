"""Safety routes: pre-flash checklist, firmware registry, recovery guides."""

from pathlib import Path

from flask import Blueprint, jsonify, request

from web.core import Task, start_task
from web.ipfs_helpers import is_valid_cid
from web.registry import (
    all_entries,
    enriched_entries,
    lookup,
    lookup_device,
    register,
    sha256_file,
    update_ipfs_cid,
    verify,
    version_history,
)
from web.safety import RECOVERY_GUIDES, preflight_check_phone, preflight_check_pixel, preflight_check_scooter

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


@bp.route("/api/preflight/pixel", methods=["POST"])
def api_preflight_pixel():
    """Run pre-flash checklist for Pixel/fastboot operations."""
    body = request.json or {}
    result = preflight_check_pixel(
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


@bp.route("/api/registry/enriched")
def api_registry_enriched():
    """List all registry entries enriched with local-file and IPFS status.

    Each entry includes:
    - file_exists: whether the firmware file is still on disk
    - ipfs_pinned: whether the IPFS CID (if any) is pinned locally
    - ipfs_peers: number of IPFS peers providing this CID (capped at 5)
    """
    from web.ipfs_helpers import ipfs_available, ipfs_find_providers, ipfs_pin_ls

    entries = enriched_entries()
    ipfs_up = ipfs_available()

    for e in entries:
        cid = e.get("ipfs_cid", "")
        if cid and ipfs_up:
            e["ipfs_pinned"] = ipfs_pin_ls(cid)
            providers = ipfs_find_providers(cid, max_providers=5, timeout_secs=5)
            e["ipfs_peers"] = len(providers)
        else:
            e["ipfs_pinned"] = False
            e["ipfs_peers"] = 0

    return jsonify(entries)


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

    # Auto-pin to IPFS if daemon is available and user opted in
    if body.get("ipfs_pin"):
        try:
            from web.ipfs_helpers import ipfs_add, ipfs_available

            if ipfs_available():
                cid = ipfs_add(fw_path)
                if cid:
                    update_ipfs_cid(entry["sha256"], cid)
                    entry["ipfs_cid"] = cid
        except Exception:
            pass

    return jsonify(entry), 201


@bp.route("/api/registry/device/<device_id>/history")
def api_registry_history(device_id: str):
    """Get firmware version history for a device, grouped by component."""
    return jsonify(version_history(device_id))


@bp.route("/api/registry/restore", methods=["POST"])
def api_registry_restore():
    """Restore a firmware version by fetching it from IPFS.

    JSON body: {"sha256": "...", "device_id": "..."}
    Looks up the registry entry, checks for an ipfs_cid, and fetches it.
    """
    from web.ipfs_helpers import ipfs_available, is_valid_cid, verify_fetched_file

    body = request.json or {}
    sha256 = body.get("sha256", "")
    if not sha256:
        return jsonify({"error": "sha256 is required"}), 400

    matches = lookup(sha256)
    if not matches:
        return jsonify({"error": "No registry entry found for this hash"}), 404

    entry = matches[0]
    cid = entry.get("ipfs_cid", "")
    if not cid or not is_valid_cid(cid):
        return jsonify({"error": "No IPFS CID associated with this firmware entry"}), 404

    if not ipfs_available():
        return jsonify({"error": "IPFS daemon not running"}), 503

    def _run(task: Task):
        filename = entry.get("filename", f"firmware-{sha256[:8]}.bin")
        device_id = entry.get("device_id", "unknown")
        dest_dir = Path.home() / "Osmosis-downloads" / device_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = str(dest_dir / filename)

        task.emit(f"Restoring firmware: {filename}")
        task.emit(f"Version: {entry.get('version', 'unknown')}")
        task.emit(f"CID: {cid}")
        task.emit(f"Expected SHA256: {sha256}")
        task.emit("")

        rc = task.run_shell(["ipfs", "get", "-o", dest, cid])
        if rc != 0:
            task.emit("IPFS fetch failed.", "error")
            task.done(False)
            return

        result = verify_fetched_file(dest)
        task.emit(f"Downloaded SHA256: {result['sha256']}")
        if result["sha256"] == sha256:
            task.emit("Integrity verified: hash matches registry entry.", "success")
        else:
            task.emit("WARNING: hash does NOT match expected value!", "error")
            task.done(False)
            return

        task.emit(f"Restored to: {dest}", "success")
        task.done(True)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@bp.route("/api/registry/ipfs-link", methods=["POST"])
def api_registry_ipfs_link():
    """Attach an IPFS CID to a registry entry by SHA256.

    JSON body: {"sha256": "...", "cid": "..."}
    """
    body = request.json or {}
    sha256 = body.get("sha256", "")
    cid = body.get("cid", "")
    if not sha256 or not cid:
        return jsonify({"error": "sha256 and cid are required"}), 400
    if not is_valid_cid(cid):
        return jsonify({"error": "Invalid IPFS CID format"}), 400
    updated = update_ipfs_cid(sha256, cid)
    if not updated:
        return jsonify({"error": "No matching registry entry found"}), 404
    return jsonify({"ok": True, "sha256": sha256, "cid": cid})


# ---------------------------------------------------------------------------
# Recovery guides
# ---------------------------------------------------------------------------


@bp.route("/api/recovery")
def api_recovery_list():
    """List available recovery guides."""
    guides = []
    for key, guide in RECOVERY_GUIDES.items():
        guides.append(
            {
                "id": key,
                "title": guide["title"],
                "device_type": guide["device_type"],
                "step_count": len(guide["steps"]),
            }
        )
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
        backups.append(
            {
                "name": d.name,
                "path": str(d),
                "model": info.get("model", "unknown"),
                "serial": info.get("serial", "unknown"),
                "drv_version": info.get("drv_version", ""),
                "has_firmware_dump": has_dump,
            }
        )
    return jsonify(backups)


# ---------------------------------------------------------------------------
# IPFS backup sync
# ---------------------------------------------------------------------------


@bp.route("/api/backup/ipfs-sync", methods=["POST"])
def api_backup_ipfs_sync():
    """Upload a backup directory to IPFS for decentralized storage.

    JSON body: {"backup_name": "20240101-120000"}
    """
    body = request.json or {}
    backup_name = body.get("backup_name", "")

    from web.core import BACKUP_DIR

    backup_path = BACKUP_DIR / backup_name
    if not backup_path.is_dir():
        return jsonify({"error": f"Backup '{backup_name}' not found"}), 404

    try:
        from web.ipfs_helpers import ipfs_available

        if not ipfs_available():
            return jsonify({"error": "IPFS daemon not running"}), 503
    except ImportError:
        return jsonify({"error": "IPFS helpers not available"}), 500

    def _run(task: Task):
        import subprocess as sp

        task.emit(f"Syncing backup '{backup_name}' to IPFS...")

        # Add entire backup directory to IPFS
        try:
            result = sp.run(
                ["ipfs", "add", "-r", "-Q", "--pin", str(backup_path)],
                capture_output=True,
                text=True,
                timeout=600,
            )
            if result.returncode == 0:
                cid = result.stdout.strip()
                task.emit("Backup pinned to IPFS!", "success")
                task.emit(f"CID: {cid}", "info")
                task.emit(f"Retrieve with: ipfs get {cid}", "info")

                # Save CID to backup directory
                (backup_path / "ipfs-cid.txt").write_text(cid + "\n")
                task.emit(f"CID saved to {backup_path / 'ipfs-cid.txt'}", "success")
            else:
                task.emit(f"IPFS add failed: {result.stderr}", "error")
                task.done(False)
                return
        except Exception as e:
            task.emit(f"IPFS sync failed: {e}", "error")
            task.done(False)
            return

        task.done(True)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})
