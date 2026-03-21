"""Tests for safety module — preflight checks and recovery guides."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web.safety import (
    RECOVERY_GUIDES,
    preflight_check_phone,
    preflight_check_pixel,
    preflight_check_scooter,
)

# ---------------------------------------------------------------------------
# Recovery guides structure
# ---------------------------------------------------------------------------


def test_recovery_guides_has_expected_keys():
    assert "samsung" in RECOVERY_GUIDES
    assert "scooter" in RECOVERY_GUIDES
    assert "pixel" in RECOVERY_GUIDES
    assert "bootable" in RECOVERY_GUIDES


def test_recovery_guide_structure():
    for key, guide in RECOVERY_GUIDES.items():
        assert "title" in guide, f"{key} missing title"
        assert "device_type" in guide, f"{key} missing device_type"
        assert "steps" in guide, f"{key} missing steps"
        assert isinstance(guide["steps"], list)
        assert len(guide["steps"]) > 0, f"{key} has no steps"
        for step in guide["steps"]:
            assert "title" in step
            assert "description" in step
            assert "warning" in step  # can be None


# ---------------------------------------------------------------------------
# Preflight: phone
# ---------------------------------------------------------------------------


@patch("web.safety.subprocess.run")
@patch("web.safety.BACKUP_DIR")
def test_preflight_phone_all_pass(mock_backup_dir, mock_run, tmp_path):
    # ADB devices: one connected
    adb_devices = MagicMock()
    adb_devices.stdout = "List of devices attached\nABC123\tdevice\n"

    # Battery: 80%
    adb_battery = MagicMock()
    adb_battery.stdout = "  level: 80\n  status: 2\n"

    # Storage: plenty free
    adb_storage = MagicMock()
    adb_storage.stdout = (
        "Filesystem  1K-blocks  Used  Available  Use%  Mounted on\n/data  10000000  5000000  5000000  50%  /data\n"
    )

    mock_run.side_effect = [adb_devices, adb_battery, adb_storage]

    # Backup exists
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    (backup_dir / "backup-20240101").mkdir()
    mock_backup_dir.exists.return_value = True
    mock_backup_dir.iterdir.return_value = list(backup_dir.iterdir())

    result = preflight_check_phone()
    assert result["passed"] is True
    assert result["passed_count"] > 0
    assert result["total"] > 0


@patch("web.safety.subprocess.run", side_effect=FileNotFoundError)
@patch("web.safety.BACKUP_DIR")
def test_preflight_phone_no_adb(mock_backup_dir, mock_run):
    mock_backup_dir.exists.return_value = False
    result = preflight_check_phone()
    assert result["passed"] is False
    adb_check = next(c for c in result["checks"] if c["id"] == "adb_connected")
    assert adb_check["passed"] is False


@patch("web.safety.subprocess.run")
@patch("web.safety.BACKUP_DIR")
def test_preflight_phone_low_battery(mock_backup_dir, mock_run):
    adb_devices = MagicMock()
    adb_devices.stdout = "List of devices attached\nABC\tdevice\n"

    adb_battery = MagicMock()
    adb_battery.stdout = "  level: 10\n"

    adb_storage = MagicMock()
    adb_storage.stdout = ""

    mock_run.side_effect = [adb_devices, adb_battery, adb_storage]
    mock_backup_dir.exists.return_value = False

    result = preflight_check_phone()
    assert result["passed"] is False
    battery = next(c for c in result["checks"] if c["id"] == "battery_level")
    assert battery["passed"] is False
    assert "10%" in battery["detail"]


@patch("web.safety.subprocess.run")
@patch("web.safety.BACKUP_DIR")
def test_preflight_phone_with_firmware(mock_backup_dir, mock_run, tmp_path):
    mock_run.side_effect = FileNotFoundError
    mock_backup_dir.exists.return_value = False

    fw = tmp_path / "stock.tar"
    fw.write_bytes(b"firmware data here")

    result = preflight_check_phone(fw_path=str(fw))
    fw_check = next(c for c in result["checks"] if c["id"] == "firmware_exists")
    assert fw_check["passed"] is True


@patch("web.safety.subprocess.run")
@patch("web.safety.BACKUP_DIR")
def test_preflight_phone_missing_firmware(mock_backup_dir, mock_run):
    mock_run.side_effect = FileNotFoundError
    mock_backup_dir.exists.return_value = False

    result = preflight_check_phone(fw_path="/nonexistent/fw.zip")
    fw_check = next(c for c in result["checks"] if c["id"] == "firmware_exists")
    assert fw_check["passed"] is False


@patch("web.safety.subprocess.run")
@patch("web.safety.BACKUP_DIR")
def test_preflight_phone_with_recovery_img(mock_backup_dir, mock_run, tmp_path):
    mock_run.side_effect = FileNotFoundError
    mock_backup_dir.exists.return_value = False

    rec = tmp_path / "twrp.img"
    rec.write_bytes(b"recovery image")

    result = preflight_check_phone(recovery_img=str(rec))
    rec_check = next(c for c in result["checks"] if c["id"] == "recovery_exists")
    assert rec_check["passed"] is True


# ---------------------------------------------------------------------------
# Preflight: scooter
# ---------------------------------------------------------------------------


def test_preflight_scooter_no_address():
    with patch("web.safety.subprocess.run", side_effect=FileNotFoundError):
        result = preflight_check_scooter()
    ble = next(c for c in result["checks"] if c["id"] == "ble_address")
    assert ble["passed"] is False
    assert result["passed"] is False


def test_preflight_scooter_with_address():
    with patch("web.safety.subprocess.run", side_effect=FileNotFoundError):
        result = preflight_check_scooter(address="AA:BB:CC:DD:EE:FF")
    ble = next(c for c in result["checks"] if c["id"] == "ble_address")
    assert ble["passed"] is True


def test_preflight_scooter_firmware_check(tmp_path):
    fw = tmp_path / "scooter_fw.bin"
    fw.write_bytes(b"scooter firmware")

    with patch("web.safety.subprocess.run", side_effect=FileNotFoundError):
        result = preflight_check_scooter(address="AA:BB:CC:DD:EE:FF", fw_path=str(fw))
    fw_check = next(c for c in result["checks"] if c["id"] == "firmware_exists")
    assert fw_check["passed"] is True


# ---------------------------------------------------------------------------
# Preflight: pixel
# ---------------------------------------------------------------------------


@patch("web.safety.subprocess.run")
@patch("web.safety.BACKUP_DIR")
def test_preflight_pixel_device_connected(mock_backup_dir, mock_run):
    fb_devices = MagicMock()
    fb_devices.stdout = "ABC123\tfastboot\n"

    fb_unlock = MagicMock()
    fb_unlock.stdout = ""
    fb_unlock.stderr = "unlocked: yes\n"

    mock_run.side_effect = [fb_devices, fb_unlock]
    mock_backup_dir.exists.return_value = False

    result = preflight_check_pixel()
    fb_check = next(c for c in result["checks"] if c["id"] == "fastboot_connected")
    assert fb_check["passed"] is True


@patch("web.safety.subprocess.run", side_effect=FileNotFoundError)
@patch("web.safety.BACKUP_DIR")
def test_preflight_pixel_no_fastboot(mock_backup_dir, mock_run):
    mock_backup_dir.exists.return_value = False
    result = preflight_check_pixel()
    fb_check = next(c for c in result["checks"] if c["id"] == "fastboot_connected")
    assert fb_check["passed"] is False
    assert "not installed" in fb_check["detail"]


@patch("web.safety.subprocess.run")
@patch("web.safety.BACKUP_DIR")
def test_preflight_pixel_locked_bootloader(mock_backup_dir, mock_run):
    fb_devices = MagicMock()
    fb_devices.stdout = "ABC123\tfastboot\n"

    fb_unlock = MagicMock()
    fb_unlock.stdout = ""
    fb_unlock.stderr = "unlocked: no\n"

    mock_run.side_effect = [fb_devices, fb_unlock]
    mock_backup_dir.exists.return_value = False

    result = preflight_check_pixel()
    bl = next(c for c in result["checks"] if c["id"] == "bootloader_unlocked")
    assert bl["passed"] is False


@patch("web.safety.subprocess.run")
@patch("web.safety.BACKUP_DIR")
def test_preflight_pixel_with_firmware(mock_backup_dir, mock_run, tmp_path):
    mock_run.side_effect = FileNotFoundError
    mock_backup_dir.exists.return_value = False

    fw = tmp_path / "pixel_image.zip"
    fw.write_bytes(b"pixel factory image")

    result = preflight_check_pixel(fw_path=str(fw))
    fw_check = next(c for c in result["checks"] if c["id"] == "firmware_exists")
    assert fw_check["passed"] is True


# ---------------------------------------------------------------------------
# Preflight result structure
# ---------------------------------------------------------------------------


@patch("web.safety.subprocess.run", side_effect=FileNotFoundError)
@patch("web.safety.BACKUP_DIR")
def test_preflight_result_structure(mock_backup_dir, mock_run):
    mock_backup_dir.exists.return_value = False
    for fn in [preflight_check_phone, preflight_check_pixel]:
        result = fn()
        assert "checks" in result
        assert "passed" in result
        assert "total" in result
        assert "passed_count" in result
        assert isinstance(result["checks"], list)
        assert isinstance(result["passed"], bool)
        for check in result["checks"]:
            assert "id" in check
            assert "label" in check
            assert "passed" in check
            assert "detail" in check
            assert "required" in check
