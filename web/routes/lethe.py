"""Lethe routes — L.E.T.H.E. (Logical Erasure & Total History Elimination).

Privacy-hardened Android fork based on LineageOS.

Provides endpoints for:
  - Listing supported devices and their build status
  - Triggering builds for specific devices
  - Serving Lethe images (local or via IPFS)
  - Managing privacy overlay configuration
"""

from pathlib import Path

import yaml
from flask import Blueprint, jsonify, request, send_file

from web.core import Task, start_task
from web.device_profile import load_all_profiles
from web.routes.lethe_build import BUILD_OUTPUT_DIR, build_lethe

bp = Blueprint("lethe", __name__)

MANIFEST_PATH = (
    Path(__file__).resolve().parent.parent.parent / "lethe" / "manifest.yaml"
)

# Fallback device info when no profile YAML exists — derived from manifest.yaml
_LETHE_DEVICE_INFO: dict[str, tuple[str, str]] = {
    # codename: (brand, friendly_name)
    "chagalllte": ("Samsung", "Galaxy Tab S 10.5"),
    "t03g": ("Samsung", "Galaxy Note II"),
    "panther": ("Google", "Pixel 7"),
    "cheetah": ("Google", "Pixel 7 Pro"),
    "lynx": ("Google", "Pixel 7a"),
    "shiba": ("Google", "Pixel 8"),
    "husky": ("Google", "Pixel 8 Pro"),
    "akita": ("Google", "Pixel 8a"),
    "caiman": ("Google", "Pixel 9"),
    "komodo": ("Google", "Pixel 9 Pro"),
    "tokay": ("Google", "Pixel 9 Pro Fold"),
    "spacewar": ("Nothing", "Phone (1)"),
    "pong": ("Nothing", "Phone (2)"),
    "pacman": ("Nothing", "Phone (2a)"),
    "FP4": ("Fairphone", "Fairphone 4"),
    "FP5": ("Fairphone", "Fairphone 5"),
    "instantnoodlep": ("OnePlus", "8 Pro"),
    "lemonades": ("OnePlus", "9"),
    "martini": ("OnePlus", "9 Pro"),
    "courbet": ("Xiaomi", "Mi 11 Lite 4G"),
    "renoir": ("Xiaomi", "Mi 11 Lite 5G"),
    "hawao": ("Motorola", "Moto G7 Plus"),
    "devon": ("Motorola", "Moto G52"),
    "pdx206": ("Sony", "Xperia 1 II"),
    "pdx215": ("Sony", "Xperia 1 III"),
}


def _fmt_size(size_bytes: int) -> str:
    """Human-readable file size (KB for < 1 MB, else MB)."""
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def _load_manifest() -> dict:
    """Load the Lethe build manifest."""
    if not MANIFEST_PATH.exists():
        return {}
    return yaml.safe_load(MANIFEST_PATH.read_text()) or {}


def _get_supported_codenames() -> list[str]:
    """Return list of device codenames supported by Lethe.

    Devices can be plain strings or dicts with a 'codename' key
    (for per-device overrides like base_version).
    """
    manifest = _load_manifest()
    codenames = []
    for entry in manifest.get("devices", []):
        if isinstance(entry, str):
            codenames.append(entry)
        elif isinstance(entry, dict) and "codename" in entry:
            codenames.append(entry["codename"])
    return codenames


def _get_features() -> dict:
    """Return the privacy feature configuration."""
    manifest = _load_manifest()
    return manifest.get("features", {})


def _build_path(codename: str) -> Path | None:
    """Return the expected build output path for a codename."""
    manifest = _load_manifest()
    version = manifest.get("version", "1.0.0")
    return BUILD_OUTPUT_DIR / f"Lethe-{version}-{codename}.zip"


def _build_exists(codename: str) -> bool:
    """Check if a build exists for a codename."""
    path = _build_path(codename)
    return path.exists() if path else False


# ---------------------------------------------------------------------------
# Info endpoints
# ---------------------------------------------------------------------------


@bp.route("/api/lethe/info")
def api_lethe_info():
    """Return Lethe metadata, supported devices, and feature list."""
    manifest = _load_manifest()
    if not manifest:
        return jsonify({"error": "Lethe manifest not found"}), 404

    raw_devices = manifest.get("devices", [])

    # Match codenames to device profiles for friendly names
    all_profiles = load_all_profiles()
    devices = []
    for entry in raw_devices:
        codename = entry["codename"] if isinstance(entry, dict) else entry
        profile = None
        for p in all_profiles:
            if p.codename == codename:
                profile = p
                break
        fallback = _LETHE_DEVICE_INFO.get(codename)
        devices.append(
            {
                "codename": codename,
                "name": profile.name if profile else (fallback[1] if fallback else codename),
                "brand": profile.brand if profile else (fallback[0] if fallback else ""),
                "category": profile.category if profile else "phone",
                "has_build": _build_exists(codename),
            }
        )

    return jsonify(
        {
            "id": manifest.get("id", "lethe"),
            "name": manifest.get("name", "Lethe"),
            "version": manifest.get("version", ""),
            "base": manifest.get("base", "lineageos"),
            "base_version": manifest.get("base_version", ""),
            "android_version": manifest.get("android_version", ""),
            "description": manifest.get("description", ""),
            "device_count": len(raw_devices),
            "devices": devices,
            "features": _get_features(),
        }
    )


@bp.route("/api/lethe/devices")
def api_lethe_devices():
    """List all devices supported by Lethe with build status."""
    codenames = _get_supported_codenames()
    all_profiles = load_all_profiles()

    devices = []
    for codename in codenames:
        profile = None
        for p in all_profiles:
            if p.codename == codename:
                profile = p
                break

        fallback = _LETHE_DEVICE_INFO.get(codename)
        build_path = _build_path(codename)
        devices.append(
            {
                "codename": codename,
                "name": profile.name if profile else (fallback[1] if fallback else codename),
                "brand": profile.brand if profile else (fallback[0] if fallback else ""),
                "model": profile.model if profile else (fallback[1] if fallback else ""),
                "flash_tool": profile.flash_tool if profile else "",  # no fallback for flash_tool
                "has_build": build_path.exists() if build_path else False,
                "build_size": _fmt_size(build_path.stat().st_size)
                if build_path and build_path.exists()
                else "0 KB",
            }
        )

    return jsonify(devices)


@bp.route("/api/lethe/features")
def api_lethe_features():
    """Return the Lethe privacy feature configuration."""
    features = _get_features()
    if not features:
        return jsonify({"error": "No features defined"}), 404
    return jsonify(features)


# ---------------------------------------------------------------------------
# Build endpoints
# ---------------------------------------------------------------------------


@bp.route("/api/lethe/build", methods=["POST"])
def api_lethe_build():
    """Start a Lethe build for a specific device.

    JSON body: {"codename": "spacewar", "ipfs_publish": false}
    """
    body = request.json or {}
    codename = body.get("codename", "")
    ipfs_publish = body.get("ipfs_publish", False)

    if not codename:
        return jsonify({"error": "codename is required"}), 400

    supported = _get_supported_codenames()
    if codename not in supported:
        return jsonify(
            {
                "error": f"Device '{codename}' is not supported by Lethe",
                "supported": supported,
            }
        ), 400

    manifest = _load_manifest()

    def _run(task: Task):
        build_lethe(task, codename, manifest, ipfs_publish)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id, "codename": codename})


# ---------------------------------------------------------------------------
# Build listing
# ---------------------------------------------------------------------------


@bp.route("/api/lethe/builds")
def api_lethe_builds():
    """List completed Lethe builds."""
    import json

    BUILD_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    builds = []
    for f in sorted(BUILD_OUTPUT_DIR.glob("Lethe-*.zip"), reverse=True):
        meta_path = f.with_name(f.stem + "-meta.json")
        meta = None
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text())
            except Exception:
                pass

        builds.append(
            {
                "filename": f.name,
                "path": str(f),
                "size": _fmt_size(f.stat().st_size),
                "meta": meta,
            }
        )
    return jsonify(builds)


@bp.route("/api/lethe/builds/<filename>")
def api_lethe_build_download(filename):
    """Serve a local Lethe build ZIP."""
    # Sanitize filename to prevent path traversal
    safe_name = Path(filename).name
    build_path = BUILD_OUTPUT_DIR / safe_name
    if not build_path.exists() or not safe_name.endswith(".zip"):
        return jsonify({"error": "build_not_found"}), 404
    return send_file(build_path, as_attachment=True, download_name=safe_name)
