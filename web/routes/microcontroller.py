"""Microcontroller detection, board lookup, and flashing routes.

Supports Arduino, ESP32/ESP8266, Raspberry Pi Pico, STM32, Teensy, and
other popular microcontroller boards.  Detection works via USB VID/PID
matching and serial port enumeration.  Flashing delegates to the
appropriate tool (arduino-cli, esptool, picotool, st-flash, etc.).
"""

from pathlib import Path

from flask import Blueprint, jsonify, request

from web.core import Task, cmd_exists, parse_microcontrollers_cfg, start_task
from web.registry import register

bp = Blueprint("microcontroller", __name__)

# Known USB VID -> brand mapping for microcontroller vendors
_MCU_USB_VENDORS: dict[str, str] = {
    "2341": "Arduino",
    "2a03": "Arduino (clone)",
    "1a86": "CH340 (clone/Wemos)",
    "10c4": "CP2102 (Espressif/SparkFun)",
    "0403": "FTDI (Arduino Nano/clone)",
    "303a": "Espressif",
    "2e8a": "Raspberry Pi",
    "0483": "STMicroelectronics",
    "16c0": "PJRC (Teensy)",
    "239a": "Adafruit",
    "2886": "Seeed Studio",
    "0d28": "ARM mbed (micro:bit)",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _list_serial_ports() -> list[dict]:
    """Enumerate serial ports and return info about each.

    Uses /sys/class/tty and udevadm to get USB VID/PID without pyserial.
    """
    ports = []
    tty_path = Path("/sys/class/tty")
    if not tty_path.exists():
        return ports

    for entry in sorted(tty_path.iterdir()):
        device_path = entry / "device"
        if not device_path.exists():
            continue

        # Only include USB-backed serial ports
        real = str(device_path.resolve())
        if "usb" not in real.lower():
            continue

        port_name = f"/dev/{entry.name}"
        vid = ""
        pid = ""
        manufacturer = ""
        product = ""

        # Walk up to find USB device attributes
        usb_dir = device_path.resolve()
        for _ in range(6):
            parent = usb_dir.parent
            id_vendor = parent / "idVendor"
            if id_vendor.exists():
                vid = id_vendor.read_text().strip()
                pid_file = parent / "idProduct"
                pid = pid_file.read_text().strip() if pid_file.exists() else ""
                mfr_file = parent / "manufacturer"
                manufacturer = mfr_file.read_text().strip() if mfr_file.exists() else ""
                prod_file = parent / "product"
                product = prod_file.read_text().strip() if prod_file.exists() else ""
                break
            usb_dir = parent

        brand = _MCU_USB_VENDORS.get(vid.lower(), manufacturer or "Unknown")

        ports.append(
            {
                "port": port_name,
                "vid": vid,
                "pid": pid,
                "manufacturer": manufacturer,
                "product": product,
                "brand": brand,
            }
        )

    return ports


def _match_board(vid: str, pid: str) -> dict | None:
    """Try to match a USB VID/PID to a known microcontroller board."""
    vid_low = vid.lower()
    pid_low = pid.lower()
    for board in parse_microcontrollers_cfg():
        if board["usb_vid"].lower() == vid_low and board["usb_pid"].lower() == pid_low:
            return board
    # Fallback: match by VID only and return first hit
    for board in parse_microcontrollers_cfg():
        if board["usb_vid"].lower() == vid_low:
            return board
    return None


def _detect_uf2_drives() -> list[dict]:
    """Detect UF2 bootloader drives (Pico, Adafruit, etc.) mounted as mass storage."""
    drives = []
    try:
        mounts = Path("/proc/mounts").read_text()
        for line in mounts.splitlines():
            parts = line.split()
            if len(parts) < 2:
                continue
            mount_point = parts[1]
            info_file = Path(mount_point) / "INFO_UF2.TXT"
            if info_file.exists():
                info = info_file.read_text()
                model = ""
                board_id = ""
                for info_line in info.splitlines():
                    if info_line.startswith("Model:"):
                        model = info_line.split(":", 1)[1].strip()
                    elif info_line.startswith("Board-ID:"):
                        board_id = info_line.split(":", 1)[1].strip()
                drives.append(
                    {
                        "mount": mount_point,
                        "model": model,
                        "board_id": board_id,
                        "type": "uf2",
                    }
                )
    except Exception:
        pass
    return drives


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@bp.route("/api/microcontrollers")
def api_microcontrollers():
    """Return all microcontroller board presets."""
    return jsonify(parse_microcontrollers_cfg())


@bp.route("/api/microcontrollers/search")
def api_microcontrollers_search():
    """Search microcontroller boards by brand, name, or architecture."""
    brand = request.args.get("brand", "").lower().strip()
    query = request.args.get("q", "").lower().strip()
    arch = request.args.get("arch", "").lower().strip()

    if not any([brand, query, arch]):
        return jsonify(parse_microcontrollers_cfg())

    results = []
    for board in parse_microcontrollers_cfg():
        score = 0
        haystack = f"{board['label']} {board['brand']} {board['arch']} {board['notes']} {board['id']}".lower()

        if brand and brand in board["brand"].lower():
            score += 3
        if arch and arch == board["arch"].lower():
            score += 2
        if query:
            if query in board["label"].lower():
                score += 5
            elif query in board["id"].lower():
                score += 4
            elif query in haystack:
                score += 1

        if score > 0 or not any([brand, query, arch]):
            results.append({**board, "_score": score})

    results.sort(key=lambda b: b["_score"], reverse=True)
    for r in results:
        r.pop("_score", None)

    return jsonify(results[:30])


@bp.route("/api/microcontrollers/detect")
def api_microcontrollers_detect():
    """Detect connected microcontroller boards via USB serial ports and UF2 drives."""
    serial_ports = _list_serial_ports()
    uf2_drives = _detect_uf2_drives()

    detected = []

    for port in serial_ports:
        match = _match_board(port["vid"], port["pid"])
        detected.append(
            {
                "port": port["port"],
                "vid": port["vid"],
                "pid": port["pid"],
                "brand": port["brand"],
                "product": port["product"],
                "match": match,
                "type": "serial",
            }
        )

    for drive in uf2_drives:
        detected.append(
            {
                "mount": drive["mount"],
                "model": drive["model"],
                "board_id": drive["board_id"],
                "type": "uf2",
                "match": None,
            }
        )

    if not detected:
        return jsonify({"error": "no_device", "serial_ports": [], "uf2_drives": []}), 404

    return jsonify({"devices": detected})


@bp.route("/api/microcontrollers/tools")
def api_microcontrollers_tools():
    """Check which microcontroller flashing tools are installed."""
    return jsonify(
        {
            "arduino_cli": cmd_exists("arduino-cli"),
            "esptool": cmd_exists("esptool") or cmd_exists("esptool.py"),
            "picotool": cmd_exists("picotool"),
            "stflash": cmd_exists("st-flash"),
            "openocd": cmd_exists("openocd"),
            "avrdude": cmd_exists("avrdude"),
            "dfu_util": cmd_exists("dfu-util"),
            "teensy_loader": cmd_exists("teensy_loader_cli"),
        }
    )


@bp.route("/api/microcontrollers/flash", methods=["POST"])
def api_microcontrollers_flash():
    """Flash firmware to a microcontroller board.

    Expected JSON body:
        {
            "board_id":  "<preset id from microcontrollers.cfg>",
            "fw_path":   "<absolute path to firmware file (.bin/.hex/.uf2/.ino)>",
            "port":      "<serial port, e.g. /dev/ttyUSB0>",
            "uf2_mount": "<UF2 drive mount point, if applicable>"
        }
    """
    body = request.json or {}
    board_id = body.get("board_id", "").strip()
    fw_path = body.get("fw_path", "").strip()
    port = body.get("port", "").strip()
    uf2_mount = body.get("uf2_mount", "").strip()

    if not fw_path or not Path(fw_path).is_file():
        return jsonify({"error": "Firmware file not found"}), 400

    board = None
    if board_id:
        board = next((b for b in parse_microcontrollers_cfg() if b["id"] == board_id), None)

    if not board:
        return jsonify({"error": f"Board preset '{board_id}' not found"}), 404

    tool = board["flash_tool"]

    # Validate that the required tool is installed
    tool_cmd = tool.replace("_", "-")
    if tool == "esptool" and not cmd_exists("esptool"):
        tool_cmd = "esptool.py"
    if not cmd_exists(tool_cmd):
        return jsonify({"error": f"Flash tool '{tool_cmd}' is not installed"}), 500

    def _run(task: Task):
        import hashlib

        fw = Path(fw_path)
        h = hashlib.sha256(fw.read_bytes()).hexdigest()

        task.emit(f"Board: {board['label']} ({board['id']})", "info")
        task.emit(f"Architecture: {board['arch']}", "info")
        task.emit(f"Firmware: {fw_path}", "info")
        task.emit(f"SHA256: {h}")
        if port:
            task.emit(f"Port: {port}", "info")

        rc = 1

        if tool == "arduino-cli":
            cmd = ["arduino-cli", "upload", "-i", fw_path]
            # Parse flash_args for --fqbn
            if board["flash_args"]:
                cmd.extend(board["flash_args"].split())
            if port:
                cmd.extend(["-p", port])
            task.emit("Uploading via arduino-cli...", "info")
            rc = task.run_shell(cmd)

        elif tool == "esptool":
            esptool_cmd = "esptool" if cmd_exists("esptool") else "esptool.py"
            cmd = [esptool_cmd]
            if port:
                cmd.extend(["--port", port])
            # Parse flash_args for --chip
            if board["flash_args"]:
                cmd.extend(board["flash_args"].split())
            cmd.extend(["write_flash", "0x0", fw_path])
            task.emit("Flashing via esptool...", "info")
            rc = task.run_shell(cmd)

        elif tool == "picotool":
            if uf2_mount and fw_path.endswith(".uf2"):
                # UF2 drag-and-drop style
                import shutil

                task.emit(f"Copying UF2 firmware to {uf2_mount}...", "info")
                try:
                    shutil.copy2(fw_path, uf2_mount)
                    task.emit("UF2 firmware copied. Board will reboot automatically.", "success")
                    rc = 0
                except Exception as e:
                    task.emit(f"Copy failed: {e}", "error")
                    rc = 1
            else:
                cmd = ["picotool", "load", fw_path, "-f"]
                task.emit("Flashing via picotool...", "info")
                rc = task.run_shell(cmd)

        elif tool == "stflash":
            # Parse flash_args, replacing {{fw}} placeholder
            args = board["flash_args"].replace("{{fw}}", fw_path)
            cmd = ["st-flash"] + args.split()
            task.emit("Flashing via st-flash...", "info")
            rc = task.run_shell(cmd)

        elif tool == "teensy_loader_cli":
            cmd = ["teensy_loader_cli"]
            if board["flash_args"]:
                cmd.extend(board["flash_args"].split())
            cmd.extend(["-w", fw_path])
            task.emit("Flashing via teensy_loader_cli...", "info")
            rc = task.run_shell(cmd)

        elif tool == "dfu-util":
            cmd = ["dfu-util"]
            if board["flash_args"]:
                cmd.extend(board["flash_args"].split())
            cmd.extend(["-D", fw_path])
            task.emit("Flashing via dfu-util...", "info")
            rc = task.run_shell(cmd)

        elif tool == "avrdude":
            cmd = ["avrdude"]
            if board["flash_args"]:
                cmd.extend(board["flash_args"].split())
            if port:
                cmd.extend(["-P", port])
            cmd.extend(["-U", f"flash:w:{fw_path}:i"])
            task.emit("Flashing via avrdude...", "info")
            rc = task.run_shell(cmd)

        else:
            task.emit(f"Unknown flash tool: {tool}", "error")
            task.done(False)
            return

        if rc == 0:
            task.emit("Flash complete!", "success")
            register(
                fw_path,
                device_id=board_id,
                device_label=board["label"],
                component="firmware",
                flash_method=tool,
                port=port or "",
                sha256=h,
            )
        task.done(rc == 0)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})
