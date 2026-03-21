"""Router/OpenWrt flashing routes — TFTP, sysupgrade, and web upload."""

import subprocess
from pathlib import Path

from flask import Blueprint, jsonify, request

from web.core import Task, cmd_exists, start_task
from web.registry import register, verify

bp = Blueprint("router", __name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dnsmasq_available() -> bool:
    return cmd_exists("dnsmasq")


def _curl_available() -> bool:
    return cmd_exists("curl")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@bp.route("/api/router/tools")
def api_router_tools():
    """Check which router-related tools are installed."""
    return jsonify({
        "dnsmasq": _dnsmasq_available(),
        "curl": _curl_available(),
        "tftp": cmd_exists("tftp") or cmd_exists("atftp"),
    })


@bp.route("/api/router/flash/tftp", methods=["POST"])
def api_router_flash_tftp():
    """Flash a router via TFTP failsafe mode.

    JSON body: {
        "fw_path": "/path/to/openwrt-...-sysupgrade.bin",
        "interface": "eth0",
        "router_ip": "192.168.1.1",      (default: 192.168.1.1)
        "host_ip": "192.168.1.2",         (default: 192.168.1.2)
    }

    Sets up a TFTP server on the specified interface and waits for the router
    to request the firmware file during failsafe boot.
    """
    body = request.json or {}
    fw_path = body.get("fw_path", "").strip()
    interface = body.get("interface", "eth0").strip()
    router_ip = body.get("router_ip", "192.168.1.1").strip()
    host_ip = body.get("host_ip", "192.168.1.2").strip()

    if not fw_path or not Path(fw_path).is_file():
        return jsonify({"error": "Firmware file not found"}), 400
    if not _dnsmasq_available():
        return jsonify({"error": "dnsmasq not installed (needed for TFTP server)"}), 503

    def _run(task: Task):
        task.emit(f"Firmware: {fw_path}", "info")
        task.emit(f"Interface: {interface}", "info")
        task.emit(f"Router IP: {router_ip}", "info")
        task.emit(f"Host IP: {host_ip}", "info")

        vr = verify(fw_path)
        task.emit(f"SHA256: {vr['sha256']}")
        if vr["known"]:
            task.emit("Firmware verified against registry.", "success")
        else:
            task.emit("Warning: firmware not in registry.", "warn")
        task.emit("")

        # Configure network interface
        task.emit("Configuring network interface...", "info")
        task.run_shell(["ip", "addr", "flush", "dev", interface], sudo=True)
        task.run_shell(["ip", "addr", "add", f"{host_ip}/24", "dev", interface], sudo=True)
        task.run_shell(["ip", "link", "set", interface, "up"], sudo=True)

        # Copy firmware to TFTP directory
        tftp_dir = Path("/tmp/osmosis-tftp")
        tftp_dir.mkdir(parents=True, exist_ok=True)
        import shutil
        fw_dest = tftp_dir / Path(fw_path).name
        shutil.copy2(fw_path, fw_dest)

        # Start TFTP server via dnsmasq
        task.emit("Starting TFTP server...", "info")
        task.emit("Power cycle the router and enter failsafe/TFTP recovery mode.", "warn")
        task.emit(f"Serving {fw_dest.name} on {host_ip}", "info")
        task.emit("")

        dnsmasq_proc = subprocess.Popen(
            [
                "dnsmasq", "--no-daemon",
                f"--interface={interface}",
                "--enable-tftp",
                f"--tftp-root={tftp_dir}",
                f"--dhcp-range={router_ip},{router_ip},255.255.255.0,5m",
                "--port=0",  # Disable DNS
                "--log-dhcp",
                "--log-facility=-",  # Log to stderr
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        import time
        timeout = 300  # 5 minutes
        start = time.time()
        transfer_seen = False

        try:
            while time.time() - start < timeout:
                if task.cancelled:
                    break
                line = dnsmasq_proc.stdout.readline()
                if not line:
                    break
                line = line.strip()
                if line:
                    task.emit(line)
                if "TFTP" in line and ("sent" in line.lower() or "ack" in line.lower()):
                    transfer_seen = True
                if transfer_seen and "sent" in line.lower():
                    task.emit("Firmware transfer complete!", "success")
                    break
        finally:
            dnsmasq_proc.terminate()
            dnsmasq_proc.wait(timeout=5)

        if transfer_seen:
            task.emit("Router should reboot with new firmware.", "success")
            task.emit("Wait 2-3 minutes, then access the router at http://192.168.1.1", "info")
            register(fw_path, flash_method="tftp", component="router-firmware", sha256=vr["sha256"])
            task.done(True)
        elif task.cancelled:
            task.emit("Cancelled by user.", "warn")
            task.done(False)
        else:
            task.emit("Timed out waiting for TFTP transfer (5 minutes).", "error")
            task.emit("Make sure the router is in failsafe/TFTP mode.", "info")
            task.done(False)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@bp.route("/api/router/flash/sysupgrade", methods=["POST"])
def api_router_flash_sysupgrade():
    """Flash an OpenWrt router via SSH sysupgrade.

    JSON body: {
        "fw_path": "/path/to/openwrt-...-sysupgrade.bin",
        "router_ip": "192.168.1.1",
        "keep_settings": true
    }

    SCPs the firmware to the router, then runs sysupgrade over SSH.
    """
    body = request.json or {}
    fw_path = body.get("fw_path", "").strip()
    router_ip = body.get("router_ip", "192.168.1.1").strip()
    keep_settings = body.get("keep_settings", True)

    if not fw_path or not Path(fw_path).is_file():
        return jsonify({"error": "Firmware file not found"}), 400

    def _run(task: Task):
        task.emit(f"Firmware: {fw_path}", "info")
        task.emit(f"Router: {router_ip}", "info")
        task.emit(f"Keep settings: {keep_settings}", "info")

        vr = verify(fw_path)
        task.emit(f"SHA256: {vr['sha256']}")
        task.emit("")

        # Upload firmware via SCP
        remote_path = "/tmp/firmware.bin"
        task.emit("Uploading firmware to router...", "info")
        rc = task.run_shell([
            "scp", "-o", "StrictHostKeyChecking=no",
            fw_path, f"root@{router_ip}:{remote_path}",
        ])
        if rc != 0:
            task.emit("SCP upload failed. Is SSH enabled on the router?", "error")
            task.done(False)
            return

        # Run sysupgrade
        sysupgrade_flags = "-v"
        if not keep_settings:
            sysupgrade_flags += " -n"

        task.emit("Running sysupgrade on router...", "info")
        task.emit("The router will reboot. Connection will be lost.", "warn")

        rc = task.run_shell([
            "ssh", "-o", "StrictHostKeyChecking=no",
            f"root@{router_ip}",
            f"sysupgrade {sysupgrade_flags} {remote_path}",
        ])

        # sysupgrade kills the SSH connection, so rc != 0 is expected
        task.emit("")
        task.emit("Sysupgrade initiated. Router is rebooting.", "success")
        task.emit(f"Wait 2-3 minutes, then access http://{router_ip}", "info")
        register(fw_path, flash_method="sysupgrade", component="router-firmware", sha256=vr["sha256"])
        task.done(True)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@bp.route("/api/router/flash/web", methods=["POST"])
def api_router_flash_web():
    """Flash a router by uploading firmware to its web admin interface.

    JSON body: {
        "fw_path": "/path/to/firmware.bin",
        "router_ip": "192.168.1.1",
        "upload_url": "/cgi-bin/firmware_upgrade",  (optional)
        "username": "admin",                        (optional)
        "password": "admin"                         (optional)
    }
    """
    body = request.json or {}
    fw_path = body.get("fw_path", "").strip()
    router_ip = body.get("router_ip", "192.168.1.1").strip()
    upload_url = body.get("upload_url", "/cgi-bin/luci/admin/system/flashops/sysupgrade").strip()
    username = body.get("username", "root")
    password = body.get("password", "")

    if not fw_path or not Path(fw_path).is_file():
        return jsonify({"error": "Firmware file not found"}), 400

    def _run(task: Task):
        task.emit(f"Firmware: {fw_path}", "info")
        task.emit(f"Router: http://{router_ip}{upload_url}", "info")

        vr = verify(fw_path)
        task.emit(f"SHA256: {vr['sha256']}")
        task.emit("")

        full_url = f"http://{router_ip}{upload_url}"
        task.emit(f"Uploading firmware to {full_url}...", "info")

        curl_cmd = [
            "curl", "-s", "--max-time", "120",
            "-F", f"image=@{fw_path}",
        ]
        if username:
            curl_cmd.extend(["-u", f"{username}:{password}"])
        curl_cmd.append(full_url)

        rc = task.run_shell(curl_cmd)
        if rc == 0:
            task.emit("Firmware uploaded. Router should begin flashing.", "success")
            task.emit(f"Wait 2-3 minutes, then access http://{router_ip}", "info")
            register(fw_path, flash_method="web-upload", component="router-firmware", sha256=vr["sha256"])
        else:
            task.emit("Upload failed. Check the router IP, URL, and credentials.", "error")
        task.done(rc == 0)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})
