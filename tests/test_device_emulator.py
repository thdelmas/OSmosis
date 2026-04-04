"""Tests using the device emulator — exercises detection and flash flows
against fake devices without any real hardware connected."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.device_emulator import DeviceEmulator, FakeDevice
from web.app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def emu():
    return DeviceEmulator()


# ---------------------------------------------------------------------------
# Detection: ADB device mode
# ---------------------------------------------------------------------------


def test_detect_samsung_note2(client, emu):
    """Samsung Note II in normal ADB mode is detected with correct props."""
    emu.connect(FakeDevice.SAMSUNG_NOTE2)
    with emu.patch():
        resp = client.get("/api/detect")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["model"] == "GT-N7100"
    assert data["codename"] == "t03g"
    assert data["brand"] == "Samsung"


def test_detect_pixel3a(client, emu):
    """Pixel 3a in normal ADB mode."""
    emu.connect(FakeDevice.PIXEL_3A)
    with emu.patch():
        resp = client.get("/api/detect")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["model"] == "Pixel 3a"
    assert data["codename"] == "sargo"


def test_detect_fairphone4(client, emu):
    """Fairphone 4 in normal ADB mode."""
    emu.connect(FakeDevice.FAIRPHONE_4)
    with emu.patch():
        resp = client.get("/api/detect")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["brand"] == "Fairphone"


# ---------------------------------------------------------------------------
# Detection: no device
# ---------------------------------------------------------------------------


def test_detect_no_device(client, emu):
    """No devices connected returns 404."""
    with emu.patch():
        resp = client.get("/api/detect")
    assert resp.status_code == 404
    data = resp.get_json()
    assert data["error"] == "no_device"


# ---------------------------------------------------------------------------
# Detection: Samsung Download Mode
# ---------------------------------------------------------------------------


def test_detect_samsung_download_mode(client, emu):
    """Samsung in Download Mode detected via heimdall."""
    emu.connect(FakeDevice.SAMSUNG_NOTE2_DOWNLOAD)
    with emu.patch():
        resp = client.get("/api/detect")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["error"] == "download_mode"
    assert "Download Mode" in data["hint"]


# ---------------------------------------------------------------------------
# Detection: unauthorized device
# ---------------------------------------------------------------------------


def test_detect_unauthorized_device(client, emu):
    """Unauthorized ADB device returns hint about authorization prompt."""
    emu.connect(FakeDevice.SAMSUNG_NOTE2_UNAUTHORIZED)
    with emu.patch():
        resp = client.get("/api/detect")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["error"] == "unauthorized"
    assert "hint" in data


# ---------------------------------------------------------------------------
# Connected devices endpoint
# ---------------------------------------------------------------------------


def test_connected_devices_multiple(client, emu):
    """Multiple devices from different transports appear together."""
    emu.connect(FakeDevice.SAMSUNG_NOTE2)
    emu.connect(FakeDevice.PIXEL_3A)
    with emu.patch():
        resp = client.get("/api/devices/connected")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["count"] == 2
    serials = {d["serial"] for d in data["devices"]}
    assert FakeDevice.SAMSUNG_NOTE2.serial in serials
    assert FakeDevice.PIXEL_3A.serial in serials


def test_connected_devices_empty(client, emu):
    """No connected devices returns empty list."""
    with emu.patch():
        resp = client.get("/api/devices/connected")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["count"] == 0
    assert data["devices"] == []


def test_connected_devices_download_mode(client, emu):
    """Samsung in Download Mode appears in connected list."""
    emu.connect(FakeDevice.SAMSUNG_NOTE2_DOWNLOAD)
    with emu.patch():
        resp = client.get("/api/devices/connected")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["count"] == 1
    assert data["devices"][0]["mode"] == "download"


# ---------------------------------------------------------------------------
# Emulator: connect and disconnect
# ---------------------------------------------------------------------------


def test_emulator_disconnect_specific(client, emu):
    """Disconnecting a specific device removes only that device."""
    emu.connect(FakeDevice.SAMSUNG_NOTE2)
    emu.connect(FakeDevice.PIXEL_3A)
    emu.disconnect(FakeDevice.SAMSUNG_NOTE2)

    with emu.patch():
        resp = client.get("/api/detect")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["codename"] == "sargo"


def test_emulator_disconnect_all(client, emu):
    """Disconnecting all devices results in no detection."""
    emu.connect(FakeDevice.SAMSUNG_NOTE2)
    emu.connect(FakeDevice.PIXEL_3A)
    emu.disconnect()

    with emu.patch():
        resp = client.get("/api/detect")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# USB listing (lsusb)
# ---------------------------------------------------------------------------


def test_lsusb_contains_device_info(emu):
    """The fake lsusb output contains the device's USB vendor ID."""
    emu.connect(FakeDevice.SAMSUNG_NOTE2)
    output = emu._lsusb()
    assert "04e8" in output
    assert "Samsung" in output
    # Always includes the root hub
    assert "root hub" in output


# ---------------------------------------------------------------------------
# Flash routes with emulated device
# ---------------------------------------------------------------------------


def test_flash_stock_no_file(client, emu):
    """Flash stock with nonexistent file returns 400 even with a device connected."""
    emu.connect(FakeDevice.SAMSUNG_NOTE2)
    with emu.patch():
        resp = client.post(
            "/api/flash/stock", json={"fw_zip": "/nonexistent.zip"}
        )
    assert resp.status_code == 400
