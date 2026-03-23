"""Dynamic device inventory — auto-detect USB, serial, BLE, and network devices.

Extends the existing ADB + USB VID detection into a unified inventory that
maps detected hardware to device profiles. Supports:

- USB devices (via lsusb)
- ADB-connected Android devices
- Serial ports (for MCUs, scooters, e-bikes)
- Network devices via mDNS/SSDP (routers, SBCs, IoT post-flash)
"""

import logging
import re
import subprocess
from dataclasses import dataclass, field

from web.core import cmd_exists
from web.device_profile import load_all_profiles

log = logging.getLogger(__name__)


@dataclass
class InventoryDevice:
    """A detected device in the inventory."""

    id: str
    name: str
    type: str  # usb, adb, serial, network
    vendor: str = ""
    model: str = ""
    serial: str = ""
    connection: str = ""  # e.g. "USB Bus 001 Device 003", "/dev/ttyUSB0", "192.168.1.50"
    profile_id: str = ""  # matched device profile, if any
    status: str = "detected"  # detected, ready, busy, error
    details: dict = field(default_factory=dict)


# USB VID -> vendor name (expanded from device.py)
_USB_VENDORS = {
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
    "1a86": "CH340 (serial)",
    "0403": "FTDI (serial)",
    "10c4": "CP210x (serial)",
    "2341": "Arduino",
    "239a": "Adafruit",
    "303a": "Espressif",
    "1d50": "OpenMoko/HackRF",
    "0483": "STMicroelectronics",
    "1fc9": "NXP",
    "2e8a": "Raspberry Pi (RP2040)",
}


def _detect_usb() -> list[InventoryDevice]:
    """Detect USB devices via lsusb."""
    devices = []
    try:
        result = subprocess.run(["lsusb"], capture_output=True, text=True, timeout=5)
        for line in result.stdout.strip().splitlines():
            # Bus 001 Device 003: ID 04e8:6860 Samsung Electronics Co., Ltd ...
            m = re.match(r"Bus (\d+) Device (\d+): ID ([0-9a-f]{4}):([0-9a-f]{4})\s+(.*)", line, re.I)
            if not m:
                continue

            bus, dev_num, vid, pid, desc = m.groups()
            vendor = _USB_VENDORS.get(vid, "")
            if not vendor:
                continue  # Skip unknown USB devices (hubs, HID, etc.)

            # Clean up description
            name = (
                re.sub(
                    r"\b(Inc\.?|Co\.?,?\s*Ltd\.?|Corp\.?|Electronics|Technology|Communication)\b",
                    "",
                    desc,
                    flags=re.IGNORECASE,
                )
                .strip()
                .strip(",")
                .strip()
            )
            if not name:
                name = vendor

            dev = InventoryDevice(
                id=f"usb-{vid}-{pid}-{bus}-{dev_num}",
                name=name,
                type="usb",
                vendor=vendor,
                connection=f"USB Bus {bus} Device {dev_num}",
                details={"vid": vid, "pid": pid, "bus": bus, "device": dev_num},
            )

            # Try to match a profile by USB VID
            for profile in load_all_profiles():
                if profile.usb_vid and profile.usb_vid.lower() == vid.lower():
                    if not profile.usb_pid or profile.usb_pid.lower() == pid.lower():
                        dev.profile_id = profile.id
                        dev.model = profile.model
                        break

            devices.append(dev)
    except Exception as e:
        log.debug("USB detection failed: %s", e)

    return devices


def _detect_adb() -> list[InventoryDevice]:
    """Detect ADB-connected Android devices."""
    if not cmd_exists("adb"):
        return []

    devices = []
    try:
        result = subprocess.run(["adb", "devices", "-l"], capture_output=True, text=True, timeout=5)
        for line in result.stdout.strip().splitlines()[1:]:
            parts = line.split()
            if len(parts) < 2:
                continue
            serial = parts[0]
            state = parts[1]
            if state not in ("device", "recovery", "sideload"):
                continue

            # Extract properties from -l output
            props = {}
            for p in parts[2:]:
                if ":" in p:
                    k, v = p.split(":", 1)
                    props[k] = v

            model = props.get("model", "")
            device_code = props.get("device", "")

            dev = InventoryDevice(
                id=f"adb-{serial}",
                name=model or serial,
                type="adb",
                vendor=props.get("brand", ""),
                model=model,
                serial=serial,
                connection=f"ADB ({state})",
                status="ready" if state == "device" else state,
                details={"state": state, "transport_id": props.get("transport_id", ""), **props},
            )

            # Match profile by codename or model
            for profile in load_all_profiles():
                if profile.codename and profile.codename.lower() == device_code.lower():
                    dev.profile_id = profile.id
                    break
                if profile.model and profile.model.lower() == model.lower():
                    dev.profile_id = profile.id
                    break

            devices.append(dev)
    except Exception as e:
        log.debug("ADB detection failed: %s", e)

    return devices


def _detect_serial() -> list[InventoryDevice]:
    """Detect serial port devices (MCUs, ST-Link, etc.)."""
    from pathlib import Path

    devices = []
    serial_dirs = ["/dev/serial/by-id", "/dev/serial/by-path"]

    # Check /dev/ttyUSB* and /dev/ttyACM*
    for pattern in ["/dev/ttyUSB*", "/dev/ttyACM*"]:
        import glob

        for port in sorted(glob.glob(pattern)):
            name = Path(port).name
            dev = InventoryDevice(
                id=f"serial-{name}",
                name=name,
                type="serial",
                connection=port,
                details={"port": port},
            )
            devices.append(dev)

    # Try to get more info from /dev/serial/by-id
    for serial_dir in serial_dirs:
        p = Path(serial_dir)
        if not p.exists():
            continue
        for link in sorted(p.iterdir()):
            if link.is_symlink():
                target = str(link.resolve())
                # Match to an existing device or create new
                matched = False
                for d in devices:
                    if d.details.get("port") == target:
                        d.name = link.name
                        d.details["by_id"] = str(link)
                        matched = True
                        break
                if not matched:
                    devices.append(
                        InventoryDevice(
                            id=f"serial-{link.name}",
                            name=link.name,
                            type="serial",
                            connection=target,
                            details={"port": target, "by_id": str(link)},
                        )
                    )

    return devices


def _detect_network() -> list[InventoryDevice]:
    """Detect network devices via mDNS (avahi-browse)."""
    devices = []

    if not cmd_exists("avahi-browse"):
        return devices

    try:
        # Look for common OSmosis-relevant services
        result = subprocess.run(
            ["avahi-browse", "-tpr", "_http._tcp"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in result.stdout.strip().splitlines():
            # =;eth0;IPv4;hostname;_http._tcp;local;hostname.local;192.168.1.50;80;...
            parts = line.split(";")
            if len(parts) < 8 or parts[0] != "=":
                continue

            hostname = parts[3]
            ip = parts[7]
            port = parts[8] if len(parts) > 8 else "80"

            # Filter to likely OSmosis-relevant devices
            lower_name = hostname.lower()
            if any(
                kw in lower_name
                for kw in [
                    "openwrt",
                    "raspberry",
                    "pine",
                    "orange",
                    "jetson",
                    "homeassistant",
                    "hass",
                    "octoprint",
                    "klipper",
                ]
            ):
                dev = InventoryDevice(
                    id=f"net-{ip}",
                    name=hostname,
                    type="network",
                    connection=f"{ip}:{port}",
                    details={"ip": ip, "port": port, "hostname": hostname},
                )
                devices.append(dev)
    except Exception as e:
        log.debug("Network detection failed: %s", e)

    return devices


def scan_inventory() -> list[InventoryDevice]:
    """Run all detection methods and return a unified inventory."""
    all_devices = []
    all_devices.extend(_detect_usb())
    all_devices.extend(_detect_adb())
    all_devices.extend(_detect_serial())
    all_devices.extend(_detect_network())

    # Deduplicate: if we have both USB and ADB for the same device, prefer ADB
    adb_serials = {d.serial for d in all_devices if d.type == "adb"}
    deduped = []
    for d in all_devices:
        if d.type == "usb" and d.vendor in (
            "Samsung",
            "Google",
            "OnePlus",
            "Xiaomi",
            "Fairphone",
            "Motorola",
            "Sony",
            "Nothing",
        ):
            # Skip USB entry if we have a richer ADB entry
            if adb_serials:
                continue
        deduped.append(d)

    return deduped


def inventory_to_dicts(devices: list[InventoryDevice]) -> list[dict]:
    """Convert inventory devices to JSON-serializable dicts."""
    from dataclasses import asdict

    return [asdict(d) for d in devices]
