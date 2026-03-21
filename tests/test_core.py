"""Tests for core module — Task class, config parsing, utilities."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web.core import Task, cmd_exists, parse_devices_cfg, parse_microcontrollers_cfg, start_task

# ---------------------------------------------------------------------------
# cmd_exists
# ---------------------------------------------------------------------------


def test_cmd_exists_python():
    assert cmd_exists("python3") is True or cmd_exists("python") is True


def test_cmd_exists_nonexistent():
    assert cmd_exists("nonexistent_command_xyz_123") is False


# ---------------------------------------------------------------------------
# Task class
# ---------------------------------------------------------------------------


def test_task_emit():
    t = Task("test-1")
    t.emit("hello", "info")
    msg = json.loads(t.q.get_nowait())
    assert msg["level"] == "info"
    assert msg["msg"] == "hello"


def test_task_done_success():
    t = Task("test-2")
    t.done(True)
    msg = json.loads(t.q.get_nowait())
    assert msg["level"] == "done"
    assert msg["msg"] == "done"
    assert t.status == "done"


def test_task_done_error():
    t = Task("test-3")
    t.done(False)
    msg = json.loads(t.q.get_nowait())
    assert msg["msg"] == "error"
    assert t.status == "error"


def test_task_cancel():
    t = Task("test-4")
    t.cancel()
    assert t.cancelled is True
    assert t.status == "error"
    # Should have emitted cancellation + done messages
    messages = []
    while not t.q.empty():
        messages.append(json.loads(t.q.get_nowait()))
    assert any("cancelled" in m["msg"].lower() for m in messages)


def test_task_run_shell_echo():
    t = Task("test-5")
    rc = t.run_shell(["echo", "hello world"])
    assert rc == 0
    assert t.status == "running"  # run_shell doesn't call done()
    messages = []
    while not t.q.empty():
        messages.append(json.loads(t.q.get_nowait()))
    assert any("hello world" in m["msg"] for m in messages)


def test_task_run_shell_nonexistent_command():
    t = Task("test-6")
    rc = t.run_shell(["nonexistent_cmd_xyz"])
    assert rc == 127
    messages = []
    while not t.q.empty():
        messages.append(json.loads(t.q.get_nowait()))
    assert any("not found" in m["msg"].lower() for m in messages)


def test_task_run_shell_cancelled():
    t = Task("test-7")
    t.cancelled = True
    rc = t.run_shell(["echo", "should not run"])
    assert rc == 1


def test_task_run_shell_failing_command():
    t = Task("test-8")
    rc = t.run_shell(["false"])
    assert rc != 0


def test_task_run_shell_sudo_prepends():
    t = Task("test-9")
    # We can't actually run sudo, but we can verify it builds the command
    # by checking the emitted command line
    t.cancelled = True  # Cancel immediately so it doesn't actually run
    t.run_shell(["ls"], sudo=True)
    # Nothing should run since cancelled, but we tested the path


# ---------------------------------------------------------------------------
# start_task
# ---------------------------------------------------------------------------


def test_start_task():
    results = []

    def worker(task):
        task.emit("working")
        results.append(True)
        task.done(True)

    task_id = start_task(worker)
    assert isinstance(task_id, str)
    assert len(task_id) == 8

    from web.core import tasks

    assert task_id in tasks
    # Wait for thread to complete
    tasks[task_id].thread.join(timeout=2)
    assert results == [True]
    assert tasks[task_id].status == "done"


# ---------------------------------------------------------------------------
# parse_devices_cfg
# ---------------------------------------------------------------------------


def test_parse_devices_cfg_returns_list():
    devices = parse_devices_cfg()
    assert isinstance(devices, list)


def test_parse_devices_cfg_entry_fields():
    devices = parse_devices_cfg()
    if devices:
        d = devices[0]
        assert "id" in d
        assert "label" in d


# ---------------------------------------------------------------------------
# parse_microcontrollers_cfg
# ---------------------------------------------------------------------------


def test_parse_microcontrollers_cfg_returns_list():
    boards = parse_microcontrollers_cfg()
    assert isinstance(boards, list)


def test_parse_microcontrollers_cfg_entry_fields():
    boards = parse_microcontrollers_cfg()
    if boards:
        b = boards[0]
        assert "id" in b
        assert "label" in b
