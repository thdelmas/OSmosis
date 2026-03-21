"""Tests for Osmosis web UI backend."""

import sys
from pathlib import Path

import pytest

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web.app import app
from web.core import parse_devices_cfg


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------


def test_index_returns_html(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Osmosis" in resp.data


# ---------------------------------------------------------------------------
# API: status
# ---------------------------------------------------------------------------


def test_api_status(client):
    resp = client.get("/api/status")
    assert resp.status_code == 200
    data = resp.get_json()
    for tool in ("heimdall", "adb", "wget", "curl", "lz4"):
        assert tool in data
        assert isinstance(data[tool], bool)


# ---------------------------------------------------------------------------
# API: devices
# ---------------------------------------------------------------------------


def test_api_devices(client):
    resp = client.get("/api/devices")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)


def test_parse_devices_cfg():
    devices = parse_devices_cfg()
    assert isinstance(devices, list)
    if devices:
        d = devices[0]
        assert "id" in d
        assert "label" in d
        assert "model" in d
        assert "codename" in d


# ---------------------------------------------------------------------------
# API: browse
# ---------------------------------------------------------------------------


def test_api_browse_home(client):
    resp = client.get("/api/browse")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["type"] == "dir"
    assert "entries" in data


def test_api_browse_specific_dir(client):
    resp = client.get("/api/browse?path=/tmp")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["type"] == "dir"
    assert data["path"] == "/tmp"


def test_api_browse_nonexistent(client):
    resp = client.get("/api/browse?path=/nonexistent_path_12345")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# API: logs
# ---------------------------------------------------------------------------


def test_api_logs(client):
    resp = client.get("/api/logs")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)


def test_api_log_not_found(client):
    resp = client.get("/api/logs/nonexistent.log")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# API: flash/stock — validation
# ---------------------------------------------------------------------------


def test_flash_stock_missing_file(client):
    resp = client.post(
        "/api/flash/stock",
        json={"fw_zip": "/nonexistent/firmware.zip"},
    )
    assert resp.status_code == 400


def test_flash_stock_empty(client):
    resp = client.post("/api/flash/stock", json={"fw_zip": ""})
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# API: flash/recovery — validation
# ---------------------------------------------------------------------------


def test_flash_recovery_missing_file(client):
    resp = client.post(
        "/api/flash/recovery",
        json={"recovery_img": "/nonexistent/recovery.img"},
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# API: sideload — validation
# ---------------------------------------------------------------------------


def test_sideload_missing_file(client):
    resp = client.post(
        "/api/sideload",
        json={"zip_path": "/nonexistent/rom.zip", "label": "ROM"},
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# API: download — validation
# ---------------------------------------------------------------------------


def test_download_unknown_device(client):
    resp = client.post(
        "/api/download",
        json={"device_id": "nonexistent-device", "selected": ["rom_url"]},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# API: updates — starts a task
# ---------------------------------------------------------------------------


def test_updates_returns_task(client):
    resp = client.get("/api/updates")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "task_id" in data


# ---------------------------------------------------------------------------
# API: stream — unknown task
# ---------------------------------------------------------------------------


def test_stream_unknown_task(client):
    resp = client.get("/api/stream/nonexistent")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# API: workflow — validation (empty is ok, starts task)
# ---------------------------------------------------------------------------


def test_workflow_empty(client):
    resp = client.post("/api/workflow", json={})
    assert resp.status_code == 200
    data = resp.get_json()
    assert "task_id" in data


# ---------------------------------------------------------------------------
# API: magisk — validation
# ---------------------------------------------------------------------------


def test_magisk_missing_file(client):
    resp = client.post(
        "/api/magisk",
        json={"boot_img": "/nonexistent/boot.img"},
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# API: fastboot
# ---------------------------------------------------------------------------


def test_fastboot_status_no_cmd(client):
    from unittest.mock import patch

    with patch("web.routes.fastboot.cmd_exists", return_value=False):
        resp = client.get("/api/fastboot/status")
    assert resp.status_code == 503
    data = resp.get_json()
    assert data["connected"] is False


def test_fastboot_status_no_device(client):
    from unittest.mock import patch

    with patch("web.routes.fastboot.cmd_exists", return_value=True), \
         patch("web.routes.fastboot._fastboot_devices", return_value=[]):
        resp = client.get("/api/fastboot/status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["connected"] is False


def test_fastboot_unlock_no_device(client):
    from unittest.mock import patch

    with patch("web.routes.fastboot.cmd_exists", return_value=True), \
         patch("web.routes.fastboot._fastboot_devices", return_value=[]):
        resp = client.post("/api/fastboot/unlock")
    assert resp.status_code == 400


def test_fastboot_flash_missing_zip(client):
    from unittest.mock import patch

    with patch("web.routes.fastboot.cmd_exists", return_value=True), \
         patch("web.routes.fastboot._fastboot_devices", return_value=[{"serial": "abc", "mode": "fastboot"}]):
        resp = client.post("/api/fastboot/flash", json={"image_zip": "/nonexistent/image.zip"})
    assert resp.status_code == 400
    data = resp.get_json()
    assert "error" in data


def test_fastboot_flash_no_cmd(client):
    from unittest.mock import patch

    with patch("web.routes.fastboot.cmd_exists", return_value=False):
        resp = client.post("/api/fastboot/flash", json={"image_zip": "/tmp/test.zip"})
    assert resp.status_code == 503


# ---------------------------------------------------------------------------
# API: scooters list
# ---------------------------------------------------------------------------


def test_scooters_list(client):
    resp = client.get("/api/scooters")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    ids = [s["id"] for s in data]
    assert "nb-g30" in ids
    assert "xi-m365" in ids


# ---------------------------------------------------------------------------
# Scooter config parsing
# ---------------------------------------------------------------------------


def test_scooters_cfg_parsing():
    from web.routes.scooter import parse_scooters_cfg

    scooters = parse_scooters_cfg()
    assert isinstance(scooters, list)
    assert len(scooters) > 0
    required_keys = {"id", "label", "brand", "protocol", "flash_method", "cfw_url", "shfw_supported", "notes"}
    for s in scooters:
        assert required_keys == s.keys(), f"Unexpected keys in scooter dict: {s.keys()}"
        assert s["id"]
        assert s["label"]


# ---------------------------------------------------------------------------
# API: scooter tools
# ---------------------------------------------------------------------------


def test_scooter_tools(client):
    resp = client.get("/api/scooter/tools")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "bleak" in data
    assert "stlink" in data
    assert "stflash" in data
    assert isinstance(data["bleak"], bool)
    assert isinstance(data["stlink"], bool)
    assert isinstance(data["stflash"], bool)


# ---------------------------------------------------------------------------
# API: scooter scan — bleak not installed
# ---------------------------------------------------------------------------


def test_scooter_scan_no_bleak(client):
    from unittest.mock import patch

    with patch("web.routes.scooter._bleak_available", return_value=False):
        resp = client.get("/api/scooter/scan")
    assert resp.status_code == 500
    data = resp.get_json()
    assert "error" in data
    assert "bleak" in data["error"].lower()


# ---------------------------------------------------------------------------
# API: scooter flash — missing address
# ---------------------------------------------------------------------------


def test_scooter_flash_missing_fields(client):
    from unittest.mock import patch

    with patch("web.routes.scooter._bleak_available", return_value=True):
        resp = client.post("/api/scooter/flash", json={})
    assert resp.status_code == 400
    data = resp.get_json()
    assert "error" in data


# ---------------------------------------------------------------------------
# Protocol: NinebotPacket encode/decode round-trip
# ---------------------------------------------------------------------------


def test_scooter_proto_ninebot_packet():
    from web.scooter_proto import NinebotPacket, ADDR_APP, ADDR_ESC, CMD_READ_INFO

    payload = b"\x10\x00\x01\x02"
    original = NinebotPacket(
        src=ADDR_APP,
        dst=ADDR_ESC,
        cmd=CMD_READ_INFO,
        arg=0x02,
        payload=payload,
    )

    encoded = original.encode()
    assert isinstance(encoded, bytes)
    # Header magic
    assert encoded[0] == 0x5A
    assert encoded[1] == 0xA5

    decoded = NinebotPacket.decode(encoded)
    assert decoded.src == original.src
    assert decoded.dst == original.dst
    assert decoded.cmd == original.cmd
    assert decoded.arg == original.arg
    assert decoded.payload == original.payload


# ---------------------------------------------------------------------------
# Protocol: XiaomiPacket encode/decode round-trip
# ---------------------------------------------------------------------------


def test_scooter_proto_xiaomi_packet():
    from web.scooter_proto import XiaomiPacket, ADDR_APP, ADDR_ESC, CMD_READ_REG

    payload = b"\xAB\xCD"
    original = XiaomiPacket(
        src=ADDR_APP,
        dst=ADDR_ESC,
        cmd=CMD_READ_REG,
        arg=0x00,
        payload=payload,
    )

    encoded = original.encode()
    assert isinstance(encoded, bytes)
    # Header magic
    assert encoded[0] == 0x55
    assert encoded[1] == 0xAA

    decoded = XiaomiPacket.decode(encoded)
    assert decoded.src == original.src
    assert decoded.dst == original.dst
    assert decoded.cmd == original.cmd
    assert decoded.arg == original.arg
    assert decoded.payload == original.payload


# ---------------------------------------------------------------------------
# Protocol: CRC16 XModem known test vectors
# ---------------------------------------------------------------------------


def test_scooter_proto_crc():
    from web.scooter_proto import _crc16_xmodem

    # Canonical XModem CRC16 test vector: "123456789" -> 0x31C3
    assert _crc16_xmodem(b"123456789") == 0x31C3

    # Empty input produces zero
    assert _crc16_xmodem(b"") == 0x0000

    # Single zero byte: all XOR/shift steps produce 0, result is 0
    assert _crc16_xmodem(b"\x00") == 0x0000

    # Verify commutativity is NOT expected — order matters (sanity check)
    assert _crc16_xmodem(b"\x01\x02") != _crc16_xmodem(b"\x02\x01")
