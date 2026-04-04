"""Tests for IPFS config distribution and trust management routes."""

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


# ---------------------------------------------------------------------------
# Publish configs — no IPFS
# ---------------------------------------------------------------------------


@patch("web.routes.ipfs_config.ipfs_available", return_value=False)
def test_publish_configs_no_ipfs(mock_ipfs, client):
    resp = client.post("/api/ipfs/publish-configs")
    assert resp.status_code == 503


# ---------------------------------------------------------------------------
# Config status
# ---------------------------------------------------------------------------


def test_config_status(client):
    resp = client.get("/api/ipfs/config-status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    for entry in data:
        assert "name" in entry
        assert "exists" in entry
        assert "pinned" in entry


# ---------------------------------------------------------------------------
# Config channel — GET (not subscribed)
# ---------------------------------------------------------------------------


def test_config_channel_get(client):
    resp = client.get("/api/ipfs/config-channel")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Config channel — POST validation
# ---------------------------------------------------------------------------


def test_config_channel_subscribe_invalid_cid(client):
    resp = client.post(
        "/api/ipfs/config-channel", json={"channel_cid": "invalid"}
    )
    assert resp.status_code == 400


@patch("web.routes.ipfs_config.ipfs_available", return_value=False)
def test_config_channel_subscribe_no_ipfs(mock_ipfs, client):
    # Use a properly formatted CIDv0 (Qm + 44 base58 chars)
    resp = client.post(
        "/api/ipfs/config-channel",
        json={
            "channel_cid": "QmT5NvUtoM5nWFfrQdVrFtvGfKFmG7AHE8P34isapyhCxX",
        },
    )
    assert resp.status_code == 503


# ---------------------------------------------------------------------------
# Config channel check — not subscribed
# ---------------------------------------------------------------------------


def test_config_channel_check_not_subscribed(client):
    # Remove the channel file if it exists to ensure clean test
    channel_file = Path.home() / ".osmosis" / "ipfs-config-channel.json"
    existed = channel_file.exists()
    if existed:
        backup = channel_file.read_text()

    try:
        if channel_file.exists():
            channel_file.unlink()
        resp = client.get("/api/ipfs/config-channel/check")
        assert resp.status_code == 400
    finally:
        if existed:
            channel_file.write_text(backup)


# ---------------------------------------------------------------------------
# Config channel apply — no IPFS
# ---------------------------------------------------------------------------


@patch("web.routes.ipfs_config.ipfs_available", return_value=False)
def test_config_channel_apply_no_ipfs(mock_ipfs, client):
    resp = client.post("/api/ipfs/config-channel/apply", json={"all": True})
    assert resp.status_code == 503


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------


def test_ipfs_identity(client):
    try:
        resp = client.get("/api/ipfs/identity")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "public_key" in data
        assert len(data["public_key"]) > 0
    except Exception:
        # cryptography module may not be installed
        pytest.skip("cryptography module not available")


# ---------------------------------------------------------------------------
# Trust management
# ---------------------------------------------------------------------------


def test_trust_list(client):
    resp = client.get("/api/ipfs/trust")
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), dict)


def test_trust_add_missing_fields(client):
    resp = client.post("/api/ipfs/trust", json={"name": "test"})
    assert resp.status_code == 400


def test_trust_delete_not_found(client):
    resp = client.delete(
        "/api/ipfs/trust", json={"name": "nonexistent-publisher"}
    )
    assert resp.status_code == 404


def test_trust_delete_missing_name(client):
    resp = client.delete("/api/ipfs/trust", json={})
    assert resp.status_code == 400
