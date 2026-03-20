"""IPFS management routes."""

import json
import subprocess
from pathlib import Path

from flask import Blueprint, jsonify, request

from web.core import Task, start_task
from web.ipfs_helpers import ipfs_add, ipfs_available, ipfs_index_load, ipfs_index_save

bp = Blueprint("ipfs", __name__)


@bp.route("/api/ipfs/status")
def api_ipfs_status():
    """Check if IPFS daemon is running and reachable."""
    available = ipfs_available()
    info = {}
    if available:
        try:
            r = subprocess.run(
                ["ipfs", "id"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            data = json.loads(r.stdout)
            info = {"peer_id": data.get("ID", ""), "agent": data.get("AgentVersion", "")}
        except Exception:
            pass
    return jsonify({"available": available, **info})


@bp.route("/api/ipfs/index")
def api_ipfs_index():
    """List all ROMs stored in the local IPFS index."""
    index = ipfs_index_load()
    items = []
    for key, entry in index.items():
        items.append({"key": key, **entry})
    return jsonify(items)


@bp.route("/api/ipfs/pin", methods=["POST"])
def api_ipfs_pin():
    """Pin a downloaded ROM file to IPFS and record its CID."""
    filepath = request.json.get("filepath", "")
    codename = request.json.get("codename", "unknown")
    rom_id = request.json.get("rom_id", "")
    rom_name = request.json.get("rom_name", "")
    version = request.json.get("version", "")

    if not filepath or not Path(filepath).exists():
        return jsonify({"error": "File not found"}), 400
    if not ipfs_available():
        return jsonify({"error": "IPFS daemon not running"}), 503

    def _run(task: Task):
        import datetime

        p = Path(filepath)
        task.emit(f"Pinning to IPFS: {p.name}")
        task.emit(f"File size: {p.stat().st_size / (1024 * 1024):.1f} MB")
        task.emit("")

        cid = ipfs_add(filepath)
        if not cid:
            task.emit("Failed to add file to IPFS.", "error")
            task.done(False)
            return

        task.emit(f"CID: {cid}", "success")
        task.emit(f"Gateway: https://ipfs.io/ipfs/{cid}")

        index = ipfs_index_load()
        key = f"{codename}/{p.name}"
        index[key] = {
            "cid": cid,
            "size": p.stat().st_size,
            "filename": p.name,
            "codename": codename,
            "rom_id": rom_id,
            "rom_name": rom_name,
            "version": version,
            "pinned_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        ipfs_index_save(index)

        task.emit("")
        task.emit(f"Stored in IPFS index: {key}", "success")
        task.done(True)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@bp.route("/api/ipfs/fetch", methods=["POST"])
def api_ipfs_fetch():
    """Retrieve a ROM from IPFS by CID and save it locally."""
    cid = request.json.get("cid", "")
    codename = request.json.get("codename", "unknown")
    filename = request.json.get("filename", "rom.zip")

    if not cid:
        return jsonify({"error": "No CID provided"}), 400
    if not ipfs_available():
        return jsonify({"error": "IPFS daemon not running"}), 503

    def _run(task: Task):
        import hashlib

        target = Path.home() / "Osmosis-downloads" / codename
        target.mkdir(parents=True, exist_ok=True)
        dest = str(target / filename)

        task.emit(f"Fetching from IPFS: {cid}")
        task.emit(f"Destination: {dest}")
        task.emit("")

        rc = task.run_shell(["ipfs", "get", "-o", dest, cid])
        if rc == 0:
            h = hashlib.sha256(Path(dest).read_bytes()).hexdigest()
            task.emit(f"SHA256: {h}")
            task.emit(f"Saved to: {dest}", "success")
        else:
            task.emit("IPFS fetch failed.", "error")
        task.done(rc == 0)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@bp.route("/api/ipfs/unpin", methods=["POST"])
def api_ipfs_unpin():
    """Unpin a ROM from IPFS and remove it from the index."""
    key = request.json.get("key", "")
    if not key:
        return jsonify({"error": "No key provided"}), 400

    index = ipfs_index_load()
    entry = index.get(key)
    if not entry:
        return jsonify({"error": "Not found in index"}), 404

    cid = entry["cid"]
    if ipfs_available():
        subprocess.run(
            ["ipfs", "pin", "rm", cid],
            capture_output=True,
            text=True,
            timeout=30,
        )

    del index[key]
    ipfs_index_save(index)
    return jsonify({"ok": True, "cid": cid})
