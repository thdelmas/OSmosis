#!/usr/bin/env python3
"""
FlashWizard Web UI — local Flask app for Samsung device flashing.
Runs on http://localhost:5000 and calls heimdall/adb under the hood.
"""

import json
import os
import queue
import shutil
import subprocess
import threading
import uuid
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request, stream_with_context

app = Flask(__name__)

SCRIPT_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = SCRIPT_DIR / "devices.cfg"
LOG_DIR = Path.home() / ".flashwizard" / "logs"
BACKUP_DIR = Path.home() / ".flashwizard" / "backups"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# In-memory task store: task_id -> {queue, thread, status}
tasks: dict = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def cmd_exists(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def parse_devices_cfg() -> list[dict]:
    """Parse devices.cfg and return list of device dicts."""
    devices = []
    if not CONFIG_FILE.exists():
        return devices
    for line in CONFIG_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|")
        if len(parts) < 9:
            continue
        devices.append({
            "id": parts[0],
            "label": parts[1],
            "model": parts[2],
            "codename": parts[3],
            "rom_url": parts[4],
            "twrp_url": parts[5],
            "eos_url": parts[6],
            "stock_url": parts[7],
            "gapps_url": parts[8] if len(parts) > 8 else "",
        })
    return devices


class Task:
    """Background task that streams line-by-line output via a queue."""

    def __init__(self, task_id: str):
        self.id = task_id
        self.q: queue.Queue = queue.Queue()
        self.status = "running"
        self.thread: threading.Thread | None = None

    def emit(self, msg: str, level: str = "info"):
        self.q.put(json.dumps({"level": level, "msg": msg}))

    def done(self, success: bool = True):
        self.status = "done" if success else "error"
        self.q.put(json.dumps({"level": "done", "msg": self.status}))

    def run_shell(self, cmd: list[str], sudo: bool = False) -> int:
        """Run a shell command, streaming output line by line."""
        if sudo:
            cmd = ["sudo"] + cmd
        self.emit(f"$ {' '.join(cmd)}", "cmd")
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            for line in proc.stdout:
                self.emit(line.rstrip())
            proc.wait()
            if proc.returncode == 0:
                self.emit("Command succeeded.", "success")
            else:
                self.emit(f"Command failed (exit {proc.returncode}).", "error")
            return proc.returncode
        except FileNotFoundError:
            self.emit(f"Command not found: {cmd[0]}", "error")
            return 127
        except Exception as e:
            self.emit(f"Error: {e}", "error")
            return 1


def start_task(fn, *args) -> str:
    task_id = str(uuid.uuid4())[:8]
    task = Task(task_id)
    tasks[task_id] = task
    task.thread = threading.Thread(target=fn, args=(task, *args), daemon=True)
    task.thread.start()
    return task_id


# ---------------------------------------------------------------------------
# Routes — Pages
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------------------
# Routes — API
# ---------------------------------------------------------------------------

@app.route("/api/status")
def api_status():
    """System status: check which tools are available."""
    return jsonify({
        "heimdall": cmd_exists("heimdall"),
        "adb": cmd_exists("adb"),
        "wget": cmd_exists("wget"),
        "curl": cmd_exists("curl"),
        "lz4": cmd_exists("lz4"),
    })


@app.route("/api/devices")
def api_devices():
    return jsonify(parse_devices_cfg())


@app.route("/api/detect")
def api_detect():
    """Auto-detect connected device via adb."""
    result = {"model": "", "codename": "", "match": None}
    if not cmd_exists("adb"):
        return jsonify({"error": "adb not installed"}), 500

    try:
        dev_list = subprocess.run(
            ["adb", "devices"], capture_output=True, text=True, timeout=5
        )
        if "device" not in dev_list.stdout and "recovery" not in dev_list.stdout:
            return jsonify({"error": "No device detected via ADB"}), 404

        model = subprocess.run(
            ["adb", "shell", "getprop", "ro.product.model"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
        codename = subprocess.run(
            ["adb", "shell", "getprop", "ro.product.device"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
        if not codename:
            codename = subprocess.run(
                ["adb", "shell", "getprop", "ro.product.board"],
                capture_output=True, text=True, timeout=5,
            ).stdout.strip()

        result["model"] = model
        result["codename"] = codename

        # Match against devices.cfg
        for dev in parse_devices_cfg():
            if dev["model"].lower() == model.lower() or dev["codename"].lower() == codename.lower():
                result["match"] = dev
                break
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify(result)


@app.route("/api/stream/<task_id>")
def api_stream(task_id):
    """SSE endpoint — streams task output."""
    task = tasks.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404

    def generate():
        while True:
            try:
                data = task.q.get(timeout=30)
                yield f"data: {data}\n\n"
                parsed = json.loads(data)
                if parsed.get("level") == "done":
                    break
            except queue.Empty:
                yield "data: {}\n\n"  # keepalive

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# Routes — Operations
# ---------------------------------------------------------------------------

@app.route("/api/flash/stock", methods=["POST"])
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

        # Extract tar.md5 files
        import glob
        for pattern in ["BL_*.tar.md5", "AP_*.tar.md5", "CP_*.tar.md5", "CSC_*.tar.md5"]:
            for f in glob.glob(str(work_dir / pattern)):
                task.emit(f"Extracting {Path(f).name}")
                task.run_shell(["tar", "-xvf", f, "-C", str(work_dir)])

        # Detect images
        images = {}
        for name in ["boot.img", "recovery.img", "system.img", "super.img",
                      "modem.bin", "cache.img", "vbmeta.img"]:
            p = work_dir / name
            if p.exists():
                images[name.split(".")[0].upper()] = str(p)

        task.emit(f"Detected images: {', '.join(images.keys()) or 'none'}")

        # Build heimdall command
        heimdall_args = ["heimdall", "flash"]
        for part, path in images.items():
            heimdall_args.extend([f"--{part}", path])

        task.emit("Ready to flash. Ensure device is in Download Mode.", "warn")
        task.emit(f"Command: sudo {' '.join(heimdall_args)}", "cmd")

        rc = task.run_shell(heimdall_args, sudo=True)
        if rc == 0:
            task.emit("Flash complete!", "success")
        task.done(rc == 0)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@app.route("/api/flash/recovery", methods=["POST"])
def api_flash_recovery():
    """Flash custom recovery image."""
    img_path = request.json.get("recovery_img", "")
    if not img_path or not Path(img_path).is_file():
        return jsonify({"error": "Recovery image not found"}), 400

    def _run(task: Task):
        task.emit(f"Recovery image: {img_path}")

        # SHA256
        import hashlib
        h = hashlib.sha256(Path(img_path).read_bytes()).hexdigest()
        task.emit(f"SHA256: {h}")

        task.emit("Ensure device is in Download Mode.", "warn")
        rc = task.run_shell(["heimdall", "flash", "--RECOVERY", img_path, "--no-reboot"], sudo=True)
        if rc == 0:
            task.emit("Recovery flashed! Boot into recovery now (Power + Home + VolUp).", "success")
        task.done(rc == 0)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@app.route("/api/sideload", methods=["POST"])
def api_sideload():
    """ADB sideload a ZIP."""
    zip_path = request.json.get("zip_path", "")
    label = request.json.get("label", "ROM")
    if not zip_path or not Path(zip_path).is_file():
        return jsonify({"error": "ZIP file not found"}), 400

    def _run(task: Task):
        task.emit(f"Sideloading {label}: {zip_path}")

        import hashlib
        h = hashlib.sha256(Path(zip_path).read_bytes()).hexdigest()
        task.emit(f"SHA256: {h}")

        task.emit("Ensure device is in ADB sideload mode (TWRP > Advanced > ADB Sideload).", "warn")
        rc = task.run_shell(["adb", "sideload", zip_path])
        if rc == 0:
            task.emit(f"{label} sideload complete!", "success")
        task.done(rc == 0)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@app.route("/api/download", methods=["POST"])
def api_download():
    """Download files for a device preset."""
    device_id = request.json.get("device_id", "")
    selected = request.json.get("selected", [])  # list of keys: rom_url, twrp_url, etc.

    devices = parse_devices_cfg()
    device = next((d for d in devices if d["id"] == device_id), None)
    if not device:
        return jsonify({"error": f"Device '{device_id}' not found"}), 404

    def _run(task: Task):
        target = Path.home() / "FlashWizard-downloads" / device_id
        target.mkdir(parents=True, exist_ok=True)
        task.emit(f"Download directory: {target}")

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

        task.emit("All downloads finished.", "success")
        task.done(True)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@app.route("/api/backup", methods=["POST"])
def api_backup():
    """Backup device partitions via ADB."""
    partitions = request.json.get("partitions", ["boot", "recovery"])
    backup_efs = request.json.get("backup_efs", False)

    def _run(task: Task):
        from datetime import datetime
        backup_path = BACKUP_DIR / datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path.mkdir(parents=True, exist_ok=True)
        task.emit(f"Backup directory: {backup_path}")

        # Check ADB
        rc = task.run_shell(["adb", "devices"])
        if rc != 0:
            task.emit("ADB not available.", "error")
            task.done(False)
            return

        # Check root
        result = subprocess.run(
            ["adb", "shell", "su", "-c", "id"],
            capture_output=True, text=True, timeout=5,
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
                            ["adb", "shell", "su", "-c",
                             f"dd if=$(ls /dev/block/platform/*/by-name/{part} "
                             f"/dev/block/by-name/{part} 2>/dev/null | head -1)"],
                            stdout=f, stderr=subprocess.PIPE,
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
                            ["adb", "shell", "su", "-c",
                             "dd if=$(ls /dev/block/platform/*/by-name/efs "
                             "/dev/block/by-name/efs 2>/dev/null | head -1)"],
                            stdout=f, stderr=subprocess.PIPE,
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

        # Checksums
        import hashlib
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


@app.route("/api/updates")
def api_updates():
    """Check for ROM updates across all configured devices."""
    def _run(task: Task):
        devices = parse_devices_cfg()
        if not devices:
            task.emit("No devices configured.", "warn")
            task.done(True)
            return

        for dev in devices:
            task.emit(f"\n{dev['label']} ({dev['model']} / {dev['codename']})", "info")

            for label, key, pattern in [
                ("LineageOS", "rom_url", r'title="(lineage-[^"]*\.zip)"'),
                ("/e/OS", "eos_url", r'title="(e-[^"]*\.zip)"'),
            ]:
                url = dev.get(key, "")
                if not url or "sourceforge.net" not in url:
                    continue

                import re
                import urllib.parse

                # Extract SF project and path
                m_proj = re.search(r"sourceforge\.net/projects/([^/]+)/", url)
                m_path = re.search(r"files/(.+)/download", url)
                if not m_proj or not m_path:
                    continue

                sf_dir = os.path.dirname(m_path.group(1))
                page_url = f"https://sourceforge.net/projects/{m_proj.group(1)}/files/{sf_dir}/"
                task.emit(f"  {label}: checking {m_proj.group(1)}/{sf_dir}...")

                try:
                    result = subprocess.run(
                        ["curl", "-sL", page_url],
                        capture_output=True, text=True, timeout=15,
                    )
                    matches = re.findall(pattern, result.stdout)[:3]
                    if matches:
                        task.emit(f"  Latest {label} builds:", "success")
                        for m in matches:
                            task.emit(f"    {m}")
                        configured = os.path.basename(url.split("?")[0])
                        task.emit(f"  Configured: {configured}")
                    else:
                        task.emit(f"  Could not fetch {label} build list.", "warn")
                except Exception as e:
                    task.emit(f"  Error checking {label}: {e}", "error")

        task.done(True)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@app.route("/api/magisk", methods=["POST"])
def api_magisk():
    """Magisk boot.img patching workflow."""
    boot_img = request.json.get("boot_img", "")
    flash_after = request.json.get("flash_after", False)

    if not boot_img or not Path(boot_img).is_file():
        return jsonify({"error": "boot.img not found"}), 400

    def _run(task: Task):
        import hashlib

        task.emit(f"boot.img: {boot_img}")
        h = hashlib.sha256(Path(boot_img).read_bytes()).hexdigest()
        task.emit(f"SHA256: {h}")

        # Check ADB
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=5)
        if "device" not in result.stdout:
            task.emit("No device detected via ADB. Connect the device with USB debugging enabled.", "error")
            task.done(False)
            return

        # Check Magisk installed
        pm_list = subprocess.run(
            ["adb", "shell", "pm", "list", "packages"],
            capture_output=True, text=True, timeout=5,
        ).stdout
        magisk_pkg = None
        for pkg in ["com.topjohnwu.magisk", "io.github.vvb2060.magisk"]:
            if pkg in pm_list:
                magisk_pkg = pkg
                break

        if not magisk_pkg:
            task.emit("Magisk app not found on device. Install it first.", "error")
            task.done(False)
            return
        task.emit(f"Magisk app found: {magisk_pkg}", "success")

        # Push boot.img
        device_path = "/sdcard/Download/boot-to-patch.img"
        task.emit("Pushing boot.img to device...")
        rc = task.run_shell(["adb", "push", boot_img, device_path])
        if rc != 0:
            task.done(False)
            return

        task.emit("", "info")
        task.emit("Now open the Magisk app on the device:", "warn")
        task.emit("  1) Tap 'Install' next to Magisk")
        task.emit("  2) Choose 'Select and Patch a File'")
        task.emit("  3) Select Download/boot-to-patch.img")
        task.emit("  4) Tap 'LET'S GO' and wait for patching")
        task.emit("", "info")
        task.emit("Waiting for patched file to appear on device...", "info")

        # Poll for patched file (up to 5 minutes)
        import time
        patched_device = ""
        for _ in range(60):
            time.sleep(5)
            check = subprocess.run(
                ["adb", "shell", "ls", "-t", "/sdcard/Download/magisk_patched-*.img"],
                capture_output=True, text=True, timeout=5,
            )
            if check.returncode == 0 and "magisk_patched" in check.stdout:
                patched_device = check.stdout.strip().split("\n")[0].strip()
                break

        if not patched_device:
            task.emit("Timed out waiting for patched file. Check Magisk app.", "error")
            task.done(False)
            return

        task.emit(f"Patched file found: {patched_device}", "success")

        # Pull it back
        patched_local = str(Path(boot_img).parent / "magisk_patched-boot.img")
        task.emit(f"Pulling to {patched_local}...")
        rc = task.run_shell(["adb", "pull", patched_device, patched_local])
        if rc != 0:
            task.done(False)
            return

        h2 = hashlib.sha256(Path(patched_local).read_bytes()).hexdigest()
        task.emit(f"Patched SHA256: {h2}", "success")

        if flash_after:
            task.emit("Flashing patched boot.img via Heimdall...", "warn")
            task.emit("Ensure device is in Download Mode.", "warn")
            rc = task.run_shell(["heimdall", "flash", "--BOOT", patched_local], sudo=True)
            if rc == 0:
                task.emit("Magisk patched boot.img flashed!", "success")

        task.emit(f"Done. Patched image: {patched_local}", "success")
        task.done(True)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@app.route("/api/workflow", methods=["POST"])
def api_workflow():
    """Full guided workflow: stock restore + recovery + ROM + GApps."""
    data = request.json or {}
    fw_zip = data.get("fw_zip", "")
    recovery_img = data.get("recovery_img", "")
    rom_zip = data.get("rom_zip", "")
    gapps_zip = data.get("gapps_zip", "")

    def _run(task: Task):
        import hashlib

        # Step 1: Stock firmware
        if fw_zip:
            task.emit("=== Step 1: Restore stock firmware ===", "info")
            if not Path(fw_zip).is_file():
                task.emit(f"Firmware ZIP not found: {fw_zip}", "error")
            else:
                work_dir = Path.home() / "Downloads" / (Path(fw_zip).stem + "-unpacked")
                work_dir.mkdir(parents=True, exist_ok=True)
                task.emit(f"Extracting {fw_zip}...")
                task.run_shell(["unzip", "-o", fw_zip, "-d", str(work_dir)])

                import glob
                for pattern in ["BL_*.tar.md5", "AP_*.tar.md5", "CP_*.tar.md5", "CSC_*.tar.md5"]:
                    for f in glob.glob(str(work_dir / pattern)):
                        task.run_shell(["tar", "-xvf", f, "-C", str(work_dir)])

                images = {}
                for name in ["boot.img", "recovery.img", "system.img", "super.img", "modem.bin"]:
                    if (work_dir / name).exists():
                        images[name.split(".")[0].upper()] = str(work_dir / name)

                if images:
                    task.emit(f"Images: {', '.join(images.keys())}")
                    task.emit("Ensure device is in Download Mode.", "warn")
                    heimdall_args = ["heimdall", "flash"]
                    for part, path in images.items():
                        heimdall_args.extend([f"--{part}", path])
                    task.run_shell(heimdall_args, sudo=True)
                    task.emit("Step 1 complete.", "success")
                else:
                    task.emit("No flashable images found.", "error")
        else:
            task.emit("Step 1 skipped (no firmware ZIP).", "info")

        # Step 2: Custom recovery
        if recovery_img:
            task.emit("")
            task.emit("=== Step 2: Flash custom recovery ===", "info")
            if not Path(recovery_img).is_file():
                task.emit(f"Recovery image not found: {recovery_img}", "error")
            else:
                task.emit("Ensure device is in Download Mode.", "warn")
                task.run_shell(["heimdall", "flash", "--RECOVERY", recovery_img, "--no-reboot"], sudo=True)
                task.emit("Step 2 complete. Boot into recovery now (Power+Home+VolUp).", "success")
        else:
            task.emit("Step 2 skipped (no recovery image).", "info")

        # Step 3: Sideload ROM
        if rom_zip:
            task.emit("")
            task.emit("=== Step 3: Sideload custom ROM ===", "info")
            if not Path(rom_zip).is_file():
                task.emit(f"ROM ZIP not found: {rom_zip}", "error")
            else:
                h = hashlib.sha256(Path(rom_zip).read_bytes()).hexdigest()
                task.emit(f"SHA256: {h}")
                task.emit("Start ADB sideload on the device (TWRP > Advanced > ADB Sideload).", "warn")

                # Wait a moment for user to start sideload
                import time
                time.sleep(3)
                task.run_shell(["adb", "sideload", rom_zip])
                task.emit("Step 3 complete.", "success")
        else:
            task.emit("Step 3 skipped (no ROM ZIP).", "info")

        # Step 4: GApps
        if gapps_zip:
            task.emit("")
            task.emit("=== Step 4: Sideload GApps ===", "info")
            if not Path(gapps_zip).is_file():
                task.emit(f"GApps ZIP not found: {gapps_zip}", "error")
            else:
                task.emit("Start ADB sideload again for GApps.", "warn")
                import time
                time.sleep(3)
                task.run_shell(["adb", "sideload", gapps_zip])
                task.emit("Step 4 complete.", "success")
        else:
            task.emit("Step 4 skipped (no GApps ZIP).", "info")

        task.emit("")
        task.emit("Workflow finished! Reboot from recovery.", "success")
        task.done(True)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@app.route("/api/browse")
def api_browse():
    """Simple file/directory browser for the web UI."""
    path = request.args.get("path", str(Path.home()))
    try:
        p = Path(path).resolve()
        if not p.exists():
            return jsonify({"error": "Path not found"}), 404

        if p.is_file():
            return jsonify({
                "type": "file",
                "path": str(p),
                "name": p.name,
                "size": p.stat().st_size,
            })

        entries = []
        # Parent directory
        if p.parent != p:
            entries.append({"name": "..", "path": str(p.parent), "type": "dir", "size": 0})
        for child in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            try:
                entries.append({
                    "name": child.name,
                    "path": str(child),
                    "type": "dir" if child.is_dir() else "file",
                    "size": child.stat().st_size if child.is_file() else 0,
                })
            except PermissionError:
                continue

        return jsonify({"type": "dir", "path": str(p), "entries": entries})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/logs")
def api_logs():
    """List session logs."""
    logs = []
    if LOG_DIR.exists():
        for f in sorted(LOG_DIR.glob("session-*.log"), reverse=True):
            logs.append({
                "name": f.name,
                "path": str(f),
                "size": f.stat().st_size,
                "modified": f.stat().st_mtime,
            })
    return jsonify(logs)


@app.route("/api/logs/<name>")
def api_log_content(name):
    """Read a specific log file."""
    log_file = LOG_DIR / name
    if not log_file.exists() or not log_file.name.startswith("session-"):
        return jsonify({"error": "Log not found"}), 404
    content = log_file.read_text(errors="replace")
    # Limit to last 2000 lines
    lines = content.splitlines()[-2000:]
    return jsonify({"name": name, "content": "\n".join(lines)})


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import webbrowser
    port = int(os.environ.get("PORT", 5000))
    print(f"\n  FlashWizard Web UI: http://localhost:{port}\n")
    webbrowser.open(f"http://localhost:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)
