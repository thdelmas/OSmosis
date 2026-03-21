"""Tests for IPFS helper functions."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web.ipfs_helpers import (
    ipfs_index_load,
    is_valid_cid,
    layer_cache_key,
    verify_fetched_file,
)

# ---------------------------------------------------------------------------
# CID validation
# ---------------------------------------------------------------------------


def test_valid_cid_v0():
    # CIDv0 starts with Qm and is 46 base58 chars — use a realistic one
    assert is_valid_cid("QmT5NvUtoM5nWFfrQdVrFtvGfKFmG7AHE8P34isapyhCxX") is True


def test_valid_cid_v1():
    # CIDv1 starts with bafy
    cid = "bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi"
    assert is_valid_cid(cid) is True


def test_invalid_cid_empty():
    assert is_valid_cid("") is False


def test_invalid_cid_short():
    assert is_valid_cid("Qm123") is False


def test_invalid_cid_bad_prefix():
    assert is_valid_cid("Xm" + "a" * 44) is False


def test_invalid_cid_none():
    assert is_valid_cid(None) is False


# ---------------------------------------------------------------------------
# Index load
# ---------------------------------------------------------------------------


def test_ipfs_index_load_returns_dict():
    result = ipfs_index_load()
    assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Layer cache key
# ---------------------------------------------------------------------------


def test_layer_cache_key_deterministic():
    key1 = layer_cache_key("base", distro="debian", suite="bookworm", arch="amd64")
    key2 = layer_cache_key("base", distro="debian", suite="bookworm", arch="amd64")
    assert key1 == key2


def test_layer_cache_key_different_for_different_inputs():
    key1 = layer_cache_key("base", distro="debian", suite="bookworm", arch="amd64")
    key2 = layer_cache_key("base", distro="ubuntu", suite="noble", arch="amd64")
    assert key1 != key2


def test_layer_cache_key_includes_layer_type():
    key = layer_cache_key("packages", distro="debian", suite="bookworm", arch="amd64")
    assert "packages" in key


def test_layer_cache_key_handles_list_packages():
    key1 = layer_cache_key("packages", distro="debian", packages=["vim", "git"])
    key2 = layer_cache_key("packages", distro="debian", packages=["git", "vim"])
    # Packages are sorted, so order shouldn't matter
    assert key1 == key2


# ---------------------------------------------------------------------------
# Verify fetched file
# ---------------------------------------------------------------------------


def test_verify_fetched_file(tmp_path):
    f = tmp_path / "test.bin"
    f.write_bytes(b"test content")
    result = verify_fetched_file(str(f))
    assert "sha256" in result
    assert isinstance(result["known"], bool)
    assert isinstance(result["matches"], list)
