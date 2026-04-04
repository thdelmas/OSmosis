"""Migrate legacy .cfg files to declarative YAML device profiles.

Reads devices.cfg, scooters.cfg, ebikes.cfg, microcontrollers.cfg, t2.cfg,
and medicat.cfg, and generates one YAML profile per device in profiles/.

Also provides a validation function for profile YAML files.
"""

import logging
from pathlib import Path

from web.core import parse_devices_cfg, parse_microcontrollers_cfg

log = logging.getLogger(__name__)

PROFILES_DIR = Path(__file__).resolve().parent.parent / "profiles"

# ---------------------------------------------------------------------------
# Profile validation
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = {"id", "name"}
OPTIONAL_FIELDS = {
    "brand",
    "category",
    "model",
    "codename",
    "usb_vid",
    "usb_pid",
    "adb_props",
    "flash_tool",
    "flash_method",
    "partitions",
    "firmware",
    "flash_steps",
    "post_flash",
    "requires_unlock",
    "support_status",
    "notes",
}
VALID_CATEGORIES = {
    "phone",
    "tablet",
    "sbc",
    "scooter",
    "ebike",
    "router",
    "mcu",
    "console",
    "wearable",
    "camera",
    "ereader",
    "tv",
    "vacuum",
    "keyboard",
    "synth",
    "calculator",
    "printer",
    "drone",
    "sdr",
    "laptop",
    "desktop",
    "server",
    "solar",
    "vehicle",
    "other",
}
VALID_FIRMWARE_TYPES = {
    "rom",
    "recovery",
    "stock",
    "addon",
    "bootloader",
    "cfw",
}
VALID_SUPPORT_STATUSES = {
    "supported",
    "experimental",
    "not-supported",
    "research",
}


def validate_profile(path: Path) -> list[str]:
    """Validate a YAML profile file. Returns a list of error messages (empty = valid)."""
    import yaml

    errors = []

    try:
        data = yaml.safe_load(path.read_text())
    except Exception as e:
        return [f"Invalid YAML: {e}"]

    if not isinstance(data, dict):
        return ["Profile must be a YAML mapping (dict)"]

    # Required fields
    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append(f"Missing required field: {field}")

    # Category validation
    cat = data.get("category", "")
    if cat and cat not in VALID_CATEGORIES:
        errors.append(
            f"Unknown category '{cat}'. Valid: {', '.join(sorted(VALID_CATEGORIES))}"
        )

    # Support status
    status = data.get("support_status", "")
    if status and status not in VALID_SUPPORT_STATUSES:
        errors.append(
            f"Unknown support_status '{status}'. Valid: {', '.join(VALID_SUPPORT_STATUSES)}"
        )

    # Firmware entries
    for i, fw in enumerate(data.get("firmware", [])):
        if not isinstance(fw, dict):
            errors.append(f"firmware[{i}]: must be a dict")
            continue
        if "id" not in fw:
            errors.append(f"firmware[{i}]: missing 'id'")
        if "name" not in fw:
            errors.append(f"firmware[{i}]: missing 'name'")
        fw_type = fw.get("type", "")
        if fw_type and fw_type not in VALID_FIRMWARE_TYPES:
            errors.append(f"firmware[{i}]: unknown type '{fw_type}'")

    # Flash steps
    for i, step in enumerate(data.get("flash_steps", [])):
        if not isinstance(step, dict):
            errors.append(f"flash_steps[{i}]: must be a dict")
            continue
        if "id" not in step:
            errors.append(f"flash_steps[{i}]: missing 'id'")
        if "name" not in step:
            errors.append(f"flash_steps[{i}]: missing 'name'")

    return errors


def validate_all_profiles() -> dict[str, list[str]]:
    """Validate all profiles in the profiles/ directory.

    Returns {filename: [errors]} for files with errors. Empty dict = all valid.
    """
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    results = {}
    for f in sorted(PROFILES_DIR.glob("**/*.yaml")) + sorted(
        PROFILES_DIR.glob("**/*.yml")
    ):
        errors = validate_profile(f)
        if errors:
            results[str(f.relative_to(PROFILES_DIR))] = errors
    return results


# ---------------------------------------------------------------------------
# Migration from .cfg to profiles/
# ---------------------------------------------------------------------------

# Map flash tool based on device category hints
_FLASH_TOOL_HINTS = {
    "heimdall": ["galaxy", "samsung", "sm-"],
    "fastboot": [
        "pixel",
        "oneplus",
        "xiaomi",
        "fairphone",
        "motorola",
        "sony",
        "nothing",
    ],
}


def _guess_flash_tool(device_id: str, label: str) -> str:
    """Guess the flash tool from the device ID/label."""
    lower = f"{device_id} {label}".lower()
    for tool, keywords in _FLASH_TOOL_HINTS.items():
        if any(kw in lower for kw in keywords):
            return tool
    return ""


def _guess_category(device_id: str, label: str) -> str:
    lower = f"{device_id} {label}".lower()
    if any(kw in lower for kw in ["tab", "tablet"]):
        return "tablet"
    return "phone"


def _guess_brand(label: str) -> str:
    first_word = label.split()[0] if label else ""
    known = [
        "Samsung",
        "Google",
        "OnePlus",
        "Xiaomi",
        "Fairphone",
        "Motorola",
        "Sony",
        "Nothing",
        "LG",
        "HTC",
        "Huawei",
    ]
    for b in known:
        if b.lower() in label.lower():
            return b
    return first_word


def migrate_devices_cfg() -> list[str]:
    """Migrate devices.cfg entries to individual YAML profiles.

    Returns list of created filenames.
    """
    import yaml

    devices = parse_devices_cfg()
    if not devices:
        return []

    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    created = []

    for dev in devices:
        dev_id = dev["id"]
        codename = dev.get("codename", dev_id)
        filename = f"{dev_id}.yaml"
        dest = PROFILES_DIR / filename

        if dest.exists():
            continue  # Don't overwrite existing profiles

        flash_tool = _guess_flash_tool(dev_id, dev.get("label", ""))
        flash_method = (
            "download-mode"
            if flash_tool == "heimdall"
            else "fastboot"
            if flash_tool == "fastboot"
            else ""
        )

        profile = {
            "id": dev_id,
            "name": dev.get("label", dev_id),
            "brand": _guess_brand(dev.get("label", "")),
            "category": _guess_category(dev_id, dev.get("label", "")),
            "model": dev.get("model", ""),
            "codename": codename,
            "flash_tool": flash_tool,
            "flash_method": flash_method,
        }

        # Build firmware sources
        firmware = []
        if dev.get("rom_url"):
            firmware.append(
                {
                    "id": "lineageos",
                    "name": "LineageOS",
                    "url": dev["rom_url"],
                    "type": "rom",
                    "tags": ["privacy", "open-source"],
                }
            )
        if dev.get("twrp_url"):
            firmware.append(
                {
                    "id": "twrp",
                    "name": "TWRP Recovery",
                    "url": dev["twrp_url"],
                    "type": "recovery",
                    "tags": ["recovery", "advanced"],
                }
            )
        if dev.get("eos_url"):
            firmware.append(
                {
                    "id": "eos",
                    "name": "/e/OS",
                    "url": dev["eos_url"],
                    "type": "rom",
                    "tags": ["privacy", "de-googled"],
                }
            )
        if dev.get("stock_url"):
            firmware.append(
                {
                    "id": "stock",
                    "name": "Stock firmware",
                    "url": dev["stock_url"],
                    "type": "stock",
                    "tags": ["official"],
                }
            )
        if dev.get("gapps_url"):
            firmware.append(
                {
                    "id": "gapps",
                    "name": "Google Apps",
                    "url": dev["gapps_url"],
                    "type": "addon",
                    "tags": ["addon"],
                }
            )

        if firmware:
            profile["firmware"] = firmware

        # Default flash steps
        steps = [
            {"id": "download", "name": "Download firmware"},
            {"id": "verify", "name": "Verify integrity"},
        ]
        if flash_tool == "heimdall":
            steps.extend(
                [
                    {
                        "id": "flash-recovery",
                        "name": "Flash recovery",
                        "tool": "heimdall",
                        "sudo": True,
                    },
                    {
                        "id": "flash-rom",
                        "name": "Flash ROM via sideload",
                        "tool": "adb",
                    },
                ]
            )
        elif flash_tool == "fastboot":
            steps.extend(
                [
                    {
                        "id": "unlock",
                        "name": "Unlock bootloader",
                        "tool": "fastboot",
                    },
                    {
                        "id": "flash",
                        "name": "Flash firmware",
                        "tool": "fastboot",
                    },
                ]
            )
        else:
            steps.append({"id": "flash", "name": "Flash firmware"})
        steps.append(
            {
                "id": "post-configure",
                "name": "Post-flash setup",
                "optional": True,
            }
        )

        profile["flash_steps"] = steps

        dest.write_text(
            yaml.dump(profile, default_flow_style=False, sort_keys=False)
        )
        created.append(filename)

    return created


def migrate_microcontrollers_cfg() -> list[str]:
    """Migrate microcontrollers.cfg entries to YAML profiles."""
    import yaml

    boards = parse_microcontrollers_cfg()
    if not boards:
        return []

    mcu_dir = PROFILES_DIR / "mcu"
    mcu_dir.mkdir(parents=True, exist_ok=True)
    created = []

    for board in boards:
        filename = f"{board['id']}.yaml"
        dest = mcu_dir / filename

        if dest.exists():
            continue

        profile = {
            "id": board["id"],
            "name": board.get("label", board["id"]),
            "brand": board.get("brand", ""),
            "category": "mcu",
            "flash_tool": board.get("flash_tool", ""),
            "usb_vid": board.get("usb_vid", ""),
            "usb_pid": board.get("usb_pid", ""),
        }

        if board.get("notes"):
            profile["notes"] = board["notes"]

        flash_args = board.get("flash_args", "")
        if flash_args:
            profile["flash_steps"] = [
                {"id": "download", "name": "Download firmware"},
                {"id": "verify", "name": "Verify integrity"},
                {
                    "id": "flash",
                    "name": "Flash firmware",
                    "tool": board.get("flash_tool", ""),
                    "command": flash_args,
                },
                {
                    "id": "post-configure",
                    "name": "Post-flash setup",
                    "optional": True,
                },
            ]

        dest.write_text(
            yaml.dump(profile, default_flow_style=False, sort_keys=False)
        )
        created.append(f"mcu/{filename}")

    return created


def migrate_all() -> dict[str, list[str]]:
    """Run all migrations. Returns {source: [created files]}."""
    results = {}
    devices = migrate_devices_cfg()
    if devices:
        results["devices.cfg"] = devices
    mcus = migrate_microcontrollers_cfg()
    if mcus:
        results["microcontrollers.cfg"] = mcus
    return results
