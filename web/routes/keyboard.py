"""Keyboard firmware routes — QMK/ZMK/VIA detection and flashing.

Detects connected keyboards in bootloader mode (DFU, UF2, or Cataract),
identifies the MCU, and flashes QMK or ZMK firmware.
"""

import subprocess
from pathlib import Path

from flask import Blueprint, jsonify, request

from web.core import Task, cmd_exists, start_task
from web.registry import register

bp = Blueprint("keyboard", __name__)

# Known keyboard bootloader USB VID:PID pairs
_KEYBOARD_BOOTLOADERS = {
    # STM32 DFU
    ("0483", "df11"): {
        "mcu": "STM32",
        "method": "dfu-util",
        "desc": "STM32 DFU bootloader",
    },
    # ATmega32u4 (Caterina bootloader — Arduino Pro Micro)
    ("2341", "0036"): {
        "mcu": "ATmega32u4",
        "method": "avrdude",
        "desc": "Caterina bootloader (Pro Micro)",
    },
    ("1b4f", "9205"): {
        "mcu": "ATmega32u4",
        "method": "avrdude",
        "desc": "SparkFun Pro Micro",
    },
    ("1b4f", "9206"): {
        "mcu": "ATmega32u4",
        "method": "avrdude",
        "desc": "SparkFun Pro Micro",
    },
    # ATmega32u4 (DFU — Atmel DFU)
    ("03eb", "2ff4"): {
        "mcu": "ATmega32u4",
        "method": "dfu-programmer",
        "desc": "Atmel DFU bootloader",
    },
    # RP2040 (UF2)
    ("2e8a", "0003"): {
        "mcu": "RP2040",
        "method": "uf2",
        "desc": "RP2040 UF2 bootloader",
    },
    # nRF52 (Adafruit bootloader — ZMK)
    ("239a", "0029"): {
        "mcu": "nRF52840",
        "method": "uf2",
        "desc": "nRF52 UF2 bootloader (ZMK)",
    },
    # QMK DFU (generic)
    ("feed", "6060"): {
        "mcu": "ATmega32u4",
        "method": "dfu-programmer",
        "desc": "QMK DFU bootloader",
    },
}


def _detect_keyboard_bootloader() -> list[dict]:
    """Detect keyboards in bootloader mode via lsusb."""
    devices = []
    try:
        result = subprocess.run(
            ["lsusb"], capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.strip().splitlines():
            for (vid, pid), info in _KEYBOARD_BOOTLOADERS.items():
                if f"{vid}:{pid}" in line.lower():
                    devices.append(
                        {
                            "vid": vid,
                            "pid": pid,
                            **info,
                            "raw": line.strip(),
                        }
                    )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return devices


@bp.route("/api/keyboard/detect")
def api_keyboard_detect():
    """Detect keyboards in bootloader mode."""
    devices = _detect_keyboard_bootloader()
    if not devices:
        return (
            jsonify(
                {
                    "error": "no_device",
                    "hint": "No keyboard in bootloader mode detected. "
                    "Put your keyboard into bootloader mode first:\n"
                    "- QMK: hold the RESET button or press the key combo\n"
                    "- ZMK: double-tap the reset button\n"
                    "- Pro Micro: short RST to GND twice quickly",
                }
            ),
            404,
        )
    return jsonify({"devices": devices})


@bp.route("/api/keyboard/tools")
def api_keyboard_tools():
    """Check which keyboard flashing tools are installed."""
    return jsonify(
        {
            "qmk": cmd_exists("qmk"),
            "dfu_util": cmd_exists("dfu-util"),
            "dfu_programmer": cmd_exists("dfu-programmer"),
            "avrdude": cmd_exists("avrdude"),
            "picotool": cmd_exists("picotool"),
        }
    )


@bp.route("/api/keyboard/flash", methods=["POST"])
def api_keyboard_flash():
    """Flash keyboard firmware.

    JSON body: {
        "fw_path": "/path/to/firmware.hex",
        "method": "dfu-util",   // dfu-util, dfu-programmer, avrdude, uf2
        "mcu": "STM32"          // optional, for avrdude -p flag
    }
    """
    body = request.json or {}
    fw_path = body.get("fw_path", "").strip()
    method = body.get("method", "").strip()
    mcu = body.get("mcu", "").strip()

    if not fw_path or not Path(fw_path).is_file():
        return jsonify({"error": "Firmware file not found"}), 400
    if not method:
        return jsonify({"error": "Flash method not specified"}), 400

    def _run(task: Task):
        import hashlib

        fw = Path(fw_path)
        h = hashlib.sha256(fw.read_bytes()).hexdigest()

        task.emit(f"Firmware: {fw_path}", "info")
        task.emit(f"Method: {method}", "info")
        task.emit(f"SHA256: {h}", "info")

        rc = 1

        if method == "dfu-util":
            if not cmd_exists("dfu-util"):
                task.emit("dfu-util is not installed.", "error")
                task.done(False)
                return
            cmd = ["dfu-util", "-D", fw_path, "-a", "0"]
            task.emit("Flashing via dfu-util...", "info")
            rc = task.run_shell(cmd)

        elif method == "dfu-programmer":
            if not cmd_exists("dfu-programmer"):
                task.emit("dfu-programmer is not installed.", "error")
                task.done(False)
                return
            mcu_type = mcu or "atmega32u4"
            task.emit(f"Erasing {mcu_type}...", "info")
            task.run_shell(["dfu-programmer", mcu_type, "erase", "--force"])
            task.emit("Flashing...", "info")
            rc = task.run_shell(["dfu-programmer", mcu_type, "flash", fw_path])
            if rc == 0:
                task.run_shell(["dfu-programmer", mcu_type, "reset"])

        elif method == "avrdude":
            if not cmd_exists("avrdude"):
                task.emit("avrdude is not installed.", "error")
                task.done(False)
                return
            mcu_type = mcu or "atmega32u4"
            cmd = [
                "avrdude",
                "-p",
                mcu_type,
                "-c",
                "avr109",
                "-U",
                f"flash:w:{fw_path}:i",
            ]
            task.emit("Flashing via avrdude...", "info")
            rc = task.run_shell(cmd)

        elif method == "uf2":
            # Find UF2 drive
            import shutil

            uf2_mount = None
            try:
                mounts = Path("/proc/mounts").read_text()
                for line in mounts.splitlines():
                    parts = line.split()
                    if len(parts) >= 2:
                        info_file = Path(parts[1]) / "INFO_UF2.TXT"
                        if info_file.exists():
                            uf2_mount = parts[1]
                            break
            except OSError:
                pass

            if not uf2_mount:
                task.emit(
                    "No UF2 drive found. Is the keyboard in bootloader mode?",
                    "error",
                )
                task.done(False)
                return

            task.emit(f"Copying firmware to UF2 drive ({uf2_mount})...", "info")
            try:
                shutil.copy2(fw_path, uf2_mount)
                task.emit("Firmware copied. Keyboard will reboot.", "success")
                rc = 0
            except OSError as e:
                task.emit(f"Copy failed: {e}", "error")
                rc = 1

        else:
            task.emit(f"Unknown flash method: {method}", "error")
            task.done(False)
            return

        if rc == 0:
            task.emit("Keyboard firmware flashed successfully!", "success")
            register(
                fw_path,
                device_id="keyboard",
                device_label="Keyboard",
                component="firmware",
                flash_method=method,
                sha256=h,
            )
        else:
            task.emit("Flash failed. Check the log above.", "error")

        task.done(rc == 0)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})
