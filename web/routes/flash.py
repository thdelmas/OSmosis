"""Flash stock/recovery, sideload, download, and backup routes."""

import subprocess
from pathlib import Path

from flask import Blueprint, jsonify, request

from web.core import BACKUP_DIR, Task, parse_devices_cfg, start_task
from web.registry import register, verify

bp = Blueprint("flash", __name__)


def _verify_before_flash(task: Task, fw_path: str) -> dict:
    """Verify a firmware file against the registry before flashing.

    Emits status messages to the task. Returns the verification result.
    """
    task.emit("Verifying firmware against registry...", "info")
    result = verify(fw_path)
    task.emit(f"SHA256: {result['sha256']}")
    if result["known"]:
        match = result["matches"][0]
        task.emit(
            f"Verified: matches registry entry "
            f"({match.get('device_label', '')} {match.get('version', '')} via {match.get('flash_method', '')})",
            "success",
        )
    else:
        task.emit(
            "Warning: this firmware is NOT in the registry. "
            "It may be safe, but it hasn't been flashed by Osmosis before. Proceeding.",
            "warn",
        )
    task.emit("")
    return result


@bp.route("/api/flash/stock", methods=["POST"])
def api_flash_stock():
    """Flash stock firmware from a ZIP path."""
    fw_zip = request.json.get("fw_zip", "")
    if not fw_zip or not Path(fw_zip).is_file():
        return jsonify({"error": "Firmware ZIP not found"}), 400

    def _run(task: Task):
        task.emit(f"Firmware ZIP: {fw_zip}")
        _verify_before_flash(task, fw_zip)

        work_dir = Path.home() / "Downloads" / (Path(fw_zip).stem + "-unpacked")
        work_dir.mkdir(parents=True, exist_ok=True)
        task.emit(f"Working directory: {work_dir}")

        task.emit("Extracting firmware ZIP...", "info")
        rc = task.run_shell(["unzip", "-o", fw_zip, "-d", str(work_dir)])
        if rc != 0:
            task.done(False)
            return

        import glob

        for pattern in ["BL_*.tar.md5", "AP_*.tar.md5", "CP_*.tar.md5", "CSC_*.tar.md5"]:
            for f in glob.glob(str(work_dir / pattern)):
                task.emit(f"Extracting {Path(f).name}")
                task.run_shell(["tar", "-xvf", f, "-C", str(work_dir)])

        images = {}
        for name in ["boot.img", "recovery.img", "system.img", "super.img", "modem.bin", "cache.img", "vbmeta.img"]:
            p = work_dir / name
            if p.exists():
                images[name.split(".")[0].upper()] = str(p)

        task.emit(f"Detected images: {', '.join(images.keys()) or 'none'}")

        heimdall_args = ["heimdall", "flash"]
        for part, path in images.items():
            heimdall_args.extend([f"--{part}", path])

        task.emit("Ready to flash. Ensure device is in Download Mode.", "warn")
        rc = task.run_shell(heimdall_args, sudo=True)
        if rc == 0:
            task.emit("Flash complete!", "success")
            register(fw_zip, flash_method="heimdall-stock", component="stock")
        task.done(rc == 0)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@bp.route("/api/flash/recovery", methods=["POST"])
def api_flash_recovery():
    """Flash custom recovery image."""
    img_path = request.json.get("recovery_img", "")
    if not img_path or not Path(img_path).is_file():
        return jsonify({"error": "Recovery image not found"}), 400

    def _run(task: Task):
        task.emit(f"Recovery image: {img_path}")
        result = _verify_before_flash(task, img_path)
        h = result["sha256"]
        task.emit("Ensure device is in Download Mode.", "warn")
        rc = task.run_shell(["heimdall", "flash", "--RECOVERY", img_path, "--no-reboot"], sudo=True)
        if rc == 0:
            task.emit("Recovery flashed! Boot into recovery now (Power + Home + VolUp).", "success")
            register(img_path, flash_method="heimdall", component="recovery", sha256=h)
        task.done(rc == 0)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@bp.route("/api/sideload", methods=["POST"])
def api_sideload():
    """ADB sideload a ZIP."""
    zip_path = request.json.get("zip_path", "")
    label = request.json.get("label", "ROM")
    if not zip_path or not Path(zip_path).is_file():
        return jsonify({"error": "ZIP file not found"}), 400

    def _run(task: Task):
        task.emit(f"Sideloading {label}: {zip_path}")
        result = _verify_before_flash(task, zip_path)
        h = result["sha256"]
        task.emit("Ensure device is in ADB sideload mode (TWRP > Advanced > ADB Sideload).", "warn")
        rc = task.run_shell(["adb", "sideload", zip_path])
        if rc == 0:
            task.emit(f"{label} sideload complete!", "success")
            register(zip_path, flash_method="adb-sideload", component=label.lower(), sha256=h)
        task.done(rc == 0)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


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
                import hashlib

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


@bp.route("/api/backup", methods=["POST"])
def api_backup():
    """Backup device partitions via ADB."""
    partitions = request.json.get("partitions", ["boot", "recovery"])
    backup_efs = request.json.get("backup_efs", False)

    def _run(task: Task):
        import hashlib
        from datetime import datetime

        backup_path = BACKUP_DIR / datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path.mkdir(parents=True, exist_ok=True)
        task.emit(f"Backup directory: {backup_path}")

        rc = task.run_shell(["adb", "devices"])
        if rc != 0:
            task.emit("ADB not available.", "error")
            task.done(False)
            return

        result = subprocess.run(
            ["adb", "shell", "su", "-c", "id"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        has_root = "uid=0" in result.stdout

        if has_root:
            task.emit("Root access available.", "success")
            for part in partitions:
                task.emit(f"Backing up {part}...")
                dest = backup_path / f"{part}.img"
                try:
                    with open(dest, "wb") as f:
                        proc = subprocess.Popen(
                            [
                                "adb",
                                "shell",
                                "su",
                                "-c",
                                f"dd if=$(ls /dev/block/platform/*/by-name/{part} "
                                f"/dev/block/by-name/{part} 2>/dev/null | head -1)",
                            ],
                            stdout=f,
                            stderr=subprocess.PIPE,
                        )
                        proc.wait(timeout=120)
                    if dest.stat().st_size > 0:
                        task.emit(f"{part} saved ({dest.stat().st_size // 1024}K).", "success")
                    else:
                        task.emit(f"Failed to back up {part} (empty file).", "error")
                        dest.unlink(missing_ok=True)
                except Exception as e:
                    task.emit(f"Error backing up {part}: {e}", "error")

            if backup_efs:
                task.emit("Backing up EFS...")
                dest = backup_path / "efs.img"
                try:
                    with open(dest, "wb") as f:
                        proc = subprocess.Popen(
                            [
                                "adb",
                                "shell",
                                "su",
                                "-c",
                                "dd if=$(ls /dev/block/platform/*/by-name/efs "
                                "/dev/block/by-name/efs 2>/dev/null | head -1)",
                            ],
                            stdout=f,
                            stderr=subprocess.PIPE,
                        )
                        proc.wait(timeout=120)
                    if dest.stat().st_size > 0:
                        task.emit(f"EFS saved ({dest.stat().st_size // 1024}K).", "success")
                    else:
                        dest.unlink(missing_ok=True)
                        task.emit("EFS backup failed — trying adb pull /efs ...", "warn")
                        task.run_shell(["adb", "pull", "/efs", str(backup_path / "efs-folder")])
                except Exception as e:
                    task.emit(f"Error backing up EFS: {e}", "error")
        else:
            task.emit("No root access. Pulling /sdcard/ instead.", "warn")
            task.run_shell(["adb", "pull", "/sdcard/", str(backup_path / "sdcard")])

        checksums = []
        for f in backup_path.glob("*.img"):
            h = hashlib.sha256(f.read_bytes()).hexdigest()
            checksums.append(f"{h}  {f.name}")
        if checksums:
            (backup_path / "checksums.sha256").write_text("\n".join(checksums) + "\n")
            task.emit("Checksums saved.", "success")

        task.emit(f"Backup complete: {backup_path}", "success")
        task.done(True)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@bp.route("/api/backup/full", methods=["POST"])
def api_backup_full():
    """Full NAND backup for Samsung devices — all partitions including system.

    Requires root access (TWRP or rooted device).
    """

    def _run(task: Task):
        import hashlib
        from datetime import datetime

        backup_path = BACKUP_DIR / datetime.now().strftime("%Y%m%d-%H%M%S-full")
        backup_path.mkdir(parents=True, exist_ok=True)
        task.emit(f"Full backup directory: {backup_path}")

        rc = task.run_shell(["adb", "devices"])
        if rc != 0:
            task.emit("ADB not available.", "error")
            task.done(False)
            return

        result = subprocess.run(
            ["adb", "shell", "su", "-c", "id"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        has_root = "uid=0" in result.stdout

        if not has_root:
            task.emit("Root access required for full NAND backup.", "error")
            task.emit("Boot into TWRP recovery for root ADB access.", "warn")
            task.done(False)
            return

        task.emit("Root access confirmed.", "success")

        # Discover all partitions from the partition table
        task.emit("Discovering partitions...")
        result = subprocess.run(
            [
                "adb",
                "shell",
                "su",
                "-c",
                "ls /dev/block/platform/*/by-name/ 2>/dev/null || ls /dev/block/by-name/ 2>/dev/null",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        partitions = [p.strip() for p in result.stdout.strip().split() if p.strip()]

        if not partitions:
            task.emit("Could not discover partitions.", "error")
            task.done(False)
            return

        task.emit(
            f"Found {len(partitions)} partitions: {', '.join(partitions[:10])}{'...' if len(partitions) > 10 else ''}"
        )

        # Core partitions to always back up
        core_parts = ["boot", "recovery", "efs", "param", "modem"]
        # Large partitions
        large_parts = ["system", "super", "cache", "hidden", "userdata"]
        target_parts = [p for p in partitions if p in core_parts + large_parts]
        other_parts = [p for p in partitions if p not in core_parts + large_parts]

        task.emit(f"Backing up {len(target_parts)} core/large partitions...")

        backed_up = 0
        for part in target_parts:
            task.emit(f"Backing up {part}...")
            dest = backup_path / f"{part}.img"
            try:
                with open(dest, "wb") as f:
                    proc = subprocess.Popen(
                        [
                            "adb",
                            "shell",
                            "su",
                            "-c",
                            f"dd if=$(ls /dev/block/platform/*/by-name/{part} "
                            f"/dev/block/by-name/{part} 2>/dev/null | head -1)",
                        ],
                        stdout=f,
                        stderr=subprocess.PIPE,
                    )
                    proc.wait(timeout=600)
                if dest.stat().st_size > 0:
                    size_mb = dest.stat().st_size / (1024 * 1024)
                    task.emit(f"  {part}: {size_mb:.1f} MB", "success")
                    backed_up += 1
                else:
                    dest.unlink(missing_ok=True)
                    task.emit(f"  {part}: empty (skipped)", "warn")
            except subprocess.TimeoutExpired:
                task.emit(f"  {part}: timed out", "warn")
                dest.unlink(missing_ok=True)
            except Exception as e:
                task.emit(f"  {part}: error - {e}", "error")

        # Back up small unknown partitions
        for part in other_parts:
            dest = backup_path / f"{part}.img"
            try:
                with open(dest, "wb") as f:
                    proc = subprocess.Popen(
                        [
                            "adb",
                            "shell",
                            "su",
                            "-c",
                            f"dd if=$(ls /dev/block/platform/*/by-name/{part} "
                            f"/dev/block/by-name/{part} 2>/dev/null | head -1)",
                        ],
                        stdout=f,
                        stderr=subprocess.PIPE,
                    )
                    proc.wait(timeout=60)
                if dest.stat().st_size > 0 and dest.stat().st_size < 100 * 1024 * 1024:
                    size_mb = dest.stat().st_size / (1024 * 1024)
                    task.emit(f"  {part}: {size_mb:.1f} MB", "success")
                    backed_up += 1
                else:
                    dest.unlink(missing_ok=True)
            except Exception:
                dest.unlink(missing_ok=True)

        # Generate checksums
        checksums = []
        for f in sorted(backup_path.glob("*.img")):
            h = hashlib.sha256(f.read_bytes()).hexdigest()
            checksums.append(f"{h}  {f.name}")
        if checksums:
            (backup_path / "checksums.sha256").write_text("\n".join(checksums) + "\n")

        # Save partition list
        (backup_path / "partitions.txt").write_text("\n".join(partitions) + "\n")

        task.emit(f"Full backup complete: {backed_up} partitions saved to {backup_path}", "success")
        task.done(True)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@bp.route("/api/backup/list")
def api_backup_list():
    """List all available backups."""
    if not BACKUP_DIR.exists():
        return jsonify([])

    backups = []
    for d in sorted(BACKUP_DIR.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        images = list(d.glob("*.img"))
        total_size = sum(f.stat().st_size for f in images)
        backups.append(
            {
                "name": d.name,
                "path": str(d),
                "partition_count": len(images),
                "partitions": [f.stem for f in sorted(images)],
                "total_size_mb": round(total_size / (1024 * 1024), 1),
                "has_checksums": (d / "checksums.sha256").exists(),
                "is_full": d.name.endswith("-full"),
            }
        )
    return jsonify(backups)


@bp.route("/api/backup/restore", methods=["POST"])
def api_restore():
    """Restore partitions from a backup via Heimdall.

    JSON body: {
        "backup_name": "20240101-120000",
        "partitions": ["boot", "recovery"]   // optional, defaults to all
    }
    """
    body = request.json or {}
    backup_name = body.get("backup_name", "")
    selected_partitions = body.get("partitions")

    backup_path = BACKUP_DIR / backup_name
    if not backup_path.is_dir():
        return jsonify({"error": f"Backup '{backup_name}' not found"}), 404

    def _run(task: Task):
        import hashlib

        task.emit(f"Restoring from backup: {backup_name}")

        # Verify checksums first
        checksum_file = backup_path / "checksums.sha256"
        if checksum_file.exists():
            task.emit("Verifying checksums...")
            for line in checksum_file.read_text().strip().splitlines():
                parts = line.split("  ", 1)
                if len(parts) != 2:
                    continue
                expected_hash, filename = parts
                filepath = backup_path / filename
                if not filepath.exists():
                    task.emit(f"  {filename}: MISSING", "error")
                    task.done(False)
                    return
                actual_hash = hashlib.sha256(filepath.read_bytes()).hexdigest()
                if actual_hash != expected_hash:
                    task.emit(f"  {filename}: CHECKSUM MISMATCH", "error")
                    task.done(False)
                    return
                task.emit(f"  {filename}: OK", "success")

        images = list(backup_path.glob("*.img"))
        if selected_partitions:
            images = [f for f in images if f.stem in selected_partitions]

        if not images:
            task.emit("No partition images to restore.", "error")
            task.done(False)
            return

        task.emit(f"Restoring {len(images)} partition(s): {', '.join(f.stem for f in images)}")
        task.emit("Ensure device is in Download Mode.", "warn")

        heimdall_args = ["heimdall", "flash"]
        for img in images:
            heimdall_args.extend([f"--{img.stem.upper()}", str(img)])

        rc = task.run_shell(heimdall_args, sudo=True)
        if rc == 0:
            task.emit("Restore complete!", "success")
        task.done(rc == 0)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})
