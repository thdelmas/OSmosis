"""OS Builder IPFS layer sharing and reproducibility helpers.

Extracted from os_builder.py to keep route files under the 500-line limit.
"""

import json

from flask import Blueprint, jsonify, request

from web.ipfs_helpers import (
    ipfs_add,
    ipfs_available,
    ipfs_index_load,
    ipfs_pin_and_index,
    layer_cache_key,
    layer_cache_lookup,
)
from web.os_builder import OUTPUT_DIR, BuildProfile

bp = Blueprint("os_builder_ipfs", __name__)


def ipfs_publish_build(task, profile: BuildProfile):
    """Pin the built image to IPFS after a successful build."""
    if not ipfs_available():
        task.emit("IPFS daemon not running — skipping publish.", "warn")
        return

    output_name = f"{profile.name}-{profile.base}-{profile.suite}-{profile.arch}"
    ext_map = {"img": ".img", "rootfs": ".tar.gz", "iso": ".iso"}
    ext = ext_map.get(profile.output_format, ".img")
    out_path = OUTPUT_DIR / f"{output_name}{ext}"

    if not out_path.exists():
        task.emit(f"Output file not found for IPFS publish: {out_path}", "warn")
        return

    task.emit("")
    task.emit(f"Publishing to IPFS: {out_path.name}...", "info")
    cid = ipfs_pin_and_index(
        str(out_path),
        key=f"os-build/{output_name}{ext}",
        codename=f"os-build-{profile.base}",
        rom_name=f"{profile.name} ({profile.base} {profile.suite} {profile.arch})",
        version=profile.suite,
        extra={"build_profile": profile.to_dict()},
    )
    if not cid:
        task.emit("Failed to pin to IPFS.", "error")
        return

    task.emit(f"IPFS CID: {cid}", "success")
    task.emit(f"Gateway: http://localhost:8080/ipfs/{cid}")
    task.emit("Build published to IPFS and indexed.", "success")

    # Also pin the profile JSON
    profile_path = OUTPUT_DIR / f"{output_name}-profile.json"
    if profile_path.exists():
        profile_cid = ipfs_add(str(profile_path))
        if profile_cid:
            task.emit(f"Profile CID: {profile_cid}", "info")


@bp.route("/api/os-builder/layers")
def api_os_builder_layers():
    """List all cached build layers in the IPFS index."""
    index = ipfs_index_load()
    layers = []
    for key, entry in index.items():
        if key.startswith("os-layer/"):
            layers.append(
                {
                    "key": key,
                    "cid": entry.get("cid", ""),
                    "size": entry.get("size", 0),
                    "pinned_at": entry.get("pinned_at", ""),
                    **{k: v for k, v in entry.items() if k in ("distro", "suite", "arch", "desktop", "package_count")},
                }
            )
    return jsonify(layers)


@bp.route("/api/os-builder/layers/manifest")
def api_os_builder_layers_manifest():
    """Export cached layers as a shareable manifest.

    Other users can import this to pre-fetch layers before building.
    """
    import hashlib

    from web.ipfs_helpers import get_public_key_b64, sign_manifest

    index = ipfs_index_load()
    entries = []
    for key, entry in index.items():
        if key.startswith("os-layer/") and entry.get("cid"):
            entries.append(
                {
                    "key": key,
                    "cid": entry["cid"],
                    "size": entry.get("size", 0),
                    "distro": entry.get("distro", ""),
                    "suite": entry.get("suite", ""),
                    "arch": entry.get("arch", ""),
                    "desktop": entry.get("desktop", ""),
                }
            )

    if not entries:
        return jsonify({"error": "No cached layers found"}), 404

    manifest = {"version": 1, "type": "os-layers", "entries": entries}
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


@bp.route("/api/os-builder/layers/prefetch", methods=["POST"])
def api_os_builder_layers_prefetch():
    """Pre-fetch layers from a shared profile or manifest.

    JSON body: either a build profile (with base/suite/arch/desktop/extra_packages)
    or a layer manifest (with entries[].cid).
    """
    if not ipfs_available():
        return jsonify({"error": "IPFS daemon not running"}), 503

    body = request.json or {}

    # If it's a manifest with entries, fetch those layers directly
    if body.get("type") == "os-layers" and body.get("entries"):
        return _prefetch_from_manifest(body)

    # If it's a profile, compute cache keys and check what's available
    base = body.get("base", "")
    suite = body.get("suite", "")
    arch = body.get("arch", "amd64")
    desktop = body.get("desktop", "none")
    extra_packages = body.get("extra_packages", [])

    results = []
    base_key = layer_cache_key("base", distro=base, suite=suite, arch=arch)
    base_cid = layer_cache_lookup(base_key)
    results.append({"layer": "base", "key": base_key, "cached": base_cid is not None, "cid": base_cid or ""})

    if extra_packages or desktop != "none":
        pkg_key = layer_cache_key(
            "packages",
            distro=base,
            suite=suite,
            arch=arch,
            desktop=desktop,
            packages=extra_packages,
        )
        pkg_cid = layer_cache_lookup(pkg_key)
        results.append(
            {
                "layer": "packages",
                "key": pkg_key,
                "cached": pkg_cid is not None,
                "cid": pkg_cid or "",
            }
        )

    return jsonify({"layers": results})


def _prefetch_from_manifest(body: dict):
    """Prefetch layers from a manifest with entries."""
    from web.ipfs_helpers import ipfs_index_save, is_valid_cid

    index = ipfs_index_load()
    fetched = 0
    for entry in body["entries"]:
        key = entry.get("key", "")
        cid = entry.get("cid", "")
        if not key or not cid or not is_valid_cid(cid):
            continue
        if key in index:
            continue
        index[key] = {
            "cid": cid,
            "filename": "",
            "size": entry.get("size", 0),
            "codename": "os-layer",
            "rom_name": key,
            "version": "",
            "pinned_at": "",
            "source": "prefetched",
            "distro": entry.get("distro", ""),
            "suite": entry.get("suite", ""),
            "arch": entry.get("arch", ""),
            "desktop": entry.get("desktop", ""),
        }
        fetched += 1
    if fetched:
        ipfs_index_save(index)
    return jsonify({"prefetched": fetched})


@bp.route("/api/os-builder/reproducibility", methods=["POST"])
def api_os_builder_reproducibility():
    """Check if a build profile matches any existing build by comparing layer CIDs.

    JSON body: a BuildProfile dict (must include layer_cids).
    Returns whether the input CIDs match locally known layers.
    """
    body = request.json or {}
    layer_cids = body.get("layer_cids", {})
    if not layer_cids:
        return jsonify({"error": "No layer_cids in profile"}), 400

    index = ipfs_index_load()
    matches = {}
    for layer_name, cid in layer_cids.items():
        found = False
        for key, entry in index.items():
            if entry.get("cid") == cid:
                matches[layer_name] = {"cid": cid, "key": key, "match": True}
                found = True
                break
        if not found:
            matches[layer_name] = {"cid": cid, "key": "", "match": False}

    all_match = all(m["match"] for m in matches.values())
    return jsonify(
        {
            "reproducible": all_match,
            "layers": matches,
            "summary": "All layers match local cache" if all_match else "Some layers differ or are missing",
        }
    )
