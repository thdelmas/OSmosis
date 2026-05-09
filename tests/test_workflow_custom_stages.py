"""Tests for user-defined workflow stage chains.

Closes the last 12.5 item: "User-defined workflow templates (chain stages
in any order)." Users can POST to /api/workflows with a custom stages list
(e.g. ["download", "verify"]) instead of picking from the named templates.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web.app import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Test client with WORKFLOWS_DIR redirected and run_workflow stubbed.

    The route's run_workflow spawns a background thread that races with the
    test's read of the persisted state file. Stub it: tests here verify the
    HTTP contract (validation, stage list, ordering), not stage execution.
    """
    monkeypatch.setattr("web.workflow_engine.WORKFLOWS_DIR", tmp_path)
    monkeypatch.setattr("web.routes.profiles.run_workflow", lambda wid, **_: f"task-{wid}")
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_custom_stages_accepted(client):
    resp = client.post(
        "/api/workflows",
        json={
            "device_id": "test-device",
            "stages": ["download", "verify"],
            "url": "https://example.com/fw.zip",
        },
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert "workflow_id" in body
    # Confirm stages were honored
    detail = client.get(f"/api/workflows/{body['workflow_id']}").get_json()
    stage_ids = [s["id"] for s in detail["stages"]]
    assert stage_ids == ["download", "verify"]


def test_custom_stages_rejects_unknown_stage(client):
    resp = client.post(
        "/api/workflows",
        json={
            "device_id": "test-device",
            "stages": ["download", "do-something-evil", "verify"],
        },
    )
    assert resp.status_code == 400
    assert "do-something-evil" in resp.get_json()["error"]


def test_custom_stages_rejects_empty_list(client):
    resp = client.post(
        "/api/workflows",
        json={"device_id": "test-device", "stages": []},
    )
    assert resp.status_code == 400


def test_custom_stages_rejects_non_list(client):
    resp = client.post(
        "/api/workflows",
        json={"device_id": "test-device", "stages": "download,verify"},
    )
    assert resp.status_code == 400


def test_custom_stages_can_reorder(client):
    """The stages list dictates execution order — backup before download is allowed."""
    resp = client.post(
        "/api/workflows",
        json={
            "device_id": "test-device",
            "stages": ["backup", "download", "verify", "flash"],
        },
    )
    assert resp.status_code == 200
    detail = client.get(f"/api/workflows/{resp.get_json()['workflow_id']}").get_json()
    assert [s["id"] for s in detail["stages"]] == [
        "backup",
        "download",
        "verify",
        "flash",
    ]


def test_template_still_works(client):
    """Template selection must still work when `stages` is omitted."""
    resp = client.post(
        "/api/workflows",
        json={
            "device_id": "test-device",
            "template": "verify-only",
            "url": "https://example.com/fw.zip",
        },
    )
    assert resp.status_code == 200
    detail = client.get(f"/api/workflows/{resp.get_json()['workflow_id']}").get_json()
    assert [s["id"] for s in detail["stages"]] == ["download", "verify"]


def test_default_stages_when_neither_given(client):
    resp = client.post(
        "/api/workflows",
        json={
            "device_id": "test-device",
            "url": "https://example.com/fw.zip",
        },
    )
    assert resp.status_code == 200
    detail = client.get(f"/api/workflows/{resp.get_json()['workflow_id']}").get_json()
    # Default chain = full pipeline
    stage_ids = [s["id"] for s in detail["stages"]]
    assert "download" in stage_ids
    assert "flash" in stage_ids
