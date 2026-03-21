"""Plugin architecture — device driver interface and plugin registry.

Each device family (Samsung, scooter, ESP, router, etc.) can be implemented
as a plugin conforming to the DeviceDriver protocol. Plugins are discovered
automatically from the web/plugins/ directory.

A plugin is a Python module with a `driver` attribute that is an instance of
a class implementing the DeviceDriver interface.
"""

import importlib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Device driver interface
# ---------------------------------------------------------------------------


@runtime_checkable
class DeviceDriver(Protocol):
    """Interface that all device plugins must implement."""

    # Identity
    id: str               # unique plugin id (e.g. "samsung-heimdall")
    name: str             # human-readable name
    category: str         # "phone", "scooter", "ebike", "router", "console", "sbc", "mcu"
    version: str          # plugin version

    def detect(self) -> list[dict]:
        """Detect connected devices. Returns list of {id, name, ...} dicts."""
        ...

    def flash(self, device_id: str, fw_path: str, options: dict) -> bool:
        """Flash firmware to a device. Returns True on success."""
        ...

    def backup(self, device_id: str, dest_dir: str) -> bool:
        """Backup device firmware/data. Returns True on success."""
        ...

    def info(self, device_id: str) -> dict:
        """Read device information. Returns a dict of key-value pairs."""
        ...


@runtime_checkable
class MonitorableDriver(Protocol):
    """Optional interface for devices that support live monitoring."""

    def telemetry(self, device_id: str) -> dict:
        """Read current telemetry data. Returns a dict."""
        ...


@runtime_checkable
class UpdatableDriver(Protocol):
    """Optional interface for devices that support OTA updates."""

    def check_update(self, device_id: str) -> dict:
        """Check for available updates. Returns {available: bool, ...}."""
        ...

    def apply_update(self, device_id: str, fw_path: str) -> bool:
        """Apply an OTA update. Returns True on success."""
        ...


# ---------------------------------------------------------------------------
# Plugin registry
# ---------------------------------------------------------------------------


@dataclass
class PluginInfo:
    """Metadata about a registered plugin."""
    id: str
    name: str
    category: str
    version: str
    module_path: str
    capabilities: list[str] = field(default_factory=list)


_registry: dict[str, DeviceDriver] = {}
_plugin_info: dict[str, PluginInfo] = {}
_PLUGINS_DIR = Path(__file__).resolve().parent / "plugins"


def register_driver(driver: DeviceDriver) -> None:
    """Register a device driver plugin."""
    caps = ["detect", "flash", "backup", "info"]
    if isinstance(driver, MonitorableDriver):
        caps.append("monitor")
    if isinstance(driver, UpdatableDriver):
        caps.append("update")

    _registry[driver.id] = driver
    _plugin_info[driver.id] = PluginInfo(
        id=driver.id,
        name=driver.name,
        category=driver.category,
        version=driver.version,
        module_path=type(driver).__module__,
        capabilities=caps,
    )
    log.info("Registered plugin: %s (%s)", driver.id, driver.name)


def get_driver(plugin_id: str) -> DeviceDriver | None:
    """Get a registered driver by ID."""
    return _registry.get(plugin_id)


def list_plugins() -> list[PluginInfo]:
    """List all registered plugins."""
    return list(_plugin_info.values())


def list_plugins_by_category(category: str) -> list[PluginInfo]:
    """List plugins filtered by category."""
    return [p for p in _plugin_info.values() if p.category == category]


def discover_plugins() -> int:
    """Auto-discover and load plugins from the plugins directory.

    Each plugin module must have a `driver` attribute that implements
    DeviceDriver.

    Returns the number of plugins loaded.
    """
    if not _PLUGINS_DIR.is_dir():
        _PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
        # Create __init__.py
        (_PLUGINS_DIR / "__init__.py").write_text("")
        return 0

    if not (_PLUGINS_DIR / "__init__.py").exists():
        (_PLUGINS_DIR / "__init__.py").write_text("")

    loaded = 0
    for py_file in sorted(_PLUGINS_DIR.glob("*.py")):
        if py_file.name.startswith("_"):
            continue
        module_name = f"web.plugins.{py_file.stem}"
        try:
            module = importlib.import_module(module_name)
            driver = getattr(module, "driver", None)
            if driver and isinstance(driver, DeviceDriver):
                register_driver(driver)
                loaded += 1
            else:
                log.warning("Plugin %s has no valid 'driver' attribute", module_name)
        except Exception as e:
            log.error("Failed to load plugin %s: %s", module_name, e)

    return loaded
