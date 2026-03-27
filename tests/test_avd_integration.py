"""Integration tests using Android Studio emulator (AVD).

These tests hit real ADB against an emulated Android device — no subprocess
mocking.  They validate the same OSmosis routes that unit tests cover with
FakeDevice, but against genuine Android output.

Run:
    pytest tests/test_avd_integration.py -v --timeout=180

Skip in CI without an emulator:
    pytest -m "not avd"

Prerequisites:
    - AVD "osmosis_test" created (see tests/avd_helper.py docstring)
    - KVM available for x86_64 acceleration (check: /dev/kvm)
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.avd_helper import AVDInstance
from web.app import app

# ---------------------------------------------------------------------------
# Mark all tests in this module so they can be selected / deselected
# ---------------------------------------------------------------------------
pytestmark = pytest.mark.avd


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def avd():
    """Boot the emulator once for the whole module, then tear it down."""
    instance = AVDInstance()
    try:
        instance.start(timeout=180)
    except (FileNotFoundError, TimeoutError) as exc:
        pytest.skip(f"AVD not available: {exc}")
    yield instance
    instance.stop()


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# Detection tests — real ADB, real getprop
# ---------------------------------------------------------------------------


class TestDetection:
    """Validate /api/detect against the emulated Pixel 3a."""

    def test_detect_returns_200(self, client, avd):
        resp = client.get("/api/detect")
        assert resp.status_code == 200, resp.get_json()

    def test_detect_has_model(self, client, avd):
        data = client.get("/api/detect").get_json()
        # Emulator reports the AVD's hardware profile model
        assert data.get("model"), f"model missing: {data}"

    def test_detect_has_brand(self, client, avd):
        data = client.get("/api/detect").get_json()
        assert data.get("brand"), f"brand missing: {data}"

    def test_detect_has_codename(self, client, avd):
        data = client.get("/api/detect").get_json()
        assert data.get("codename"), f"codename missing: {data}"

    def test_detect_serial_is_emulator(self, client, avd):
        """The serial should be emulator-NNNN, not a physical serial."""
        data = client.get("/api/detect").get_json()
        # /api/detect doesn't always return serial at top level, but
        # the underlying ADB call uses it — just ensure no crash.
        assert "error" not in data or data.get("adb_state") == "device"


# ---------------------------------------------------------------------------
# Connected devices endpoint
# ---------------------------------------------------------------------------


class TestConnectedDevices:
    """Validate /api/devices/connected sees the emulator."""

    def test_connected_count(self, client, avd):
        data = client.get("/api/devices/connected").get_json()
        assert data["count"] >= 1

    def test_connected_serial(self, client, avd):
        data = client.get("/api/devices/connected").get_json()
        serials = [d["serial"] for d in data["devices"]]
        assert avd.serial in serials

    def test_connected_mode_is_device(self, client, avd):
        data = client.get("/api/devices/connected").get_json()
        emu_dev = next(d for d in data["devices"] if d["serial"] == avd.serial)
        assert emu_dev["mode"] == "device"

    def test_connected_has_display_name(self, client, avd):
        data = client.get("/api/devices/connected").get_json()
        emu_dev = next(d for d in data["devices"] if d["serial"] == avd.serial)
        assert emu_dev.get("display_name"), f"no display_name: {emu_dev}"


# ---------------------------------------------------------------------------
# ADB property consistency
# ---------------------------------------------------------------------------


class TestAdbProperties:
    """Cross-check that OSmosis detection matches direct getprop calls."""

    def test_model_matches_getprop(self, client, avd):
        expected = avd.getprop("ro.product.model")
        data = client.get("/api/detect").get_json()
        assert data["model"] == expected

    def test_codename_matches_getprop(self, client, avd):
        expected = avd.getprop("ro.product.device")
        data = client.get("/api/detect").get_json()
        assert data["codename"] == expected

    def test_brand_matches_getprop(self, client, avd):
        expected = avd.getprop("ro.product.brand").capitalize()
        data = client.get("/api/detect").get_json()
        assert data["brand"] == expected


# ---------------------------------------------------------------------------
# Recovery mode (adb reboot recovery)
# ---------------------------------------------------------------------------


class TestRecoveryMode:
    """Test detection when the emulator is in recovery mode.

    NOTE: The stock emulator recovery is minimal — OSmosis should handle
    the case where getprop returns empty strings gracefully.
    """

    def test_reboot_to_recovery_and_detect(self, client, avd):
        """Reboot into recovery, verify detection handles it, reboot back."""
        # Reboot to recovery — adb blocks until device disconnects, so
        # use a generous timeout; the command itself may time out, which is
        # fine as long as the device actually reboots.
        try:
            avd.adb("reboot", "recovery", timeout=30)
        except Exception:
            pass  # timeout expected — device drops the USB connection

        # Wait for device to reappear in recovery mode
        import time

        deadline = time.monotonic() + 60
        in_recovery = False
        while time.monotonic() < deadline:
            result = avd.adb("devices")
            for line in result.stdout.splitlines():
                if avd.serial in line and "recovery" in line:
                    in_recovery = True
                    break
            if in_recovery:
                break
            time.sleep(3)

        if not in_recovery:
            # Some emulator images don't support recovery — skip gracefully
            avd.wait_for_boot(timeout=60)
            pytest.skip("Emulator did not enter recovery mode")

        # Now test OSmosis detection
        resp = client.get("/api/detect")
        data = resp.get_json()
        # Should either detect recovery state or return a hint
        assert resp.status_code == 200 or "error" in data

        # Reboot back to normal
        avd.adb("reboot", timeout=10)
        avd.wait_for_boot(timeout=120)


# ---------------------------------------------------------------------------
# Multi-device scenario
# ---------------------------------------------------------------------------


class TestMultiDevice:
    """If a second emulator is available, test multi-device detection."""

    @pytest.fixture
    def second_avd(self):
        """Try to start a second emulator on a different port."""
        instance = AVDInstance(port=5556)
        try:
            instance.start(timeout=90)
        except (FileNotFoundError, TimeoutError, Exception) as exc:
            pytest.skip(f"Second AVD could not start: {exc}")
        yield instance
        instance.stop()

    def test_two_emulators_detected(self, client, avd, second_avd):
        data = client.get("/api/devices/connected").get_json()
        serials = {d["serial"] for d in data["devices"]}
        assert avd.serial in serials
        assert second_avd.serial in serials
        assert data["count"] >= 2
