"""Android Virtual Device (AVD) lifecycle helper for integration tests.

Manages starting/stopping the Android Studio emulator so that OSmosis
routes can be tested against a real ADB device without physical hardware.

Prerequisites (one-time setup):
    export ANDROID_HOME=~/Android/Sdk
    sdkmanager "emulator" "system-images;android-34;google_apis;x86_64"
    echo "no" | avdmanager create avd -n osmosis_test \
        -k "system-images;android-34;google_apis;x86_64" -d pixel_3a

Usage in tests:
    from tests.avd_helper import AVDInstance

    avd = AVDInstance()
    avd.start()          # boots emulator, waits for 'device' state
    serial = avd.serial  # e.g. "emulator-5554"
    ...
    avd.stop()
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time

# Default AVD name created by the setup instructions above.
DEFAULT_AVD = "osmosis_test"

# Max seconds to wait for boot-complete after the emulator process starts.
BOOT_TIMEOUT = 120

# Android SDK location — falls back to common paths.
ANDROID_HOME = os.environ.get(
    "ANDROID_HOME",
    os.environ.get("ANDROID_SDK_ROOT", os.path.expanduser("~/Android/Sdk")),
)


def _find_emulator_bin() -> str:
    """Locate the emulator binary."""
    # Prefer the SDK copy
    sdk_emu = os.path.join(ANDROID_HOME, "emulator", "emulator")
    if os.path.isfile(sdk_emu):
        return sdk_emu
    # Fall back to PATH
    which = shutil.which("emulator")
    if which:
        return which
    raise FileNotFoundError("Android emulator not found. Install via: sdkmanager 'emulator'")


def _adb(*args: str, timeout: int = 10) -> subprocess.CompletedProcess:
    """Run an adb command and return the result."""
    return subprocess.run(
        ["adb", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


class AVDInstance:
    """Manages a single emulator instance for testing."""

    def __init__(self, avd_name: str = DEFAULT_AVD, port: int = 5554):
        self.avd_name = avd_name
        self.port = port
        self.serial = f"emulator-{port}"
        self._proc: subprocess.Popen | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self, timeout: int = BOOT_TIMEOUT, cold_boot: bool = False) -> None:
        """Launch the emulator and block until the device is ready.

        Args:
            timeout: Max seconds to wait for boot-complete.
            cold_boot: If True, wipe snapshot and do a fresh boot (slower).
        """
        if self.is_running():
            return

        emulator = _find_emulator_bin()
        cmd = [
            emulator,
            "-avd",
            self.avd_name,
            "-port",
            str(self.port),
            "-no-window",
            "-no-audio",
            "-no-snapshot-save",
            "-gpu",
            "swiftshader_indirect",
        ]
        if cold_boot:
            cmd.append("-no-snapshot-load")

        self._proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        self._wait_for_device(timeout)

    def stop(self) -> None:
        """Kill the emulator."""
        # Try graceful shutdown via adb first
        try:
            _adb("-s", self.serial, "emu", "kill", timeout=5)
        except Exception:
            pass

        if self._proc:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._proc.kill()
            self._proc = None

    def is_running(self) -> bool:
        """Check if emulator-{port} is listed as an ADB device."""
        try:
            result = _adb("devices")
            return self.serial in result.stdout
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Device interaction helpers
    # ------------------------------------------------------------------

    def adb(self, *args: str, timeout: int = 10) -> subprocess.CompletedProcess:
        """Run an ADB command against this emulator instance."""
        return _adb("-s", self.serial, *args, timeout=timeout)

    def getprop(self, prop: str) -> str:
        """Shorthand for ``adb shell getprop <prop>``."""
        return self.adb("shell", "getprop", prop).stdout.strip()

    def wait_for_boot(self, timeout: int = BOOT_TIMEOUT) -> None:
        """Block until sys.boot_completed == 1."""
        self._wait_for_device(timeout)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _wait_for_device(self, timeout: int) -> None:
        """Wait for the emulator to become reachable and fully booted."""
        deadline = time.monotonic() + timeout

        # Phase 1: wait for adb to see the device at all
        while time.monotonic() < deadline:
            if self.is_running():
                break
            time.sleep(2)
        else:
            raise TimeoutError(f"Emulator {self.serial} did not appear in 'adb devices' within {timeout}s")

        # Phase 2: wait for boot_completed property
        while time.monotonic() < deadline:
            try:
                result = self.adb("shell", "getprop", "sys.boot_completed", timeout=5)
                if result.stdout.strip() == "1":
                    return
            except Exception:
                pass
            time.sleep(3)

        raise TimeoutError(f"Emulator {self.serial} did not finish booting within {timeout}s")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc):
        self.stop()
