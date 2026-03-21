"""Tests for OS Builder backend and routes."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web.app import app
from web.os_builder import (
    BuildProfile,
    SUPPORTED_BASES,
    estimate_image_size,
    generate_alpine_answers,
    generate_pacstrap_script,
    generate_preseed,
)


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# BuildProfile
# ---------------------------------------------------------------------------


def test_build_profile_defaults():
    p = BuildProfile()
    assert p.base == "debian"
    assert p.suite == "bookworm"
    assert p.arch == "amd64"
    assert p.hostname == "osmosis"
    assert p.output_format == "img"


def test_build_profile_to_dict_and_back():
    p = BuildProfile(name="test-os", base="ubuntu", suite="noble", desktop="gnome")
    d = p.to_dict()
    assert d["name"] == "test-os"
    assert d["desktop"] == "gnome"

    p2 = BuildProfile.from_dict(d)
    assert p2.name == "test-os"
    assert p2.base == "ubuntu"
    assert p2.suite == "noble"
    assert p2.desktop == "gnome"


def test_build_profile_from_dict_ignores_unknown():
    d = {"name": "test", "unknown_field": "value", "base": "arch"}
    p = BuildProfile.from_dict(d)
    assert p.name == "test"
    assert p.base == "arch"
    assert not hasattr(p, "unknown_field")


def test_build_profile_save_and_load(tmp_path):
    p = BuildProfile(name="save-test", base="alpine", suite="3.21")
    path = p.save(tmp_path / "save-test.json")
    assert path.exists()

    loaded = BuildProfile.load(path)
    assert loaded.name == "save-test"
    assert loaded.base == "alpine"
    assert loaded.suite == "3.21"


# ---------------------------------------------------------------------------
# Preseed generation
# ---------------------------------------------------------------------------


def test_generate_preseed_basic():
    p = BuildProfile(hostname="myhost", locale="en_US.UTF-8", timezone="UTC")
    preseed = generate_preseed(p)
    assert "d-i debian-installer/locale string en_US.UTF-8" in preseed
    assert "d-i time/zone string UTC" in preseed
    assert "d-i netcfg/hostname string myhost" in preseed


def test_generate_preseed_static_network():
    p = BuildProfile(network="static", static_ip="10.0.0.5", gateway="10.0.0.1", dns=["8.8.8.8"])
    preseed = generate_preseed(p)
    assert "d-i netcfg/get_ipaddress string 10.0.0.5" in preseed
    assert "d-i netcfg/get_gateway string 10.0.0.1" in preseed


def test_generate_preseed_packages():
    p = BuildProfile(extra_packages=["vim", "htop"], firewall="ufw", ssh_keys=["ssh-ed25519 AAAA"])
    preseed = generate_preseed(p)
    assert "vim" in preseed
    assert "htop" in preseed
    assert "ufw" in preseed
    assert "openssh-server" in preseed


def test_generate_preseed_lvm():
    p = BuildProfile(disk_layout="lvm")
    preseed = generate_preseed(p)
    assert "partman-auto/method string lvm" in preseed


# ---------------------------------------------------------------------------
# Arch script generation
# ---------------------------------------------------------------------------


def test_generate_pacstrap_script_basic():
    p = BuildProfile(hostname="archbox", username="archuser", timezone="Europe/Paris")
    script = generate_pacstrap_script(p)
    assert "#!/bin/bash" in script
    assert "pacstrap" in script
    assert "archbox" in script
    assert "archuser" in script
    assert "Europe/Paris" in script


def test_generate_pacstrap_script_desktop():
    p = BuildProfile(desktop="gnome")
    script = generate_pacstrap_script(p)
    assert "gnome" in script
    assert "gdm" in script


def test_generate_pacstrap_script_post_install():
    p = BuildProfile(post_install_script="echo hello")
    script = generate_pacstrap_script(p)
    assert "echo hello" in script
    assert "POSTSCRIPT" in script


# ---------------------------------------------------------------------------
# Alpine answer file generation
# ---------------------------------------------------------------------------


def test_generate_alpine_answers_basic():
    p = BuildProfile(hostname="alpinebox", keyboard_layout="fr", timezone="UTC")
    answers = generate_alpine_answers(p)
    assert "alpinebox" in answers
    assert "fr" in answers
    assert "UTC" in answers


# ---------------------------------------------------------------------------
# Size estimation
# ---------------------------------------------------------------------------


def test_estimate_image_size_minimal():
    p = BuildProfile(base="alpine", desktop="none", extra_packages=[])
    est = estimate_image_size(p)
    assert est["base_mb"] == 50
    assert est["desktop_mb"] == 0
    assert est["total_mb"] == 50
    assert est["recommended_image_mb"] >= 2048


def test_estimate_image_size_with_desktop():
    p = BuildProfile(base="ubuntu", desktop="gnome", extra_packages=["vim", "git"])
    est = estimate_image_size(p)
    assert est["base_mb"] == 300
    assert est["desktop_mb"] == 1200
    assert est["packages_mb"] == 20
    assert est["total_mb"] == 1520


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------


def test_api_os_builder_options(client):
    resp = client.get("/api/os-builder/options")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "bases" in data
    assert "debian" in data["bases"]
    assert "ubuntu" in data["bases"]
    assert "arch" in data["bases"]
    assert "alpine" in data["bases"]
    assert "desktops" in data
    assert "output_formats" in data
    assert "target_devices" in data


def test_api_os_builder_estimate(client):
    resp = client.post(
        "/api/os-builder/estimate",
        data=json.dumps({"base": "debian", "desktop": "xfce", "extra_packages": ["vim"]}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "total_mb" in data
    assert "recommended_image_mb" in data


def test_api_os_builder_preview_debian(client):
    resp = client.post(
        "/api/os-builder/preview",
        data=json.dumps({"base": "debian", "hostname": "testhost"}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["type"] == "preseed"
    assert "testhost" in data["content"]


def test_api_os_builder_preview_arch(client):
    resp = client.post(
        "/api/os-builder/preview",
        data=json.dumps({"base": "arch", "hostname": "archtest"}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["type"] == "pacstrap-script"
    assert "archtest" in data["content"]


def test_api_os_builder_preview_alpine(client):
    resp = client.post(
        "/api/os-builder/preview",
        data=json.dumps({"base": "alpine", "hostname": "alpinetest"}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["type"] == "alpine-answers"
    assert "alpinetest" in data["content"]


def test_api_os_builder_profiles_crud(client):
    # List (empty initially or with existing)
    resp = client.get("/api/os-builder/profiles")
    assert resp.status_code == 200

    # Save
    resp = client.post(
        "/api/os-builder/profiles",
        data=json.dumps({"name": "test-profile-crud", "base": "debian"}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"]

    # Get
    resp = client.get("/api/os-builder/profiles/test-profile-crud")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["name"] == "test-profile-crud"

    # Delete
    resp = client.delete("/api/os-builder/profiles/test-profile-crud")
    assert resp.status_code == 200
    assert resp.get_json()["ok"]

    # Get after delete
    resp = client.get("/api/os-builder/profiles/test-profile-crud")
    assert resp.status_code == 404


def test_api_os_builder_build_missing_name(client):
    resp = client.post(
        "/api/os-builder/build",
        data=json.dumps({"name": "", "base": "debian"}),
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_api_os_builder_build_bad_base(client):
    resp = client.post(
        "/api/os-builder/build",
        data=json.dumps({"name": "test", "base": "gentoo"}),
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_api_os_builder_builds_list(client):
    resp = client.get("/api/os-builder/builds")
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)
