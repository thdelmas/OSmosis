"""Tests for system routes — status, tools, browse, logs, companion, plugins."""

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
# Status
# ---------------------------------------------------------------------------


def test_status(client):
    resp = client.get("/api/status")
    assert resp.status_code == 200
    data = resp.get_json()
    for key in ("heimdall", "adb", "wget", "curl", "lz4", "ipfs", "dnsmasq"):
        assert key in data
        assert isinstance(data[key], bool)


# ---------------------------------------------------------------------------
# Install tool — validation
# ---------------------------------------------------------------------------


def test_install_tool_unknown(client):
    resp = client.post("/api/install-tool", json={"tool": "nonexistent_tool"})
    assert resp.status_code == 400
    assert "Unknown tool" in resp.get_json()["error"]


# ---------------------------------------------------------------------------
# Task cancel — not found
# ---------------------------------------------------------------------------


def test_task_cancel_not_found(client):
    resp = client.post("/api/task/nonexistent/cancel")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Stream — not found
# ---------------------------------------------------------------------------


def test_stream_not_found(client):
    resp = client.get("/api/stream/nonexistent")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Browse
# ---------------------------------------------------------------------------


def test_browse_home(client):
    resp = client.get("/api/browse")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["type"] == "dir"


def test_browse_tmp(client):
    resp = client.get("/api/browse?path=/tmp")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["path"] == "/tmp"


def test_browse_nonexistent(client):
    resp = client.get("/api/browse?path=/nonexistent_xyz_12345")
    assert resp.status_code == 404


def test_browse_shortcut_downloads(client):
    resp = client.get("/api/browse?path=__downloads__")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Logs
# ---------------------------------------------------------------------------


def test_logs_list(client):
    resp = client.get("/api/logs")
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)


def test_log_not_found(client):
    resp = client.get("/api/logs/nonexistent.log")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Companion
# ---------------------------------------------------------------------------


def test_companion_script(client):
    resp = client.get("/api/companion-script")
    assert resp.status_code == 200
    assert b"Osmosis Companion" in resp.data


def test_companion_tools(client):
    resp = client.get("/api/companion-tools")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert len(data) > 0
    ids = [t["id"] for t in data]
    assert "termux-script" in ids
    assert "magisk" in ids


# ---------------------------------------------------------------------------
# Plugins
# ---------------------------------------------------------------------------


def test_plugins_list(client):
    resp = client.get("/api/plugins")
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)


def test_plugin_detect_not_found(client):
    resp = client.get("/api/plugins/detect/nonexistent-plugin")
    assert resp.status_code == 404


def test_plugin_info_not_found(client):
    resp = client.get("/api/plugins/info/nonexistent-plugin/dev1")
    assert resp.status_code == 404
