"""API routes for declarative device profiles and the resumable workflow engine."""

from flask import Blueprint, jsonify, request

from web.device_profile import get_profile, load_all_profiles, profile_to_dict
from web.profile_migration import migrate_all, validate_all_profiles
from web.workflow_engine import (
    create_workflow,
    get_template,
    list_templates,
    list_workflows,
    load_state,
    run_workflow,
)

bp = Blueprint("profiles", __name__)


# ---------------------------------------------------------------------------
# Device profiles
# ---------------------------------------------------------------------------


@bp.route("/api/profiles")
def api_profiles():
    """List all declarative device profiles."""
    profiles = load_all_profiles()
    return jsonify([profile_to_dict(p) for p in profiles])


@bp.route("/api/profiles/<device_id>")
def api_profile(device_id):
    """Get a single device profile by ID."""
    profile = get_profile(device_id)
    if not profile:
        return jsonify({"error": "Profile not found"}), 404
    return jsonify(profile_to_dict(profile))


@bp.route("/api/profiles/validate")
def api_profiles_validate():
    """Validate all device profiles. Returns errors grouped by file."""
    errors = validate_all_profiles()
    return jsonify(
        {
            "valid": len(errors) == 0,
            "errors": errors,
            "profiles_checked": len(load_all_profiles()) + len(errors),
        }
    )


@bp.route("/api/profiles/migrate", methods=["POST"])
def api_profiles_migrate():
    """Migrate legacy .cfg files to declarative YAML profiles."""
    results = migrate_all()
    if not results:
        return jsonify(
            {
                "message": "Nothing to migrate (profiles already exist or no .cfg files found)"
            }
        )

    total = sum(len(v) for v in results.values())
    return jsonify(
        {
            "migrated": results,
            "total_created": total,
        }
    )


@bp.route("/api/profiles/search")
def api_profiles_search():
    """Search profiles by category, brand, or name."""
    q = request.args.get("q", "").lower().strip()
    category = request.args.get("category", "").lower().strip()

    if not q and not category:
        return jsonify([])

    profiles = load_all_profiles()
    results = []
    for p in profiles:
        if category and p.category.lower() != category:
            continue
        if q:
            haystack = (
                f"{p.name} {p.brand} {p.model} {p.codename} {p.id}".lower()
            )
            if q not in haystack:
                continue
        results.append(profile_to_dict(p))

    return jsonify(results)


# ---------------------------------------------------------------------------
# Resumable workflows
# ---------------------------------------------------------------------------


@bp.route("/api/workflows/templates")
def api_workflow_templates():
    """List all available workflow templates."""
    return jsonify(list_templates())


@bp.route("/api/workflows")
def api_workflows():
    """List all workflows with status summary."""
    return jsonify(list_workflows())


@bp.route("/api/workflows/<workflow_id>")
def api_workflow_status(workflow_id):
    """Get detailed status of a specific workflow."""
    state = load_state(workflow_id)
    if not state:
        return jsonify({"error": "Workflow not found"}), 404

    from dataclasses import asdict

    return jsonify(asdict(state))


@bp.route("/api/workflows", methods=["POST"])
def api_workflow_create():
    """Create and start a new flash workflow.

    JSON body: {
        "device_id": "sm-t805",
        "firmware_id": "lineageos",
        "template": "flash-and-configure",  // optional, defaults to full workflow
        "url": "https://...",
        "ipfs_cid": "",
        "filename": "lineage-18.1.zip",
        "flash_method": "sideload",
        "expected_sha256": ""
    }
    """
    data = request.json or {}
    device_id = data.get("device_id", "")
    if not device_id:
        return jsonify({"error": "device_id is required"}), 400

    firmware_id = data.get("firmware_id", "")
    context = {
        "url": data.get("url", ""),
        "ipfs_cid": data.get("ipfs_cid", ""),
        "filename": data.get("filename", "firmware.zip"),
        "codename": data.get("codename", device_id),
        "flash_method": data.get("flash_method", "sideload"),
        "expected_sha256": data.get("expected_sha256", ""),
    }

    # If a device profile exists, enrich context from it
    profile = get_profile(device_id)
    if profile:
        if not context["flash_method"]:
            context["flash_method"] = profile.flash_method or "sideload"
        # Find selected firmware source
        for fw in profile.firmware:
            if fw.id == firmware_id:
                if not context["url"]:
                    context["url"] = fw.url
                if not context["ipfs_cid"]:
                    context["ipfs_cid"] = fw.ipfs_cid
                if not context["expected_sha256"]:
                    context["expected_sha256"] = fw.sha256
                if not context["filename"]:
                    context["filename"] = f"{device_id}-{fw.id}.zip"
                break
        # Include post-flash tasks from profile
        if profile.post_flash:
            from dataclasses import asdict

            context["post_flash_tasks"] = [
                asdict(pt) for pt in profile.post_flash
            ]

    # Select workflow template
    template_name = data.get("template", "")
    stages = None
    if template_name:
        stages = get_template(template_name)
        if stages is None:
            return jsonify({"error": f"Unknown template: {template_name}"}), 400

    state = create_workflow(
        device_id, firmware_id=firmware_id, context=context, stages=stages
    )
    task_id = run_workflow(state.id)

    return jsonify({"workflow_id": state.id, "task_id": task_id})


@bp.route("/api/workflows/<workflow_id>/resume", methods=["POST"])
def api_workflow_resume(workflow_id):
    """Resume a failed or paused workflow from a specific stage.

    Query param: ?from=stage_id (e.g. ?from=flash)
    If omitted, resumes from the first non-completed stage.
    """
    state = load_state(workflow_id)
    if not state:
        return jsonify({"error": "Workflow not found"}), 404

    resume_from = request.args.get("from", "")
    if not resume_from:
        # Find first non-completed stage
        for stage in state.stages:
            if stage.status not in ("completed", "skipped"):
                resume_from = stage.id
                break

    if not resume_from:
        return jsonify({"error": "All stages already completed"}), 400

    task_id = run_workflow(workflow_id, resume_from=resume_from)
    return jsonify(
        {
            "workflow_id": workflow_id,
            "task_id": task_id,
            "resuming_from": resume_from,
        }
    )


@bp.route("/api/workflows/<workflow_id>", methods=["DELETE"])
def api_workflow_delete(workflow_id):
    """Delete a workflow's state."""
    from web.workflow_engine import _state_path

    path = _state_path(workflow_id)
    if not path.exists():
        return jsonify({"error": "Workflow not found"}), 404
    path.unlink()
    return jsonify({"deleted": workflow_id})
