"""Tests for device submission routes."""

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
# Submit — validation
# ---------------------------------------------------------------------------


def test_submit_missing_category(client):
    resp = client.post("/api/devices/submit", json={"label": "Test"})
    assert resp.status_code == 400
    assert "category" in resp.get_json()["error"]


def test_submit_invalid_category(client):
    resp = client.post(
        "/api/devices/submit",
        json={
            "category": "spaceship",
            "label": "Test",
        },
    )
    assert resp.status_code == 400
    assert "Invalid category" in resp.get_json()["error"]


def test_submit_missing_label(client):
    resp = client.post("/api/devices/submit", json={"category": "phone"})
    assert resp.status_code == 400
    assert "label" in resp.get_json()["error"]


def test_submit_valid(client):
    resp = client.post(
        "/api/devices/submit",
        json={
            "category": "phone",
            "label": "Test Device",
            "model": "TST-001",
            "codename": "testdev",
            "brand": "TestBrand",
        },
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["ok"] is True
    assert "filename" in data

    # Clean up the submission file
    submissions_dir = Path.home() / ".osmosis" / "device-submissions"
    sub_file = submissions_dir / data["filename"]
    if sub_file.exists():
        sub_file.unlink()


# ---------------------------------------------------------------------------
# List submissions
# ---------------------------------------------------------------------------


def test_submissions_list(client):
    resp = client.get("/api/devices/submissions")
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)


# ---------------------------------------------------------------------------
# Approve — validation
# ---------------------------------------------------------------------------


def test_approve_missing_filename(client):
    resp = client.post("/api/devices/submissions/approve", json={})
    assert resp.status_code == 400


def test_approve_not_found(client):
    resp = client.post(
        "/api/devices/submissions/approve",
        json={
            "filename": "nonexistent-file.json",
        },
    )
    assert resp.status_code == 404
