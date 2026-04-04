"""Resumable workflow engine — break flash operations into discrete, resumable stages.

Each workflow is a sequence of stages (download, verify, flash, post-configure).
If a stage fails, the user can resume from that stage instead of restarting.
Stages are idempotent: skip download if cached, skip flash if already at target version.

Workflow state is persisted to ~/.osmosis/workflows/<id>.json so it survives
server restarts.
"""

import hashlib
import json
import logging
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path

from web.core import Task, start_task

log = logging.getLogger(__name__)

WORKFLOWS_DIR = Path.home() / ".osmosis" / "workflows"
DOWNLOADS_DIR = Path.home() / "Osmosis-downloads"


class StageStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StageState:
    """Persistent state for a single workflow stage."""

    id: str
    name: str
    status: str = StageStatus.PENDING
    started_at: float = 0.0
    completed_at: float = 0.0
    error: str = ""
    result: dict = field(default_factory=dict)


@dataclass
class WorkflowState:
    """Full workflow state — persisted to disk."""

    id: str
    device_id: str
    firmware_id: str = ""
    created_at: float = 0.0
    updated_at: float = 0.0
    status: str = "pending"  # pending, running, completed, failed, cancelled
    current_stage: str = ""
    stages: list[StageState] = field(default_factory=list)
    context: dict = field(default_factory=dict)  # shared data between stages


def _state_path(workflow_id: str) -> Path:
    return WORKFLOWS_DIR / f"{workflow_id}.json"


def save_state(state: WorkflowState) -> None:
    """Persist workflow state to disk."""
    WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)
    state.updated_at = time.time()
    data = asdict(state)
    _state_path(state.id).write_text(json.dumps(data, indent=2))


def load_state(workflow_id: str) -> WorkflowState | None:
    """Load workflow state from disk."""
    path = _state_path(workflow_id)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        stages = [StageState(**s) for s in data.pop("stages", [])]
        return WorkflowState(**data, stages=stages)
    except Exception as e:
        log.error("Failed to load workflow %s: %s", workflow_id, e)
        return None


def list_workflows() -> list[dict]:
    """List all workflows with summary info."""
    WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for f in sorted(WORKFLOWS_DIR.glob("*.json"), reverse=True):
        state = load_state(f.stem)
        if state:
            results.append(
                {
                    "id": state.id,
                    "device_id": state.device_id,
                    "firmware_id": state.firmware_id,
                    "status": state.status,
                    "current_stage": state.current_stage,
                    "created_at": state.created_at,
                    "updated_at": state.updated_at,
                    "stages": [
                        {"id": s.id, "name": s.name, "status": s.status}
                        for s in state.stages
                    ],
                }
            )
    return results


# ---------------------------------------------------------------------------
# Stage executors
# ---------------------------------------------------------------------------


def _stage_download(
    task: Task, state: WorkflowState, stage: StageState
) -> bool:
    """Download firmware, skipping if already cached and checksum matches."""
    url = state.context.get("url", "")
    ipfs_cid = state.context.get("ipfs_cid", "")
    dest = state.context.get("dest", "")
    expected_sha256 = state.context.get("expected_sha256", "")

    if not dest:
        codename = state.context.get("codename", state.device_id)
        filename = state.context.get("filename", "firmware.zip")
        dest = str(DOWNLOADS_DIR / codename / filename)
        state.context["dest"] = dest

    dest_path = Path(dest)

    # Idempotent: skip if cached and checksum matches
    if dest_path.exists() and expected_sha256:
        actual = hashlib.sha256(dest_path.read_bytes()).hexdigest()
        if actual == expected_sha256:
            task.emit(
                f"Firmware already cached and verified: {dest_path.name}",
                "success",
            )
            stage.result["sha256"] = actual
            stage.result["cached"] = True
            return True

    if dest_path.exists() and not expected_sha256:
        task.emit(
            f"Firmware already downloaded: {dest_path.name} (no checksum to verify)",
            "info",
        )
        actual = hashlib.sha256(dest_path.read_bytes()).hexdigest()
        stage.result["sha256"] = actual
        stage.result["cached"] = True
        return True

    dest_path.parent.mkdir(parents=True, exist_ok=True)

    # Try IPFS first
    if ipfs_cid:
        from web.ipfs_helpers import ipfs_available

        if ipfs_available():
            task.emit(f"Downloading from IPFS: {ipfs_cid[:24]}...")
            rc = task.run_shell(["ipfs", "get", "-o", dest, ipfs_cid])
            if rc == 0:
                stage.result["source"] = "ipfs"
                return True

    # Fall back to HTTP
    if not url:
        task.emit("No download URL or IPFS CID available.", "error")
        return False

    task.emit(f"Downloading: {url}")
    rc = task.run_shell(["wget", "--progress=dot:giga", "-O", dest, url])
    if rc != 0:
        task.emit("Download failed.", "error")
        dest_path.unlink(missing_ok=True)
        return False

    actual = hashlib.sha256(dest_path.read_bytes()).hexdigest()
    stage.result["sha256"] = actual
    stage.result["source"] = "http"
    return True


def _stage_verify(task: Task, state: WorkflowState, stage: StageState) -> bool:
    """Verify firmware integrity against registry and expected checksum."""
    dest = state.context.get("dest", "")
    if not dest or not Path(dest).exists():
        task.emit("No firmware file to verify.", "error")
        return False

    from web.ipfs_helpers import verify_fetched_file

    result = verify_fetched_file(dest)
    task.emit(f"SHA256: {result['sha256']}")

    expected = state.context.get("expected_sha256", "")
    if expected and result["sha256"] != expected:
        task.emit(
            f"Checksum mismatch! Expected {expected[:16]}..., got {result['sha256'][:16]}...",
            "error",
        )
        return False

    if result["known"]:
        task.emit("Integrity: matches a known-good firmware entry.", "success")
    else:
        task.emit(
            "Integrity: NOT in firmware registry. Verify manually before flashing.",
            "warn",
        )

    stage.result["sha256"] = result["sha256"]
    stage.result["registry_known"] = result["known"]
    state.context["verified_sha256"] = result["sha256"]
    return True


def _stage_backup(task: Task, state: WorkflowState, stage: StageState) -> bool:
    """Back up current device firmware before flashing."""
    task.emit("Checking for connected device...")

    import subprocess

    try:
        result = subprocess.run(
            ["adb", "devices"], capture_output=True, text=True, timeout=5
        )
        if "device" not in result.stdout:
            task.emit("No device connected via ADB. Skipping backup.", "warn")
            stage.status = StageStatus.SKIPPED
            return True
    except Exception:
        task.emit("ADB not available. Skipping backup.", "warn")
        stage.status = StageStatus.SKIPPED
        return True

    from datetime import datetime

    backup_dir = (
        Path.home()
        / ".osmosis"
        / "backups"
        / datetime.now().strftime("%Y%m%d-%H%M%S")
    )
    backup_dir.mkdir(parents=True, exist_ok=True)
    task.emit(f"Backup directory: {backup_dir}")

    for part in ["boot", "recovery"]:
        task.emit(f"Backing up {part}...")
        dest = backup_dir / f"{part}.img"
        rc = task.run_shell(
            ["adb", "pull", f"/dev/block/by-name/{part}", str(dest)]
        )
        if rc != 0:
            task.emit(f"Could not back up {part} (may need root).", "warn")

    state.context["backup_dir"] = str(backup_dir)
    stage.result["backup_dir"] = str(backup_dir)
    return True


def _stage_flash(task: Task, state: WorkflowState, stage: StageState) -> bool:
    """Flash firmware to the device."""
    dest = state.context.get("dest", "")
    flash_method = state.context.get("flash_method", "sideload")

    if not dest or not Path(dest).exists():
        task.emit("No firmware file to flash.", "error")
        return False

    if flash_method == "sideload":
        task.emit("Ensure device is in ADB sideload mode.", "warn")
        import time as _time

        _time.sleep(2)
        rc = task.run_shell(["adb", "sideload", dest])
    elif flash_method == "heimdall":
        task.emit("Ensure device is in Download Mode.", "warn")
        rc = task.run_shell(
            ["heimdall", "flash", "--RECOVERY", dest, "--no-reboot"]
        )
    elif flash_method == "fastboot":
        partition = state.context.get("partition", "system")
        task.emit("Ensure device is in fastboot mode.", "warn")
        rc = task.run_shell(["fastboot", "flash", partition, dest])
    else:
        task.emit(f"Unknown flash method: {flash_method}", "error")
        return False

    if rc == 0:
        task.emit("Flash complete!", "success")

        # Register in firmware registry
        try:
            from web.registry import register

            register(
                dest, flash_method=flash_method, component=state.firmware_id
            )
        except Exception:
            pass

    return rc == 0


def _stage_post_configure(
    task: Task, state: WorkflowState, stage: StageState
) -> bool:
    """Run post-flash configuration tasks."""
    task.emit("Running post-flash configuration...")

    post_tasks = state.context.get("post_flash_tasks", [])
    if not post_tasks:
        task.emit("No post-flash tasks configured. Done!", "success")
        return True

    for pt in post_tasks:
        task_type = pt.get("type", "shell")
        command = pt.get("command", "")
        name = pt.get("name", command)

        task.emit(f"Running: {name}")

        if task_type == "adb" and command:
            parts = command.split()
            rc = task.run_shell(parts)
        elif task_type == "shell" and command:
            rc = task.run_shell(["bash", "-c", command])
        else:
            task.emit(f"Unknown task type: {task_type}", "warn")
            continue

        if rc != 0:
            task.emit(f"Post-flash task failed: {name}", "error")
            return False

    task.emit("Post-flash configuration complete!", "success")
    return True


# Stage registry
STAGE_EXECUTORS = {
    "download": _stage_download,
    "verify": _stage_verify,
    "backup": _stage_backup,
    "flash": _stage_flash,
    "post-configure": _stage_post_configure,
}

DEFAULT_STAGES = [
    StageState(id="download", name="Download firmware"),
    StageState(id="verify", name="Verify integrity"),
    StageState(id="backup", name="Backup current firmware"),
    StageState(id="flash", name="Flash firmware"),
    StageState(id="post-configure", name="Post-flash setup"),
]

# ---------------------------------------------------------------------------
# Composed workflow templates
# ---------------------------------------------------------------------------

WORKFLOW_TEMPLATES: dict[str, list[StageState]] = {
    "flash-and-configure": [
        StageState(id="download", name="Download firmware"),
        StageState(id="verify", name="Verify integrity"),
        StageState(id="backup", name="Backup current firmware"),
        StageState(id="flash", name="Flash firmware"),
        StageState(id="post-configure", name="Post-flash setup"),
    ],
    "configure-only": [
        StageState(id="post-configure", name="Post-flash setup"),
    ],
    "verify-only": [
        StageState(id="download", name="Download firmware"),
        StageState(id="verify", name="Verify integrity"),
    ],
    "download-only": [
        StageState(id="download", name="Download firmware"),
        StageState(id="verify", name="Verify integrity"),
    ],
    "flash-only": [
        StageState(id="flash", name="Flash firmware"),
    ],
    "backup-and-flash": [
        StageState(id="backup", name="Backup current firmware"),
        StageState(id="flash", name="Flash firmware"),
    ],
}


def get_template(name: str) -> list[StageState] | None:
    """Get a workflow template by name. Returns a fresh copy of stages."""
    template = WORKFLOW_TEMPLATES.get(name)
    if not template:
        return None
    return [StageState(id=s.id, name=s.name) for s in template]


def list_templates() -> list[dict]:
    """List all available workflow templates."""
    return [
        {
            "id": name,
            "stages": [{"id": s.id, "name": s.name} for s in stages],
            "stage_count": len(stages),
        }
        for name, stages in WORKFLOW_TEMPLATES.items()
    ]


# ---------------------------------------------------------------------------
# Workflow execution
# ---------------------------------------------------------------------------


def create_workflow(
    device_id: str,
    firmware_id: str = "",
    context: dict | None = None,
    stages: list[StageState] | None = None,
) -> WorkflowState:
    """Create a new workflow and persist it."""
    import uuid

    workflow_id = str(uuid.uuid4())[:8]
    state = WorkflowState(
        id=workflow_id,
        device_id=device_id,
        firmware_id=firmware_id,
        created_at=time.time(),
        stages=stages
        or [StageState(id=s.id, name=s.name) for s in DEFAULT_STAGES],
        context=context or {},
    )
    save_state(state)
    return state


def run_workflow(workflow_id: str, resume_from: str | None = None) -> str:
    """Run a workflow (or resume from a specific stage). Returns a task_id."""
    state = load_state(workflow_id)
    if not state:
        raise ValueError(f"Workflow {workflow_id} not found")

    def _run(task: Task):
        state.status = "running"
        save_state(state)

        # Find the starting stage
        start_idx = 0
        if resume_from:
            for i, stage in enumerate(state.stages):
                if stage.id == resume_from:
                    start_idx = i
                    break

        task.emit(f"Workflow {state.id}: {state.device_id}", "info")
        if resume_from:
            task.emit(f"Resuming from stage: {resume_from}", "info")
        task.emit("")

        for i, stage in enumerate(state.stages):
            if i < start_idx:
                continue

            # Skip already completed stages (unless resuming from them)
            if (
                stage.status == StageStatus.COMPLETED
                and stage.id != resume_from
            ):
                task.emit(
                    f"[{stage.name}] Already completed, skipping.", "info"
                )
                continue

            executor = STAGE_EXECUTORS.get(stage.id)
            if not executor:
                task.emit(
                    f"[{stage.name}] No executor found, skipping.", "warn"
                )
                stage.status = StageStatus.SKIPPED
                save_state(state)
                continue

            task.emit(f"=== {stage.name} ===", "info")
            stage.status = StageStatus.IN_PROGRESS
            stage.started_at = time.time()
            state.current_stage = stage.id
            save_state(state)

            try:
                success = executor(task, state, stage)
            except Exception as e:
                task.emit(f"Stage error: {e}", "error")
                success = False
                stage.error = str(e)

            stage.completed_at = time.time()

            if success:
                if stage.status != StageStatus.SKIPPED:
                    stage.status = StageStatus.COMPLETED
                task.emit(f"[{stage.name}] Done.", "success")
            else:
                stage.status = StageStatus.FAILED
                state.status = "failed"
                save_state(state)
                task.emit("")
                task.emit(f"Workflow paused at stage: {stage.name}", "warn")
                task.emit(
                    f"Resume with: POST /api/workflows/{state.id}/resume?from={stage.id}",
                    "info",
                )
                task.done(False)
                return

            save_state(state)
            task.emit("")

        state.status = "completed"
        state.current_stage = ""
        save_state(state)
        task.emit("Workflow completed successfully!", "success")
        task.done(True)

    task_id = start_task(_run)
    return task_id
