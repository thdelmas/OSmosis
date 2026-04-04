"""Structured error handling middleware for OSmosis.

Provides:
- OsmosisError hierarchy with error codes, HTTP status, and user-facing hints
- Flask error handlers that return consistent JSON responses
- Helpers for common error patterns (missing tool, subprocess failure, etc.)

Every API error response follows the shape:
    {"error": "<code>", "message": "<human-readable>", "hint": "<actionable advice>"}
"""

import logging
import subprocess
import traceback

from flask import Flask, jsonify

log = logging.getLogger("osmosis.errors")


# ---------------------------------------------------------------------------
# Error hierarchy
# ---------------------------------------------------------------------------


class OsmosisError(Exception):
    """Base error — all OSmosis-specific errors inherit from this."""

    status_code: int = 500
    error_code: str = "internal_error"
    hint: str = ""

    def __init__(
        self, message: str, *, hint: str = "", status_code: int | None = None
    ):
        super().__init__(message)
        self.message = message
        if hint:
            self.hint = hint
        if status_code is not None:
            self.status_code = status_code

    def to_dict(self) -> dict:
        d: dict = {"error": self.error_code, "message": self.message}
        if self.hint:
            d["hint"] = self.hint
        return d


class ToolNotFoundError(OsmosisError):
    """A required external tool (adb, heimdall, fastboot, ...) is not installed."""

    status_code = 503
    error_code = "tool_not_found"

    def __init__(self, tool: str, *, hint: str = ""):
        default_hint = f"Install '{tool}' and make sure it's on your PATH."
        super().__init__(
            f"Required tool not found: {tool}",
            hint=hint or default_hint,
        )
        self.tool = tool


class DeviceNotFoundError(OsmosisError):
    """No device detected on USB / ADB / fastboot."""

    status_code = 404
    error_code = "device_not_found"
    hint = "Connect a device via USB and make sure USB debugging is enabled."


class DeviceUnauthorizedError(OsmosisError):
    """Device connected but not authorized for ADB."""

    status_code = 403
    error_code = "device_unauthorized"
    hint = "Check the device screen for an authorization prompt and tap Allow."


class ValidationError(OsmosisError):
    """Bad input from the client."""

    status_code = 400
    error_code = "validation_error"


class FileNotFoundOnDiskError(OsmosisError):
    """A file path supplied by the client doesn't exist."""

    status_code = 400
    error_code = "file_not_found"

    def __init__(self, path: str):
        super().__init__(f"File not found: {path}")
        self.path = path


class SubprocessError(OsmosisError):
    """An external command failed."""

    status_code = 500
    error_code = "command_failed"

    def __init__(
        self, cmd: str, returncode: int, stderr: str = "", *, hint: str = ""
    ):
        msg = f"Command '{cmd}' failed with exit code {returncode}"
        if stderr:
            msg += f": {stderr[:300]}"
        super().__init__(msg, hint=hint)
        self.cmd = cmd
        self.returncode = returncode
        self.stderr = stderr


class TimeoutError(OsmosisError):
    """An external command or device operation timed out."""

    status_code = 504
    error_code = "timeout"
    hint = "The operation timed out. Check that the device is responding."


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def require_tool(tool: str) -> None:
    """Raise ToolNotFoundError if *tool* is not on PATH."""
    import shutil

    if not shutil.which(tool):
        raise ToolNotFoundError(tool)


def run_checked(
    cmd: list[str],
    *,
    timeout: int = 30,
    hint: str = "",
) -> subprocess.CompletedProcess:
    """Run a subprocess and raise a structured error on failure.

    Replaces the pattern:
        try:
            result = subprocess.run(...)
            if result.returncode != 0: ...
        except Exception: pass

    Returns the CompletedProcess on success.
    """
    cmd_str = cmd[0] if cmd else "<empty>"
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
    except FileNotFoundError as err:
        raise ToolNotFoundError(cmd_str) from err
    except subprocess.TimeoutExpired as err:
        raise TimeoutError(
            f"Command '{cmd_str}' timed out after {timeout}s"
        ) from err

    if result.returncode != 0:
        raise SubprocessError(
            cmd_str,
            result.returncode,
            stderr=result.stderr.strip(),
            hint=hint,
        )
    return result


# ---------------------------------------------------------------------------
# Flask integration
# ---------------------------------------------------------------------------


def init_error_handlers(app: Flask) -> None:
    """Register global error handlers that return consistent JSON for API routes."""

    @app.errorhandler(OsmosisError)
    def handle_osmosis_error(exc: OsmosisError):
        log.warning("%s [%s]: %s", exc.error_code, exc.status_code, exc.message)
        return jsonify(exc.to_dict()), exc.status_code

    @app.errorhandler(404)
    def handle_404(_exc):
        return jsonify(
            {
                "error": "not_found",
                "message": "The requested endpoint does not exist.",
            }
        ), 404

    @app.errorhandler(405)
    def handle_405(_exc):
        return jsonify(
            {
                "error": "method_not_allowed",
                "message": "HTTP method not allowed for this endpoint.",
            }
        ), 405

    @app.errorhandler(Exception)
    def handle_unexpected(exc: Exception):
        # Don't intercept HTTPException subclasses that Flask handles natively
        from werkzeug.exceptions import HTTPException

        if isinstance(exc, HTTPException):
            return exc

        log.error("Unhandled exception: %s\n%s", exc, traceback.format_exc())
        return (
            jsonify(
                {
                    "error": "internal_error",
                    "message": "An unexpected error occurred.",
                    "hint": "Check the server logs for details.",
                }
            ),
            500,
        )
