"""Device emulator for testing OSmosis without real hardware.

Provides FakeDevice presets and a subprocess mock that returns realistic
output for adb, fastboot, heimdall, lsusb, and flashrom commands.

Usage in tests:

    from tests.device_emulator import DeviceEmulator, FakeDevice

    emu = DeviceEmulator()
    emu.connect(FakeDevice.SAMSUNG_NOTE2)

    with emu.patch():
        resp = client.get("/api/detect")
        assert resp.get_json()["codename"] == "t03g"

    emu.disconnect()
    with emu.patch():
        resp = client.get("/api/detect")
        assert resp.status_code == 404
"""

from __future__ import annotations

import subprocess
from contextlib import contextmanager
from dataclasses import dataclass, field
from unittest.mock import patch


@dataclass
class FakeDeviceSpec:
    """Specification for an emulated device."""

    serial: str
    brand: str
    model: str
    codename: str
    display_name: str
    mode: str = "device"  # device | recovery | sideload | download | fastboot | unauthorized
    usb_vid: str = ""
    usb_pid: str = ""
    usb_description: str = ""
    # Android properties (returned by getprop)
    props: dict[str, str] = field(default_factory=dict)
    # Fastboot vars (returned by fastboot getvar)
    fastboot_vars: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Preset devices — add more as needed
# ---------------------------------------------------------------------------


class FakeDevice:
    """Pre-configured device specs for common test scenarios."""

    SAMSUNG_NOTE2 = FakeDeviceSpec(
        serial="4df798d76f98e513",
        brand="Samsung",
        model="GT-N7100",
        codename="t03g",
        display_name="Galaxy Note II",
        mode="device",
        usb_vid="04e8",
        usb_pid="6860",
        usb_description="Samsung Electronics Co., Ltd Galaxy Nexus/Jelly Bean (MTP)",
        props={
            "ro.product.model": "GT-N7100",
            "ro.product.device": "t03g",
            "ro.product.board": "smdk4x12",
            "ro.product.brand": "samsung",
            "ro.product.marketname": "Galaxy Note II",
            "ro.config.marketing_name": "",
        },
    )

    SAMSUNG_NOTE2_DOWNLOAD = FakeDeviceSpec(
        serial="",
        brand="Samsung",
        model="GT-N7100",
        codename="t03g",
        display_name="Galaxy Note II",
        mode="download",
        usb_vid="04e8",
        usb_pid="685d",
        usb_description="Samsung Electronics Co., Ltd GT-I9100 Phone (Download mode)",
    )

    SAMSUNG_NOTE2_UNAUTHORIZED = FakeDeviceSpec(
        serial="4df798d76f98e513",
        brand="Samsung",
        model="GT-N7100",
        codename="t03g",
        display_name="Galaxy Note II",
        mode="unauthorized",
        usb_vid="04e8",
        usb_pid="6860",
        usb_description="Samsung Electronics Co., Ltd Galaxy (MTP)",
    )

    PIXEL_3A = FakeDeviceSpec(
        serial="94LAY0B89R",
        brand="Google",
        model="Pixel 3a",
        codename="sargo",
        display_name="Pixel 3a",
        mode="device",
        usb_vid="18d1",
        usb_pid="4ee7",
        usb_description="Google Inc. Nexus/Pixel Device (MTP)",
        props={
            "ro.product.model": "Pixel 3a",
            "ro.product.device": "sargo",
            "ro.product.board": "sargo",
            "ro.product.brand": "google",
            "ro.product.marketname": "Pixel 3a",
            "ro.config.marketing_name": "",
        },
    )

    PIXEL_3A_FASTBOOT = FakeDeviceSpec(
        serial="94LAY0B89R",
        brand="Google",
        model="Pixel 3a",
        codename="sargo",
        display_name="Pixel 3a",
        mode="fastboot",
        usb_vid="18d1",
        usb_pid="4ee0",
        usb_description="Google Inc. Nexus/Pixel Device (bootloader)",
        fastboot_vars={
            "product": "sargo",
            "unlocked": "yes",
            "serialno": "94LAY0B89R",
            "variant": "sargo",
        },
    )

    XIAOMI_MI11_SIDELOAD = FakeDeviceSpec(
        serial="a1b2c3d4",
        brand="Xiaomi",
        model="M2101K9AG",
        codename="courbet",
        display_name="Mi 11 Lite 4G",
        mode="sideload",
        usb_vid="2717",
        usb_pid="ff48",
        usb_description="Xiaomi Inc. Mi/Redmi series (MTP + ADB)",
        props={
            "ro.product.model": "M2101K9AG",
            "ro.product.device": "courbet",
            "ro.product.board": "courbet",
            "ro.product.brand": "Xiaomi",
            "ro.product.marketname": "Mi 11 Lite 4G",
            "ro.config.marketing_name": "",
        },
    )

    FAIRPHONE_4 = FakeDeviceSpec(
        serial="FP4ABC123",
        brand="Fairphone",
        model="FP4",
        codename="FP4",
        display_name="Fairphone 4",
        mode="device",
        usb_vid="2ae5",
        usb_pid="9024",
        usb_description="Fairphone B.V. FP4",
        props={
            "ro.product.model": "FP4",
            "ro.product.device": "FP4",
            "ro.product.board": "FP4",
            "ro.product.brand": "Fairphone",
            "ro.product.marketname": "Fairphone 4",
            "ro.config.marketing_name": "Fairphone 4",
        },
    )


# ---------------------------------------------------------------------------
# Emulator
# ---------------------------------------------------------------------------


class DeviceEmulator:
    """Emulates USB-connected devices by mocking subprocess.run.

    Supports multiple simultaneous devices. Generates realistic command
    output for adb, fastboot, heimdall, lsusb, and shutil.which.
    """

    def __init__(self):
        self.devices: list[FakeDeviceSpec] = []

    def connect(self, device: FakeDeviceSpec) -> None:
        """Simulate plugging in a device."""
        if device not in self.devices:
            self.devices.append(device)

    def disconnect(self, device: FakeDeviceSpec | None = None) -> None:
        """Simulate unplugging a device (or all devices if None)."""
        if device is None:
            self.devices.clear()
        elif device in self.devices:
            self.devices.remove(device)

    # -- Fake output generators -------------------------------------------

    def _adb_devices(self, long: bool = False) -> str:
        """Generate `adb devices [-l]` output."""
        lines = ["List of devices attached"]
        for d in self.devices:
            if d.mode in ("device", "recovery", "sideload", "unauthorized"):
                if long:
                    lines.append(f"{d.serial}\t{d.mode} product:{d.codename} model:{d.model} device:{d.codename}")
                else:
                    lines.append(f"{d.serial}\t{d.mode}")
        lines.append("")
        return "\n".join(lines)

    def _adb_getprop(self, serial: str, prop: str) -> str:
        """Generate `adb shell getprop <prop>` output."""
        for d in self.devices:
            if d.serial == serial and d.mode == "device":
                return d.props.get(prop, "")
        return ""

    def _fastboot_devices(self) -> str:
        """Generate `fastboot devices` output."""
        lines = []
        for d in self.devices:
            if d.mode == "fastboot":
                lines.append(f"{d.serial}\tfastboot")
        return "\n".join(lines)

    def _fastboot_getvar(self, var: str) -> str:
        """Generate `fastboot getvar <var>` stderr (fastboot prints to stderr)."""
        for d in self.devices:
            if d.mode == "fastboot" and var in d.fastboot_vars:
                return f"{var}: {d.fastboot_vars[var]}\nFinished. Total time: 0.001s"
        return f"{var}: \nFinished. Total time: 0.001s"

    def _heimdall_detect(self) -> int:
        """Return exit code for `heimdall detect`."""
        return 0 if any(d.mode == "download" for d in self.devices) else 1

    def _lsusb(self) -> str:
        """Generate `lsusb` output."""
        lines = []
        for i, d in enumerate(self.devices):
            if d.usb_vid:
                lines.append(f"Bus 001 Device {i + 2:03d}: ID {d.usb_vid}:{d.usb_pid} {d.usb_description}")
        # Add some non-device USB entries for realism
        lines.insert(0, "Bus 001 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub")
        return "\n".join(lines)

    # -- Mock subprocess.run ----------------------------------------------

    def _fake_run(self, cmd, **kwargs):
        """Drop-in replacement for subprocess.run that returns emulated output."""
        if isinstance(cmd, str):
            parts = cmd.split()
        else:
            parts = list(cmd)

        if not parts:
            raise FileNotFoundError("empty command")

        binary = parts[0]
        stdout = ""
        stderr = ""
        returncode = 0

        if binary == "adb":
            if "devices" in parts:
                long = "-l" in parts
                stdout = self._adb_devices(long=long)
            elif "shell" in parts and "getprop" in parts:
                serial_idx = parts.index("-s") + 1 if "-s" in parts else None
                serial = parts[serial_idx] if serial_idx else ""
                prop = parts[-1]
                stdout = self._adb_getprop(serial, prop)
            elif "start-server" in parts:
                stdout = "* daemon started successfully\n"
            elif "reboot" in parts:
                stdout = ""
            else:
                stdout = ""

        elif binary == "fastboot":
            if "devices" in parts:
                stdout = self._fastboot_devices()
            elif "getvar" in parts:
                var = parts[-1]
                stderr = self._fastboot_getvar(var)
            else:
                stdout = ""

        elif binary == "heimdall":
            if "detect" in parts:
                returncode = self._heimdall_detect()
            elif "flash" in parts:
                stdout = "Uploading RECOVERY\nRESUME OPERATION\n100%\nUpload successful.\nRebooting device...\n"
            else:
                stdout = ""

        elif binary == "lsusb":
            stdout = self._lsusb()

        else:
            # Unknown command — return empty success
            pass

        result = subprocess.CompletedProcess(cmd, returncode, stdout=stdout, stderr=stderr)
        return result

    def _fake_which(self, cmd: str) -> str | None:
        """Always report adb/fastboot/heimdall/lsusb as available."""
        known = {"adb", "fastboot", "heimdall", "lsusb", "flashrom", "curl"}
        if cmd in known:
            return f"/usr/bin/{cmd}"
        return None

    @contextmanager
    def patch(self):
        """Context manager that patches subprocess.run and shutil.which."""
        with (
            patch("subprocess.run", side_effect=self._fake_run),
            patch("shutil.which", side_effect=self._fake_which),
        ):
            yield self
