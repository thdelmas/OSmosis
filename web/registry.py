"""Firmware hash registry — tracks every firmware Osmosis has ever flashed.

Stores SHA256 hashes alongside metadata (device, version, source, date) in a
JSON file at ~/.osmosis/firmware-registry.json.  Used for:

- Pre-flash verification: confirm a downloaded file matches a known-good hash.
- Audit trail: see what was flashed, when, and from where.
- Rollback: find a previous firmware version for a device.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

REGISTRY_PATH = Path.home() / ".osmosis" / "firmware-registry.json"


def _load() -> list[dict]:
    if not REGISTRY_PATH.exists():
        return []
    try:
        return json.loads(REGISTRY_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return []


def _save(entries: list[dict]) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(json.dumps(entries, indent=2) + "\n")


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def register(
    fw_path: str | Path,
    *,
    device_id: str = "",
    device_label: str = "",
    component: str = "",
    version: str = "",
    source_url: str = "",
    flash_method: str = "",
    sha256: str = "",
) -> dict:
    """Record a firmware file in the registry. Returns the new entry."""
    fw_path = Path(fw_path)
    if not sha256:
        sha256 = sha256_file(fw_path)

    entry = {
        "sha256": sha256,
        "filename": fw_path.name,
        "size": fw_path.stat().st_size if fw_path.exists() else 0,
        "device_id": device_id,
        "device_label": device_label,
        "component": component,
        "version": version,
        "source_url": source_url,
        "flash_method": flash_method,
        "flashed_at": datetime.now(timezone.utc).isoformat(),
    }

    entries = _load()
    entries.append(entry)
    _save(entries)
    return entry


def lookup(sha256: str) -> list[dict]:
    """Find all registry entries matching a SHA256 hash."""
    return [e for e in _load() if e["sha256"] == sha256]


def lookup_device(device_id: str) -> list[dict]:
    """Find all registry entries for a device, newest first."""
    entries = [e for e in _load() if e["device_id"] == device_id]
    entries.sort(key=lambda e: e.get("flashed_at", ""), reverse=True)
    return entries


def verify(fw_path: str | Path) -> dict:
    """Verify a firmware file against the registry.

    Returns:
        {
            "sha256": "<hash>",
            "known": True/False,
            "matches": [<matching entries>],
            "filename": "<name>",
            "size": <bytes>
        }
    """
    fw_path = Path(fw_path)
    sha256 = sha256_file(fw_path)
    matches = lookup(sha256)
    return {
        "sha256": sha256,
        "known": len(matches) > 0,
        "matches": matches,
        "filename": fw_path.name,
        "size": fw_path.stat().st_size,
    }


def all_entries() -> list[dict]:
    """Return all registry entries, newest first."""
    entries = _load()
    entries.sort(key=lambda e: e.get("flashed_at", ""), reverse=True)
    return entries


def version_history(device_id: str) -> list[dict]:
    """Return firmware version history for a device, grouped by component.

    Returns a list of {component, versions: [{version, sha256, flashed_at, ...}]}
    """
    entries = lookup_device(device_id)
    by_component: dict[str, list[dict]] = {}
    for e in entries:
        comp = e.get("component", "unknown")
        if comp not in by_component:
            by_component[comp] = []
        by_component[comp].append(e)
    return [{"component": comp, "versions": versions} for comp, versions in by_component.items()]


def update_ipfs_cid(sha256: str, cid: str) -> bool:
    """Attach an IPFS CID to all registry entries matching a SHA256 hash."""
    entries = _load()
    updated = False
    for e in entries:
        if e["sha256"] == sha256:
            e["ipfs_cid"] = cid
            updated = True
    if updated:
        _save(entries)
    return updated
