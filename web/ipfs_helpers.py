"""IPFS utility functions shared by route modules."""

import json
import subprocess

from web.core import IPFS_INDEX, cmd_exists


def ipfs_available() -> bool:
    """Check if the IPFS CLI (kubo) is installed and the daemon is reachable."""
    if not cmd_exists("ipfs"):
        return False
    try:
        r = subprocess.run(
            ["ipfs", "id"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return r.returncode == 0
    except Exception:
        return False


def ipfs_index_load() -> dict:
    """Load the local IPFS CID index."""
    if IPFS_INDEX.exists():
        try:
            return json.loads(IPFS_INDEX.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def ipfs_index_save(index: dict) -> None:
    IPFS_INDEX.parent.mkdir(parents=True, exist_ok=True)
    IPFS_INDEX.write_text(json.dumps(index, indent=2))


def ipfs_add(filepath: str) -> str | None:
    """Add a file to IPFS and return its CID, or None on failure."""
    try:
        r = subprocess.run(
            ["ipfs", "add", "-Q", "--pin", filepath],
            capture_output=True,
            text=True,
            timeout=600,
        )
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:
        pass
    return None


def ipfs_cat_to_file(cid: str, dest: str) -> bool:
    """Retrieve a file from IPFS by CID and write it to dest."""
    try:
        r = subprocess.run(
            ["ipfs", "get", "-o", dest, cid],
            capture_output=True,
            text=True,
            timeout=600,
        )
        return r.returncode == 0
    except Exception:
        return False


def ipfs_pin_ls(cid: str) -> bool:
    """Check if a CID is pinned locally."""
    try:
        r = subprocess.run(
            ["ipfs", "pin", "ls", "--type=recursive", cid],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return r.returncode == 0 and cid in r.stdout
    except Exception:
        return False
