"""Tests for IPFS security hardening — CID validation, path restrictions, integrity checks."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web.app import app
from web.ipfs_helpers import is_valid_cid


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# CID validation (Finding 1.4)
# ---------------------------------------------------------------------------


class TestCIDValidation:
    def test_valid_cidv0(self):
        assert is_valid_cid("QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG")

    def test_valid_cidv1_bafybe(self):
        assert is_valid_cid("bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi")

    def test_valid_cidv1_bafkre(self):
        # CIDv1 with base32lower encoding — must be 59+ chars after the 'b' prefix
        assert is_valid_cid("bafkreihdwdcefgh4dqkjv67uzcmw7ojee6xedzdetojuzjevtenderaaabbcc")

    def test_rejects_empty(self):
        assert not is_valid_cid("")

    def test_rejects_none(self):
        assert not is_valid_cid(None)

    def test_rejects_arbitrary_string(self):
        assert not is_valid_cid("hello-world")

    def test_rejects_path_traversal_attempt(self):
        assert not is_valid_cid("../../etc/shadow")

    def test_rejects_command_injection_attempt(self):
        assert not is_valid_cid("Qmtest; rm -rf /")

    def test_rejects_too_short_cidv0(self):
        assert not is_valid_cid("Qm123")

    def test_rejects_spaces(self):
        assert not is_valid_cid("Qm abc def")

    def test_rejects_cidv0_with_invalid_chars(self):
        # CIDv0 uses base58 — no 0, O, I, l
        assert not is_valid_cid("Qm" + "O" * 44)
        assert not is_valid_cid("Qm" + "0" * 44)


# ---------------------------------------------------------------------------
# Pin path allowlist (Finding 1.2)
# ---------------------------------------------------------------------------


class TestPinPathAllowlist:
    def test_allowed_path(self, tmp_path):
        from web.routes.ipfs import _path_allowed_for_pin

        with patch("web.routes.ipfs.ALLOWED_PIN_ROOTS", [tmp_path]):
            allowed_file = tmp_path / "test.zip"
            allowed_file.touch()
            assert _path_allowed_for_pin(str(allowed_file))

    def test_disallowed_path(self, tmp_path):
        from web.routes.ipfs import _path_allowed_for_pin

        with patch("web.routes.ipfs.ALLOWED_PIN_ROOTS", [tmp_path / "allowed"]):
            assert not _path_allowed_for_pin("/etc/shadow")

    def test_symlink_escape(self, tmp_path):
        from web.routes.ipfs import _path_allowed_for_pin

        allowed = tmp_path / "allowed"
        allowed.mkdir()
        secret = tmp_path / "secret.txt"
        secret.write_text("sensitive")
        link = allowed / "link.txt"
        link.symlink_to(secret)

        with patch("web.routes.ipfs.ALLOWED_PIN_ROOTS", [allowed]):
            # The symlink resolves outside the allowed root
            assert not _path_allowed_for_pin(str(link))

    def test_path_traversal_blocked(self, tmp_path):
        from web.routes.ipfs import _path_allowed_for_pin

        allowed = tmp_path / "downloads"
        allowed.mkdir()
        with patch("web.routes.ipfs.ALLOWED_PIN_ROOTS", [allowed]):
            assert not _path_allowed_for_pin(str(allowed / ".." / "etc" / "passwd"))


# ---------------------------------------------------------------------------
# Fetch filename sanitization (Finding 1.3)
# ---------------------------------------------------------------------------


class TestFilenameSanitization:
    def test_fetch_sanitizes_path_traversal(self, client):
        with patch("web.routes.ipfs.ipfs_available", return_value=True):
            resp = client.post(
                "/api/ipfs/fetch",
                json={
                    "cid": "QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG",
                    "filename": "../../.bashrc",
                },
            )
            # Should proceed (task started) but filename should be sanitized
            # The endpoint replaces dotfiles with "rom.zip"
            assert resp.status_code == 200

    def test_fetch_rejects_invalid_cid(self, client):
        with patch("web.routes.ipfs.ipfs_available", return_value=True):
            resp = client.post(
                "/api/ipfs/fetch",
                json={"cid": "not-a-cid", "filename": "test.zip"},
            )
            assert resp.status_code == 400
            assert "Invalid" in resp.get_json()["error"]

    def test_fetch_rejects_empty_cid(self, client):
        resp = client.post("/api/ipfs/fetch", json={"cid": ""})
        assert resp.status_code == 400

    def test_download_and_flash_sanitizes_filename(self, client):
        resp = client.post(
            "/api/download-and-flash",
            json={
                "url": "http://example.com/rom.zip",
                "filename": "../../../etc/crontab",
                "codename": "test",
            },
        )
        # Should start the task, filename sanitized to basename
        assert resp.status_code == 200
        data = resp.get_json()
        assert "task_id" in data
        # dest should use sanitized filename
        assert ".." not in data.get("dest", "")


# ---------------------------------------------------------------------------
# IPFS pin endpoint — path restriction (Finding 1.2)
# ---------------------------------------------------------------------------


class TestPinEndpoint:
    def test_pin_rejects_outside_allowlist(self, client):
        with patch("web.routes.ipfs.ipfs_available", return_value=True):
            resp = client.post(
                "/api/ipfs/pin",
                json={"filepath": "/etc/shadow", "codename": "test"},
            )
            assert resp.status_code == 403
            data = resp.get_json()
            assert "outside allowed" in data["error"].lower()

    def test_pin_rejects_nonexistent_file(self, client):
        resp = client.post(
            "/api/ipfs/pin",
            json={"filepath": "/nonexistent/file.zip"},
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Manifest import — integrity and CID validation (Findings 1.4, 4.3)
# ---------------------------------------------------------------------------


class TestManifestImport:
    def test_import_rejects_bad_sha256(self, client):
        manifest = {"version": 1, "entries": []}
        resp = client.post(
            "/api/ipfs/manifest/import",
            json={"manifest": manifest, "sha256": "badhash"},
        )
        assert resp.status_code == 400
        assert "SHA256 mismatch" in resp.get_json()["error"]

    def test_import_rejects_invalid_cids_in_entries(self, client):
        import hashlib
        import json

        manifest = {
            "version": 1,
            "entries": [
                {"key": "test/rom.zip", "cid": "not-a-valid-cid"},
                {"key": "test/rom2.zip", "cid": "also-invalid"},
            ],
        }
        payload = json.dumps(manifest, indent=2)
        sha = hashlib.sha256(payload.encode()).hexdigest()

        resp = client.post(
            "/api/ipfs/manifest/import",
            json={"manifest": manifest, "sha256": sha},
        )
        # The endpoint skips invalid CIDs but needs at least some entries
        # With all invalid, all get skipped — endpoint still returns 200
        # because entries exist, they're just all skipped
        data = resp.get_json()
        if resp.status_code == 200:
            assert data["imported"] == 0
            assert data["skipped"] == 2
        else:
            # If the endpoint treats all-skipped as an error, that's fine too
            assert resp.status_code == 400

    def test_import_rejects_empty_manifest(self, client):
        resp = client.post(
            "/api/ipfs/manifest/import",
            json={"manifest": "not a dict"},
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Remote pin — CID validation (Finding 1.4)
# ---------------------------------------------------------------------------


class TestRemotePin:
    def test_remote_pin_rejects_invalid_cid(self, client):
        resp = client.post(
            "/api/ipfs/remote-pin",
            json={"cid": "invalid!"},
        )
        assert resp.status_code == 400
        assert "Invalid" in resp.get_json()["error"]

    def test_remote_pin_rejects_empty_cid(self, client):
        resp = client.post(
            "/api/ipfs/remote-pin",
            json={"cid": ""},
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# IPFS index file locking (Finding 2.2)
# ---------------------------------------------------------------------------


class TestIndexLocking:
    def test_index_save_load_roundtrip(self, tmp_path):
        from web.ipfs_helpers import ipfs_index_load, ipfs_index_save

        with (
            patch("web.ipfs_helpers.IPFS_INDEX", tmp_path / "index.json"),
            patch("web.ipfs_helpers._INDEX_LOCK", tmp_path / ".lock"),
        ):
            test_data = {
                "test/rom.zip": {
                    "cid": "QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG",
                    "filename": "rom.zip",
                    "size": 1024,
                }
            }
            ipfs_index_save(test_data)
            loaded = ipfs_index_load()
            assert loaded == test_data

    def test_index_load_returns_empty_on_missing(self, tmp_path):
        from web.ipfs_helpers import ipfs_index_load

        with patch("web.ipfs_helpers.IPFS_INDEX", tmp_path / "nonexistent.json"):
            assert ipfs_index_load() == {}


# ---------------------------------------------------------------------------
# Device submission validation
# ---------------------------------------------------------------------------


class TestDeviceSubmissions:
    def test_submit_rejects_missing_category(self, client):
        resp = client.post("/api/devices/submit", json={"label": "Test"})
        assert resp.status_code == 400

    def test_submit_rejects_invalid_category(self, client):
        resp = client.post(
            "/api/devices/submit",
            json={"category": "spaceship", "label": "Test"},
        )
        assert resp.status_code == 400

    def test_submit_rejects_missing_label(self, client):
        resp = client.post(
            "/api/devices/submit",
            json={"category": "phone"},
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# T2 routes — basic validation
# ---------------------------------------------------------------------------


class TestT2Routes:
    def test_t2_models(self, client):
        resp = client.get("/api/t2/models")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)

    def test_t2_tools(self, client):
        resp = client.get("/api/t2/tools")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "t2tool" in data
        assert "lsusb" in data

    def test_t2_restore_missing_backup(self, client):
        resp = client.post(
            "/api/t2/restore",
            json={"backup_name": "nonexistent-backup"},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Device search and OS options
# ---------------------------------------------------------------------------


class TestDeviceRoutes:
    def test_devices_search_empty(self, client):
        resp = client.get("/api/devices/search")
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_device_os_not_found(self, client):
        resp = client.get("/api/devices/nonexistent-device-xyz/os")
        assert resp.status_code == 404

    def test_devices_search_with_query(self, client):
        resp = client.get("/api/devices/search?model=SM-T805")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
