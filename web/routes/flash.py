"""Flash stock/recovery, sideload, download, and backup routes."""

import subprocess
from pathlib import Path

from flask import Blueprint, jsonify, request

from web.core import BACKUP_DIR, Task, parse_devices_cfg, start_task

bp = Blueprint("flash", __name__)


@bp.route("/api/flash/stock", methods=["POST"])
def api_flash_stock():
    """Flash stock firmware from a ZIP path."""
    fw_zip = request.json.get("fw_zip", "")
    if not fw_zip or not Path(fw_zip).is_file():
        return jsonify({"error": "Firmware ZIP not found"}), 400

    def _run(task: Task):
        task.emit(f"Firmware ZIP: {fw_zip}")
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
        import hashlib

        task.emit(f"Recovery image: {img_path}")
        h = hashlib.sha256(Path(img_path).read_bytes()).hexdigest()
        task.emit(f"SHA256: {h}")
        task.emit("Ensure device is in Download Mode.", "warn")
        rc = task.run_shell(["heimdall", "flash", "--RECOVERY", img_path, "--no-reboot"], sudo=True)
        if rc == 0:
            task.emit("Recovery flashed! Boot into recovery now (Power + Home + VolUp).", "success")
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
        import hashlib

        task.emit(f"Sideloading {label}: {zip_path}")
        h = hashlib.sha256(Path(zip_path).read_bytes()).hexdigest()
        task.emit(f"SHA256: {h}")
        task.emit("Ensure device is in ADB sideload mode (TWRP > Advanced > ADB Sideload).", "warn")
        rc = task.run_shell(["adb", "sideload", zip_path])
        if rc == 0:
            task.emit(f"{label} sideload complete!", "success")
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
