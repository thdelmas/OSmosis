"""Tests for flash, sideload, download, backup, and restore routes."""

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
# Flash stock — validation
# ---------------------------------------------------------------------------


def test_flash_stock_missing(client):
    resp = client.post("/api/flash/stock", json={"fw_zip": "/nonexistent.zip"})
    assert resp.status_code == 400


def test_flash_stock_empty(client):
    resp = client.post("/api/flash/stock", json={"fw_zip": ""})
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Flash recovery — validation
# ---------------------------------------------------------------------------


def test_flash_recovery_missing(client):
    resp = client.post(
        "/api/flash/recovery", json={"recovery_img": "/nonexistent.img"}
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Sideload — validation
# ---------------------------------------------------------------------------


def test_sideload_missing(client):
    resp = client.post(
        "/api/sideload", json={"zip_path": "/nonexistent.zip", "label": "ROM"}
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Download — unknown device
# ---------------------------------------------------------------------------


def test_download_unknown_device(client):
    resp = client.post(
        "/api/download",
        json={
            "device_id": "nonexistent-device",
            "selected": ["rom_url"],
        },
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Backup — returns task
# ---------------------------------------------------------------------------


def test_backup_returns_task(client):
    resp = client.post(
        "/api/backup",
        json={
            "partitions": ["boot"],
        },
    )
    assert resp.status_code == 200
    assert "task_id" in resp.get_json()


def test_backup_full_returns_task(client):
    resp = client.post("/api/backup/full", json={})
    assert resp.status_code == 200
    assert "task_id" in resp.get_json()


# ---------------------------------------------------------------------------
# Backup list
# ---------------------------------------------------------------------------


def test_backup_list(client):
    resp = client.get("/api/backup/list")
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)


# ---------------------------------------------------------------------------
# Restore — validation
# ---------------------------------------------------------------------------


def test_restore_not_found(client):
    resp = client.post(
        "/api/backup/restore",
        json={
            "backup_name": "nonexistent-backup",
        },
    )
    assert resp.status_code == 404
