"""Xiaomi MIAssistant protocol helpers and device identification."""

from web.core import parse_devices_cfg

# Xiaomi model -> (codename, friendly name) lookup for sideload-mode
# identification.  In MIAssistant sideload mode ``adb shell getprop`` is
# unavailable, so we rely on the USB serial string which often contains
# the model number, or the user supplies the codename/model explicitly.
# IMPORTANT: M2101K9AG (with A) = Mi 11 Lite 4G (courbet, SD732G)
#            M2101K9G  (no A)  = Mi 11 Lite 5G (renoir, SD780G)
# The 'A' suffix is critical — these are completely different devices.
XIAOMI_MODELS: dict[str, tuple[str, str]] = {
    "M2101K9AG": ("courbet", "Mi 11 Lite 4G"),
    "M2101K9AI": ("courbet", "Mi 11 Lite 4G"),
    "M2101K9G": ("renoir", "Mi 11 Lite 5G"),
    "M2101K9R": ("renoir", "Mi 11 Lite 5G"),
    "M2101K9C": ("renoir", "Mi 11 Lite 5G"),
}

# Xiaomi region code mapping: device identifier suffix -> (region_code, region_label)
# The device reports e.g. "renoir_eea_global" but the ROM code differs.
XIAOMI_REGIONS = {
    "global": ("MI", "Global"),
    "eea_global": ("EU", "EEA (European)"),
    "cn": ("CN", "China"),
    "in_global": ("IN", "India"),
    "ru_global": ("RU", "Russia"),
    "jp_global": ("JP", "Japan"),
    "tw_global": ("TW", "Taiwan"),
}

# ROM code patterns per region for filename matching
REGION_ROM_CODES = {
    "MI": "MIXM",
    "EU": "EUXM",
    "CN": "CNXM",
    "IN": "INXM",
    "RU": "RUXM",
    "JP": "JPXM",
    "TW": "TWXM",
}


def identify_xiaomi_sideload(serial: str) -> dict | None:
    """Try to identify a Xiaomi device from its ADB sideload serial.

    When a Xiaomi device enters MIAssistant sideload mode the serial
    reported by ``adb devices`` is often the USB serial which may embed
    the model number (e.g. ``M2101K9G``).  We also fall back to
    ``devices.cfg`` matching.
    """
    upper = serial.upper()
    for model, (codename, name) in XIAOMI_MODELS.items():
        if model in upper:
            return {
                "model": model,
                "codename": codename,
                "display_name": f"Xiaomi {name}",
            }

    for dev in parse_devices_cfg():
        if (
            dev["codename"].lower() == serial.lower()
            or dev["model"].lower() == serial.lower()
        ):
            return {
                "model": dev["model"],
                "codename": dev["codename"],
                "display_name": dev["label"],
            }

    return None


def parse_device_info(output: str) -> dict:
    """Parse MiAssistantTool option 1 output into a dict."""
    info = {}
    for line in output.strip().splitlines():
        if ": " in line:
            key, val = line.split(": ", 1)
            info[key.strip()] = val.strip()
    return info


def detect_region(device_str: str, version_str: str) -> tuple[str, str]:
    """Detect the ROM region code from device identifier and version.

    Returns (region_code, region_label) e.g. ("MI", "Global").
    """
    device_lower = device_str.lower()
    for suffix, (code, label) in XIAOMI_REGIONS.items():
        if device_lower.endswith(suffix):
            if version_str:
                rom_code = REGION_ROM_CODES.get(code, "")
                if rom_code and rom_code not in version_str:
                    for c, rc in REGION_ROM_CODES.items():
                        if rc in version_str:
                            for _s, (cc, ll) in XIAOMI_REGIONS.items():
                                if cc == c:
                                    return c, ll
            return code, label

    if version_str:
        for code, rom_code in REGION_ROM_CODES.items():
            if rom_code in version_str:
                for _suffix, (c, label) in XIAOMI_REGIONS.items():
                    if c == code:
                        return code, label

    return "MI", "Global"
