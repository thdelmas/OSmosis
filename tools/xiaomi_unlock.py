#!/usr/bin/env python3
"""Non-interactive Xiaomi bootloader unlock using miunlock library internals.

Usage:
    python3 tools/xiaomi_unlock.py login <email> <password>
    python3 tools/xiaomi_unlock.py send-code
    python3 tools/xiaomi_unlock.py verify <code>
    python3 tools/xiaomi_unlock.py unlock

Step 1: 'login' authenticates with Xiaomi (saves state to ~/.unlockApi/)
Step 2: 'send-code' requests the 2FA code be sent to email/phone
Step 3: 'verify' completes 2FA with the received code
Step 4: 'unlock' performs the actual bootloader unlock via fastboot
"""

import hashlib
import json
import os
import pickle  # noqa: S403
import sys
import uuid
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests
from migate.config import HEADERS, SERVICELOGIN_URL, SERVICELOGINAUTH2_URL

STATE_DIR = Path.home() / ".unlockApi"
COOKIES_FILE = STATE_DIR / "cookies.pkl"
PENDING_FILE = STATE_DIR / "pending_verify.pkl"


def cmd_login(email: str, password: str):
    """Authenticate with Xiaomi — triggers 2FA if needed."""

    # Check for existing session
    if COOKIES_FILE.exists():
        tokens = pickle.loads(COOKIES_FILE.read_bytes())  # noqa: S301
        print(f"Already logged in as userId={tokens.get('userId')}")
        print(
            "Run 'unlock' to proceed, or delete ~/.unlockApi/cookies.pkl to re-login."
        )
        return True

    sid = "unlockApi"
    auth_data = {"sid": sid, "checkSafeAddress": True, "_json": True}

    # Get login page params
    resp = requests.get(SERVICELOGIN_URL, params=auth_data, timeout=15)
    page = json.loads(resp.text[11:])
    auth_data["serviceParam"] = page["serviceParam"]
    auth_data["qs"] = page["qs"]
    auth_data["callback"] = page["callback"]
    auth_data["_sign"] = page["_sign"]

    # Login
    pwd_hash = hashlib.md5(password.encode()).hexdigest().upper()  # noqa: S324
    auth_data["user"] = email
    auth_data["hash"] = pwd_hash
    device_id = "wb_" + str(
        uuid.UUID(
            bytes=hashlib.md5(  # noqa: S324
                (
                    email + pwd_hash + json.dumps(auth_data, sort_keys=True)
                ).encode()
            ).digest()
        )
    )
    cookies = {"deviceId": device_id}

    resp = requests.post(
        SERVICELOGINAUTH2_URL,
        headers=HEADERS,
        data=auth_data,
        cookies=cookies,
        timeout=15,
    )
    result = json.loads(resp.text[11:])

    if result.get("code") == 70016:
        print("ERROR: Invalid password or username.")
        return False

    if result.get("code") == 87001:
        print("CAPTCHA required — not supported in non-interactive mode.")
        print("Try again later or use the interactive miunlock tool.")
        return False

    # Check if 2FA is needed
    if "notificationUrl" in result:
        notification_url = result["notificationUrl"]

        if any(
            x in notification_url
            for x in ["callback", "SetEmail", "BindAppealOrSafePhone"]
        ):
            print(f"ERROR: Action required at: {notification_url}")
            return False

        context = parse_qs(urlparse(notification_url).query)["context"][0]

        # Save state for verify step
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        state = {
            "context": context,
            "auth_data": auth_data,
            "cookies": cookies,
            "device_id": device_id,
        }
        PENDING_FILE.write_bytes(pickle.dumps(state))
        print("2FA required. Check your email for the verification code.")
        print("Then run: python3 tools/xiaomi_unlock.py verify <code>")
        return True

    # No 2FA needed — save session directly
    session_cookies = resp.cookies.get_dict()
    required = {"deviceId", "passToken", "userId"}
    missing = required - session_cookies.keys()
    if missing:
        print(f"ERROR: Missing keys: {', '.join(missing)}")
        print(f"Response: {result}")
        return False

    tokens = {k: session_cookies[k] for k in required}
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    COOKIES_FILE.write_bytes(pickle.dumps(tokens))
    print(f"Login successful! userId={tokens['userId']}")
    print("Run: python3 tools/xiaomi_unlock.py unlock")
    return True


def cmd_send_code():
    """Send the 2FA verification code to email."""
    if not PENDING_FILE.exists():
        print("ERROR: No pending verification. Run 'login' first.")
        return False

    state = pickle.loads(PENDING_FILE.read_bytes())  # noqa: S301
    context = state["context"]
    auth_data = state["auth_data"]
    cookies = state["cookies"]

    from migate.config import HEADERS, LIST_URL

    # Get available verification methods
    params = {"sid": auth_data["sid"], "supportedMask": "0", "context": context}
    resp = requests.get(
        LIST_URL, params=params, headers=HEADERS, cookies=cookies, timeout=15
    )
    cookies.update(resp.cookies.get_dict())
    result = json.loads(resp.text[11:])
    options = result.get("options", [])
    print(f"Available methods: {options} (4=Phone, 8=Email)")

    # Prefer email
    if 8 in options:
        address_type = "EM"
    elif 4 in options:
        address_type = "PH"
    else:
        print(f"ERROR: No supported verification options: {result}")
        return False

    # Send the code
    from migate.login.sendcode import send_verification_code

    send_result = send_verification_code(address_type, cookies)
    if isinstance(send_result, dict) and "error" in send_result:
        print(f"ERROR: {send_result['error']}")
        return False

    # Save updated cookies and address type
    state["cookies"] = cookies
    state["address_type"] = address_type
    PENDING_FILE.write_bytes(pickle.dumps(state))

    label = "email" if address_type == "EM" else "phone"
    print(f"Code sent to {label}!")
    print("Run: python3 tools/xiaomi_unlock.py verify <code>")
    return True


def cmd_verify(code: str):
    """Complete 2FA verification with the emailed code."""
    if not PENDING_FILE.exists():
        print("ERROR: No pending verification. Run 'login' first.")
        return False

    state = pickle.loads(PENDING_FILE.read_bytes())  # noqa: S301
    auth_data = state["auth_data"]
    cookies = state["cookies"]
    address_type = state.get("address_type", "EM")

    from migate.config import HEADERS, VERIFY_EM, VERIFY_PH
    from migate.config import SERVICELOGINAUTH2_URL as AUTH_URL

    # Verify the code
    url = VERIFY_EM if address_type == "EM" else VERIFY_PH
    resp = requests.post(
        url,
        data={"ticket": code, "trust": "true", "_json": "true"},
        headers=HEADERS,
        cookies=cookies,
        timeout=15,
    )
    result = json.loads(resp.text[11:])

    if result.get("code") == 70014:
        print(
            "ERROR: Invalid code. Check and try again (don't re-run send-code)."
        )
        return False
    if result.get("code") != 0:
        print(f"ERROR: {result}")
        return False

    # Follow redirects to complete auth
    location = result.get("location")
    if not location:
        print(f"ERROR: No redirect location in response: {result}")
        return False

    resp = requests.get(
        location,
        headers=HEADERS,
        allow_redirects=False,
        cookies=cookies,
        timeout=15,
    )
    redirect_url = resp.headers.get("Location")
    resp = requests.get(
        redirect_url,
        headers=HEADERS,
        allow_redirects=False,
        cookies=cookies,
        timeout=15,
    )
    cookies.update(resp.cookies.get_dict())

    # Final auth call
    resp = requests.post(
        AUTH_URL, headers=HEADERS, data=auth_data, cookies=cookies, timeout=15
    )
    session_cookies = resp.cookies.get_dict()

    required = {"deviceId", "passToken", "userId"}
    missing = required - session_cookies.keys()
    if missing:
        result = json.loads(resp.text[11:])
        print(f"ERROR: Missing keys: {', '.join(missing)}")
        print(f"Response: {result}")
        return False

    tokens = {k: session_cookies[k] for k in required}
    COOKIES_FILE.write_bytes(pickle.dumps(tokens))
    PENDING_FILE.unlink(missing_ok=True)
    print(f"2FA verified! userId={tokens['userId']}")
    print("Run: python3 tools/xiaomi_unlock.py unlock")
    return True


def cmd_unlock():
    """Perform the actual bootloader unlock."""
    import shutil
    import subprocess
    import time

    if not COOKIES_FILE.exists():
        print("ERROR: Not logged in. Run 'login' first.")
        return False

    tokens = pickle.loads(COOKIES_FILE.read_bytes())  # noqa: S301
    print(f"Using session: userId={tokens['userId']}")

    fastboot_cmd = shutil.which("fastboot")
    if not fastboot_cmd:
        print("ERROR: fastboot not found in PATH")
        return False

    # Check device is in fastboot
    result = subprocess.run(
        [fastboot_cmd, "devices"], capture_output=True, text=True, timeout=5
    )
    if not result.stdout.strip():
        print("ERROR: No device in fastboot mode")
        return False
    print(f"Device: {result.stdout.strip()}")

    # Get service token
    sid = "unlockApi"
    import migate

    # Re-use cached passToken
    pc_id = hashlib.md5(tokens.get("deviceId", "").encode()).hexdigest()  # noqa: S324

    # Resolve domain non-interactively (get_domain has interactive prompts)
    from miunlock.region.domain import domain as get_domain_url
    from miunlock.region.region import region as get_region
    from miunlock.region.region_config import region_config

    region_result = get_region(tokens)
    if "error" in region_result:
        print(f"ERROR getting region: {region_result['error']}")
        return False
    region_name = region_result["success"]
    print(f"Account region: {region_name}")

    rc_result = region_config(region_name)
    if "error" in rc_result:
        print(f"ERROR getting region config: {rc_result['error']}")
        return False
    region_cfg = rc_result["regionConfig"]
    print(f"Region config: {region_cfg}")

    # Allow override via env var (e.g. UNLOCK_REGION=Singapore)
    override = os.environ.get("UNLOCK_REGION")
    if override:
        region_cfg = override
        print(f"Region override: {region_cfg}")

    domain = get_domain_url(region_cfg)
    if not domain:
        print(f"ERROR: No domain for region config '{region_cfg}'")
        return False
    print(f"Unlock domain: {domain}")

    service_data = migate.get_service(tokens, sid)
    if "error" in service_data:
        print(f"ERROR getting service: {service_data['error']}")
        return False

    cookies = service_data["cookies"]
    ssecurity = service_data["servicedata"]["ssecurity"]

    # Now call unlock_device logic directly (without interactive prompts)
    import random

    from miunlock.utils import _send

    r = "".join(random.choices("abcdefghijklmnopqrstuvwxyz", k=16))  # noqa: S311
    nonce_resp = _send("/api/v2/nonce", {"r": r}, domain, ssecurity, cookies)

    if "error" in nonce_resp:
        print(f"ERROR getting nonce: {nonce_resp}")
        return False
    if nonce_resp["code"] != 0:
        print(f"ERROR nonce response: {nonce_resp}")
        return False

    nonce = nonce_resp.get("nonce")
    print("Got nonce from server")

    # Get product
    fb_result = subprocess.run(
        [fastboot_cmd, "getvar", "product"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    product = None
    for line in (fb_result.stderr + fb_result.stdout).splitlines():
        if line.startswith("product:"):
            product = line.split(":", 1)[1].strip()
    if not product:
        print("ERROR: Could not get product from fastboot")
        return False
    print(f"Product: {product}")

    # Clear step
    clear_resp = _send(
        "/api/v2/unlock/device/clear",
        {"appId": "1", "data": {"product": product}, "nonce": nonce},
        domain,
        ssecurity,
        cookies,
    )

    if "error" in clear_resp:
        print(f"ERROR clear: {clear_resp}")
        return False
    if clear_resp["code"] != 0:
        print(f"ERROR clear response: {clear_resp}")
        return False

    print(f"Notice: {clear_resp.get('notice', 'none')}")
    if clear_resp.get("cleanOrNot") == 1:
        print("WARNING: Device will be wiped during unlock!")
    else:
        print("Device data will NOT be wiped.")

    # Get device token
    fb_result = subprocess.run(
        [fastboot_cmd, "getvar", "token"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    device_token = None
    for line in (fb_result.stderr + fb_result.stdout).splitlines():
        if line.startswith("token:"):
            device_token = line.split(":", 1)[1].strip()
    if not device_token:
        # Try oem get_token
        fb_result = subprocess.run(
            [fastboot_cmd, "oem", "get_token"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in (fb_result.stderr + fb_result.stdout).splitlines():
            if "token:" in line:
                device_token = line.split("token:", 1)[1].strip()
    if not device_token:
        print("ERROR: Could not get device token")
        return False
    print(f"Device token: {device_token[:20]}...")

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
        "uid": cookies.get("userId"),
    }

    print("Sending unlock request to Xiaomi servers...")
    unlock_result = _send(
        "/api/v3/ahaUnlock",
        {"appId": "1", "data": unlock_data, "nonce": nonce},
        domain,
        ssecurity,
        cookies,
    )

    if "error" in unlock_result:
        print(f"ERROR: {unlock_result}")
        return False
    if unlock_result.get("code") != 0:
        desc = unlock_result.get(
            "descEN", unlock_result.get("description", str(unlock_result))
        )
        code = unlock_result.get("code", "?")
        print(f"Unlock denied by server (code={code}): {desc}")
        return False

    encrypt_data = unlock_result["encryptData"]
    ed_bytes = bytes.fromhex(encrypt_data)
    ed_file = Path.home() / f"{int(time.time())}encryptData"
    ed_file.write_bytes(ed_bytes)
    print(f"Encrypted unlock data saved: {ed_file} ({len(ed_bytes)} bytes)")

    # Stage and unlock
    print("Staging unlock data via fastboot...")
    rc = subprocess.run(
        [fastboot_cmd, "stage", str(ed_file)], capture_output=True, text=True
    )
    print(f"  stage: {rc.stderr.strip() or rc.stdout.strip()}")
    if rc.returncode != 0:
        print(f"ERROR: fastboot stage failed (rc={rc.returncode})")
        return False

    print("Sending OEM unlock command...")
    rc = subprocess.run(
        [fastboot_cmd, "oem", "unlock"], capture_output=True, text=True
    )
    output = (rc.stderr + rc.stdout).strip()
    print(f"  oem unlock: {output}")

    if rc.returncode == 0:
        print("\nBOOTLOADER UNLOCKED SUCCESSFULLY!")
        print("The device may reboot. You can now flash firmware via fastboot.")
        return True
    else:
        print(f"\nERROR: oem unlock failed (rc={rc.returncode})")
        print(output)
        return False


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "login":
        if len(sys.argv) < 4:
            print("Usage: login <email> <password>")
            sys.exit(1)
        ok = cmd_login(sys.argv[2], sys.argv[3])
        sys.exit(0 if ok else 1)

    elif cmd == "send-code":
        ok = cmd_send_code()
        sys.exit(0 if ok else 1)

    elif cmd == "verify":
        if len(sys.argv) < 3:
            print("Usage: verify <code>")
            sys.exit(1)
        ok = cmd_verify(sys.argv[2])
        sys.exit(0 if ok else 1)

    elif cmd == "unlock":
        ok = cmd_unlock()
        sys.exit(0 if ok else 1)

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
