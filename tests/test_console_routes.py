"""Tests for game console routes — Switch, Steam Deck, PS Vita."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web.app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# Nintendo Switch — status
# ---------------------------------------------------------------------------


def test_switch_status(client):
    resp = client.get("/api/console/switch/status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "connected" in data


# ---------------------------------------------------------------------------
# Switch inject — validation
# ---------------------------------------------------------------------------


def test_switch_inject_missing_payload(client):
    resp = client.post(
        "/api/console/switch/inject",
        json={
            "payload_path": "/nonexistent/hekate.bin",
        },
    )
    assert resp.status_code == 400
    assert "Payload file not found" in resp.get_json()["error"]


def test_switch_inject_empty_body(client):
    resp = client.post("/api/console/switch/inject", json={})
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Steam Deck recovery — validation
# ---------------------------------------------------------------------------


def test_steamdeck_recovery_missing_image(client):
    resp = client.post(
        "/api/console/steamdeck/recovery",
        json={
            "image_path": "/nonexistent/recovery.img",
            "device": "/dev/sdz",
        },
    )
    assert resp.status_code == 400
    assert "Recovery image not found" in resp.get_json()["error"]


def test_steamdeck_recovery_no_device(client):
    resp = client.post(
        "/api/console/steamdeck/recovery",
        json={
            "image_path": "/tmp/test.img",
        },
    )
    assert resp.status_code == 400


def test_steamdeck_recovery_invalid_device(client):
    resp = client.post(
        "/api/console/steamdeck/recovery",
        json={
            "image_path": "/tmp/test.img",
            "device": "not-dev",
        },
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# PS Vita guide
# ---------------------------------------------------------------------------


def test_vita_guide(client):
    resp = client.get("/api/console/vita/guide")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "title" in data
    assert "steps" in data
    assert isinstance(data["steps"], list)
    assert len(data["steps"]) > 0
    assert "notes" in data
    assert "required_firmware" in data
