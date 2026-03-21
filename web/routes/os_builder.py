"""OS Builder routes — build custom OS images from the web UI."""

import json

from flask import Blueprint, jsonify, request

from web.core import Task, start_task
from web.ipfs_helpers import (
    ipfs_add,
    ipfs_available,
    ipfs_index_load,
    ipfs_pin_and_index,
    layer_cache_key,
    layer_cache_lookup,
)
from web.os_builder import (
    DESKTOP_ENVIRONMENTS,
    INIT_SYSTEMS,
    OUTPUT_DIR,
    OUTPUT_FORMATS,
    PROFILES_DIR,
    SUPPORTED_BASES,
    TARGET_DEVICES,
    BuildProfile,
    build_os,
    estimate_image_size,
    generate_alpine_answers,
    generate_kickstart,
    generate_nix_config,
    generate_pacstrap_script,
    generate_preseed,
    list_profiles,
)

bp = Blueprint("os_builder", __name__)


# ---------------------------------------------------------------------------
# Info endpoints — drive the UI dropdowns
# ---------------------------------------------------------------------------


@bp.route("/api/os-builder/options")
def api_os_builder_options():
    """Return all options for the OS builder form."""
    return jsonify(
        {
            "bases": {k: {kk: vv for kk, vv in v.items()} for k, v in SUPPORTED_BASES.items()},
            "init_systems": INIT_SYSTEMS,
            "desktops": DESKTOP_ENVIRONMENTS,
            "output_formats": OUTPUT_FORMATS,
            "target_devices": TARGET_DEVICES,
        }
    )


@bp.route("/api/os-builder/estimate", methods=["POST"])
def api_os_builder_estimate():
    """Estimate the output image size for a given profile."""
    body = request.json or {}
    try:
        profile = BuildProfile.from_dict(body)
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(estimate_image_size(profile))


# ---------------------------------------------------------------------------
# Config file preview
# ---------------------------------------------------------------------------


@bp.route("/api/os-builder/preview", methods=["POST"])
def api_os_builder_preview():
    """Preview the generated preseed/answer file/install script."""
    body = request.json or {}
    try:
        profile = BuildProfile.from_dict(body)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    if profile.base in ("ubuntu", "debian"):
        return jsonify(
            {
                "type": "preseed",
                "filename": "preseed.cfg",
                "content": generate_preseed(profile),
            }
        )
    elif profile.base == "arch":
        return jsonify(
            {
                "type": "pacstrap-script",
                "filename": "install.sh",
                "content": generate_pacstrap_script(profile),
            }
        )
    elif profile.base == "alpine":
        return jsonify(
            {
                "type": "alpine-answers",
                "filename": "answers",
                "content": generate_alpine_answers(profile),
            }
        )
    elif profile.base == "fedora":
        return jsonify(
            {
                "type": "kickstart",
                "filename": "kickstart.cfg",
                "content": generate_kickstart(profile),
            }
        )
    elif profile.base == "nixos":
        return jsonify(
            {
                "type": "nix-config",
                "filename": "configuration.nix",
                "content": generate_nix_config(profile),
            }
        )
    else:
        return jsonify({"error": f"Unsupported base: {profile.base}"}), 400


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------


@bp.route("/api/os-builder/build", methods=["POST"])
def api_os_builder_build():
    """Start an OS build as a background task.

    JSON body: a BuildProfile dict.
    Optional: "ipfs_publish": true to pin the output to IPFS after build.
    """
    body = request.json or {}
    ipfs_publish = body.pop("ipfs_publish", False)

    try:
        profile = BuildProfile.from_dict(body)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    if not profile.name:
        return jsonify({"error": "Build name is required"}), 400
    if profile.base not in SUPPORTED_BASES:
        return jsonify({"error": f"Unsupported base: {profile.base}"}), 400

    def _run(task: Task):
        build_os(task, profile)

        # If the build succeeded and IPFS publish is requested, pin the output
        if task.status == "done" and ipfs_publish:
            _ipfs_publish_build(task, profile)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


def _ipfs_publish_build(task: Task, profile: BuildProfile):
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


# ---------------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------------


@bp.route("/api/os-builder/profiles")
def api_os_builder_profiles():
    """List saved build profiles."""
    return jsonify(list_profiles())


@bp.route("/api/os-builder/profiles", methods=["POST"])
def api_os_builder_save_profile():
    """Save a build profile."""
    body = request.json or {}
    try:
        profile = BuildProfile.from_dict(body)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    path = profile.save()
    return jsonify({"ok": True, "path": str(path), "profile": profile.to_dict()})


@bp.route("/api/os-builder/profiles/<name>", methods=["DELETE"])
def api_os_builder_delete_profile(name: str):
    """Delete a saved build profile."""
    path = PROFILES_DIR / f"{name}.json"
    if not path.exists():
        return jsonify({"error": "Profile not found"}), 404
    path.unlink()
    return jsonify({"ok": True})


@bp.route("/api/os-builder/profiles/<name>")
def api_os_builder_get_profile(name: str):
    """Load a specific build profile."""
    path = PROFILES_DIR / f"{name}.json"
    if not path.exists():
        return jsonify({"error": "Profile not found"}), 404
    try:
        profile = BuildProfile.load(path)
        return jsonify(profile.to_dict())
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ---------------------------------------------------------------------------
# Builds listing
# ---------------------------------------------------------------------------


@bp.route("/api/os-builder/builds")
def api_os_builder_builds():
    """List completed OS builds in the output directory."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    builds = []
    for f in sorted(OUTPUT_DIR.iterdir(), reverse=True):
        if f.suffix in (".img", ".iso", ".gz") and not f.name.endswith("-profile.json"):
            profile_path = f.with_name(f.stem.replace(".tar", "") + "-profile.json")
            profile_data = None
            if profile_path.exists():
                try:
                    profile_data = json.loads(profile_path.read_text())
                except Exception:
                    pass
            builds.append(
                {
                    "filename": f.name,
                    "path": str(f),
                    "size_mb": round(f.stat().st_size / (1024 * 1024), 1),
                    "profile": profile_data,
                }
            )
    return jsonify(builds)


# ---------------------------------------------------------------------------
# Layer sharing
# ---------------------------------------------------------------------------


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

    from web.ipfs_helpers import ipfs_index_save, is_valid_cid

    body = request.json or {}

    # If it's a manifest with entries, fetch those layers directly
    if body.get("type") == "os-layers" and body.get("entries"):
        index = ipfs_index_load()
        fetched = 0
        for entry in body["entries"]:
            key = entry.get("key", "")
            cid = entry.get("cid", "")
            if not key or not cid or not is_valid_cid(cid):
                continue
            if key in index:
                continue
            # Just pin it — don't extract, the build will find it by cache key
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
            "packages", distro=base, suite=suite, arch=arch, desktop=desktop, packages=extra_packages
        )
        pkg_cid = layer_cache_lookup(pkg_key)
        results.append({"layer": "packages", "key": pkg_key, "cached": pkg_cid is not None, "cid": pkg_cid or ""})

    return jsonify({"layers": results})


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
        # Find the index entry that has this CID
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
