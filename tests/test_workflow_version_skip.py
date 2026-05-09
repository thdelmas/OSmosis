"""Tests for the idempotent flash skip — _stage_flash short-circuits when the
device already reports the target firmware version.

This is the last open 12.1 item: "Skip flash if device already reports the
target firmware version."
"""

import sys
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web import workflow_engine
from web.workflow_engine import (
    StageState,
    StageStatus,
    WorkflowState,
    _device_already_at_target,
    _stage_flash,
)


@pytest.fixture
def state():
    return WorkflowState(
        id="t1",
        device_id="x",
        stages=[StageState(id="flash", name="Flash")],
        context={"dest": "/nonexistent.zip", "flash_method": "sideload"},
    )


@pytest.fixture
def fake_task():
    """A test double for Task that just collects emits."""
    t = mock.MagicMock()
    t.emits = []
    t.emit = lambda msg, level="info": t.emits.append((level, msg))
    return t


# ---------------------------------------------------------------------------
# _device_already_at_target — the comparison itself
# ---------------------------------------------------------------------------


def test_no_target_means_no_match(state):
    matched, _ = _device_already_at_target(state)
    assert matched is False


def test_no_adb_response_means_no_match(state, monkeypatch):
    state.context["target_version"] = "13"
    monkeypatch.setattr(workflow_engine, "_device_props_via_adb", lambda: {})
    matched, _ = _device_already_at_target(state)
    assert matched is False


def test_fingerprint_match(state, monkeypatch):
    state.context["target_fingerprint"] = "google/fp1"
    monkeypatch.setattr(
        workflow_engine,
        "_device_props_via_adb",
        lambda: {"ro.build.fingerprint": "google/fp1"},
    )
    matched, reason = _device_already_at_target(state)
    assert matched is True
    assert "fingerprint" in reason


def test_build_id_match(state, monkeypatch):
    state.context["target_build_id"] = "TQ3A.230805.001"
    monkeypatch.setattr(
        workflow_engine,
        "_device_props_via_adb",
        lambda: {"ro.build.display.id": "TQ3A.230805.001"},
    )
    matched, _ = _device_already_at_target(state)
    assert matched is True


def test_version_match(state, monkeypatch):
    state.context["target_version"] = "13"
    monkeypatch.setattr(
        workflow_engine,
        "_device_props_via_adb",
        lambda: {"ro.build.version.release": "13"},
    )
    matched, _ = _device_already_at_target(state)
    assert matched is True


def test_version_mismatch(state, monkeypatch):
    state.context["target_version"] = "13"
    monkeypatch.setattr(
        workflow_engine,
        "_device_props_via_adb",
        lambda: {"ro.build.version.release": "12"},
    )
    matched, _ = _device_already_at_target(state)
    assert matched is False


# ---------------------------------------------------------------------------
# _stage_flash — short-circuits and marks SKIPPED on match
# ---------------------------------------------------------------------------


def test_stage_flash_skipped_when_target_matches(state, fake_task, monkeypatch):
    state.context["target_version"] = "13"
    monkeypatch.setattr(
        workflow_engine,
        "_device_props_via_adb",
        lambda: {"ro.build.version.release": "13"},
    )

    stage = state.stages[0]
    result = _stage_flash(fake_task, state, stage)

    assert result is True
    assert stage.status == StageStatus.SKIPPED
    assert stage.result.get("skip_reason")
    # And it must NOT have tried to actually flash — no shell calls happened
    fake_task.run_shell.assert_not_called()


def test_stage_flash_proceeds_when_no_target(state, fake_task, monkeypatch):
    """No target = no skip — flash attempts as normal (and fails fast on missing file)."""
    monkeypatch.setattr(workflow_engine, "_device_props_via_adb", lambda: {})

    stage = state.stages[0]
    result = _stage_flash(fake_task, state, stage)

    # No firmware file -> flash fails. The point: it didn't short-circuit on a
    # phantom match and it went past the version check.
    assert result is False
    assert stage.status != StageStatus.SKIPPED


def test_stage_flash_proceeds_when_adb_unreachable(state, fake_task, monkeypatch):
    """Download/fastboot mode means no adb getprop — must fall through, not block."""
    state.context["target_version"] = "13"
    monkeypatch.setattr(workflow_engine, "_device_props_via_adb", lambda: {})

    stage = state.stages[0]
    _stage_flash(fake_task, state, stage)

    # We should not have skipped — adb being unreachable in download/fastboot
    # mode is the normal flashing case
    assert stage.status != StageStatus.SKIPPED
