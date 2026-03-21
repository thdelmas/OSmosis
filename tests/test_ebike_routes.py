"""Tests for e-bike controller routes."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web.app import app
from web.routes.ebike import parse_ebikes_cfg


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# Config parsing
# ---------------------------------------------------------------------------


def test_parse_ebikes_cfg():
    ebikes = parse_ebikes_cfg()
    assert isinstance(ebikes, list)
    if ebikes:
        e = ebikes[0]
        assert "id" in e
        assert "label" in e
        assert "brand" in e
        assert "controller" in e
        assert "flash_method" in e


# ---------------------------------------------------------------------------
# Ebike list
# ---------------------------------------------------------------------------


def test_ebikes_list(client):
    resp = client.get("/api/ebikes")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


def test_ebike_tools(client):
    resp = client.get("/api/ebike/tools")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "stlink" in data
    assert "stflash" in data
    assert "vesc_tool" in data
    for v in data.values():
        assert isinstance(v, bool)


# ---------------------------------------------------------------------------
# Detect — no stlink
# ---------------------------------------------------------------------------


@patch("web.routes.ebike._stinfo_available", return_value=False)
def test_ebike_detect_no_stlink(mock_cmd, client):
    resp = client.get("/api/ebike/detect")
    assert resp.status_code == 500
    assert "stlink" in resp.get_json()["error"].lower()


# ---------------------------------------------------------------------------
# Flash — validation
# ---------------------------------------------------------------------------


def test_ebike_flash_missing_firmware(client):
    resp = client.post(
        "/api/ebike/flash",
        json={
            "fw_path": "/nonexistent/firmware.bin",
            "controller": "test",
        },
    )
    assert resp.status_code == 400
    assert "Firmware file not found" in resp.get_json()["error"]


@patch("web.routes.ebike._stflash_available", return_value=False)
def test_ebike_flash_no_stflash(mock_cmd, client, tmp_path):
    fw = tmp_path / "test.bin"
    fw.write_bytes(b"\x00" * 100)
    resp = client.post(
        "/api/ebike/flash",
        json={
            "fw_path": str(fw),
            "controller": "test",
        },
    )
    assert resp.status_code == 500
    assert "st-flash" in resp.get_json()["error"]


# ---------------------------------------------------------------------------
# Backup — no stflash
# ---------------------------------------------------------------------------


@patch("web.routes.ebike._stflash_available", return_value=False)
def test_ebike_backup_no_stflash(mock_cmd, client):
    resp = client.post("/api/ebike/backup", json={"controller": "test"})
    assert resp.status_code == 500
