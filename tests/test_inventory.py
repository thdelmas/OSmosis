"""Tests for the dynamic device inventory (Phase 12.4).

Covers parsing of lsusb / adb / serial / bluetoothctl / avahi-browse output,
SSDP packet handling, and the /api/inventory routes. External commands and
network sockets are stubbed — these tests do not require any hardware.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web import inventory
from web.app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class _FakeProc:
    def __init__(self, stdout=""):
        self.stdout = stdout
        self.stderr = ""
        self.returncode = 0


def _stub_run(monkeypatch, mapping):
    """Replace subprocess.run with a lookup keyed on argv[0]."""

    def fake_run(cmd, *_, **__):
        key = cmd[0] if cmd else ""
        if key not in mapping:
            return _FakeProc("")
        return _FakeProc(mapping[key])

    monkeypatch.setattr(inventory.subprocess, "run", fake_run)


# ---- USB ---------------------------------------------------------------


def test_detect_usb_known_vendor(monkeypatch):
    _stub_run(
        monkeypatch,
        {
            "lsusb": (
                "Bus 001 Device 003: ID 04e8:6860 Samsung Electronics Co., Ltd "
                "GT-N7100 [Galaxy Note II]\n"
                "Bus 001 Device 004: ID 1d6b:0002 Linux Foundation 2.0 root hub\n"
            )
        },
    )
    devices = inventory._detect_usb()
    assert len(devices) == 1
    d = devices[0]
    assert d.type == "usb"
    assert d.vendor == "Samsung"
    assert d.details["vid"] == "04e8"
    assert d.details["pid"] == "6860"
    assert "Galaxy Note II" in d.name


def test_detect_usb_skips_unknown_vid(monkeypatch):
    _stub_run(
        monkeypatch,
        {"lsusb": "Bus 001 Device 002: ID 1d6b:0003 Linux Foundation\n"},
    )
    assert inventory._detect_usb() == []


# ---- ADB ---------------------------------------------------------------


def test_detect_adb_parses_l_output(monkeypatch):
    monkeypatch.setattr(inventory, "cmd_exists", lambda c: c == "adb")
    _stub_run(
        monkeypatch,
        {
            "adb": (
                "List of devices attached\n"
                "AABB1234            device usb:1-1 product:foo model:Pixel_7 "
                "device:panther transport_id:1\n"
            )
        },
    )
    devices = inventory._detect_adb()
    assert len(devices) == 1
    d = devices[0]
    assert d.type == "adb"
    assert d.serial == "AABB1234"
    assert d.model == "Pixel_7"
    assert d.status == "ready"


def test_detect_adb_missing_binary(monkeypatch):
    monkeypatch.setattr(inventory, "cmd_exists", lambda c: False)
    assert inventory._detect_adb() == []


# ---- BLE ---------------------------------------------------------------


def test_detect_ble_parses_bluetoothctl(monkeypatch):
    monkeypatch.setattr(inventory, "cmd_exists", lambda c: c == "bluetoothctl")
    _stub_run(
        monkeypatch,
        {
            "bluetoothctl": (
                "Device AA:BB:CC:DD:EE:FF Mi Scooter\n"
                "Device 11:22:33:44:55:66 PineTime\n"
                "Device 99:88:77:66:55:44 \n"
            )
        },
    )
    devices = inventory._detect_ble()
    macs = sorted(d.connection for d in devices)
    assert macs == [
        "11:22:33:44:55:66",
        "99:88:77:66:55:44",
        "AA:BB:CC:DD:EE:FF",
    ]
    by_mac = {d.connection: d for d in devices}
    assert by_mac["AA:BB:CC:DD:EE:FF"].name == "Mi Scooter"
    # Empty name falls back to MAC
    assert by_mac["99:88:77:66:55:44"].name == "99:88:77:66:55:44"


def test_detect_ble_missing_binary(monkeypatch):
    monkeypatch.setattr(inventory, "cmd_exists", lambda c: False)
    assert inventory._detect_ble() == []


def test_detect_ble_dedupes_repeated_macs(monkeypatch):
    monkeypatch.setattr(inventory, "cmd_exists", lambda c: c == "bluetoothctl")
    _stub_run(
        monkeypatch,
        {
            "bluetoothctl": (
                "Device AA:BB:CC:DD:EE:FF First Name\n"
                "Device aa:bb:cc:dd:ee:ff Second Name\n"
            )
        },
    )
    devices = inventory._detect_ble()
    assert len(devices) == 1
    assert devices[0].name == "First Name"


# ---- mDNS --------------------------------------------------------------


def test_detect_mdns_filters_relevant_hosts(monkeypatch):
    monkeypatch.setattr(inventory, "cmd_exists", lambda c: c == "avahi-browse")
    _stub_run(
        monkeypatch,
        {
            "avahi-browse": (
                "=;eth0;IPv4;openwrt;_http._tcp;local;openwrt.local;192.168.1.1;80;\n"
                "=;eth0;IPv4;some-laptop;_http._tcp;local;some-laptop.local;192.168.1.42;80;\n"
                "=;eth0;IPv4;octoprint;_http._tcp;local;octoprint.local;192.168.1.50;5000;\n"
            )
        },
    )
    devices = inventory._detect_mdns()
    names = sorted(d.name for d in devices)
    assert names == ["octoprint", "openwrt"]
    assert all(d.details.get("discovery") == "mdns" for d in devices)


# ---- SSDP --------------------------------------------------------------


def test_detect_ssdp_parses_response(monkeypatch):
    """Stub the UDP socket so the test runs without a network."""

    response = (
        b"HTTP/1.1 200 OK\r\n"
        b"LOCATION: http://192.168.1.1:5000/desc.xml\r\n"
        b"SERVER: Linux/3.10 UPnP/1.0 OpenWRT/22.03\r\n"
        b"ST: upnp:rootdevice\r\n\r\n"
    )

    class FakeSocket:
        def __init__(self, *a, **kw):
            self._calls = 0

        def setsockopt(self, *a, **kw):
            pass

        def settimeout(self, *a, **kw):
            pass

        def sendto(self, *a, **kw):
            return len(a[0])

        def recvfrom(self, _bufsize):
            self._calls += 1
            if self._calls == 1:
                return response, ("192.168.1.1", 1900)
            raise TimeoutError()

        def close(self):
            pass

    monkeypatch.setattr(inventory.socket, "socket", lambda *a, **kw: FakeSocket())
    devices = inventory._detect_ssdp(timeout=0.1)
    assert len(devices) == 1
    d = devices[0]
    assert d.type == "network"
    assert d.details["ip"] == "192.168.1.1"
    assert d.details["discovery"] == "ssdp"
    assert "OpenWRT" in d.details["server"] or "Linux" in d.details["server"]


def test_detect_ssdp_handles_no_network(monkeypatch):
    def boom(*_a, **_kw):
        raise OSError("Network is unreachable")

    monkeypatch.setattr(inventory.socket, "socket", boom)
    assert inventory._detect_ssdp(timeout=0.1) == []


# ---- combined network --------------------------------------------------


def test_detect_network_dedupes_by_ip(monkeypatch):
    monkeypatch.setattr(
        inventory,
        "_detect_mdns",
        lambda: [
            inventory.InventoryDevice(
                id="net-192.168.1.1",
                name="openwrt",
                type="network",
                connection="192.168.1.1:80",
                details={"ip": "192.168.1.1", "discovery": "mdns"},
            )
        ],
    )
    monkeypatch.setattr(
        inventory,
        "_detect_ssdp",
        lambda: [
            inventory.InventoryDevice(
                id="net-192.168.1.1",
                name="OpenWRT (192.168.1.1)",
                type="network",
                connection="192.168.1.1",
                details={"ip": "192.168.1.1", "discovery": "ssdp"},
            ),
            inventory.InventoryDevice(
                id="net-192.168.1.50",
                name="Roku (192.168.1.50)",
                type="network",
                connection="192.168.1.50",
                details={"ip": "192.168.1.50", "discovery": "ssdp"},
            ),
        ],
    )
    devices = inventory._detect_network()
    ips = sorted(d.details["ip"] for d in devices)
    assert ips == ["192.168.1.1", "192.168.1.50"]
    # mDNS wins over SSDP for the duplicate
    by_ip = {d.details["ip"]: d for d in devices}
    assert by_ip["192.168.1.1"].details["discovery"] == "mdns"


# ---- routes ------------------------------------------------------------


def test_inventory_routes_return_lists(client, monkeypatch):
    monkeypatch.setattr(inventory, "scan_inventory", lambda: [])
    monkeypatch.setattr(inventory, "_detect_usb", lambda: [])
    monkeypatch.setattr(inventory, "_detect_adb", lambda: [])
    monkeypatch.setattr(inventory, "_detect_serial", lambda: [])
    monkeypatch.setattr(inventory, "_detect_ble", lambda: [])
    monkeypatch.setattr(inventory, "_detect_network", lambda: [])
    monkeypatch.setattr(inventory, "_detect_mdns", lambda: [])
    monkeypatch.setattr(inventory, "_detect_ssdp", lambda: [])

    for path in (
        "/api/inventory",
        "/api/inventory/usb",
        "/api/inventory/adb",
        "/api/inventory/serial",
        "/api/inventory/ble",
        "/api/inventory/network",
        "/api/inventory/mdns",
        "/api/inventory/ssdp",
    ):
        resp = client.get(path)
        assert resp.status_code == 200, path
        assert resp.get_json() == [], path


def test_inventory_full_scan_serializes(client, monkeypatch):
    monkeypatch.setattr(
        inventory,
        "scan_inventory",
        lambda: [
            inventory.InventoryDevice(
                id="usb-04e8-6860-1-3",
                name="Galaxy Note II",
                type="usb",
                vendor="Samsung",
                connection="USB Bus 001 Device 003",
                profile_id="t0lte",
                details={"vid": "04e8", "pid": "6860"},
            )
        ],
    )
    resp = client.get("/api/inventory")
    assert resp.status_code == 200
    body = resp.get_json()
    assert isinstance(body, list)
    assert body[0]["profile_id"] == "t0lte"
    assert body[0]["details"]["vid"] == "04e8"
