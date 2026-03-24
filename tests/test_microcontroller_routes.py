"""Tests for microcontroller routes — boards, search, tools, detect, flash,
and ESP firmware catalog."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web.app import app
from web.routes.microcontroller import _MCU_USB_VENDORS


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# Board listing
# ---------------------------------------------------------------------------


def test_microcontrollers_list(client):
    resp = client.get("/api/microcontrollers")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


def test_microcontrollers_search_no_query(client):
    resp = client.get("/api/microcontrollers/search")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)


def test_microcontrollers_search_by_brand(client):
    resp = client.get("/api/microcontrollers/search?brand=esp")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)


def test_microcontrollers_search_by_query(client):
    resp = client.get("/api/microcontrollers/search?q=pico")
    assert resp.status_code == 200


def test_microcontrollers_search_by_arch(client):
    resp = client.get("/api/microcontrollers/search?arch=arm")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


def test_microcontrollers_tools(client):
    resp = client.get("/api/microcontrollers/tools")
    assert resp.status_code == 200
    data = resp.get_json()
    expected_keys = ["arduino_cli", "esptool", "picotool", "stflash", "openocd", "avrdude", "dfu_util", "teensy_loader"]
    for key in expected_keys:
        assert key in data
        assert isinstance(data[key], bool)


# ---------------------------------------------------------------------------
# Detect — no devices
# ---------------------------------------------------------------------------


def test_microcontrollers_detect_no_devices(client):
    with patch("web.routes.microcontroller._list_serial_ports", return_value=[]):
        with patch("web.routes.microcontroller._detect_uf2_drives", return_value=[]):
            resp = client.get("/api/microcontrollers/detect")
    assert resp.status_code == 404
    data = resp.get_json()
    assert data["error"] == "no_device"


# ---------------------------------------------------------------------------
# Flash — validation
# ---------------------------------------------------------------------------


def test_microcontrollers_flash_missing_firmware(client):
    resp = client.post(
        "/api/microcontrollers/flash",
        json={
            "board_id": "esp32-devkit",
            "fw_path": "/nonexistent/firmware.bin",
        },
    )
    assert resp.status_code == 400
    assert "Firmware file not found" in resp.get_json()["error"]


def test_microcontrollers_flash_empty_body(client):
    resp = client.post("/api/microcontrollers/flash", json={})
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# USB vendor lookup
# ---------------------------------------------------------------------------


def test_mcu_usb_vendors_has_common_entries():
    assert "2341" in _MCU_USB_VENDORS  # Arduino
    assert "303a" in _MCU_USB_VENDORS  # Espressif
    assert "2e8a" in _MCU_USB_VENDORS  # Raspberry Pi


# ---------------------------------------------------------------------------
# Firmware targets catalog
# ---------------------------------------------------------------------------


def test_firmware_targets_by_board_id(client):
    resp = client.get("/api/microcontrollers/firmware-targets?board_id=esp32-devkit")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert len(data) >= 2  # Tasmota + ESPHome at minimum
    ids = [t["id"] for t in data]
    assert "tasmota" in ids
    assert "esphome" in ids


def test_firmware_targets_by_chip(client):
    resp = client.get("/api/microcontrollers/firmware-targets?chip=esp32s3")
    assert resp.status_code == 200
    data = resp.get_json()
    ids = [t["id"] for t in data]
    assert "tasmota" in ids


def test_firmware_targets_esp8266(client):
    resp = client.get("/api/microcontrollers/firmware-targets?chip=esp8266")
    assert resp.status_code == 200
    data = resp.get_json()
    ids = [t["id"] for t in data]
    assert "tasmota" in ids
    assert "wled" in ids


def test_firmware_targets_unknown_board(client):
    resp = client.get("/api/microcontrollers/firmware-targets?board_id=nonexistent")
    assert resp.status_code == 404


def test_firmware_targets_no_params(client):
    resp = client.get("/api/microcontrollers/firmware-targets")
    assert resp.status_code == 400


def test_firmware_targets_has_required_fields(client):
    resp = client.get("/api/microcontrollers/firmware-targets?chip=esp32")
    data = resp.get_json()
    for target in data:
        assert "id" in target
        assert "name" in target
        assert "desc" in target
        assert "tags" in target
        assert "homepage" in target


# ---------------------------------------------------------------------------
# Download firmware — validation only (no network)
# ---------------------------------------------------------------------------


def test_download_firmware_missing_url(client):
    resp = client.post("/api/microcontrollers/download-firmware", json={})
    assert resp.status_code == 400
    assert "No URL" in resp.get_json()["error"]


def test_download_firmware_bad_scheme(client):
    resp = client.post(
        "/api/microcontrollers/download-firmware",
        json={"url": "ftp://example.com/firmware.bin"},
    )
    assert resp.status_code == 400
    assert "HTTP" in resp.get_json()["error"]
