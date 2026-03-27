"""Mi account management routes.

Stores Mi accounts in ~/.osmosis/mi-accounts.json with Fernet-encrypted
passwords.  Exposes CRUD endpoints plus login/2FA/session helpers that
delegate to web.mi_auth for all Xiaomi API calls.
"""

import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path

from cryptography.fernet import Fernet
from flask import Blueprint, jsonify, request

from web.mi_auth import (
    mi_get_region,
    mi_login,
    mi_send_code,
    mi_verify,
)

bp = Blueprint("mi_accounts", __name__)

_ACCOUNTS_FILE = Path.home() / ".osmosis" / "mi-accounts.json"
_KEY_FILE = Path.home() / ".osmosis" / "mi-accounts.key"

# Maps Xiaomi region/country codes to unlock server region configs.
# Xiaomi returns country codes (ES, DE, FR…) not region codes — map both.
_EU_CODES = (
    "EU ES DE FR IT PT NL PL CZ AT BE SE NO DK FI IE GR HU RO BG HR SK SI LT LV EE GB CH TR"
).split()
_GLOBAL_CODES = "MI Global US MX BR AR CO CL CA SG MY TH VN PH ID TW HK KR JP AU NZ".split()
_REGION_MAP = {
    **{c: "Europe" for c in _EU_CODES},
    **{c: "Singapore" for c in _GLOBAL_CODES},
    "CN": "China",
    "IN": "India",
    "RU": "Russia",
}

# Max age for pending 2FA state (seconds)
_PENDING_2FA_MAX_AGE = 600  # 10 minutes


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_fernet() -> Fernet:
    """Return a Fernet instance, creating the key file if needed."""
    _KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    if _KEY_FILE.exists():
        key = _KEY_FILE.read_bytes().strip()
    else:
        key = Fernet.generate_key()
        _KEY_FILE.write_bytes(key)
        os.chmod(_KEY_FILE, 0o600)
    return Fernet(key)


def _encrypt_password(password: str) -> str:
    """Encrypt a plaintext password and return base64 token."""
    return _get_fernet().encrypt(password.encode()).decode()


def _decrypt_password(encrypted: str) -> str:
    """Decrypt a Fernet-encrypted password token."""
    return _get_fernet().decrypt(encrypted.encode()).decode()


def _load() -> list[dict]:
    """Load accounts from the JSON file."""
    if not _ACCOUNTS_FILE.exists():
        return []
    try:
        data = json.loads(_ACCOUNTS_FILE.read_text())
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def _save(accounts: list[dict]) -> None:
    """Write accounts to the JSON file with restricted permissions."""
    _ACCOUNTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _ACCOUNTS_FILE.write_text(json.dumps(accounts, indent=2))
    os.chmod(_ACCOUNTS_FILE, 0o600)


def _get_account(account_id: str) -> dict | None:
    """Find an account by id, returning None if not found."""
    for acct in _load():
        if acct.get("id") == account_id:
            return acct
    return None


def _expire_pending_2fa(account: dict) -> None:
    """Clear pending_2fa if it is older than 10 minutes."""
    pending = account.get("pending_2fa")
    if not pending:
        return
    created = pending.get("created")
    if not created:
        account["pending_2fa"] = None
        return
    try:
        ts = datetime.fromisoformat(created)
        age = (datetime.now(timezone.utc) - ts).total_seconds()
        if age > _PENDING_2FA_MAX_AGE:
            account["pending_2fa"] = None
    except Exception:
        account["pending_2fa"] = None


def _update_account(account_id: str, updates: dict) -> dict | None:
    """Apply *updates* to the account with *account_id* and persist."""
    accounts = _load()
    for acct in accounts:
        if acct.get("id") == account_id:
            acct.update(updates)
            _save(accounts)
            return acct
    return None


def _safe_view(account: dict) -> dict:
    """Return a public-safe representation of an account (no password)."""
    _expire_pending_2fa(account)
    session = account.get("session")
    return {
        "id": account.get("id"),
        "email": account.get("email"),
        "region": account.get("region"),
        "region_config": account.get("region_config"),
        "user_id": account.get("user_id"),
        "label": account.get("label"),
        "has_session": session is not None and bool(session),
        "session_updated": account.get("session_updated"),
        "pending_2fa": account.get("pending_2fa") is not None,
        "created": account.get("created"),
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@bp.route("/api/mi-accounts/", methods=["GET"])
def api_list_accounts():
    """List all stored Mi accounts (no passwords)."""
    accounts = _load()
    for acct in accounts:
        _expire_pending_2fa(acct)
    # Persist any cleared pending states
    _save(accounts)
    return jsonify([_safe_view(a) for a in accounts])


@bp.route("/api/mi-accounts/", methods=["POST"])
def api_add_account():
    """Add a new Mi account.

    Expected JSON body::

        {"email": "user@example.com", "password": "...", "label": "EU unlock account"}
    """
    data = request.json or {}
    email = data.get("email", "").strip()
    password = data.get("password", "")
    label = data.get("label", "").strip()

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400

    accounts = _load()

    # Prevent duplicate emails
    for acct in accounts:
        if acct.get("email", "").lower() == email.lower():
            return jsonify({"error": "An account with this email already exists"}), 409

    now = datetime.now(timezone.utc).isoformat()
    account = {
        "id": secrets.token_hex(3),
        "email": email,
        "password_encrypted": _encrypt_password(password),
        "region": None,
        "region_config": None,
        "user_id": None,
        "session": None,
        "session_updated": None,
        "pending_2fa": None,
        "created": now,
        "label": label or None,
    }

    accounts.append(account)
    _save(accounts)
    return jsonify(_safe_view(account)), 201


@bp.route("/api/mi-accounts/<account_id>", methods=["DELETE"])
def api_delete_account(account_id):
    """Remove a stored Mi account."""
    accounts = _load()
    before = len(accounts)
    accounts = [a for a in accounts if a.get("id") != account_id]
    if len(accounts) == before:
        return jsonify({"error": "Account not found"}), 404
    _save(accounts)
    return jsonify({"ok": True})


@bp.route("/api/mi-accounts/<account_id>/login", methods=["POST"])
def api_login(account_id):
    """Start login for a stored Mi account.

    Decrypts the password and calls mi_login().  If 2FA is needed the
    pending state is saved on the account record.
    """
    account = _get_account(account_id)
    if not account:
        return jsonify({"error": "Account not found"}), 404

    try:
        password = _decrypt_password(account["password_encrypted"])
    except Exception:
        return jsonify({"error": "Failed to decrypt password"}), 500

    result = mi_login(account["email"], password)
    status = result.get("status")

    updates: dict = {}

    if status == "error":
        updated = _update_account(account_id, {})
        return jsonify(
            {
                "needs_2fa": False,
                "methods": [],
                "error": result.get("message"),
                "account": _safe_view(updated) if updated else None,
            }
        )

    if status == "2fa_required":
        # Save pending 2FA state (must be JSON-serializable)
        updates["pending_2fa"] = {
            "state": result.get("pending", {}),
            "methods": result.get("methods", []),
            "created": datetime.now(timezone.utc).isoformat(),
        }
        updated = _update_account(account_id, updates)
        return jsonify(
            {
                "needs_2fa": True,
                "methods": result.get("methods", []),
                "error": None,
                "account": _safe_view(updated) if updated else None,
            }
        )

    # status == "ok" — login succeeded without 2FA
    tokens = result.get("tokens", {})
    now = datetime.now(timezone.utc).isoformat()
    updates["session"] = tokens
    updates["session_updated"] = now
    updates["user_id"] = tokens.get("userId")
    updates["pending_2fa"] = None

    # Region from login result
    region_code = result.get("region")
    if region_code:
        updates["region"] = region_code
        updates["region_config"] = _REGION_MAP.get(region_code, region_code)

    updated = _update_account(account_id, updates)
    return jsonify(
        {
            "needs_2fa": False,
            "methods": [],
            "error": None,
            "account": _safe_view(updated) if updated else None,
        }
    )


@bp.route("/api/mi-accounts/<account_id>/send-code", methods=["POST"])
def api_send_code(account_id):
    """Send a 2FA verification code.

    Expected JSON body::

        {"method": "email" | "phone"}
    """
    account = _get_account(account_id)
    if not account:
        return jsonify({"error": "Account not found"}), 404

    _expire_pending_2fa(account)
    pending = account.get("pending_2fa")
    if not pending:
        return jsonify({"error": "No pending 2FA session (expired or not started)"}), 400

    data = request.json or {}
    method = data.get("method", "email")

    result = mi_send_code(pending["state"], method=method)

    if result.get("status") == "ok":
        # Update the pending state with new cookies/address_type
        pending["state"] = result.get("pending", pending["state"])
        _update_account(account_id, {"pending_2fa": pending})
        return jsonify(
            {
                "ok": True,
                "error": None,
                "attempts_remaining": result.get("attempts_remaining"),
            }
        )

    return jsonify(
        {
            "ok": False,
            "error": result.get("message", "Unknown error"),
        }
    )


@bp.route("/api/mi-accounts/<account_id>/verify", methods=["POST"])
def api_verify(account_id):
    """Verify a 2FA code and complete login.

    Expected JSON body::

        {"code": "123456"}
    """
    account = _get_account(account_id)
    if not account:
        return jsonify({"error": "Account not found"}), 404

    _expire_pending_2fa(account)
    pending = account.get("pending_2fa")
    if not pending:
        return jsonify({"error": "No pending 2FA session (expired or not started)"}), 400

    data = request.json or {}
    code = data.get("code", "").strip()
    if not code:
        return jsonify({"error": "code is required"}), 400

    result = mi_verify(pending["state"], code)

    if result.get("status") == "ok":
        tokens = result.get("tokens", {})
        now = datetime.now(timezone.utc).isoformat()
        updates = {
            "session": tokens,
            "session_updated": now,
            "user_id": tokens.get("userId"),
            "pending_2fa": None,
        }

        # Region from verify result
        region_code = result.get("region")
        if region_code:
            updates["region"] = region_code
            updates["region_config"] = _REGION_MAP.get(region_code, region_code)

        updated = _update_account(account_id, updates)
        return jsonify(
            {
                "ok": True,
                "error": None,
                "account": _safe_view(updated) if updated else None,
            }
        )

    return jsonify(
        {
            "ok": False,
            "error": result.get("message", "Verification failed"),
        }
    )


@bp.route("/api/mi-accounts/<account_id>/status", methods=["GET"])
def api_status(account_id):
    """Check whether the stored session is still valid."""
    account = _get_account(account_id)
    if not account:
        return jsonify({"error": "Account not found"}), 404

    session = account.get("session")
    if not session:
        return jsonify({"valid": False, "reason": "No session stored"})

    try:
        region_code = mi_get_region(session)
        if region_code is None:
            return jsonify({"valid": False, "reason": "Session expired or invalid"})
        # Update region info while we're at it
        updates = {
            "region": region_code,
            "region_config": _REGION_MAP.get(region_code, region_code),
        }
        _update_account(account_id, updates)
        return jsonify({"valid": True, "region": region_code})
    except Exception as e:
        return jsonify({"valid": False, "reason": str(e)})


@bp.route("/api/mi-accounts/<account_id>/logout", methods=["POST"])
def api_logout(account_id):
    """Clear session tokens for an account."""
    account = _get_account(account_id)
    if not account:
        return jsonify({"error": "Account not found"}), 404

    updated = _update_account(
        account_id,
        {
            "session": None,
            "session_updated": None,
            "pending_2fa": None,
        },
    )
    return jsonify({"ok": True, "account": _safe_view(updated) if updated else None})


@bp.route("/api/mi-accounts/match", methods=["GET"])
def api_match_accounts():
    """Return accounts sorted by compatibility with a device region code.

    Query params:
        region_code — e.g. "EU", "CN", "IN", "MI", "Global", "RU"
    """
    region_code = request.args.get("region_code", "").strip()
    if not region_code:
        return jsonify({"error": "region_code query parameter is required"}), 400

    target_config = _REGION_MAP.get(region_code, region_code)

    accounts = _load()
    for acct in accounts:
        _expire_pending_2fa(acct)

    # Sort: matching region first, then accounts with sessions, then the rest
    def _sort_key(acct):
        matches_region = acct.get("region_config") == target_config
        has_session = bool(acct.get("session"))
        return (not matches_region, not has_session)

    accounts.sort(key=_sort_key)
    _save(accounts)

    result = []
    for acct in accounts:
        view = _safe_view(acct)
        view["region_match"] = acct.get("region_config") == target_config
        result.append(view)

    return jsonify(result)
