"""Declarative device profiles — structured YAML definitions for any device.

A device profile is a YAML file in profiles/ that declares everything OSmosis
needs to flash, verify, and configure a device:

    id, name, brand, category, flash_tool, firmware sources, checksums,
    partition layout, required privileges, and post-flash steps.

Adding a new device = adding a YAML file. No Python code changes needed.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)

PROFILES_DIR = Path(__file__).resolve().parent.parent / "profiles"


@dataclass
class FirmwareSource:
    """A firmware image available for a device."""

    id: str  # e.g. "lineageos", "stock", "twrp"
    name: str
    url: str = ""
    ipfs_cid: str = ""
    sha256: str = ""
    version: str = ""
    type: str = "rom"  # rom, recovery, stock, addon, bootloader
    tags: list[str] = field(default_factory=list)
    mirrors: list[str] = field(
        default_factory=list
    )  # alternative URLs (ftp, http mirrors, etc.)


@dataclass
class FlashStep:
    """A single step in a flash workflow."""

    id: str  # e.g. "download", "verify", "flash", "post-configure"
    name: str
    command: str = (
        ""  # shell command template, e.g. "heimdall flash --RECOVERY {file}"
    )
    tool: str = ""  # required tool, e.g. "heimdall", "fastboot", "adb"
    sudo: bool = False
    optional: bool = False
    description: str = ""


@dataclass
class PostFlashTask:
    """A post-flash configuration task."""

    id: str
    name: str
    type: str = "shell"  # shell, adb, ansible
    command: str = ""
    playbook: str = ""  # path to ansible playbook
    description: str = ""


@dataclass
class DeviceProfile:
    """Complete device profile — everything needed to flash and configure."""

    id: str
    name: str
    brand: str = ""
    category: str = (
        "phone"  # phone, tablet, sbc, scooter, ebike, router, mcu, etc.
    )
    model: str = ""
    codename: str = ""

    # Detection
    usb_vid: str = ""
    usb_pid: str = ""
    adb_props: dict[str, str] = field(default_factory=dict)

    # Flash configuration
    flash_tool: str = ""  # heimdall, fastboot, adb, esptool, stlink, etc.
    flash_method: str = ""  # sideload, download-mode, dfu, serial, ble, etc.
    partitions: list[str] = field(
        default_factory=list
    )  # e.g. ["boot", "recovery", "system"]

    # Firmware sources
    firmware: list[FirmwareSource] = field(default_factory=list)

    # Flash workflow steps
    flash_steps: list[FlashStep] = field(default_factory=list)

    # Post-flash tasks
    post_flash: list[PostFlashTask] = field(default_factory=list)

    # Flags
    requires_unlock: bool = False
    support_status: str = "supported"  # supported, experimental, not-supported
    notes: str = ""

    # Extra YAML fields not modelled above (variants, known_issues, sensors, etc.)
    extra: dict = field(default_factory=dict)


def _parse_firmware(raw: list[dict] | None) -> list[FirmwareSource]:
    if not raw:
        return []
    return [
        FirmwareSource(
            **{
                k: v
                for k, v in item.items()
                if k in FirmwareSource.__dataclass_fields__
            }
        )
        for item in raw
    ]


def _parse_flash_steps(raw: list[dict] | None) -> list[FlashStep]:
    if not raw:
        return []
    return [
        FlashStep(
            **{
                k: v
                for k, v in item.items()
                if k in FlashStep.__dataclass_fields__
            }
        )
        for item in raw
    ]


def _parse_post_flash(raw: list[dict] | None) -> list[PostFlashTask]:
    if not raw:
        return []
    return [
        PostFlashTask(
            **{
                k: v
                for k, v in item.items()
                if k in PostFlashTask.__dataclass_fields__
            }
        )
        for item in raw
    ]


def load_profile(path: Path) -> DeviceProfile | None:
    """Load a single device profile from a YAML file."""
    try:
        import yaml

        data = yaml.safe_load(path.read_text())
        if not isinstance(data, dict):
            log.warning("Profile %s is not a dict, skipping", path)
            return None

        firmware = _parse_firmware(data.pop("firmware", None))
        flash_steps = _parse_flash_steps(data.pop("flash_steps", None))
        post_flash = _parse_post_flash(data.pop("post_flash", None))

        # Separate known dataclass fields from extra YAML-specific ones
        known = set(DeviceProfile.__dataclass_fields__) - {"extra"}
        filtered = {k: v for k, v in data.items() if k in known}
        extra = {k: v for k, v in data.items() if k not in known}

        return DeviceProfile(
            **filtered,
            firmware=firmware,
            flash_steps=flash_steps,
            post_flash=post_flash,
            extra=extra,
        )
    except Exception as e:
        log.error("Failed to load profile %s: %s", path, e)
        return None


def load_all_profiles() -> list[DeviceProfile]:
    """Load all device profiles from the profiles/ directory."""
    if not PROFILES_DIR.is_dir():
        PROFILES_DIR.mkdir(parents=True, exist_ok=True)
        return []

    profiles = []
    for yaml_file in sorted(PROFILES_DIR.glob("**/*.yaml")) + sorted(
        PROFILES_DIR.glob("**/*.yml")
    ):
        profile = load_profile(yaml_file)
        if profile:
            profiles.append(profile)
    return profiles


def get_profile(device_id: str) -> DeviceProfile | None:
    """Look up a profile by device ID."""
    for p in load_all_profiles():
        if p.id == device_id:
            return p
    return None


def profile_to_dict(p: DeviceProfile) -> dict:
    """Convert a DeviceProfile to a JSON-serializable dict."""
    from dataclasses import asdict

    return asdict(p)
