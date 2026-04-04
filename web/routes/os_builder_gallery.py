"""OS Builder gallery and community build sharing routes."""

import json

from flask import Blueprint, jsonify, request

from web.ipfs_helpers import ipfs_index_load, ipfs_index_save
from web.os_builder import OUTPUT_DIR, BuildProfile

bp = Blueprint("os_builder_gallery", __name__)


@bp.route("/api/os-builder/gallery")
def api_os_builder_gallery():
    """Browse published OS builds from the IPFS index.

    Returns builds that have been published to IPFS (from this node or imported).
    Query params: ?distro=, ?arch=, ?desktop= for filtering.
    """
    index = ipfs_index_load()
    distro_filter = request.args.get("distro", "")
    arch_filter = request.args.get("arch", "")
    desktop_filter = request.args.get("desktop", "")

    builds = []
    for key, entry in index.items():
        if not key.startswith("os-build/"):
            continue
        profile = entry.get("build_profile", {})
        if distro_filter and profile.get("base") != distro_filter:
            continue
        if arch_filter and profile.get("arch") != arch_filter:
            continue
        if desktop_filter and profile.get("desktop") != desktop_filter:
            continue

        builds.append(
            {
                "key": key,
                "cid": entry.get("cid", ""),
                "filename": entry.get("filename", ""),
                "size": entry.get("size", 0),
                "rom_name": entry.get("rom_name", ""),
                "version": entry.get("version", ""),
                "pinned_at": entry.get("pinned_at", ""),
                "source": entry.get("source", "local"),
                "profile": profile,
            }
        )

    builds.sort(key=lambda b: b.get("pinned_at", ""), reverse=True)
    return jsonify(builds)


@bp.route("/api/os-builder/gallery/publish", methods=["POST"])
def api_os_builder_gallery_publish():
    """Publish a local build to the gallery by exporting it as a signed manifest.

    JSON body: {"filename": "my-os-debian-bookworm-amd64.img"}
    """
    import hashlib

    from web.ipfs_helpers import get_public_key_b64, sign_manifest

    filename = (request.json or {}).get("filename", "")
    if not filename:
        return jsonify({"error": "filename is required"}), 400

    out_path = OUTPUT_DIR / filename
    if not out_path.exists():
        return jsonify({"error": "Build not found"}), 404

    index = ipfs_index_load()
    build_entry = None
    for key, entry in index.items():
        if key.startswith("os-build/") and entry.get("filename") == filename:
            build_entry = entry
            break

    if not build_entry or not build_entry.get("cid"):
        return jsonify(
            {"error": "Build not pinned to IPFS. Publish to IPFS first."}
        ), 400

    manifest = {
        "version": 1,
        "type": "os-build",
        "build": {
            "cid": build_entry["cid"],
            "filename": filename,
            "size": build_entry.get("size", 0),
            "rom_name": build_entry.get("rom_name", ""),
            "profile": build_entry.get("build_profile", {}),
            "layer_cids": build_entry.get("build_profile", {}).get(
                "layer_cids", {}
            ),
        },
    }
    payload = json.dumps(manifest, indent=2)
    sha256 = hashlib.sha256(payload.encode()).hexdigest()

    return jsonify(
        {
            "manifest": manifest,
            "sha256": sha256,
            "signature": sign_manifest(payload),
            "public_key": get_public_key_b64(),
        }
    )


@bp.route("/api/os-builder/gallery/import", methods=["POST"])
def api_os_builder_gallery_import():
    """Import a published build into the local gallery.

    JSON body: {"manifest": {...}, "sha256": "...", "signature": "...", "public_key": "..."}
    """
    import hashlib

    from web.ipfs_helpers import (
        is_trusted_publisher,
        is_valid_cid,
        verify_manifest_signature,
    )

    body = request.json or {}
    manifest = body.get("manifest")
    expected_hash = body.get("sha256", "")
    signature = body.get("signature", "")
    public_key = body.get("public_key", "")

    if not manifest or manifest.get("type") != "os-build":
        return jsonify({"error": "Invalid OS build manifest"}), 400

    payload = json.dumps(manifest, indent=2)

    if expected_hash:
        actual_hash = hashlib.sha256(payload.encode()).hexdigest()
        if actual_hash != expected_hash:
            return jsonify({"error": "SHA256 mismatch"}), 400

    signer_info = {}
    if signature and public_key:
        if verify_manifest_signature(payload, signature, public_key):
            trusted_name = is_trusted_publisher(public_key)
            signer_info = {
                "signature_valid": True,
                "trusted": trusted_name is not None,
                "publisher": trusted_name or "unknown",
            }
        else:
            return jsonify({"error": "Signature verification failed"}), 400

    build = manifest.get("build", {})
    cid = build.get("cid", "")
    if not cid or not is_valid_cid(cid):
        return jsonify({"error": "Invalid or missing CID"}), 400

    filename = build.get("filename", f"community-build-{cid[:12]}")
    profile = build.get("profile", {})
    key = f"os-build/{filename}"

    index = ipfs_index_load()
    if key in index:
        return jsonify({"error": "Build already in gallery", "key": key}), 409

    index[key] = {
        "cid": cid,
        "filename": filename,
        "size": build.get("size", 0),
        "codename": f"os-build-{profile.get('base', 'unknown')}",
        "rom_name": build.get(
            "rom_name",
            f"{profile.get('name', 'Community')} ({profile.get('base', '')} {profile.get('suite', '')})",
        ),
        "version": profile.get("suite", ""),
        "pinned_at": "",
        "source": "gallery-import",
        "build_profile": profile,
    }
    ipfs_index_save(index)

    result = {"ok": True, "key": key, "cid": cid}
    if signer_info:
        result["signer"] = signer_info
    return jsonify(result)


@bp.route("/api/os-builder/gallery/fork", methods=["POST"])
def api_os_builder_gallery_fork():
    """Fork a gallery build into a new editable profile.

    JSON body: {"key": "os-build/...", "new_name": "my-fork"}
    """
    body = request.json or {}
    key = body.get("key", "")
    new_name = body.get("new_name", "")

    if not key or not new_name:
        return jsonify({"error": "key and new_name are required"}), 400

    index = ipfs_index_load()
    entry = index.get(key)
    if not entry:
        return jsonify({"error": "Build not found in gallery"}), 404

    profile_data = entry.get("build_profile", {})
    if not profile_data:
        return jsonify(
            {"error": "No build profile data available for this build"}
        ), 400

    profile_data["name"] = new_name
    # Clear layer_cids so the fork builds fresh
    profile_data.pop("layer_cids", None)

    try:
        profile = BuildProfile.from_dict(profile_data)
        path = profile.save()
        return jsonify(
            {
                "ok": True,
                "name": new_name,
                "path": str(path),
                "profile": profile.to_dict(),
            }
        )
    except Exception as e:
        return jsonify({"error": f"Failed to create profile: {e}"}), 400
