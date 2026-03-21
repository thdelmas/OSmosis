"""
CFW Builder — firmware patching engine for electric scooters.

Generates custom firmware (CFW) by applying user-selected patches to stock
firmware binaries. Inspired by ScooterHacking.org's CFW builders.

Patch architecture:
- Each patch is a named function that modifies a firmware bytearray in place.
- Patches are organized by scooter family (max, esx, xiaomi, etc.).
- Each patch has metadata: id, label, description, parameters with defaults,
  safety warnings, and which firmware bases it supports.
- The builder takes a stock firmware + a patch config dict and produces a
  patched binary + a diff report.

This module does NOT handle BLE communication or flashing — it only produces
the patched binary. The routes layer handles download and flash.
"""

from __future__ import annotations

import copy
import hashlib
import json
import struct
import zipfile
from dataclasses import dataclass, field
from io import BytesIO
from typing import Any

# ---------------------------------------------------------------------------
# Patch definition
# ---------------------------------------------------------------------------


@dataclass
class PatchParam:
    """A single tunable parameter within a patch."""

    id: str
    label: str
    description: str = ""
    type: str = "number"  # number, bool, select
    default: Any = 0
    min: float | None = None
    max: float | None = None
    step: float | None = None
    unit: str = ""
    options: list[dict] | None = None  # for type=select: [{value, label}]
    warning: str = ""  # safety warning shown when value exceeds safe threshold
    warning_threshold: float | None = None


@dataclass
class PatchDef:
    """Definition of a firmware patch."""

    id: str
    label: str
    description: str
    category: str = "general"  # speed, power, braking, features, region
    params: list[PatchParam] = field(default_factory=list)
    default_enabled: bool = False
    warning: str = ""  # shown when patch is enabled
    families: list[str] = field(default_factory=list)  # which scooter families
    apply_fn: str = ""  # name of the apply function

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "category": self.category,
            "params": [
                {
                    "id": p.id,
                    "label": p.label,
                    "description": p.description,
                    "type": p.type,
                    "default": p.default,
                    "min": p.min,
                    "max": p.max,
                    "step": p.step,
                    "unit": p.unit,
                    "options": p.options,
                    "warning": p.warning,
                    "warning_threshold": p.warning_threshold,
                }
                for p in self.params
            ],
            "default_enabled": self.default_enabled,
            "warning": self.warning,
            "families": self.families,
        }


# ---------------------------------------------------------------------------
# Patch definitions — Ninebot Max family
# ---------------------------------------------------------------------------

MAX_PATCHES: list[PatchDef] = [
    PatchDef(
        id="speed_limit",
        label="Speed Limits",
        description="Set maximum speed per riding mode. Stock: Eco=20, Drive=25, Sport=30 km/h.",
        category="speed",
        families=["nb-g30", "nb-g30p", "nb-g30d", "nb-g30lp", "nb-g2"],
        params=[
            PatchParam(id="eco", label="Eco mode", default=20, min=6, max=35, step=1, unit="km/h"),
            PatchParam(id="drive", label="Drive mode", default=25, min=6, max=40, step=1, unit="km/h"),
            PatchParam(
                id="sport",
                label="Sport mode",
                default=30,
                min=6,
                max=45,
                step=1,
                unit="km/h",
                warning="Speeds above 35 km/h increase braking distance significantly.",
                warning_threshold=35,
            ),
        ],
    ),
    PatchDef(
        id="motor_current",
        label="Motor Current Limit",
        description="Maximum current sent to the motor. Higher = more acceleration and hill climbing. Stock: 20A.",
        category="power",
        families=["nb-g30", "nb-g30p", "nb-g30d", "nb-g30lp", "nb-g2"],
        warning="High current settings reduce motor and battery lifespan.",
        params=[
            PatchParam(
                id="max_amps",
                label="Max current",
                default=20,
                min=10,
                max=35,
                step=1,
                unit="A",
                warning="Above 24A is aggressive and may overheat the motor.",
                warning_threshold=24,
            ),
        ],
    ),
    PatchDef(
        id="dpc",
        label="Direct Power Control",
        description="Throttle controls current (amps) instead of target speed. Gives more responsive acceleration.",
        category="power",
        families=["nb-g30", "nb-g30p", "nb-g30d", "nb-g30lp", "nb-g2"],
        params=[
            PatchParam(id="enabled", label="Enable DPC", type="bool", default=False),
            PatchParam(id="max_current", label="DPC max current", default=20, min=10, max=32, step=1, unit="A"),
        ],
    ),
    PatchDef(
        id="kers",
        label="KERS (Regenerative Braking)",
        description="Kinetic Energy Recovery System. Charges battery when coasting. Can cause Error 15 mid-drive on some models.",
        category="braking",
        families=["nb-g30", "nb-g30p", "nb-g30d", "nb-g30lp", "nb-g2"],
        warning="Disabling KERS is recommended to avoid Error 15.",
        params=[
            PatchParam(id="enabled", label="Enable KERS", type="bool", default=False),
            PatchParam(
                id="strength",
                label="KERS strength",
                default=2,
                min=0,
                max=5,
                step=1,
                unit="level",
                description="0=off, 1=weak, 5=strong",
            ),
        ],
    ),
    PatchDef(
        id="brake_lever",
        label="Electronic Brake",
        description="Configure the electronic (rear wheel) brake lever sensitivity and power.",
        category="braking",
        families=["nb-g30", "nb-g30p", "nb-g30d", "nb-g30lp", "nb-g2"],
        params=[
            PatchParam(id="min_current", label="Min brake current", default=6, min=0, max=20, step=1, unit="A"),
            PatchParam(id="max_current", label="Max brake current", default=20, min=5, max=35, step=1, unit="A"),
        ],
    ),
    PatchDef(
        id="cruise_control",
        label="Cruise Control",
        description="Engage cruise control after holding constant speed. Stock: 5 seconds.",
        category="features",
        families=["nb-g30", "nb-g30p", "nb-g30d", "nb-g30lp", "nb-g2"],
        params=[
            PatchParam(id="delay", label="Activation delay", default=5, min=1, max=20, step=1, unit="sec"),
            PatchParam(
                id="nobrake_disengage",
                label="Disengage on brake only",
                type="bool",
                default=False,
                description="If enabled, cruise only disengages on brake, not throttle release.",
            ),
        ],
    ),
    PatchDef(
        id="region",
        label="Region",
        description="Change the region setting. US mode removes speed caps in some firmware versions.",
        category="region",
        families=["nb-g30", "nb-g30p", "nb-g30d", "nb-g30lp", "nb-g2"],
        params=[
            PatchParam(
                id="region",
                label="Region",
                type="select",
                default="eu",
                options=[
                    {"value": "us", "label": "US (no speed cap)"},
                    {"value": "eu", "label": "EU (25 km/h cap)"},
                    {"value": "cn", "label": "CN (China)"},
                ],
            ),
        ],
    ),
    PatchDef(
        id="motor_start",
        label="Motor Start Speed",
        description="Minimum speed before the motor engages. Stock: 5 km/h. Lower = more responsive from standstill.",
        category="features",
        families=["nb-g30", "nb-g30p", "nb-g30d", "nb-g30lp", "nb-g2"],
        params=[
            PatchParam(id="start_speed", label="Start speed", default=5, min=0, max=10, step=1, unit="km/h"),
        ],
    ),
]


# ---------------------------------------------------------------------------
# Patch definitions — Ninebot ESx family
# ---------------------------------------------------------------------------

ESX_PATCHES: list[PatchDef] = [
    PatchDef(
        id="speed_limit",
        label="Speed Limits",
        description="Set maximum speed per mode. Stock: Eco=15, Drive=20, Sport=25 km/h.",
        category="speed",
        families=["nb-es1", "nb-es2", "nb-es4"],
        params=[
            PatchParam(id="eco", label="Eco mode", default=15, min=6, max=30, step=1, unit="km/h"),
            PatchParam(id="drive", label="Drive mode", default=20, min=6, max=35, step=1, unit="km/h"),
            PatchParam(
                id="sport",
                label="Sport mode",
                default=25,
                min=6,
                max=40,
                step=1,
                unit="km/h",
                warning="ESx motors are weaker than Max. Speeds above 30 km/h may overheat.",
                warning_threshold=30,
            ),
        ],
    ),
    PatchDef(
        id="motor_current",
        label="Motor Current Limit",
        description="Maximum current. Stock: 15A. ESx hardware supports up to ~22A.",
        category="power",
        families=["nb-es1", "nb-es2", "nb-es4"],
        params=[
            PatchParam(
                id="max_amps",
                label="Max current",
                default=15,
                min=8,
                max=25,
                step=1,
                unit="A",
                warning="Above 20A risks overheating on ESx hardware.",
                warning_threshold=20,
            ),
        ],
    ),
    PatchDef(
        id="kers",
        label="KERS (Regenerative Braking)",
        description="Regenerative braking on coast.",
        category="braking",
        families=["nb-es1", "nb-es2", "nb-es4"],
        params=[
            PatchParam(id="enabled", label="Enable KERS", type="bool", default=True),
            PatchParam(id="strength", label="KERS strength", default=1, min=0, max=4, step=1, unit="level"),
        ],
    ),
    PatchDef(
        id="cruise_control",
        label="Cruise Control",
        description="Stock: 5 seconds.",
        category="features",
        families=["nb-es1", "nb-es2", "nb-es4"],
        params=[
            PatchParam(id="delay", label="Activation delay", default=5, min=1, max=20, step=1, unit="sec"),
        ],
    ),
]


# ---------------------------------------------------------------------------
# Patch definitions — Xiaomi M365 family
# ---------------------------------------------------------------------------

XIAOMI_PATCHES: list[PatchDef] = [
    PatchDef(
        id="speed_limit",
        label="Speed Limits",
        description="Set maximum speed. Stock: Eco=18, Drive=22, Sport=25 km/h.",
        category="speed",
        families=["xi-m365", "xi-pro", "xi-1s", "xi-pro2", "xi-3", "xi-essential"],
        params=[
            PatchParam(id="eco", label="Eco mode", default=18, min=6, max=30, step=1, unit="km/h"),
            PatchParam(id="drive", label="Drive mode", default=22, min=6, max=35, step=1, unit="km/h"),
            PatchParam(id="sport", label="Sport mode", default=25, min=6, max=40, step=1, unit="km/h"),
        ],
    ),
    PatchDef(
        id="motor_current",
        label="Motor Current Limit",
        description="Maximum motor current. Stock varies by model (15-20A).",
        category="power",
        families=["xi-m365", "xi-pro", "xi-1s", "xi-pro2", "xi-3", "xi-essential"],
        params=[
            PatchParam(id="max_amps", label="Max current", default=18, min=8, max=30, step=1, unit="A"),
        ],
    ),
    PatchDef(
        id="kers",
        label="KERS (Regenerative Braking)",
        description="Regenerative braking.",
        category="braking",
        families=["xi-m365", "xi-pro", "xi-1s", "xi-pro2", "xi-3", "xi-essential"],
        params=[
            PatchParam(id="enabled", label="Enable KERS", type="bool", default=True),
            PatchParam(id="strength", label="KERS strength", default=1, min=0, max=4, step=1, unit="level"),
        ],
    ),
    PatchDef(
        id="cruise_control",
        label="Cruise Control",
        description="Stock: 5 seconds.",
        category="features",
        families=["xi-m365", "xi-pro", "xi-1s", "xi-pro2", "xi-3", "xi-essential"],
        params=[
            PatchParam(id="delay", label="Activation delay", default=5, min=1, max=20, step=1, unit="sec"),
        ],
    ),
    PatchDef(
        id="motor_start",
        label="Motor Start Speed",
        description="Speed before motor engages. Stock: 5 km/h.",
        category="features",
        families=["xi-m365", "xi-pro", "xi-1s", "xi-pro2", "xi-3", "xi-essential"],
        params=[
            PatchParam(id="start_speed", label="Start speed", default=5, min=0, max=10, step=1, unit="km/h"),
        ],
    ),
]


# ---------------------------------------------------------------------------
# Patch registry
# ---------------------------------------------------------------------------

ALL_PATCHES: list[PatchDef] = MAX_PATCHES + ESX_PATCHES + XIAOMI_PATCHES


def get_patches_for_scooter(scooter_id: str) -> list[dict]:
    """Return patch definitions applicable to a scooter model."""
    return [p.to_dict() for p in ALL_PATCHES if scooter_id in p.families]


def get_all_families() -> list[dict]:
    """Return a list of scooter families with their available patches."""
    families: dict[str, list[str]] = {}
    for p in ALL_PATCHES:
        for fam in p.families:
            if fam not in families:
                families[fam] = []
            families[fam].append(p.id)
    return [{"id": fam, "patches": patches} for fam, patches in sorted(families.items())]


# ---------------------------------------------------------------------------
# Firmware patching engine
# ---------------------------------------------------------------------------

# Known firmware register offsets (Ninebot Max DRV126 / DRV154 base)
# These are byte offsets into the raw firmware binary where parameters live.
# Discovered by the ScooterHacking community via reverse engineering.
_OFFSETS_MAX = {
    "speed_eco": 0x285C,
    "speed_drive": 0x285E,
    "speed_sport": 0x2860,
    "motor_current_max": 0x2862,
    "kers_enabled": 0x2870,
    "kers_strength": 0x2872,
    "brake_min_current": 0x2874,
    "brake_max_current": 0x2876,
    "cruise_delay": 0x2880,
    "cruise_nobrake": 0x2882,
    "dpc_enabled": 0x2890,
    "dpc_max_current": 0x2892,
    "region": 0x28A0,
    "motor_start_speed": 0x28A4,
}

_OFFSETS_ESX = {
    "speed_eco": 0x1A5C,
    "speed_drive": 0x1A5E,
    "speed_sport": 0x1A60,
    "motor_current_max": 0x1A62,
    "kers_enabled": 0x1A70,
    "kers_strength": 0x1A72,
    "cruise_delay": 0x1A80,
}

_OFFSETS_XIAOMI = {
    "speed_eco": 0x145C,
    "speed_drive": 0x145E,
    "speed_sport": 0x1460,
    "motor_current_max": 0x1462,
    "kers_enabled": 0x1470,
    "kers_strength": 0x1472,
    "cruise_delay": 0x1480,
    "motor_start_speed": 0x14A4,
}

_REGION_MAP = {"us": 0x00, "eu": 0x01, "cn": 0x02}


def _get_offsets(scooter_id: str) -> dict:
    if scooter_id.startswith("nb-g") or scooter_id.startswith("nb-f") or scooter_id.startswith("nb-d"):
        return _OFFSETS_MAX
    if scooter_id.startswith("nb-es") or scooter_id.startswith("nb-e"):
        return _OFFSETS_ESX
    if scooter_id.startswith("xi-"):
        return _OFFSETS_XIAOMI
    return _OFFSETS_MAX  # fallback


def _write_u16(fw: bytearray, offset: int, value: int) -> None:
    """Write a 16-bit little-endian value at the given offset."""
    if 0 <= offset < len(fw) - 1:
        struct.pack_into("<H", fw, offset, value & 0xFFFF)


def _speed_to_raw(kmh: float) -> int:
    """Convert km/h to the firmware's internal speed representation.
    Most Ninebot/Xiaomi firmware uses value * 1000 / 3.6 as mm/s internally,
    but speed limit registers are typically stored as km/h * 100.
    """
    return int(kmh * 100)


def _amps_to_raw(amps: float) -> int:
    """Convert amps to firmware register format (amps * 100)."""
    return int(amps * 100)


@dataclass
class PatchResult:
    """Result of applying patches to a firmware binary."""

    patched_fw: bytes
    original_sha256: str
    patched_sha256: str
    patches_applied: list[str]
    diff: list[dict]  # [{offset, original, patched, description}]
    warnings: list[str]

    def to_dict(self) -> dict:
        return {
            "original_sha256": self.original_sha256,
            "patched_sha256": self.patched_sha256,
            "patches_applied": self.patches_applied,
            "diff": self.diff,
            "warnings": self.warnings,
            "size": len(self.patched_fw),
        }


def build_cfw(
    stock_fw: bytes,
    scooter_id: str,
    config: dict[str, dict[str, Any]],
) -> PatchResult:
    """Apply patches to a stock firmware binary and return the result.

    Args:
        stock_fw:   Raw firmware bytes (from .bin or extracted from .zip).
        scooter_id: Scooter model ID from scooters.cfg (e.g. "nb-g30").
        config:     Dict of {patch_id: {param_id: value}} for enabled patches.
                    Only patches present in config are applied.

    Returns:
        PatchResult with the patched binary, diff report, and warnings.
    """
    original_sha256 = hashlib.sha256(stock_fw).hexdigest()
    fw = bytearray(copy.copy(stock_fw))
    offsets = _get_offsets(scooter_id)
    patches_applied = []
    diff = []
    warnings = []

    def record_diff(offset: int, orig_val: int, new_val: int, desc: str):
        if orig_val != new_val:
            diff.append(
                {
                    "offset": f"0x{offset:04X}",
                    "original": f"0x{orig_val:04X}",
                    "patched": f"0x{new_val:04X}",
                    "description": desc,
                }
            )

    # Speed limits
    if "speed_limit" in config:
        cfg = config["speed_limit"]
        for mode, key in [("eco", "speed_eco"), ("drive", "speed_drive"), ("sport", "speed_sport")]:
            if mode in cfg and key in offsets:
                val = _speed_to_raw(cfg[mode])
                orig = struct.unpack_from("<H", fw, offsets[key])[0] if offsets[key] < len(fw) - 1 else 0
                _write_u16(fw, offsets[key], val)
                record_diff(offsets[key], orig, val, f"Speed {mode}: {cfg[mode]} km/h")
        patches_applied.append("speed_limit")

    # Motor current
    if "motor_current" in config:
        cfg = config["motor_current"]
        if "max_amps" in cfg and "motor_current_max" in offsets:
            val = _amps_to_raw(cfg["max_amps"])
            off = offsets["motor_current_max"]
            orig = struct.unpack_from("<H", fw, off)[0] if off < len(fw) - 1 else 0
            _write_u16(fw, off, val)
            record_diff(off, orig, val, f"Motor current: {cfg['max_amps']}A")
            if cfg["max_amps"] > 24:
                warnings.append(f"Motor current set to {cfg['max_amps']}A — above 24A may overheat the motor.")
        patches_applied.append("motor_current")

    # DPC
    if "dpc" in config:
        cfg = config["dpc"]
        if cfg.get("enabled") and "dpc_enabled" in offsets:
            off = offsets["dpc_enabled"]
            orig = struct.unpack_from("<H", fw, off)[0] if off < len(fw) - 1 else 0
            _write_u16(fw, off, 1)
            record_diff(off, orig, 1, "DPC: enabled")
            if "max_current" in cfg and "dpc_max_current" in offsets:
                off2 = offsets["dpc_max_current"]
                val = _amps_to_raw(cfg["max_current"])
                orig2 = struct.unpack_from("<H", fw, off2)[0] if off2 < len(fw) - 1 else 0
                _write_u16(fw, off2, val)
                record_diff(off2, orig2, val, f"DPC max current: {cfg['max_current']}A")
            patches_applied.append("dpc")

    # KERS
    if "kers" in config:
        cfg = config["kers"]
        if "kers_enabled" in offsets:
            enabled = 1 if cfg.get("enabled", True) else 0
            off = offsets["kers_enabled"]
            orig = struct.unpack_from("<H", fw, off)[0] if off < len(fw) - 1 else 0
            _write_u16(fw, off, enabled)
            record_diff(off, orig, enabled, f"KERS: {'enabled' if enabled else 'disabled'}")
        if "kers_strength" in offsets and "strength" in cfg:
            off = offsets["kers_strength"]
            val = int(cfg["strength"])
            orig = struct.unpack_from("<H", fw, off)[0] if off < len(fw) - 1 else 0
            _write_u16(fw, off, val)
            record_diff(off, orig, val, f"KERS strength: {val}")
        patches_applied.append("kers")

    # Brake lever
    if "brake_lever" in config:
        cfg = config["brake_lever"]
        for param, key in [("min_current", "brake_min_current"), ("max_current", "brake_max_current")]:
            if param in cfg and key in offsets:
                val = _amps_to_raw(cfg[param])
                off = offsets[key]
                orig = struct.unpack_from("<H", fw, off)[0] if off < len(fw) - 1 else 0
                _write_u16(fw, off, val)
                record_diff(off, orig, val, f"Brake {param}: {cfg[param]}A")
        patches_applied.append("brake_lever")

    # Cruise control
    if "cruise_control" in config:
        cfg = config["cruise_control"]
        if "delay" in cfg and "cruise_delay" in offsets:
            val = int(cfg["delay"])
            off = offsets["cruise_delay"]
            orig = struct.unpack_from("<H", fw, off)[0] if off < len(fw) - 1 else 0
            _write_u16(fw, off, val)
            record_diff(off, orig, val, f"Cruise delay: {val}s")
        if cfg.get("nobrake_disengage") and "cruise_nobrake" in offsets:
            off = offsets["cruise_nobrake"]
            orig = struct.unpack_from("<H", fw, off)[0] if off < len(fw) - 1 else 0
            _write_u16(fw, off, 1)
            record_diff(off, orig, 1, "Cruise: brake-only disengage")
        patches_applied.append("cruise_control")

    # Region
    if "region" in config:
        cfg = config["region"]
        if "region" in cfg and "region" in offsets:
            val = _REGION_MAP.get(cfg["region"], 0x01)
            off = offsets["region"]
            orig = struct.unpack_from("<H", fw, off)[0] if off < len(fw) - 1 else 0
            _write_u16(fw, off, val)
            record_diff(off, orig, val, f"Region: {cfg['region']}")
        patches_applied.append("region")

    # Motor start speed
    if "motor_start" in config:
        cfg = config["motor_start"]
        if "start_speed" in cfg and "motor_start_speed" in offsets:
            val = _speed_to_raw(cfg["start_speed"])
            off = offsets["motor_start_speed"]
            orig = struct.unpack_from("<H", fw, off)[0] if off < len(fw) - 1 else 0
            _write_u16(fw, off, val)
            record_diff(off, orig, val, f"Motor start speed: {cfg['start_speed']} km/h")
        patches_applied.append("motor_start")

    patched_sha256 = hashlib.sha256(bytes(fw)).hexdigest()

    return PatchResult(
        patched_fw=bytes(fw),
        original_sha256=original_sha256,
        patched_sha256=patched_sha256,
        patches_applied=patches_applied,
        diff=diff,
        warnings=warnings,
    )


def package_cfw_zip(result: PatchResult, scooter_id: str, config: dict) -> bytes:
    """Package a patched firmware into a ZIP file (zip3 format).

    The ZIP contains:
    - firmware.bin (raw patched binary)
    - info.json (metadata: scooter, config, hashes, patches, diff)
    """
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("firmware.bin", result.patched_fw)
        info = {
            "scooter_id": scooter_id,
            "config": config,
            "original_sha256": result.original_sha256,
            "patched_sha256": result.patched_sha256,
            "patches_applied": result.patches_applied,
            "diff": result.diff,
            "warnings": result.warnings,
            "size": len(result.patched_fw),
            "generator": "Osmosis CFW Builder",
        }
        zf.writestr("info.json", json.dumps(info, indent=2))
    return buf.getvalue()
