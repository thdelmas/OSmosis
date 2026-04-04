"""Lethe OTA — publish signed update manifests to IPFS/IPNS.

When a Lethe build completes, this module creates a multi-device OTA
manifest, signs it with Ed25519, pins it to IPFS, and publishes the
CID under the ``lethe-updates`` IPNS key.  Devices resolve that IPNS
name periodically and pull their own build from the manifest.

Endpoints:
  POST /api/lethe/ota/publish   — publish builds to OTA channel
  GET  /api/lethe/ota/manifest  — view current OTA manifest
  GET  /api/lethe/ota/status    — channel health check
"""

import json
import logging
import subprocess
from pathlib import Path

from flask import Blueprint, jsonify, request

from web.core import IPFS_INDEX, Task, start_task
from web.ipfs_helpers import (
    get_public_key_b64,
    ipfs_available,
    is_valid_cid,
    sign_manifest,
)
from web.registry import sha256_file
from web.routes.lethe_build import BUILD_OUTPUT_DIR

bp = Blueprint("lethe_ota", __name__)
log = logging.getLogger(__name__)

IPNS_KEY_NAME = "lethe-updates"


def _load_ipfs_index() -> dict:
    """Load the IPFS index (pinned items)."""
    if not IPFS_INDEX.exists():
        return {}
    return json.loads(IPFS_INDEX.read_text())


def _find_lethe_builds() -> dict:
    """Scan build output dir and IPFS index for available Lethe builds.

    Returns {codename: build_info} for each device that has a build.
    """
    builds = {}
    ipfs_index = _load_ipfs_index()

    # Scan local build directory for meta files
    if BUILD_OUTPUT_DIR.exists():
        for meta_path in BUILD_OUTPUT_DIR.glob("Lethe-*-meta.json"):
            try:
                meta = json.loads(meta_path.read_text())
            except (json.JSONDecodeError, OSError):
                continue

            codename = meta.get("codename")
            if not codename:
                continue

            zip_path = BUILD_OUTPUT_DIR / meta_path.name.replace(
                "-meta.json", ".zip"
            )
            if not zip_path.exists():
                continue

            # Look up IPFS CID from meta or index
            cid = meta.get("ipfs_cid", "")
            if not cid:
                index_key = f"lethe/{codename}/{meta.get('version', '')}"
                entry = ipfs_index.get(index_key, {})
                cid = entry.get("cid", "")

            if not cid:
                continue

            sha256 = meta.get("sha256") or sha256_file(str(zip_path))

            builds[codename] = {
                "cid": cid,
                "filename": zip_path.name,
                "size": zip_path.stat().st_size,
                "sha256": sha256,
                "lethe_version": meta.get("version", ""),
                "android_version": meta.get("android_version", ""),
                "security_patch": meta.get("security_patch", ""),
                "is_security_patch": meta.get("is_security_patch", False),
            }

    return builds


def _ensure_ipns_key() -> bool:
    """Ensure the IPNS key for OTA publishing exists."""
    try:
        result = subprocess.run(
            ["ipfs", "key", "list", "-l"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if IPNS_KEY_NAME in result.stdout:
            return True

        # Create the key
        subprocess.run(
            ["ipfs", "key", "gen", "--type=ed25519", IPNS_KEY_NAME],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        return True
    except Exception as e:
        log.error("Failed to ensure IPNS key: %s", e)
        return False


def _publish_to_ipns(cid: str) -> str | None:
    """Publish a CID under the lethe-updates IPNS key.

    Returns the IPNS name on success, None on failure.
    """
    try:
        result = subprocess.run(
            [
                "ipfs",
                "name",
                "publish",
                "--key",
                IPNS_KEY_NAME,
                "--lifetime",
                "48h",
                "--ttl",
                "1h",
                cid,
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            # Output: "Published to <ipns-id>: <cid>"
            parts = result.stdout.strip().split()
            return parts[2] if len(parts) >= 3 else cid
        log.error("IPNS publish failed: %s", result.stderr.strip())
        return None
    except Exception as e:
        log.error("IPNS publish error: %s", e)
        return None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@bp.route("/api/lethe/ota/publish", methods=["POST"])
def api_lethe_ota_publish():
    """Publish a signed OTA manifest to IPFS and update the IPNS channel.

    Optional JSON body:
      codenames: list[str]    — limit to specific devices (default: all)
      security_patch: str     — security patch date (e.g. "2026-03-05")
      is_security_patch: bool — mark all builds as security-only update
    """
    if not ipfs_available():
        return jsonify({"error": "IPFS daemon not available"}), 503

    body = request.json or {}
    filter_codenames = body.get("codenames", [])
    security_patch_override = body.get("security_patch", "")
    is_security_patch = body.get("is_security_patch", False)

    builds = _find_lethe_builds()
    if not builds:
        return jsonify({"error": "No Lethe builds found with IPFS CIDs"}), 404

    if filter_codenames:
        builds = {k: v for k, v in builds.items() if k in filter_codenames}
        if not builds:
            return jsonify(
                {
                    "error": "No builds match the requested codenames",
                    "available": list(_find_lethe_builds().keys()),
                }
            ), 404

    # Apply overrides
    if security_patch_override or is_security_patch:
        for info in builds.values():
            if security_patch_override:
                info["security_patch"] = security_patch_override
            if is_security_patch:
                info["is_security_patch"] = True

    def _run(task: Task):
        _publish_ota_manifest(task, builds)

    task_id = start_task(_run)
    return jsonify(
        {
            "task_id": task_id,
            "devices": list(builds.keys()),
            "build_count": len(builds),
        }
    )


def _publish_ota_manifest(task: Task, builds: dict):
    """Build, sign, pin, and publish the OTA manifest."""
    import tempfile

    task.emit("=" * 60)
    task.emit("Lethe OTA — Publishing update manifest", "info")
    task.emit(f"Devices: {', '.join(builds.keys())}")
    task.emit("=" * 60)

    # Step 1: Build manifest
    task.emit("")
    task.progress(1, 4, "Building OTA manifest")

    from datetime import datetime, timezone

    manifest = {
        "version": 2,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "channel": IPNS_KEY_NAME,
        "builds": builds,
    }

    # Serialize with consistent formatting for reproducible signatures.
    # Each build field on its own line so the device can grep-parse it.
    payload = json.dumps(manifest, indent=2, sort_keys=True)
    task.emit(f"  Manifest: {len(builds)} device(s), {len(payload)} bytes")

    # Step 2: Sign
    task.emit("")
    task.progress(2, 4, "Signing manifest", "Ed25519")
    signature = sign_manifest(payload)
    pubkey = get_public_key_b64()
    task.emit(f"  Public key: {pubkey[:16]}...")
    task.emit("  Signature OK", "success")

    # Step 3: Pin manifest + signature to IPFS as a directory
    task.emit("")
    task.progress(3, 4, "Pinning to IPFS")

    with tempfile.TemporaryDirectory() as tmpdir:
        manifest_path = Path(tmpdir) / "manifest.json"
        sig_path = Path(tmpdir) / "manifest.json.sig"

        manifest_path.write_text(payload)
        # Detached signature as base64 (device decodes with base64 -d)
        sig_path.write_text(signature)

        try:
            result = subprocess.run(
                ["ipfs", "add", "-r", "-Q", "--pin=true", tmpdir],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                task.emit(
                    f"  IPFS add failed: {result.stderr.strip()}", "error"
                )
                return
            dir_cid = result.stdout.strip()
        except Exception as e:
            task.emit(f"  IPFS add error: {e}", "error")
            return

    if not is_valid_cid(dir_cid):
        task.emit(f"  Invalid CID returned: {dir_cid}", "error")
        return

    task.emit(f"  Directory CID: {dir_cid}", "success")

    # Step 4: Publish to IPNS
    task.emit("")
    task.progress(4, 4, "Publishing to IPNS channel")

    if not _ensure_ipns_key():
        task.emit("  Failed to create IPNS key", "error")
        return

    ipns_name = _publish_to_ipns(dir_cid)
    if not ipns_name:
        task.emit("  IPNS publish failed", "error")
        return

    task.emit(f"  IPNS name: {ipns_name}", "success")
    task.emit("")
    task.emit("=" * 60)
    task.emit("OTA manifest published successfully", "success")
    task.emit(f"  Channel:  {IPNS_KEY_NAME}")
    task.emit(f"  CID:      {dir_cid}")
    task.emit(f"  Devices:  {', '.join(builds.keys())}")
    task.emit(f"  IPNS:     {ipns_name}")
    task.emit("")
    task.emit("Devices will pick up the update within 6 hours.", "info")
    task.emit("=" * 60)


@bp.route("/api/lethe/ota/manifest")
def api_lethe_ota_manifest():
    """Return the current OTA manifest (what would be published)."""
    builds = _find_lethe_builds()
    return jsonify(
        {
            "channel": IPNS_KEY_NAME,
            "builds": builds,
            "device_count": len(builds),
            "devices": list(builds.keys()),
        }
    )


@bp.route("/api/lethe/ota/status")
def api_lethe_ota_status():
    """Check the health of the OTA IPNS channel."""
    if not ipfs_available():
        return jsonify(
            {"status": "offline", "error": "IPFS not available"}
        ), 503

    # Check if IPNS key exists
    try:
        result = subprocess.run(
            ["ipfs", "key", "list", "-l"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        key_exists = IPNS_KEY_NAME in result.stdout
    except Exception:
        key_exists = False

    # Try to resolve current IPNS value
    current_cid = None
    if key_exists:
        try:
            result = subprocess.run(
                ["ipfs", "name", "resolve", IPNS_KEY_NAME],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                current_cid = result.stdout.strip()
        except Exception:
            pass

    # Count available builds
    builds = _find_lethe_builds()

    return jsonify(
        {
            "status": "active" if key_exists and current_cid else "inactive",
            "channel": IPNS_KEY_NAME,
            "ipns_key_exists": key_exists,
            "current_cid": current_cid,
            "available_builds": len(builds),
            "devices": list(builds.keys()),
            "public_key": get_public_key_b64() if key_exists else None,
        }
    )
