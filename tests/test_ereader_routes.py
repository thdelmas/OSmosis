"""Tests for e-reader routes — Kobo detection and KOReader install."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web.app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_ereader_detect_no_device(client):
    with patch("web.routes.ereader._find_kobo_mount", return_value=None):
        resp = client.get("/api/ereader/detect")
    assert resp.status_code == 404
    data = resp.get_json()
    assert data["error"] == "no_device"
    assert "hint" in data


def test_ereader_detect_found(client):
    mock_kobo = {
        "mount": "/media/KOBOeReader",
        "model": "N613",
        "firmware": "4.38.22801",
        "kobo_dir": "/media/KOBOeReader/.kobo",
    }
    with patch("web.routes.ereader._find_kobo_mount", return_value=mock_kobo):
        resp = client.get("/api/ereader/detect")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["model"] == "N613"
    assert data["mount"] == "/media/KOBOeReader"


def test_install_koreader_no_url(client):
    resp = client.post("/api/ereader/install-koreader", json={})
    assert resp.status_code == 400
    assert "No KOReader" in resp.get_json()["error"]


def test_install_koreader_no_device(client):
    with patch("web.routes.ereader._find_kobo_mount", return_value=None):
        resp = client.post(
            "/api/ereader/install-koreader",
            json={"koreader_url": "https://example.com/koreader.zip"},
        )
    assert resp.status_code == 404
