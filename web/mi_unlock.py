"""Xiaomi bootloader unlock via fastboot.

Separated from mi_auth to keep modules focused.  Contains mi_unlock_device
and the fastboot / encrypted-API helpers it needs.
"""

import hashlib
import logging
import random
import shutil
import subprocess
import time
from pathlib import Path

from web.mi_auth import _get_service, mi_resolve_unlock_domain

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Fastboot helpers
# ---------------------------------------------------------------------------


def _fastboot_getvar(fastboot_cmd: str, var_name: str) -> str | None:
    """Read a single fastboot variable, return its value or None."""
    try:
        result = subprocess.run(
            [fastboot_cmd, "getvar", var_name],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception:
        return None

    for line in (result.stderr + result.stdout).splitlines():
        if line.startswith(f"{var_name}:"):
            val = line.split(":", 1)[1].strip()
            if val:
                return val
    return None


def _fastboot_get_device_token(fastboot_cmd: str) -> str | None:
    """Obtain the device token via fastboot (tries two methods)."""
    # Method 1: getvar token
    token = _fastboot_getvar(fastboot_cmd, "token")
    if token:
        return token

    # Method 2: oem get_token
    try:
        result = subprocess.run(
            [fastboot_cmd, "oem", "get_token"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception:
        return None

    lines = []
    for line in (result.stderr + result.stdout).splitlines():
        if "token:" in line:
            val = line.split("token:", 1)[1].strip()
            if val:
                lines.append(val)

    if len(lines) > 1:
        return "".join(lines)
    return lines[0] if lines else None


# ---------------------------------------------------------------------------
# mi_unlock_device
# ---------------------------------------------------------------------------


def mi_unlock_device(tokens: dict, domain_override: str | None = None) -> dict:
    """Perform the actual bootloader unlock via fastboot.

    Returns:
      {"status": "ok",    "message": "Bootloader unlocked successfully"}
      {"status": "error", "message": "...", "code": <int or None>}
    """
    from miunlock.utils import _send  # encrypted API helper

    fastboot_cmd = shutil.which("fastboot")
    if not fastboot_cmd:
        return {
            "status": "error",
            "message": "fastboot not found in PATH",
            "code": None,
        }

    # Verify device is connected in fastboot mode
    try:
        fb_check = subprocess.run(
            [fastboot_cmd, "devices"], capture_output=True, text=True, timeout=5
        )
    except Exception as exc:
        return {
            "status": "error",
            "message": f"fastboot devices failed: {exc}",
            "code": None,
        }

    if not fb_check.stdout.strip():
        return {
            "status": "error",
            "message": "No device detected in fastboot mode",
            "code": None,
        }

    # Obtain service token
    sid = "unlockApi"
    svc = _get_service(tokens, sid)
    if "error" in svc:
        return {"status": "error", "message": svc["error"], "code": None}

    ssecurity = svc["ssecurity"]
    svc_cookies = svc["cookies"]

    # Resolve unlock domain
    domain = domain_override
    if not domain:
        domain = mi_resolve_unlock_domain(tokens)
    if not domain:
        return {
            "status": "error",
            "message": "Could not resolve unlock domain for account region",
            "code": None,
        }

    pc_id = hashlib.md5(tokens.get("deviceId", "").encode()).hexdigest()  # noqa: S324

    # Get server nonce
    r = "".join(random.choices("abcdefghijklmnopqrstuvwxyz", k=16))  # noqa: S311
    nonce_resp = _send(
        "/api/v2/nonce", {"r": r}, domain, ssecurity, svc_cookies
    )

    if "error" in nonce_resp:
        return {
            "status": "error",
            "message": f"Nonce error: {nonce_resp['error']}",
            "code": None,
        }
    if nonce_resp.get("code") != 0:
        return {
            "status": "error",
            "message": f"Nonce response: {nonce_resp}",
            "code": nonce_resp.get("code"),
        }

    nonce = nonce_resp["nonce"]

    # Get product
    product = _fastboot_getvar(fastboot_cmd, "product")
    if not product:
        return {
            "status": "error",
            "message": "Could not get product from fastboot",
            "code": None,
        }

    # Clear step
    clear_resp = _send(
        "/api/v2/unlock/device/clear",
        {"appId": "1", "data": {"product": product}, "nonce": nonce},
        domain,
        ssecurity,
        svc_cookies,
    )

    if "error" in clear_resp:
        return {
            "status": "error",
            "message": f"Clear error: {clear_resp['error']}",
            "code": None,
        }
    if clear_resp.get("code") != 0:
        return {
            "status": "error",
            "message": f"Clear response: {clear_resp}",
            "code": clear_resp.get("code"),
        }

    # Get device token
    device_token = _fastboot_get_device_token(fastboot_cmd)
    if not device_token:
        return {
            "status": "error",
            "message": "Could not get device token via fastboot",
            "code": None,
        }

    # Unlock API call
    unlock_data = {
        "clientId": "2",
        "clientVersion": "7.6.727.43",
        "deviceInfo": {
            "boardVersion": "",
            "deviceName": "",
            "product": product,
            "socId": "",
        },
        "deviceToken": device_token,
        "language": "en",
        "operate": "unlock",
        "pcId": pc_id,
        "region": "",
        "uid": svc_cookies.get("userId"),
    }

    unlock_result = _send(
        "/api/v3/ahaUnlock",
        {"appId": "1", "data": unlock_data, "nonce": nonce},
        domain,
        ssecurity,
        svc_cookies,
    )

    if "error" in unlock_result:
        return {
            "status": "error",
            "message": f"Unlock error: {unlock_result['error']}",
            "code": None,
        }
    if unlock_result.get("code") != 0:
        desc = (
            unlock_result.get("descEN")
            or unlock_result.get("description")
            or str(unlock_result)
        )
        code = unlock_result.get("code")
        return {"status": "error", "message": desc, "code": code}

    # Write encrypted unlock data to temp file and flash
    encrypt_data = unlock_result["encryptData"]
    ed_bytes = bytes.fromhex(encrypt_data)
    ed_file = Path.home() / f"{int(time.time())}encryptData"
    ed_file.write_bytes(ed_bytes)

    try:
        # Stage encrypted data
        rc = subprocess.run(
            [fastboot_cmd, "stage", str(ed_file)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if rc.returncode != 0:
            output = (rc.stderr + rc.stdout).strip()
            return {
                "status": "error",
                "message": f"fastboot stage failed: {output}",
                "code": None,
            }

        # OEM unlock
        rc = subprocess.run(
            [fastboot_cmd, "oem", "unlock"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = (rc.stderr + rc.stdout).strip()
        if rc.returncode != 0:
            return {
                "status": "error",
                "message": f"oem unlock failed: {output}",
                "code": None,
            }
    finally:
        # Clean up temp file
        ed_file.unlink(missing_ok=True)

    return {"status": "ok", "message": "Bootloader unlocked successfully"}
