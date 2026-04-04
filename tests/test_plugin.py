"""Tests for the plugin architecture — driver registration and discovery."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web.plugin import (
    PluginInfo,
    get_driver,
    list_plugins,
    list_plugins_by_category,
    register_driver,
)


class FakeDriver:
    """Minimal DeviceDriver implementation for testing."""

    def __init__(
        self,
        id="test-driver",
        name="Test Driver",
        category="phone",
        version="1.0",
    ):
        self.id = id
        self.name = name
        self.category = category
        self.version = version

    def detect(self):
        return [{"id": "dev1", "name": "Test Device"}]

    def flash(self, device_id, fw_path, options):
        return True

    def backup(self, device_id, dest_dir):
        return True

    def info(self, device_id):
        return {"model": "Test", "serial": "123"}


class FakeMonitorableDriver(FakeDriver):
    """Driver that also supports telemetry."""

    def telemetry(self, device_id):
        return {"speed": 25, "battery": 80}


class FakeUpdatableDriver(FakeDriver):
    """Driver that also supports OTA updates."""

    def check_update(self, device_id):
        return {"available": True, "version": "2.0"}

    def apply_update(self, device_id, fw_path):
        return True


class FakeFullDriver(FakeMonitorableDriver, FakeUpdatableDriver):
    """Driver with all capabilities."""

    pass


@pytest.fixture(autouse=True)
def clean_registry():
    """Clear the plugin registry before each test."""
    from web import plugin

    plugin._registry.clear()
    plugin._plugin_info.clear()
    yield
    plugin._registry.clear()
    plugin._plugin_info.clear()


# ---------------------------------------------------------------------------
# register_driver / get_driver
# ---------------------------------------------------------------------------


def test_register_and_get_driver():
    drv = FakeDriver()
    register_driver(drv)
    assert get_driver("test-driver") is drv


def test_get_driver_not_found():
    assert get_driver("nonexistent") is None


def test_register_multiple_drivers():
    drv1 = FakeDriver(id="drv-a", name="Driver A")
    drv2 = FakeDriver(id="drv-b", name="Driver B", category="scooter")
    register_driver(drv1)
    register_driver(drv2)
    assert get_driver("drv-a") is drv1
    assert get_driver("drv-b") is drv2


# ---------------------------------------------------------------------------
# Capabilities detection
# ---------------------------------------------------------------------------


def test_basic_capabilities():
    drv = FakeDriver()
    register_driver(drv)
    plugins = list_plugins()
    assert len(plugins) == 1
    info = plugins[0]
    assert set(info.capabilities) == {"detect", "flash", "backup", "info"}


def test_monitorable_capabilities():
    drv = FakeMonitorableDriver(id="mon-drv")
    register_driver(drv)
    info = list_plugins()[0]
    assert "monitor" in info.capabilities


def test_updatable_capabilities():
    drv = FakeUpdatableDriver(id="upd-drv")
    register_driver(drv)
    info = list_plugins()[0]
    assert "update" in info.capabilities


def test_full_capabilities():
    drv = FakeFullDriver(id="full-drv")
    register_driver(drv)
    info = list_plugins()[0]
    assert set(info.capabilities) == {
        "detect",
        "flash",
        "backup",
        "info",
        "monitor",
        "update",
    }


# ---------------------------------------------------------------------------
# list_plugins / list_plugins_by_category
# ---------------------------------------------------------------------------


def test_list_plugins_empty():
    assert list_plugins() == []


def test_list_plugins_returns_plugin_info():
    drv = FakeDriver(id="x", name="X Driver", category="mcu", version="0.5")
    register_driver(drv)
    plugins = list_plugins()
    assert len(plugins) == 1
    p = plugins[0]
    assert isinstance(p, PluginInfo)
    assert p.id == "x"
    assert p.name == "X Driver"
    assert p.category == "mcu"
    assert p.version == "0.5"


def test_list_plugins_by_category():
    register_driver(FakeDriver(id="p1", category="phone"))
    register_driver(FakeDriver(id="p2", category="scooter"))
    register_driver(FakeDriver(id="p3", category="phone"))

    phones = list_plugins_by_category("phone")
    assert len(phones) == 2
    assert all(p.category == "phone" for p in phones)

    scooters = list_plugins_by_category("scooter")
    assert len(scooters) == 1

    routers = list_plugins_by_category("router")
    assert len(routers) == 0


# ---------------------------------------------------------------------------
# discover_plugins
# ---------------------------------------------------------------------------


def test_discover_plugins_empty_dir(tmp_path):
    from web import plugin

    with patch.object(plugin, "_PLUGINS_DIR", tmp_path / "plugins"):
        loaded = plugin.discover_plugins()
    assert loaded == 0
    assert (tmp_path / "plugins" / "__init__.py").exists()


def test_discover_plugins_creates_init(tmp_path):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    # No __init__.py yet

    from web import plugin

    with patch.object(plugin, "_PLUGINS_DIR", plugins_dir):
        plugin.discover_plugins()
    assert (plugins_dir / "__init__.py").exists()


def test_discover_plugins_skips_underscore_files(tmp_path):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    (plugins_dir / "__init__.py").write_text("")
    (plugins_dir / "_internal.py").write_text("x = 1")

    from web import plugin

    with patch.object(plugin, "_PLUGINS_DIR", plugins_dir):
        loaded = plugin.discover_plugins()
    assert loaded == 0


# ---------------------------------------------------------------------------
# PluginInfo dataclass
# ---------------------------------------------------------------------------


def test_plugin_info_defaults():
    p = PluginInfo(
        id="a",
        name="A",
        category="phone",
        version="1.0",
        module_path="web.plugins.a",
    )
    assert p.capabilities == []


def test_plugin_info_with_capabilities():
    p = PluginInfo(
        id="b",
        name="B",
        category="scooter",
        version="2.0",
        module_path="web.plugins.b",
        capabilities=["detect", "flash", "monitor"],
    )
    assert "monitor" in p.capabilities


# ---------------------------------------------------------------------------
# Driver interface methods
# ---------------------------------------------------------------------------


def test_driver_detect():
    drv = FakeDriver()
    register_driver(drv)
    devices = get_driver("test-driver").detect()
    assert len(devices) == 1
    assert devices[0]["id"] == "dev1"


def test_driver_flash():
    drv = FakeDriver()
    register_driver(drv)
    assert get_driver("test-driver").flash("dev1", "/fw.bin", {}) is True


def test_driver_backup():
    drv = FakeDriver()
    register_driver(drv)
    assert get_driver("test-driver").backup("dev1", "/backups") is True


def test_driver_info():
    drv = FakeDriver()
    register_driver(drv)
    info = get_driver("test-driver").info("dev1")
    assert info["model"] == "Test"
