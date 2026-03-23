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


# ---------------------------------------------------------------------------
# Battery check
# ---------------------------------------------------------------------------


@patch("web.routes.diagnostics.cmd_exists", return_value=False)
def test_battery_check_no_adb(mock_cmd, client):
    resp = client.get("/api/battery-check")
    assert resp.status_code == 500
    assert "adb" in resp.get_json()["error"]


@patch("web.routes.diagnostics.cmd_exists", return_value=True)
@patch("web.routes.diagnostics.subprocess.run")
def test_battery_check_no_device(mock_run, mock_cmd, client):
    # adb devices returns no devices
    mock_run.return_value = type("R", (), {"stdout": "List of devices attached\n\n", "returncode": 0})()
    resp = client.get("/api/battery-check")
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "no_device"


@patch("web.routes.diagnostics.cmd_exists", return_value=True)
@patch("web.routes.diagnostics.subprocess.run")
def test_battery_check_success(mock_run, mock_cmd, client):
    def side_effect(cmd, **kwargs):
        if cmd == ["adb", "devices"]:
            return type("R", (), {"stdout": "List of devices attached\nabc123\tdevice\n", "returncode": 0})()
        if "dumpsys" in cmd:
            return type(
                "R", (), {"stdout": "  level: 72\n  AC powered: false\n  USB powered: true\n", "returncode": 0}
            )()
        return type("R", (), {"stdout": "", "returncode": 0})()

    mock_run.side_effect = side_effect
    resp = client.get("/api/battery-check")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["level"] == 72
    assert data["plugged"] is True
    assert data["ok"] is True


@patch("web.routes.diagnostics.cmd_exists", return_value=True)
@patch("web.routes.diagnostics.subprocess.run")
def test_battery_check_low_battery(mock_run, mock_cmd, client):
    def side_effect(cmd, **kwargs):
        if cmd == ["adb", "devices"]:
            return type("R", (), {"stdout": "List of devices attached\nabc123\tdevice\n", "returncode": 0})()
        if "dumpsys" in cmd:
            return type(
                "R", (), {"stdout": "  level: 15\n  AC powered: false\n  USB powered: false\n", "returncode": 0}
            )()
        return type("R", (), {"stdout": "", "returncode": 0})()

    mock_run.side_effect = side_effect
    resp = client.get("/api/battery-check")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["level"] == 15
    assert data["plugged"] is False
    assert data["ok"] is False


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
