"""OS Builder routes — build custom OS images from the web UI."""

import json

from flask import Blueprint, jsonify, request

from web.core import Task, start_task
from web.os_builder import (
    AGENT_OS_TEMPLATES,
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
from web.routes.os_builder_ipfs import ipfs_publish_build

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
            "agent_templates": {
                k: {
                    "id": v["id"],
                    "label": v["label"],
                    "description": v["description"],
                    "defaults": v["defaults"],
                }
                for k, v in AGENT_OS_TEMPLATES.items()
            },
        }
    )


@bp.route("/api/os-builder/templates")
def api_os_builder_templates():
    """List available agent OS templates."""
    return jsonify(
        [
            {
                "id": v["id"],
                "label": v["label"],
                "description": v["description"],
                "defaults": v["defaults"],
                "system_packages": v.get("system_packages", []),
                "pip_packages": v.get("pip_packages", []),
            }
            for v in AGENT_OS_TEMPLATES.values()
        ]
    )


@bp.route("/api/os-builder/templates/<template_id>")
def api_os_builder_template_detail(template_id: str):
    """Get full details for an agent OS template."""
    tmpl = AGENT_OS_TEMPLATES.get(template_id)
    if not tmpl:
        return jsonify({"error": f"Unknown template: {template_id}"}), 404
    return jsonify(
        {
            "id": tmpl["id"],
            "label": tmpl["label"],
            "description": tmpl["description"],
            "defaults": tmpl["defaults"],
            "system_packages": tmpl.get("system_packages", []),
            "pip_packages": tmpl.get("pip_packages", []),
            "kiosk_packages": tmpl.get("kiosk_packages", []),
            "services": {k: v["description"] for k, v in tmpl.get("services", {}).items()},
        }
    )


@bp.route("/api/os-builder/templates/<template_id>/build", methods=["POST"])
def api_os_builder_template_build(template_id: str):
    """Build an OS image from an agent template with optional overrides.

    JSON body: optional BuildProfile overrides (target_device, arch, etc.).
    The template's defaults are applied first, then overrides.
    """
    tmpl = AGENT_OS_TEMPLATES.get(template_id)
    if not tmpl:
        return jsonify({"error": f"Unknown template: {template_id}"}), 404

    body = request.json or {}
    ipfs_publish = body.pop("ipfs_publish", False)

    # Start from template defaults, apply user overrides
    profile_data = dict(tmpl["defaults"])
    profile_data.update({k: v for k, v in body.items() if k in BuildProfile.__dataclass_fields__})
    profile_data["agent_template"] = template_id

    try:
        profile = BuildProfile.from_dict(profile_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    def _run(task: Task):
        build_os(task, profile)
        if task.status == "done" and ipfs_publish:
            ipfs_publish_build(task, profile)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id, "profile": profile.to_dict()})


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
        if task.status == "done" and ipfs_publish:
            ipfs_publish_build(task, profile)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


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
