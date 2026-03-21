"""IPFS config distribution and trust management routes."""

import json
from pathlib import Path

from flask import Blueprint, jsonify, request

from web.ipfs_helpers import (
    ipfs_available,
    ipfs_index_load,
    ipfs_index_save,
    ipfs_pin_and_index,
    is_valid_cid,
)

bp = Blueprint("ipfs_config", __name__)

_CONFIG_FILES = ["devices.cfg", "scooters.cfg", "ebikes.cfg", "microcontrollers.cfg"]


@bp.route("/api/ipfs/publish-configs", methods=["POST"])
def api_ipfs_publish_configs():
    """Pin all device config files to IPFS and return their CIDs."""
    if not ipfs_available():
        return jsonify({"error": "IPFS daemon not running"}), 503

    from web.core import SCRIPT_DIR

    published = {}
    for name in _CONFIG_FILES:
        cfg_path = SCRIPT_DIR / name
        if not cfg_path.exists():
            continue
        cid = ipfs_pin_and_index(
            str(cfg_path),
            key=f"config/{name}",
            codename="config",
            rom_name=name,
        )
        if cid:
            published[name] = cid

    return jsonify({"published": published})


@bp.route("/api/ipfs/config-status")
def api_ipfs_config_status():
    """Check which config files are pinned and their CIDs."""
    from web.core import SCRIPT_DIR

    index = ipfs_index_load()
    configs = []
    for name in _CONFIG_FILES:
        key = f"config/{name}"
        entry = index.get(key)
        cfg_path = SCRIPT_DIR / name
        configs.append({
            "name": name,
            "exists": cfg_path.exists(),
            "pinned": entry is not None,
            "cid": entry.get("cid", "") if entry else "",
            "pinned_at": entry.get("pinned_at", "") if entry else "",
        })
    return jsonify(configs)


_CHANNEL_FILE = Path.home() / ".osmosis" / "ipfs-config-channel.json"


@bp.route("/api/ipfs/config-channel", methods=["GET", "POST"])
def api_ipfs_config_channel():
    """GET: return the current config channel subscription.
    POST: subscribe to a config channel by importing its manifest CID.

    A config channel is a JSON manifest pinned to IPFS containing CIDs for
    each config file. Format: {"version": 1, "configs": {"devices.cfg": "<cid>", ...}}

    POST body: {"channel_cid": "Qm..."}
    """
    if request.method == "GET":
        if _CHANNEL_FILE.exists():
            try:
                data = json.loads(_CHANNEL_FILE.read_text())
                return jsonify(data)
            except (json.JSONDecodeError, OSError):
                pass
        return jsonify({"subscribed": False})

    # POST — subscribe
    channel_cid = (request.json or {}).get("channel_cid", "")
    if not channel_cid or not is_valid_cid(channel_cid):
        return jsonify({"error": "Invalid channel CID"}), 400
    if not ipfs_available():
        return jsonify({"error": "IPFS daemon not running"}), 503

    from web.ipfs_helpers import ipfs_cat_to_file
    import tempfile as _tmpmod

    with _tmpmod.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as tmp:
        tmp_path = tmp.name

    try:
        ok = ipfs_cat_to_file(channel_cid, tmp_path)
        if not ok:
            return jsonify({"error": "Failed to fetch channel manifest from IPFS"}), 502

        manifest = json.loads(Path(tmp_path).read_text())
        if not isinstance(manifest.get("configs"), dict):
            return jsonify({"error": "Invalid channel manifest format"}), 400

        _CHANNEL_FILE.parent.mkdir(parents=True, exist_ok=True)
        _CHANNEL_FILE.write_text(json.dumps({
            "subscribed": True,
            "channel_cid": channel_cid,
            "configs": manifest["configs"],
        }, indent=2))
        return jsonify({"ok": True, "channel_cid": channel_cid, "configs": manifest["configs"]})
    finally:
        if Path(tmp_path).exists():
            Path(tmp_path).unlink()


@bp.route("/api/ipfs/config-channel/check")
def api_ipfs_config_channel_check():
    """Check for config updates from the subscribed channel."""
    if not _CHANNEL_FILE.exists():
        return jsonify({"error": "Not subscribed to any config channel"}), 400

    from web.core import SCRIPT_DIR
    from web.ipfs_helpers import ipfs_pin_ls

    try:
        channel = json.loads(_CHANNEL_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return jsonify({"error": "Invalid channel subscription file"}), 500

    configs = channel.get("configs", {})
    index = ipfs_index_load()
    updates = []
    for name, remote_cid in configs.items():
        if name not in _CONFIG_FILES:
            continue
        local_entry = index.get(f"config/{name}")
        local_cid = local_entry.get("cid", "") if local_entry else ""
        if local_cid != remote_cid:
            updates.append({
                "name": name,
                "local_cid": local_cid,
                "remote_cid": remote_cid,
                "has_local": (SCRIPT_DIR / name).exists(),
            })

    return jsonify({
        "channel_cid": channel.get("channel_cid", ""),
        "updates_available": len(updates),
        "updates": updates,
    })


@bp.route("/api/ipfs/config-channel/apply", methods=["POST"])
def api_ipfs_config_channel_apply():
    """Apply config updates from the subscribed channel.

    POST body: {"name": "devices.cfg"} or {"all": true}
    """
    if not ipfs_available():
        return jsonify({"error": "IPFS daemon not running"}), 503
    if not _CHANNEL_FILE.exists():
        return jsonify({"error": "Not subscribed to any config channel"}), 400

    from web.core import SCRIPT_DIR
    from web.ipfs_helpers import ipfs_cat_to_file

    try:
        channel = json.loads(_CHANNEL_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return jsonify({"error": "Invalid channel file"}), 500

    body = request.json or {}
    apply_all = body.get("all", False)
    target_name = body.get("name", "")
    configs = channel.get("configs", {})

    applied = []
    failed = []
    for name, remote_cid in configs.items():
        if name not in _CONFIG_FILES:
            continue
        if not apply_all and name != target_name:
            continue
        if not is_valid_cid(remote_cid):
            failed.append({"name": name, "error": "Invalid CID"})
            continue

        dest = str(SCRIPT_DIR / name)
        ok = ipfs_cat_to_file(remote_cid, dest)
        if ok:
            idx = ipfs_index_load()
            idx[f"config/{name}"] = {
                "cid": remote_cid,
                "filename": name,
                "size": (SCRIPT_DIR / name).stat().st_size,
                "codename": "config",
                "rom_name": name,
                "version": "",
                "pinned_at": "",
                "source": "channel",
            }
            ipfs_index_save(idx)
            applied.append(name)
        else:
            failed.append({"name": name, "error": "IPFS fetch failed"})

    return jsonify({"applied": applied, "failed": failed})


# ---------------------------------------------------------------------------
# Trust management
# ---------------------------------------------------------------------------


@bp.route("/api/ipfs/identity")
def api_ipfs_identity():
    """Return this node's signing public key."""
    from web.ipfs_helpers import get_public_key_b64

    return jsonify({"public_key": get_public_key_b64()})


@bp.route("/api/ipfs/trust", methods=["GET", "POST", "DELETE"])
def api_ipfs_trust():
    """Manage trusted publishers.

    GET: list all trusted publishers
    POST: {"name": "...", "public_key": "..."} — add a trusted publisher
    DELETE: {"name": "..."} — remove a trusted publisher
    """
    from web.ipfs_helpers import add_trusted_publisher, get_trusted_publishers, remove_trusted_publisher

    if request.method == "GET":
        return jsonify(get_trusted_publishers())

    body = request.json or {}
    name = body.get("name", "").strip()

    if request.method == "POST":
        pubkey = body.get("public_key", "").strip()
        if not name or not pubkey:
            return jsonify({"error": "name and public_key are required"}), 400
        add_trusted_publisher(name, pubkey)
        return jsonify({"ok": True, "name": name})

    if request.method == "DELETE":
        if not name:
            return jsonify({"error": "name is required"}), 400
        if remove_trusted_publisher(name):
            return jsonify({"ok": True, "name": name})
        return jsonify({"error": f"Publisher '{name}' not found"}), 404
