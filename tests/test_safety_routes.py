"""Tests for safety/registry/recovery/plugin API routes."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web import registry
from web.app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def tmp_registry(tmp_path, monkeypatch):
    reg_path = tmp_path / "firmware-registry.json"
    monkeypatch.setattr(registry, "REGISTRY_PATH", reg_path)
    return reg_path


# ---------------------------------------------------------------------------
# Recovery guide routes
# ---------------------------------------------------------------------------


def test_recovery_list(client):
    resp = client.get("/api/recovery")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert len(data) >= 4
    ids = {g["id"] for g in data}
    assert "samsung" in ids
    assert "pixel" in ids


def test_recovery_guide_samsung(client):
    resp = client.get("/api/recovery/samsung")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["title"] == "Samsung Recovery Guide"
    assert len(data["steps"]) > 0


def test_recovery_guide_not_found(client):
    resp = client.get("/api/recovery/nonexistent")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Preflight routes
# ---------------------------------------------------------------------------


@patch("web.safety.subprocess.run", side_effect=FileNotFoundError)
@patch("web.safety.BACKUP_DIR")
def test_preflight_phone_route(mock_backup, mock_run, client):
    mock_backup.exists.return_value = False
    resp = client.post("/api/preflight/phone", json={})
    assert resp.status_code == 200
    data = resp.get_json()
    assert "checks" in data
    assert "passed" in data


@patch("web.safety.subprocess.run", side_effect=FileNotFoundError)
def test_preflight_scooter_route(mock_run, client):
    resp = client.post("/api/preflight/scooter", json={"address": "AA:BB:CC:DD:EE:FF"})
    assert resp.status_code == 200
    data = resp.get_json()
    ble = next(c for c in data["checks"] if c["id"] == "ble_address")
    assert ble["passed"] is True


@patch("web.safety.subprocess.run", side_effect=FileNotFoundError)
@patch("web.safety.BACKUP_DIR")
def test_preflight_pixel_route(mock_backup, mock_run, client):
    mock_backup.exists.return_value = False
    resp = client.post("/api/preflight/pixel", json={})
    assert resp.status_code == 200
    data = resp.get_json()
    assert "checks" in data


# ---------------------------------------------------------------------------
# Registry routes
# ---------------------------------------------------------------------------


def test_registry_list_empty(client):
    resp = client.get("/api/registry")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_registry_add_missing_file(client):
    resp = client.post("/api/registry/add", json={"fw_path": "/nonexistent/fw.bin"})
    assert resp.status_code == 400


def test_registry_add_and_list(client, tmp_path):
    fw = tmp_path / "test.bin"
    fw.write_bytes(b"test firmware data")

    resp = client.post(
        "/api/registry/add",
        json={
            "fw_path": str(fw),
            "device_id": "test-device",
            "version": "1.0",
        },
    )
    assert resp.status_code == 201
    entry = resp.get_json()
    assert entry["device_id"] == "test-device"
    assert entry["sha256"]

    # Now list
    resp = client.get("/api/registry")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 1


def test_registry_verify_missing_file(client):
    resp = client.post("/api/registry/verify", json={"fw_path": "/nonexistent"})
    assert resp.status_code == 400


def test_registry_verify_known_file(client, tmp_path):
    fw = tmp_path / "known.bin"
    fw.write_bytes(b"known firmware")

    # Register first
    client.post("/api/registry/add", json={"fw_path": str(fw), "device_id": "d1"})

    # Verify
    resp = client.post("/api/registry/verify", json={"fw_path": str(fw)})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["known"] is True


def test_registry_lookup_empty(client):
    resp = client.get("/api/registry/lookup/abc123")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_registry_device_entries(client, tmp_path):
    fw = tmp_path / "fw.bin"
    fw.write_bytes(b"data")
    client.post("/api/registry/add", json={"fw_path": str(fw), "device_id": "pixel-7"})

    resp = client.get("/api/registry/device/pixel-7")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 1

    resp = client.get("/api/registry/device/unknown")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_registry_device_history(client, tmp_path):
    fw = tmp_path / "fw.bin"
    fw.write_bytes(b"data")
    client.post(
        "/api/registry/add",
        json={"fw_path": str(fw), "device_id": "dev1", "component": "esc", "version": "1.0"},
    )
    resp = client.get("/api/registry/device/dev1/history")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 1
    assert data[0]["component"] == "esc"


def test_registry_ipfs_link_missing_fields(client):
    resp = client.post("/api/registry/ipfs-link", json={})
    assert resp.status_code == 400


def test_registry_ipfs_link_invalid_cid(client):
    resp = client.post("/api/registry/ipfs-link", json={"sha256": "abc", "cid": "not-a-cid"})
    assert resp.status_code == 400


def test_registry_restore_missing_sha256(client):
    resp = client.post("/api/registry/restore", json={})
    assert resp.status_code == 400


def test_registry_restore_not_found(client):
    resp = client.post("/api/registry/restore", json={"sha256": "nonexistent"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Plugin routes
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
