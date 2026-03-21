"""System routes: status, install-tool, task streaming, browse, logs, companion tools."""

import json
import os
import subprocess
import tarfile
import tempfile
from pathlib import Path

from flask import Blueprint, jsonify, request

from web.core import LOG_DIR, Task, cmd_exists, start_task
from web.ipfs_helpers import ipfs_available

bp = Blueprint("system", __name__)


# ---------------------------------------------------------------------------
# Status & install
# ---------------------------------------------------------------------------


@bp.route("/api/status")
def api_status():
    """System status: check which tools are available."""
    return jsonify(
        {
            "heimdall": cmd_exists("heimdall"),
            "adb": cmd_exists("adb"),
            "wget": cmd_exists("wget"),
            "curl": cmd_exists("curl"),
            "lz4": cmd_exists("lz4"),
            "ipfs": ipfs_available(),
            "dnsmasq": cmd_exists("dnsmasq"),
        }
    )


_INSTALL_CMDS: dict[str, list[list[str]]] = {
    "adb": [["sudo", "apt-get", "install", "-y", "adb"]],
    "heimdall": [["sudo", "apt-get", "install", "-y", "heimdall-flash"]],
    "wget": [["sudo", "apt-get", "install", "-y", "wget"]],
    "curl": [["sudo", "apt-get", "install", "-y", "curl"]],
    "lz4": [["sudo", "apt-get", "install", "-y", "lz4"]],
    "dnsmasq": [["sudo", "apt-get", "install", "-y", "dnsmasq"]],
    "ipfs": [],
}


@bp.route("/api/install-tool", methods=["POST"])
def api_install_tool():
    """Install a missing system tool."""
    tool = request.json.get("tool", "")
    if tool not in _INSTALL_CMDS:
        return jsonify({"error": f"Unknown tool: {tool}"}), 400

    if tool == "ipfs":
        if ipfs_available():
            return jsonify({"error": "IPFS is already available"}), 400
    elif cmd_exists(tool):
        return jsonify({"error": f"{tool} is already installed"}), 400

    def _run(task: Task):
        if tool == "ipfs":
            _install_ipfs(task)
        else:
            task.emit(f"Installing {tool}...")
            task.run_shell(["sudo", "apt-get", "update"])
            for cmd in _INSTALL_CMDS[tool]:
                rc = task.run_shell(cmd)
                if rc != 0:
                    task.emit(f"Failed to install {tool}.", "error")
                    task.done(False)
                    return
            task.emit(f"{tool} installed.", "success")
        ok = ipfs_available() if tool == "ipfs" else cmd_exists(tool)
        if ok:
            task.emit(f"{tool} is now available.", "success")
        else:
            task.emit(f"{tool} install may have failed — please check.", "warn")
        task.done(ok)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


def _install_ipfs(task: Task):
    """Download and install kubo (IPFS CLI), then start the daemon."""
    import platform
    import time

    arch = platform.machine()
    arch_map = {"x86_64": "amd64", "aarch64": "arm64", "armv7l": "arm"}
    go_arch = arch_map.get(arch, "amd64")

    # Try to fetch latest stable version; fall back to known-good version
    version = "v0.33.2"
    try:
        r = subprocess.run(
            ["curl", "-sL", "--max-time", "5", "https://dist.ipfs.tech/kubo/versions"],
            capture_output=True, text=True, timeout=8,
        )
        if r.returncode == 0 and r.stdout.strip():
            stable = [v.strip() for v in r.stdout.strip().splitlines()
                       if v.strip().startswith("v") and "-rc" not in v]
            if stable:
                version = stable[-1]
    except Exception:
        pass

    url = f"https://dist.ipfs.tech/kubo/{version}/kubo_{version}_linux-{go_arch}.tar.gz"

    task.emit(f"Downloading IPFS (kubo {version} for {go_arch})...")
    with tempfile.TemporaryDirectory() as tmp:
        tarball = os.path.join(tmp, "kubo.tar.gz")
        rc = task.run_shell(["wget", "-q", "-O", tarball, url])
        if rc != 0:
            rc = task.run_shell(["curl", "-sL", "-o", tarball, url])
        if rc != 0:
            task.emit("Download failed.", "error")
            task.done(False)
            return

        task.emit("Extracting...")
        try:
            with tarfile.open(tarball, "r:gz") as tf:
                tf.extractall(tmp, filter="data")
        except Exception as e:
            task.emit(f"Extract failed: {e}", "error")
            task.done(False)
            return

        install_script = os.path.join(tmp, "kubo", "install.sh")
        if os.path.exists(install_script):
            task.emit("Running installer...")
            rc = task.run_shell(["sudo", "bash", install_script])
        else:
            binary = os.path.join(tmp, "kubo", "ipfs")
            task.emit("Copying ipfs binary to /usr/local/bin/...")
            rc = task.run_shell(["sudo", "cp", binary, "/usr/local/bin/ipfs"])

        if rc != 0:
            task.emit("Install failed.", "error")
            task.done(False)
            return

    ipfs_path = Path.home() / ".ipfs"
    if not ipfs_path.exists():
        task.emit("Initializing IPFS repository...")
        task.run_shell(["ipfs", "init"])

        # Harden: ensure API only listens on localhost
        task.emit("Configuring IPFS security settings...")
        task.run_shell(["ipfs", "config", "Addresses.API", "/ip4/127.0.0.1/tcp/5001"])
        task.run_shell(["ipfs", "config", "Addresses.Gateway", "/ip4/127.0.0.1/tcp/8080"])
        task.run_shell([
            "ipfs", "config", "--json", "API.HTTPHeaders.Access-Control-Allow-Origin",
            '["http://127.0.0.1:5001"]',
        ])
        task.run_shell([
            "ipfs", "config", "--json", "API.HTTPHeaders.Access-Control-Allow-Methods",
            '["PUT", "POST", "GET"]',
        ])
        task.emit("IPFS API restricted to localhost only.", "success")

    task.emit("Starting IPFS daemon...")
    subprocess.Popen(
        ["ipfs", "daemon"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    time.sleep(3)
    task.emit("IPFS daemon started.", "success")


# ---------------------------------------------------------------------------
# Task streaming
# ---------------------------------------------------------------------------


@bp.route("/api/task/<task_id>/cancel", methods=["POST"])
def api_task_cancel(task_id):
    from web.core import tasks

    task = tasks.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    if task.status != "running":
        return jsonify({"error": "Task not running"}), 400
    task.cancel()
    return jsonify({"ok": True})


@bp.route("/api/stream/<task_id>")
def api_stream(task_id):
    import queue as queue_mod

    from flask import Response, stream_with_context

    from web.core import tasks

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
            except queue_mod.Empty:
                yield "data: {}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# Browse & logs
# ---------------------------------------------------------------------------


@bp.route("/api/browse")
def api_browse():
    """Simple file/directory browser."""
    path = request.args.get("path", str(Path.home()))
    shortcuts = {
        "__downloads__": str(Path.home() / "Downloads"),
        "__desktop__": str(Path.home() / "Desktop"),
        "__osmosis__": str(Path.home() / "Osmosis-downloads"),
    }
    if path in shortcuts:
        path = shortcuts[path]
        Path(path).mkdir(parents=True, exist_ok=True)
    try:
        p = Path(path).resolve()
        if not p.exists():
            return jsonify({"error": "Path not found"}), 404
        if p.is_file():
            return jsonify({"type": "file", "path": str(p), "name": p.name, "size": p.stat().st_size})
        entries = []
        if p.parent != p:
            entries.append({"name": "..", "path": str(p.parent), "type": "dir", "size": 0})
        for child in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            try:
                entries.append(
                    {
                        "name": child.name,
                        "path": str(child),
                        "type": "dir" if child.is_dir() else "file",
                        "size": child.stat().st_size if child.is_file() else 0,
                    }
                )
            except PermissionError:
                continue
        return jsonify({"type": "dir", "path": str(p), "entries": entries})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/logs")
def api_logs():
    """List session logs."""
    logs = []
    if LOG_DIR.exists():
        for f in sorted(LOG_DIR.glob("session-*.log"), reverse=True):
            logs.append({"name": f.name, "path": str(f), "size": f.stat().st_size, "modified": f.stat().st_mtime})
    return jsonify(logs)


@bp.route("/api/logs/<name>")
def api_log_content(name):
    """Read a specific log file."""
    log_file = LOG_DIR / name
    if not log_file.exists() or not log_file.name.startswith("session-"):
        return jsonify({"error": "Log not found"}), 404
    content = log_file.read_text(errors="replace")
    lines = content.splitlines()[-2000:]
    return jsonify({"name": name, "content": "\n".join(lines)})


# ---------------------------------------------------------------------------
# Companion tools
# ---------------------------------------------------------------------------


@bp.route("/api/companion-script")
def api_companion_script():
    """Generate a Termux/Android companion script."""
    script = r"""#!/data/data/com.termux/files/usr/bin/bash
# Osmosis Companion Script for Termux
echo "=== Osmosis Companion ==="
echo ""
if [ -z "$TERMUX_VERSION" ]; then
    echo "This script is designed for Termux on Android."
    echo "Install Termux from F-Droid: https://f-droid.org/en/packages/com.termux/"
    exit 1
fi
echo "[1/4] Checking USB debugging..."
if command -v getprop >/dev/null 2>&1; then
    echo "  USB config: $(getprop persist.sys.usb.config 2>/dev/null)"
else
    echo "  Run: Settings > Developer options > USB debugging = ON"
fi
echo ""
echo "[2/4] Setting up storage access..."
termux-setup-storage 2>/dev/null || echo "  Run: termux-setup-storage"
echo ""
echo "[3/4] Installing tools..."
pkg update -y
pkg install -y tsu android-tools openssh curl wget
echo ""
echo "[4/4] Device information:"
echo "  Brand:    $(getprop ro.product.brand 2>/dev/null)"
echo "  Model:    $(getprop ro.product.model 2>/dev/null)"
echo "  Codename: $(getprop ro.product.device 2>/dev/null)"
echo "  Android:  $(getprop ro.build.version.release 2>/dev/null)"
echo "  Security: $(getprop ro.build.version.security_patch 2>/dev/null)"
echo ""
if su -c "id" 2>/dev/null | grep -q "uid=0"; then echo "  Root: YES"; else echo "  Root: NO"; fi
echo ""
echo "=== Device is ready! ==="
echo "Connect via USB to your computer running Osmosis."
echo ""
echo "=== Update Checker ==="
OSMOSIS_HOST="${OSMOSIS_HOST:-http://192.168.1.100:5000}"
CODENAME="$(getprop ro.product.device 2>/dev/null)"
if [ -n "$CODENAME" ]; then
    echo "Checking for ROM updates for $CODENAME..."
    RESULT=$(curl -sL --max-time 10 "$OSMOSIS_HOST/api/romfinder/$CODENAME" 2>/dev/null)
    if [ -n "$RESULT" ]; then
        echo "$RESULT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    roms = data.get('roms', [])
    if not roms:
        print('  No ROMs found for this device.')
    else:
        for r in roms[:5]:
            name = r.get('name', '?')
            ver = r.get('version', '')
            src = ' (IPFS)' if r.get('ipfs_cid') else ''
            print(f'  {name} {ver}{src}')
except: print('  Could not parse update info.')
" 2>/dev/null
    else
        echo "  Could not reach Osmosis server at $OSMOSIS_HOST"
        echo "  Set OSMOSIS_HOST=http://<your-ip>:5000 and retry."
    fi
else
    echo "  Could not detect device codename."
fi
"""
    return (
        script,
        200,
        {"Content-Type": "text/plain", "Content-Disposition": "attachment; filename=osmosis-companion.sh"},
    )


@bp.route("/api/companion-tools")
def api_companion_tools():
    """List companion tools and their download info."""
    tools = [
        {
            "id": "termux-script",
            "name": "Termux Companion Script",
            "platform": "android",
            "icon": "terminal",
            "desc": "Bash script to prepare your Android device for flashing.",
            "action": "download",
            "url": "/api/companion-script",
        },
        {
            "id": "termux",
            "name": "Termux",
            "platform": "android",
            "icon": "terminal",
            "desc": "Terminal emulator for Android.",
            "action": "link",
            "url": "https://f-droid.org/en/packages/com.termux/",
        },
        {
            "id": "magisk",
            "name": "Magisk",
            "platform": "android",
            "icon": "root",
            "desc": "Root access manager.",
            "action": "link",
            "url": "https://github.com/topjohnwu/Magisk/releases",
        },
        {
            "id": "odin",
            "name": "Odin (Windows)",
            "platform": "windows",
            "icon": "flash",
            "desc": "Samsung's official flashing tool.",
            "action": "link",
            "url": "https://odindownloader.com/",
        },
        {
            "id": "heimdall-suite",
            "name": "Heimdall Suite",
            "platform": "cross",
            "icon": "flash",
            "desc": "Cross-platform Samsung flashing tool.",
            "action": "link",
            "url": "https://github.com/Benjamin-Dobell/Heimdall/releases",
        },
        {
            "id": "adb-platform-tools",
            "name": "Android Platform Tools",
            "platform": "cross",
            "icon": "tools",
            "desc": "Official ADB and fastboot from Google.",
            "action": "link",
            "url": "https://developer.android.com/tools/releases/platform-tools",
        },
    ]
    return jsonify(tools)


# ---------------------------------------------------------------------------
# Plugin management
# ---------------------------------------------------------------------------


@bp.route("/api/plugins")
def api_plugins():
    """List all registered device driver plugins."""
    from web.plugin import list_plugins
    return jsonify([{
        "id": p.id,
        "name": p.name,
        "category": p.category,
        "version": p.version,
        "capabilities": p.capabilities,
    } for p in list_plugins()])


@bp.route("/api/plugins/detect/<plugin_id>")
def api_plugin_detect(plugin_id: str):
    """Run device detection using a specific plugin."""
    from web.plugin import get_driver
    driver = get_driver(plugin_id)
    if not driver:
        return jsonify({"error": f"Plugin '{plugin_id}' not found"}), 404
    try:
        devices = driver.detect()
        return jsonify({"plugin": plugin_id, "devices": devices})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/plugins/info/<plugin_id>/<device_id>")
def api_plugin_info(plugin_id: str, device_id: str):
    """Read device info using a specific plugin."""
    from web.plugin import get_driver
    driver = get_driver(plugin_id)
    if not driver:
        return jsonify({"error": f"Plugin '{plugin_id}' not found"}), 404
    try:
        info = driver.info(device_id)
        return jsonify(info)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
