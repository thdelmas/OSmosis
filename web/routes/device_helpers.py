"""Device detection helpers — USB parsing and ADB device querying."""

import re
import subprocess

from web.core import _MODEL_NAMES, parse_devices_cfg


def parse_usb_devices() -> list[dict]:
    """Return list of phone-like USB devices from lsusb, with friendly names."""
    phone_vendors = {
        # --- Phones & Tablets ---
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
        "2a96": "Shift",
        "0e8d": "MediaTek",
        "19d2": "ZTE",
        "05c6": "Qualcomm",
        "1bbb": "Alcatel",
        "2916": "Yota",
        "2b4f": "Murena",
        # --- Linux Phones & SBCs ---
        "2df3": "Pine64",
        # Note: Purism Librem 5 uses 1fc6 (not 1d6b which is Linux root hub)
        "1fc6": "Purism",
        "2c97": "Ledger",
        # --- Routers & Networking ---
        "0846": "Netgear",
        "13b1": "Linksys",
        "2357": "TP-Link",
        "0b05": "ASUS",
        "0bda": "Realtek",
        # --- IoT & Microcontrollers ---
        "10c4": "Silicon Labs",
        "1a86": "QinHeng (CH340)",
        "0403": "FTDI",
        "2341": "Arduino",
        "2e8a": "Raspberry Pi",
        "303a": "Espressif",
        "1fc9": "NXP",
        "1366": "SEGGER",
        "0483": "STMicroelectronics",
        # --- E-Readers ---
        "2237": "Kobo",
        "1d6a": "reMarkable",
        # --- Game Consoles ---
        "057e": "Nintendo",
        "28de": "Valve",
        # --- Scooters & E-Bikes ---
        "0000": "Ninebot",
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
                    raw = line
                    id_pos = line.find("ID ")
                    if id_pos != -1:
                        after_id = line[id_pos + 4 :]
                        space = after_id.find(" ")
                        raw = (
                            after_id[space + 1 :].strip()
                            if space != -1
                            else after_id
                        )

                    name = re.sub(
                        r"\b(Inc\.?|Co\.?,?\s*Ltd\.?|Corp\.?|Electronics|Technology|Communication)\b",
                        "",
                        raw,
                        flags=re.IGNORECASE,
                    )
                    name = re.sub(r"\([^)]*\)", "", name)
                    name = re.sub(
                        r"\b(misc\.?|series)\b", "", name, flags=re.IGNORECASE
                    )
                    name = (
                        re.sub(r"[,\s]+", " ", name).strip().strip(",").strip()
                    )
                    if not name or name.lower() == brand.lower():
                        name = brand

                    devices.append({"vendor": brand, "name": name})
                    break
    except Exception:
        pass
    return devices


def get_adb_prop(serial: str, prop: str) -> str:
    """Get a single Android system property via adb."""
    return subprocess.run(
        ["adb", "-s", serial, "shell", "getprop", prop],
        capture_output=True,
        text=True,
        timeout=5,
    ).stdout.strip()


def get_adb_imei(serial: str) -> str:
    """Try to read IMEI from a connected ADB device.

    Uses ``service call iphonesubinfo`` which works on most Android versions
    without root.  Falls back to the ``persist.radio.imei`` property.
    """
    try:
        result = subprocess.run(
            [
                "adb",
                "-s",
                serial,
                "shell",
                "service",
                "call",
                "iphonesubinfo",
                "1",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        digits = re.sub(
            r"[^0-9]",
            "",
            "".join(
                seg.split("'")[1] if "'" in seg else ""
                for seg in result.stdout.splitlines()
            ),
        ).replace(".", "")
        if len(digits) >= 14:
            return digits[:15]
    except Exception:
        pass

    prop = get_adb_prop(serial, "persist.radio.imei")
    if prop and len(prop) >= 14:
        return prop.strip()

    return ""


def query_adb_device(serial: str) -> dict:
    """Query a single ADB device by serial for model/codename info."""
    model = get_adb_prop(serial, "ro.product.model")
    codename = get_adb_prop(serial, "ro.product.device")
    if not codename:
        codename = get_adb_prop(serial, "ro.product.board")

    brand = get_adb_prop(serial, "ro.product.brand").capitalize()
    marketing = get_adb_prop(serial, "ro.product.marketname")
    if not marketing:
        marketing = get_adb_prop(serial, "ro.config.marketing_name")
    if not marketing:
        marketing = _MODEL_NAMES.get(model, "")

    display_name = marketing or model
    if brand and not display_name.lower().startswith(brand.lower()):
        display_name = f"{brand} {display_name}"

    imei = get_adb_imei(serial)

    match = None
    for dev in parse_devices_cfg():
        if (
            dev["model"].lower() == model.lower()
            or dev["codename"].lower() == codename.lower()
        ):
            match = dev
            break

    return {
        "serial": serial,
        "model": model,
        "codename": codename,
        "brand": brand,
        "display_name": display_name,
        "imei": imei,
        "match": match,
    }
