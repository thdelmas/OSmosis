"""Tests for new device family routes: vacuum, lab, keyboard, synth."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web.app import app
from web.routes.keyboard import _KEYBOARD_BOOTLOADERS
from web.routes.synth import _SYNTH_MODULES
from web.routes.vacuum import _VACUUM_MODELS


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# Robot vacuum
# ---------------------------------------------------------------------------


def test_vacuum_models(client):
    resp = client.get("/api/vacuum/models")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert len(data) >= 5


def test_vacuum_models_filter_brand(client):
    resp = client.get("/api/vacuum/models?brand=roborock")
    data = resp.get_json()
    assert all("Roborock" in m["brand"] for m in data)


def test_vacuum_check_model_found(client):
    resp = client.get("/api/vacuum/check-model?model=roborock.vacuum.s5")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["supported"] is True
    assert data["valetudo"] is True


def test_vacuum_check_model_not_found(client):
    resp = client.get("/api/vacuum/check-model?model=fake.vacuum.x9")
    assert resp.status_code == 404


def test_vacuum_flash_guide_ota(client):
    resp = client.post(
        "/api/vacuum/flash-guide",
        json={"model": "roborock.vacuum.s5", "method": "ota"},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["steps"]) >= 3
    step_ids = [s["id"] for s in data["steps"]]
    assert "dustbuilder" in step_ids
    assert "valetudo-setup" in step_ids


def test_vacuum_flash_guide_uart(client):
    resp = client.post(
        "/api/vacuum/flash-guide",
        json={"model": "roborock.vacuum.s5", "method": "uart"},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    step_ids = [s["id"] for s in data["steps"]]
    assert "uart-access" in step_ids


def test_vacuum_flash_guide_bad_method(client):
    resp = client.post(
        "/api/vacuum/flash-guide",
        json={"model": "roborock.vacuum.a27", "method": "uart"},
    )
    # Q7 Max only supports OTA
    assert resp.status_code == 400


def test_vacuum_verify_missing_file(client):
    resp = client.post(
        "/api/vacuum/verify-firmware", json={"fw_path": "/nonexistent.pkg"}
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Lab equipment
# ---------------------------------------------------------------------------


def test_lab_detect_no_device(client):
    with patch(
        "web.routes.lab_equipment._find_usbtmc_devices", return_value=[]
    ):
        resp = client.get("/api/lab/detect")
    assert resp.status_code == 404


def test_lab_query_missing_params(client):
    resp = client.post("/api/lab/query", json={})
    assert resp.status_code == 400


def test_lab_query_missing_command(client):
    resp = client.post("/api/lab/query", json={"target": "/dev/usbtmc0"})
    assert resp.status_code == 400


def test_lab_rigol_info_no_target(client):
    resp = client.get("/api/lab/rigol/info")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Keyboard
# ---------------------------------------------------------------------------


def test_keyboard_bootloaders_has_entries():
    assert len(_KEYBOARD_BOOTLOADERS) >= 5


def test_keyboard_detect_no_device(client):
    with patch(
        "web.routes.keyboard._detect_keyboard_bootloader", return_value=[]
    ):
        resp = client.get("/api/keyboard/detect")
    assert resp.status_code == 404
    assert "bootloader" in resp.get_json()["hint"].lower()


def test_keyboard_tools(client):
    resp = client.get("/api/keyboard/tools")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "qmk" in data
    assert "dfu_util" in data


def test_keyboard_flash_missing_file(client):
    resp = client.post(
        "/api/keyboard/flash",
        json={"fw_path": "/nonexistent.hex", "method": "dfu-util"},
    )
    assert resp.status_code == 400


def test_keyboard_flash_no_method(client):
    resp = client.post("/api/keyboard/flash", json={"fw_path": "/tmp/x"})
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Synth
# ---------------------------------------------------------------------------


def test_synth_modules(client):
    resp = client.get("/api/synth/modules")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) >= 5


def test_synth_modules_filter_brand(client):
    resp = client.get("/api/synth/modules?brand=korg")
    data = resp.get_json()
    assert all("Korg" in m["brand"] for m in data)


def test_synth_flash_guide_wav(client):
    resp = client.get("/api/synth/flash-guide/mi-plaits")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["method"] == "wav"
    assert len(data["steps"]) >= 3


def test_synth_flash_guide_korg(client):
    resp = client.get("/api/synth/flash-guide/korg-prologue")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["method"] == "sound-librarian"


def test_synth_flash_guide_unknown(client):
    resp = client.get("/api/synth/flash-guide/nonexistent")
    assert resp.status_code == 404


def test_synth_play_missing_file(client):
    resp = client.post(
        "/api/synth/play-firmware", json={"wav_path": "/nonexistent.wav"}
    )
    assert resp.status_code == 400


def test_synth_play_wrong_extension(client):
    # Create a temp file with wrong extension
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        f.write(b"fake")
        tmp = f.name
    resp = client.post("/api/synth/play-firmware", json={"wav_path": tmp})
    assert resp.status_code == 400
    Path(tmp).unlink()


def test_synth_modules_registry():
    assert len(_SYNTH_MODULES) >= 7
    assert "mi-plaits" in _SYNTH_MODULES
    assert "korg-prologue" in _SYNTH_MODULES


def test_vacuum_models_registry():
    assert len(_VACUUM_MODELS) >= 5
    assert "roborock.vacuum.s5" in _VACUUM_MODELS
