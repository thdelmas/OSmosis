"""IPFS management routes."""

import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from flask import Blueprint, jsonify, request

from web.core import Task, start_task
from web.ipfs_helpers import (
    ipfs_available,
    ipfs_index_load,
    ipfs_index_save,
    ipfs_pin_and_index,
    ipfs_remote_pin,
    ipfs_remote_pin_configured,
    is_valid_cid,
    verify_fetched_file,
)

bp = Blueprint("ipfs", __name__)

_executor = ThreadPoolExecutor(max_workers=2)


@bp.route("/api/ipfs/status")
def api_ipfs_status():
    """Check if IPFS daemon is running and reachable."""

    def _check():
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
                info = {
                    "peer_id": data.get("ID", ""),
                    "agent": data.get("AgentVersion", ""),
                }
            except Exception:
                pass
        return {"available": available, **info}

    future = _executor.submit(_check)
    return jsonify(future.result(timeout=10))


@bp.route("/api/ipfs/index")
def api_ipfs_index():
    """List all ROMs stored in the local IPFS index."""
    index = ipfs_index_load()
    items = []
    for key, entry in index.items():
        items.append({"key": key, **entry})
    return jsonify(items)


ALLOWED_PIN_ROOTS = [
    Path.home() / "Osmosis-downloads",
    Path.home() / ".osmosis" / "backups",
    Path.home() / ".osmosis" / "scooter-backups",
    Path(__file__).resolve().parent.parent.parent / "roms",
]


def _path_allowed_for_pin(filepath: str) -> bool:
    """Check that filepath is under an allowed directory."""
    try:
        resolved = Path(filepath).resolve()
        return any(resolved.is_relative_to(root) for root in ALLOWED_PIN_ROOTS)
    except (ValueError, OSError):
        return False


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
    if not _path_allowed_for_pin(filepath):
        return jsonify(
            {"error": "File path is outside allowed directories"}
        ), 403
    if not ipfs_available():
        return jsonify({"error": "IPFS daemon not running"}), 503

    def _run(task: Task):
        p = Path(filepath)
        task.emit(f"Pinning to IPFS: {p.name}")
        task.emit(f"File size: {p.stat().st_size / (1024 * 1024):.1f} MB")
        task.emit("")

        key = f"{codename}/{p.name}"
        cid = ipfs_pin_and_index(
            filepath,
            key=key,
            codename=codename,
            rom_id=rom_id,
            rom_name=rom_name,
            version=version,
            task=task,
        )
        if not cid:
            task.emit("Failed to add file to IPFS.", "error")
            task.done(False)
            return

        task.emit(f"CID: {cid}", "success")
        task.emit(f"Gateway: http://localhost:8080/ipfs/{cid}")
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
    filename = Path(request.json.get("filename", "rom.zip")).name
    if not filename or filename.startswith("."):
        filename = "rom.zip"

    if not cid:
        return jsonify({"error": "No CID provided"}), 400
    if not is_valid_cid(cid):
        return jsonify({"error": "Invalid IPFS CID format"}), 400
    if not ipfs_available():
        return jsonify({"error": "IPFS daemon not running"}), 503

    def _run(task: Task):
        target = Path.home() / "Osmosis-downloads" / codename
        target.mkdir(parents=True, exist_ok=True)
        dest = str(target / filename)

        task.emit(f"Fetching from IPFS: {cid}")
        task.emit(f"Destination: {dest}")
        task.emit("")

        rc = task.run_shell(["ipfs", "get", "-o", dest, cid])
        if rc == 0:
            result = verify_fetched_file(dest)
            task.emit(f"SHA256: {result['sha256']}")
            if result["known"]:
                task.emit(
                    "Integrity check: file matches a known-good firmware entry.",
                    "success",
                )
            else:
                task.emit(
                    "Integrity warning: this file is NOT in the firmware registry. Verify before flashing.",
                    "warn",
                )
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
        _executor.submit(
            subprocess.run,
            ["ipfs", "pin", "rm", cid],
            capture_output=True,
            text=True,
            timeout=30,
        )

    del index[key]
    ipfs_index_save(index)
    return jsonify({"ok": True, "cid": cid})


@bp.route("/api/ipfs/remote-pin", methods=["POST"])
def api_ipfs_remote_pin():
    """Pin a CID to the configured remote pinning service."""
    cid = (request.json or {}).get("cid", "")
    name = (request.json or {}).get("name", "")
    if not cid:
        return jsonify({"error": "No CID provided"}), 400
    if not is_valid_cid(cid):
        return jsonify({"error": "Invalid IPFS CID format"}), 400
    if not ipfs_available():
        return jsonify({"error": "IPFS daemon not running"}), 503
    if not ipfs_remote_pin_configured():
        return jsonify(
            {
                "error": "No remote pinning service configured. Run: ipfs pin remote service add osmosis-pin <endpoint> <key>"
            }
        ), 400

    ok = ipfs_remote_pin(cid, name=name)
    if ok:
        return jsonify({"ok": True, "cid": cid})
    return jsonify({"error": "Remote pin failed"}), 502


@bp.route("/api/ipfs/remote-pin/status")
def api_ipfs_remote_pin_status():
    """Check if remote pinning is configured."""
    return jsonify({"configured": ipfs_remote_pin_configured()})


@bp.route("/api/ipfs/health")
def api_ipfs_health():
    """Check health of all indexed CIDs — verify they are still pinned locally."""
    if not ipfs_available():
        return jsonify({"error": "IPFS daemon not running"}), 503

    from web.ipfs_helpers import ipfs_pin_ls

    index = ipfs_index_load()
    healthy = []
    stale = []
    for key, entry in index.items():
        cid = entry.get("cid", "")
        if cid and ipfs_pin_ls(cid):
            healthy.append(key)
        else:
            stale.append(
                {"key": key, "cid": cid, "filename": entry.get("filename", "")}
            )
    return jsonify(
        {"healthy": len(healthy), "stale": stale, "total": len(index)}
    )


@bp.route("/api/ipfs/providers/<cid>")
def api_ipfs_providers(cid: str):
    """Query the DHT for peers providing a CID."""
    if not is_valid_cid(cid):
        return jsonify({"error": "Invalid CID format"}), 400
    if not ipfs_available():
        return jsonify({"error": "IPFS daemon not running"}), 503

    from web.ipfs_helpers import ipfs_find_providers

    providers = ipfs_find_providers(cid, max_providers=5, timeout_secs=8)
    return jsonify(
        {"cid": cid, "providers": providers, "count": len(providers)}
    )


@bp.route("/api/ipfs/manifest/export")
def api_ipfs_manifest_export():
    """Export the IPFS index as a signed, shareable manifest.

    Query param: ?sign=true (default true) to include Ed25519 signature.
    """
    import hashlib

    from web.ipfs_helpers import get_public_key_b64, sign_manifest

    index = ipfs_index_load()
    manifest = {
        "version": 1,
        "entries": [],
    }
    for key, entry in index.items():
        manifest["entries"].append(
            {
                "key": key,
                "cid": entry.get("cid", ""),
                "filename": entry.get("filename", ""),
                "size": entry.get("size", 0),
                "codename": entry.get("codename", ""),
                "rom_name": entry.get("rom_name", ""),
                "version": entry.get("version", ""),
            }
        )

    payload = json.dumps(manifest, indent=2)
    digest = hashlib.sha256(payload.encode()).hexdigest()

    result = {"manifest": manifest, "sha256": digest}

    if request.args.get("sign", "true").lower() != "false":
        result["signature"] = sign_manifest(payload)
        result["public_key"] = get_public_key_b64()

    # Broadcast via PubSub
    if ipfs_available() and manifest["entries"]:
        from web.ipfs_p2p import PUBSUB_TOPIC, pubsub_publish

        pubsub_publish(
            PUBSUB_TOPIC,
            {
                "type": "manifest",
                "message": f"Manifest exported ({len(manifest['entries'])} entries)",
                "cid": digest[:16],
            },
        )

    return jsonify(result)


@bp.route("/api/ipfs/manifest/import", methods=["POST"])
def api_ipfs_manifest_import():
    """Import entries from a shared manifest into the local IPFS index.

    JSON body: {"manifest": {...}, "sha256": "...", "signature": "...", "public_key": "..."}
    If signature + public_key are present, verifies Ed25519 signature.
    Entries are merged — existing keys are not overwritten.
    """
    import hashlib

    from web.ipfs_helpers import is_trusted_publisher, verify_manifest_signature

    body = request.json or {}
    manifest = body.get("manifest")
    expected_hash = body.get("sha256", "")
    signature = body.get("signature", "")
    public_key = body.get("public_key", "")

    if not manifest or not isinstance(manifest, dict):
        return jsonify({"error": "Invalid manifest"}), 400

    payload = json.dumps(manifest, indent=2)

    if expected_hash:
        actual_hash = hashlib.sha256(payload.encode()).hexdigest()
        if actual_hash != expected_hash:
            return jsonify(
                {"error": "Manifest integrity check failed (SHA256 mismatch)"}
            ), 400

    # Verify signature if present
    signer_info = {}
    if signature and public_key:
        if verify_manifest_signature(payload, signature, public_key):
            trusted_name = is_trusted_publisher(public_key)
            signer_info = {
                "signature_valid": True,
                "trusted": trusted_name is not None,
                "publisher": trusted_name or "unknown",
                "public_key": public_key,
            }
        else:
            return jsonify(
                {"error": "Manifest signature verification failed"}
            ), 400

    entries = manifest.get("entries", [])
    if not entries:
        return jsonify({"error": "Manifest has no entries"}), 400

    index = ipfs_index_load()
    imported = 0
    skipped = 0
    for entry in entries:
        key = entry.get("key", "")
        cid = entry.get("cid", "")
        if not key or not cid or not is_valid_cid(cid):
            skipped += 1
            continue
        if key in index:
            skipped += 1
            continue
        index[key] = {
            "cid": cid,
            "filename": entry.get("filename", ""),
            "size": entry.get("size", 0),
            "codename": entry.get("codename", ""),
            "rom_id": "",
            "rom_name": entry.get("rom_name", ""),
            "version": entry.get("version", ""),
            "pinned_at": "",
            "source": "imported",
        }
        imported += 1

    if imported:
        ipfs_index_save(index)
    result = {"imported": imported, "skipped": skipped}
    if signer_info:
        result["signer"] = signer_info
    return jsonify(result)
