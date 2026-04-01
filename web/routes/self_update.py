"""Self-update routes: check for and apply OSmosis updates."""

import subprocess
from pathlib import Path

from flask import Blueprint, jsonify

from web.core import Task, start_task

bp = Blueprint("self_update", __name__)

REPO_DIR = Path(__file__).resolve().parent.parent.parent


@bp.route("/api/update/check")
def api_update_check():
    """Check if a newer version is available on the remote."""
    try:
        subprocess.run(
            ["git", "fetch", "--quiet"],
            cwd=str(REPO_DIR),
            capture_output=True,
            timeout=15,
        )
        local = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(REPO_DIR),
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
        remote = subprocess.run(
            ["git", "rev-parse", "origin/main"],
            cwd=str(REPO_DIR),
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
        behind = subprocess.run(
            ["git", "rev-list", "--count", f"{local}..{remote}"],
            cwd=str(REPO_DIR),
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
        return jsonify(
            {
                "update_available": local != remote,
                "local": local[:8],
                "remote": remote[:8],
                "behind": int(behind) if behind.isdigit() else 0,
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/update/apply", methods=["POST"])
def api_update_apply():
    """Pull latest code, reinstall deps, and rebuild frontend."""

    def _run(task: Task):
        task.progress(1, 4, "Pulling latest code")
        rc = task.run_shell(["git", "pull", "--ff-only"], sudo=False)
        if rc != 0:
            task.emit("Git pull failed. You may have local changes.", "error")
            task.done(False)
            return

        task.progress(2, 4, "Installing Python dependencies")
        task.run_shell(
            [str(REPO_DIR / ".venv" / "bin" / "pip"), "install", "-q", "-r", "requirements.txt"],
            sudo=False,
        )

        task.progress(3, 4, "Installing frontend dependencies")
        task.run_shell(["npm", "install"], sudo=False)

        task.progress(4, 4, "Rebuilding frontend")
        task.run_shell(["npm", "run", "build"], sudo=False)

        task.emit("Update complete. Restart OSmosis to apply.", "success")
        task.done()

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})
