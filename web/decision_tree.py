"""Xiaomi device recovery decision tree.

Given the current device state (mode, firmware, hardware, bootloader,
available ROMs), returns the recommended action path and compatible
next steps.

The tree is evaluated server-side and returned as a JSON structure
that the frontend renders as a guided flow.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DeviceState:
    """Snapshot of a connected device's current state."""

    mode: str = ""  # sideload, fastboot, recovery, device
    serial: str = ""
    display_name: str = ""

    # Hardware layer (physical device)
    hw_model: str = ""  # M2101K9AG
    hw_codename: str = ""  # courbet
    hw_name: str = ""  # Mi 11 Lite 4G

    # Firmware layer (what's installed)
    fw_device: str = ""  # renoir_eea_global
    fw_version: str = ""  # V14.0.9.0.TKIEUXM
    fw_codename: str = ""  # renoir
    fw_region: str = ""  # EU
    fw_region_label: str = ""  # EEA (European)
    fw_rom_code: str = ""  # EUXM

    # Bootloader layer
    bl_locked: bool = True
    bl_unlock_ability: bool = False

    # Derived
    is_cross_flashed: bool = False


@dataclass
class Step:
    """A single step in the decision tree."""

    id: str
    title: str
    description: str
    action: str = ""  # API endpoint or UI action
    status: str = "available"  # available, blocked, done, active, warning
    reason: str = ""  # why blocked / warning
    children: list[Step] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


def evaluate(state: DeviceState, available_roms: list[dict] = None) -> dict:
    """Evaluate the decision tree for the given device state.

    Returns a dict with:
        - diagnosis: what's wrong with the device
        - recommended_path: ordered list of steps to take
        - all_paths: all possible paths with compatibility info
        - warnings: any warnings to show
    """
    if available_roms is None:
        available_roms = []

    diagnosis = _diagnose(state)
    warnings = _get_warnings(state)
    paths = _build_paths(state, available_roms)
    recommended = _pick_recommended(paths, state)

    return {
        "diagnosis": diagnosis,
        "recommended_path": recommended,
        "all_paths": [_step_to_dict(p) for p in paths],
        "warnings": warnings,
        "device_state": {
            "mode": state.mode,
            "is_cross_flashed": state.is_cross_flashed,
            "bl_locked": state.bl_locked,
            "bl_unlock_ability": state.bl_unlock_ability,
            "hw_codename": state.hw_codename,
            "fw_codename": state.fw_codename,
        },
    }


def _diagnose(state: DeviceState) -> dict:
    """Determine what's wrong with the device."""
    issues = []
    severity = "info"

    if state.is_cross_flashed:
        issues.append(
            {
                "id": "cross_flash",
                "severity": "critical",
                "title": "Firmware/hardware mismatch",
                "detail": (
                    f"Hardware is {state.hw_name or state.hw_codename} ({state.hw_codename}) "
                    f"but firmware reports as {state.fw_codename}. "
                    f"Neither the correct nor the installed firmware can be flashed via MIAssistant."
                ),
            }
        )
        severity = "critical"

    if state.bl_locked:
        if state.is_cross_flashed:
            issues.append(
                {
                    "id": "locked_crossflash",
                    "severity": "critical",
                    "title": "Bootloader locked on cross-flashed device",
                    "detail": "Must unlock bootloader before flashing correct firmware.",
                }
            )
        else:
            issues.append(
                {
                    "id": "locked",
                    "severity": "warning",
                    "title": "Bootloader locked",
                    "detail": "Standard fastboot flash is blocked. MIAssistant or unlock required.",
                }
            )
            if severity != "critical":
                severity = "warning"

    if not issues:
        issues.append(
            {
                "id": "ok",
                "severity": "info",
                "title": "Device is ready",
                "detail": "Device can be flashed via the available method.",
            }
        )

    return {"issues": issues, "severity": severity}


def _get_warnings(state: DeviceState) -> list[dict]:
    """Generate warnings for the current state."""
    warnings = []

    if state.is_cross_flashed:
        warnings.append(
            {
                "type": "cross_flash",
                "message": (
                    f"This {state.hw_name or state.hw_codename} has {state.fw_codename} firmware installed. "
                    f"MIAssistant sideload will NOT work. Bootloader unlock + fastboot flash required."
                ),
            }
        )

    if state.mode == "sideload" and state.bl_locked and not state.is_cross_flashed:
        warnings.append(
            {
                "type": "region_check",
                "message": "Ensure the ROM region matches this device. Wrong region = rejected by server.",
            }
        )

    return warnings


def _build_paths(state: DeviceState, available_roms: list[dict]) -> list[Step]:
    """Build all possible action paths."""
    paths = []

    # Path 1: MIAssistant sideload (locked bootloader, matching firmware)
    if state.mode == "sideload" and not state.is_cross_flashed:
        compatible_roms = [r for r in available_roms if r.get("compatible", True)]
        sideload_step = Step(
            id="miassistant_flash",
            title="Restore stock firmware via MIAssistant",
            description="Flash an official recovery ROM through Xiaomi's proprietary protocol. Works on locked bootloaders.",
            action="/api/miassistant/sideload",
            status="available" if compatible_roms else "blocked",
            reason="" if compatible_roms else "No compatible ROMs available. Download one first.",
            metadata={"rom_count": len(compatible_roms), "requires_unlock": False},
        )
        paths.append(sideload_step)

    # Path 2: Bootloader unlock → fastboot flash
    if state.mode in ("sideload", "fastboot"):
        unlock_status = "available"
        unlock_reason = ""
        if not state.bl_locked:
            unlock_status = "done"
            unlock_reason = "Already unlocked"
        elif not state.bl_unlock_ability:
            unlock_status = "blocked"
            unlock_reason = "OEM unlocking not enabled. Requires booting into system first."

        flash_status = "available" if not state.bl_locked else "blocked"
        flash_reason = "" if not state.bl_locked else "Unlock bootloader first"

        unlock_step = Step(
            id="unlock_bootloader",
            title="Unlock bootloader",
            description="Unlock via Mi account to enable fastboot flashing. Requires internet and Xiaomi account.",
            action="/api/miassistant/unlock",
            status=unlock_status,
            reason=unlock_reason,
            metadata={
                "requires_mi_account": True,
                "may_have_wait_period": True,
                "requires_fastboot": True,
            },
            children=[
                Step(
                    id="fastboot_flash",
                    title="Flash correct firmware via fastboot",
                    description=f"Flash {state.hw_codename} firmware to restore the device.",
                    action="/api/fastboot/flash-stock",
                    status=flash_status,
                    reason=flash_reason,
                    metadata={"codename": state.hw_codename},
                ),
            ],
        )
        paths.append(unlock_step)

    # Path 3: EDL (last resort)
    edl_step = Step(
        id="edl_flash",
        title="Flash via EDL (Emergency Download)",
        description="Bypass all software locks by entering Qualcomm 9008 mode. Requires EDL cable or testpoint.",
        action="edl",
        status="available",
        reason="",
        metadata={
            "requires_edl_cable": True,
            "requires_testpoint": False,
            "bypasses_bootloader": True,
        },
    )
    paths.append(edl_step)

    # Path 4: Read device info (always available in sideload)
    if state.mode == "sideload":
        paths.append(
            Step(
                id="read_info",
                title="Read device info",
                description="Query device details via MIAssistant protocol.",
                action="/api/miassistant/info",
                status="available",
            )
        )

    # Path 5: Wipe data
    if state.mode in ("sideload", "recovery"):
        paths.append(
            Step(
                id="wipe_data",
                title="Wipe data (factory reset)",
                description="Erase user data. May fix boot loops caused by corrupt data.",
                action="format-data",
                status="available",
                metadata={"destructive": True},
            )
        )

    return paths


def _pick_recommended(paths: list[Step], state: DeviceState) -> list[dict]:
    """Pick the recommended path based on device state."""
    if state.is_cross_flashed:
        # Cross-flashed: unlock → fastboot is the only viable path
        for p in paths:
            if p.id == "unlock_bootloader":
                return [_step_to_dict(p)]
        # Fall back to EDL
        for p in paths:
            if p.id == "edl_flash":
                return [_step_to_dict(p)]

    if state.bl_locked:
        # Locked but not cross-flashed: try MIAssistant first
        for p in paths:
            if p.id == "miassistant_flash" and p.status == "available":
                return [_step_to_dict(p)]
        # No compatible ROMs: suggest unlock
        for p in paths:
            if p.id == "unlock_bootloader":
                return [_step_to_dict(p)]

    if not state.bl_locked:
        # Unlocked: fastboot flash directly
        for p in paths:
            if p.id == "unlock_bootloader":
                for child in p.children:
                    if child.id == "fastboot_flash":
                        return [_step_to_dict(child)]

    return [_step_to_dict(p) for p in paths[:1]] if paths else []


def _step_to_dict(step: Step) -> dict:
    """Convert a Step to a JSON-serializable dict."""
    return {
        "id": step.id,
        "title": step.title,
        "description": step.description,
        "action": step.action,
        "status": step.status,
        "reason": step.reason,
        "metadata": step.metadata,
        "children": [_step_to_dict(c) for c in step.children],
    }
