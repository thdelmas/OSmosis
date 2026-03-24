"""Tests for desktop/laptop firmware routes — detection, probe, backup, flash."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web.app import app
from web.routes.firmware import _SUPPORTED_SYSTEMS


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_supported_systems_has_entries():
    assert len(_SUPPORTED_SYSTEMS) >= 5
    assert "ThinkPad X200" in _SUPPORTED_SYSTEMS
    assert "ThinkPad X230" in _SUPPORTED_SYSTEMS


def test_firmware_detect(client):
    mock_dmi = {
        "product_name": "ThinkPad X230",
        "sys_vendor": "LENOVO",
        "product_version": "ThinkPad X230",
        "bios_vendor": "LENOVO",
        "bios_version": "G2ETB5WW (2.75)",
    }

    def fake_read_dmi(field):
        return mock_dmi.get(field, "")

    with patch("web.routes.firmware._read_dmi_field", side_effect=fake_read_dmi):
        resp = client.get("/api/firmware/detect")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["product"] == "ThinkPad X230"
    assert data["supported"] is not None
    assert "coreboot" in data["supported"]["firmware"]
    assert data["already_coreboot"] is False


def test_firmware_detect_unsupported(client):
    def fake_read_dmi(field):
        if field == "product_name":
            return "Some Random Laptop"
        return ""

    with patch("web.routes.firmware._read_dmi_field", side_effect=fake_read_dmi):
        resp = client.get("/api/firmware/detect")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["supported"] is None


def test_firmware_detect_already_coreboot(client):
    def fake_read_dmi(field):
        if field == "product_name":
            return "ThinkPad X200"
        if field == "bios_vendor":
            return "coreboot"
        return ""

    with patch("web.routes.firmware._read_dmi_field", side_effect=fake_read_dmi):
        resp = client.get("/api/firmware/detect")
    data = resp.get_json()
    assert data["already_coreboot"] is True


def test_firmware_flash_missing_file(client):
    resp = client.post(
        "/api/firmware/flash",
        json={"fw_path": "/nonexistent/coreboot.rom"},
    )
    assert resp.status_code in (400, 500)


def test_firmware_flash_empty_body(client):
    resp = client.post("/api/firmware/flash", json={})
    assert resp.status_code in (400, 500)


def test_firmware_backup_no_flashrom(client):
    with patch("web.routes.firmware.cmd_exists", return_value=False):
        resp = client.post("/api/firmware/backup", json={})
    assert resp.status_code == 500
    assert "flashrom" in resp.get_json()["error"]
