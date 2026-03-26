"""Device detection and USB device parsing routes."""

import re
import subprocess

from flask import Blueprint, jsonify, request

from web.core import _MODEL_NAMES, cmd_exists, parse_devices_cfg

bp = Blueprint("device", __name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_usb_devices() -> list[dict]:
    """Return list of phone-like USB devices from lsusb, with friendly names."""
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
        lsusb = subprocess.run(["lsusb"], capture_output=True, text=True, timeout=5)
        for line in lsusb.stdout.strip().splitlines():
            low = line.lower()
            for vid, brand in phone_vendors.items():
                if vid in low:
                    raw = line
                    id_pos = line.find("ID ")
                    if id_pos != -1:
                        after_id = line[id_pos + 4 :]
                        space = after_id.find(" ")
                        raw = after_id[space + 1 :].strip() if space != -1 else after_id

                    name = re.sub(
                        r"\b(Inc\.?|Co\.?,?\s*Ltd\.?|Corp\.?|Electronics|Technology|Communication)\b",
                        "",
                        raw,
                        flags=re.IGNORECASE,
                    )
                    name = re.sub(r"\([^)]*\)", "", name)
                    name = re.sub(r"\b(misc\.?|series)\b", "", name, flags=re.IGNORECASE)
                    name = re.sub(r"[,\s]+", " ", name).strip().strip(",").strip()
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
        capture_output=True,
        text=True,
        timeout=5,
    ).stdout.strip()


def _query_adb_device(serial: str) -> dict:
    """Query a single ADB device by serial for model/codename info."""
    model = _get_adb_prop(serial, "ro.product.model")
    codename = _get_adb_prop(serial, "ro.product.device")
    if not codename:
        codename = _get_adb_prop(serial, "ro.product.board")

    brand = _get_adb_prop(serial, "ro.product.brand").capitalize()
    marketing = _get_adb_prop(serial, "ro.product.marketname")
    if not marketing:
        marketing = _get_adb_prop(serial, "ro.config.marketing_name")
    if not marketing:
        marketing = _MODEL_NAMES.get(model, "")

    display_name = marketing or model
    if brand and not display_name.lower().startswith(brand.lower()):
        display_name = f"{brand} {display_name}"

    match = None
    for dev in parse_devices_cfg():
        if dev["model"].lower() == model.lower() or dev["codename"].lower() == codename.lower():
            match = dev
            break

    return {
        "serial": serial,
        "model": model,
        "codename": codename,
        "brand": brand,
        "display_name": display_name,
        "match": match,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@bp.route("/api/devices")
def api_devices():
    return jsonify(parse_devices_cfg())


@bp.route("/api/devices/search")
def api_devices_search():
    """Search devices by category, brand, model, or serial. Returns scored matches."""
    category = request.args.get("category", "").lower().strip()
    brand = request.args.get("brand", "").lower().strip()
    model_q = request.args.get("model", "").lower().strip()
    serial_q = request.args.get("serial", "").lower().strip()

    if not any([category, brand, model_q, serial_q]):
        return jsonify([])

    all_devices = parse_devices_cfg()

    # Also include _MODEL_NAMES entries as virtual devices for broader matching
    for model_code, friendly in _MODEL_NAMES.items():
        # Avoid duplicates with devices.cfg
        if any(d["model"].lower() == model_code.lower() for d in all_devices):
            continue
        all_devices.append(
            {
                "id": model_code.lower().replace(" ", "-"),
                "label": friendly,
                "model": model_code,
                "codename": "",
                "rom_url": "",
                "twrp_url": "",
                "eos_url": "",
                "stock_url": "",
                "gapps_url": "",
            }
        )

    results = []
    for dev in all_devices:
        score = 0
        haystack = f"{dev['label']} {dev['model']} {dev['codename']} {dev.get('id', '')}".lower()

        if brand and brand in haystack:
            score += 2
        if model_q:
            if model_q in dev["model"].lower():
                score += 5
            elif model_q in dev["label"].lower():
                score += 3
            elif model_q in dev["codename"].lower():
                score += 3
            elif model_q in haystack:
                score += 1
        if serial_q and serial_q in haystack:
            score += 1

        if score > 0:
            results.append({**dev, "_score": score})

    results.sort(key=lambda d: d["_score"], reverse=True)

    # Strip internal score before returning
    for r in results:
        r.pop("_score", None)

    return jsonify(results[:20])


@bp.route("/api/detect")
def api_detect():
    """Auto-detect connected device via adb."""
    if not cmd_exists("adb"):
        return jsonify({"error": "adb not installed"}), 500

    try:
        dev_list = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=5)
        adb_states = ("device", "recovery", "sideload")
        all_adb_lines = [line for line in dev_list.stdout.strip().splitlines()[1:] if line.strip() and "\t" in line]
        dev_lines = [line for line in all_adb_lines if line.split("\t")[-1] in adb_states]
        # Check for unauthorized devices
        unauth_lines = [line for line in all_adb_lines if line.split("\t")[-1] == "unauthorized"]
        if unauth_lines and not dev_lines:
            serial = unauth_lines[0].split("\t")[0]
            usb_devices = _parse_usb_devices()
            return jsonify(
                {
                    "error": "unauthorized",
                    "serial": serial,
                    "usb_devices": usb_devices,
                    "hint": "Device connected but not authorized. Check the device screen for an authorization prompt, or if in recovery mode, ADB may need to be enabled.",
                }
            )
        if not dev_lines:
            # Check if device is in Download Mode (Samsung/Heimdall)
            in_download = False
            if cmd_exists("heimdall"):
                try:
                    dl = subprocess.run(
                        ["heimdall", "detect"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    in_download = dl.returncode == 0
                except Exception:
                    pass

            usb_devices = _parse_usb_devices()

            if in_download:
                # Try to identify the device from USB info
                brand = usb_devices[0]["vendor"] if usb_devices else "Unknown"
                name = usb_devices[0]["name"] if usb_devices else "Device"
                return jsonify(
                    {
                        "error": "download_mode",
                        "brand": brand,
                        "usb_name": name,
                        "usb_devices": usb_devices,
                        "hint": f"{name} is in Download Mode. You can flash recovery or stock firmware, or reboot it to normal mode.",
                    }
                )

            if usb_devices:
                return jsonify({"error": "usb_no_adb", "usb_devices": usb_devices}), 404
            return jsonify({"error": "no_device"}), 404

        serials = [line.split("\t")[0] for line in dev_lines]
        states = {line.split("\t")[0]: line.split("\t")[-1] for line in dev_lines}

        # For sideload mode, we can't query device properties — just report the state
        if all(states.get(s) == "sideload" for s in serials):
            serial = serials[0]

            # Try to identify Xiaomi devices in MIAssistant sideload mode
            from web.miassistant_protocol import identify_xiaomi_sideload
            from web.routes.miassistant import _check_xiaomi_usb

            xiaomi_ident = identify_xiaomi_sideload(serial)
            is_xiaomi_usb = _check_xiaomi_usb()

            if xiaomi_ident:
                match = None
                for dev in parse_devices_cfg():
                    if (
                        dev["codename"].lower() == xiaomi_ident["codename"].lower()
                        or dev["model"].lower() == xiaomi_ident["model"].lower()
                    ):
                        match = dev
                        break
                return jsonify(
                    {
                        "adb_state": "sideload",
                        "serial": serial,
                        "model": xiaomi_ident["model"],
                        "codename": xiaomi_ident["codename"],
                        "brand": "Xiaomi",
                        "display_name": xiaomi_ident["display_name"],
                        "match": match,
                        "hint": (
                            f"{xiaomi_ident['display_name']} detected in MIAssistant sideload mode. "
                            "Use the MIAssistant sideload endpoint to flash a stock ROM."
                        ),
                    }
                )

            return jsonify(
                {
                    "adb_state": "sideload",
                    "serial": serial,
                    "model": "",
                    "codename": "",
                    "brand": "Xiaomi" if is_xiaomi_usb else "",
                    "display_name": "Xiaomi device in sideload mode" if is_xiaomi_usb else "Device in sideload mode",
                    "match": None,
                    "hint": (
                        "Device is in ADB sideload mode and ready to receive a ROM. Go to the Install step to flash."
                    ),
                }
            )

        # For recovery mode, try to query but fall back gracefully
        detected = []
        for s in serials:
            d = _query_adb_device(s)
            d["adb_state"] = states.get(s, "device")
            detected.append(d)

        if len(detected) == 1:
            d = detected[0]
            # If recovery mode returned no model, indicate the state
            if not d["model"] and d["adb_state"] == "recovery":
                d["display_name"] = "Device in recovery mode"
                d["hint"] = (
                    "Device is in recovery mode. Model couldn't be detected — you can reboot to normal mode for auto-detection, or search for your device manually."
                )
            return jsonify(
                {
                    "model": d["model"],
                    "codename": d["codename"],
                    "brand": d["brand"],
                    "display_name": d["display_name"],
                    "match": d["match"],
                    "adb_state": d.get("adb_state", "device"),
                    "hint": d.get("hint", ""),
                }
            )
        else:
            return jsonify({"multiple": True, "devices": detected})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/devices/connected")
def api_devices_connected():
    """Return all connected devices across ADB, fastboot, and sideload modes.

    Designed for real-time polling by the frontend sidebar.
    """
    # When MiAssistantTool is using the USB bus, skip ADB/fastboot calls
    from web.routes.miassistant import _usb_locked

    if _usb_locked:
        return jsonify(
            {
                "devices": [
                    {
                        "serial": "",
                        "mode": "flashing",
                        "transport": "usb",
                        "model": "",
                        "product": "",
                        "display_name": "Flashing in progress...",
                    }
                ],
                "count": 1,
                "usb_locked": True,
            }
        )

    devices = []

    # 1. ADB devices (normal, recovery, sideload)
    if cmd_exists("adb"):
        try:
            result = subprocess.run(
                ["adb", "devices", "-l"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            for line in result.stdout.strip().splitlines()[1:]:
                parts = line.split()
                if len(parts) < 2:
                    continue
                serial = parts[0]
                state = parts[1]

                if state not in ("device", "recovery", "sideload", "unauthorized"):
                    continue

                # Extract model/product from -l output
                props = {}
                for token in parts[2:]:
                    if ":" in token:
                        k, v = token.split(":", 1)
                        props[k] = v

                entry = {
                    "serial": serial,
                    "mode": state,
                    "transport": "usb",
                    "model": props.get("model", ""),
                    "product": props.get("product", ""),
                    "display_name": "",
                }

                if state == "sideload":
                    from web.miassistant_protocol import identify_xiaomi_sideload

                    ident = identify_xiaomi_sideload(serial)
                    if not ident and props.get("model"):
                        ident = identify_xiaomi_sideload(props["model"])
                    if ident:
                        entry["display_name"] = ident["display_name"]
                        entry["codename"] = ident["codename"]
                    else:
                        entry["display_name"] = props.get("model", "Unknown device")
                elif state == "unauthorized":
                    entry["display_name"] = "Unauthorized (check phone screen)"
                else:
                    d = _query_adb_device(serial)
                    entry["display_name"] = d.get("display_name", props.get("model", serial))
                    entry["codename"] = d.get("codename", "")
                    entry["brand"] = d.get("brand", "")

                if not entry["display_name"]:
                    entry["display_name"] = _MODEL_NAMES.get(props.get("model", "").upper(), props.get("model", serial))

                devices.append(entry)
        except Exception:
            pass

    # 2. Fastboot devices
    if cmd_exists("fastboot"):
        try:
            from web.routes.fastboot import _fastboot_devices, _fastboot_getvar

            fb_devs = _fastboot_devices()
            for fb in fb_devs:
                product = _fastboot_getvar("product")
                unlocked = _fastboot_getvar("unlocked")

                # Look up friendly name: try model number first, then codename from devices.cfg
                display = _MODEL_NAMES.get(product.upper(), "") if product else ""
                codename = product or ""
                if not display and product:
                    for dev in parse_devices_cfg():
                        if dev["codename"].lower() == product.lower():
                            display = dev["label"]
                            break
                if not display:
                    display = product or "Fastboot device"

                devices.append(
                    {
                        "serial": fb["serial"],
                        "mode": "fastboot",
                        "transport": "usb",
                        "model": product,
                        "codename": codename,
                        "product": product,
                        "display_name": display,
                        "unlocked": unlocked == "yes",
                    }
                )
        except Exception:
            pass

    # 3. Samsung Download Mode (Heimdall)
    if cmd_exists("heimdall"):
        try:
            dl = subprocess.run(
                ["heimdall", "detect"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if dl.returncode == 0:
                devices.append(
                    {
                        "serial": "",
                        "mode": "download",
                        "transport": "usb",
                        "model": "",
                        "product": "",
                        "display_name": "Samsung device (Download Mode)",
                    }
                )
        except Exception:
            pass

    return jsonify({"devices": devices, "count": len(devices)})
