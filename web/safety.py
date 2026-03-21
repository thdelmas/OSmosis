"""Safety module — pre-flash checklists, recovery guides, and verification."""

import subprocess
from pathlib import Path

from web.core import BACKUP_DIR


def preflight_check_phone(fw_path: str = "", recovery_img: str = "") -> dict:
    """Run pre-flash checklist for phone/tablet operations.

    Returns a dict with check results and overall pass/fail.
    """
    checks = []

    # 1. ADB connection
    try:
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=5)
        devices = [line for line in result.stdout.splitlines() if "\tdevice" in line]
        checks.append(
            {
                "id": "adb_connected",
                "label": "Device connected via ADB",
                "passed": len(devices) > 0,
                "detail": f"{len(devices)} device(s) detected" if devices else "No device found. Enable USB debugging.",
                "required": True,
            }
        )
    except Exception:
        checks.append(
            {
                "id": "adb_connected",
                "label": "Device connected via ADB",
                "passed": False,
                "detail": "ADB not available",
                "required": True,
            }
        )

    # 2. Battery level (>25% recommended)
    try:
        result = subprocess.run(
            ["adb", "shell", "dumpsys", "battery"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        level = None
        for line in result.stdout.splitlines():
            if "level:" in line:
                level = int(line.split(":")[-1].strip())
                break
        if level is not None:
            checks.append(
                {
                    "id": "battery_level",
                    "label": "Battery level above 25%",
                    "passed": level >= 25,
                    "detail": f"Battery at {level}%",
                    "required": True,
                }
            )
        else:
            checks.append(
                {
                    "id": "battery_level",
                    "label": "Battery level above 25%",
                    "passed": False,
                    "detail": "Could not read battery level",
                    "required": True,
                }
            )
    except Exception:
        checks.append(
            {
                "id": "battery_level",
                "label": "Battery level above 25%",
                "passed": False,
                "detail": "Could not check battery (no ADB?)",
                "required": True,
            }
        )

    # 3. Backup exists
    has_backup = False
    if BACKUP_DIR.exists():
        backups = sorted(BACKUP_DIR.iterdir(), reverse=True)
        has_backup = len(backups) > 0
    checks.append(
        {
            "id": "backup_exists",
            "label": "Backup available for rollback",
            "passed": has_backup,
            "detail": f"Latest backup: {backups[0].name}"
            if has_backup
            else "No backups found. Consider backing up first.",
            "required": False,
        }
    )

    # 4. Firmware file valid
    if fw_path:
        fw = Path(fw_path)
        checks.append(
            {
                "id": "firmware_exists",
                "label": "Firmware file exists and is non-empty",
                "passed": fw.is_file() and fw.stat().st_size > 0,
                "detail": f"{fw.name} ({fw.stat().st_size // 1024}K)" if fw.is_file() else f"Not found: {fw_path}",
                "required": True,
            }
        )

    # 5. Recovery image valid
    if recovery_img:
        rec = Path(recovery_img)
        checks.append(
            {
                "id": "recovery_exists",
                "label": "Recovery image exists and is non-empty",
                "passed": rec.is_file() and rec.stat().st_size > 0,
                "detail": f"{rec.name} ({rec.stat().st_size // 1024}K)"
                if rec.is_file()
                else f"Not found: {recovery_img}",
                "required": True,
            }
        )

    # 6. Sufficient storage on device
    try:
        result = subprocess.run(
            ["adb", "shell", "df", "/data"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        lines = result.stdout.strip().splitlines()
        if len(lines) >= 2:
            parts = lines[1].split()
            if len(parts) >= 4:
                avail_kb = int(parts[3])
                avail_mb = avail_kb // 1024
                checks.append(
                    {
                        "id": "storage_space",
                        "label": "Sufficient storage on device (>500MB free)",
                        "passed": avail_mb >= 500,
                        "detail": f"{avail_mb}MB free on /data",
                        "required": False,
                    }
                )
    except Exception:
        pass

    all_required_pass = all(c["passed"] for c in checks if c["required"])
    return {
        "checks": checks,
        "passed": all_required_pass,
        "total": len(checks),
        "passed_count": sum(1 for c in checks if c["passed"]),
    }


def preflight_check_scooter(address: str = "", fw_path: str = "") -> dict:
    """Run pre-flash checklist for scooter operations."""
    checks = []

    # 1. BLE address provided
    checks.append(
        {
            "id": "ble_address",
            "label": "BLE address specified",
            "passed": bool(address and address.strip()),
            "detail": address if address else "No BLE address provided. Scan for scooters first.",
            "required": True,
        }
    )

    # 2. Firmware file valid
    if fw_path:
        fw = Path(fw_path)
        checks.append(
            {
                "id": "firmware_exists",
                "label": "Firmware file exists and is non-empty",
                "passed": fw.is_file() and fw.stat().st_size > 0,
                "detail": f"{fw.name} ({fw.stat().st_size // 1024}K)" if fw.is_file() else f"Not found: {fw_path}",
                "required": True,
            }
        )

    # 3. Bleak available
    try:
        import importlib

        importlib.import_module("bleak")
        bleak_ok = True
    except ImportError:
        bleak_ok = False
    checks.append(
        {
            "id": "bleak_installed",
            "label": "BLE library (bleak) installed",
            "passed": bleak_ok,
            "detail": "bleak is available" if bleak_ok else "pip install bleak",
            "required": True,
        }
    )

    # 4. Bluetooth adapter present
    try:
        result = subprocess.run(
            ["hciconfig"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        bt_up = "UP RUNNING" in result.stdout
        checks.append(
            {
                "id": "bluetooth_adapter",
                "label": "Bluetooth adapter is up",
                "passed": bt_up,
                "detail": "Adapter detected and running" if bt_up else "No Bluetooth adapter found or adapter is down",
                "required": True,
            }
        )
    except FileNotFoundError:
        checks.append(
            {
                "id": "bluetooth_adapter",
                "label": "Bluetooth adapter is up",
                "passed": False,
                "detail": "hciconfig not available — install bluez",
                "required": True,
            }
        )
    except Exception:
        pass

    # 5. Scooter backup exists
    backup_dir = Path.home() / ".osmosis" / "scooter-backups"
    has_backup = backup_dir.exists() and any(backup_dir.iterdir()) if backup_dir.exists() else False
    checks.append(
        {
            "id": "scooter_backup",
            "label": "Scooter firmware backup available",
            "passed": has_backup,
            "detail": "Backup found" if has_backup else "No scooter backup. Consider reading current firmware first.",
            "required": False,
        }
    )

    all_required_pass = all(c["passed"] for c in checks if c["required"])
    return {
        "checks": checks,
        "passed": all_required_pass,
        "total": len(checks),
        "passed_count": sum(1 for c in checks if c["passed"]),
    }


def preflight_check_pixel(fw_path: str = "") -> dict:
    """Run pre-flash checklist for Pixel/fastboot operations."""
    checks = []

    # 1. Fastboot connection
    try:
        result = subprocess.run(["fastboot", "devices"], capture_output=True, text=True, timeout=5)
        devices = [line for line in result.stdout.strip().splitlines() if line.strip()]
        checks.append(
            {
                "id": "fastboot_connected",
                "label": "Device connected via fastboot",
                "passed": len(devices) > 0,
                "detail": f"{len(devices)} device(s) detected"
                if devices
                else "No device found. Enter Fastboot Mode (Volume Down + Power).",
                "required": True,
            }
        )
    except FileNotFoundError:
        checks.append(
            {
                "id": "fastboot_connected",
                "label": "Device connected via fastboot",
                "passed": False,
                "detail": "fastboot not installed. Install Android SDK Platform Tools.",
                "required": True,
            }
        )
    except Exception:
        checks.append(
            {
                "id": "fastboot_connected",
                "label": "Device connected via fastboot",
                "passed": False,
                "detail": "Could not run fastboot",
                "required": True,
            }
        )

    # 2. Bootloader unlock status
    try:
        result = subprocess.run(
            ["fastboot", "getvar", "unlocked"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        output = result.stdout + result.stderr
        unlocked = "unlocked: yes" in output.lower()
        checks.append(
            {
                "id": "bootloader_unlocked",
                "label": "Bootloader is unlocked",
                "passed": unlocked,
                "detail": "Bootloader unlocked"
                if unlocked
                else "Bootloader is locked. Unlock via 'fastboot flashing unlock' (erases all data).",
                "required": True,
            }
        )
    except Exception:
        pass

    # 3. Firmware file valid
    if fw_path:
        fw = Path(fw_path)
        checks.append(
            {
                "id": "firmware_exists",
                "label": "Firmware file exists and is non-empty",
                "passed": fw.is_file() and fw.stat().st_size > 0,
                "detail": f"{fw.name} ({fw.stat().st_size // 1024}K)" if fw.is_file() else f"Not found: {fw_path}",
                "required": True,
            }
        )

    # 4. Backup exists
    has_backup = False
    if BACKUP_DIR.exists():
        backups = sorted(BACKUP_DIR.iterdir(), reverse=True)
        has_backup = len(backups) > 0
    checks.append(
        {
            "id": "backup_exists",
            "label": "Backup available for rollback",
            "passed": has_backup,
            "detail": f"Latest backup: {backups[0].name}"
            if has_backup
            else "No backups found. Consider backing up first.",
            "required": False,
        }
    )

    all_required_pass = all(c["passed"] for c in checks if c["required"])
    return {
        "checks": checks,
        "passed": all_required_pass,
        "total": len(checks),
        "passed_count": sum(1 for c in checks if c["passed"]),
    }


# ---------------------------------------------------------------------------
# Recovery guides — structured data for the UI
# ---------------------------------------------------------------------------

RECOVERY_GUIDES = {
    "samsung": {
        "title": "Samsung Recovery Guide",
        "device_type": "phone",
        "steps": [
            {
                "title": "Enter Download Mode",
                "description": "Power off the device completely. Then hold Volume Down + Home + Power simultaneously until you see a warning screen. Press Volume Up to enter Download Mode.",
                "warning": None,
            },
            {
                "title": "Re-flash stock firmware via Heimdall",
                "description": "With the device in Download Mode and connected via USB, use Osmosis to flash the stock firmware. Go to 'Restore stock firmware' in the wizard.",
                "warning": None,
            },
            {
                "title": "If Heimdall doesn't detect the device",
                "description": "Try a different USB cable (prefer the original). Try a USB 2.0 port instead of USB 3.0. On Linux, check udev rules: sudo cp 50-samsung.rules /etc/udev/rules.d/ && sudo udevadm control --reload-rules",
                "warning": None,
            },
            {
                "title": "Bootloop recovery",
                "description": "If the device is stuck in a bootloop, enter Download Mode and re-flash stock firmware. If you have TWRP installed, boot into recovery (Power + Home + Volume Up) and wipe cache/dalvik.",
                "warning": None,
            },
            {
                "title": "EFS recovery (IMEI issues)",
                "description": "If you lose cellular connectivity after flashing, your EFS partition may be corrupted. Restore from your EFS backup: heimdall flash --EFS efs.img. If you don't have a backup, the EFS cannot be recreated — this is why Osmosis recommends backing up EFS before any flash operation.",
                "warning": "EFS contains your IMEI. Without a backup, a corrupted EFS means permanent loss of cellular connectivity on this device.",
            },
            {
                "title": "Last resort: Odin on Windows",
                "description": "If Heimdall consistently fails, use Odin on a Windows machine with Samsung USB drivers installed. Download Odin from the companion tools page. Load the stock firmware and flash.",
                "warning": None,
            },
        ],
    },
    "scooter": {
        "title": "Scooter Recovery Guide",
        "device_type": "scooter",
        "steps": [
            {
                "title": "BLE flash failed mid-way",
                "description": "If a BLE firmware flash was interrupted, the scooter may not boot normally but should still be discoverable via BLE. Try scanning again and re-flashing. If the scooter shows an error code, note it — most error codes are recoverable.",
                "warning": None,
            },
            {
                "title": "Scooter not responding to BLE",
                "description": "Turn the scooter off and on again. Wait 30 seconds for the BLE module to initialize. If still unresponsive, the BLE module firmware may be corrupted — you'll need ST-Link recovery.",
                "warning": None,
            },
            {
                "title": "ST-Link ESC recovery",
                "description": "Connect an ST-Link V2 programmer to the ESC debug header (SWDIO, SWCLK, GND, 3.3V). Use Osmosis with the ST-Link flash option to write stock firmware directly to the ESC. This bypasses BLE entirely and can recover from any software-level brick.",
                "warning": "Double-check wiring before connecting power. Incorrect connections can damage the ESC.",
            },
            {
                "title": "ST-Link BLE module recovery",
                "description": "The BLE module (usually nRF51822) can also be recovered via ST-Link/SWD. Connect to the BLE module's SWD pins and flash the stock BLE firmware.",
                "warning": None,
            },
            {
                "title": "Error 14 / Error 15 after CFW",
                "description": "Error 14 (throttle error) and Error 15 (motor error) are common after aggressive CFW settings. Flash stock firmware to clear the error. Then re-apply CFW with conservative settings — reduce motor current and disable KERS.",
                "warning": None,
            },
            {
                "title": "Downgrade firmware version",
                "description": "If a newer firmware causes issues, you can downgrade. For Ninebot scooters, use the DRV downgrade option in the scooter flash menu. For Xiaomi scooters, flash the older firmware file directly via BLE or ST-Link.",
                "warning": "Some newer ESC hardware revisions may reject older firmware versions. Check the wiki for your specific model.",
            },
            {
                "title": "Check scooter hardware revision",
                "description": "The same scooter model can have different microcontrollers depending on the manufacturing date. Use 'Read scooter info' to check the chip type (STM32, GD32, AT32). Using firmware for the wrong chip type can brick the ESC — always verify before flashing.",
                "warning": "GD32 and AT32 chips require different firmware than STM32. Flashing the wrong variant will brick the controller.",
            },
        ],
    },
    "pixel": {
        "title": "Google Pixel Recovery Guide",
        "device_type": "phone",
        "steps": [
            {
                "title": "Enter Fastboot Mode",
                "description": "Power off the device. Hold Volume Down + Power until the bootloader screen appears. Use the volume keys to navigate and Power to select.",
                "warning": None,
            },
            {
                "title": "Re-flash factory image",
                "description": "Download the factory image for your exact model from the Google firmware page. Extract it, then use Osmosis (Pixel wizard) or run 'flash-all.sh' manually from the extracted directory.",
                "warning": None,
            },
            {
                "title": "Bootloader won't unlock",
                "description": "OEM unlocking must be enabled in Developer Options before the device is bricked. If it was never enabled, the bootloader cannot be unlocked and only Google-signed images can be flashed. Carrier-locked Pixels may block OEM unlock entirely.",
                "warning": "Without OEM unlock, only stock signed images can be flashed. Custom ROMs require an unlocked bootloader.",
            },
            {
                "title": "Stuck in bootloop after custom ROM",
                "description": "Enter Fastboot Mode (Volume Down + Power). Flash the stock factory image to fully restore the device. If fastboot is responsive, the device is recoverable.",
                "warning": None,
            },
            {
                "title": "Fastboot not detecting device",
                "description": "Try a different USB cable (prefer USB-C to USB-C or the original cable). On Linux, check udev rules: create /etc/udev/rules.d/51-android.rules with your device's USB vendor ID (18d1 for Google). Run 'sudo udevadm control --reload-rules'.",
                "warning": None,
            },
            {
                "title": "Device stuck on Google logo",
                "description": "Wait at least 15 minutes — first boot after flashing can be slow. If it doesn't progress, force reboot into Fastboot (hold Power 10s, then Volume Down + Power) and re-flash.",
                "warning": None,
            },
            {
                "title": "Lost Android Verified Boot (AVB) keys",
                "description": "If you flashed a custom ROM without disabling verification, the device may refuse to boot. Flash stock factory image to restore the original AVB keys, or flash with '--disable-verity --disable-verification' flags.",
                "warning": None,
            },
            {
                "title": "Rescue Mode (last resort)",
                "description": "Some Pixels support Rescue Mode: with the device off, connect USB to a computer, then hold Power for 15+ seconds. If the device enters rescue mode, you can use the Android Flash Tool from Google to restore it.",
                "warning": None,
            },
        ],
    },
    "bootable": {
        "title": "Bootable Media Recovery Guide",
        "device_type": "bootable",
        "steps": [
            {
                "title": "USB drive not booting",
                "description": "Check BIOS/UEFI boot order — USB must be first. Try a different USB port (prefer USB 2.0). Some systems need Secure Boot disabled and Legacy/CSM mode enabled.",
                "warning": None,
            },
            {
                "title": "Wrong image written",
                "description": "Re-write the correct image using Osmosis. The previous data is overwritten — there's no undo, but the USB drive itself is fine.",
                "warning": None,
            },
            {
                "title": "Verification failed after write",
                "description": "The SHA256 of the written data doesn't match the source. Try a different USB drive — the current one may have bad sectors. Re-download the image and verify its hash before writing.",
                "warning": None,
            },
        ],
    },
}
