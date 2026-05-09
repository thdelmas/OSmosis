"""Shared helpers, config, and the Task class used across all route modules."""

import json
import os
import queue
import shutil
import subprocess
import threading
import time
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


def tool_path() -> str:
    """Return PATH extended with ~/.local/bin (where setup-ipfs.sh installs kubo)."""
    local_bin = str(Path.home() / ".local" / "bin")
    system_path = os.environ.get("PATH", "")
    if local_bin not in system_path:
        return f"{local_bin}:{system_path}"
    return system_path


def tool_env() -> dict:
    """Return a copy of os.environ with the extended PATH."""
    return dict(os.environ, PATH=tool_path())


def cmd_exists(cmd: str) -> bool:
    return shutil.which(cmd, path=tool_path()) is not None


DEVICES_YAML = SCRIPT_DIR / "devices.yaml"
SCOOTERS_YAML = SCRIPT_DIR / "scooters.yaml"
EBIKES_YAML = SCRIPT_DIR / "ebikes.yaml"
MCU_YAML = SCRIPT_DIR / "microcontrollers.yaml"


def _load_yaml(path: Path) -> list[dict]:
    """Load a YAML config file if it exists. Returns [] on failure."""
    if not path.exists():
        return []
    try:
        import yaml

        data = yaml.safe_load(path.read_text())
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "devices" in data:
            return data["devices"]
    except Exception:
        pass
    return []


def _device_profile_to_legacy(p) -> dict:
    """Map a DeviceProfile (phone/tablet) onto the legacy parse_devices_cfg dict."""
    rom_url = ""
    twrp_url = ""
    eos_url = ""
    stock_url = ""
    gapps_url = ""
    for fw in p.firmware:
        if fw.id in ("lineageos", "replicant", "lethe") and not rom_url:
            rom_url = fw.url
        elif fw.id == "twrp" and not twrp_url:
            twrp_url = fw.url
        elif fw.id == "eos" and not eos_url:
            eos_url = fw.url
        elif fw.id == "stock" and not stock_url:
            stock_url = fw.url
        elif fw.id == "gapps" and not gapps_url:
            gapps_url = fw.url
    return {
        "id": p.id,
        "label": p.name,
        "model": p.model,
        "codename": p.codename,
        "rom_url": rom_url,
        "twrp_url": twrp_url,
        "eos_url": eos_url,
        "stock_url": stock_url,
        "gapps_url": gapps_url,
    }


def parse_devices_cfg() -> list[dict]:
    """Return device presets. Order of precedence:
        1. profiles/*.yaml  (one-file-per-device, declarative — preferred)
        2. devices.yaml     (legacy single-file YAML)
        3. devices.cfg      (legacy pipe-delimited)
    """
    devices = _load_yaml(DEVICES_YAML)
    if not devices and CONFIG_FILE.exists():
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

    # Overlay one-file-per-device profiles. Phone/tablet/laptop categories
    # all flow through this parser; T2-specific filtering happens in t2.py.
    from web.device_profile import load_all_profiles

    by_id = {row["id"]: row for row in devices}
    for prof in load_all_profiles():
        if prof.category in ("phone", "tablet"):
            by_id[prof.id] = _device_profile_to_legacy(prof)
    return list(by_id.values())


def _mcu_profile_to_legacy(p) -> dict:
    """Map a DeviceProfile (category=mcu) onto the legacy parse_microcontrollers_cfg dict."""
    flash_args = ""
    for step in p.flash_steps:
        if step.id == "flash" and step.command:
            flash_args = step.command
            break
    return {
        "id": p.id,
        "label": p.name,
        "brand": p.brand,
        "arch": p.extra.get("arch", ""),
        "flash_tool": p.flash_tool,
        "flash_args": flash_args,
        "bootloader": p.extra.get("bootloader", ""),
        "usb_vid": p.usb_vid,
        "usb_pid": p.usb_pid,
        "notes": p.notes,
    }


def parse_microcontrollers_cfg() -> list[dict]:
    """Return microcontroller presets. Order of precedence:
        1. profiles/mcu/*.yaml
        2. microcontrollers.yaml
        3. microcontrollers.cfg

    .cfg fields (pipe-delimited):
        id|label|brand|arch|flash_tool|flash_args|bootloader|usb_vid|usb_pid|notes
    """
    boards = _load_yaml(MCU_YAML)
    if not boards and MCU_CONFIG_FILE.exists():
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

    from web.device_profile import merge_legacy_with_profiles

    return merge_legacy_with_profiles(boards, "mcu", _mcu_profile_to_legacy)


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
    "GT-I8160": "Galaxy Ace 2",
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
    "M2101K9AG": "Mi 11 Lite 4G",
    "M2101K9AI": "Mi 11 Lite 4G",
    "M2101K9G": "Mi 11 Lite 5G",
    "M2101K9R": "Mi 11 Lite 5G",
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

    def progress(self, step: int, total: int, label: str, detail: str = ""):
        """Emit a structured progress message the frontend can parse.

        Emits a line like: ``[2/6] Applying overlays... (33%)``
        The ``TerminalOutput`` component picks up the ``%`` automatically.
        """
        pct = int(step / total * 100) if total else 0
        msg = f"[{step}/{total}] {label}"
        if detail:
            msg += f" — {detail}"
        msg += f" ({pct}%)"
        self.q.put(json.dumps({"level": "info", "msg": msg}))

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

    def run_shell_with_retry(
        self,
        cmd: list[str],
        *,
        max_attempts: int = 3,
        base_delay: float = 5.0,
        sudo: bool = False,
    ) -> int:
        """Run a shell command with exponential backoff between attempts.

        Emits ``__retry:{attempt}/{max}`` markers the frontend can parse, plus
        human-readable lines. Aborts immediately if the task is cancelled —
        including during the inter-attempt sleep.
        """
        for attempt in range(1, max_attempts + 1):
            if attempt > 1:
                self.emit(f"__retry:{attempt}/{max_attempts}", "warn")
                self.emit(
                    f"Retrying (attempt {attempt} of {max_attempts})...",
                    "warn",
                )
            rc = self.run_shell(cmd, sudo=sudo)
            if rc == 0 or self.cancelled:
                return rc
            if attempt >= max_attempts:
                self.emit(
                    f"Gave up after {max_attempts} attempts.",
                    "error",
                )
                return rc
            delay = base_delay * (2 ** (attempt - 1))
            self.emit(
                f"Waiting {int(delay)}s before retry. "
                f"Click Abort to give up.",
                "info",
            )
            slept = 0.0
            while slept < delay:
                if self.cancelled:
                    return 1
                time.sleep(0.5)
                slept += 0.5
        return 1

    def run_shell(self, cmd: list[str], sudo: bool = False) -> int:
        """Run a shell command, streaming output line by line."""
        if self.cancelled:
            return 1
        if sudo:
            cmd = ["sudo"] + cmd
            # Audit log for privileged operations
            try:
                from web.integrity import audit_log

                audit_log(
                    action="privileged_command",
                    command=cmd,
                    task_id=self.id,
                    result="started",
                )
            except Exception:
                pass
        self.emit(f"$ {' '.join(cmd)}", "cmd")
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=tool_env(),
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
