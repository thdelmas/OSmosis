"""OS/ROM identification and device OS listing routes."""

import re
from urllib.parse import urlparse

from flask import Blueprint, jsonify

from web.core import _MODEL_NAMES, parse_devices_cfg

bp = Blueprint("device_os", __name__)


# ── ROM identification registry ──
# Maps URL patterns to ROM metadata. Each ROM can declare:
#   required_recovery: a specific recovery that MUST be used (e.g., Replicant)
#   compatible_recoveries: list of recovery IDs that work (e.g., ["twrp"])
# This keeps ROM<->recovery relationships data-driven and extensible.
_ROM_REGISTRY = [
    {
        "url_pattern": "replicant",
        "id": "replicant",
        "name": "Replicant",
        "desc": "Fully free Android distribution focused on freedom and privacy.",
        "tags": ["freedom", "privacy"],
        "required_recovery": {
            "id": "replicant-recovery",
            "name": "Replicant Recovery",
            "desc": "Replicant's own recovery — required to install Replicant ROMs.",
            "type": "recovery",
            "tags": ["recovery"],
            "url_template": "https://download.replicant.us/images/replicant-6.0/0004-transition/images/{codename}/recovery-{codename}.img",
        },
    },
    {
        "url_pattern": "lineageos",
        "id": "lineageos",
        "name": "LineageOS",
        "desc": "Privacy-focused, open-source Android distribution.",
        "tags": ["popular", "privacy"],
        "compatible_recoveries": ["twrp"],
    },
    {
        "url_pattern": "lineage-",
        "id": "lineageos",
        "name": "LineageOS",
        "desc": "Privacy-focused, open-source Android distribution.",
        "tags": ["popular", "privacy"],
        "compatible_recoveries": ["twrp"],
    },
    {
        "url_pattern": "calyxos",
        "id": "calyxos",
        "name": "CalyxOS",
        "desc": "Privacy-focused Android with verified boot.",
        "tags": ["privacy", "security"],
        "compatible_recoveries": ["twrp"],
    },
    {
        "url_pattern": "grapheneos",
        "id": "grapheneos",
        "name": "GrapheneOS",
        "desc": "Security-hardened Android for Pixel devices.",
        "tags": ["security", "privacy"],
        "flash_method": "fastboot",
    },
    {
        "url_pattern": "postmarketos",
        "id": "postmarketos",
        "name": "postmarketOS",
        "desc": "Real Linux distribution for phones and mobile devices.",
        "tags": ["linux", "freedom"],
        "compatible_recoveries": ["twrp"],
    },
]


def _identify_rom(url: str, device: dict) -> dict:
    """Identify a ROM from its URL and return metadata with recovery requirements."""
    url_lower = url.lower()
    codename = device.get("codename", "") or device.get("model", "")
    raw_model = (device.get("model", "") or "").lower()
    model_lower = re.sub(r"^(gt|sm|lg|xt|ta)-?", "", raw_model).replace("-", "")

    for entry in _ROM_REGISTRY:
        if entry["url_pattern"] in url_lower:
            rom = {
                "id": entry["id"],
                "name": entry["name"],
                "desc": entry["desc"],
                "url": url,
                "type": "rom",
                "tags": entry.get("tags", []),
            }
            if entry.get("compatible_recoveries"):
                rom["compatible_recoveries"] = entry["compatible_recoveries"]
            if entry.get("flash_method"):
                rom["flash_method"] = entry["flash_method"]
            if entry.get("required_recovery"):
                rec = dict(entry["required_recovery"])
                if "url_template" in rec:
                    rom_codename = codename
                    path_parts = urlparse(url_lower).path.rstrip("/").split("/")[:-1]
                    for part in reversed(path_parts):
                        if model_lower and model_lower in part.replace("-", ""):
                            rom_codename = part
                            break
                    if rom_codename:
                        rec["url"] = rec.pop("url_template").replace("{codename}", rom_codename)
                    else:
                        rec.pop("url_template", None)
                rom["required_recovery"] = rec
            return rom

    return {
        "id": "custom-rom",
        "name": "Custom ROM",
        "desc": "Custom ROM for this device.",
        "url": url,
        "type": "rom",
        "tags": [],
        "compatible_recoveries": ["twrp"],
    }


@bp.route("/api/devices/<device_id>/os")
def api_device_os(device_id):
    """Return available OS options for a specific device."""
    device = None
    for dev in parse_devices_cfg():
        if dev["id"].lower() == device_id.lower():
            device = dev
            break

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

    rom_url = device.get("rom_url", "")
    rom_info = _identify_rom(rom_url, device)

    if rom_url:
        os_list.append(rom_info)

    if device.get("eos_url"):
        os_list.append(
            {
                "id": "eos",
                "name": "/e/OS",
                "desc": "De-Googled Android with built-in privacy tools and cloud.",
                "url": device["eos_url"],
                "type": "rom",
                "tags": ["privacy", "de-googled"],
                "compatible_recoveries": ["twrp"],
            }
        )

    if device.get("stock_url"):
        os_list.append(
            {
                "id": "stock",
                "name": "Stock firmware",
                "desc": "Original manufacturer firmware — restore to factory state.",
                "url": device["stock_url"],
                "type": "stock",
                "tags": ["official"],
                "flash_method": "stock-recovery",
            }
        )

    recoveries = {}
    if device.get("twrp_url"):
        recoveries["twrp"] = {
            "id": "twrp",
            "name": "TWRP Recovery",
            "desc": "Custom recovery for advanced flashing, backups, and root.",
            "url": device["twrp_url"],
            "type": "recovery",
            "tags": ["recovery", "advanced"],
        }

    for entry in os_list:
        req = entry.get("required_recovery")
        if req and req.get("id") not in recoveries:
            recoveries[req["id"]] = req

    os_list.extend(recoveries.values())

    if device.get("gapps_url"):
        os_list.append(
            {
                "id": "gapps",
                "name": "Google Apps (GApps)",
                "desc": "Add Google Play Store and services after installing a custom ROM.",
                "url": device["gapps_url"],
                "type": "addon",
                "tags": ["addon"],
            }
        )

    return jsonify({"device": device, "os_list": os_list})
