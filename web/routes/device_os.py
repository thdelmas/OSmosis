"""OS/ROM identification and device OS listing routes."""

import json
import re
from pathlib import Path
from urllib.parse import urlparse

from flask import Blueprint, jsonify

from web.core import _MODEL_NAMES, parse_devices_cfg
from web.device_profile import get_profile

LETHE_BUILD_DIR = Path.home() / "Osmosis-downloads" / "lethe-builds"

bp = Blueprint("device_os", __name__)


# ── ROM identification registry ──
# Maps URL patterns to ROM metadata. Each ROM can declare:
#   required_recovery: a specific recovery that MUST be used (e.g., Replicant)
#   compatible_recoveries: list of recovery IDs that work (e.g., ["twrp"])
# This keeps ROM<->recovery relationships data-driven and extensible.
_ROM_REGISTRY = [
    {
        "url_pattern": "lethe",
        "id": "lethe",
        "name": "Lethe",
        "desc": "Privacy-hardened Android by OSmosis. Dead man's switch, duress PIN, burner mode, tracker blocking, default-deny firewall.",
        "tags": ["privacy", "security", "hardened", "lethe", "dead-mans-switch"],
        "compatible_recoveries": ["twrp"],
        "recommended_apps": [
            {
                "id": "fdroid",
                "name": "F-Droid",
                "desc": "Free and open-source app store — pre-installed on Lethe.",
                "url": "https://f-droid.org/F-Droid.apk",
                "type": "app",
                "tags": ["app-store", "freedom", "recommended"],
                "install_method": "adb",
            },
            {
                "id": "mull",
                "name": "Mull Browser",
                "desc": "Privacy-hardened Firefox fork — pre-installed on Lethe.",
                "url": "https://f-droid.org/packages/us.spotco.fennec_dos/",
                "type": "app",
                "tags": ["browser", "privacy", "recommended"],
                "install_method": "adb",
            },
        ],
    },
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
        "recommended_apps": [
            {
                "id": "fdroid",
                "name": "F-Droid",
                "desc": "Free and open-source app store. Replicant has no built-in app store — F-Droid lets you discover and install apps on your device.",
                "url": "https://f-droid.org/F-Droid.apk",
                "type": "app",
                "tags": ["app-store", "freedom", "recommended"],
                "install_method": "adb",
            },
        ],
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
        "flash_method": "sd-card",
    },
    {
        "url_pattern": "mobian",
        "id": "mobian",
        "name": "Mobian",
        "desc": "Debian-based mobile Linux with Phosh UI. Stable and well-supported.",
        "tags": ["linux", "debian", "phosh"],
        "flash_method": "sd-card",
    },
    {
        "url_pattern": "manjaro",
        "id": "manjaro-arm",
        "name": "Manjaro ARM",
        "desc": "Arch-based rolling release for ARM devices. Plasma Mobile or Phosh.",
        "tags": ["linux", "arch", "rolling"],
        "flash_method": "sd-card",
    },
    {
        "url_pattern": "ubports",
        "id": "ubuntu-touch",
        "name": "Ubuntu Touch",
        "desc": "Unity-based mobile OS. Maintained by the UBports community.",
        "tags": ["linux", "ubuntu"],
        "flash_method": "sd-card",
    },
    {
        "url_pattern": "nothing.tech",
        "id": "nothingos",
        "name": "Nothing OS",
        "desc": "Near-stock Android with the Glyph interface for Nothing phones.",
        "tags": ["official", "near-stock"],
        "flash_method": "fastboot",
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
            if entry.get("recommended_apps"):
                rom["recommended_apps"] = entry["recommended_apps"]
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


def _identify_rom_by_id(rom_id: str) -> dict | None:
    """Look up ROM metadata from the registry by ID."""
    for entry in _ROM_REGISTRY:
        if entry["id"] == rom_id:
            return entry
    return None


def _find_local_build(rom_id: str, codename: str) -> dict | None:
    """Check for a local pre-built image (e.g. Lethe overlay ZIP)."""
    if not codename or not LETHE_BUILD_DIR.is_dir():
        return None
    # Look for meta JSON first (has sha256, version info)
    for meta_path in LETHE_BUILD_DIR.glob(f"*-{codename}-meta.json"):
        try:
            meta = json.loads(meta_path.read_text())
            zip_path = meta_path.with_name(meta_path.name.replace("-meta.json", ".zip"))
            if zip_path.exists():
                return {
                    "path": str(zip_path),
                    "filename": zip_path.name,
                    "sha256": meta.get("sha256", ""),
                    "version": meta.get("version", ""),
                    "base_version": meta.get("base_version", ""),
                    "android_version": meta.get("android_version", ""),
                }
        except (json.JSONDecodeError, OSError):
            continue
    # Fallback: look for ZIP without meta
    for zip_path in LETHE_BUILD_DIR.glob(f"*-{codename}.zip"):
        return {"path": str(zip_path), "filename": zip_path.name}
    return None


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

    # Merge firmware entries from YAML profile (adds ROMs not in devices.cfg)
    existing_ids = {e["id"] for e in os_list}
    profile = get_profile(device["id"])
    if not profile:
        # Try codename as fallback
        codename = device.get("codename", "")
        if codename:
            profile = get_profile(codename)
    if profile:
        for fw in profile.firmware:
            if fw.id not in existing_ids:
                entry = {
                    "id": fw.id,
                    "name": fw.name,
                    "url": fw.url,
                    "type": fw.type,
                    "tags": fw.tags,
                    "version": fw.version,
                }
                if fw.ipfs_cid:
                    entry["ipfs_cid"] = fw.ipfs_cid
                if fw.sha256:
                    entry["sha256"] = fw.sha256
                # Enrich from ROM registry if available
                registry_match = _identify_rom_by_id(fw.id)
                if registry_match:
                    entry.setdefault("desc", registry_match.get("desc", ""))
                    entry.setdefault("compatible_recoveries", registry_match.get("compatible_recoveries", []))
                    if registry_match.get("recommended_apps"):
                        entry["recommended_apps"] = registry_match["recommended_apps"]
                os_list.append(entry)

    # Enrich entries with local builds when URL is empty
    codename = device.get("codename", "")
    for entry in os_list:
        if not entry.get("url") and not entry.get("ipfs_cid"):
            local = _find_local_build(entry["id"], codename)
            if local:
                entry["url"] = f"/api/lethe/builds/{local['filename']}"
                entry["local_path"] = local["path"]
                if local.get("sha256"):
                    entry["sha256"] = local["sha256"]
                if local.get("version"):
                    entry.setdefault("version", local["version"])
                if local.get("base_version"):
                    entry["base_info"] = (
                        f"LineageOS {local['base_version']} (Android {local.get('android_version', '')})"
                    )

    # Group by type for sectioned display
    sections = {}
    type_order = ["rom", "stock", "recovery", "addon", "app"]
    type_labels = {
        "rom": "Operating Systems",
        "stock": "Stock Firmware",
        "recovery": "Recovery",
        "addon": "Add-ons",
        "app": "Apps",
    }
    for entry in os_list:
        t = entry.get("type", "rom")
        sections.setdefault(t, []).append(entry)

    grouped = []
    for t in type_order:
        if t in sections:
            grouped.append({"type": t, "label": type_labels.get(t, t.title()), "items": sections[t]})
    # Any remaining types not in type_order
    for t, items in sections.items():
        if t not in type_order:
            grouped.append({"type": t, "label": t.title(), "items": items})

    return jsonify({"device": device, "os_list": os_list, "sections": grouped})
