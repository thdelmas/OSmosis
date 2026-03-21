"""Apple T2 security chip backup, restore, and detection routes."""

import hashlib
from pathlib import Path

from flask import Blueprint, jsonify, request

from web.core import Task, cmd_exists, start_task
from web.registry import register

bp = Blueprint("t2", __name__)

_T2_CFG = Path(__file__).resolve().parent.parent.parent / "t2.cfg"

# USB VID:PID for Apple T2 in DFU mode
_T2_DFU_VID = "05ac"
_T2_DFU_PID = "1881"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def parse_t2_cfg() -> list[dict]:
    """Parse t2.cfg and return list of T2-equipped Mac dicts.

    Fields per line (pipe-delimited):
        id|label|model|board_id|bridge_os_url|notes
    """
    macs = []
    if not _T2_CFG.exists():
        return macs
    for line in _T2_CFG.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|")
        if len(parts) < 5:
            continue
        macs.append(
            {
                "id": parts[0],
                "label": parts[1],
                "model": parts[2],
                "board_id": parts[3],
                "bridge_os_url": parts[4],
                "notes": parts[5] if len(parts) > 5 else "",
            }
        )
    return macs


def _t2_tool_available() -> bool:
    """Return True if apple-t2-tool (or t2tool) is on PATH."""
    return cmd_exists("t2tool") or cmd_exists("apple-t2-tool")


def _t2_tool_cmd() -> str:
    """Return the actual command name for the T2 tool."""
    if cmd_exists("t2tool"):
        return "t2tool"
    return "apple-t2-tool"


def _lsusb_available() -> bool:
    return cmd_exists("lsusb")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@bp.route("/api/t2/models")
def api_t2_models():
    """Return all T2-equipped Mac presets from t2.cfg."""
    return jsonify(parse_t2_cfg())


@bp.route("/api/t2/tools")
def api_t2_tools():
    """Check which T2-related tools are installed."""
    return jsonify(
        {
            "t2tool": _t2_tool_available(),
            "lsusb": _lsusb_available(),
            "libusb": cmd_exists("lsusb"),  # proxy for libusb availability
        }
    )


@bp.route("/api/t2/detect")
def api_t2_detect():
    """Detect a T2 chip in DFU mode via USB."""

    def _run(task: Task):
        task.emit("Scanning USB bus for an Apple T2 chip in DFU mode...", "info")
        task.emit(
            "Looking for USB device 05ac:1881 — this is the T2's DFU-mode identifier.",
            "info",
        )
        task.emit("")

        if _lsusb_available():
            rc = task.run_shell(["lsusb", "-d", f"{_T2_DFU_VID}:{_T2_DFU_PID}"])
            if rc == 0:
                task.emit("T2 chip detected in DFU mode.", "success")
            else:
                task.emit(
                    "T2 chip not found on USB.",
                    "warn",
                )
                task.emit("")
                task.emit("Troubleshooting tips:", "info")
                task.emit("  1. Is the Mac powered off? The screen should stay completely black.", "info")
                task.emit("  2. Are you using the correct port? Use the left Thunderbolt port", "info")
                task.emit("     closest to you on MacBooks, or the port nearest Ethernet on desktops.", "info")
                task.emit("  3. Try the DFU sequence again: hold Power for 10 seconds, release,", "info")
                task.emit("     then press Power and hold Right Shift + Left Option + Left Control.", "info")
                task.emit("  4. Try a different USB-C cable — not all cables carry data.", "info")
        else:
            # Fallback: check /sys/bus/usb
            task.emit("lsusb not available — falling back to sysfs scan.", "info")
            task.emit("(Install usbutils for more detailed USB information.)", "info")
            import glob

            found = False
            for vid_path in glob.glob("/sys/bus/usb/devices/*/idVendor"):
                try:
                    vid = Path(vid_path).read_text().strip()
                    pid_path = Path(vid_path).parent / "idProduct"
                    pid = pid_path.read_text().strip()
                    if vid == _T2_DFU_VID and pid == _T2_DFU_PID:
                        found = True
                        dev_path = Path(vid_path).parent
                        task.emit(f"Found at {dev_path.name}", "info")
                        break
                except OSError:
                    continue

            if found:
                task.emit("T2 chip detected in DFU mode (via sysfs).", "success")
            else:
                task.emit(
                    "T2 chip not found. Ensure the Mac is in DFU mode and connected via USB-C.",
                    "warn",
                )

        task.emit("")

        if _t2_tool_available():
            task.emit("Querying T2 chip details via t2tool...", "info")
            rc = task.run_shell([_t2_tool_cmd(), "info"])
            if rc == 0:
                task.emit("T2 chip is responding and ready for backup or restore.", "success")
            else:
                task.emit(
                    "Could not read T2 chip info. The chip may not be fully in DFU mode, "
                    "or the USB connection may be unstable.",
                    "warn",
                )
        else:
            task.emit(
                "t2tool is not installed — detection is limited to USB bus scanning.",
                "warn",
            )
            task.emit(
                "Install t2tool for full T2 communication: https://github.com/t2linux/apple-t2-tool",
                "info",
            )

        task.done(True)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@bp.route("/api/t2/backup", methods=["POST"])
def api_t2_backup():
    """Backup T2 chip firmware via DFU.

    JSON body: {
        "model": "<model id from t2.cfg>",
        "regions": ["firmware", "nvram", "sep"]  // optional, defaults to all
    }
    """
    body = request.json or {}
    model_id = body.get("model", "").strip()
    regions = body.get("regions", ["firmware", "nvram", "sep"])

    if not _t2_tool_available():
        return jsonify({"error": "t2tool not installed (see https://github.com/t2linux/apple-t2-tool)"}), 500

    preset = None
    if model_id:
        preset = next((m for m in parse_t2_cfg() if m["id"] == model_id), None)

    def _run(task: Task):
        from datetime import datetime

        label = preset["label"] if preset else model_id or "unknown-mac"
        backup_dir = Path.home() / ".osmosis" / "t2-backups"
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_name = f"{model_id or 'T2'}-{timestamp}"
        backup_path = backup_dir / backup_name
        backup_path.mkdir(parents=True, exist_ok=True)

        task.emit(f"Mac model: {label}", "info")
        task.emit(f"Backup directory: {backup_path}", "info")
        task.emit(f"Regions to back up: {', '.join(regions)}", "info")
        task.emit("")

        region_explanations = {
            "firmware": "bridgeOS firmware — the T2 chip's own operating system",
            "nvram": "NVRAM — boot configuration, startup disk, display settings",
            "sep": "Secure Enclave — Touch ID, encryption key metadata",
        }
        for r in regions:
            if r in region_explanations:
                task.emit(f"  {r}: {region_explanations[r]}", "info")
        task.emit("")

        # Verify DFU connection
        task.emit("Step 1/3: Verifying T2 DFU connection...", "info")
        rc = task.run_shell([_t2_tool_cmd(), "info"])
        if rc != 0:
            task.emit("Cannot communicate with T2 chip.", "error")
            task.emit(
                "Make sure the Mac is still in DFU mode (screen black) and the USB-C "
                "cable is firmly connected. Try re-entering DFU mode if needed.",
                "info",
            )
            task.done(False)
            return
        task.emit("T2 chip is responding.", "success")
        task.emit("")

        task.emit("Step 2/3: Reading T2 regions...", "info")
        task.emit(
            "Each region is read over USB and saved as a binary file. Do not unplug the cable during this process.",
            "info",
        )
        task.emit("")

        backed_up = 0
        for region in regions:
            dest = backup_path / f"{region}.bin"
            task.emit(f"Reading {region}...", "info")
            rc = task.run_shell([_t2_tool_cmd(), "read", region, "-o", str(dest)])
            if rc == 0 and dest.exists() and dest.stat().st_size > 0:
                size_kb = dest.stat().st_size / 1024
                task.emit(f"  {region}: {size_kb:.1f} KB saved", "success")
                backed_up += 1
            else:
                dest.unlink(missing_ok=True)
                task.emit(f"  {region}: could not be read (this region may not be accessible on all models)", "warn")

        task.emit("")

        if backed_up == 0:
            task.emit("No regions were backed up successfully.", "error")
            task.emit(
                "This can happen if the T2 chip dropped out of DFU mode during the read. "
                "Try re-entering DFU mode and running the backup again.",
                "info",
            )
            task.done(False)
            return

        # Generate checksums
        task.emit("Step 3/3: Generating integrity checksums...", "info")
        task.emit(
            "SHA-256 checksums are saved alongside each backup file so Osmosis can "
            "verify the data hasn't been corrupted before a future restore.",
            "info",
        )
        checksums = []
        for f in sorted(backup_path.glob("*.bin")):
            h = hashlib.sha256(f.read_bytes()).hexdigest()
            checksums.append(f"{h}  {f.name}")
            task.emit(f"  {f.name}: {h[:16]}...", "info")
        if checksums:
            (backup_path / "checksums.sha256").write_text("\n".join(checksums) + "\n")
            task.emit("Checksums saved.", "success")

        # Save model metadata
        import json

        meta = {
            "model_id": model_id,
            "label": label,
            "board_id": preset["board_id"] if preset else "",
            "timestamp": timestamp,
            "regions": regions,
        }
        (backup_path / "t2-info.json").write_text(json.dumps(meta, indent=2) + "\n")

        # Register in firmware registry
        for f in backup_path.glob("*.bin"):
            h = hashlib.sha256(f.read_bytes()).hexdigest()
            register(
                str(f),
                device_id=model_id or "t2-unknown",
                device_label=label,
                component=f"t2-{f.stem}",
                flash_method="t2tool-dfu",
                sha256=h,
            )
        task.emit("Backup registered in the Osmosis firmware registry.", "success")

        task.emit("")
        task.emit(f"T2 backup complete: {backed_up} region(s) saved to {backup_path}", "success")
        task.emit(
            "You can safely exit DFU mode by holding the power button until the Mac restarts.",
            "info",
        )
        task.done(True)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@bp.route("/api/t2/backups")
def api_t2_backups():
    """List available T2 backups."""
    import json

    backup_dir = Path.home() / ".osmosis" / "t2-backups"
    if not backup_dir.exists():
        return jsonify([])

    backups = []
    for d in sorted(backup_dir.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        info = {}
        info_file = d / "t2-info.json"
        if info_file.exists():
            try:
                info = json.loads(info_file.read_text())
            except Exception:
                pass
        bins = list(d.glob("*.bin"))
        total_size = sum(f.stat().st_size for f in bins)
        backups.append(
            {
                "name": d.name,
                "path": str(d),
                "label": info.get("label", "Unknown Mac"),
                "model_id": info.get("model_id", ""),
                "board_id": info.get("board_id", ""),
                "regions": [f.stem for f in sorted(bins)],
                "region_count": len(bins),
                "total_size_kb": round(total_size / 1024, 1),
                "has_checksums": (d / "checksums.sha256").exists(),
            }
        )
    return jsonify(backups)


@bp.route("/api/t2/restore", methods=["POST"])
def api_t2_restore():
    """Restore T2 firmware from a backup.

    JSON body: {
        "backup_name": "mbp-2019-16-20260321-143000",
        "regions": ["firmware"]  // optional, defaults to all
    }
    """
    body = request.json or {}
    backup_name = body.get("backup_name", "")
    selected_regions = body.get("regions")

    backup_dir = Path.home() / ".osmosis" / "t2-backups"
    backup_path = backup_dir / backup_name
    if not backup_path.is_dir():
        return jsonify({"error": f"Backup '{backup_name}' not found"}), 404

    if not _t2_tool_available():
        return jsonify({"error": "t2tool not installed"}), 500

    def _run(task: Task):
        task.emit(f"Restoring T2 from backup: {backup_name}", "info")
        task.emit(
            "This will write the backed-up firmware regions back to the T2 chip. "
            "Do not disconnect the USB-C cable or turn off either computer until "
            "the restore is finished.",
            "warn",
        )
        task.emit("")

        # Step 1: Verify checksums
        task.emit("Step 1/3: Verifying backup integrity...", "info")
        task.emit(
            "Checking SHA-256 checksums to make sure the backup files haven't been corrupted since they were saved.",
            "info",
        )
        checksum_file = backup_path / "checksums.sha256"
        if checksum_file.exists():
            for line in checksum_file.read_text().strip().splitlines():
                parts = line.split("  ", 1)
                if len(parts) != 2:
                    continue
                expected_hash, filename = parts
                filepath = backup_path / filename
                if not filepath.exists():
                    task.emit(f"  {filename}: MISSING — the backup may be incomplete", "error")
                    task.done(False)
                    return
                actual_hash = hashlib.sha256(filepath.read_bytes()).hexdigest()
                if actual_hash != expected_hash:
                    task.emit(f"  {filename}: CHECKSUM MISMATCH — file may be corrupted", "error")
                    task.emit(
                        "The backup file does not match the checksum recorded at backup time. "
                        "This could mean the file was modified or the disk has errors. "
                        "Do NOT restore from a corrupted backup.",
                        "error",
                    )
                    task.done(False)
                    return
                task.emit(f"  {filename}: OK", "success")
            task.emit("All checksums verified.", "success")
        else:
            task.emit(
                "No checksum file found — skipping integrity check. "
                "This backup may have been created by an older version of Osmosis.",
                "warn",
            )
        task.emit("")

        bins = list(backup_path.glob("*.bin"))
        if selected_regions:
            bins = [f for f in bins if f.stem in selected_regions]

        if not bins:
            task.emit("No firmware region files found in this backup.", "error")
            task.done(False)
            return

        # Step 2: Verify DFU
        task.emit("Step 2/3: Checking T2 DFU connection...", "info")
        task.emit("Ensure Mac is in DFU mode and connected via USB-C.", "warn")

        rc = task.run_shell([_t2_tool_cmd(), "info"])
        if rc != 0:
            task.emit("Cannot communicate with T2 chip.", "error")
            task.emit(
                "Re-enter DFU mode: power off the Mac, hold Power for 10 seconds, "
                "release, then press Power and hold Right Shift + Left Option + Left Control.",
                "info",
            )
            task.done(False)
            return
        task.emit("T2 chip is responding.", "success")
        task.emit("")

        # Step 3: Write regions
        task.emit(
            f"Step 3/3: Writing {len(bins)} region(s): {', '.join(f.stem for f in bins)}",
            "info",
        )
        task.emit(
            "Each region is written individually. If the process is interrupted, "
            "re-enter DFU mode and run the restore again.",
            "info",
        )
        task.emit("")

        any_failed = False
        for bin_file in bins:
            region = bin_file.stem
            size_kb = bin_file.stat().st_size / 1024
            task.emit(f"Writing {region} ({size_kb:.1f} KB)...", "info")
            rc = task.run_shell([_t2_tool_cmd(), "write", region, "-i", str(bin_file)])
            if rc == 0:
                task.emit(f"  {region}: restored successfully", "success")
            else:
                task.emit(f"  {region}: write failed", "error")
                any_failed = True

        task.emit("")

        if any_failed:
            task.emit(
                "Some regions failed to restore. The T2 chip may still be functional — "
                "try re-entering DFU mode and running the restore again for the failed regions.",
                "error",
            )
        else:
            task.emit("T2 restore complete!", "success")
            task.emit(
                "You can exit DFU mode by holding the power button until the Mac restarts. "
                "The first boot after a restore may take longer than usual.",
                "info",
            )
        task.done(not any_failed)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})
