"""Tests for device detection, search, and OS routes."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web.app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# Device list
# ---------------------------------------------------------------------------


def test_devices_list(client):
    resp = client.get("/api/devices")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)


# ---------------------------------------------------------------------------
# Device search
# ---------------------------------------------------------------------------


def test_devices_search_no_query(client):
    resp = client.get("/api/devices/search")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_devices_search_by_brand(client):
    resp = client.get("/api/devices/search?brand=samsung")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)


def test_devices_search_by_model(client):
    resp = client.get("/api/devices/search?model=SM-")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Device OS options
# ---------------------------------------------------------------------------


def test_device_os_not_found(client):
    resp = client.get("/api/devices/nonexistent-device-xyz/os")
    assert resp.status_code == 404
    assert "device_not_found" in resp.get_json()["error"]


# ---------------------------------------------------------------------------
# Auto-detect — no adb
# ---------------------------------------------------------------------------


@patch("web.routes.device.cmd_exists", return_value=False)
def test_detect_no_adb(mock_cmd, client):
    resp = client.get("/api/detect")
    assert resp.status_code == 500
    assert "adb" in resp.get_json()["error"]
