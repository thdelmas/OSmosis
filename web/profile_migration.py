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
    "computer",
    "server",
    "solar",
    "vehicle",
    "lab",
    "iot",
    "other",
}
VALID_FIRMWARE_TYPES = {
    "rom",
    "recovery",
    "stock",
    "addon",
    "bootloader",
    "cfw",
    "os",
    "bios",
    "app",
    "agent-os",
    "config",
    "tool",
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


def migrate_scooters_cfg() -> list[str]:
    """Migrate scooters.cfg entries to YAML profiles under profiles/scooter/."""
    import yaml

    from web.routes.scooter import parse_scooters_cfg

    scooters = parse_scooters_cfg()
    if not scooters:
        return []

    out_dir = PROFILES_DIR / "scooter"
    out_dir.mkdir(parents=True, exist_ok=True)
    created = []

    for s in scooters:
        filename = f"{s['id']}.yaml"
        dest = out_dir / filename
        if dest.exists():
            continue

        method = s.get("flash_method", "")
        flash_tool = (
            "stlink"
            if "stlink" in method
            else "bleak"
            if "ble" in method
            else ""
        )

        profile = {
            "id": s["id"],
            "name": s.get("label", s["id"]),
            "brand": s.get("brand", ""),
            "category": "scooter",
            "flash_tool": flash_tool,
            "flash_method": method,
        }
        if s.get("notes"):
            profile["notes"] = s["notes"]

        firmware = []
        if s.get("cfw_url"):
            firmware.append(
                {
                    "id": "cfw",
                    "name": "Custom firmware",
                    "url": s["cfw_url"],
                    "type": "cfw",
                    "tags": ["scooter", s.get("protocol", "")],
                }
            )
        if firmware:
            profile["firmware"] = firmware

        steps = [
            {"id": "download", "name": "Download firmware"},
            {"id": "verify", "name": "Verify integrity"},
            {"id": "backup", "name": "Backup current firmware", "optional": True},
        ]
        if "ble" in method:
            steps.append(
                {"id": "flash", "name": "Flash CFW over BLE", "tool": "bleak"}
            )
        if "stlink" in method:
            steps.append(
                {
                    "id": "flash-stlink",
                    "name": "Flash via ST-Link",
                    "tool": "st-flash",
                    "sudo": True,
                }
            )
        steps.append(
            {"id": "post-configure", "name": "Post-flash setup", "optional": True}
        )
        profile["flash_steps"] = steps

        # Preserve scooter-specific metadata in extra-friendly top-level keys
        if s.get("protocol"):
            profile["protocol"] = s["protocol"]
        if s.get("shfw_supported"):
            profile["shfw_supported"] = s["shfw_supported"].lower() in (
                "yes",
                "true",
                "1",
            )

        dest.write_text(
            yaml.dump(profile, default_flow_style=False, sort_keys=False)
        )
        created.append(f"scooter/{filename}")

    return created


def migrate_ebikes_cfg() -> list[str]:
    """Migrate ebikes.cfg entries to YAML profiles under profiles/ebike/."""
    import yaml

    from web.routes.ebike import parse_ebikes_cfg

    ebikes = parse_ebikes_cfg()
    if not ebikes:
        return []

    out_dir = PROFILES_DIR / "ebike"
    out_dir.mkdir(parents=True, exist_ok=True)
    created = []

    for e in ebikes:
        filename = f"{e['id']}.yaml"
        dest = out_dir / filename
        if dest.exists():
            continue

        method = e.get("flash_method", "")
        flash_tool = (
            "stlink"
            if "stlink" in method
            else "uart"
            if "uart" in method
            else "usb"
            if "usb" in method
            else ""
        )
        status = e.get("support_status", "supported")
        if status not in VALID_SUPPORT_STATUSES:
            status = "experimental"

        profile = {
            "id": e["id"],
            "name": e.get("label", e["id"]),
            "brand": e.get("brand", ""),
            "category": "ebike",
            "flash_tool": flash_tool,
            "flash_method": method,
            "support_status": status,
        }
        if e.get("controller"):
            profile["controller"] = e["controller"]
        if e.get("notes"):
            profile["notes"] = e["notes"]

        firmware = []
        if e.get("fw_url"):
            firmware.append(
                {
                    "id": e.get("fw_project") or "open-fw",
                    "name": e.get("fw_project") or "Open firmware",
                    "url": e["fw_url"],
                    "type": "cfw",
                    "tags": ["ebike", e.get("controller", "")],
                }
            )
        if firmware:
            profile["firmware"] = firmware

        steps = [
            {"id": "download", "name": "Download firmware"},
            {"id": "verify", "name": "Verify integrity"},
            {"id": "backup", "name": "Backup current firmware", "optional": True},
        ]
        if "stlink" in method:
            steps.append(
                {
                    "id": "flash-stlink",
                    "name": "Flash via ST-Link",
                    "tool": "st-flash",
                    "sudo": True,
                }
            )
        if "uart" in method:
            steps.append(
                {"id": "flash-uart", "name": "Flash via UART", "tool": "uart"}
            )
        if "usb" in method:
            steps.append(
                {"id": "flash-usb", "name": "Flash via USB", "tool": "usb"}
            )
        steps.append(
            {"id": "post-configure", "name": "Post-flash setup", "optional": True}
        )
        profile["flash_steps"] = steps

        dest.write_text(
            yaml.dump(profile, default_flow_style=False, sort_keys=False)
        )
        created.append(f"ebike/{filename}")

    return created


def migrate_t2_cfg() -> list[str]:
    """Migrate t2.cfg entries to YAML profiles under profiles/t2/."""
    import yaml

    from web.routes.t2 import parse_t2_cfg

    macs = parse_t2_cfg()
    if not macs:
        return []

    out_dir = PROFILES_DIR / "t2"
    out_dir.mkdir(parents=True, exist_ok=True)
    created = []

    for m in macs:
        filename = f"{m['id']}.yaml"
        dest = out_dir / filename
        if dest.exists():
            continue

        profile = {
            "id": m["id"],
            "name": m.get("label", m["id"]),
            "brand": "Apple",
            "category": "laptop",
            "model": m.get("model", ""),
            "flash_tool": "apple-t2-tool",
            "flash_method": "dfu",
            "usb_vid": "05ac",
            "usb_pid": "1881",
        }
        if m.get("board_id"):
            profile["board_id"] = m["board_id"]
        if m.get("notes"):
            profile["notes"] = m["notes"]

        firmware = []
        if m.get("bridge_os_url"):
            firmware.append(
                {
                    "id": "bridge-os",
                    "name": "BridgeOS",
                    "url": m["bridge_os_url"],
                    "type": "stock",
                    "tags": ["apple", "t2"],
                }
            )
        if firmware:
            profile["firmware"] = firmware

        profile["flash_steps"] = [
            {"id": "download", "name": "Download BridgeOS"},
            {"id": "verify", "name": "Verify integrity"},
            {
                "id": "enter-dfu",
                "name": "Enter DFU mode",
                "description": "Hold power + right shift + left option + left ctrl for 10s",
            },
            {
                "id": "flash",
                "name": "Restore via apple-t2-tool",
                "tool": "apple-t2-tool",
                "sudo": True,
            },
            {"id": "post-configure", "name": "Post-flash setup", "optional": True},
        ]

        dest.write_text(
            yaml.dump(profile, default_flow_style=False, sort_keys=False)
        )
        created.append(f"t2/{filename}")

    return created


def migrate_medicat_cfg() -> list[str]:
    """Migrate medicat.cfg entries to YAML profiles under profiles/medicat/."""
    import yaml

    from web.routes.medicat import parse_medicat_cfg

    entries = parse_medicat_cfg()
    if not entries:
        return []

    out_dir = PROFILES_DIR / "medicat"
    out_dir.mkdir(parents=True, exist_ok=True)
    created = []

    for m in entries:
        filename = f"{m['id']}.yaml"
        dest = out_dir / filename
        if dest.exists():
            continue

        profile = {
            "id": m["id"],
            "name": m.get("label", m["id"]),
            "category": "other",
            "flash_tool": "ventoy" if m.get("ventoy_required") else "dd",
            "flash_method": "usb-image",
            "min_usb_gb": m.get("min_usb_gb", 32),
            "ventoy_required": bool(m.get("ventoy_required")),
        }
        if m.get("notes"):
            profile["notes"] = m["notes"]

        profile["flash_steps"] = [
            {"id": "download", "name": "Download Medicat ISO"},
            {"id": "verify", "name": "Verify integrity"},
            {
                "id": "prepare-usb",
                "name": "Prepare USB drive (Ventoy)" if m.get("ventoy_required") else "Prepare USB drive",
                "tool": "ventoy" if m.get("ventoy_required") else "dd",
                "sudo": True,
            },
            {"id": "post-configure", "name": "Post-flash setup", "optional": True},
        ]

        dest.write_text(
            yaml.dump(profile, default_flow_style=False, sort_keys=False)
        )
        created.append(f"medicat/{filename}")

    return created


def migrate_all() -> dict[str, list[str]]:
    """Run all migrations. Returns {source: [created files]}."""
    results = {}
    for source, fn in (
        ("devices.cfg", migrate_devices_cfg),
        ("microcontrollers.cfg", migrate_microcontrollers_cfg),
        ("scooters.cfg", migrate_scooters_cfg),
        ("ebikes.cfg", migrate_ebikes_cfg),
        ("t2.cfg", migrate_t2_cfg),
        ("medicat.cfg", migrate_medicat_cfg),
    ):
        try:
            created = fn()
        except Exception as e:
            log.error("Migration of %s failed: %s", source, e)
            continue
        if created:
            results[source] = created
    return results
