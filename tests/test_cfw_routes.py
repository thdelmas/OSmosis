"""Tests for CFW builder routes."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web.app import app
from web.cfw_builder import get_all_families


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# CFW families
# ---------------------------------------------------------------------------


def test_cfw_families(client):
    resp = client.get("/api/cfw/families")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)


def test_get_all_families():
    families = get_all_families()
    assert isinstance(families, list)


# ---------------------------------------------------------------------------
# CFW patches
# ---------------------------------------------------------------------------


def test_cfw_patches_not_found(client):
    resp = client.get("/api/cfw/patches/nonexistent-model")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# CFW build — validation
# ---------------------------------------------------------------------------


def test_cfw_build_missing_scooter_id(client):
    resp = client.post(
        "/api/cfw/build",
        json={
            "fw_path": "/tmp/test.bin",
            "config": {"speed_limit": {}},
        },
    )
    assert resp.status_code == 400
    assert "scooter_id" in resp.get_json()["error"]


def test_cfw_build_missing_firmware(client):
    resp = client.post(
        "/api/cfw/build",
        json={
            "scooter_id": "nb-g30",
            "fw_path": "/nonexistent/firmware.bin",
            "config": {"speed_limit": {}},
        },
    )
    assert resp.status_code == 400
    assert "Firmware file not found" in resp.get_json()["error"]


def test_cfw_build_no_config(client):
    resp = client.post(
        "/api/cfw/build",
        json={
            "scooter_id": "nb-g30",
            "fw_path": "/tmp/test.bin",
            "config": {},
        },
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# CFW download — validation
# ---------------------------------------------------------------------------


def test_cfw_download_missing_zip(client):
    resp = client.post(
        "/api/cfw/download",
        json={
            "zip_path": "/nonexistent/cfw.zip",
        },
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# CFW build-and-flash — validation
# ---------------------------------------------------------------------------


def test_cfw_build_and_flash_missing_address(client):
    resp = client.post(
        "/api/cfw/build-and-flash",
        json={
            "scooter_id": "nb-g30",
            "fw_path": "/tmp/test.bin",
            "config": {"speed_limit": {}},
        },
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# CFW manifest export — no builds
# ---------------------------------------------------------------------------


def test_cfw_manifest_export_no_builds(client):
    resp = client.get("/api/cfw/manifest/export/nonexistent-model")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# CFW manifest import — validation
# ---------------------------------------------------------------------------


def test_cfw_manifest_import_invalid(client):
    resp = client.post("/api/cfw/manifest/import", json={})
    assert resp.status_code == 400


def test_cfw_manifest_import_wrong_type(client):
    resp = client.post(
        "/api/cfw/manifest/import",
        json={
            "manifest": {"type": "wrong"},
        },
    )
    assert resp.status_code == 400


def test_cfw_manifest_import_hash_mismatch(client):
    resp = client.post(
        "/api/cfw/manifest/import",
        json={
            "manifest": {"type": "cfw", "scooter_id": "test", "entries": [{"cid": "Qm" + "a" * 44}]},
            "sha256": "0000000000000000000000000000000000000000000000000000000000000000",
        },
    )
    assert resp.status_code == 400
    assert "integrity" in resp.get_json()["error"].lower()


def test_cfw_manifest_import_no_entries(client):
    resp = client.post(
        "/api/cfw/manifest/import",
        json={
            "manifest": {"type": "cfw", "scooter_id": "test", "entries": []},
        },
    )
    assert resp.status_code == 400
