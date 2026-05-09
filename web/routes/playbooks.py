"""API routes for the post-flash configuration engine (Phase 12.3).

Lists built-in and user playbooks, accepts custom uploads, and runs them
against a target host. Uploads are stored under ``~/.osmosis/playbooks/``
and validated for shape (must parse as YAML, must look like an Ansible
playbook) before being persisted.
"""

import re

from flask import Blueprint, jsonify, request

from web import ansible_runner
from web.ansible_runner import (
    list_builtin_playbooks,
    list_user_playbooks,
    resolve_playbook,
    run_playbook,
)
from web.core import start_task

bp = Blueprint("playbooks", __name__)

_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


@bp.route("/api/playbooks")
def api_list_playbooks():
    """List every playbook the engine can run."""
    return jsonify(
        {
            "builtin": list_builtin_playbooks(),
            "user": list_user_playbooks(),
        }
    )


@bp.route("/api/playbooks/upload", methods=["POST"])
def api_upload_playbook():
    """Save a user-supplied playbook under ``~/.osmosis/playbooks/<id>.yml``.

    Accepts JSON: ``{"id": "<safe-name>", "content": "<yaml text>"}``.
    The id is restricted to ``[A-Za-z0-9_-]`` so it can be embedded in URLs
    and filesystem paths without quoting.
    """
    data = request.get_json(silent=True) or {}
    pid = (data.get("id") or "").strip()
    content = data.get("content") or ""

    if not _SAFE_ID.match(pid):
        return jsonify(
            {"error": "id must match [A-Za-z0-9][A-Za-z0-9_-]{0,63}"}
        ), 400
    if not content.strip():
        return jsonify({"error": "content is required"}), 400

    # Validate as YAML and as a playbook (list of plays with hosts/tasks)
    try:
        import yaml

        parsed = yaml.safe_load(content)
    except yaml.YAMLError as e:
        return jsonify({"error": f"invalid YAML: {e}"}), 400

    if not isinstance(parsed, list) or not parsed:
        return jsonify(
            {"error": "playbook must be a non-empty YAML list of plays"}
        ), 400
    for play in parsed:
        if not isinstance(play, dict) or "hosts" not in play:
            return jsonify(
                {"error": "every play must be a mapping with a 'hosts' key"}
            ), 400

    ansible_runner.USER_PLAYBOOKS_DIR.mkdir(parents=True, exist_ok=True)
    dest = ansible_runner.USER_PLAYBOOKS_DIR / f"{pid}.yml"
    dest.write_text(content)
    return jsonify({"id": pid, "path": str(dest)}), 201


@bp.route("/api/playbooks/<pid>", methods=["DELETE"])
def api_delete_playbook(pid: str):
    """Delete a user-uploaded playbook. Built-ins are not deletable."""
    if not _SAFE_ID.match(pid):
        return jsonify({"error": "invalid id"}), 400
    target = ansible_runner.USER_PLAYBOOKS_DIR / f"{pid}.yml"
    if not target.exists():
        return jsonify({"error": "not found"}), 404
    target.unlink()
    return jsonify({"deleted": pid})


@bp.route("/api/playbooks/run", methods=["POST"])
def api_run_playbook():
    """Run a playbook against a target host. Returns ``{task_id}``.

    Body: ``{playbook, host, user?, connection?, become?, extra_vars?}``.
    The frontend then streams ``/api/tasks/<id>/stream`` like any workflow.
    """
    data = request.get_json(silent=True) or {}
    playbook = data.get("playbook") or ""
    host = data.get("host") or ""
    connection = data.get("connection") or "ssh"

    if not playbook:
        return jsonify({"error": "playbook is required"}), 400
    if resolve_playbook(playbook) is None:
        return jsonify({"error": f"unknown playbook: {playbook}"}), 404
    if connection != "local" and not host:
        return jsonify(
            {"error": "host is required when connection is not 'local'"}
        ), 400

    user = data.get("user") or "root"
    become = bool(data.get("become", False))
    extra_vars = data.get("extra_vars") or None
    if extra_vars is not None and not isinstance(extra_vars, dict):
        return jsonify({"error": "extra_vars must be an object"}), 400

    def _run(task):
        rc = run_playbook(
            task,
            playbook=playbook,
            host=host,
            user=user,
            connection=connection,
            become=become,
            extra_vars=extra_vars,
        )
        task.done(rc == 0)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})
