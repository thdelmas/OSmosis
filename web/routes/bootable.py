"""Bootable media, block devices, PXE boot, and network interface routes."""

import hashlib
import json
import re
import subprocess
from pathlib import Path

from flask import Blueprint, jsonify, request

from web.core import Task, cmd_exists, start_task

bp = Blueprint("bootable", __name__)


def _get_system_drives() -> set[str]:
    """Return set of device names that host the running OS."""
    system_devs: set[str] = set()
    try:
        r = subprocess.run(
            ["lsblk", "-ln", "-o", "NAME,MOUNTPOINT,TYPE"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in r.stdout.strip().splitlines():
            parts = line.split()
            if len(parts) < 3:
                continue
            name, mount = parts[0], parts[1] if len(parts) > 1 else ""
            if mount in ("/", "/boot", "/boot/efi", "[SWAP]") or mount.startswith("/boot"):
                parent = subprocess.run(
                    ["lsblk", "-no", "PKNAME", f"/dev/{name}"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                parent_name = parent.stdout.strip().splitlines()[-1].strip() if parent.stdout.strip() else name
                system_devs.add(parent_name if parent_name else name)
    except Exception:
        pass
    return system_devs


def _parse_size_bytes(size_str: str) -> int | None:
    """Parse lsblk size like '14.9G' to bytes."""
    size_str = size_str.strip().upper()
    multipliers = {"B": 1, "K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4}
    for suffix, mult in multipliers.items():
        if size_str.endswith(suffix):
            try:
                return int(float(size_str[:-1]) * mult)
            except ValueError:
                return None
    try:
        return int(size_str)
    except ValueError:
        return None


@bp.route("/api/blockdevices")
def api_blockdevices():
    """List block devices suitable for bootable media creation."""
    devices = []
    system_drives = _get_system_drives()
    try:
        r = subprocess.run(
            ["lsblk", "-J", "-o", "NAME,SIZE,TYPE,MOUNTPOINT,TRAN,MODEL,VENDOR,RM"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if r.returncode == 0:
            data = json.loads(r.stdout)
            for blk in data.get("blockdevices", []):
                if blk.get("type") != "disk" or blk["name"] in system_drives:
                    continue
                is_removable = blk.get("rm") in (True, "1", 1)
                is_usb = blk.get("tran") in ("usb", "USB")
                if not is_removable and not is_usb:
                    continue
                model = (blk.get("vendor", "") + " " + blk.get("model", "")).strip()
                size_str = blk.get("size", "")
                size_bytes = _parse_size_bytes(size_str)
                devices.append(
                    {
                        "name": blk["name"],
                        "path": f"/dev/{blk['name']}",
                        "size": size_str,
                        "size_bytes": size_bytes,
                        "model": model or blk["name"],
                        "transport": blk.get("tran", ""),
                        "mounted": bool(blk.get("mountpoint")),
                        "is_system": False,
                        "large_drive": size_bytes is not None and size_bytes > 128 * 1024**3,
                    }
                )
    except Exception:
        pass
    return jsonify(devices)


@bp.route("/api/bootable", methods=["POST"])
def api_bootable():
    """Write an ISO/IMG to a USB drive or SD card."""
    image_path = request.json.get("image_path", "")
    target_device = request.json.get("target_device", "")
    block_size = request.json.get("block_size", "4M")
    skip_verify = request.json.get("skip_verify", False)

    if not image_path or not Path(image_path).is_file():
        return jsonify({"error": "Image file not found"}), 400
    if not target_device or not target_device.startswith("/dev/"):
        return jsonify({"error": "Invalid target device"}), 400

    try:
        check = subprocess.run(["lsblk", "-no", "RM,TYPE", target_device], capture_output=True, text=True, timeout=5)
        fields = check.stdout.strip().split()
        if len(fields) < 2 or fields[1] != "disk":
            return jsonify({"error": f"{target_device} is not a whole disk"}), 400
    except Exception:
        pass

    system_drives = _get_system_drives()
    if target_device.replace("/dev/", "") in system_drives:
        return jsonify({"error": f"{target_device} is your system drive — refusing to write"}), 400

    image_size = Path(image_path).stat().st_size
    try:
        drive_size = int(
            subprocess.run(
                ["lsblk", "-bno", "SIZE", target_device],
                capture_output=True,
                text=True,
                timeout=5,
            )
            .stdout.strip()
            .splitlines()[0]
        )
        if drive_size < image_size:
            return jsonify(
                {"error": f"Image ({image_size // (1024 * 1024)} MB) > drive ({drive_size // (1024 * 1024)} MB)"}
            ), 400
    except Exception:
        pass

    large_drive_warning = False
    try:
        drv_bytes = int(
            subprocess.run(
                ["lsblk", "-bno", "SIZE", target_device],
                capture_output=True,
                text=True,
                timeout=5,
            )
            .stdout.strip()
            .splitlines()[0]
        )
        large_drive_warning = drv_bytes > 128 * 1024**3
    except Exception:
        pass

    def _run(task: Task):
        img_size = Path(image_path).stat().st_size
        task.emit(f"Source image: {image_path}")
        task.emit(f"Image size: {img_size / (1024 * 1024):.1f} MB")

        task.emit("Computing source checksum...")
        sha = hashlib.sha256()
        with open(image_path, "rb") as f:
            while chunk := f.read(4 * 1024 * 1024):
                sha.update(chunk)
        source_hash = sha.hexdigest()
        task.emit(f"SHA256: {source_hash}")
        task.emit(f"Target device: {target_device}")
        if large_drive_warning:
            task.emit("WARNING: Target > 128 GB — verify this is correct!", "warn")
        task.emit("")

        task.emit("Unmounting target device partitions...")
        try:
            lsblk = subprocess.run(
                ["lsblk", "-ln", "-o", "NAME,MOUNTPOINT", target_device], capture_output=True, text=True, timeout=5
            )
            for line in lsblk.stdout.strip().splitlines():
                parts = line.split()
                if len(parts) >= 2 and parts[1]:
                    task.run_shell(["umount", f"/dev/{parts[0]}"], sudo=True)
        except Exception:
            pass

        task.emit("")
        task.emit("Writing image to device...", "warn")
        dd_cmd = [
            "sudo",
            "dd",
            f"if={image_path}",
            f"of={target_device}",
            f"bs={block_size}",
            "status=progress",
            "conv=fsync",
        ]
        task.emit(f"$ {' '.join(dd_cmd)}", "cmd")
        try:
            proc = subprocess.Popen(dd_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
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
                    m = re.match(r"(\d+)\s+bytes?\s.*copied,\s*([\d.,]+)\s*s,\s*([\d.,]+\s*[kMGT]?B/s)", line)
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
        except FileNotFoundError:
            task.emit("Command not found: dd", "error")
            rc = 127
        except Exception as e:
            task.emit(f"Error: {e}", "error")
            rc = 1

        if rc != 0:
            task.emit("Failed to write image.", "error")
            task.done(False)
            return

        task.emit("")
        task.run_shell(["sync"])

        if skip_verify:
            task.emit("Skipping verification.")
        else:
            task.emit("")
            task.emit("Verifying written data...", "warn")
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

        task.emit("")
        task.emit("Bootable device created!", "success")
        task.emit(f"You can now safely remove {target_device}.")
        task.done(True)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id, "large_drive_warning": large_drive_warning})


# ---------------------------------------------------------------------------
# PXE
# ---------------------------------------------------------------------------


@bp.route("/api/pxe/start", methods=["POST"])
def api_pxe_start():
    """Start a PXE boot server using dnsmasq."""
    image_path = request.json.get("image_path", "")
    interface = request.json.get("interface", "")
    server_ip = request.json.get("server_ip", "")
    dhcp_range = request.json.get("dhcp_range", "")
    mode = request.json.get("mode", "proxy")

    if not interface:
        return jsonify({"error": "No network interface specified"}), 400

    def _run(task: Task):
        import shutil as _shutil

        if not cmd_exists("dnsmasq"):
            task.emit("dnsmasq is not installed.", "error")
            task.done(False)
            return

        tftp_root = Path.home() / ".osmosis" / "pxe" / "tftpboot"
        tftp_root.mkdir(parents=True, exist_ok=True)

        actual_ip = server_ip
        if not actual_ip:
            try:
                r = subprocess.run(["ip", "-4", "addr", "show", interface], capture_output=True, text=True, timeout=5)
                m = re.search(r"inet (\d+\.\d+\.\d+\.\d+)/", r.stdout)
                if m:
                    actual_ip = m.group(1)
            except Exception:
                pass
        if not actual_ip:
            task.emit(f"Could not detect IP on {interface}.", "error")
            task.done(False)
            return

        task.emit(f"Server IP: {actual_ip}, Interface: {interface}, Mode: {mode}")

        for src in ["/usr/lib/PXELINUX/pxelinux.0", "/usr/share/syslinux/pxelinux.0", "/usr/lib/syslinux/pxelinux.0"]:
            if Path(src).exists():
                _shutil.copy2(src, str(tftp_root / "pxelinux.0"))
                break

        if image_path and Path(image_path).is_file():
            dest = tftp_root / Path(image_path).name
            if not dest.exists():
                _shutil.copy2(image_path, str(dest))

        pxecfg_dir = tftp_root / "pxelinux.cfg"
        pxecfg_dir.mkdir(exist_ok=True)
        menu = "DEFAULT menu.c32\nPROMPT 0\nMENU TITLE Osmosis PXE Boot\nTIMEOUT 300\n\n"
        menu += "LABEL local\n  MENU LABEL Boot from local disk\n  LOCALBOOT 0\n"
        (pxecfg_dir / "default").write_text(menu)

        dnsmasq_conf = Path.home() / ".osmosis" / "pxe" / "dnsmasq-pxe.conf"
        conf_lines = [f"interface={interface}", "bind-interfaces", "enable-tftp", f"tftp-root={tftp_root}", "log-dhcp"]
        if mode == "proxy":
            conf_lines.extend([f"dhcp-range={actual_ip},proxy", 'pxe-service=x86PC,"Osmosis PXE",pxelinux'])
        else:
            if dhcp_range:
                conf_lines.append(f"dhcp-range={dhcp_range}")
            else:
                parts = actual_ip.split(".")
                parts[-1] = "100"
                start = ".".join(parts)
                parts[-1] = "200"
                end = ".".join(parts)
                conf_lines.append(f"dhcp-range={start},{end},12h")
            conf_lines.append(f"dhcp-boot=pxelinux.0,osmosis,{actual_ip}")
        dnsmasq_conf.write_text("\n".join(conf_lines) + "\n")

        task.emit("Starting PXE server...", "warn")
        rc = task.run_shell(["dnsmasq", "--no-daemon", "-C", str(dnsmasq_conf)], sudo=True)
        task.done(rc == 0)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@bp.route("/api/pxe/stop", methods=["POST"])
def api_pxe_stop():
    try:
        subprocess.run(["pkill", "-f", "dnsmasq.*dnsmasq-pxe.conf"], capture_output=True, text=True, timeout=5)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/interfaces")
def api_interfaces():
    """List network interfaces for PXE setup."""
    interfaces = []
    try:
        r = subprocess.run(["ip", "-j", "link", "show"], capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            for iface in json.loads(r.stdout):
                name = iface.get("ifname", "")
                if name != "lo":
                    interfaces.append({"name": name, "state": iface.get("operstate", "UNKNOWN")})
    except Exception:
        pass
    return jsonify(interfaces)
