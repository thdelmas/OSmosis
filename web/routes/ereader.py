"""E-reader routes — Kobo KOReader/NickelMenu install via USB mass storage.

Detects mounted Kobo e-readers by looking for the `.kobo/` directory,
then copies KOReader and NickelMenu files to the correct locations.
"""

import subprocess
import zipfile
from pathlib import Path

from flask import Blueprint, jsonify, request

from web.core import Task, start_task

bp = Blueprint("ereader", __name__)


def _find_kobo_mount() -> dict | None:
    """Detect a mounted Kobo e-reader by looking for .kobo/ directory."""
    try:
        mounts = Path("/proc/mounts").read_text()
    except OSError:
        return None

    for line in mounts.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        mount_point = Path(parts[1])
        kobo_dir = mount_point / ".kobo"
        if kobo_dir.is_dir():
            # Read device info if available
            version_file = kobo_dir / "version"
            model = ""
            firmware = ""
            if version_file.exists():
                try:
                    content = version_file.read_text().strip()
                    # Format: N613,4.38.22801,4.38.22801,4.38.22801,...
                    vparts = content.split(",")
                    if vparts:
                        model = vparts[0]
                    if len(vparts) > 1:
                        firmware = vparts[1]
                except OSError:
                    pass
            return {
                "mount": str(mount_point),
                "model": model,
                "firmware": firmware,
                "kobo_dir": str(kobo_dir),
            }
    return None


@bp.route("/api/ereader/detect")
def api_ereader_detect():
    """Detect a connected Kobo e-reader in USB mass storage mode."""
    kobo = _find_kobo_mount()
    if not kobo:
        return (
            jsonify(
                {
                    "error": "no_device",
                    "hint": "Connect your Kobo via USB and choose 'Connect' "
                    "(not 'Charge only') when prompted on the device.",
                }
            ),
            404,
        )
    return jsonify(kobo)


@bp.route("/api/ereader/install-koreader", methods=["POST"])
def api_install_koreader():
    """Install KOReader and optionally NickelMenu on a mounted Kobo.

    JSON body: {
        "koreader_url": "https://github.com/.../KOReader-kobo-arm-linux.zip",
        "nickelmenu_url": "https://github.com/.../NickelMenu-kobo.zip"  (optional)
    }
    """
    body = request.json or {}
    koreader_url = body.get("koreader_url", "").strip()
    nickelmenu_url = body.get("nickelmenu_url", "").strip()

    if not koreader_url:
        return jsonify({"error": "No KOReader download URL provided"}), 400

    kobo = _find_kobo_mount()
    if not kobo:
        return jsonify({"error": "Kobo not detected. Connect via USB first."}), 404

    mount = Path(kobo["mount"])

    def _run(task: Task):
        dl_dir = Path.home() / "Osmosis-downloads" / "ereader"
        dl_dir.mkdir(parents=True, exist_ok=True)

        # Download KOReader
        task.emit("Downloading KOReader...", "info")
        koreader_zip = dl_dir / "koreader-kobo.zip"
        rc = task.run_shell(["curl", "-fSL", "--max-time", "300", "-o", str(koreader_zip), koreader_url])
        if rc != 0:
            task.emit("Failed to download KOReader.", "error")
            task.done(False)
            return

        # Extract KOReader to Kobo root
        task.emit("Installing KOReader...", "info")
        try:
            with zipfile.ZipFile(koreader_zip, "r") as zf:
                zf.extractall(mount)
            task.emit("KOReader installed.", "success")
        except (zipfile.BadZipFile, OSError) as e:
            task.emit(f"Failed to extract KOReader: {e}", "error")
            task.done(False)
            return

        # Download and install NickelMenu (optional)
        if nickelmenu_url:
            task.emit("Downloading NickelMenu...", "info")
            nm_zip = dl_dir / "nickelmenu-kobo.zip"
            rc = task.run_shell(["curl", "-fSL", "--max-time", "120", "-o", str(nm_zip), nickelmenu_url])
            if rc == 0:
                try:
                    with zipfile.ZipFile(nm_zip, "r") as zf:
                        zf.extractall(mount)
                    task.emit("NickelMenu installed.", "success")
                except (zipfile.BadZipFile, OSError) as e:
                    task.emit(f"Failed to extract NickelMenu: {e}", "error")
            else:
                task.emit("Failed to download NickelMenu (non-fatal).", "warn")

        # Safely eject
        task.emit("Syncing filesystem...", "info")
        subprocess.run(["sync"], timeout=30)
        task.emit(
            "Done! Safely eject the Kobo from your file manager, then "
            "disconnect USB. KOReader will appear in the Kobo menu.",
            "success",
        )
        task.done(True)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})
