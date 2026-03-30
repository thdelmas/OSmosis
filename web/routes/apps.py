"""Download firmware, validate paths, and install apps via ADB."""

import hashlib
import subprocess
from pathlib import Path

from flask import Blueprint, jsonify, request

from web.core import Task, parse_devices_cfg, start_task

bp = Blueprint("apps", __name__)


@bp.route("/api/download", methods=["POST"])
def api_download():
    """Download files for a device preset."""
    device_id = request.json.get("device_id", "")
    selected = request.json.get("selected", [])

    devices = parse_devices_cfg()
    device = next((d for d in devices if d["id"] == device_id), None)
    if not device:
        return jsonify({"error": f"Device '{device_id}' not found"}), 404

    def _run(task: Task):
        target = Path.home() / "Osmosis-downloads" / device_id
        target.mkdir(parents=True, exist_ok=True)
        task.emit(f"Download directory: {target}")

        any_failed = False
        for key in selected:
            url = device.get(key, "")
            if not url:
                task.emit(f"No URL for {key}, skipping.", "warn")
                continue

            url_clean = url.split("?")[0]
            filename = Path(url_clean).name or f"{device_id}-{key}.bin"
            dest = str(target / filename)

            task.emit(f"Downloading {key}: {filename}...")
            rc = task.run_shell(["wget", "--progress=dot:giga", "-O", dest, url])
            if rc == 0:
                h = hashlib.sha256(Path(dest).read_bytes()).hexdigest()
                task.emit(f"SHA256: {h}")
            else:
                task.emit(f"Failed to download {key}.", "error")
                if Path(dest).exists():
                    Path(dest).unlink(missing_ok=True)
                any_failed = True

        task.done(not any_failed)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@bp.route("/api/validate-path", methods=["POST"])
def api_validate_path():
    """Check if a local file path exists and looks like a valid ROM/image."""
    file_path = request.json.get("path", "").strip()
    if not file_path:
        return jsonify({"valid": False, "reason": "No path provided"})

    p = Path(file_path).expanduser()
    if not p.exists():
        return jsonify({"valid": False, "reason": "File not found"})
    if not p.is_file():
        return jsonify({"valid": False, "reason": "Path is a directory, not a file"})
    size = p.stat().st_size
    if size < 1024:
        return jsonify({"valid": False, "reason": "File is too small to be a ROM or image"})
    ext = p.suffix.lower()
    known = {".zip", ".img", ".tar", ".md5", ".bin", ".apk", ".uf2", ".gz", ".xz", ".bz2"}
    return jsonify(
        {
            "valid": True,
            "filename": p.name,
            "size": size,
            "size_human": f"{size // (1024 * 1024)}MB" if size >= 1024 * 1024 else f"{size // 1024}KB",
            "ext_warning": f"Unexpected file type ({ext}). ROM files are usually .zip or .img."
            if ext not in known
            else None,
        }
    )


@bp.route("/api/apps/install", methods=["POST"])
def api_apps_install():
    """Download and install selected apps via ADB.

    JSON body: {
        "apps": [{"id": "fdroid", "name": "F-Droid", "url": "https://...", "install_method": "adb"}]
    }

    Each app is downloaded and installed via `adb install`.
    The device must be booted into the OS with USB debugging enabled.
    """
    apps = request.json.get("apps", [])
    if not apps:
        return jsonify({"error": "No apps specified"}), 400

    def _run(task: Task):
        import re

        dl_dir = Path.home() / "Osmosis-downloads" / "apps"
        dl_dir.mkdir(parents=True, exist_ok=True)

        # Verify ADB connection to a booted device
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            task.emit("ADB not available.", "error")
            task.done(False)
            return

        has_device = False
        for line in result.stdout.strip().splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                has_device = True
                break

        if not has_device:
            task.emit(
                "No device found in normal mode. Make sure the device has booted "
                "into the OS and USB debugging is enabled.",
                "error",
            )
            task.done(False)
            return

        task.emit(f"Installing {len(apps)} app(s)...")
        any_failed = False

        for app in apps:
            app_name = app.get("name", app.get("id", "app"))
            url = app.get("url", "")
            local_path = app.get("local_path", "")

            # Resolve APK path: either use a local file or download from URL
            if local_path and Path(local_path).is_file():
                dest = Path(local_path)
                task.emit(f"Using local APK: {dest}")
            elif url:
                # Sanitize filename
                safe_name = re.sub(r"[^a-zA-Z0-9._-]", "-", app_name)
                filename = f"{safe_name}.apk"
                dest = dl_dir / filename

                # Download
                task.emit(f"Downloading {app_name}...")
                rc = task.run_shell(["wget", "-q", "-O", str(dest), url])
                if rc != 0 or not dest.exists() or dest.stat().st_size < 1000:
                    task.emit(f"Failed to download {app_name}.", "error")
                    dest.unlink(missing_ok=True)
                    any_failed = True
                    continue

                h = hashlib.sha256(dest.read_bytes()).hexdigest()
                task.emit(f"Downloaded {app_name} ({dest.stat().st_size // 1024}K, SHA256: {h[:16]}...)")
            else:
                task.emit(f"No URL or local path for {app_name}, skipping.", "warn")
                continue

            # Install via ADB
            task.emit(f"Installing {app_name} on device...")
            rc = task.run_shell(["adb", "install", str(dest)])
            if rc == 0:
                task.emit(f"{app_name} installed successfully!", "success")
            else:
                task.emit(
                    f"Failed to install {app_name}. The device may need to be unlocked or USB debugging re-enabled.",
                    "error",
                )
                any_failed = True

        if any_failed:
            task.emit("Some apps failed to install.", "warn")
        else:
            task.emit("All apps installed!", "success")
        task.done(not any_failed)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})
