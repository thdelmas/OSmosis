"""Tests for Apple T2 security chip routes."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web.app import app
from web.routes.t2 import parse_t2_cfg


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# Config parsing
# ---------------------------------------------------------------------------


def test_parse_t2_cfg():
    macs = parse_t2_cfg()
    assert isinstance(macs, list)
    if macs:
        m = macs[0]
        assert "id" in m
        assert "label" in m
        assert "model" in m
        assert "board_id" in m


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


def test_t2_models(client):
    resp = client.get("/api/t2/models")
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


def test_t2_tools(client):
    resp = client.get("/api/t2/tools")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "t2tool" in data
    assert "lsusb" in data
    assert "libusb" in data


# ---------------------------------------------------------------------------
# Detect — returns task
# ---------------------------------------------------------------------------


def test_t2_detect(client):
    resp = client.get("/api/t2/detect")
    assert resp.status_code == 200
    assert "task_id" in resp.get_json()


# ---------------------------------------------------------------------------
# Backup — no t2tool
# ---------------------------------------------------------------------------


@patch("web.routes.t2._t2_tool_available", return_value=False)
def test_t2_backup_no_tool(mock_tool, client):
    resp = client.post("/api/t2/backup", json={"model": "mbp-2019-16"})
    assert resp.status_code == 500
    assert "t2tool" in resp.get_json()["error"]


# ---------------------------------------------------------------------------
# Backups list
# ---------------------------------------------------------------------------


def test_t2_backups(client):
    resp = client.get("/api/t2/backups")
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)


# ---------------------------------------------------------------------------
# Restore — validation
# ---------------------------------------------------------------------------


def test_t2_restore_not_found(client):
    resp = client.post("/api/t2/restore", json={"backup_name": "nonexistent"})
    assert resp.status_code == 404


@patch("web.routes.t2._t2_tool_available", return_value=False)
def test_t2_restore_no_tool(mock_tool, client, tmp_path):
    # Create a fake backup dir
    backup_dir = Path.home() / ".osmosis" / "t2-backups" / "test-restore-dir"
    backup_dir.mkdir(parents=True, exist_ok=True)
    (backup_dir / "firmware.bin").write_bytes(b"\x00" * 100)
    try:
        resp = client.post("/api/t2/restore", json={"backup_name": "test-restore-dir"})
        assert resp.status_code == 500
        assert "t2tool" in resp.get_json()["error"]
    finally:
        (backup_dir / "firmware.bin").unlink(missing_ok=True)
        backup_dir.rmdir()
