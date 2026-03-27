"""Tests for the structured error handling middleware."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flask import Flask, jsonify

from web.errors import (
    DeviceNotFoundError,
    DeviceUnauthorizedError,
    FileNotFoundOnDiskError,
    OsmosisError,
    SubprocessError,
    TimeoutError,
    ToolNotFoundError,
    ValidationError,
    init_error_handlers,
    require_tool,
    run_checked,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def error_app():
    """Minimal Flask app with error handlers registered."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    init_error_handlers(app)

    @app.route("/raise-tool")
    def _raise_tool():
        raise ToolNotFoundError("heimdall")

    @app.route("/raise-device")
    def _raise_device():
        raise DeviceNotFoundError("No device on USB bus")

    @app.route("/raise-unauthorized")
    def _raise_unauthorized():
        raise DeviceUnauthorizedError("Device not authorized")

    @app.route("/raise-validation")
    def _raise_validation():
        raise ValidationError("fw_zip is required", hint="Provide the path to a firmware ZIP file.")

    @app.route("/raise-file")
    def _raise_file():
        raise FileNotFoundOnDiskError("/tmp/missing.zip")

    @app.route("/raise-subprocess")
    def _raise_subprocess():
        raise SubprocessError("heimdall", 1, stderr="ERROR: Failed to detect device")

    @app.route("/raise-timeout")
    def _raise_timeout():
        raise TimeoutError("flashrom probe timed out")

    @app.route("/raise-generic")
    def _raise_generic():
        raise RuntimeError("something broke")

    @app.route("/ok")
    def _ok():
        return jsonify({"status": "ok"})

    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# Tests: structured error responses
# ---------------------------------------------------------------------------


def test_tool_not_found_returns_503(error_app):
    resp = error_app.get("/raise-tool")
    assert resp.status_code == 503
    data = resp.get_json()
    assert data["error"] == "tool_not_found"
    assert "heimdall" in data["message"]
    assert "hint" in data


def test_device_not_found_returns_404(error_app):
    resp = error_app.get("/raise-device")
    assert resp.status_code == 404
    data = resp.get_json()
    assert data["error"] == "device_not_found"


def test_device_unauthorized_returns_403(error_app):
    resp = error_app.get("/raise-unauthorized")
    assert resp.status_code == 403
    data = resp.get_json()
    assert data["error"] == "device_unauthorized"
    assert "hint" in data


def test_validation_error_returns_400(error_app):
    resp = error_app.get("/raise-validation")
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["error"] == "validation_error"
    assert "hint" in data


def test_file_not_found_returns_400(error_app):
    resp = error_app.get("/raise-file")
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["error"] == "file_not_found"
    assert "/tmp/missing.zip" in data["message"]


def test_subprocess_error_returns_500(error_app):
    resp = error_app.get("/raise-subprocess")
    assert resp.status_code == 500
    data = resp.get_json()
    assert data["error"] == "command_failed"
    assert "heimdall" in data["message"]


def test_timeout_error_returns_504(error_app):
    resp = error_app.get("/raise-timeout")
    assert resp.status_code == 504
    data = resp.get_json()
    assert data["error"] == "timeout"


def test_unhandled_exception_returns_500(error_app):
    resp = error_app.get("/raise-generic")
    assert resp.status_code == 500
    data = resp.get_json()
    assert data["error"] == "internal_error"
    # Must NOT leak the internal error message
    assert "something broke" not in data["message"]


def test_404_returns_json(error_app):
    resp = error_app.get("/nonexistent-route")
    assert resp.status_code == 404
    data = resp.get_json()
    assert data["error"] == "not_found"


def test_ok_route_unaffected(error_app):
    resp = error_app.get("/ok")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Tests: error hierarchy
# ---------------------------------------------------------------------------


def test_all_errors_inherit_from_osmosis_error():
    errors = [
        ToolNotFoundError("x"),
        DeviceNotFoundError("x"),
        DeviceUnauthorizedError("x"),
        ValidationError("x"),
        FileNotFoundOnDiskError("/x"),
        SubprocessError("x", 1),
        TimeoutError("x"),
    ]
    for err in errors:
        assert isinstance(err, OsmosisError)
        d = err.to_dict()
        assert "error" in d
        assert "message" in d


def test_custom_status_code_override():
    err = OsmosisError("test", status_code=418)
    assert err.status_code == 418


# ---------------------------------------------------------------------------
# Tests: require_tool helper
# ---------------------------------------------------------------------------


def test_require_tool_missing(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda cmd: None)
    with pytest.raises(ToolNotFoundError) as exc_info:
        require_tool("nonexistent-tool")
    assert exc_info.value.tool == "nonexistent-tool"


def test_require_tool_present(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda cmd: f"/usr/bin/{cmd}")
    require_tool("adb")  # Should not raise


# ---------------------------------------------------------------------------
# Tests: run_checked helper
# ---------------------------------------------------------------------------


def test_run_checked_success(monkeypatch):
    import subprocess as sp

    def fake_run(cmd, **kw):
        return sp.CompletedProcess(cmd, 0, stdout="ok\n", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)
    result = run_checked(["echo", "hi"])
    assert result.returncode == 0


def test_run_checked_failure(monkeypatch):
    import subprocess as sp

    def fake_run(cmd, **kw):
        return sp.CompletedProcess(cmd, 1, stdout="", stderr="fatal error")

    monkeypatch.setattr("subprocess.run", fake_run)
    with pytest.raises(SubprocessError) as exc_info:
        run_checked(["bad-cmd"])
    assert exc_info.value.returncode == 1
    assert "fatal error" in exc_info.value.stderr


def test_run_checked_timeout(monkeypatch):
    import subprocess as sp

    def fake_run(cmd, **kw):
        raise sp.TimeoutExpired(cmd, kw.get("timeout", 30))

    monkeypatch.setattr("subprocess.run", fake_run)
    with pytest.raises(TimeoutError):
        run_checked(["slow-cmd"], timeout=5)


def test_run_checked_tool_missing(monkeypatch):
    def fake_run(cmd, **kw):
        raise FileNotFoundError()

    monkeypatch.setattr("subprocess.run", fake_run)
    with pytest.raises(ToolNotFoundError):
        run_checked(["missing-tool"])
