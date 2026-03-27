"""IPFS Tier 6 routes — Bitswap stats, CAR export/import, PubSub.

Split from ipfs.py to keep modules under the 500-line limit.
"""

import datetime
import json
from pathlib import Path

from flask import Blueprint, Response, jsonify, request

from web.core import Task, start_task
from web.ipfs_helpers import ipfs_available, ipfs_index_load, is_valid_cid
from web.ipfs_p2p import (
    PUBSUB_TOPIC,
    ipfs_bitswap_stat,
    ipfs_dag_export,
    ipfs_dag_import,
    pubsub_publish,
    pubsub_subscribe,
)

bp = Blueprint("ipfs_p2p", __name__)


# ---------------------------------------------------------------------------
# Bitswap stats
# ---------------------------------------------------------------------------


@bp.route("/api/ipfs/bitswap")
def api_ipfs_bitswap():
    """Return IPFS bitswap statistics — blocks/bytes sent and received,
    connected peers, and seeding ratio."""
    if not ipfs_available():
        return jsonify({"error": "IPFS daemon not running"}), 503

    stats = ipfs_bitswap_stat()
    if stats is None:
        return jsonify({"error": "Failed to retrieve bitswap stats"}), 500
    return jsonify(stats)


# ---------------------------------------------------------------------------
# CAR export/import — offline firmware transfer
# ---------------------------------------------------------------------------


@bp.route("/api/ipfs/car/export", methods=["POST"])
def api_ipfs_car_export():
    """Export selected IPFS index entries as a .car archive.

    JSON body: {"keys": ["codename/file.zip", ...]}
    If keys is empty or omitted, exports all entries.
    Returns: {"task_id": "..."}  — task streams progress, final line has path.
    """
    if not ipfs_available():
        return jsonify({"error": "IPFS daemon not running"}), 503

    body = request.json or {}
    requested_keys = body.get("keys", [])

    index = ipfs_index_load()
    if requested_keys:
        entries = {k: index[k] for k in requested_keys if k in index}
    else:
        entries = index

    if not entries:
        return jsonify({"error": "No matching entries in IPFS index"}), 400

    def _run(task: Task):
        export_dir = Path.home() / "Osmosis-downloads" / "car-exports"
        export_dir.mkdir(parents=True, exist_ok=True)

        exported = []
        failed = []
        for key, entry in entries.items():
            cid = entry.get("cid", "")
            if not cid or not is_valid_cid(cid):
                failed.append(key)
                continue
            fname = entry.get("filename", cid)
            dest = str(export_dir / f"{Path(fname).stem}-{cid[:12]}.car")
            task.emit(f"Exporting {key} ({cid[:16]}...)")
            if ipfs_dag_export(cid, dest):
                size_mb = Path(dest).stat().st_size / (1024 * 1024)
                task.emit(f"  Saved: {dest} ({size_mb:.1f} MB)", "success")
                exported.append({"key": key, "cid": cid, "path": dest})
            else:
                task.emit(f"  Failed to export {key}", "error")
                failed.append(key)

        task.emit("")
        task.emit(f"Exported {len(exported)} of {len(entries)} entries.", "success")
        if failed:
            task.emit(f"Failed: {', '.join(failed)}", "warn")
        task.done(len(exported) > 0)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@bp.route("/api/ipfs/car/import", methods=["POST"])
def api_ipfs_car_import():
    """Import a .car file into IPFS and pin its roots.

    JSON body: {"path": "/path/to/file.car"}
    Returns: {"roots": ["Qm..."], "count": N}
    """
    if not ipfs_available():
        return jsonify({"error": "IPFS daemon not running"}), 503

    body = request.json or {}
    car_path = body.get("path", "")

    if not car_path:
        return jsonify({"error": "No path provided"}), 400

    resolved = Path(car_path).resolve()
    if not resolved.exists():
        return jsonify({"error": "File not found"}), 404
    if resolved.suffix != ".car":
        return jsonify({"error": "File must be a .car archive"}), 400

    def _run(task: Task):
        task.emit(f"Importing CAR file: {resolved.name}")
        task.emit(f"Size: {resolved.stat().st_size / (1024 * 1024):.1f} MB")
        task.emit("")

        roots = ipfs_dag_import(str(resolved))
        if roots:
            task.emit(f"Imported {len(roots)} root(s):", "success")
            for root_cid in roots:
                task.emit(f"  {root_cid}")
            task.emit("")
            task.emit("Root CIDs are now pinned locally.", "success")
        else:
            task.emit("CAR import failed — no roots were pinned.", "error")
        task.done(len(roots) > 0)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


# ---------------------------------------------------------------------------
# PubSub — real-time update notifications
# ---------------------------------------------------------------------------


@bp.route("/api/ipfs/pubsub/publish", methods=["POST"])
def api_ipfs_pubsub_publish():
    """Broadcast an update notification to the osmosis-updates PubSub topic.

    JSON body: {"type": "firmware|config|manifest", "cid": "...", "message": "..."}
    """
    if not ipfs_available():
        return jsonify({"error": "IPFS daemon not running"}), 503

    body = request.json or {}
    msg_type = body.get("type", "update")
    cid = body.get("cid", "")
    message = body.get("message", "")

    notification = {
        "type": msg_type,
        "cid": cid,
        "message": message,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    ok = pubsub_publish(PUBSUB_TOPIC, notification)
    if ok:
        return jsonify({"ok": True, "topic": PUBSUB_TOPIC})
    return jsonify({"error": "PubSub publish failed"}), 502


@bp.route("/api/ipfs/pubsub/subscribe")
def api_ipfs_pubsub_subscribe():
    """SSE endpoint that relays IPFS PubSub messages to the frontend.

    Streams messages from the osmosis-updates topic as Server-Sent Events.
    """
    if not ipfs_available():
        return jsonify({"error": "IPFS daemon not running"}), 503

    def _generate():
        try:
            for msg in pubsub_subscribe(PUBSUB_TOPIC):
                yield f"data: {json.dumps(msg)}\n\n"
        except GeneratorExit:
            pass

    return Response(_generate(), mimetype="text/event-stream")
