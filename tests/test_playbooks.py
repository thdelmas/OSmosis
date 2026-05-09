"""Tests for the post-flash configuration engine (Phase 12.3).

Covers the ansible_runner module (resolution, inventory generation, missing
binary handling) and the /api/playbooks routes (list, upload, validate,
delete, run). The actual ansible-playbook subprocess is stubbed — these
tests do not require Ansible to be installed.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web import ansible_runner
from web.app import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(ansible_runner, "USER_PLAYBOOKS_DIR", tmp_path / "user-pb")
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def isolate_user_dir(tmp_path, monkeypatch):
    """For runner tests that don't need the Flask client."""
    user_dir = tmp_path / "user-pb"
    monkeypatch.setattr(ansible_runner, "USER_PLAYBOOKS_DIR", user_dir)
    return user_dir


# ---- runner ------------------------------------------------------------


def test_resolve_builtin_by_id(isolate_user_dir):
    p = ansible_runner.resolve_playbook("hardening")
    assert p is not None
    assert p.name == "hardening.yml"
    assert "playbooks" in p.parts


def test_resolve_unknown_returns_none(isolate_user_dir):
    assert ansible_runner.resolve_playbook("nope-not-real") is None


def test_resolve_user_playbook(isolate_user_dir):
    isolate_user_dir.mkdir(parents=True)
    custom = isolate_user_dir / "my-pb.yml"
    custom.write_text("- hosts: all\n")
    assert ansible_runner.resolve_playbook("my-pb") == custom


def test_list_builtin_playbooks_present(isolate_user_dir):
    entries = ansible_runner.list_builtin_playbooks()
    ids = {e["id"] for e in entries}
    # The five playbooks shipped with Phase 12.3
    assert {"network", "locale", "packages", "ssh-keys", "hardening"} <= ids
    for e in entries:
        assert e["source"] == "builtin"
        assert e["path"].endswith(".yml")


class _StubTask:
    """Records commands and snapshots the inventory file at run_shell time.

    The runner uses a TemporaryDirectory that's cleaned up on return, so we
    have to read the inventory while the command is "running."
    """

    def __init__(self):
        self.events = []
        self.cmds = []
        self.inventories = []
        self.return_code = 0

    def emit(self, msg, level="info"):
        self.events.append((level, msg))

    def run_shell(self, cmd, sudo=False):
        self.cmds.append(cmd)
        if "-i" in cmd:
            inv_path = Path(cmd[cmd.index("-i") + 1])
            if inv_path.exists():
                self.inventories.append(inv_path.read_text())
        return self.return_code


def test_run_playbook_missing_binary(monkeypatch, isolate_user_dir):
    monkeypatch.setattr(ansible_runner.shutil, "which", lambda _b: None)
    task = _StubTask()
    rc = ansible_runner.run_playbook(task, playbook="hardening", host="1.2.3.4")
    assert rc == 127
    assert any("__error_type:ansible_missing" in m for _, m in task.events)


def test_run_playbook_unknown(monkeypatch, isolate_user_dir):
    monkeypatch.setattr(
        ansible_runner.shutil, "which", lambda _b: "/usr/bin/ansible-playbook"
    )
    task = _StubTask()
    rc = ansible_runner.run_playbook(
        task, playbook="not-a-real-playbook", host="1.2.3.4"
    )
    assert rc == 2


def test_run_playbook_requires_host(monkeypatch, isolate_user_dir):
    monkeypatch.setattr(
        ansible_runner.shutil, "which", lambda _b: "/usr/bin/ansible-playbook"
    )
    task = _StubTask()
    rc = ansible_runner.run_playbook(task, playbook="hardening", host="")
    assert rc == 2
    assert any("No target host" in m for _, m in task.events)


def test_run_playbook_local_defaults_host(monkeypatch, isolate_user_dir):
    monkeypatch.setattr(
        ansible_runner.shutil, "which", lambda _b: "/usr/bin/ansible-playbook"
    )
    task = _StubTask()
    rc = ansible_runner.run_playbook(
        task, playbook="hardening", connection="local"
    )
    assert rc == 0
    assert task.cmds, "expected ansible-playbook to be invoked"
    cmd = task.cmds[0]
    assert cmd[0] == "ansible-playbook"
    assert task.inventories
    assert "localhost" in task.inventories[0]
    assert "ansible_connection=local" in task.inventories[0]


def test_run_playbook_passes_extra_vars(monkeypatch, isolate_user_dir):
    monkeypatch.setattr(
        ansible_runner.shutil, "which", lambda _b: "/usr/bin/ansible-playbook"
    )
    task = _StubTask()
    ansible_runner.run_playbook(
        task,
        playbook="locale",
        host="10.0.0.1",
        become=True,
        extra_vars={"locale": "fr_FR.UTF-8"},
    )
    cmd = task.cmds[0]
    assert "--become" in cmd
    assert "--extra-vars" in cmd
    extra_idx = cmd.index("--extra-vars") + 1
    assert "fr_FR.UTF-8" in cmd[extra_idx]


# ---- routes ------------------------------------------------------------


def test_list_route_returns_builtin(client):
    resp = client.get("/api/playbooks")
    assert resp.status_code == 200
    body = resp.get_json()
    assert isinstance(body["builtin"], list)
    ids = {p["id"] for p in body["builtin"]}
    assert "hardening" in ids


def test_upload_rejects_bad_id(client):
    resp = client.post(
        "/api/playbooks/upload",
        json={"id": "../etc/passwd", "content": "- hosts: all\n"},
    )
    assert resp.status_code == 400


def test_upload_rejects_invalid_yaml(client):
    resp = client.post(
        "/api/playbooks/upload",
        json={"id": "broken", "content": "not: [valid"},
    )
    assert resp.status_code == 400


def test_upload_rejects_non_playbook_shape(client):
    resp = client.post(
        "/api/playbooks/upload",
        json={"id": "nopb", "content": "just_a_mapping: true"},
    )
    assert resp.status_code == 400


def test_upload_then_list_and_delete(client):
    resp = client.post(
        "/api/playbooks/upload",
        json={
            "id": "my-test-pb",
            "content": "- hosts: osmosis\n  tasks: []\n",
        },
    )
    assert resp.status_code == 201

    listed = client.get("/api/playbooks").get_json()
    user_ids = {p["id"] for p in listed["user"]}
    assert "my-test-pb" in user_ids

    resp = client.delete("/api/playbooks/my-test-pb")
    assert resp.status_code == 200
    listed = client.get("/api/playbooks").get_json()
    assert "my-test-pb" not in {p["id"] for p in listed["user"]}


def test_delete_unknown_404(client):
    resp = client.delete("/api/playbooks/never-existed")
    assert resp.status_code == 404


def test_run_route_validates_inputs(client):
    # missing playbook
    assert client.post("/api/playbooks/run", json={}).status_code == 400
    # missing host with ssh
    resp = client.post(
        "/api/playbooks/run",
        json={"playbook": "hardening"},
    )
    assert resp.status_code == 400
    # unknown playbook
    resp = client.post(
        "/api/playbooks/run",
        json={"playbook": "no-such", "host": "1.1.1.1"},
    )
    assert resp.status_code == 404
    # bad extra_vars
    resp = client.post(
        "/api/playbooks/run",
        json={
            "playbook": "hardening",
            "host": "1.1.1.1",
            "extra_vars": "not-an-object",
        },
    )
    assert resp.status_code == 400


def test_run_route_starts_task(client, monkeypatch):
    """Stub run_playbook so the test doesn't shell out to ansible."""
    calls = []

    def fake_run(task, **kw):
        calls.append(kw)
        return 0

    monkeypatch.setattr("web.routes.playbooks.run_playbook", fake_run)
    resp = client.post(
        "/api/playbooks/run",
        json={
            "playbook": "hardening",
            "host": "192.168.1.50",
            "user": "pi",
            "become": True,
        },
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert "task_id" in body

    # The background thread should have been spawned and called fake_run.
    # Wait briefly for it.
    import time

    deadline = time.time() + 2
    while not calls and time.time() < deadline:
        time.sleep(0.05)
    assert calls, "run_playbook was not invoked"
    assert calls[0]["playbook"] == "hardening"
    assert calls[0]["host"] == "192.168.1.50"
    assert calls[0]["user"] == "pi"
    assert calls[0]["become"] is True


# ---- workflow integration ---------------------------------------------


def test_post_configure_dispatches_ansible(monkeypatch):
    """The post-configure stage should hand ansible tasks to run_playbook
    instead of trying to bash-exec them.
    """
    from web.workflow_engine import (
        StageState,
        WorkflowState,
        _stage_post_configure,
    )

    captured = {}

    def fake_run(task, **kw):
        captured.update(kw)
        return 0

    monkeypatch.setattr("web.ansible_runner.run_playbook", fake_run)

    state = WorkflowState(
        id="wf-test",
        device_id="testdev",
        context={
            "post_flash_tasks": [
                {
                    "id": "harden",
                    "name": "Harden",
                    "type": "ansible",
                    "playbook": "hardening",
                }
            ],
            "device_ip": "10.0.0.42",
            "device_user": "pi",
            "ansible_become": True,
        },
        stages=[],
    )
    stage = StageState(id="post-configure", name="Post-configure")
    task = _StubTask()
    ok = _stage_post_configure(task, state, stage)
    assert ok
    assert captured["playbook"] == "hardening"
    assert captured["host"] == "10.0.0.42"
    assert captured["user"] == "pi"
    assert captured["become"] is True
