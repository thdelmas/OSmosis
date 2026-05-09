"""Run Ansible playbooks against a freshly-flashed device (Phase 12.3).

Generates an ephemeral inventory file, then shells out to ``ansible-playbook``
through a :class:`web.core.Task` so output streams to the workflow log just
like any other stage.

Connection details come from the workflow context — typically populated by
the device profile and the inventory module:

- ``device_ip`` / ``device_host`` — target host (required for SSH)
- ``device_user`` — SSH user (default: ``root``)
- ``ansible_connection`` — ``ssh`` (default), ``local``, or ``adb``
- ``ansible_become`` — bool, whether to use sudo on the target
- ``ansible_extra_vars`` — dict, passed as ``--extra-vars``

Built-in playbooks live under ``playbooks/`` and are referenced by the file
stem (e.g. ``"hardening"`` resolves to ``playbooks/hardening.yml``). Custom
playbooks can be uploaded — the routes layer stores them under
``~/.osmosis/playbooks/`` and passes the absolute path through.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from web.core import Task

# Bundled playbooks ship inside the repo
BUILTIN_PLAYBOOKS_DIR = Path(__file__).resolve().parent.parent / "playbooks"

# User-uploaded playbooks live under the OSmosis state dir
USER_PLAYBOOKS_DIR = Path.home() / ".osmosis" / "playbooks"


def list_builtin_playbooks() -> list[dict]:
    """Return metadata for every bundled playbook.

    Each entry has ``id`` (filename stem), ``name`` (human title from the
    play's ``name:`` field), ``description``, and ``path``. Used by the UI
    gallery and the API.
    """
    if not BUILTIN_PLAYBOOKS_DIR.exists():
        return []

    entries = []
    for path in sorted(BUILTIN_PLAYBOOKS_DIR.glob("*.yml")):
        entries.append(_describe_playbook(path, source="builtin"))
    return entries


def list_user_playbooks() -> list[dict]:
    """Return metadata for every uploaded playbook."""
    if not USER_PLAYBOOKS_DIR.exists():
        return []
    return [
        _describe_playbook(p, source="user")
        for p in sorted(USER_PLAYBOOKS_DIR.glob("*.yml"))
    ]


def _describe_playbook(path: Path, *, source: str) -> dict:
    """Pull a name + description out of a playbook header without yaml."""
    name = path.stem.replace("-", " ").replace("_", " ").title()
    description = ""
    try:
        text = path.read_text()
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("# description:"):
                description = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("- name:") and not name.startswith(
                stripped.split(":", 1)[1].strip()
            ):
                name = stripped.split(":", 1)[1].strip().strip('"').strip("'")
                break
    except OSError:
        pass
    return {
        "id": path.stem,
        "name": name,
        "description": description,
        "path": str(path),
        "source": source,
    }


def resolve_playbook(playbook: str) -> Path | None:
    """Resolve a playbook id or path to an absolute path.

    Lookup order:
      1. Absolute path that exists on disk
      2. Relative path under the OSmosis tree
      3. ``<id>.yml`` under user playbooks
      4. ``<id>.yml`` under built-in playbooks
    """
    if not playbook:
        return None

    p = Path(playbook)
    if p.is_absolute() and p.exists():
        return p

    repo_root = Path(__file__).resolve().parent.parent
    rel = repo_root / playbook
    if rel.exists() and rel.is_file():
        return rel

    stem = p.stem if p.suffix else p.name
    user = USER_PLAYBOOKS_DIR / f"{stem}.yml"
    if user.exists():
        return user

    builtin = BUILTIN_PLAYBOOKS_DIR / f"{stem}.yml"
    if builtin.exists():
        return builtin

    return None


def _write_inventory(
    tmp_dir: Path,
    *,
    host: str,
    connection: str,
    user: str,
    extra_host_vars: dict | None = None,
) -> Path:
    """Write an INI-style inventory file under ``tmp_dir``.

    A single host is added under the ``[osmosis]`` group with connection
    variables inlined — this is enough for every built-in playbook.
    """
    inv = tmp_dir / "inventory.ini"
    parts = [
        host,
        f"ansible_connection={connection}",
        f"ansible_user={user}",
        # Strip strict host-key checking for first-boot scenarios where the
        # device's host key has just been generated.
        "ansible_ssh_common_args='-o StrictHostKeyChecking=no "
        "-o UserKnownHostsFile=/dev/null'",
    ]
    if extra_host_vars:
        for k, v in extra_host_vars.items():
            parts.append(f"{k}={v}")
    inv.write_text("[osmosis]\n" + " ".join(parts) + "\n")
    return inv


def run_playbook(
    task: Task,
    *,
    playbook: str,
    host: str = "",
    user: str = "root",
    connection: str = "ssh",
    become: bool = False,
    extra_vars: dict | None = None,
) -> int:
    """Run an Ansible playbook against a device. Returns the exit code.

    Emits a typed error marker (``__error_type:ansible_missing``) when
    ``ansible-playbook`` is not on PATH so the frontend can offer the right
    install hint.
    """
    if not shutil.which("ansible-playbook"):
        task.emit("__error_type:ansible_missing", "error")
        task.emit(
            "ansible-playbook not found. Install ansible "
            "(e.g. `sudo apt install ansible` or `pip install ansible`).",
            "error",
        )
        return 127

    resolved = resolve_playbook(playbook)
    if resolved is None:
        task.emit(f"Playbook not found: {playbook}", "error")
        return 2

    if connection == "local":
        host = host or "localhost"
    elif not host:
        task.emit(
            "No target host provided. Set device_ip in the workflow context "
            "or use connection=local.",
            "error",
        )
        return 2

    with tempfile.TemporaryDirectory(prefix="osmosis-ansible-") as td:
        tmp = Path(td)
        inv = _write_inventory(tmp, host=host, connection=connection, user=user)
        cmd = [
            "ansible-playbook",
            "-i",
            str(inv),
            str(resolved),
        ]
        if become:
            cmd.append("--become")
        if extra_vars:
            cmd.extend(["--extra-vars", json.dumps(extra_vars)])

        task.emit(
            f"Running playbook: {resolved.name} on {host} ({connection})"
        )
        return task.run_shell(cmd)
