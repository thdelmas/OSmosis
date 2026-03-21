"""OS Builder routes — build custom OS images from the web UI."""

import json
from pathlib import Path

from flask import Blueprint, jsonify, request

from web.core import Task, start_task
from web.ipfs_helpers import ipfs_add, ipfs_available, ipfs_index_load, ipfs_index_save
from web.os_builder import (
    BUILD_DIR,
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
    return jsonify({
        "bases": {k: {kk: vv for kk, vv in v.items()} for k, v in SUPPORTED_BASES.items()},
        "init_systems": INIT_SYSTEMS,
        "desktops": DESKTOP_ENVIRONMENTS,
        "output_formats": OUTPUT_FORMATS,
        "target_devices": TARGET_DEVICES,
    })


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
        return jsonify({
            "type": "preseed",
            "filename": "preseed.cfg",
            "content": generate_preseed(profile),
        })
    elif profile.base == "arch":
        return jsonify({
            "type": "pacstrap-script",
            "filename": "install.sh",
            "content": generate_pacstrap_script(profile),
        })
    elif profile.base == "alpine":
        return jsonify({
            "type": "alpine-answers",
            "filename": "answers",
            "content": generate_alpine_answers(profile),
        })
    elif profile.base == "fedora":
        return jsonify({
            "type": "kickstart",
            "filename": "kickstart.cfg",
            "content": generate_kickstart(profile),
        })
    elif profile.base == "nixos":
        return jsonify({
            "type": "nix-config",
            "filename": "configuration.nix",
            "content": generate_nix_config(profile),
        })
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

    import datetime

    task.emit("")
    task.emit(f"Publishing to IPFS: {out_path.name}...", "info")
    cid = ipfs_add(str(out_path))
    if not cid:
        task.emit("Failed to pin to IPFS.", "error")
        return

    task.emit(f"IPFS CID: {cid}", "success")
    task.emit(f"Gateway: https://ipfs.io/ipfs/{cid}")

    # Record in the IPFS index
    index = ipfs_index_load()
    key = f"os-build/{output_name}{ext}"
    index[key] = {
        "cid": cid,
        "size": out_path.stat().st_size,
        "filename": out_path.name,
        "codename": f"os-build-{profile.base}",
        "rom_id": "",
        "rom_name": f"{profile.name} ({profile.base} {profile.suite} {profile.arch})",
        "version": profile.suite,
        "pinned_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "build_profile": profile.to_dict(),
    }
    ipfs_index_save(index)
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
            builds.append({
                "filename": f.name,
                "path": str(f),
                "size_mb": round(f.stat().st_size / (1024 * 1024), 1),
                "profile": profile_data,
            })
    return jsonify(builds)
