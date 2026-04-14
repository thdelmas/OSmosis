"""LAN sharing routes — share and receive firmware over local network.

No IPFS or internet required. Uses mDNS for peer discovery and
a temporary HTTP server for file transfer.
"""

import os
from pathlib import Path

from flask import Blueprint, jsonify, request

from web.core import Task, start_task
from web.ipfs_helpers import ipfs_index_load
from web.lan_share import (
    discover_peers,
    download_from_peer,
    list_shares,
    start_share,
    stop_share,
)

bp = Blueprint("lan_share", __name__)


@bp.route("/api/lan/shares")
def api_lan_shares():
    """List active LAN shares from this machine."""
    return jsonify(list_shares())


@bp.route("/api/lan/share", methods=["POST"])
def api_lan_share_start():
    """Start sharing a file on the LAN.

    JSON body: {"key": "codename/file.zip"}  (IPFS index key)
      or:      {"path": "/path/to/file.zip"}
    """
    body = request.json or {}

    file_path = body.get("path")
    cid = None
    filename = None

    # Resolve from IPFS index if key provided
    if not file_path and body.get("key"):
        index = ipfs_index_load()
        entry = index.get(body["key"])
        if not entry:
            return jsonify({"error": f"Key not found in IPFS index: {body['key']}"}), 404
        # Look for the file on disk
        cid = entry.get("cid", "")
        filename = entry.get("filename", "")
        # Check common download locations
        for search_dir in [
            Path.home() / "Osmosis-downloads",
            Path.home() / "Downloads",
            Path("/tmp/osmosis"),
        ]:
            candidate = search_dir / filename
            if candidate.exists():
                file_path = str(candidate)
                break
        if not file_path:
            return jsonify({
                "error": f"File not on disk: {filename}. Download it first.",
            }), 404

    if not file_path:
        return jsonify({"error": "Provide 'key' or 'path'"}), 400

    info = start_share(file_path, filename=filename, cid=cid)
    if not info:
        return jsonify({"error": "Failed to start share"}), 500

    return jsonify(info.to_dict()), 201


@bp.route("/api/lan/share/<share_id>", methods=["DELETE"])
def api_lan_share_stop(share_id: str):
    """Stop sharing a file."""
    if stop_share(share_id):
        return jsonify({"ok": True})
    return jsonify({"error": "Share not found"}), 404


@bp.route("/api/lan/peers")
def api_lan_peers():
    """Discover other OSmosis instances sharing on the LAN."""
    timeout = request.args.get("timeout", 5, type=int)
    timeout = min(timeout, 15)
    peers = discover_peers(timeout_secs=timeout)
    return jsonify(peers)


@bp.route("/api/lan/download", methods=["POST"])
def api_lan_download():
    """Download a shared file from a LAN peer.

    JSON body: {"host": "192.168.1.42", "port": 19200, "sha256": "..."}
    Returns: {"task_id": "..."} — streams download progress.
    """
    body = request.json or {}
    host = body.get("host", "")
    port = body.get("port", 0)
    sha256 = body.get("sha256")

    if not host or not port:
        return jsonify({"error": "Provide host and port"}), 400

    dest_dir = str(Path.home() / "Osmosis-downloads")
    os.makedirs(dest_dir, exist_ok=True)

    def _run(task: Task):
        task.emit(f"Downloading from {host}:{port}...")
        result = download_from_peer(
            host=host,
            port=port,
            dest_dir=dest_dir,
            expected_sha256=sha256,
        )
        if result:
            size_mb = os.path.getsize(result) / (1024 * 1024)
            task.emit(f"Downloaded: {result} ({size_mb:.1f} MB)", "success")
            if sha256:
                task.emit("SHA256 verified.", "success")
            task.done(True)
        else:
            task.emit("Download failed or integrity check failed.", "error")
            task.done(False)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})
