"""Tests for diagnostics and post-install configuration routes."""

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
# Diagnostics — no adb
# ---------------------------------------------------------------------------


@patch("web.routes.diagnostics.cmd_exists", return_value=False)
def test_diagnostics_no_adb(mock_cmd, client):
    resp = client.get("/api/diagnostics")
    assert resp.status_code == 500
    assert "adb" in resp.get_json()["error"]


# ---------------------------------------------------------------------------
# Configure ROM — returns task
# ---------------------------------------------------------------------------


def test_configure_rom_returns_task(client):
    resp = client.post("/api/configure-rom", json={})
    assert resp.status_code == 200
    data = resp.get_json()
    assert "task_id" in data


def test_configure_rom_with_config(client):
    resp = client.post(
        "/api/configure-rom",
        json={
            "debloat": ["com.example.bloat"],
            "privacy": {"disable_analytics": True},
            "locale": "en-US",
            "timezone": "UTC",
            "display": {"dark_mode": True, "font_scale": 1.2},
        },
    )
    assert resp.status_code == 200
    assert "task_id" in resp.get_json()
