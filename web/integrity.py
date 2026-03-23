"""Firmware integrity monitoring and privilege audit logging.

9.3 — Scheduled checksum verification of cached firmware images.
9.4 — Audit log of all privilege-escalated operations.

The integrity checker scans ~/Osmosis-downloads/ and ~/.osmosis/backups/
for firmware files and verifies their SHA256 against the registry. Results
are persisted to ~/.osmosis/integrity-report.json.

The audit log records every sudo/root operation that OSmosis performs,
stored at ~/.osmosis/audit-log.jsonl (one JSON object per line).
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)

OSMOSIS_DIR = Path.home() / ".osmosis"
DOWNLOADS_DIR = Path.home() / "Osmosis-downloads"
BACKUPS_DIR = OSMOSIS_DIR / "backups"
INTEGRITY_REPORT = OSMOSIS_DIR / "integrity-report.json"
AUDIT_LOG = OSMOSIS_DIR / "audit-log.jsonl"

FIRMWARE_EXTENSIONS = {".zip", ".img", ".tar", ".tar.md5", ".bin", ".hex", ".elf", ".uf2"}


# ---------------------------------------------------------------------------
# 9.3 — Firmware integrity monitoring
# ---------------------------------------------------------------------------


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _find_firmware_files() -> list[Path]:
    """Find all firmware files in download and backup directories."""
    files = []
    for base_dir in [DOWNLOADS_DIR, BACKUPS_DIR]:
        if not base_dir.exists():
            continue
        for f in base_dir.rglob("*"):
            if f.is_file() and f.suffix.lower() in FIRMWARE_EXTENSIONS:
                files.append(f)
    return sorted(files)


def check_integrity() -> dict:
    """Verify all cached firmware files against expected checksums.

    For each file, checks:
    1. Against the firmware registry (known-good hashes from previous flashes)
    2. Against a stored hash from the last integrity scan (detect tampering)

    Returns a report dict with ok/tampered/unknown/missing lists.
    """
    from web.registry import lookup as registry_lookup

    # Load previous report for comparison
    previous: dict[str, str] = {}
    if INTEGRITY_REPORT.exists():
        try:
            prev_data = json.loads(INTEGRITY_REPORT.read_text())
            previous = prev_data.get("file_hashes", {})
        except Exception:
            pass

    files = _find_firmware_files()
    results = {"ok": [], "tampered": [], "unknown": [], "errors": []}
    file_hashes: dict[str, str] = {}

    for f in files:
        try:
            current_hash = _sha256(f)
            file_hashes[str(f)] = current_hash
            rel_path = str(f)

            # Check registry
            registry_matches = registry_lookup(current_hash)

            # Check against previous scan
            prev_hash = previous.get(str(f))

            if registry_matches:
                results["ok"].append(
                    {
                        "path": rel_path,
                        "sha256": current_hash,
                        "registry_match": registry_matches[0].get("filename", ""),
                        "status": "verified",
                    }
                )
            elif prev_hash and prev_hash != current_hash:
                results["tampered"].append(
                    {
                        "path": rel_path,
                        "sha256": current_hash,
                        "expected_sha256": prev_hash,
                        "status": "tampered",
                    }
                )
            elif prev_hash and prev_hash == current_hash:
                results["ok"].append(
                    {
                        "path": rel_path,
                        "sha256": current_hash,
                        "status": "unchanged",
                    }
                )
            else:
                results["unknown"].append(
                    {
                        "path": rel_path,
                        "sha256": current_hash,
                        "status": "unknown",
                    }
                )
        except Exception as e:
            results["errors"].append(
                {
                    "path": str(f),
                    "error": str(e),
                    "status": "error",
                }
            )

    # Check for files that existed before but are now missing
    for prev_path in previous:
        if not Path(prev_path).exists():
            results["tampered"].append(
                {
                    "path": prev_path,
                    "sha256": "",
                    "expected_sha256": previous[prev_path],
                    "status": "missing",
                }
            )

    report = {
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "files_scanned": len(files),
        "ok_count": len(results["ok"]),
        "tampered_count": len(results["tampered"]),
        "unknown_count": len(results["unknown"]),
        "error_count": len(results["errors"]),
        "all_clear": len(results["tampered"]) == 0 and len(results["errors"]) == 0,
        "results": results,
        "file_hashes": file_hashes,
    }

    # Persist report
    OSMOSIS_DIR.mkdir(parents=True, exist_ok=True)
    INTEGRITY_REPORT.write_text(json.dumps(report, indent=2) + "\n")

    return report


def get_last_report() -> dict | None:
    """Load the most recent integrity report."""
    if not INTEGRITY_REPORT.exists():
        return None
    try:
        return json.loads(INTEGRITY_REPORT.read_text())
    except Exception:
        return None


# ---------------------------------------------------------------------------
# 9.4 — Privilege escalation audit log
# ---------------------------------------------------------------------------


def audit_log(
    action: str,
    command: list[str],
    *,
    user: str = "",
    source_ip: str = "",
    task_id: str = "",
    result: str = "",
    details: dict | None = None,
) -> None:
    """Append an entry to the audit log.

    Called whenever OSmosis runs a privileged command (sudo).
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "command": command,
        "user": user,
        "source_ip": source_ip,
        "task_id": task_id,
        "result": result,
    }
    if details:
        entry["details"] = details

    OSMOSIS_DIR.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


def get_audit_log(limit: int = 100) -> list[dict]:
    """Read the most recent audit log entries."""
    if not AUDIT_LOG.exists():
        return []

    lines = AUDIT_LOG.read_text().strip().splitlines()
    entries = []
    for line in reversed(lines[-limit:]):
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries
