"""Tests for e-bike controller routes."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web.app import app
from web.routes.ebike import parse_ebikes_cfg


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# Config parsing
# ---------------------------------------------------------------------------


def test_parse_ebikes_cfg():
    ebikes = parse_ebikes_cfg()
    assert isinstance(ebikes, list)
    if ebikes:
        e = ebikes[0]
        assert "id" in e
        assert "label" in e
        assert "brand" in e
        assert "controller" in e
        assert "flash_method" in e


# ---------------------------------------------------------------------------
# Ebike list
# ---------------------------------------------------------------------------


def test_ebikes_list(client):
    resp = client.get("/api/ebikes")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


def test_ebike_tools(client):
    resp = client.get("/api/ebike/tools")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "stlink" in data
    assert "stflash" in data
    assert "vesc_tool" in data
    for v in data.values():
        assert isinstance(v, bool)


# ---------------------------------------------------------------------------
# Detect — no stlink
# ---------------------------------------------------------------------------


@patch("web.routes.ebike._stinfo_available", return_value=False)
def test_ebike_detect_no_stlink(mock_cmd, client):
    resp = client.get("/api/ebike/detect")
    assert resp.status_code == 500
    assert "stlink" in resp.get_json()["error"].lower()


# ---------------------------------------------------------------------------
# Flash — validation
# ---------------------------------------------------------------------------


def test_ebike_flash_missing_firmware(client):
    resp = client.post(
        "/api/ebike/flash",
        json={
            "fw_path": "/nonexistent/firmware.bin",
            "controller": "test",
        },
    )
    assert resp.status_code == 400
    assert "Firmware file not found" in resp.get_json()["error"]


@patch("web.routes.ebike._stflash_available", return_value=False)
def test_ebike_flash_no_stflash(mock_cmd, client, tmp_path):
    fw = tmp_path / "test.bin"
    fw.write_bytes(b"\x00" * 100)
    resp = client.post(
        "/api/ebike/flash",
        json={
            "fw_path": str(fw),
            "controller": "test",
        },
    )
    assert resp.status_code == 500
    assert "st-flash" in resp.get_json()["error"]


# ---------------------------------------------------------------------------
# Backup — no stflash
# ---------------------------------------------------------------------------


@patch("web.routes.ebike._stflash_available", return_value=False)
def test_ebike_backup_no_stflash(mock_cmd, client):
    resp = client.post("/api/ebike/backup", json={"controller": "test"})
    assert resp.status_code == 500


# ---------------------------------------------------------------------------
# Parameter configuration
# ---------------------------------------------------------------------------


def test_ebike_params_tsdz2(client):
    resp = client.get("/api/ebike/params/tsdz2")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["name"] == "TSDZ2 Open Source Firmware"
    assert "speed_limit" in data["params"]
    assert "max_current" in data["params"]
    assert "regen_braking" in data["params"]


def test_ebike_params_bafang(client):
    resp = client.get("/api/ebike/params/bafang")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "Bafang" in data["name"]
    assert "wheel_diameter" in data["params"]


def test_ebike_params_unknown(client):
    resp = client.get("/api/ebike/params/unknown")
    assert resp.status_code == 404
    assert "available" in resp.get_json()


def test_ebike_params_apply_no_stflash(client):
    with patch("web.routes.ebike._stflash_available", return_value=False):
        resp = client.post(
            "/api/ebike/params/tsdz2/apply",
            json={"params": {"speed_limit": 32}},
        )
    assert resp.status_code == 500


def test_ebike_params_apply_no_params(client):
    resp = client.post("/api/ebike/params/tsdz2/apply", json={})
    assert resp.status_code == 400


def test_ebike_params_apply_unknown_type(client):
    resp = client.post("/api/ebike/params/unknown/apply", json={"params": {"x": 1}})
    assert resp.status_code == 404


def test_ebike_params_have_required_fields(client):
    resp = client.get("/api/ebike/params/tsdz2")
    data = resp.get_json()
    for key, spec in data["params"].items():
        assert "label" in spec, f"{key} missing label"
        assert "type" in spec, f"{key} missing type"
        assert "default" in spec, f"{key} missing default"
        assert "register" in spec, f"{key} missing register"
