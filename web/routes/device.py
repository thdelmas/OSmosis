"""Device detection and USB device parsing routes."""

import re
import subprocess

from flask import Blueprint, jsonify, request

from web.core import _MODEL_NAMES, cmd_exists, parse_devices_cfg

bp = Blueprint("device", __name__)


# ---------------------------------------------------------------------------
# Config migration (pipe-delimited -> YAML)
# ---------------------------------------------------------------------------


@bp.route("/api/devices/migrate-yaml", methods=["POST"])
def api_devices_migrate_yaml():
    """Migrate pipe-delimited .cfg files to structured YAML.

    This creates .yaml files alongside the existing .cfg files.
    The .cfg files are preserved as backups.
    """
    import yaml
    from web.core import (
        CONFIG_FILE, DEVICES_YAML,
        MCU_CONFIG_FILE, MCU_YAML,
        SCRIPT_DIR,
        parse_devices_cfg,
        parse_microcontrollers_cfg,
    )

    migrated = []

    # Devices
    if CONFIG_FILE.exists() and not DEVICES_YAML.exists():
        devices = parse_devices_cfg()
        if devices:
            DEVICES_YAML.write_text(yaml.dump(devices, default_flow_style=False, sort_keys=False))
            migrated.append("devices.yaml")

    # Microcontrollers
    if MCU_CONFIG_FILE.exists() and not MCU_YAML.exists():
        boards = parse_microcontrollers_cfg()
        if boards:
            MCU_YAML.write_text(yaml.dump(boards, default_flow_style=False, sort_keys=False))
            migrated.append("microcontrollers.yaml")

    # Scooters
    scooters_cfg = SCRIPT_DIR / "scooters.cfg"
    scooters_yaml = SCRIPT_DIR / "scooters.yaml"
    if scooters_cfg.exists() and not scooters_yaml.exists():
        from web.routes.scooter import parse_scooters_cfg
        scooters = parse_scooters_cfg()
        if scooters:
            scooters_yaml.write_text(yaml.dump(scooters, default_flow_style=False, sort_keys=False))
            migrated.append("scooters.yaml")

    # E-bikes
    ebikes_cfg = SCRIPT_DIR / "ebikes.cfg"
    ebikes_yaml = SCRIPT_DIR / "ebikes.yaml"
    if ebikes_cfg.exists() and not ebikes_yaml.exists():
        from web.routes.ebike import parse_ebikes_cfg
        ebikes = parse_ebikes_cfg()
        if ebikes:
            ebikes_yaml.write_text(yaml.dump(ebikes, default_flow_style=False, sort_keys=False))
            migrated.append("ebikes.yaml")

    if not migrated:
        return jsonify({"message": "Nothing to migrate (YAML files already exist or no .cfg files found)"})

    return jsonify({"migrated": migrated})


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
        all_devices.append({
            "id": model_code.lower().replace(" ", "-"),
            "label": friendly,
            "model": model_code,
            "codename": "",
            "rom_url": "",
            "twrp_url": "",
            "eos_url": "",
            "stock_url": "",
            "gapps_url": "",
        })

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


@bp.route("/api/devices/<device_id>/os")
def api_device_os(device_id):
    """Return available OS options for a specific device."""
    device = None
    for dev in parse_devices_cfg():
        if dev["id"].lower() == device_id.lower():
            device = dev
            break

    # Also check _MODEL_NAMES fallback entries
    if not device:
        for model_code, friendly in _MODEL_NAMES.items():
            slug = model_code.lower().replace(" ", "-")
            if slug == device_id.lower():
                device = {
                    "id": slug,
                    "label": friendly,
                    "model": model_code,
                    "codename": "",
                    "rom_url": "",
                    "twrp_url": "",
                    "eos_url": "",
                    "stock_url": "",
                    "gapps_url": "",
                }
                break

    if not device:
        return jsonify({"error": "device_not_found"}), 404

    os_list = []

    if device.get("rom_url"):
        os_list.append({
            "id": "lineageos",
            "name": "LineageOS",
            "desc": "Privacy-focused, open-source Android distribution.",
            "url": device["rom_url"],
            "type": "rom",
            "tags": ["popular", "privacy"],
        })

    if device.get("eos_url"):
        os_list.append({
            "id": "eos",
            "name": "/e/OS",
            "desc": "De-Googled Android with built-in privacy tools and cloud.",
            "url": device["eos_url"],
            "type": "rom",
            "tags": ["privacy", "de-googled"],
        })

    if device.get("stock_url"):
        os_list.append({
            "id": "stock",
            "name": "Stock firmware",
            "desc": "Original manufacturer firmware — restore to factory state.",
            "url": device["stock_url"],
            "type": "stock",
            "tags": ["official"],
        })

    if device.get("twrp_url"):
        os_list.append({
            "id": "twrp",
            "name": "TWRP Recovery",
            "desc": "Custom recovery for advanced flashing, backups, and root.",
            "url": device["twrp_url"],
            "type": "recovery",
            "tags": ["recovery", "advanced"],
        })

    if device.get("gapps_url"):
        os_list.append({
            "id": "gapps",
            "name": "Google Apps (GApps)",
            "desc": "Add Google Play Store and services after installing a custom ROM.",
            "url": device["gapps_url"],
            "type": "addon",
            "tags": ["addon"],
        })

    return jsonify({"device": device, "os_list": os_list})


@bp.route("/api/detect")
def api_detect():
    """Auto-detect connected device via adb."""
    if not cmd_exists("adb"):
        return jsonify({"error": "adb not installed"}), 500

    try:
        dev_list = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=5)
        dev_lines = [
            line
            for line in dev_list.stdout.strip().splitlines()[1:]
            if line.strip() and ("device" in line.split("\t")[-1:] or "recovery" in line.split("\t")[-1:])
        ]
        if not dev_lines:
            usb_devices = _parse_usb_devices()
            if usb_devices:
                return jsonify({"error": "usb_no_adb", "usb_devices": usb_devices}), 404
            return jsonify({"error": "no_device"}), 404

        serials = [line.split("\t")[0] for line in dev_lines]
        detected = [_query_adb_device(s) for s in serials]

        if len(detected) == 1:
            d = detected[0]
            return jsonify(
                {
                    "model": d["model"],
                    "codename": d["codename"],
                    "display_name": d["display_name"],
                    "match": d["match"],
                }
            )
        else:
            return jsonify({"multiple": True, "devices": detected})

    except Exception as e:
        return jsonify({"error": str(e)}), 500



