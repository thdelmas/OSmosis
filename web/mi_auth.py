"""Reusable Xiaomi Mi account authentication module for Flask routes.

Extracts login / 2FA / unlock logic from tools/xiaomi_unlock.py and the
migate/miunlock libraries into pure functions that return JSON-serializable
dicts.  No interactive prompts, no pickle, no console output.
"""

import base64
import hashlib
import json
import logging
import os
import uuid
from urllib.parse import parse_qs, quote, urlparse

import requests

# ---------------------------------------------------------------------------
# Constants (copied from migate.config so we never import console)
# ---------------------------------------------------------------------------

_AGENT = "offici5l/migate"

HEADERS = {
    "User-Agent": _AGENT,
    "Content-Type": "application/x-www-form-urlencoded",
}

_BASE = "https://account.xiaomi.com"

SERVICELOGIN_URL = _BASE + "/pass/serviceLogin"
SERVICELOGINAUTH2_URL = SERVICELOGIN_URL + "Auth2"
LIST_URL = _BASE + "/identity/list"
SEND_EM_TICKET = _BASE + "/identity/auth/sendEmailTicket"
SEND_PH_TICKET = _BASE + "/identity/auth/sendPhoneTicket"
VERIFY_EM = _BASE + "/identity/auth/verifyEmail"
VERIFY_PH = _BASE + "/identity/auth/verifyPhone"
USERQUOTA_URL = _BASE + "/identity/pass/sms/userQuota"

REGION_URL = _BASE + "/pass/user/login/region"
REGION_CONFIG_URL = _BASE + "/pass2/config?key=regionConfig"

UNLOCK_DOMAINS = {
    "Singapore": "https://unlock.update.intl.miui.com",
    "China": "https://unlock.update.miui.com",
    "India": "https://in-unlock.update.intl.miui.com",
    "Russia": "https://ru-unlock.update.intl.miui.com",
    "Europe": "https://eu-unlock.update.intl.miui.com",
}

_TIMEOUT = 15  # seconds for HTTP requests

log = logging.getLogger(__name__)


def _get_proxies() -> dict | None:
    """Return proxy dict for requests if configured.

    Checks, in order:
    - OSMOSIS_PROXY env var  (e.g. "socks5://127.0.0.1:1080")
    - HTTPS_PROXY / HTTP_PROXY env vars (standard)

    Supports HTTP, HTTPS, SOCKS4, and SOCKS5 proxies.
    """
    proxy = os.environ.get("OSMOSIS_PROXY", "").strip()
    if not proxy:
        proxy = os.environ.get("HTTPS_PROXY", os.environ.get("HTTP_PROXY", "")).strip()
    if proxy:
        return {"http": proxy, "https": proxy}
    return None


def _http_get(url: str, **kwargs) -> requests.Response:
    """requests.get with proxy support."""
    kwargs.setdefault("timeout", _TIMEOUT)
    proxies = _get_proxies()
    if proxies:
        kwargs.setdefault("proxies", proxies)
    return requests.get(url, **kwargs)  # noqa: S113 — timeout set above


def _http_post(url: str, **kwargs) -> requests.Response:
    """requests.post with proxy support."""
    kwargs.setdefault("timeout", _TIMEOUT)
    proxies = _get_proxies()
    if proxies:
        kwargs.setdefault("proxies", proxies)
    return requests.post(url, **kwargs)  # noqa: S113 — timeout set above


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_mi_json(text: str) -> dict:
    """Xiaomi prepends '&&&START&&&' (11 chars) to JSON responses."""
    return json.loads(text[11:])


def _get_service(tokens: dict, sid: str) -> dict:
    """Obtain a service token (ssecurity + service cookies) for *sid*."""
    try:
        resp = _http_get(
            SERVICELOGIN_URL,
            params={"_json": "true", "sid": sid},
            cookies=tokens,
            headers=HEADERS,
            timeout=_TIMEOUT,
        )
        data = _parse_mi_json(resp.text)
    except Exception as exc:
        return {"error": f"get_service request failed: {exc}"}

    nonce = data.get("nonce")
    ssecurity = data.get("ssecurity")
    location = data.get("location")

    if not all([nonce, ssecurity, location]):
        return {"error": f"Incomplete service response: {data}"}

    sign_text = f"nonce={nonce}&{ssecurity}"
    sha1_digest = hashlib.sha1(sign_text.encode()).digest()  # noqa: S324
    client_sign = quote(base64.b64encode(sha1_digest))
    url = f"{location}&clientSign={client_sign}"

    try:
        resp = _http_get(url, headers=HEADERS, cookies=tokens, timeout=_TIMEOUT)
    except Exception as exc:
        return {"error": f"Service redirect failed: {exc}"}

    return {
        "ssecurity": ssecurity,
        "cookies": resp.cookies.get_dict(),
    }


def _available_2fa_methods(options: list[int]) -> list[str]:
    """Map Xiaomi option codes to human-readable method names."""
    methods = []
    if 8 in options:
        methods.append("email")
    if 4 in options:
        methods.append("phone")
    return methods


def _method_to_address_type(method: str) -> str:
    return "EM" if method == "email" else "PH"


# ---------------------------------------------------------------------------
# 1. mi_login
# ---------------------------------------------------------------------------


def mi_login(email: str, password: str) -> dict:
    """Authenticate with Xiaomi — returns ok/2fa_required/error status dict."""
    sid = "unlockApi"
    auth_data: dict = {"sid": sid, "checkSafeAddress": True, "_json": True}

    # Step 1 — fetch login page params
    try:
        resp = _http_get(SERVICELOGIN_URL, params=auth_data, timeout=_TIMEOUT)
        page = _parse_mi_json(resp.text)
    except Exception as exc:
        return {"status": "error", "message": f"Connection error: {exc}"}

    auth_data["serviceParam"] = page.get("serviceParam", "")
    auth_data["qs"] = page.get("qs", "")
    auth_data["callback"] = page.get("callback", "")
    auth_data["_sign"] = page.get("_sign", "")

    # Step 2 — submit credentials
    pwd_hash = hashlib.md5(password.encode()).hexdigest().upper()  # noqa: S324
    auth_data["user"] = email
    auth_data["hash"] = pwd_hash

    device_id = "wb_" + str(
        uuid.UUID(
            bytes=hashlib.md5(  # noqa: S324
                (email + pwd_hash + json.dumps(auth_data, sort_keys=True)).encode()
            ).digest()
        )
    )
    cookies: dict = {"deviceId": device_id}

    try:
        resp = _http_post(
            SERVICELOGINAUTH2_URL,
            headers=HEADERS,
            data=auth_data,
            cookies=cookies,
            timeout=_TIMEOUT,
        )
        result = _parse_mi_json(resp.text)
    except Exception as exc:
        return {"status": "error", "message": f"Login request failed: {exc}"}

    # -- error codes --
    if result.get("code") == 70016:
        return {"status": "error", "message": "Invalid password or username."}

    if result.get("code") == 87001:
        return {
            "status": "error",
            "message": "CAPTCHA required — not supported in non-interactive mode.",
        }

    # -- 2FA required --
    if "notificationUrl" in result:
        notification_url = result["notificationUrl"]
        if any(x in notification_url for x in ["callback", "SetEmail", "BindAppealOrSafePhone"]):
            return {
                "status": "error",
                "message": f"Action required at: {notification_url}",
            }

        context = parse_qs(urlparse(notification_url).query).get("context", [None])[0]
        if not context:
            return {
                "status": "error",
                "message": f"Could not extract 2FA context from URL: {notification_url}",
            }

        # Fetch available 2FA methods
        try:
            list_resp = _http_get(
                LIST_URL,
                params={"sid": sid, "supportedMask": "0", "context": context},
                headers=HEADERS,
                cookies=cookies,
                timeout=_TIMEOUT,
            )
            cookies.update(list_resp.cookies.get_dict())
            list_data = _parse_mi_json(list_resp.text)
        except Exception as exc:
            return {"status": "error", "message": f"Failed to list 2FA methods: {exc}"}

        options = list_data.get("options", [])
        methods = _available_2fa_methods(options)
        if not methods:
            return {
                "status": "error",
                "message": f"No supported 2FA methods. Server options: {options}",
            }

        pending = {
            "context": context,
            "auth_data": auth_data,
            "cookies": cookies,
            "device_id": device_id,
        }

        return {
            "status": "2fa_required",
            "pending": pending,
            "methods": methods,
        }

    # -- Direct success (no 2FA) --
    session_cookies = resp.cookies.get_dict()
    required = {"deviceId", "passToken", "userId"}
    missing = required - session_cookies.keys()
    if missing:
        return {
            "status": "error",
            "message": f"Missing session keys: {', '.join(missing)}. Response: {result}",
        }

    tokens = {k: session_cookies[k] for k in required}
    region = mi_get_region(tokens)
    return {"status": "ok", "tokens": tokens, "region": region}


# ---------------------------------------------------------------------------
# 2. mi_send_code
# ---------------------------------------------------------------------------


def mi_send_code(pending: dict, method: str = "email") -> dict:
    """Request that Xiaomi sends a 2FA verification code (*method*: email|phone)."""
    if method not in ("email", "phone"):
        return {"status": "error", "message": f"Invalid method: {method!r}"}

    cookies = dict(pending["cookies"])
    address_type = _method_to_address_type(method)
    label = "email" if address_type == "EM" else "phone"

    # Check quota
    try:
        quota_resp = _http_post(
            USERQUOTA_URL,
            data={"addressType": address_type, "contentType": "160040", "_json": "true"},
            headers=HEADERS,
            cookies=cookies,
            timeout=_TIMEOUT,
        )
        quota_data = _parse_mi_json(quota_resp.text)
    except Exception as exc:
        return {"status": "error", "message": f"Quota check failed: {exc}"}

    remaining = int(quota_data.get("info", 0))
    if remaining <= 0:
        return {
            "status": "error",
            "message": f"Sent too many codes to {label}. Try again tomorrow.",
        }

    # Send the code
    send_url = SEND_EM_TICKET if address_type == "EM" else SEND_PH_TICKET
    try:
        send_resp = _http_post(send_url, headers=HEADERS, cookies=cookies, timeout=_TIMEOUT)
        send_data = _parse_mi_json(send_resp.text)
    except Exception as exc:
        return {"status": "error", "message": f"Send code request failed: {exc}"}

    if send_data.get("code") == 87001:
        return {
            "status": "error",
            "message": "CAPTCHA required to send code — not supported in non-interactive mode.",
        }

    if send_data.get("code") != 0:
        error_msg = send_data.get("tips", str(send_data))
        return {"status": "error", "message": f"Failed to send code: {error_msg}"}

    # Persist updated cookies and chosen method in pending state
    updated_pending = dict(pending)
    updated_pending["cookies"] = cookies
    updated_pending["address_type"] = address_type

    return {
        "status": "ok",
        "pending": updated_pending,
        "attempts_remaining": remaining,
    }


# ---------------------------------------------------------------------------
# 3. mi_verify
# ---------------------------------------------------------------------------


def mi_verify(pending: dict, code: str) -> dict:
    """Complete 2FA verification with the user-received code."""
    auth_data = pending["auth_data"]
    cookies = dict(pending["cookies"])
    address_type = pending.get("address_type", "EM")

    verify_url = VERIFY_EM if address_type == "EM" else VERIFY_PH

    # Submit the code
    try:
        resp = _http_post(
            verify_url,
            data={"ticket": code, "trust": "true", "_json": "true"},
            headers=HEADERS,
            cookies=cookies,
            timeout=_TIMEOUT,
        )
        result = _parse_mi_json(resp.text)
    except Exception as exc:
        return {"status": "error", "message": f"Verify request failed: {exc}"}

    if result.get("code") == 70014:
        return {"status": "error", "message": "Invalid verification code."}
    if result.get("code") != 0:
        return {"status": "error", "message": f"Verification failed: {result}"}

    location = result.get("location")
    if not location:
        return {
            "status": "error",
            "message": f"No redirect location in verify response: {result}",
        }

    # Follow redirects to complete authentication
    try:
        resp = _http_get(
            location,
            headers=HEADERS,
            allow_redirects=False,
            cookies=cookies,
            timeout=_TIMEOUT,
        )
        redirect_url = resp.headers.get("Location")
        if not redirect_url:
            return {"status": "error", "message": "Missing redirect after verification."}

        resp = _http_get(
            redirect_url,
            headers=HEADERS,
            allow_redirects=False,
            cookies=cookies,
            timeout=_TIMEOUT,
        )
        cookies.update(resp.cookies.get_dict())
    except Exception as exc:
        return {"status": "error", "message": f"Post-verify redirect failed: {exc}"}

    # Final auth call to obtain session tokens
    try:
        resp = _http_post(
            SERVICELOGINAUTH2_URL,
            headers=HEADERS,
            data=auth_data,
            cookies=cookies,
            timeout=_TIMEOUT,
        )
    except Exception as exc:
        return {"status": "error", "message": f"Final auth request failed: {exc}"}

    session_cookies = resp.cookies.get_dict()
    required = {"deviceId", "passToken", "userId"}
    missing = required - session_cookies.keys()
    if missing:
        try:
            body = _parse_mi_json(resp.text)
        except Exception:
            body = resp.text[:200]
        return {
            "status": "error",
            "message": f"Missing session keys: {', '.join(missing)}. Response: {body}",
        }

    tokens = {k: session_cookies[k] for k in required}
    region = mi_get_region(tokens)
    return {"status": "ok", "tokens": tokens, "region": region}


# ---------------------------------------------------------------------------
# 4. mi_get_region
# ---------------------------------------------------------------------------


def mi_get_region(tokens: dict) -> str | None:
    """Return the account region code (e.g. ``"ES"``, ``"IN"``, ``"CN"``)."""
    try:
        resp = _http_get(
            REGION_URL,
            headers={"User-Agent": "XiaomiPCSuite"},
            cookies=tokens,
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = _parse_mi_json(resp.text)
        return data.get("data", {}).get("region") or None
    except Exception as exc:
        log.warning("mi_get_region failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# 5. mi_resolve_unlock_domain
# ---------------------------------------------------------------------------


def mi_resolve_unlock_domain(tokens: dict) -> str | None:
    """Resolve the unlock API domain URL for the account's region."""
    region = mi_get_region(tokens)
    if not region:
        return None

    # Fetch region config mapping
    try:
        resp = _http_get(
            REGION_CONFIG_URL,
            headers={"User-Agent": "XiaomiPCSuite"},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = _parse_mi_json(resp.text)
        region_config_dict = data.get("regionConfig", {})
    except Exception as exc:
        log.warning("Failed to fetch region config: %s", exc)
        return None

    # Find which config name contains our region code
    config_name = next(
        (k for k, v in region_config_dict.items() if v.get("region.codes") and region in v["region.codes"]),
        None,
    )
    if not config_name:
        log.warning("No region config found for region %r", region)
        return None

    domain_url = UNLOCK_DOMAINS.get(config_name)
    if not domain_url:
        log.warning("No unlock domain for config %r", config_name)
    return domain_url
