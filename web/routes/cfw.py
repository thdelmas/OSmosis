"""CFW Builder routes — firmware customization and patching."""

import hashlib
import json
from pathlib import Path

from flask import Blueprint, Response, jsonify, request

from web.cfw_builder import (
    build_cfw,
    get_all_families,
    get_patches_for_scooter,
    package_cfw_zip,
)
from web.core import Task, start_task
from web.ipfs_helpers import ipfs_available, ipfs_index_load, ipfs_pin_and_index, is_valid_cid
from web.registry import register
from web.scooter_proto import _load_firmware

bp = Blueprint("cfw", __name__)


@bp.route("/api/cfw/families")
def api_cfw_families():
    """List scooter families that have CFW patches available."""
    return jsonify(get_all_families())


@bp.route("/api/cfw/patches/<scooter_id>")
def api_cfw_patches(scooter_id: str):
    """Get available patches for a specific scooter model."""
    patches = get_patches_for_scooter(scooter_id)
    if not patches:
        return jsonify({"error": f"No patches available for '{scooter_id}'"}), 404
    return jsonify(patches)


@bp.route("/api/cfw/build", methods=["POST"])
def api_cfw_build():
    """Build a custom firmware from a stock binary + patch config.

    JSON body: {
        "scooter_id": "nb-g30",
        "fw_path": "/path/to/stock-firmware.bin",  (or .zip)
        "config": {
            "speed_limit": {"eco": 22, "drive": 28, "sport": 35},
            "motor_current": {"max_amps": 24},
            ...
        }
    }

    Returns the patch result (diff, warnings, hashes) as JSON.
    The patched firmware can then be downloaded via /api/cfw/download.
    """
    body = request.json or {}
    scooter_id = body.get("scooter_id", "")
    fw_path = body.get("fw_path", "")
    config = body.get("config", {})

    if not scooter_id:
        return jsonify({"error": "scooter_id is required"}), 400
    if not fw_path or not Path(fw_path).is_file():
        return jsonify({"error": "Firmware file not found"}), 400
    if not config:
        return jsonify({"error": "No patches configured"}), 400

    try:
        stock_fw = _load_firmware(fw_path)
    except Exception as e:
        return jsonify({"error": f"Failed to load firmware: {e}"}), 400

    result = build_cfw(stock_fw, scooter_id, config)

    # Save patched firmware to disk
    out_dir = Path.home() / "Osmosis-downloads" / "cfw" / scooter_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_bin = out_dir / f"{scooter_id}-cfw-{result.patched_sha256[:8]}.bin"
    out_bin.write_bytes(result.patched_fw)

    out_zip = out_dir / f"{scooter_id}-cfw-{result.patched_sha256[:8]}.zip"
    out_zip.write_bytes(package_cfw_zip(result, scooter_id, config))

    # Auto-pin to IPFS if available
    ipfs_cid = None
    if ipfs_available():
        ipfs_cid = ipfs_pin_and_index(
            str(out_zip),
            key=f"cfw/{scooter_id}/{out_zip.name}",
            codename=scooter_id,
            rom_name=f"CFW {scooter_id}",
            version=result.patched_sha256[:8],
            extra={"build_config": config},
        )

    response = result.to_dict()
    response["fw_path"] = str(out_bin)
    response["zip_path"] = str(out_zip)
    if ipfs_cid:
        response["ipfs_cid"] = ipfs_cid
    return jsonify(response)


@bp.route("/api/cfw/download", methods=["POST"])
def api_cfw_download():
    """Download a previously built CFW ZIP.

    JSON body: {"zip_path": "/path/to/cfw.zip"}
    """
    zip_path = (request.json or {}).get("zip_path", "")
    if not zip_path or not Path(zip_path).is_file():
        return jsonify({"error": "CFW ZIP not found"}), 400

    data = Path(zip_path).read_bytes()
    return Response(
        data,
        mimetype="application/zip",
        headers={"Content-Disposition": f"attachment; filename={Path(zip_path).name}"},
    )


@bp.route("/api/cfw/build-and-flash", methods=["POST"])
def api_cfw_build_and_flash():
    """Build CFW and immediately flash it to a connected scooter.

    JSON body: {
        "scooter_id": "nb-g30",
        "fw_path": "/path/to/stock-firmware.bin",
        "config": { ... },
        "address": "XX:XX:XX:XX:XX:XX"
    }
    """
    body = request.json or {}
    scooter_id = body.get("scooter_id", "")
    fw_path = body.get("fw_path", "")
    config = body.get("config", {})
    address = body.get("address", "").strip()

    if not scooter_id:
        return jsonify({"error": "scooter_id is required"}), 400
    if not fw_path or not Path(fw_path).is_file():
        return jsonify({"error": "Firmware file not found"}), 400
    if not config:
        return jsonify({"error": "No patches configured"}), 400
    if not address:
        return jsonify({"error": "BLE address is required"}), 400

    def _run(task: Task):
        import asyncio

        # Build
        task.emit("Loading stock firmware...", "info")
        try:
            stock_fw = _load_firmware(fw_path)
        except Exception as e:
            task.emit(f"Failed to load firmware: {e}", "error")
            task.done(False)
            return

        task.emit(f"Stock firmware: {len(stock_fw)} bytes", "info")
        task.emit("Applying patches...", "info")

        result = build_cfw(stock_fw, scooter_id, config)

        for p in result.patches_applied:
            task.emit(f"  Applied: {p}", "success")
        for w in result.warnings:
            task.emit(f"  Warning: {w}", "warn")
        for d in result.diff:
            task.emit(f"  {d['offset']}: {d['original']} -> {d['patched']} ({d['description']})")

        task.emit(f"Patched firmware: {len(result.patched_fw)} bytes", "info")
        task.emit(f"SHA256: {result.patched_sha256}", "info")

        # Save
        out_dir = Path.home() / "Osmosis-downloads" / "cfw" / scooter_id
        out_dir.mkdir(parents=True, exist_ok=True)
        out_bin = out_dir / f"{scooter_id}-cfw-{result.patched_sha256[:8]}.bin"
        out_bin.write_bytes(result.patched_fw)
        task.emit(f"Saved to {out_bin}", "success")

        # Auto-pin to IPFS
        if ipfs_available():
            out_zip = out_dir / f"{scooter_id}-cfw-{result.patched_sha256[:8]}.zip"
            out_zip.write_bytes(package_cfw_zip(result, scooter_id, config))
            cid = ipfs_pin_and_index(
                str(out_zip),
                key=f"cfw/{scooter_id}/{out_zip.name}",
                codename=scooter_id,
                rom_name=f"CFW {scooter_id}",
                version=result.patched_sha256[:8],
                extra={"build_config": config},
            )
            if cid:
                task.emit(f"Pinned to IPFS: {cid}", "success")

        # Flash
        task.emit(f"Connecting to scooter {address}...", "info")
        try:
            from web.scooter_proto import flash_firmware

            def on_progress(sent, total, state):
                pct = int(sent / total * 100) if total else 0
                task.emit(f"Flashing: {pct}% ({sent}/{total} bytes) [{state.name}]")

            asyncio.run(flash_firmware(address, str(out_bin), on_progress))
        except Exception as e:
            task.emit(f"Flash failed: {e}", "error")
            task.done(False)
            return

        task.emit("CFW flash complete!", "success")
        register(
            out_bin,
            device_id=address,
            device_label=scooter_id,
            component="cfw",
            flash_method="ble",
            sha256=result.patched_sha256,
        )
        task.done(True)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


# ---------------------------------------------------------------------------
# CFW Manifest sharing
# ---------------------------------------------------------------------------


@bp.route("/api/cfw/manifest/export/<scooter_id>")
def api_cfw_manifest_export(scooter_id: str):
    """Export all CFW builds for a scooter model as a shareable manifest."""
    index = ipfs_index_load()
    entries = []
    for key, entry in index.items():
        if key.startswith(f"cfw/{scooter_id}/") and entry.get("cid"):
            entries.append(
                {
                    "scooter_id": scooter_id,
                    "cid": entry["cid"],
                    "filename": entry.get("filename", ""),
                    "version": entry.get("version", ""),
                    "size": entry.get("size", 0),
                    "build_config": entry.get("build_config", {}),
                    "pinned_at": entry.get("pinned_at", ""),
                }
            )

    if not entries:
        return jsonify({"error": f"No CFW builds found for {scooter_id}"}), 404

    manifest = {"version": 1, "type": "cfw", "scooter_id": scooter_id, "entries": entries}
    payload = json.dumps(manifest, indent=2)
    sha256 = hashlib.sha256(payload.encode()).hexdigest()
    return jsonify({"manifest": manifest, "sha256": sha256})


@bp.route("/api/cfw/manifest/import", methods=["POST"])
def api_cfw_manifest_import():
    """Import CFW builds from a shared manifest.

    JSON body: {"manifest": {...}, "sha256": "..."}
    """
    from web.ipfs_helpers import ipfs_index_save

    body = request.json or {}
    manifest = body.get("manifest")
    expected_hash = body.get("sha256", "")

    if not manifest or manifest.get("type") != "cfw":
        return jsonify({"error": "Invalid CFW manifest"}), 400

    if expected_hash:
        payload = json.dumps(manifest, indent=2)
        actual_hash = hashlib.sha256(payload.encode()).hexdigest()
        if actual_hash != expected_hash:
            return jsonify({"error": "Manifest integrity check failed"}), 400

    scooter_id = manifest.get("scooter_id", "unknown")
    entries = manifest.get("entries", [])
    if not entries:
        return jsonify({"error": "Manifest has no entries"}), 400

    index = ipfs_index_load()
    imported = 0
    skipped = 0
    for entry in entries:
        cid = entry.get("cid", "")
        if not cid or not is_valid_cid(cid):
            skipped += 1
            continue
        filename = entry.get("filename", "")
        key = f"cfw/{scooter_id}/{filename}" if filename else f"cfw/{scooter_id}/{cid[:12]}"
        if key in index:
            skipped += 1
            continue
        index[key] = {
            "cid": cid,
            "filename": filename,
            "size": entry.get("size", 0),
            "codename": scooter_id,
            "rom_id": "",
            "rom_name": f"CFW {scooter_id}",
            "version": entry.get("version", ""),
            "pinned_at": entry.get("pinned_at", ""),
            "build_config": entry.get("build_config", {}),
            "source": "imported",
        }
        imported += 1

    if imported:
        ipfs_index_save(index)
    return jsonify({"imported": imported, "skipped": skipped, "scooter_id": scooter_id})
