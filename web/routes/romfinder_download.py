"""ROM download routes — HTTP, IPFS, and local build fetching."""

from pathlib import Path

from flask import Blueprint, jsonify, request

from web.core import Task, start_task
from web.ipfs_helpers import (
    ipfs_available,
    ipfs_index_lookup,
    ipfs_pin_and_index,
    verify_fetched_file,
)

bp = Blueprint("romfinder_download", __name__)


@bp.route("/api/romfinder/download", methods=["POST"])
def api_romfinder_download():
    """Download a ROM file found by romfinder, optionally from IPFS."""
    url = request.json.get("url", "")
    filename = Path(request.json.get("filename", "rom.zip")).name
    if not filename or filename.startswith("."):
        filename = "rom.zip"
    codename = request.json.get("codename", "unknown")
    ipfs_cid = request.json.get("ipfs_cid", "")
    rom_id = request.json.get("rom_id", "")
    rom_name = request.json.get("rom_name", "")
    version = request.json.get("version", "")

    if not url and not ipfs_cid:
        return jsonify({"error": "No download URL or IPFS CID provided"}), 400

    target = Path.home() / "Osmosis-downloads" / codename
    dest = str(target / filename)

    def _run(task: Task):
        import shutil

        target.mkdir(parents=True, exist_ok=True)
        rc = 1  # assume failure unless set otherwise

        fetched_from_ipfs = False

        # Handle local API URLs (e.g. /api/lethe/builds/Lethe-1.0.0-t03g.zip)
        if url.startswith("/api/lethe/builds/"):
            local_name = Path(url.split("/")[-1]).name
            local_path = (
                Path.home() / "Osmosis-downloads" / "lethe-builds" / local_name
            )
            if local_path.exists():
                task.progress(1, 3, "Copying local build")
                task.emit(f"Source: {local_path}")
                task.emit(f"Destination: {dest}")
                size = local_path.stat().st_size
                task.emit(f"Size: {size / 1024:.1f} KB")
                task.emit("")
                shutil.copy2(str(local_path), dest)
                task.progress(2, 3, "Verifying integrity")
                rc = 0
            else:
                task.emit(f"Local build not found: {local_path}", "error")
                task.done(False)
                return
        else:
            # Check IPFS index for a cached copy if no CID was provided
            effective_cid = ipfs_cid
            if not effective_cid and ipfs_available():
                cached = ipfs_index_lookup(codename, filename)
                if cached:
                    effective_cid = cached["cid"]
                    task.emit(
                        f"Found in local IPFS cache: {effective_cid[:24]}...",
                        "info",
                    )

            if effective_cid and ipfs_available():
                task.progress(1, 4, "Fetching from IPFS")
                task.emit(f"CID: {effective_cid}")
                task.emit(f"Destination: {dest}")
                task.emit("")
                rc = task.run_shell(["ipfs", "get", "-o", dest, effective_cid])
                if rc == 0:
                    fetched_from_ipfs = True
                    task.progress(3, 4, "Download complete")
                else:
                    task.emit(
                        "IPFS fetch failed, falling back to HTTP...",
                        "warn",
                    )
                    task.emit("")

            if not fetched_from_ipfs:
                if not url:
                    task.emit("No HTTP download URL available.", "error")
                    task.done(False)
                    return
                task.progress(1, 4, "Downloading firmware")
                task.emit(f"File: {filename}")
                task.emit(f"URL: {url}", "cmd")
                task.emit(f"Destination: {dest}")
                task.emit("")
                # dl.twrp.me serves an HTML page first — the actual
                # download requires the referer to be the .html page
                if "dl.twrp.me" in url:
                    html_referer = (
                        url + ".html" if not url.endswith(".html") else url
                    )
                    download_url = (
                        url.replace(".html", "")
                        if url.endswith(".html")
                        else url
                    )
                    wget_cmd = [
                        "wget",
                        "--progress=dot:giga",
                        "-O",
                        dest,
                        f"--header=Referer: {html_referer}",
                        download_url,
                    ]
                else:
                    wget_cmd = [
                        "wget",
                        "--progress=dot:giga",
                        "-O",
                        dest,
                        url,
                    ]
                rc = task.run_shell(wget_cmd)
                if rc == 0:
                    task.progress(3, 4, "Download complete")

        if rc == 0:
            task.emit("")
            task.emit("Verifying file integrity...")
            result = verify_fetched_file(dest)
            size_mb = Path(dest).stat().st_size / (1024 * 1024)
            task.emit(f"Size: {size_mb:.1f} MB")
            task.emit(f"SHA256: {result['sha256']}")
            if result["known"]:
                task.emit(
                    "Integrity check: file matches a known-good "
                    "firmware entry.",
                    "success",
                )
            else:
                task.emit(
                    "Integrity warning: this file is NOT in the "
                    "firmware registry. Verify before flashing.",
                    "warn",
                )
            task.emit(f"Saved to: {dest}", "success")
            task.emit("")

            if not fetched_from_ipfs and ipfs_available():
                task.emit("Pinning to IPFS for future sharing...")
                cid = ipfs_pin_and_index(
                    dest,
                    key=f"{codename}/{filename}",
                    codename=codename,
                    rom_id=rom_id,
                    rom_name=rom_name,
                    version=version,
                )
                if cid:
                    task.emit(f"IPFS CID: {cid}", "success")
                    task.emit(f"Stored in IPFS index: {codename}/{filename}")
                else:
                    task.emit("IPFS pin failed (non-critical).", "warn")

            task.emit("Ready to flash.", "success")
        else:
            task.emit("Download failed.", "error")
            if Path(dest).exists():
                Path(dest).unlink(missing_ok=True)
        task.done(rc == 0)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id, "dest": dest})
