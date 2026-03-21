"""Workflow routes: updates, pmbootstrap, magisk, guided workflow, download-and-flash."""

import os
import subprocess
from pathlib import Path

from flask import Blueprint, jsonify, request

from web.core import Task, cmd_exists, parse_devices_cfg, start_task
from web.ipfs_helpers import ipfs_available, ipfs_index_lookup, ipfs_pin_and_index, verify_fetched_file

bp = Blueprint("workflow", __name__)


@bp.route("/api/updates")
def api_updates():
    """Check for ROM updates across all configured devices."""
    import re

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
                        capture_output=True,
                        text=True,
                        timeout=15,
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


@bp.route("/api/pmbootstrap", methods=["POST"])
def api_pmbootstrap():
    """Install postmarketOS via pmbootstrap."""
    device = request.json.get("device", "")
    codename = request.json.get("codename", "")
    if not device and codename:
        device = f"samsung-{codename}"

    def _run(task: Task):
        if not cmd_exists("pmbootstrap"):
            task.emit("pmbootstrap is not installed. Installing via pip...", "info")
            rc = task.run_shell(["pip3", "install", "--user", "pmbootstrap"])
            if rc != 0:
                task.emit("")
                task.emit("Could not install pmbootstrap automatically.", "error")
                task.emit("  pip3 install --user pmbootstrap", "cmd")
                task.done(False)
                return
            task.emit("pmbootstrap installed.", "success")
            task.emit("")

        task.emit(f"Initializing pmbootstrap for {device}...", "info")
        task.emit("")

        work_dir = str(Path.home() / ".local" / "var" / "pmbootstrap")
        task.emit("Building postmarketOS image (this may take a while)...", "info")
        rc = task.run_shell(
            [
                "pmbootstrap",
                "--work",
                work_dir,
                "install",
                "--no-fde",
                "--device",
                device,
            ]
        )

        if rc == 0:
            task.emit("")
            task.emit("postmarketOS image built!", "success")
            task.emit("  pmbootstrap flasher flash_rootfs", "cmd")
            task.emit("  pmbootstrap flasher flash_kernel", "cmd")
            task.emit("  pmbootstrap export", "cmd")
        else:
            task.emit("")
            task.emit("pmbootstrap build failed. Run interactively:", "warn")
            task.emit("  pmbootstrap init", "cmd")
            task.emit("  pmbootstrap install", "cmd")

        task.done(rc == 0)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@bp.route("/api/magisk", methods=["POST"])
def api_magisk():
    """Magisk boot.img patching workflow."""
    boot_img = request.json.get("boot_img", "")
    flash_after = request.json.get("flash_after", False)

    if not boot_img or not Path(boot_img).is_file():
        return jsonify({"error": "boot.img not found"}), 400

    def _run(task: Task):
        import hashlib
        import time

        task.emit(f"boot.img: {boot_img}")
        h = hashlib.sha256(Path(boot_img).read_bytes()).hexdigest()
        task.emit(f"SHA256: {h}")

        result = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=5)
        if "device" not in result.stdout:
            task.emit("No device detected via ADB.", "error")
            task.done(False)
            return

        pm_list = subprocess.run(
            ["adb", "shell", "pm", "list", "packages"],
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout
        magisk_pkg = None
        for pkg in ["com.topjohnwu.magisk", "io.github.vvb2060.magisk"]:
            if pkg in pm_list:
                magisk_pkg = pkg
                break
        if not magisk_pkg:
            task.emit("Magisk app not found on device.", "error")
            task.done(False)
            return
        task.emit(f"Magisk app found: {magisk_pkg}", "success")

        task.run_shell(["adb", "push", boot_img, "/sdcard/Download/boot-to-patch.img"])

        task.emit("", "info")
        task.emit("Open Magisk app: Install > Select and Patch a File > boot-to-patch.img", "warn")
        task.emit("Waiting for patched file...", "info")

        patched_device = ""
        for _ in range(60):
            time.sleep(5)
            check = subprocess.run(
                ["adb", "shell", "ls", "-t", "/sdcard/Download/magisk_patched-*.img"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if check.returncode == 0 and "magisk_patched" in check.stdout:
                patched_device = check.stdout.strip().split("\n")[0].strip()
                break

        if not patched_device:
            task.emit("Timed out waiting for patched file.", "error")
            task.done(False)
            return

        patched_local = str(Path(boot_img).parent / "magisk_patched-boot.img")
        task.run_shell(["adb", "pull", patched_device, patched_local])

        h2 = hashlib.sha256(Path(patched_local).read_bytes()).hexdigest()
        task.emit(f"Patched SHA256: {h2}", "success")

        if flash_after:
            task.emit("Flashing patched boot.img via Heimdall...", "warn")
            task.run_shell(["heimdall", "flash", "--BOOT", patched_local], sudo=True)

        task.emit(f"Done. Patched image: {patched_local}", "success")
        task.done(True)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@bp.route("/api/workflow", methods=["POST"])
def api_workflow():
    """Full guided workflow: stock restore + recovery + ROM + GApps."""
    data = request.json or {}
    fw_zip = data.get("fw_zip", "")
    recovery_img = data.get("recovery_img", "")
    rom_zip = data.get("rom_zip", "")
    gapps_zip = data.get("gapps_zip", "")

    def _run(task: Task):
        import hashlib
        import time

        if fw_zip:
            task.emit("=== Step 1: Restore stock firmware ===", "info")
            if not Path(fw_zip).is_file():
                task.emit(f"Firmware ZIP not found: {fw_zip}", "error")
            else:
                work_dir = Path.home() / "Downloads" / (Path(fw_zip).stem + "-unpacked")
                work_dir.mkdir(parents=True, exist_ok=True)
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
                    task.emit("Ensure device is in Download Mode.", "warn")
                    heimdall_args = ["heimdall", "flash"]
                    for part, path in images.items():
                        heimdall_args.extend([f"--{part}", path])
                    task.run_shell(heimdall_args, sudo=True)
                    task.emit("Step 1 complete.", "success")
        else:
            task.emit("Step 1 skipped.", "info")

        if recovery_img:
            task.emit("")
            task.emit("=== Step 2: Flash custom recovery ===", "info")
            if Path(recovery_img).is_file():
                task.emit("Ensure device is in Download Mode.", "warn")
                task.run_shell(["heimdall", "flash", "--RECOVERY", recovery_img, "--no-reboot"], sudo=True)
                task.emit("Step 2 complete.", "success")
        else:
            task.emit("Step 2 skipped.", "info")

        if rom_zip:
            task.emit("")
            task.emit("=== Step 3: Sideload custom ROM ===", "info")
            if Path(rom_zip).is_file():
                h = hashlib.sha256(Path(rom_zip).read_bytes()).hexdigest()
                task.emit(f"SHA256: {h}")
                task.emit("Start ADB sideload on the device.", "warn")
                time.sleep(3)
                task.run_shell(["adb", "sideload", rom_zip])
                task.emit("Step 3 complete.", "success")
        else:
            task.emit("Step 3 skipped.", "info")

        if gapps_zip:
            task.emit("")
            task.emit("=== Step 4: Sideload GApps ===", "info")
            if Path(gapps_zip).is_file():
                task.emit("Start ADB sideload again for GApps.", "warn")
                time.sleep(3)
                task.run_shell(["adb", "sideload", gapps_zip])
                task.emit("Step 4 complete.", "success")
        else:
            task.emit("Step 4 skipped.", "info")

        task.emit("")
        task.emit("Workflow finished! Reboot from recovery.", "success")
        task.done(True)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@bp.route("/api/download-and-flash", methods=["POST"])
def api_download_and_flash():
    """One-click: download a ROM then flash it automatically."""
    url = request.json.get("url", "")
    filename = Path(request.json.get("filename", "rom.zip")).name
    if not filename or filename.startswith("."):
        filename = "rom.zip"
    codename = request.json.get("codename", "unknown")
    ipfs_cid = request.json.get("ipfs_cid", "")
    rom_id = request.json.get("rom_id", "")
    rom_name = request.json.get("rom_name", "")
    version = request.json.get("version", "")
    flash_method = request.json.get("flash_method", "sideload")
    recovery_url = request.json.get("recovery_url", "")

    if not url and not ipfs_cid:
        return jsonify({"error": "No download URL or IPFS CID provided"}), 400

    target = Path.home() / "Osmosis-downloads" / codename
    dest = str(target / filename)

    def _run(task: Task):
        import datetime
        import hashlib
        import time

        target.mkdir(parents=True, exist_ok=True)

        task.emit("=== Phase 1: Download ROM ===", "info")
        fetched_from_ipfs = False
        # Check IPFS index for cached copy if no CID was provided
        effective_cid = ipfs_cid
        if not effective_cid and ipfs_available():
            cached = ipfs_index_lookup(codename, filename)
            if cached:
                effective_cid = cached["cid"]
                task.emit(f"Found in local IPFS cache: {effective_cid[:24]}...", "info")

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
            rc = task.run_shell(["wget", "--progress=dot:giga", "-O", dest, url])
            if rc != 0:
                task.emit("Download failed.", "error")
                if Path(dest).exists():
                    Path(dest).unlink(missing_ok=True)
                task.done(False)
                return

        result = verify_fetched_file(dest)
        task.emit(f"SHA256: {result['sha256']}")
        if result["known"]:
            task.emit("Integrity check: file matches a known-good firmware entry.", "success")
        else:
            task.emit("Integrity warning: this file is NOT in the firmware registry. Verify before flashing.", "warn")

        if not fetched_from_ipfs and ipfs_available():
            ipfs_pin_and_index(
                dest, key=f"{codename}/{filename}",
                codename=codename, rom_id=rom_id,
                rom_name=rom_name, version=version,
            )

        if recovery_url:
            task.emit("")
            task.emit("=== Phase 2: Flash Recovery ===", "info")
            rec_filename = recovery_url.split("/")[-1] or "recovery.img"
            recovery_dest = str(target / rec_filename)
            rc = task.run_shell(["wget", "--progress=dot:giga", "-O", recovery_dest, recovery_url])
            if rc == 0:
                task.emit("Ensure device is in Download Mode.", "warn")
                task.run_shell(["heimdall", "flash", "--RECOVERY", recovery_dest, "--no-reboot"], sudo=True)

        task.emit("")
        task.emit("=== Phase 3: Flash ROM ===", "info")
        if flash_method == "sideload":
            task.emit("Start ADB sideload on the device.", "warn")
            time.sleep(3)
            rc = task.run_shell(["adb", "sideload", dest])
        elif flash_method == "heimdall":
            task.emit("Ensure device is in Download Mode.", "warn")
            work_dir = Path.home() / "Downloads" / (Path(dest).stem + "-unpacked")
            work_dir.mkdir(parents=True, exist_ok=True)
            task.run_shell(["unzip", "-o", dest, "-d", str(work_dir)])
            import glob as glob_mod

            images = {}
            for pattern in ["BL_*.tar.md5", "AP_*.tar.md5", "CP_*.tar.md5", "CSC_*.tar.md5"]:
                for f in glob_mod.glob(str(work_dir / pattern)):
                    task.run_shell(["tar", "-xvf", f, "-C", str(work_dir)])
            for name in ["boot.img", "recovery.img", "system.img", "super.img", "modem.bin"]:
                if (work_dir / name).exists():
                    images[name.split(".")[0].upper()] = str(work_dir / name)
            if images:
                heimdall_args = ["heimdall", "flash"]
                for part, path in images.items():
                    heimdall_args.extend([f"--{part}", path])
                rc = task.run_shell(heimdall_args, sudo=True)
            else:
                task.emit("No flashable images found.", "error")
                rc = 1
        else:
            task.emit(f"Unknown flash method: {flash_method}", "error")
            rc = 1

        task.emit("")
        if rc == 0:
            task.emit("All done! Reboot from recovery.", "success")
        task.done(rc == 0)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id, "dest": dest})
