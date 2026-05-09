"""End-to-end test: dropping a YAML profile must register a new device.

This validates the 12.2 design promise — "adding a device means adding a file,
not editing Python code." Each parse_*_cfg() should pick up profile YAMLs
without any other change.
"""

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web import core, device_profile


@pytest.fixture
def isolated_profiles(tmp_path, monkeypatch):
    """Point the profile loader at an empty tmp dir for the duration of the test."""
    monkeypatch.setattr(device_profile, "PROFILES_DIR", tmp_path)
    return tmp_path


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data, sort_keys=False))


# ---------------------------------------------------------------------------
# Each parser must surface a profile-only device alongside .cfg entries
# ---------------------------------------------------------------------------


def test_devices_parser_picks_up_yaml_only_phone(isolated_profiles):
    _write(
        isolated_profiles / "ghostphone-1.yaml",
        {
            "id": "ghost-1",
            "name": "Ghost Phone 1",
            "brand": "Ghost",
            "category": "phone",
            "model": "GP-1",
            "codename": "ghost",
            "firmware": [
                {"id": "lineageos", "name": "LineageOS", "url": "https://x/rom.zip", "type": "rom"},
                {"id": "twrp", "name": "TWRP", "url": "https://x/twrp.img", "type": "recovery"},
            ],
        },
    )
    devs = core.parse_devices_cfg()
    match = next((d for d in devs if d["id"] == "ghost-1"), None)
    assert match is not None, "profile-only device must appear in parse_devices_cfg()"
    assert match["label"] == "Ghost Phone 1"
    assert match["rom_url"] == "https://x/rom.zip"
    assert match["twrp_url"] == "https://x/twrp.img"


def test_scooters_parser_picks_up_yaml_only_scooter(isolated_profiles):
    _write(
        isolated_profiles / "scooter" / "ghost-scoot.yaml",
        {
            "id": "ghost-scoot",
            "name": "Ghost Scooter",
            "brand": "Ghost",
            "category": "scooter",
            "flash_method": "ble",
            "protocol": "ninebot",
            "shfw_supported": True,
            "firmware": [
                {"id": "cfw", "name": "CFW", "url": "https://x/cfw.bin", "type": "cfw"}
            ],
        },
    )
    from web.routes.scooter import parse_scooters_cfg

    scooters = parse_scooters_cfg()
    match = next((s for s in scooters if s["id"] == "ghost-scoot"), None)
    assert match is not None
    assert match["protocol"] == "ninebot"
    assert match["cfw_url"] == "https://x/cfw.bin"
    assert match["shfw_supported"] == "yes"


def test_ebikes_parser_picks_up_yaml_only_ebike(isolated_profiles):
    _write(
        isolated_profiles / "ebike" / "ghost-bafang.yaml",
        {
            "id": "ghost-bafang",
            "name": "Ghost Bafang Hack",
            "brand": "Ghost",
            "category": "ebike",
            "flash_method": "stlink",
            "support_status": "experimental",
            "controller": "bafang-bbshd",
            "firmware": [
                {"id": "bbs-fw", "name": "bbs-fw", "url": "https://x/bbs.hex", "type": "cfw"}
            ],
        },
    )
    from web.routes.ebike import parse_ebikes_cfg

    bikes = parse_ebikes_cfg()
    match = next((b for b in bikes if b["id"] == "ghost-bafang"), None)
    assert match is not None
    assert match["controller"] == "bafang-bbshd"
    assert match["fw_url"] == "https://x/bbs.hex"
    assert match["support_status"] == "experimental"


def test_t2_parser_picks_up_yaml_only_mac(isolated_profiles):
    _write(
        isolated_profiles / "t2" / "ghost-mac.yaml",
        {
            "id": "ghost-mac",
            "name": "Ghost MacBook",
            "brand": "Apple",
            "category": "laptop",
            "model": "MacGhost1,1",
            "flash_tool": "apple-t2-tool",
            "flash_method": "dfu",
            "usb_vid": "05ac",
            "usb_pid": "1881",
            "board_id": "J999AP",
            "firmware": [
                {"id": "bridge-os", "name": "BridgeOS", "url": "https://x/bridge.dmg", "type": "stock"}
            ],
        },
    )
    from web.routes.t2 import parse_t2_cfg

    macs = parse_t2_cfg()
    match = next((m for m in macs if m["id"] == "ghost-mac"), None)
    assert match is not None
    assert match["model"] == "MacGhost1,1"
    assert match["board_id"] == "J999AP"
    assert match["bridge_os_url"] == "https://x/bridge.dmg"


def test_medicat_parser_picks_up_yaml_only_entry(isolated_profiles):
    _write(
        isolated_profiles / "medicat" / "ghost-rescue.yaml",
        {
            "id": "ghost-rescue",
            "name": "Ghost Rescue USB",
            "category": "other",
            "flash_tool": "ventoy",
            "min_usb_gb": 64,
            "ventoy_required": True,
        },
    )
    from web.routes.medicat import parse_medicat_cfg

    entries = parse_medicat_cfg()
    match = next((e for e in entries if e["id"] == "ghost-rescue"), None)
    assert match is not None
    assert match["min_usb_gb"] == 64
    assert match["ventoy_required"] is True


def test_microcontrollers_parser_picks_up_yaml_only_board(isolated_profiles):
    _write(
        isolated_profiles / "mcu" / "ghost-board.yaml",
        {
            "id": "ghost-board",
            "name": "Ghost Dev Board",
            "brand": "Ghost",
            "category": "mcu",
            "flash_tool": "esptool",
            "usb_vid": "1234",
            "usb_pid": "5678",
            "arch": "esp32",
            "bootloader": "esp32-rom",
            "flash_steps": [
                {"id": "flash", "name": "Flash", "command": "esptool.py write_flash 0x0 fw.bin"}
            ],
        },
    )
    boards = core.parse_microcontrollers_cfg()
    match = next((b for b in boards if b["id"] == "ghost-board"), None)
    assert match is not None
    assert match["flash_tool"] == "esptool"
    assert match["usb_vid"] == "1234"
    assert match["arch"] == "esp32"
    assert "esptool.py" in match["flash_args"]


# ---------------------------------------------------------------------------
# Profile must override .cfg entry with same id
# ---------------------------------------------------------------------------


def test_profile_overrides_cfg_entry(isolated_profiles):
    """If a profile and a .cfg row share an id, profile wins."""
    # Pick an id that's actually in scooters.cfg and override its label.
    from web.routes.scooter import parse_scooters_cfg

    baseline = parse_scooters_cfg()
    if not baseline:
        pytest.skip("no scooters.cfg entries to override")
    target_id = baseline[0]["id"]

    _write(
        isolated_profiles / "scooter" / f"{target_id}.yaml",
        {
            "id": target_id,
            "name": "OVERRIDDEN",
            "brand": "Ghost",
            "category": "scooter",
            "flash_method": "ble",
        },
    )

    after = parse_scooters_cfg()
    overridden = next((s for s in after if s["id"] == target_id), None)
    assert overridden is not None
    assert overridden["label"] == "OVERRIDDEN"
    assert overridden["brand"] == "Ghost"
