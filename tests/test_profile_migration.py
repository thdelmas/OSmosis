"""Tests for declarative device profile migration.

Verifies that every legacy .cfg file (devices, microcontrollers, scooters,
ebikes, t2, medicat) round-trips into well-formed YAML profiles that the
loader and validator both accept.

Tests run against a temporary PROFILES_DIR so they don't pollute the real
profiles/ directory or depend on prior migration state.
"""

import sys
from pathlib import Path
from unittest import mock

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web import device_profile, profile_migration


@pytest.fixture
def tmp_profiles(tmp_path, monkeypatch):
    """Redirect both modules' PROFILES_DIR to a tmp path."""
    monkeypatch.setattr(profile_migration, "PROFILES_DIR", tmp_path)
    monkeypatch.setattr(device_profile, "PROFILES_DIR", tmp_path)
    return tmp_path


def _yaml(path):
    return yaml.safe_load(path.read_text())


# ---------------------------------------------------------------------------
# Per-source migration
# ---------------------------------------------------------------------------


def test_migrate_devices_cfg_creates_profiles(tmp_profiles):
    created = profile_migration.migrate_devices_cfg()
    assert created, "expected at least one device profile"
    sample = tmp_profiles / created[0]
    data = _yaml(sample)
    assert {"id", "name"} <= data.keys()
    assert data["category"] in profile_migration.VALID_CATEGORIES


def test_migrate_microcontrollers_cfg_creates_profiles(tmp_profiles):
    created = profile_migration.migrate_microcontrollers_cfg()
    assert created
    assert all(c.startswith("mcu/") for c in created)
    data = _yaml(tmp_profiles / created[0])
    assert data["category"] == "mcu"


def test_migrate_scooters_cfg_creates_profiles(tmp_profiles):
    created = profile_migration.migrate_scooters_cfg()
    assert created
    assert all(c.startswith("scooter/") for c in created)
    data = _yaml(tmp_profiles / created[0])
    assert data["category"] == "scooter"
    # Flash steps should always include download + verify scaffold
    step_ids = {s["id"] for s in data["flash_steps"]}
    assert {"download", "verify", "post-configure"} <= step_ids


def test_migrate_ebikes_cfg_creates_profiles(tmp_profiles):
    created = profile_migration.migrate_ebikes_cfg()
    assert created
    assert all(c.startswith("ebike/") for c in created)
    data = _yaml(tmp_profiles / created[0])
    assert data["category"] == "ebike"
    assert data["support_status"] in profile_migration.VALID_SUPPORT_STATUSES


def test_migrate_t2_cfg_creates_profiles(tmp_profiles):
    created = profile_migration.migrate_t2_cfg()
    assert created
    assert all(c.startswith("t2/") for c in created)
    data = _yaml(tmp_profiles / created[0])
    assert data["brand"] == "Apple"
    assert data["flash_method"] == "dfu"


def test_migrate_medicat_cfg_creates_profiles(tmp_profiles):
    created = profile_migration.migrate_medicat_cfg()
    assert created
    assert all(c.startswith("medicat/") for c in created)
    data = _yaml(tmp_profiles / created[0])
    assert "min_usb_gb" in data


# ---------------------------------------------------------------------------
# Idempotency — running migration twice must not overwrite or duplicate
# ---------------------------------------------------------------------------


def test_migrate_all_is_idempotent(tmp_profiles):
    first = profile_migration.migrate_all()
    second = profile_migration.migrate_all()
    assert first, "first run should create profiles"
    assert second == {}, "second run should be a no-op"


# ---------------------------------------------------------------------------
# End-to-end: every migrated profile loads and validates
# ---------------------------------------------------------------------------


def test_migrated_profiles_all_validate(tmp_profiles):
    profile_migration.migrate_all()
    errors = profile_migration.validate_all_profiles()
    assert errors == {}, f"validation failed: {errors}"


def test_migrated_profiles_all_load(tmp_profiles):
    profile_migration.migrate_all()
    profiles = device_profile.load_all_profiles()
    # Across the six .cfg files we expect well over 100 entries
    assert len(profiles) >= 100
    # Loader must produce DeviceProfile instances with required fields populated
    for p in profiles:
        assert p.id
        assert p.name


def test_validate_rejects_unknown_category(tmp_profiles):
    bad = tmp_profiles / "bad.yaml"
    bad.write_text(yaml.dump({"id": "x", "name": "X", "category": "blender"}))
    errors = profile_migration.validate_profile(bad)
    assert any("Unknown category" in e for e in errors)


def test_validate_requires_id_and_name(tmp_profiles):
    bad = tmp_profiles / "bad.yaml"
    bad.write_text(yaml.dump({"category": "phone"}))
    errors = profile_migration.validate_profile(bad)
    assert any("Missing required field: id" in e for e in errors)
    assert any("Missing required field: name" in e for e in errors)


# ---------------------------------------------------------------------------
# Empty-source guards
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fn, parser_path",
    [
        (
            profile_migration.migrate_scooters_cfg,
            "web.routes.scooter.parse_scooters_cfg",
        ),
        (
            profile_migration.migrate_ebikes_cfg,
            "web.routes.ebike.parse_ebikes_cfg",
        ),
        (profile_migration.migrate_t2_cfg, "web.routes.t2.parse_t2_cfg"),
        (
            profile_migration.migrate_medicat_cfg,
            "web.routes.medicat.parse_medicat_cfg",
        ),
    ],
)
def test_migrate_empty_source_returns_empty(tmp_profiles, fn, parser_path):
    with mock.patch(parser_path, return_value=[]):
        assert fn() == []
