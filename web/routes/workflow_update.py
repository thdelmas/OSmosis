"""ROM update workflow route — backup, download, verify, sideload."""

from pathlib import Path

from flask import Blueprint, jsonify, request

from web.core import Task, start_task
from web.ipfs_helpers import ipfs_available, ipfs_pin_and_index, verify_fetched_file

bp = Blueprint("workflow_update", __name__)


@bp.route("/api/update-rom", methods=["POST"])
def api_update_rom():
    """One-click ROM update: backup -> download -> sideload.

    JSON body: {
        "codename": "chagalllte",
        "url": "https://...",          (HTTP download URL)
        "ipfs_cid": "Qm...",          (optional, preferred over HTTP)
        "filename": "lineage-21-....zip",
        "rom_id": "lineageos",
        "rom_name": "LineageOS",
        "version": "21.0",
        "backup_partitions": ["boot", "recovery", "efs"]  (optional, default: boot+recovery)
    }
    """
    body = request.json or {}
    codename = body.get("codename", "unknown")
    url = body.get("url", "")
    ipfs_cid = body.get("ipfs_cid", "")
    filename = Path(body.get("filename", "rom.zip")).name
    if not filename or filename.startswith("."):
        filename = "rom.zip"
    rom_id = body.get("rom_id", "")
    rom_name = body.get("rom_name", "")
    version = body.get("version", "")
    backup_parts = body.get("backup_partitions", ["boot", "recovery"])

    if not url and not ipfs_cid:
        return jsonify({"error": "No download URL or IPFS CID provided"}), 400

    target = Path.home() / "Osmosis-downloads" / codename
    dest = str(target / filename)

    def _run(task: Task):
        import hashlib
        import subprocess
        import time

        # === Phase 1: Pre-flight check ===
        task.emit("=== Phase 1: Pre-flight check ===", "info")
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=5)
        if "device" not in result.stdout:
            task.emit("No device detected via ADB. Connect device and enable USB debugging.", "error")
            task.done(False)
            return
        task.emit("Device connected via ADB.", "success")

        # Check battery
        batt = subprocess.run(
            ["adb", "shell", "dumpsys", "battery"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        import re

        m = re.search(r"level:\s*(\d+)", batt.stdout)
        if m:
            level = int(m.group(1))
            task.emit(f"Battery level: {level}%")
            if level < 25:
                task.emit("Battery too low (< 25%). Charge before updating.", "error")
                task.done(False)
                return
        task.emit("")

        # === Phase 2: Backup ===
        task.emit("=== Phase 2: Backup critical partitions ===", "info")
        from datetime import datetime

        from web.core import BACKUP_DIR

        backup_name = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_dir = BACKUP_DIR / backup_name
        backup_dir.mkdir(parents=True, exist_ok=True)

        for part in backup_parts:
            task.emit(f"Backing up {part}...")
            rc = task.run_shell(
                [
                    "adb",
                    "shell",
                    "su",
                    "-c",
                    f"dd if=/dev/block/by-name/{part} of=/sdcard/{part}.img bs=4096",
                ]
            )
            if rc == 0:
                task.run_shell(["adb", "pull", f"/sdcard/{part}.img", str(backup_dir / f"{part}.img")])
                task.run_shell(["adb", "shell", "rm", f"/sdcard/{part}.img"])

        # Write checksums
        checksums = []
        for img in backup_dir.glob("*.img"):
            h = hashlib.sha256(img.read_bytes()).hexdigest()
            checksums.append(f"{h}  {img.name}")
        (backup_dir / "checksums.sha256").write_text("\n".join(checksums) + "\n")
        task.emit(f"Backup saved to {backup_dir}", "success")
        task.emit("")

        # === Phase 3: Download ===
        task.emit("=== Phase 3: Download ROM update ===", "info")
        target.mkdir(parents=True, exist_ok=True)

        fetched_from_ipfs = False
        effective_cid = ipfs_cid
        if not effective_cid and ipfs_available():
            from web.ipfs_helpers import ipfs_index_lookup

            cached = ipfs_index_lookup(codename, filename)
            if cached:
                effective_cid = cached["cid"]
                task.emit(f"Found in IPFS cache: {effective_cid[:24]}...")

        if effective_cid and ipfs_available():
            task.emit(f"Fetching from IPFS: {effective_cid}")
            rc = task.run_shell(["ipfs", "get", "-o", dest, effective_cid])
            fetched_from_ipfs = rc == 0
            if not fetched_from_ipfs:
                task.emit("IPFS failed, falling back to HTTP...", "warn")

        if not fetched_from_ipfs:
            if not url:
                task.emit("No HTTP URL available.", "error")
                task.done(False)
                return
            task.emit(f"Downloading: {filename}")
            rc = task.run_shell(["wget", "--progress=dot:giga", "-O", dest, url])
            if rc != 0:
                task.emit("Download failed.", "error")
                task.done(False)
                return

        result = verify_fetched_file(dest)
        task.emit(f"SHA256: {result['sha256']}")
        if result["known"]:
            task.emit("Verified against firmware registry.", "success")
        else:
            task.emit("Warning: not in registry.", "warn")

        # Auto-pin
        if not fetched_from_ipfs and ipfs_available():
            ipfs_pin_and_index(
                dest,
                key=f"{codename}/{filename}",
                codename=codename,
                rom_id=rom_id,
                rom_name=rom_name,
                version=version,
            )
        task.emit("")

        # === Phase 4: Sideload ===
        task.emit("=== Phase 4: Sideload ROM ===", "info")
        task.emit("Start ADB sideload on the device (TWRP > Advanced > ADB Sideload).", "warn")
        time.sleep(3)
        rc = task.run_shell(["adb", "sideload", dest])

        task.emit("")
        if rc == 0:
            task.emit("ROM update complete! Reboot from recovery.", "success")
            from web.registry import register

            register(
                dest,
                device_id=codename,
                device_label=codename,
                component="rom",
                version=version,
                source_url=url,
                flash_method="adb-sideload-ota",
                sha256=result["sha256"],
            )
        else:
            task.emit("Sideload failed. Your backup is at: " + str(backup_dir), "error")
        task.done(rc == 0)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})
