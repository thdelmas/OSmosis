"""Shared helpers, config, and the Task class used across all route modules."""

import json
import queue
import shutil
import subprocess
import threading
import uuid
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = SCRIPT_DIR / "devices.cfg"
MCU_CONFIG_FILE = SCRIPT_DIR / "microcontrollers.cfg"
LOG_DIR = Path.home() / ".osmosis" / "logs"
BACKUP_DIR = Path.home() / ".osmosis" / "backups"
IPFS_INDEX = Path.home() / ".osmosis" / "ipfs-index.json"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# In-memory task store: task_id -> Task
tasks: dict = {}


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
        devices.append(
            {
                "id": parts[0],
                "label": parts[1],
                "model": parts[2],
                "codename": parts[3],
                "rom_url": parts[4],
                "twrp_url": parts[5],
                "eos_url": parts[6],
                "stock_url": parts[7],
                "gapps_url": parts[8] if len(parts) > 8 else "",
            }
        )
    return devices


def parse_microcontrollers_cfg() -> list[dict]:
    """Parse microcontrollers.cfg and return list of microcontroller board dicts.

    Fields per line (pipe-delimited):
        id|label|brand|arch|flash_tool|flash_args|bootloader|usb_vid|usb_pid|notes
    """
    boards = []
    if not MCU_CONFIG_FILE.exists():
        return boards
    for line in MCU_CONFIG_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|")
        if len(parts) < 9:
            continue
        boards.append(
            {
                "id": parts[0],
                "label": parts[1],
                "brand": parts[2],
                "arch": parts[3],
                "flash_tool": parts[4],
                "flash_args": parts[5],
                "bootloader": parts[6],
                "usb_vid": parts[7],
                "usb_pid": parts[8],
                "notes": parts[9] if len(parts) > 9 else "",
            }
        )
    return boards


# Fallback table: model number -> common name
_MODEL_NAMES: dict[str, str] = {
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
    "GT-N7000": "Galaxy Note",
    "GT-N7100": "Galaxy Note II",
    "SM-N9005": "Galaxy Note 3",
    "SM-N910F": "Galaxy Note 4",
    "SM-N920C": "Galaxy Note 5",
    "SM-A520F": "Galaxy A5 (2017)",
    "SM-A750F": "Galaxy A7 (2018)",
    "SM-J530F": "Galaxy J5 (2017)",
    "SM-T210": "Galaxy Tab 3 7.0",
    "SM-T530": "Galaxy Tab 4 10.1",
    "Nexus 4": "Nexus 4",
    "Nexus 5": "Nexus 5",
    "Nexus 5X": "Nexus 5X",
    "Nexus 6P": "Nexus 6P",
    "Pixel": "Pixel",
    "Pixel XL": "Pixel XL",
    "Pixel 2": "Pixel 2",
    "Pixel 3a": "Pixel 3a",
    "FP2": "Fairphone 2",
    "FP3": "Fairphone 3",
    "FP4": "Fairphone 4",
    "FP5": "Fairphone 5",
}


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
