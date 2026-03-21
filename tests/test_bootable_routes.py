"""Tests for bootable media, block device, PXE, and interface routes."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web.app import app
from web.routes.bootable import _parse_size_bytes


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# _parse_size_bytes helper
# ---------------------------------------------------------------------------


def test_parse_size_bytes_gigabytes():
    assert _parse_size_bytes("14.9G") == int(14.9 * 1024**3)


def test_parse_size_bytes_megabytes():
    assert _parse_size_bytes("512M") == 512 * 1024**2


def test_parse_size_bytes_kilobytes():
    assert _parse_size_bytes("1024K") == 1024 * 1024


def test_parse_size_bytes_bytes():
    assert _parse_size_bytes("4096B") == 4096


def test_parse_size_bytes_terabytes():
    assert _parse_size_bytes("2T") == 2 * 1024**4


def test_parse_size_bytes_plain_number():
    assert _parse_size_bytes("1024") == 1024


def test_parse_size_bytes_invalid():
    assert _parse_size_bytes("abc") is None


def test_parse_size_bytes_whitespace():
    assert _parse_size_bytes("  8G  ") == 8 * 1024**3


# ---------------------------------------------------------------------------
# Block devices
# ---------------------------------------------------------------------------


def test_blockdevices_returns_list(client):
    resp = client.get("/api/blockdevices")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)


# ---------------------------------------------------------------------------
# Bootable write — validation
# ---------------------------------------------------------------------------


def test_bootable_missing_image(client):
    resp = client.post(
        "/api/bootable",
        json={
            "image_path": "/nonexistent/image.img",
            "target_device": "/dev/sdz",
        },
    )
    assert resp.status_code == 400
    assert "Image file not found" in resp.get_json()["error"]


def test_bootable_missing_device(client):
    resp = client.post(
        "/api/bootable",
        json={
            "image_path": "/tmp/test.img",
            "target_device": "",
        },
    )
    assert resp.status_code == 400


def test_bootable_invalid_device_path(client):
    resp = client.post(
        "/api/bootable",
        json={
            "image_path": "/tmp/test.img",
            "target_device": "not-a-dev-path",
        },
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# PXE
# ---------------------------------------------------------------------------


def test_pxe_start_missing_interface(client):
    resp = client.post("/api/pxe/start", json={})
    assert resp.status_code == 400
    assert "interface" in resp.get_json()["error"].lower()


def test_pxe_start_valid(client):
    resp = client.post("/api/pxe/start", json={"interface": "eth0"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert "task_id" in data


def test_pxe_stop(client):
    resp = client.post("/api/pxe/stop")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Interfaces
# ---------------------------------------------------------------------------


def test_interfaces_returns_list(client):
    resp = client.get("/api/interfaces")
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)
