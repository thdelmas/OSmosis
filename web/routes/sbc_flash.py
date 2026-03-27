"""SBC (Raspberry Pi, etc.) flash routes: download, flash, and configure."""

import hashlib
import re
import subprocess
from pathlib import Path

from flask import Blueprint, jsonify, request

from web.core import Task, start_task

bp = Blueprint("sbc_flash", __name__)

_DOWNLOAD_DIR = Path.home() / ".osmosis" / "images"


def _unmount_device(device: str, task: Task) -> None:
    """Unmount all partitions on a block device."""
    try:
        r = subprocess.run(
            ["lsblk", "-ln", "-o", "NAME,MOUNTPOINT", device],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in r.stdout.strip().splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[1]:
                task.emit(f"Unmounting /dev/{parts[0]}...")
                task.run_shell(["umount", f"/dev/{parts[0]}"], sudo=True)
    except Exception:
        pass


def _write_custom_toml(boot_mount: str, config: dict) -> str:
    """Generate and write custom.toml for Raspberry Pi first-boot config.

    Config keys: hostname, username, password, wifi_ssid, wifi_password,
    wifi_country, ssh_enabled, ssh_pubkey, timezone, keymap.
    """
    lines = ["config_version = 1", ""]

    hostname = config.get("hostname", "raspberrypi")
    lines.append("[system]")
    lines.append(f'hostname = "{hostname}"')
    lines.append("")

    username = config.get("username", "")
    password = config.get("password", "")
    if username and password:
        # Hash password with openssl
        try:
            r = subprocess.run(
                ["openssl", "passwd", "-5", password],
                capture_output=True,
                text=True,
                timeout=5,
            )
            hashed = r.stdout.strip()
        except Exception:
            hashed = password
        lines.append("[user]")
        lines.append(f'name = "{username}"')
        lines.append(f'password = "{hashed}"')
        lines.append("password_encrypted = true")
        lines.append("")

    ssh_enabled = config.get("ssh_enabled", True)
    if ssh_enabled:
        lines.append("[ssh]")
        lines.append("enabled = true")
        pubkey = config.get("ssh_pubkey", "")
        if pubkey:
            lines.append("password_authentication = false")
            lines.append(f'authorized_keys = ["{pubkey}"]')
        else:
            lines.append("password_authentication = true")
        lines.append("")

    wifi_ssid = config.get("wifi_ssid", "")
    wifi_password = config.get("wifi_password", "")
    if wifi_ssid:
        country = config.get("wifi_country", "FR")
        lines.append("[wlan]")
        lines.append(f'ssid = "{wifi_ssid}"')
        lines.append(f'password = "{wifi_password}"')
        lines.append("password_encrypted = false")
        lines.append("hidden = false")
        lines.append(f'country = "{country}"')
        lines.append("")

    tz = config.get("timezone", "")
    keymap = config.get("keymap", "")
    if tz or keymap:
        lines.append("[locale]")
        if keymap:
            lines.append(f'keymap = "{keymap}"')
        if tz:
            lines.append(f'timezone = "{tz}"')
        lines.append("")

    content = "\n".join(lines) + "\n"
    toml_path = Path(boot_mount) / "custom.toml"
    toml_path.write_text(content)
    return content


@bp.route("/api/sbc/flash", methods=["POST"])
def api_sbc_flash():
    """Download an OS image, flash it to an SD card, and optionally configure.

    Expected JSON body::

        {
            "image_url": "https://...img.xz",
            "target_device": "/dev/sda",
            "config": {
                "hostname": "mypi",
                "username": "mia",
                "password": "changeme",
                "wifi_ssid": "MyNetwork",
                "wifi_password": "secret",
                "wifi_country": "FR",
                "ssh_enabled": true,
                "timezone": "Europe/Paris",
                "keymap": "fr"
            }
        }
    """
    image_url = request.json.get("image_url", "")
    image_path = request.json.get("image_path", "")
    target_device = request.json.get("target_device", "")
    config = request.json.get("config", {})
    skip_verify = request.json.get("skip_verify", False)

    if not target_device or not target_device.startswith("/dev/"):
        return jsonify({"error": "Invalid target device"}), 400

    if not image_url and not image_path:
        return jsonify({"error": "image_url or image_path required"}), 400

    # Safety: refuse to write to system drive
    from web.routes.bootable import _get_system_drives

    system_drives = _get_system_drives()
    dev_name = target_device.replace("/dev/", "")
    if dev_name in system_drives:
        return jsonify({"error": f"{target_device} is your system drive"}), 400

    def _run(task: Task):
        # Step 1: Get the image (download or use local)
        if image_path and Path(image_path).is_file():
            local_img = Path(image_path)
            task.emit(f"Using local image: {local_img.name}")
        elif image_url:
            _DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
            filename = image_url.split("/")[-1].split("?")[0]
            local_img = _DOWNLOAD_DIR / filename

            if local_img.exists():
                task.emit(f"Image already downloaded: {local_img.name}")
            else:
                task.emit(f"Downloading {filename}...", "info")
                rc = task.run_shell(
                    [
                        "curl",
                        "-L",
                        "-o",
                        str(local_img),
                        image_url,
                        "-f",
                        "--retry",
                        "3",
                        "--retry-delay",
                        "5",
                    ]
                )
                if rc != 0 or not local_img.exists():
                    task.emit("Download failed.", "error")
                    task.done(False)
                    return
                task.emit(
                    f"Downloaded: {local_img.stat().st_size / (1024 * 1024):.1f} MB",
                    "success",
                )
        else:
            task.emit("No image source provided.", "error")
            task.done(False)
            return

        # Step 2: Decompress if needed
        raw_img = local_img
        if local_img.suffix == ".xz":
            raw_img = local_img.with_suffix("")  # strip .xz
            if raw_img.exists():
                task.emit(f"Already decompressed: {raw_img.name}")
            else:
                task.emit(f"Decompressing {local_img.name}...", "info")
                rc = task.run_shell(["xz", "-dk", str(local_img)])
                if rc != 0 or not raw_img.exists():
                    task.emit("Decompression failed.", "error")
                    task.done(False)
                    return
                task.emit(
                    f"Decompressed: {raw_img.stat().st_size / (1024 * 1024):.0f} MB",
                    "success",
                )
        elif local_img.suffix == ".gz":
            raw_img = local_img.with_suffix("")
            if raw_img.exists():
                task.emit(f"Already decompressed: {raw_img.name}")
            else:
                task.emit(f"Decompressing {local_img.name}...", "info")
                rc = task.run_shell(["gzip", "-dk", str(local_img)])
                if rc != 0 or not raw_img.exists():
                    task.emit("Decompression failed.", "error")
                    task.done(False)
                    return
                task.emit(
                    f"Decompressed: {raw_img.stat().st_size / (1024 * 1024):.0f} MB",
                    "success",
                )

        task.emit("")

        # Step 3: Checksum the raw image
        img_size = raw_img.stat().st_size
        task.emit(f"Image: {raw_img.name} ({img_size / (1024 * 1024):.0f} MB)")
        task.emit("Computing checksum...")
        sha = hashlib.sha256()
        with open(raw_img, "rb") as f:
            while chunk := f.read(4 * 1024 * 1024):
                sha.update(chunk)
        source_hash = sha.hexdigest()
        task.emit(f"SHA256: {source_hash}")
        task.emit("")

        # Step 4: Unmount and flash
        task.emit(f"Target: {target_device}")
        _unmount_device(target_device, task)
        task.emit("")

        task.emit("Writing image to SD card...", "warn")
        task.emit("Do NOT remove the SD card during this process.", "warn")
        task.emit("")

        dd_cmd = [
            "sudo",
            "dd",
            f"if={raw_img}",
            f"of={target_device}",
            "bs=4M",
            "status=progress",
            "conv=fsync",
        ]
        task.emit(f"$ {' '.join(dd_cmd)}", "cmd")
        try:
            proc = subprocess.Popen(
                dd_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            task._proc = proc
            buf = ""
            for char in iter(lambda: proc.stderr.read(1), ""):
                if task.cancelled:
                    proc.terminate()
                    break
                if char in ("\r", "\n"):
                    line = buf.strip()
                    buf = ""
                    if not line:
                        continue
                    m = re.match(
                        r"(\d+)\s+bytes?\s.*copied,\s*([\d.,]+)\s*s,\s*([\d.,]+\s*[kMGT]?B/s)",
                        line,
                    )
                    if m:
                        written = int(m.group(1))
                        pct = min(int(written * 100 / img_size), 100) if img_size > 0 else 0
                        elapsed = float(m.group(2).replace(",", "."))
                        eta_str = ""
                        if written > 0 and elapsed > 0:
                            bps = written / elapsed
                            eta_secs = int((img_size - written) / bps) if bps > 0 else 0
                            eta_str = f"{eta_secs // 60}m{eta_secs % 60:02d}s" if eta_secs >= 60 else f"{eta_secs}s"
                        task.emit(f"DDPROGRESS:{pct}:{m.group(3)}:{eta_str}:{written}/{img_size}")
                    else:
                        task.emit(line)
                else:
                    buf += char
            proc.wait()
            task._proc = None
            rc = proc.returncode
        except Exception as e:
            task.emit(f"Error: {e}", "error")
            rc = 1

        if rc != 0:
            task.emit("Flash failed.", "error")
            task.done(False)
            return

        task.emit("")
        task.run_shell(["sync"])
        task.emit("Image written.", "success")

        # Step 5: Verify (optional)
        if not skip_verify:
            task.emit("")
            task.emit("Verifying written data...")
            verify_sha = hashlib.sha256()
            bytes_verified = 0
            try:
                proc_v = subprocess.Popen(
                    [
                        "sudo",
                        "dd",
                        f"if={target_device}",
                        "bs=4M",
                        f"count={(img_size + 4 * 1024 * 1024 - 1) // (4 * 1024 * 1024)}",
                        "status=none",
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                task._proc = proc_v
                while True:
                    if task.cancelled:
                        proc_v.terminate()
                        break
                    chunk = proc_v.stdout.read(4 * 1024 * 1024)
                    if not chunk:
                        break
                    remaining = img_size - bytes_verified
                    if len(chunk) > remaining:
                        chunk = chunk[:remaining]
                    verify_sha.update(chunk)
                    bytes_verified += len(chunk)
                    if bytes_verified >= img_size:
                        break
                proc_v.wait()
                task._proc = None
                verify_hash = verify_sha.hexdigest()
                if verify_hash == source_hash:
                    task.emit("Verification PASSED.", "success")
                else:
                    task.emit(f"Source:  {source_hash}", "error")
                    task.emit(f"Device: {verify_hash}", "error")
                    task.emit("Verification FAILED!", "error")
                    task.done(False)
                    return
            except Exception as e:
                task.emit(f"Verification error: {e}", "warn")

        # Step 6: Post-flash configuration (custom.toml)
        if config:
            task.emit("")
            task.emit("Configuring first-boot settings...", "info")

            # Re-read partition table and mount boot partition
            task.run_shell(["partprobe", target_device], sudo=True)
            import time

            time.sleep(2)

            # Find the boot partition (FAT/vfat, usually partition 1)
            boot_part = f"{target_device}1"
            boot_mount = Path.home() / ".osmosis" / "mnt" / "piboot"
            boot_mount.mkdir(parents=True, exist_ok=True)

            task.run_shell(["mount", boot_part, str(boot_mount)], sudo=True)

            # Check it's actually a boot partition
            if (boot_mount / "config.txt").exists() or (boot_mount / "cmdline.txt").exists():
                toml_content = _write_custom_toml(str(boot_mount), config)
                task.emit("Written custom.toml:")
                for line in toml_content.strip().splitlines():
                    if "password" in line.lower() and "encrypted" not in line.lower():
                        task.emit("  [password hidden]")
                    else:
                        task.emit(f"  {line}")

                # Also create empty 'ssh' file as fallback
                if config.get("ssh_enabled", False):
                    (boot_mount / "ssh").touch()
                    task.emit("Created ssh marker file.")

                task.emit("First-boot configuration applied.", "success")
            else:
                task.emit("Boot partition not recognized — skipping config.", "warn")

            task.run_shell(["umount", str(boot_mount)], sudo=True)
            task.run_shell(["sync"])

        task.emit("")
        task.emit("SD card is ready!", "success")
        task.emit("")
        task.emit("Next steps:", "info")
        task.emit("  1. Remove the SD card from your computer", "info")
        task.emit("  2. Insert it into the Pi's microSD slot (underside of the board)", "info")
        task.emit("  3. Connect a 5V/2.5A micro-USB power supply", "info")
        task.emit("  4. First boot may take 1-3 minutes", "info")
        if config.get("ssh_enabled"):
            hostname = config.get("hostname", "raspberrypi")
            username = config.get("username", "pi")
            task.emit(f"  5. SSH: ssh {username}@{hostname}.local", "info")
        task.done(True)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})
