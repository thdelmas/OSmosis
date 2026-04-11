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
    "t0lte": ("Samsung", "Galaxy Note II LTE"),
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


@bp.route("/api/lethe/pair", methods=["POST"])
def api_lethe_pair():
    """Push provider config to connected LETHE device over USB.

    JSON body: {"provider": "anthropic", "key": "sk-...", "model": "..."}
    Uses ADB to inject the key into the WebView's localStorage.
    """
    import json
    import subprocess

    body = request.json or {}
    provider = body.get("provider", "")
    key = body.get("key", "")
    model = body.get("model", "")

    if not provider or not key:
        return jsonify({"error": "provider and key are required"}), 400

    # Build JS to inject into the running WebView
    js_parts = [
        f"localStorage.setItem('lethe_key_{provider}','{key}')",
    ]
    if model:
        js_parts.append(
            f"localStorage.setItem('lethe_model_{provider}','{model}')"
        )
    # Update live provider array
    js_parts.append(
        "if(typeof providers!=='undefined'){"
        f"for(var i=0;i<providers.length;i++)"
        f"{{if(providers[i].name==='{provider}')"
        f"{{providers[i].key='{key}';"
        + (f"providers[i].model='{model}';" if model else "")
        + "}}}"
        "}"
    )
    js_code = ";".join(js_parts)

    # Push via ADB content provider or broadcast
    # Cleanest: write a temp file the app reads on next launch
    config_line = json.dumps(
        {"provider": provider, "key": key, "model": model}
    )

    try:
        # Write config to device, the app reads it on next start
        result = subprocess.run(
            [
                "adb",
                "shell",
                f"echo '{config_line}' > /data/local/tmp/lethe-pair.json",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        # Also inject directly into the running WebView via input
        subprocess.run(
            [
                "adb",
                "shell",
                "am",
                "broadcast",
                "-a",
                "lethe.intent.PAIR",
                "--es",
                "provider",
                provider,
                "--es",
                "key",
                key,
                "--es",
                "model",
                model or "",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return jsonify({"ok": True, "provider": provider})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/lethe/pair-qr")
def api_lethe_pair_qr():
    """Generate a QR code containing provider config for LETHE device pairing.

    Query params: provider, key, model (all optional).
    Returns a PNG QR code image.
    """
    import io
    import json

    try:
        import qrcode
    except ImportError:
        return jsonify({"error": "qrcode library not installed"}), 500

    provider = request.args.get("provider", "anthropic")
    key = request.args.get("key", "")
    model = request.args.get("model", "")

    if not key:
        return jsonify({"error": "key is required"}), 400

    payload = json.dumps(
        {"lethe_pair": True, "provider": provider, "key": key, "model": model},
        separators=(",", ":"),
    )

    img = qrcode.make(payload, box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png", download_name="lethe-pair.png")


@bp.route("/api/lethe/builds/<filename>")
def api_lethe_build_download(filename):
    """Serve a local Lethe build ZIP."""
    # Sanitize filename to prevent path traversal
    safe_name = Path(filename).name
    build_path = BUILD_OUTPUT_DIR / safe_name
    if not build_path.exists() or not safe_name.endswith(".zip"):
        return jsonify({"error": "build_not_found"}), 404
    return send_file(build_path, as_attachment=True, download_name=safe_name)
