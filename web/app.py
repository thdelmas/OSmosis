#!/usr/bin/env python3
"""
Osmosis Web UI — local Flask app for Samsung device flashing.
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
LOG_DIR = Path.home() / ".osmosis" / "logs"
BACKUP_DIR = Path.home() / ".osmosis" / "backups"
IPFS_INDEX = Path.home() / ".osmosis" / "ipfs-index.json"
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


# ---------------------------------------------------------------------------
# IPFS helpers
# ---------------------------------------------------------------------------

def ipfs_available() -> bool:
    """Check if the IPFS CLI (kubo) is installed and the daemon is reachable."""
    if not cmd_exists("ipfs"):
        return False
    try:
        r = subprocess.run(
            ["ipfs", "id"], capture_output=True, text=True, timeout=5,
        )
        return r.returncode == 0
    except Exception:
        return False


def ipfs_index_load() -> dict:
    """Load the local IPFS CID index.

    Structure: { "<codename>/<filename>": { "cid": "Qm...", "size": 123,
    "rom_id": "lineageos", "rom_name": "LineageOS", "version": "21.0",
    "pinned_at": "2026-03-20T..." } }
    """
    if IPFS_INDEX.exists():
        try:
            return json.loads(IPFS_INDEX.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def ipfs_index_save(index: dict) -> None:
    IPFS_INDEX.parent.mkdir(parents=True, exist_ok=True)
    IPFS_INDEX.write_text(json.dumps(index, indent=2))


def ipfs_add(filepath: str) -> str | None:
    """Add a file to IPFS and return its CID, or None on failure."""
    try:
        r = subprocess.run(
            ["ipfs", "add", "-Q", "--pin", filepath],
            capture_output=True, text=True, timeout=600,
        )
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:
        pass
    return None


def ipfs_cat_to_file(cid: str, dest: str) -> bool:
    """Retrieve a file from IPFS by CID and write it to dest."""
    try:
        r = subprocess.run(
            ["ipfs", "get", "-o", dest, cid],
            capture_output=True, text=True, timeout=600,
        )
        return r.returncode == 0
    except Exception:
        return False


def ipfs_pin_ls(cid: str) -> bool:
    """Check if a CID is pinned locally."""
    try:
        r = subprocess.run(
            ["ipfs", "pin", "ls", "--type=recursive", cid],
            capture_output=True, text=True, timeout=10,
        )
        return r.returncode == 0 and cid in r.stdout
    except Exception:
        return False


class Task:
    """Background task that streams line-by-line output via a queue."""

    def __init__(self, task_id: str):
        self.id = task_id
        self.q: queue.Queue = queue.Queue()
        self.status = "running"
        self.thread: threading.Thread | None = None
        self._proc: subprocess.Popen | None = None
        self.cancelled = False

    def emit(self, msg: str, level: str = "info"):
        self.q.put(json.dumps({"level": level, "msg": msg}))

    def done(self, success: bool = True):
        self.status = "done" if success else "error"
        self.q.put(json.dumps({"level": "done", "msg": self.status}))

    def cancel(self):
        """Cancel the running task by killing the subprocess."""
        self.cancelled = True
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=3)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
        self.emit("Operation cancelled by user.", "warn")
        self.done(False)

    def run_shell(self, cmd: list[str], sudo: bool = False) -> int:
        """Run a shell command, streaming output line by line."""
        if self.cancelled:
            return 1
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
            self._proc = proc
            for line in proc.stdout:
                if self.cancelled:
                    proc.terminate()
                    return 1
                self.emit(line.rstrip())
            proc.wait()
            self._proc = None
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
        "ipfs": ipfs_available(),
        "dnsmasq": cmd_exists("dnsmasq"),
    })


# Install commands for each tool (Debian/Ubuntu)
_INSTALL_CMDS: dict[str, list[list[str]]] = {
    "adb":      [["sudo", "apt-get", "install", "-y", "adb"]],
    "heimdall": [["sudo", "apt-get", "install", "-y", "heimdall-flash"]],
    "wget":     [["sudo", "apt-get", "install", "-y", "wget"]],
    "curl":     [["sudo", "apt-get", "install", "-y", "curl"]],
    "lz4":      [["sudo", "apt-get", "install", "-y", "lz4"]],
    "dnsmasq":  [["sudo", "apt-get", "install", "-y", "dnsmasq"]],
    "ipfs":     [],  # handled specially below
}


@app.route("/api/install-tool", methods=["POST"])
def api_install_tool():
    """Install a missing system tool."""
    tool = request.json.get("tool", "")
    if tool not in _INSTALL_CMDS:
        return jsonify({"error": f"Unknown tool: {tool}"}), 400

    # Already installed?
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
        # Verify
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
    import tarfile
    import tempfile

    arch = platform.machine()
    arch_map = {"x86_64": "amd64", "aarch64": "arm64", "armv7l": "arm"}
    go_arch = arch_map.get(arch, "amd64")
    version = "v0.33.2"
    url = f"https://dist.ipfs.tech/kubo/{version}/kubo_{version}_linux-{go_arch}.tar.gz"

    task.emit(f"Downloading IPFS (kubo {version} for {go_arch})...")
    with tempfile.TemporaryDirectory() as tmp:
        tarball = os.path.join(tmp, "kubo.tar.gz")
        rc = task.run_shell(["wget", "-q", "-O", tarball, url])
        if rc != 0:
            # Fallback to curl
            rc = task.run_shell(["curl", "-sL", "-o", tarball, url])
        if rc != 0:
            task.emit("Download failed.", "error")
            task.done(False)
            return

        task.emit("Extracting...")
        try:
            with tarfile.open(tarball, "r:gz") as tf:
                tf.extractall(tmp)
        except Exception as e:
            task.emit(f"Extract failed: {e}", "error")
            task.done(False)
            return

        install_script = os.path.join(tmp, "kubo", "install.sh")
        if os.path.exists(install_script):
            task.emit("Running installer...")
            rc = task.run_shell(["sudo", "bash", install_script])
        else:
            # Manual copy
            binary = os.path.join(tmp, "kubo", "ipfs")
            task.emit("Copying ipfs binary to /usr/local/bin/...")
            rc = task.run_shell(["sudo", "cp", binary, "/usr/local/bin/ipfs"])

        if rc != 0:
            task.emit("Install failed.", "error")
            task.done(False)
            return

    # Initialize IPFS if not already done
    ipfs_path = Path.home() / ".ipfs"
    if not ipfs_path.exists():
        task.emit("Initializing IPFS repository...")
        task.run_shell(["ipfs", "init"])

    # Start daemon in background
    task.emit("Starting IPFS daemon...")
    subprocess.Popen(
        ["ipfs", "daemon"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    import time
    time.sleep(3)
    task.emit("IPFS daemon started.", "success")


@app.route("/api/devices")
def api_devices():
    return jsonify(parse_devices_cfg())


def _parse_usb_devices() -> list[dict]:
    """Return list of phone-like USB devices from lsusb, with friendly names."""
    import re

    phone_vendors = {
        "04e8": "Samsung",
        "18d1": "Google",
        "1004": "LG",
        "2717": "Xiaomi",
        "22b8": "Motorola",
        "0bb4": "HTC",
        "2a70": "OnePlus",
        "12d1": "Huawei",
        "2ae5": "Fairphone",
        "0fce": "Sony",
        "1949": "Amazon",
        "2b4c": "Nothing",
    }
    devices = []
    try:
        lsusb = subprocess.run(
            ["lsusb"], capture_output=True, text=True, timeout=5
        )
        for line in lsusb.stdout.strip().splitlines():
            low = line.lower()
            for vid, brand in phone_vendors.items():
                if vid in low:
                    # lsusb: "Bus 003 Device 013: ID 04e8:6860 Samsung Electronics Co., Ltd Galaxy series, misc. (MTP mode)"
                    # Extract description after "ID xxxx:xxxx "
                    raw = line
                    id_pos = line.find("ID ")
                    if id_pos != -1:
                        after_id = line[id_pos + 4:]  # skip "ID "
                        space = after_id.find(" ")
                        raw = after_id[space + 1:].strip() if space != -1 else after_id

                    # Clean up to a user-friendly name:
                    # 1. Remove corporate suffixes (Inc., Co., Ltd, Corp., Electronics, etc.)
                    name = re.sub(
                        r'\b(Inc\.?|Co\.?,?\s*Ltd\.?|Corp\.?|Electronics|Technology|Communication)\b',
                        '', raw, flags=re.IGNORECASE
                    )
                    # 2. Remove parenthesized technical details like (MTP mode), (ADB), (PTP)
                    name = re.sub(r'\([^)]*\)', '', name)
                    # 3. Remove "misc.", "series", and similar filler words
                    name = re.sub(r'\b(misc\.?|series)\b', '', name, flags=re.IGNORECASE)
                    # 4. Collapse whitespace, commas, trailing punctuation
                    name = re.sub(r'[,\s]+', ' ', name).strip().strip(',').strip()
                    # 5. If the cleanup left us with just the brand or empty, use brand name
                    if not name or name.lower() == brand.lower():
                        name = brand

                    devices.append({"vendor": brand, "name": name})
                    break
    except Exception:
        pass
    return devices


def _get_adb_prop(serial: str, prop: str) -> str:
    """Get a single Android system property via adb."""
    return subprocess.run(
        ["adb", "-s", serial, "shell", "getprop", prop],
        capture_output=True, text=True, timeout=5,
    ).stdout.strip()


# Fallback table: model number -> common name (for older devices without
# ro.product.marketname).  This doesn't need to be exhaustive — it just
# covers popular devices likely to be flashed with Osmosis.
_MODEL_NAMES: dict[str, str] = {
    # Samsung Galaxy S series
    "GT-I9000": "Galaxy S",
    "GT-I9100": "Galaxy S II",
    "GT-I9300": "Galaxy S III",
    "GT-I9505": "Galaxy S4",
    "GT-I9500": "Galaxy S4",
    "SM-G900F": "Galaxy S5",
    "SM-G920F": "Galaxy S6",
    "SM-G930F": "Galaxy S7",
    "SM-G950F": "Galaxy S8",
    "SM-G960F": "Galaxy S9",
    "SM-G973F": "Galaxy S10",
    # Samsung Galaxy Note series
    "GT-N7000": "Galaxy Note",
    "GT-N7100": "Galaxy Note II",
    "SM-N9005": "Galaxy Note 3",
    "SM-N910F": "Galaxy Note 4",
    "SM-N920C": "Galaxy Note 5",
    # Samsung Galaxy A / J / Tab
    "SM-A520F": "Galaxy A5 (2017)",
    "SM-A750F": "Galaxy A7 (2018)",
    "SM-J530F": "Galaxy J5 (2017)",
    "SM-T210":  "Galaxy Tab 3 7.0",
    "SM-T530":  "Galaxy Tab 4 10.1",
    # Google Nexus / Pixel
    "Nexus 4":  "Nexus 4",
    "Nexus 5":  "Nexus 5",
    "Nexus 5X": "Nexus 5X",
    "Nexus 6P": "Nexus 6P",
    "Pixel":    "Pixel",
    "Pixel XL": "Pixel XL",
    "Pixel 2":  "Pixel 2",
    "Pixel 3a": "Pixel 3a",
    # Fairphone
    "FP2": "Fairphone 2",
    "FP3": "Fairphone 3",
    "FP4": "Fairphone 4",
    "FP5": "Fairphone 5",
}


def _query_adb_device(serial: str) -> dict:
    """Query a single ADB device by serial for model/codename info."""
    model = _get_adb_prop(serial, "ro.product.model")
    codename = _get_adb_prop(serial, "ro.product.device")
    if not codename:
        codename = _get_adb_prop(serial, "ro.product.board")

    # Try to get a friendly marketing name
    brand = _get_adb_prop(serial, "ro.product.brand").capitalize()
    marketing = _get_adb_prop(serial, "ro.product.marketname")
    if not marketing:
        marketing = _get_adb_prop(serial, "ro.config.marketing_name")
    # Fallback: look up common model numbers
    if not marketing:
        marketing = _MODEL_NAMES.get(model, "")

    display_name = marketing or model
    if brand and not display_name.lower().startswith(brand.lower()):
        display_name = f"{brand} {display_name}"

    # Match against devices.cfg
    match = None
    for dev in parse_devices_cfg():
        if dev["model"].lower() == model.lower() or dev["codename"].lower() == codename.lower():
            match = dev
            break

    return {
        "serial": serial,
        "model": model,
        "codename": codename,
        "display_name": display_name,
        "match": match,
    }


@app.route("/api/detect")
def api_detect():
    """Auto-detect connected device via adb."""
    if not cmd_exists("adb"):
        return jsonify({"error": "adb not installed"}), 500

    try:
        dev_list = subprocess.run(
            ["adb", "devices"], capture_output=True, text=True, timeout=5
        )
        # Filter out the header line; look for lines with a connected state
        dev_lines = [
            l for l in dev_list.stdout.strip().splitlines()[1:]
            if l.strip() and ("device" in l.split("\t")[-1:] or "recovery" in l.split("\t")[-1:])
        ]
        if not dev_lines:
            usb_devices = _parse_usb_devices()
            if usb_devices:
                return jsonify({"error": "usb_no_adb", "usb_devices": usb_devices}), 404
            return jsonify({"error": "no_device"}), 404

        # Query each connected ADB device
        serials = [l.split("\t")[0] for l in dev_lines]
        detected = [_query_adb_device(s) for s in serials]

        if len(detected) == 1:
            # Single device — flat response for backward compat
            d = detected[0]
            return jsonify({
                "model": d["model"],
                "codename": d["codename"],
                "display_name": d["display_name"],
                "match": d["match"],
            })
        else:
            # Multiple devices — return the list, let the user pick
            return jsonify({"multiple": True, "devices": detected})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/romfinder/<codename>")
def api_romfinder(codename):
    """Check which ROMs are available for a given device codename."""
    import re
    codename_raw = codename.strip()
    codename = codename_raw.lower()

    # Also try the model number if available (passed as query param)
    model = request.args.get("model", "").strip()

    results = []

    # --- LineageOS: use the v2 API (JSON, not SPA page) ---
    for name in [codename, model.lower()] if model else [codename]:
        if not name:
            continue
        try:
            r = subprocess.run(
                ["curl", "-sL", "--max-time", "8",
                 f"https://download.lineageos.org/api/v2/devices/{name}/builds"],
                capture_output=True, text=True, timeout=12,
            )
            builds = json.loads(r.stdout) if r.stdout.strip().startswith("[") else []
            if builds and isinstance(builds, list) and len(builds) > 0:
                latest = builds[0]  # most recent build
                filename = latest.get("filename", "")
                version = latest.get("version", "")
                file_size = latest.get("size", 0)
                results.append({
                    "id": "lineageos",
                    "name": "LineageOS",
                    "version": version,
                    "filename": filename,
                    "file_size": file_size,
                    "download_url": f"https://mirrorbits.lineageos.org/full/{name}/{filename}" if filename else "",
                    "page_url": f"https://download.lineageos.org/devices/{name}/builds",
                })
                break
        except Exception:
            pass

    # --- /e/OS: check the images server directory listing ---
    for name in [codename, model.lower()] if model else [codename]:
        if not name:
            continue
        try:
            r = subprocess.run(
                ["curl", "-sL", "--max-time", "8",
                 f"https://images.ecloud.global/stable/{name}/"],
                capture_output=True, text=True, timeout=12,
            )
            if r.returncode == 0 and "Not Found" not in r.stdout and name in r.stdout.lower():
                eos_builds = re.findall(
                    r'href="(e-[\d.]+-[^"]+\.zip)"', r.stdout
                )
                latest = eos_builds[-1] if eos_builds else ""
                version = ""
                if latest:
                    m = re.search(r'e-([\d.]+)-', latest)
                    version = m.group(1) if m else ""
                results.append({
                    "id": "eos",
                    "name": "/e/OS",
                    "version": version,
                    "filename": latest,
                    "download_url": f"https://images.ecloud.global/stable/{name}/{latest}" if latest else "",
                    "page_url": f"https://doc.e.foundation/devices/{name}/install",
                })
                break
        except Exception:
            pass

    # --- TWRP: search the Samsung device list page (or generic) ---
    try:
        # TWRP lists devices by brand, search the Samsung page
        r = subprocess.run(
            ["curl", "-sL", "--max-time", "8",
             "https://twrp.me/Devices/Samsung/"],
            capture_output=True, text=True, timeout=12,
        )
        # Look for our codename in the device links
        # Format: <a href="/samsung/samsunggalaxynote2international.html">... (t03g & t0lte)</a>
        pattern = rf'<a\s+href="(/samsung/[^"]+)">[^<]*\({codename}[^)]*\)</a>'
        m = re.search(pattern, r.stdout, re.IGNORECASE)
        if not m:
            # Also try matching the model number in the link text
            if model:
                model_pattern = rf'<a\s+href="(/samsung/[^"]+)">[^<]*{re.escape(model)}[^<]*</a>'
                m = re.search(model_pattern, r.stdout, re.IGNORECASE)
        if m:
            twrp_path = m.group(1)
            results.append({
                "id": "twrp",
                "name": "TWRP Recovery",
                "version": "",
                "filename": "",
                "download_url": "",
                "page_url": f"https://twrp.me{twrp_path}",
            })
    except Exception:
        pass

    # --- postmarketOS: check official images, then wiki ---
    try:
        pmos_found = False
        # 1. Check official pre-built images (edge and latest stable)
        pmos_device = f"samsung-{codename}"
        for channel in ["edge", "v24.12", "v24.06", "v23.12"]:
            if pmos_found:
                break
            try:
                r = subprocess.run(
                    ["curl", "-sL", "--max-time", "6",
                     f"https://images.postmarketos.org/bpo/{channel}/{pmos_device}/"],
                    capture_output=True, text=True, timeout=10,
                )
                if r.returncode == 0 and "404" not in r.stdout[:200] and pmos_device in r.stdout.lower():
                    # Find the latest image file
                    imgs = re.findall(r'href="([^"]+\.img\.xz)"', r.stdout)
                    if imgs:
                        latest = imgs[-1]
                        version = channel
                        results.append({
                            "id": "postmarketos",
                            "name": "postmarketOS",
                            "version": version,
                            "filename": latest,
                            "download_url": f"https://images.postmarketos.org/bpo/{channel}/{pmos_device}/{latest}",
                            "page_url": f"https://images.postmarketos.org/bpo/{channel}/{pmos_device}/",
                        })
                        pmos_found = True
            except Exception:
                pass

        # 2. Fallback: search the wiki to confirm device is supported
        if not pmos_found:
            pmos_terms = [codename_raw]
            if model:
                pmos_terms.append(model)
            for pmos_term in pmos_terms:
                if pmos_found:
                    break
                r = subprocess.run(
                    ["curl", "-sL", "--max-time", "8",
                     f"https://wiki.postmarketos.org/api.php?action=query&list=search&srsearch={pmos_term}&format=json"],
                    capture_output=True, text=True, timeout=12,
                )
                if r.returncode == 0 and r.stdout.strip():
                    try:
                        search_data = json.loads(r.stdout)
                        for sr in search_data.get("query", {}).get("search", []):
                            title = sr.get("title", "")
                            title_low = title.lower()
                            if codename in title_low or (model and model.lower() in title_low):
                                wiki_url = f"https://wiki.postmarketos.org/wiki/{title.replace(' ', '_')}"
                                results.append({
                                    "id": "postmarketos",
                                    "name": "postmarketOS",
                                    "version": "pmbootstrap",
                                    "filename": "",
                                    "download_url": "",
                                    "page_url": wiki_url,
                                    "install_method": "pmbootstrap",
                                })
                                pmos_found = True
                                break
                    except (json.JSONDecodeError, KeyError):
                        pass
    except Exception:
        pass

    # --- Replicant: scrape download URLs from ReplicantImages wiki ---
    try:
        r = subprocess.run(
            ["curl", "-sL", "--max-time", "8",
             "https://redmine.replicant.us/projects/replicant/wiki/ReplicantImages"],
            capture_output=True, text=True, timeout=12,
        )
        if r.returncode == 0:
            # Model number without GT- prefix for matching
            model_short = model.replace("GT-", "").lower() if model else ""
            search_terms = [codename]
            if model_short:
                search_terms.append(model_short)
            for term in search_terms:
                # Find the latest ZIP download URL for this device
                dl_match = re.search(
                    rf'href="(https://download\.replicant\.us/[^"]*/{re.escape(term)}/[^"]*\.zip)"',
                    r.stdout, re.IGNORECASE,
                )
                if dl_match:
                    dl_url = dl_match.group(1)
                    filename = dl_url.rsplit("/", 1)[-1]
                    # Extract version from filename (e.g. replicant-6.0-0004)
                    ver_m = re.search(r'replicant-([\d.]+-\d+)', filename)
                    version = ver_m.group(1) if ver_m else ""
                    # Also grab recovery image URL if available
                    rec_match = re.search(
                        rf'href="(https://download\.replicant\.us/[^"]*/{re.escape(term)}/recovery[^"]*\.img)"',
                        r.stdout, re.IGNORECASE,
                    )
                    entry = {
                        "id": "replicant",
                        "name": "Replicant",
                        "version": version,
                        "filename": filename,
                        "download_url": dl_url,
                        "page_url": f"https://redmine.replicant.us/projects/replicant/wiki/ReplicantImages",
                    }
                    if rec_match:
                        entry["recovery_url"] = rec_match.group(1)
                    results.append(entry)
                    break
    except Exception:
        pass

    # --- Always provide helpful search links ---
    search_links = []
    search_term = model or codename_raw
    search_links.append({
        "id": "xda",
        "name": "XDA Forums",
        "url": f"https://xdaforums.com/search/?q={search_term}+ROM&type=post",
    })
    search_links.append({
        "id": "lineageos_wiki",
        "name": "LineageOS Wiki",
        "url": f"https://wiki.lineageos.org/devices/#samsung",
    })
    search_links.append({
        "id": "postmarketos_wiki",
        "name": "postmarketOS Wiki",
        "url": f"https://wiki.postmarketos.org/wiki/Special:Search?search={search_term}",
    })
    search_links.append({
        "id": "ubports_devices",
        "name": "Ubuntu Touch Devices",
        "url": "https://devices.ubuntu-touch.io/",
    })

    # --- IPFS: check local index for cached ROMs for this codename ---
    ipfs_roms = []
    index = ipfs_index_load()
    seen_rom_ids = {r["id"] for r in results}
    for key, entry in index.items():
        if entry.get("codename") == codename:
            # If this ROM is already in results from upstream, annotate it with CID
            matched = False
            for r in results:
                if r["id"] == entry.get("rom_id") and r.get("filename") == entry.get("filename"):
                    r["ipfs_cid"] = entry["cid"]
                    matched = True
                    break
            # Otherwise add as a standalone IPFS-only result
            if not matched:
                ipfs_roms.append({
                    "id": f"ipfs_{entry.get('rom_id', 'unknown')}",
                    "name": f"{entry.get('rom_name', 'ROM')} (IPFS)",
                    "version": entry.get("version", ""),
                    "filename": entry.get("filename", ""),
                    "download_url": "",
                    "page_url": "",
                    "ipfs_cid": entry["cid"],
                    "source": "ipfs",
                })

    return jsonify({
        "codename": codename,
        "model": model,
        "roms": results + ipfs_roms,
        "search_links": search_links,
    })


@app.route("/api/romfinder/download", methods=["POST"])
def api_romfinder_download():
    """Download a ROM file found by romfinder, optionally from IPFS."""
    url = request.json.get("url", "")
    filename = request.json.get("filename", "rom.zip")
    codename = request.json.get("codename", "unknown")
    ipfs_cid = request.json.get("ipfs_cid", "")
    rom_id = request.json.get("rom_id", "")
    rom_name = request.json.get("rom_name", "")
    version = request.json.get("version", "")

    if not url and not ipfs_cid:
        return jsonify({"error": "No download URL or IPFS CID provided"}), 400

    # Pre-compute destination so the frontend knows where the file will land
    target = Path.home() / "Osmosis-downloads" / codename
    dest = str(target / filename)

    def _run(task: Task):
        import datetime
        import hashlib
        target.mkdir(parents=True, exist_ok=True)

        # Try IPFS first if CID is available
        fetched_from_ipfs = False
        if ipfs_cid and ipfs_available():
            task.emit(f"Fetching from IPFS: {ipfs_cid}")
            task.emit(f"Destination: {dest}")
            task.emit("")
            rc = task.run_shell(["ipfs", "get", "-o", dest, ipfs_cid])
            if rc == 0:
                fetched_from_ipfs = True
            else:
                task.emit("IPFS fetch failed, falling back to HTTP download...", "warn")
                task.emit("")

        # Fall back to HTTP download
        if not fetched_from_ipfs:
            if not url:
                task.emit("No HTTP download URL available.", "error")
                task.done(False)
                return
            task.emit(f"Downloading: {filename}")
            task.emit(f"URL: {url}", "cmd")
            task.emit(f"Destination: {dest}")
            task.emit("")
            rc = task.run_shell(["wget", "--progress=dot:giga", "-O", dest, url])

        if rc == 0:
            h = hashlib.sha256(Path(dest).read_bytes()).hexdigest()
            task.emit(f"SHA256: {h}")
            task.emit(f"Saved to: {dest}", "success")

            # Auto-pin to IPFS if daemon is running and not already from IPFS
            if not fetched_from_ipfs and ipfs_available():
                task.emit("")
                task.emit("Pinning to IPFS for future sharing...")
                cid = ipfs_add(dest)
                if cid:
                    task.emit(f"IPFS CID: {cid}", "success")
                    index = ipfs_index_load()
                    key = f"{codename}/{filename}"
                    index[key] = {
                        "cid": cid,
                        "size": Path(dest).stat().st_size,
                        "filename": filename,
                        "codename": codename,
                        "rom_id": rom_id,
                        "rom_name": rom_name,
                        "version": version,
                        "pinned_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    }
                    ipfs_index_save(index)
                    task.emit(f"Stored in IPFS index: {codename}/{filename}")
                else:
                    task.emit("IPFS pin failed (non-critical).", "warn")
        else:
            task.emit("Download failed.", "error")
            # Clean up partial/error file left by wget on failure
            if Path(dest).exists():
                Path(dest).unlink(missing_ok=True)
        task.done(rc == 0)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id, "dest": dest})


@app.route("/api/task/<task_id>/cancel", methods=["POST"])
def api_task_cancel(task_id):
    """Cancel a running task."""
    task = tasks.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    if task.status != "running":
        return jsonify({"error": "Task not running"}), 400
    task.cancel()
    return jsonify({"ok": True})


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
                # Clean up partial/error file
                if Path(dest).exists():
                    Path(dest).unlink(missing_ok=True)
                any_failed = True

        if any_failed:
            task.emit("Some downloads failed.", "error")
        else:
            task.emit("All downloads finished.", "success")
        task.done(not any_failed)

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


@app.route("/api/pmbootstrap", methods=["POST"])
def api_pmbootstrap():
    """Install postmarketOS via pmbootstrap."""
    device = request.json.get("device", "")  # e.g. "samsung-t03g"
    codename = request.json.get("codename", "")

    if not device and codename:
        device = f"samsung-{codename}"

    def _run(task: Task):
        # Step 1: Check if pmbootstrap is installed
        if not cmd_exists("pmbootstrap"):
            task.emit("pmbootstrap is not installed. Installing via pip...", "info")
            rc = task.run_shell(["pip3", "install", "--user", "pmbootstrap"])
            if rc != 0:
                task.emit("", "info")
                task.emit("Could not install pmbootstrap automatically.", "error")
                task.emit("Install it manually:", "info")
                task.emit("  pip3 install --user pmbootstrap", "cmd")
                task.emit("  or: https://wiki.postmarketos.org/wiki/Installation_guide", "info")
                task.done(False)
                return
            task.emit("pmbootstrap installed.", "success")
            task.emit("")

        # Step 2: Initialize pmbootstrap for the device
        task.emit(f"Initializing pmbootstrap for {device}...", "info")
        task.emit("This will download the postmarketOS source and build an image.", "info")
        task.emit("")

        # Run pmbootstrap init non-interactively
        env = os.environ.copy()
        work_dir = str(Path.home() / ".local" / "var" / "pmbootstrap")

        # Configure and install
        task.emit("Building postmarketOS image (this may take a while)...", "info")
        rc = task.run_shell([
            "pmbootstrap", "--work", work_dir,
            "install", "--no-fde",
            "--device", device,
        ])

        if rc == 0:
            task.emit("")
            task.emit("postmarketOS image built!", "success")
            task.emit("To flash it to your device:", "info")
            task.emit(f"  pmbootstrap flasher flash_rootfs", "cmd")
            task.emit(f"  pmbootstrap flasher flash_kernel", "cmd")
            task.emit("")
            task.emit("Or export the image:", "info")
            task.emit(f"  pmbootstrap export", "cmd")
        else:
            task.emit("")
            task.emit("pmbootstrap build failed. You may need to run it interactively:", "warn")
            task.emit(f"  pmbootstrap init", "cmd")
            task.emit(f"  pmbootstrap install", "cmd")
            task.emit(f"  pmbootstrap flasher flash_rootfs", "cmd")

        task.done(rc == 0)

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
    # Handle shortcut paths
    shortcuts = {
        "__downloads__": str(Path.home() / "Downloads"),
        "__desktop__": str(Path.home() / "Desktop"),
        "__osmosis__": str(Path.home() / "Osmosis-downloads"),
    }
    if path in shortcuts:
        path = shortcuts[path]
        # Create if it doesn't exist (Osmosis-downloads)
        Path(path).mkdir(parents=True, exist_ok=True)
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


# ---------------------------------------------------------------------------
# Routes — IPFS
# ---------------------------------------------------------------------------

@app.route("/api/ipfs/status")
def api_ipfs_status():
    """Check if IPFS daemon is running and reachable."""
    available = ipfs_available()
    info = {}
    if available:
        try:
            r = subprocess.run(
                ["ipfs", "id"], capture_output=True, text=True, timeout=5,
            )
            data = json.loads(r.stdout)
            info = {"peer_id": data.get("ID", ""), "agent": data.get("AgentVersion", "")}
        except Exception:
            pass
    return jsonify({"available": available, **info})


@app.route("/api/ipfs/index")
def api_ipfs_index():
    """List all ROMs stored in the local IPFS index."""
    index = ipfs_index_load()
    items = []
    for key, entry in index.items():
        items.append({"key": key, **entry})
    return jsonify(items)


@app.route("/api/ipfs/pin", methods=["POST"])
def api_ipfs_pin():
    """Pin a downloaded ROM file to IPFS and record its CID."""
    filepath = request.json.get("filepath", "")
    codename = request.json.get("codename", "unknown")
    rom_id = request.json.get("rom_id", "")
    rom_name = request.json.get("rom_name", "")
    version = request.json.get("version", "")

    if not filepath or not Path(filepath).exists():
        return jsonify({"error": "File not found"}), 400
    if not ipfs_available():
        return jsonify({"error": "IPFS daemon not running"}), 503

    def _run(task: Task):
        import datetime
        p = Path(filepath)
        task.emit(f"Pinning to IPFS: {p.name}")
        task.emit(f"File size: {p.stat().st_size / (1024*1024):.1f} MB")
        task.emit("")

        cid = ipfs_add(filepath)
        if not cid:
            task.emit("Failed to add file to IPFS.", "error")
            task.done(False)
            return

        task.emit(f"CID: {cid}", "success")
        task.emit(f"Gateway: https://ipfs.io/ipfs/{cid}")

        # Update local index
        index = ipfs_index_load()
        key = f"{codename}/{p.name}"
        index[key] = {
            "cid": cid,
            "size": p.stat().st_size,
            "filename": p.name,
            "codename": codename,
            "rom_id": rom_id,
            "rom_name": rom_name,
            "version": version,
            "pinned_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        ipfs_index_save(index)

        task.emit("")
        task.emit(f"Stored in IPFS index: {key}", "success")
        task.done(True)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@app.route("/api/ipfs/fetch", methods=["POST"])
def api_ipfs_fetch():
    """Retrieve a ROM from IPFS by CID and save it locally."""
    cid = request.json.get("cid", "")
    codename = request.json.get("codename", "unknown")
    filename = request.json.get("filename", "rom.zip")

    if not cid:
        return jsonify({"error": "No CID provided"}), 400
    if not ipfs_available():
        return jsonify({"error": "IPFS daemon not running"}), 503

    def _run(task: Task):
        import hashlib
        target = Path.home() / "Osmosis-downloads" / codename
        target.mkdir(parents=True, exist_ok=True)
        dest = str(target / filename)

        task.emit(f"Fetching from IPFS: {cid}")
        task.emit(f"Destination: {dest}")
        task.emit("")

        rc = task.run_shell(["ipfs", "get", "-o", dest, cid])
        if rc == 0:
            h = hashlib.sha256(Path(dest).read_bytes()).hexdigest()
            task.emit(f"SHA256: {h}")
            task.emit(f"Saved to: {dest}", "success")
        else:
            task.emit("IPFS fetch failed.", "error")
        task.done(rc == 0)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@app.route("/api/ipfs/unpin", methods=["POST"])
def api_ipfs_unpin():
    """Unpin a ROM from IPFS and remove it from the index."""
    key = request.json.get("key", "")
    if not key:
        return jsonify({"error": "No key provided"}), 400

    index = ipfs_index_load()
    entry = index.get(key)
    if not entry:
        return jsonify({"error": "Not found in index"}), 404

    cid = entry["cid"]
    if ipfs_available():
        subprocess.run(
            ["ipfs", "pin", "rm", cid],
            capture_output=True, text=True, timeout=30,
        )

    del index[key]
    ipfs_index_save(index)
    return jsonify({"ok": True, "cid": cid})


@app.route("/api/blockdevices")
def api_blockdevices():
    """List block devices suitable for bootable media creation."""
    devices = []
    try:
        r = subprocess.run(
            ["lsblk", "-J", "-o", "NAME,SIZE,TYPE,MOUNTPOINT,TRAN,MODEL,VENDOR,RM"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            data = json.loads(r.stdout)
            for blk in data.get("blockdevices", []):
                if blk.get("type") != "disk":
                    continue
                is_removable = blk.get("rm") in (True, "1", 1)
                is_usb = blk.get("tran") in ("usb", "USB")
                if not is_removable and not is_usb:
                    continue
                model = (blk.get("vendor", "") + " " + blk.get("model", "")).strip()
                devices.append({
                    "name": blk["name"],
                    "path": f"/dev/{blk['name']}",
                    "size": blk.get("size", ""),
                    "model": model or blk["name"],
                    "transport": blk.get("tran", ""),
                    "mounted": bool(blk.get("mountpoint")),
                })
    except Exception:
        pass
    return jsonify(devices)


@app.route("/api/bootable", methods=["POST"])
def api_bootable():
    """Write an ISO/IMG to a USB drive or SD card."""
    image_path = request.json.get("image_path", "")
    target_device = request.json.get("target_device", "")
    block_size = request.json.get("block_size", "4M")

    if not image_path or not Path(image_path).is_file():
        return jsonify({"error": "Image file not found"}), 400
    if not target_device or not target_device.startswith("/dev/"):
        return jsonify({"error": "Invalid target device"}), 400

    # Safety: verify target is a removable disk via lsblk
    try:
        check = subprocess.run(
            ["lsblk", "-no", "RM,TYPE", target_device],
            capture_output=True, text=True, timeout=5,
        )
        fields = check.stdout.strip().split()
        if len(fields) < 2 or fields[1] != "disk":
            return jsonify({"error": f"{target_device} is not a whole disk"}), 400
    except Exception:
        pass

    def _run(task: Task):
        import hashlib

        p = Path(image_path)
        task.emit(f"Source image: {image_path}")
        task.emit(f"Image size: {p.stat().st_size / (1024*1024):.1f} MB")
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        task.emit(f"SHA256: {h}")
        task.emit(f"Target device: {target_device}")
        task.emit("")

        # Unmount any mounted partitions on the target
        task.emit("Unmounting target device partitions...")
        try:
            lsblk = subprocess.run(
                ["lsblk", "-ln", "-o", "NAME,MOUNTPOINT", target_device],
                capture_output=True, text=True, timeout=5,
            )
            for line in lsblk.stdout.strip().splitlines():
                parts = line.split()
                if len(parts) >= 2 and parts[1]:
                    task.run_shell(["umount", f"/dev/{parts[0]}"], sudo=True)
        except Exception:
            pass

        task.emit("")
        task.emit("Writing image to device (this may take a while)...", "warn")
        rc = task.run_shell([
            "dd",
            f"if={image_path}",
            f"of={target_device}",
            f"bs={block_size}",
            "status=progress",
            "conv=fsync",
        ], sudo=True)

        if rc == 0:
            task.emit("")
            task.emit("Syncing buffers...")
            task.run_shell(["sync"])
            task.emit("")
            task.emit("Bootable device created!", "success")
            task.emit(f"You can now safely remove {target_device}.")
        else:
            task.emit("Failed to write image to device.", "error")
        task.done(rc == 0)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@app.route("/api/pxe/start", methods=["POST"])
def api_pxe_start():
    """Start a PXE boot server using dnsmasq for TFTP + DHCP proxy."""
    image_path = request.json.get("image_path", "")
    interface = request.json.get("interface", "")
    server_ip = request.json.get("server_ip", "")
    dhcp_range = request.json.get("dhcp_range", "")
    mode = request.json.get("mode", "proxy")

    if not interface:
        return jsonify({"error": "No network interface specified"}), 400

    def _run(task: Task):
        import re as _re

        if not cmd_exists("dnsmasq"):
            task.emit("dnsmasq is not installed.", "error")
            task.emit("Install with: sudo apt install dnsmasq", "cmd")
            task.done(False)
            return

        tftp_root = Path.home() / ".osmosis" / "pxe" / "tftpboot"
        tftp_root.mkdir(parents=True, exist_ok=True)
        task.emit(f"TFTP root: {tftp_root}")

        # Detect server IP if not provided
        actual_ip = server_ip
        if not actual_ip:
            try:
                r = subprocess.run(
                    ["ip", "-4", "addr", "show", interface],
                    capture_output=True, text=True, timeout=5,
                )
                m = _re.search(r'inet (\d+\.\d+\.\d+\.\d+)/', r.stdout)
                if m:
                    actual_ip = m.group(1)
            except Exception:
                pass
        if not actual_ip:
            task.emit(f"Could not detect IP on {interface}. Provide a server IP.", "error")
            task.done(False)
            return

        task.emit(f"Server IP: {actual_ip}")
        task.emit(f"Interface: {interface}")
        task.emit(f"Mode: {mode}")
        task.emit("")

        # Copy PXE bootloader files
        pxelinux_path = None
        for candidate in [
            "/usr/lib/PXELINUX/pxelinux.0",
            "/usr/share/syslinux/pxelinux.0",
            "/usr/lib/syslinux/pxelinux.0",
        ]:
            if Path(candidate).exists():
                pxelinux_path = candidate
                break

        syslinux_modules = None
        for candidate in [
            "/usr/lib/syslinux/modules/bios",
            "/usr/share/syslinux",
            "/usr/lib/syslinux",
        ]:
            if Path(candidate).exists():
                syslinux_modules = candidate
                break

        if pxelinux_path:
            import shutil as _shutil
            task.emit(f"PXE bootloader: {pxelinux_path}")
            _shutil.copy2(pxelinux_path, str(tftp_root / "pxelinux.0"))
            if syslinux_modules:
                for mod in ["ldlinux.c32", "menu.c32", "libutil.c32", "libcom32.c32"]:
                    mod_path = Path(syslinux_modules) / mod
                    if mod_path.exists():
                        _shutil.copy2(str(mod_path), str(tftp_root / mod))
        else:
            task.emit("pxelinux.0 not found. Install syslinux/pxelinux:", "warn")
            task.emit("  sudo apt install pxelinux syslinux-common", "cmd")
            task.emit("")

        # Copy image to TFTP root if provided
        if image_path and Path(image_path).is_file():
            import shutil as _shutil
            img_name = Path(image_path).name
            dest = tftp_root / img_name
            if not dest.exists():
                task.emit(f"Copying image to TFTP root: {img_name}")
                _shutil.copy2(image_path, str(dest))
            task.emit(f"Image available: {dest}", "success")

        # Create PXE menu config
        pxecfg_dir = tftp_root / "pxelinux.cfg"
        pxecfg_dir.mkdir(exist_ok=True)
        default_cfg = pxecfg_dir / "default"

        menu = "DEFAULT menu.c32\nPROMPT 0\nMENU TITLE Osmosis PXE Boot\nTIMEOUT 300\n\n"
        kernels = list(tftp_root.glob("vmlinuz*")) + list(tftp_root.glob("linux*"))
        initrds = list(tftp_root.glob("initr*"))

        if kernels and initrds:
            menu += (f"LABEL install\n  MENU LABEL Boot installer\n"
                     f"  KERNEL {kernels[0].name}\n  APPEND initrd={initrds[0].name}\n\n")
        elif image_path and Path(image_path).suffix.lower() in (".iso", ".img"):
            img_name = Path(image_path).name
            menu += (f"LABEL image\n  MENU LABEL Boot {img_name}\n"
                     f"  KERNEL memdisk\n  APPEND initrd={img_name} iso raw\n\n")

        menu += "LABEL local\n  MENU LABEL Boot from local disk\n  LOCALBOOT 0\n"
        default_cfg.write_text(menu)
        task.emit("PXE menu config written.", "success")
        task.emit("")

        # Build dnsmasq config
        dnsmasq_conf = Path.home() / ".osmosis" / "pxe" / "dnsmasq-pxe.conf"
        conf_lines = [
            f"interface={interface}",
            "bind-interfaces",
            "enable-tftp",
            f"tftp-root={tftp_root}",
            "log-dhcp",
        ]

        if mode == "proxy":
            conf_lines.extend([
                f"dhcp-range={actual_ip},proxy",
                f"pxe-service=x86PC,\"Osmosis PXE\",pxelinux",
            ])
            task.emit("DHCP proxy mode (alongside existing DHCP server)", "info")
        else:
            if dhcp_range:
                conf_lines.append(f"dhcp-range={dhcp_range}")
            else:
                parts = actual_ip.split(".")
                parts[-1] = "100"
                range_start = ".".join(parts)
                parts[-1] = "200"
                range_end = ".".join(parts)
                conf_lines.append(f"dhcp-range={range_start},{range_end},12h")
            conf_lines.append(f"dhcp-boot=pxelinux.0,osmosis,{actual_ip}")
            task.emit("Standalone DHCP + TFTP server", "info")

        dnsmasq_conf.write_text("\n".join(conf_lines) + "\n")
        task.emit(f"Config: {dnsmasq_conf}")
        task.emit("")

        task.emit("Starting PXE server (Ctrl+C or Stop to terminate)...", "warn")
        rc = task.run_shell(["dnsmasq", "--no-daemon", "-C", str(dnsmasq_conf)], sudo=True)
        task.emit("PXE server stopped.", "info")
        task.done(rc == 0)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})


@app.route("/api/pxe/stop", methods=["POST"])
def api_pxe_stop():
    """Stop the PXE server."""
    try:
        subprocess.run(
            ["pkill", "-f", "dnsmasq.*dnsmasq-pxe.conf"],
            capture_output=True, text=True, timeout=5,
        )
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/interfaces")
def api_interfaces():
    """List network interfaces for PXE setup."""
    interfaces = []
    try:
        r = subprocess.run(
            ["ip", "-j", "link", "show"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            data = json.loads(r.stdout)
            for iface in data:
                name = iface.get("ifname", "")
                if name == "lo":
                    continue
                interfaces.append({
                    "name": name,
                    "state": iface.get("operstate", "UNKNOWN"),
                })
    except Exception:
        pass
    return jsonify(interfaces)


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
    print(f"\n  Osmosis Web UI: http://localhost:{port}\n")
    webbrowser.open(f"http://localhost:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)
