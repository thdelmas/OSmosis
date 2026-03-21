"""Tests for OS Builder gallery routes."""

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
# Gallery browse
# ---------------------------------------------------------------------------


def test_gallery_browse(client):
    resp = client.get("/api/os-builder/gallery")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)


def test_gallery_browse_with_filters(client):
    resp = client.get("/api/os-builder/gallery?distro=debian&arch=amd64")
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)


# ---------------------------------------------------------------------------
# Gallery publish — validation
# ---------------------------------------------------------------------------


def test_gallery_publish_missing_filename(client):
    resp = client.post("/api/os-builder/gallery/publish", json={})
    assert resp.status_code == 400
    assert "filename" in resp.get_json()["error"]


def test_gallery_publish_not_found(client):
    resp = client.post(
        "/api/os-builder/gallery/publish",
        json={
            "filename": "nonexistent-build.img",
        },
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Gallery import — validation
# ---------------------------------------------------------------------------


def test_gallery_import_invalid(client):
    resp = client.post("/api/os-builder/gallery/import", json={})
    assert resp.status_code == 400


def test_gallery_import_wrong_type(client):
    resp = client.post(
        "/api/os-builder/gallery/import",
        json={
            "manifest": {"type": "wrong"},
        },
    )
    assert resp.status_code == 400


def test_gallery_import_hash_mismatch(client):
    resp = client.post(
        "/api/os-builder/gallery/import",
        json={
            "manifest": {"type": "os-build", "build": {"cid": "Qm" + "a" * 44}},
            "sha256": "0" * 64,
        },
    )
    assert resp.status_code == 400
    assert "SHA256" in resp.get_json()["error"]


# ---------------------------------------------------------------------------
# Gallery fork — validation
# ---------------------------------------------------------------------------


def test_gallery_fork_missing_fields(client):
    resp = client.post("/api/os-builder/gallery/fork", json={})
    assert resp.status_code == 400


def test_gallery_fork_not_found(client):
    resp = client.post(
        "/api/os-builder/gallery/fork",
        json={
            "key": "os-build/nonexistent",
            "new_name": "my-fork",
        },
    )
    assert resp.status_code == 404
