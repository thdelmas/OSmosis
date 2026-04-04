"""Medicat USB device creation routes.

Medicat USB is a bootable PC repair and diagnostics toolkit that uses Ventoy
as its boot manager. The workflow is:
  1. Install Ventoy on a USB drive
  2. Copy user-supplied Medicat files (ISOs/VHDs) to the Ventoy partition
  3. Boot from USB — Ventoy presents the Medicat tool menu
"""

import json
import shutil
import subprocess
from pathlib import Path

from flask import Blueprint, jsonify, request

from web.core import Task, cmd_exists, start_task

bp = Blueprint("medicat", __name__)

_MEDICAT_CFG = Path(__file__).resolve().parent.parent.parent / "medicat.cfg"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def parse_medicat_cfg() -> list[dict]:
    """Parse medicat.cfg and return list of Medicat profile dicts.

    Fields per line (pipe-delimited):
        id|label|min_usb_gb|ventoy_required|notes
    """
    profiles = []
    if not _MEDICAT_CFG.exists():
        return profiles
    for line in _MEDICAT_CFG.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|")
        if len(parts) < 4:
            continue
        profiles.append(
            {
                "id": parts[0],
                "label": parts[1],
                "min_usb_gb": int(parts[2]) if parts[2].isdigit() else 32,
                "ventoy_required": parts[3].lower() in ("yes", "true", "1"),
                "notes": parts[4] if len(parts) > 4 else "",
            }
        )
    return profiles


def _find_ventoy_partition(device: str) -> str | None:
    """Find the Ventoy data partition on a device (typically partition 1)."""
    try:
        r = subprocess.run(
            ["lsblk", "-J", "-o", "NAME,LABEL,FSTYPE,MOUNTPOINT", device],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if r.returncode != 0:
            return None
        data = json.loads(r.stdout)
        for blk in data.get("blockdevices", []):
            for child in blk.get("children", []):
                label = (child.get("label") or "").upper()
                if label in ("VTOYEFI", "VENTOY", "VTOY"):
                    return f"/dev/{child['name']}"
                # Ventoy's data partition is usually the first partition
                if child.get("fstype") in ("exfat", "ntfs", "vfat"):
                    return f"/dev/{child['name']}"
    except Exception:
        pass
    return None


def _is_ventoy_installed(device: str) -> bool:
    """Check if Ventoy is already installed on a device."""
    return _find_ventoy_partition(device) is not None and _has_ventoy_marker(
        device
    )


def _has_ventoy_marker(device: str) -> bool:
    """Check for Ventoy's VTOYEFI partition label."""
    try:
        r = subprocess.run(
            ["lsblk", "-ln", "-o", "LABEL", device],
            capture_output=True,
            text=True,
            timeout=5,
        )
        labels = r.stdout.upper()
        return "VTOYEFI" in labels or "VTOY" in labels
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@bp.route("/api/medicat/profiles")
def api_medicat_profiles():
    """Return all Medicat USB profiles from medicat.cfg."""
    return jsonify(parse_medicat_cfg())


@bp.route("/api/medicat/tools")
def api_medicat_tools():
    """Check which Medicat-related tools are available."""
    ventoy_path = shutil.which("ventoy") or shutil.which("Ventoy2Disk.sh")
    return jsonify(
        {
            "ventoy": ventoy_path is not None,
            "ventoy_path": ventoy_path or "",
            "lsblk": cmd_exists("lsblk"),
            "mount": cmd_exists("mount"),
        }
    )


@bp.route("/api/medicat/check-ventoy", methods=["POST"])
def api_medicat_check_ventoy():
    """Check if Ventoy is installed on the target device."""
    body = request.json or {}
    device = body.get("device", "")
    if not device or not device.startswith("/dev/"):
        return jsonify({"error": "Invalid device"}), 400
    return jsonify(
        {
            "installed": _is_ventoy_installed(device),
            "partition": _find_ventoy_partition(device),
        }
    )


@bp.route("/api/medicat/install-ventoy", methods=["POST"])
def api_medicat_install_ventoy():
    """Install Ventoy on the target USB drive.

    JSON body: {
        "device": "/dev/sdX"
    }
    """
    body = request.json or {}
    device = body.get("device", "")

    if not device or not device.startswith("/dev/"):
        return jsonify({"error": "Invalid device"}), 400

    ventoy_cmd = shutil.which("ventoy") or shutil.which("Ventoy2Disk.sh")
    if not ventoy_cmd:
        return jsonify(
            {
                "error": "Ventoy is not installed. Download it from https://ventoy.net"
            }
        ), 500

    def _run(task: Task):
        task.emit("Installing Ventoy on the USB drive...", "info")
        task.emit(f"Target device: {device}", "info")
        task.emit(
            "This will format the drive and install the Ventoy boot manager. "
            "All existing data on the drive will be erased.",
            "warn",
        )
        task.emit("")

        # Unmount any partitions on the device
        task.emit("Unmounting existing partitions...", "info")
        try:
            lsblk = subprocess.run(
                ["lsblk", "-ln", "-o", "NAME,MOUNTPOINT", device],
                capture_output=True,
                text=True,
                timeout=5,
            )
            for line in lsblk.stdout.strip().splitlines():
                parts = line.split()
                if len(parts) >= 2 and parts[1]:
                    task.run_shell(["umount", f"/dev/{parts[0]}"], sudo=True)
        except Exception:
            pass

        task.emit("")
        task.emit("Running Ventoy installer...", "info")
        task.emit(
            "Ventoy creates two partitions: a large data partition (exFAT) where "
            "you place ISO/VHD files, and a small EFI partition for booting.",
            "info",
        )
        task.emit("")

        # Ventoy2Disk.sh -i means fresh install, -I forces install
        rc = task.run_shell(
            [ventoy_cmd, "-i", "-L", "VENTOY", device], sudo=True
        )

        if rc == 0:
            task.emit("")
            task.emit("Ventoy installed successfully.", "success")
            task.emit(
                "The drive now has a Ventoy boot manager. You can copy Medicat files "
                "to the data partition in the next step.",
                "info",
            )
        else:
            task.emit("")
            task.emit("Ventoy installation failed.", "error")
            task.emit(
                "Check that the USB drive is not write-protected and that Ventoy "
                "is installed correctly on this system.",
                "info",
            )
        task.done(rc == 0)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@bp.route("/api/medicat/copy-files", methods=["POST"])
def api_medicat_copy_files():
    """Copy Medicat files to the Ventoy partition.

    JSON body: {
        "device": "/dev/sdX",
        "medicat_path": "/path/to/medicat/files"
    }
    """
    body = request.json or {}
    device = body.get("device", "")
    medicat_path = body.get("medicat_path", "")

    if not device or not device.startswith("/dev/"):
        return jsonify({"error": "Invalid device"}), 400
    if not medicat_path or not Path(medicat_path).exists():
        return jsonify({"error": "Medicat files path not found"}), 400

    def _run(task: Task):
        src = Path(medicat_path)
        task.emit(f"Source: {src}", "info")
        task.emit(f"Device: {device}", "info")
        task.emit("")

        # Find and mount the Ventoy data partition
        task.emit("Locating Ventoy data partition...", "info")
        ventoy_part = _find_ventoy_partition(device)
        if not ventoy_part:
            task.emit(
                "Could not find a Ventoy data partition on this device. Make sure Ventoy is installed first.",
                "error",
            )
            task.done(False)
            return

        task.emit(f"Ventoy partition: {ventoy_part}", "info")

        mount_point = Path.home() / ".osmosis" / "mnt" / "ventoy"
        mount_point.mkdir(parents=True, exist_ok=True)

        # Check if already mounted
        try:
            findmnt = subprocess.run(
                ["findmnt", "-n", "-o", "TARGET", ventoy_part],
                capture_output=True,
                text=True,
                timeout=5,
            )
            existing_mount = findmnt.stdout.strip()
            if existing_mount:
                mount_point = Path(existing_mount)
                task.emit(f"Already mounted at {mount_point}", "info")
            else:
                task.emit(f"Mounting {ventoy_part} at {mount_point}...", "info")
                rc = task.run_shell(
                    ["mount", ventoy_part, str(mount_point)], sudo=True
                )
                if rc != 0:
                    task.emit("Could not mount the Ventoy partition.", "error")
                    task.done(False)
                    return
        except Exception:
            task.emit(f"Mounting {ventoy_part} at {mount_point}...", "info")
            rc = task.run_shell(
                ["mount", ventoy_part, str(mount_point)], sudo=True
            )
            if rc != 0:
                task.emit("Could not mount the Ventoy partition.", "error")
                task.done(False)
                return

        task.emit("")

        # Collect files to copy (ISOs, VHDs, IMGs, WIMs)
        extensions = {".iso", ".vhd", ".vhdx", ".img", ".wim"}
        if src.is_file():
            files = [src] if src.suffix.lower() in extensions else []
        else:
            files = [
                f
                for f in src.rglob("*")
                if f.is_file() and f.suffix.lower() in extensions
            ]

        if not files:
            # If no bootable files found, copy everything (user may have a directory structure)
            task.emit(
                "No ISO/VHD/WIM files found — copying entire directory contents.",
                "info",
            )
            task.emit("")
            rc = task.run_shell(
                ["cp", "-rv", f"{src}/.", str(mount_point)],
                sudo=True,
            )
            if rc != 0:
                task.emit("File copy failed.", "error")
                task.run_shell(["umount", str(mount_point)], sudo=True)
                task.done(False)
                return
        else:
            total_size = sum(f.stat().st_size for f in files)
            task.emit(
                f"Found {len(files)} bootable file(s) ({total_size / (1024**3):.1f} GB total):",
                "info",
            )
            for f in files:
                task.emit(
                    f"  {f.name} ({f.stat().st_size / (1024**3):.2f} GB)",
                    "info",
                )
            task.emit("")

            task.emit("Copying files to Ventoy partition...", "info")
            task.emit(
                "Large files may take several minutes. Do not remove the USB drive.",
                "warn",
            )
            task.emit("")

            for i, f in enumerate(files, 1):
                task.emit(f"[{i}/{len(files)}] Copying {f.name}...", "info")
                rc = task.run_shell(
                    ["cp", "-v", str(f), str(mount_point / f.name)],
                    sudo=True,
                )
                if rc != 0:
                    task.emit(f"Failed to copy {f.name}.", "error")
                    task.run_shell(["umount", str(mount_point)], sudo=True)
                    task.done(False)
                    return

        task.emit("")
        task.emit("Syncing filesystem...", "info")
        task.run_shell(["sync"])

        task.emit("Unmounting Ventoy partition...", "info")
        task.run_shell(["umount", str(mount_point)], sudo=True)

        task.emit("")
        task.emit("Medicat USB device created successfully!", "success")
        task.emit(
            "You can now boot from this USB drive. The Ventoy menu will show all available Medicat tools.",
            "info",
        )
        task.done(True)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})
