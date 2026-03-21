"""Tests for Medicat USB routes."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web.app import app
from web.routes.medicat import parse_medicat_cfg


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# Config parsing
# ---------------------------------------------------------------------------


def test_parse_medicat_cfg():
    profiles = parse_medicat_cfg()
    assert isinstance(profiles, list)
    if profiles:
        p = profiles[0]
        assert "id" in p
        assert "label" in p
        assert "min_usb_gb" in p
        assert "ventoy_required" in p


# ---------------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------------


def test_medicat_profiles(client):
    resp = client.get("/api/medicat/profiles")
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


def test_medicat_tools(client):
    resp = client.get("/api/medicat/tools")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "ventoy" in data
    assert "lsblk" in data
    assert "mount" in data


# ---------------------------------------------------------------------------
# Check Ventoy — validation
# ---------------------------------------------------------------------------


def test_check_ventoy_no_device(client):
    resp = client.post("/api/medicat/check-ventoy", json={})
    assert resp.status_code == 400


def test_check_ventoy_invalid_device(client):
    resp = client.post("/api/medicat/check-ventoy", json={"device": "not-dev"})
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Install Ventoy — validation
# ---------------------------------------------------------------------------


def test_install_ventoy_no_device(client):
    resp = client.post("/api/medicat/install-ventoy", json={})
    assert resp.status_code == 400


def test_install_ventoy_invalid_device(client):
    resp = client.post("/api/medicat/install-ventoy", json={"device": "xyz"})
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Copy files — validation
# ---------------------------------------------------------------------------


def test_copy_files_no_device(client):
    resp = client.post("/api/medicat/copy-files", json={"medicat_path": "/tmp"})
    assert resp.status_code == 400


def test_copy_files_missing_path(client):
    resp = client.post(
        "/api/medicat/copy-files",
        json={
            "device": "/dev/sdz",
            "medicat_path": "/nonexistent/medicat/path",
        },
    )
    assert resp.status_code == 400
    assert "not found" in resp.get_json()["error"].lower()
