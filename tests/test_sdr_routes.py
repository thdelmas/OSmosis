"""Tests for SDR dongle routes — detection, status, driver setup, HackRF update."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web.app import app
from web.routes.sdr import _SDR_DEVICES


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_sdr_detect_no_device(client):
    with patch("web.routes.sdr._detect_sdr_devices", return_value=[]):
        resp = client.get("/api/sdr/detect")
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "no_device"


def test_sdr_detect_found(client):
    mock = [{"vid": "0bda", "pid": "2838", "name": "RTL-SDR Blog V3/V4"}]
    with patch("web.routes.sdr._detect_sdr_devices", return_value=mock):
        resp = client.get("/api/sdr/detect")
    assert resp.status_code == 200
    assert len(resp.get_json()["devices"]) == 1


def test_sdr_status(client):
    resp = client.get("/api/sdr/status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "dvb_blacklisted" in data
    assert "dvb_loaded" in data
    assert "needs_setup" in data


def test_sdr_known_devices_has_entries():
    assert len(_SDR_DEVICES) >= 3
    assert ("0bda", "2838") in _SDR_DEVICES
    assert ("1d50", "6089") in _SDR_DEVICES


def test_hackrf_update_missing_file(client):
    resp = client.post(
        "/api/sdr/hackrf-update", json={"fw_path": "/nonexistent.bin"}
    )
    assert resp.status_code == 400


def test_hackrf_update_empty(client):
    resp = client.post("/api/sdr/hackrf-update", json={})
    assert resp.status_code == 400
