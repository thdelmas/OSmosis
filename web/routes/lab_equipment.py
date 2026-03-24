"""Lab equipment routes — SCPI instrument discovery and option unlock.

Supports Rigol oscilloscope bandwidth unlock and Siglent option management
via SCPI (Standard Commands for Programmable Instruments) over USB-TMC
or TCP/IP (port 5555).
"""

from pathlib import Path

from flask import Blueprint, jsonify, request

bp = Blueprint("lab_equipment", __name__)

# Known instrument USB VID:PID pairs
_INSTRUMENT_DEVICES = {
    ("1ab1", ""): "Rigol",
    ("f4ec", ""): "Siglent",
    ("0957", ""): "Keysight/Agilent",
    ("0699", ""): "Tektronix",
}


def _find_usbtmc_devices() -> list[dict]:
    """Find USB-TMC (Test & Measurement Class) devices."""
    devices = []
    usbtmc_path = Path("/sys/class/usbtmc")
    if not usbtmc_path.exists():
        return devices

    for entry in sorted(usbtmc_path.iterdir()):
        dev_path = f"/dev/{entry.name}"
        vid = ""
        pid = ""
        # Walk to USB device for VID/PID
        device = entry / "device"
        if device.exists():
            usb_dir = device.resolve()
            for _ in range(6):
                parent = usb_dir.parent
                id_vendor = parent / "idVendor"
                if id_vendor.exists():
                    vid = id_vendor.read_text().strip()
                    pid_file = parent / "idProduct"
                    pid = pid_file.read_text().strip() if pid_file.exists() else ""
                    break
                usb_dir = parent

        brand = "Unknown"
        for (v, _), b in _INSTRUMENT_DEVICES.items():
            if v == vid.lower():
                brand = b
                break

        devices.append({"device": dev_path, "vid": vid, "pid": pid, "brand": brand})

    return devices


def _scpi_query(target: str, command: str, timeout: int = 5) -> str | None:
    """Send a SCPI command and read the response.

    target can be a /dev/usbtmcN path or a host:port string.
    """
    if target.startswith("/dev/"):
        try:
            with open(target, "w") as f:
                f.write(command + "\n")
            with open(target) as f:
                return f.read().strip()
        except OSError:
            return None
    else:
        # TCP/IP SCPI (e.g. 192.168.1.100:5555)
        import socket

        try:
            host, port = target.rsplit(":", 1)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, int(port)))
            sock.sendall((command + "\n").encode())
            resp = sock.recv(4096).decode().strip()
            sock.close()
            return resp
        except (OSError, ValueError):
            return None


@bp.route("/api/lab/detect")
def api_lab_detect():
    """Detect connected lab instruments via USB-TMC."""
    devices = _find_usbtmc_devices()

    # Try to identify each device
    results = []
    for dev in devices:
        idn = _scpi_query(dev["device"], "*IDN?")
        results.append(
            {
                **dev,
                "idn": idn,
                "identified": idn is not None,
            }
        )

    if not results:
        return (
            jsonify(
                {
                    "error": "no_device",
                    "hint": "No USB-TMC instrument detected. Connect your oscilloscope/generator via USB.",
                }
            ),
            404,
        )

    return jsonify({"devices": results})


@bp.route("/api/lab/query", methods=["POST"])
def api_lab_query():
    """Send a SCPI command to an instrument.

    JSON body: { "target": "/dev/usbtmc0", "command": "*IDN?" }
    """
    body = request.json or {}
    target = body.get("target", "").strip()
    command = body.get("command", "").strip()

    if not target or not command:
        return jsonify({"error": "target and command are required"}), 400

    response = _scpi_query(target, command)
    if response is None:
        return jsonify({"error": "No response from instrument"}), 502

    return jsonify({"target": target, "command": command, "response": response})


@bp.route("/api/lab/rigol/info")
def api_rigol_info():
    """Get Rigol oscilloscope info and current option status.

    Query params:
        target: /dev/usbtmc0 or IP:port
    """
    target = request.args.get("target", "").strip()
    if not target:
        return jsonify({"error": "No target specified"}), 400

    idn = _scpi_query(target, "*IDN?")
    if not idn:
        return jsonify({"error": "Could not communicate with instrument"}), 502

    # Parse IDN: Rigol Technologies,DS1054Z,DS1ZA1234567890,00.04.04.SP4
    parts = idn.split(",")
    info = {
        "idn": idn,
        "manufacturer": parts[0].strip() if len(parts) > 0 else "",
        "model": parts[1].strip() if len(parts) > 1 else "",
        "serial": parts[2].strip() if len(parts) > 2 else "",
        "firmware": parts[3].strip() if len(parts) > 3 else "",
    }

    # Check installed options
    opts = _scpi_query(target, "*OPT?")
    info["options"] = opts or ""

    return jsonify(info)
