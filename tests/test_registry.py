"""Tests for the firmware registry module."""

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web import registry


@pytest.fixture(autouse=True)
def tmp_registry(tmp_path, monkeypatch):
    """Redirect the registry to a temp file for every test."""
    reg_path = tmp_path / "firmware-registry.json"
    monkeypatch.setattr(registry, "REGISTRY_PATH", reg_path)
    return reg_path


@pytest.fixture
def sample_fw(tmp_path):
    """Create a small firmware file for testing."""
    fw = tmp_path / "firmware.bin"
    fw.write_bytes(b"OSMOSIS_TEST_FW_DATA_1234567890")
    return fw


# ---------------------------------------------------------------------------
# sha256_file
# ---------------------------------------------------------------------------


def test_sha256_file(sample_fw):
    expected = hashlib.sha256(b"OSMOSIS_TEST_FW_DATA_1234567890").hexdigest()
    assert registry.sha256_file(sample_fw) == expected


def test_sha256_file_empty(tmp_path):
    empty = tmp_path / "empty.bin"
    empty.write_bytes(b"")
    expected = hashlib.sha256(b"").hexdigest()
    assert registry.sha256_file(empty) == expected


# ---------------------------------------------------------------------------
# register / lookup
# ---------------------------------------------------------------------------


def test_register_creates_entry(sample_fw, tmp_registry):
    entry = registry.register(
        sample_fw,
        device_id="sm-t805",
        device_label="Galaxy Tab S 10.5",
        component="recovery",
        version="1.0",
        source_url="https://example.com/fw.bin",
        flash_method="heimdall",
    )
    assert entry["device_id"] == "sm-t805"
    assert entry["filename"] == "firmware.bin"
    assert entry["component"] == "recovery"
    assert entry["sha256"]
    assert entry["flashed_at"]
    # Registry file should exist now
    assert tmp_registry.exists()
    stored = json.loads(tmp_registry.read_text())
    assert len(stored) == 1


def test_register_auto_hashes(sample_fw):
    entry = registry.register(sample_fw)
    expected = hashlib.sha256(b"OSMOSIS_TEST_FW_DATA_1234567890").hexdigest()
    assert entry["sha256"] == expected


def test_register_uses_provided_hash(sample_fw):
    entry = registry.register(sample_fw, sha256="custom_hash_abc")
    assert entry["sha256"] == "custom_hash_abc"


def test_lookup_finds_matching_entries(sample_fw):
    entry = registry.register(sample_fw, device_id="dev1")
    matches = registry.lookup(entry["sha256"])
    assert len(matches) == 1
    assert matches[0]["device_id"] == "dev1"


def test_lookup_returns_empty_for_unknown():
    assert registry.lookup("nonexistent_hash") == []


def test_lookup_device(sample_fw):
    registry.register(sample_fw, device_id="pixel-5", version="1.0")
    registry.register(sample_fw, device_id="pixel-5", version="2.0")
    registry.register(sample_fw, device_id="other-device", version="1.0")
    results = registry.lookup_device("pixel-5")
    assert len(results) == 2
    assert all(r["device_id"] == "pixel-5" for r in results)


def test_lookup_device_returns_empty():
    assert registry.lookup_device("no-such-device") == []


# ---------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------


def test_verify_known_firmware(sample_fw):
    registry.register(sample_fw, device_id="dev1")
    result = registry.verify(sample_fw)
    assert result["known"] is True
    assert len(result["matches"]) == 1
    assert result["filename"] == "firmware.bin"
    assert result["size"] == sample_fw.stat().st_size


def test_verify_unknown_firmware(sample_fw):
    result = registry.verify(sample_fw)
    assert result["known"] is False
    assert result["matches"] == []


# ---------------------------------------------------------------------------
# all_entries / version_history
# ---------------------------------------------------------------------------


def test_all_entries_sorted_newest_first(sample_fw):
    registry.register(sample_fw, device_id="a", version="1.0")
    registry.register(sample_fw, device_id="b", version="2.0")
    entries = registry.all_entries()
    assert len(entries) == 2
    # Newest first — last registered should come first
    assert entries[0]["device_id"] == "b"


def test_version_history_groups_by_component(sample_fw):
    registry.register(
        sample_fw, device_id="dev1", component="esc", version="1.0"
    )
    registry.register(
        sample_fw, device_id="dev1", component="ble", version="2.0"
    )
    registry.register(
        sample_fw, device_id="dev1", component="esc", version="1.1"
    )
    history = registry.version_history("dev1")
    components = {h["component"] for h in history}
    assert "esc" in components
    assert "ble" in components
    esc = next(h for h in history if h["component"] == "esc")
    assert len(esc["versions"]) == 2


# ---------------------------------------------------------------------------
# update_ipfs_cid
# ---------------------------------------------------------------------------


def test_update_ipfs_cid(sample_fw):
    entry = registry.register(sample_fw, device_id="dev1")
    sha = entry["sha256"]
    assert registry.update_ipfs_cid(sha, "QmTestCid123") is True
    matches = registry.lookup(sha)
    assert matches[0]["ipfs_cid"] == "QmTestCid123"


def test_update_ipfs_cid_no_match():
    assert registry.update_ipfs_cid("no_such_hash", "QmTest") is False


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_load_empty_registry(tmp_registry):
    assert registry.all_entries() == []


def test_load_corrupted_registry(tmp_registry):
    tmp_registry.write_text("NOT VALID JSON!!!")
    assert registry.all_entries() == []


def test_multiple_registers_accumulate(sample_fw):
    registry.register(sample_fw, device_id="a")
    registry.register(sample_fw, device_id="b")
    registry.register(sample_fw, device_id="c")
    assert len(registry.all_entries()) == 3
