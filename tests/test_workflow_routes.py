"""Tests for workflow and ROM update routes."""

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
# Update ROM — validation
# ---------------------------------------------------------------------------


def test_update_rom_no_url_or_cid(client):
    resp = client.post(
        "/api/update-rom",
        json={
            "codename": "test",
            "filename": "rom.zip",
        },
    )
    assert resp.status_code == 400
    assert "No download URL" in resp.get_json()["error"]


def test_update_rom_valid(client):
    resp = client.post(
        "/api/update-rom",
        json={
            "codename": "test",
            "url": "https://example.com/rom.zip",
            "filename": "rom.zip",
        },
    )
    assert resp.status_code == 200
    assert "task_id" in resp.get_json()
