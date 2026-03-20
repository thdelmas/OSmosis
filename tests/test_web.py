"""Tests for Osmosis web UI backend."""

import json
import sys
from pathlib import Path

import pytest

# Ensure web/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

from app import app, parse_devices_cfg


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------

def test_index_returns_html(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Osmosis" in resp.data


# ---------------------------------------------------------------------------
# API: status
# ---------------------------------------------------------------------------

def test_api_status(client):
    resp = client.get("/api/status")
    assert resp.status_code == 200
    data = resp.get_json()
    # Should report on these tools
    for tool in ("heimdall", "adb", "wget", "curl", "lz4"):
        assert tool in data
        assert isinstance(data[tool], bool)


# ---------------------------------------------------------------------------
# API: devices
# ---------------------------------------------------------------------------

def test_api_devices(client):
    resp = client.get("/api/devices")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)


def test_parse_devices_cfg():
    devices = parse_devices_cfg()
    assert isinstance(devices, list)
    if devices:
        d = devices[0]
        assert "id" in d
        assert "label" in d
        assert "model" in d
        assert "codename" in d


# ---------------------------------------------------------------------------
# API: browse
# ---------------------------------------------------------------------------

def test_api_browse_home(client):
    resp = client.get("/api/browse")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["type"] == "dir"
    assert "entries" in data


def test_api_browse_specific_dir(client):
    resp = client.get("/api/browse?path=/tmp")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["type"] == "dir"
    assert data["path"] == "/tmp"


def test_api_browse_nonexistent(client):
    resp = client.get("/api/browse?path=/nonexistent_path_12345")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# API: logs
# ---------------------------------------------------------------------------

def test_api_logs(client):
    resp = client.get("/api/logs")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)


def test_api_log_not_found(client):
    resp = client.get("/api/logs/nonexistent.log")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# API: flash/stock — validation
# ---------------------------------------------------------------------------

def test_flash_stock_missing_file(client):
    resp = client.post(
        "/api/flash/stock",
        json={"fw_zip": "/nonexistent/firmware.zip"},
    )
    assert resp.status_code == 400


def test_flash_stock_empty(client):
    resp = client.post("/api/flash/stock", json={"fw_zip": ""})
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# API: flash/recovery — validation
# ---------------------------------------------------------------------------

def test_flash_recovery_missing_file(client):
    resp = client.post(
        "/api/flash/recovery",
        json={"recovery_img": "/nonexistent/recovery.img"},
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# API: sideload — validation
# ---------------------------------------------------------------------------

def test_sideload_missing_file(client):
    resp = client.post(
        "/api/sideload",
        json={"zip_path": "/nonexistent/rom.zip", "label": "ROM"},
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# API: download — validation
# ---------------------------------------------------------------------------

def test_download_unknown_device(client):
    resp = client.post(
        "/api/download",
        json={"device_id": "nonexistent-device", "selected": ["rom_url"]},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# API: updates — starts a task
# ---------------------------------------------------------------------------

def test_updates_returns_task(client):
    resp = client.get("/api/updates")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "task_id" in data


# ---------------------------------------------------------------------------
# API: stream — unknown task
# ---------------------------------------------------------------------------

def test_stream_unknown_task(client):
    resp = client.get("/api/stream/nonexistent")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# API: workflow — validation (empty is ok, starts task)
# ---------------------------------------------------------------------------

def test_workflow_empty(client):
    resp = client.post("/api/workflow", json={})
    assert resp.status_code == 200
    data = resp.get_json()
    assert "task_id" in data


# ---------------------------------------------------------------------------
# API: magisk — validation
# ---------------------------------------------------------------------------

def test_magisk_missing_file(client):
    resp = client.post(
        "/api/magisk",
        json={"boot_img": "/nonexistent/boot.img"},
    )
    assert resp.status_code == 400
