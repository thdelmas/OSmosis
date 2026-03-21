"""Tests for fastboot API routes — unlock guides, status, validation."""

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
# Unlock guides
# ---------------------------------------------------------------------------


def test_unlock_guide_all(client):
    resp = client.get("/api/fastboot/unlock-guide")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "google" in data
    assert "oneplus" in data
    assert "xiaomi" in data
    assert "fairphone" in data
    assert "motorola" in data
    assert "samsung" in data


def test_unlock_guide_google(client):
    resp = client.get("/api/fastboot/unlock-guide/google")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["brand"] == "Google Pixel"
    assert len(data["steps"]) > 0
    assert "notes" in data


def test_unlock_guide_oneplus(client):
    resp = client.get("/api/fastboot/unlock-guide/oneplus")
    assert resp.status_code == 200
    assert "OnePlus" in resp.get_json()["brand"]


def test_unlock_guide_xiaomi(client):
    resp = client.get("/api/fastboot/unlock-guide/xiaomi")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "waiting period" in data["notes"].lower()


def test_unlock_guide_fairphone(client):
    resp = client.get("/api/fastboot/unlock-guide/fairphone")
    assert resp.status_code == 200


def test_unlock_guide_motorola(client):
    resp = client.get("/api/fastboot/unlock-guide/motorola")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["steps"]) > 3  # Motorola has a multi-step process


def test_unlock_guide_case_insensitive(client):
    resp = client.get("/api/fastboot/unlock-guide/Google")
    assert resp.status_code == 200


def test_unlock_guide_not_found(client):
    resp = client.get("/api/fastboot/unlock-guide/nonexistent")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Fastboot lock route
# ---------------------------------------------------------------------------


@patch("web.routes.fastboot.cmd_exists", return_value=False)
def test_lock_no_fastboot(mock_cmd, client):
    resp = client.post("/api/fastboot/lock")
    assert resp.status_code == 503


@patch("web.routes.fastboot._fastboot_devices", return_value=[])
@patch("web.routes.fastboot.cmd_exists", return_value=True)
def test_lock_no_device(mock_cmd, mock_devices, client):
    resp = client.post("/api/fastboot/lock")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Fastboot flash validation
# ---------------------------------------------------------------------------


@patch("web.routes.fastboot.cmd_exists", return_value=True)
@patch("web.routes.fastboot._fastboot_devices", return_value=[{"serial": "ABC", "mode": "fastboot"}])
def test_flash_missing_image(mock_devices, mock_cmd, client):
    resp = client.post("/api/fastboot/flash", json={"image_zip": "/nonexistent.zip"})
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Router routes
# ---------------------------------------------------------------------------


def test_router_tools(client):
    resp = client.get("/api/router/tools")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "dnsmasq" in data
    assert "curl" in data


def test_router_flash_tftp_missing_fields(client):
    resp = client.post("/api/router/flash/tftp", json={})
    assert resp.status_code == 400


def test_router_flash_sysupgrade_missing_fields(client):
    resp = client.post("/api/router/flash/sysupgrade", json={})
    assert resp.status_code == 400


def test_router_flash_web_missing_fields(client):
    resp = client.post("/api/router/flash/web", json={})
    assert resp.status_code == 400
