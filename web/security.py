"""Security middleware: rate limiting and optional token authentication.

Rate limiting is always active. Token auth is opt-in — enabled by setting
the OSMOSIS_AUTH_TOKEN environment variable or by running the app with
--generate-token, which writes a token to ~/.osmosis/auth-token.
"""

import hashlib
import hmac
import os
import secrets
import time
from collections import defaultdict
from pathlib import Path

from flask import Flask, Request, jsonify, request

# ---------------------------------------------------------------------------
# Rate limiter (in-memory, per-IP, sliding window)
# ---------------------------------------------------------------------------

# Defaults: 60 requests per minute for API, 200 for static
API_RATE_LIMIT = int(os.environ.get("OSMOSIS_API_RATE_LIMIT", "60"))
API_RATE_WINDOW = int(os.environ.get("OSMOSIS_API_RATE_WINDOW", "60"))

_hits: dict[str, list[float]] = defaultdict(list)


def _client_ip(req: Request) -> str:
    """Get the real client IP, respecting X-Forwarded-For from nginx."""
    forwarded = req.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return req.remote_addr or "unknown"


def _check_rate_limit(ip: str) -> tuple[bool, int]:
    """Returns (allowed, remaining). Cleans up old entries."""
    now = time.monotonic()
    cutoff = now - API_RATE_WINDOW
    hits = _hits[ip]

    # Prune old entries
    _hits[ip] = [t for t in hits if t > cutoff]
    hits = _hits[ip]

    if len(hits) >= API_RATE_LIMIT:
        return False, 0

    hits.append(now)
    return True, API_RATE_LIMIT - len(hits)


# ---------------------------------------------------------------------------
# Token authentication
# ---------------------------------------------------------------------------

TOKEN_FILE = Path.home() / ".osmosis" / "auth-token"
_active_token: str | None = None


def _load_token() -> str | None:
    """Load auth token from env or file."""
    env_token = os.environ.get("OSMOSIS_AUTH_TOKEN")
    if env_token:
        return env_token
    if TOKEN_FILE.exists():
        token = TOKEN_FILE.read_text().strip()
        if token:
            return token
    return None


def generate_token() -> str:
    """Generate a new auth token and save it."""
    token = secrets.token_urlsafe(32)
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(token + "\n")
    TOKEN_FILE.chmod(0o600)
    return token


def _verify_token(provided: str) -> bool:
    """Constant-time token comparison."""
    if not _active_token:
        return True  # Auth not enabled
    return hmac.compare_digest(
        hashlib.sha256(provided.encode()).digest(),
        hashlib.sha256(_active_token.encode()).digest(),
    )


# ---------------------------------------------------------------------------
# Flask integration
# ---------------------------------------------------------------------------


def init_security(app: Flask) -> None:
    """Register security middleware on a Flask app."""
    global _active_token
    _active_token = _load_token()

    if _active_token:
        app.logger.info("Token authentication enabled.")
    else:
        app.logger.info(
            "Token authentication disabled. Set OSMOSIS_AUTH_TOKEN or run: python -m web.security --generate-token"
        )

    @app.before_request
    def _security_middleware():
        # Skip all security middleware during testing
        if app.config.get("TESTING"):
            return None

        # Skip rate limiting and auth for static assets
        if request.path.startswith("/static/"):
            return None

        ip = _client_ip(request)

        # Rate limiting
        if request.path.startswith("/api/"):
            allowed, remaining = _check_rate_limit(ip)
            if not allowed:
                return jsonify({"error": "Rate limit exceeded. Try again later."}), 429

        # Token auth (only if enabled)
        if _active_token and request.path.startswith("/api/"):
            token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
            if not token:
                token = request.args.get("token", "")
            if not _verify_token(token):
                return jsonify({"error": "Invalid or missing auth token."}), 401

        return None

    @app.after_request
    def _add_rate_limit_headers(response):
        if request.path.startswith("/api/"):
            ip = _client_ip(request)
            now = time.monotonic()
            cutoff = now - API_RATE_WINDOW
            current = len([t for t in _hits.get(ip, []) if t > cutoff])
            response.headers["X-RateLimit-Limit"] = str(API_RATE_LIMIT)
            response.headers["X-RateLimit-Remaining"] = str(max(0, API_RATE_LIMIT - current))
            response.headers["X-RateLimit-Window"] = str(API_RATE_WINDOW)
        return response


# ---------------------------------------------------------------------------
# CLI: generate token
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if "--generate-token" in sys.argv:
        token = generate_token()
        print(f"Auth token generated and saved to {TOKEN_FILE}")
        print(f"Token: {token}")
        print()
        print("Use it in requests:")
        print(f"  curl -H 'Authorization: Bearer {token}' https://localhost/api/detect")
    else:
        print("Usage: python -m web.security --generate-token")
