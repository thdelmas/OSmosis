"""Tests for scooter OTA update routes."""

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
# OTA check — no bleak
# ---------------------------------------------------------------------------


def test_ota_check_no_bleak(client):
    # _bleak_available is imported from scooter module at call time
    with patch("web.routes.scooter._bleak_available", return_value=False):
        resp = client.post(
            "/api/scooter/ota/check",
            json={
                "address": "AA:BB:CC:DD:EE:FF",
                "scooter_id": "nb-g30",
            },
        )
    assert resp.status_code == 500
    assert "bleak" in resp.get_json()["error"].lower()


# ---------------------------------------------------------------------------
# OTA check — missing address
# ---------------------------------------------------------------------------


def test_ota_check_missing_address(client):
    with patch("web.routes.scooter._bleak_available", return_value=True):
        resp = client.post(
            "/api/scooter/ota/check",
            json={
                "scooter_id": "nb-g30",
            },
        )
    assert resp.status_code == 400
    assert "address" in resp.get_json()["error"].lower()


# ---------------------------------------------------------------------------
# OTA apply — validation
# ---------------------------------------------------------------------------


def test_ota_apply_no_bleak(client):
    with patch("web.routes.scooter._bleak_available", return_value=False):
        resp = client.post(
            "/api/scooter/ota/apply",
            json={
                "address": "AA:BB:CC:DD:EE:FF",
                "scooter_id": "nb-g30",
                "source": "ipfs",
            },
        )
    assert resp.status_code == 500


def test_ota_apply_missing_address(client):
    with patch("web.routes.scooter._bleak_available", return_value=True):
        resp = client.post(
            "/api/scooter/ota/apply",
            json={
                "scooter_id": "nb-g30",
                "source": "ipfs",
            },
        )
    assert resp.status_code == 400


def test_ota_apply_invalid_source(client):
    with patch("web.routes.scooter._bleak_available", return_value=True):
        resp = client.post(
            "/api/scooter/ota/apply",
            json={
                "address": "AA:BB:CC:DD:EE:FF",
                "scooter_id": "nb-g30",
                "source": "invalid",
            },
        )
    assert resp.status_code == 400
    assert "source" in resp.get_json()["error"]
