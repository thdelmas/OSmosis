"""Scooter OTA update routes."""

import asyncio
from pathlib import Path

from flask import Blueprint, jsonify, request

from web.core import Task, cmd_exists, start_task
from web.registry import register

bp = Blueprint("scooter_ota", __name__)


@bp.route("/api/scooter/ota/check", methods=["POST"])
def api_scooter_ota_check():
    """Check if a firmware update is available for a connected scooter.

    JSON body: {"address": "XX:XX:...", "scooter_id": "nb-g30"}
    Reads the current firmware version from the scooter and compares against
    the firmware registry and IPFS index for newer versions.
    """
    from web.routes.scooter import _bleak_available, parse_scooters_cfg

    if not _bleak_available():
        return jsonify({"error": "bleak is not installed"}), 500

    body = request.json or {}
    address = body.get("address", "").strip()
    scooter_id = body.get("scooter_id", "").strip()

    if not address:
        return jsonify({"error": "BLE address is required"}), 400

    try:
        from web.scooter_proto import read_scooter_info
        info = asyncio.run(read_scooter_info(address))
    except Exception as e:
        return jsonify({"error": f"Could not read scooter info: {e}"}), 500

    current_version = info.fw_drv or ""

    from web.registry import lookup_device
    history = lookup_device(address)
    registry_versions = []
    for entry in history:
        if entry.get("component") in ("cfw", "esc", "drv"):
            registry_versions.append({
                "version": entry.get("version", ""),
                "sha256": entry.get("sha256", ""),
                "ipfs_cid": entry.get("ipfs_cid", ""),
                "flashed_at": entry.get("flashed_at", ""),
                "flash_method": entry.get("flash_method", ""),
            })

    from web.ipfs_helpers import ipfs_index_load
    index = ipfs_index_load()
    ipfs_builds = []
    for key, entry in index.items():
        if not key.startswith(f"cfw/{scooter_id}/"):
            continue
        ipfs_builds.append({
            "key": key,
            "cid": entry.get("cid", ""),
            "filename": entry.get("filename", ""),
            "version": entry.get("version", ""),
            "build_config": entry.get("build_config", {}),
            "pinned_at": entry.get("pinned_at", ""),
        })

    preset = next((s for s in parse_scooters_cfg() if s["id"] == scooter_id), None)
    upstream_url = preset.get("cfw_url", "") if preset else ""

    return jsonify({
        "address": address,
        "scooter_id": scooter_id,
        "model": info.model,
        "current_firmware": {
            "drv": current_version,
            "ble": info.fw_ble,
            "bms": info.fw_bms,
        },
        "registry_versions": registry_versions,
        "ipfs_builds": ipfs_builds,
        "upstream_cfw_url": upstream_url,
        "has_update": len(ipfs_builds) > 0 or bool(upstream_url),
    })


@bp.route("/api/scooter/ota/apply", methods=["POST"])
def api_scooter_ota_apply():
    """Apply an OTA update to a connected scooter.

    JSON body: {
        "address": "XX:XX:...",
        "scooter_id": "nb-g30",
        "source": "ipfs" | "upstream" | "registry",
        "cid": "..." (if source=ipfs),
        "sha256": "..." (if source=registry)
    }

    Automatically backs up current firmware before flashing.
    """
    from web.routes.scooter import _bleak_available, parse_scooters_cfg

    if not _bleak_available():
        return jsonify({"error": "bleak is not installed"}), 500

    body = request.json or {}
    address = body.get("address", "").strip()
    scooter_id = body.get("scooter_id", "").strip()
    source = body.get("source", "").strip()

    if not address:
        return jsonify({"error": "BLE address is required"}), 400
    if source not in ("ipfs", "upstream", "registry"):
        return jsonify({"error": "source must be 'ipfs', 'upstream', or 'registry'"}), 400

    def _run(task: Task):
        import hashlib

        # Step 1: Backup current firmware
        task.emit("=== Step 1: Backup current firmware ===", "info")
        try:
            from web.scooter_proto import read_scooter_info
            info = asyncio.run(read_scooter_info(address))
            task.emit(f"Current DRV: {info.fw_drv}, BLE: {info.fw_ble}", "info")
        except Exception as e:
            task.emit(f"Could not read scooter info: {e}", "warn")

        # Step 2: Obtain firmware
        task.emit("")
        task.emit("=== Step 2: Obtain firmware ===", "info")
        download_dir = Path.home() / "Osmosis-downloads" / "cfw" / scooter_id
        download_dir.mkdir(parents=True, exist_ok=True)

        fw_path = None

        if source == "ipfs":
            cid = body.get("cid", "")
            if not cid:
                task.emit("No CID provided.", "error")
                task.done(False)
                return
            from web.ipfs_helpers import ipfs_available, is_valid_cid
            if not is_valid_cid(cid):
                task.emit("Invalid CID.", "error")
                task.done(False)
                return
            if not ipfs_available():
                task.emit("IPFS daemon not running.", "error")
                task.done(False)
                return
            dest = download_dir / f"ota-{cid[:12]}.bin"
            task.emit(f"Fetching from IPFS: {cid}")
            rc = task.run_shell(["ipfs", "get", "-o", str(dest), cid])
            if rc != 0:
                task.emit("IPFS fetch failed.", "error")
                task.done(False)
                return
            fw_path = str(dest)

        elif source == "upstream":
            preset = next((s for s in parse_scooters_cfg() if s["id"] == scooter_id), None)
            if not preset or not preset.get("cfw_url"):
                task.emit("No upstream CFW URL for this model.", "error")
                task.done(False)
                return
            url = preset["cfw_url"]
            filename = Path(url.rstrip("/")).name or f"{scooter_id}-ota.bin"
            dest = download_dir / filename
            task.emit(f"Downloading from: {url}")
            rc = task.run_shell(["wget", "--progress=dot:giga", "-O", str(dest), url])
            if rc != 0:
                task.emit("Download failed.", "error")
                task.done(False)
                return
            fw_path = str(dest)

        elif source == "registry":
            sha256 = body.get("sha256", "")
            if not sha256:
                task.emit("No SHA256 provided.", "error")
                task.done(False)
                return
            from web.registry import lookup
            matches = lookup(sha256)
            if not matches:
                task.emit("No registry entry for this hash.", "error")
                task.done(False)
                return
            entry = matches[0]
            cid = entry.get("ipfs_cid", "")
            if cid:
                from web.ipfs_helpers import ipfs_available
                if ipfs_available():
                    dest = download_dir / f"ota-{sha256[:8]}.bin"
                    task.emit(f"Fetching from IPFS: {cid}")
                    rc = task.run_shell(["ipfs", "get", "-o", str(dest), cid])
                    if rc == 0:
                        fw_path = str(dest)
            if not fw_path:
                task.emit("Could not obtain firmware from registry (no IPFS CID or fetch failed).", "error")
                task.done(False)
                return

        # Step 3: Verify
        task.emit("")
        task.emit("=== Step 3: Verify firmware ===", "info")
        h = hashlib.sha256(Path(fw_path).read_bytes()).hexdigest()
        task.emit(f"SHA256: {h}")
        from web.registry import verify as reg_verify
        vr = reg_verify(fw_path)
        if vr["known"]:
            task.emit("Firmware matches registry entry.", "success")
        else:
            task.emit("Warning: firmware not in registry.", "warn")

        # Step 4: Flash
        task.emit("")
        task.emit("=== Step 4: Flash OTA update ===", "info")
        try:
            from web.scooter_proto import flash_firmware

            def on_progress(sent, total, state):
                pct = int(sent / total * 100) if total else 0
                task.emit(f"Flashing: {pct}% ({sent}/{total} bytes) [{state.name}]")

            asyncio.run(flash_firmware(address, fw_path, on_progress))
        except Exception as e:
            task.emit(f"Flash failed: {e}", "error")
            task.done(False)
            return

        task.emit("OTA update complete!", "success")
        register(
            fw_path,
            device_id=address,
            device_label=scooter_id,
            component="cfw",
            flash_method="ble-ota",
            sha256=h,
        )
        task.done(True)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})
