"""Trusted publisher key management for IPFS manifest signing."""

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

_TRUSTED_KEYS_FILE = Path.home() / ".osmosis" / "trusted-publishers.json"
_PROJECT_KEY_FILE = (
    Path(__file__).resolve().parent.parent / "keys" / "osmosis-project.pub"
)


def _seed_project_key(publishers: dict[str, str]) -> dict[str, str]:
    """Seed the project's public key into trusted publishers if missing."""
    if "osmosis-project" in publishers:
        return publishers
    if _PROJECT_KEY_FILE.exists():
        try:
            pubkey = _PROJECT_KEY_FILE.read_text().strip()
            if pubkey:
                publishers["osmosis-project"] = pubkey
                _TRUSTED_KEYS_FILE.parent.mkdir(parents=True, exist_ok=True)
                _TRUSTED_KEYS_FILE.write_text(json.dumps(publishers, indent=2))
                log.info("Auto-trusted osmosis-project signing key")
        except (OSError, ValueError) as e:
            log.debug("Failed to seed project key: %s", e)
    return publishers


def get_trusted_publishers() -> dict[str, str]:
    """Load trusted publisher keys. Returns {name: pubkey_b64}.

    On first run, auto-trusts the project's signing key shipped in keys/.
    """
    publishers = {}
    if _TRUSTED_KEYS_FILE.exists():
        try:
            publishers = json.loads(_TRUSTED_KEYS_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return _seed_project_key(publishers)


def add_trusted_publisher(name: str, pubkey_b64: str) -> None:
    """Add a publisher's public key to the trusted set."""
    publishers = get_trusted_publishers()
    publishers[name] = pubkey_b64
    _TRUSTED_KEYS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _TRUSTED_KEYS_FILE.write_text(json.dumps(publishers, indent=2))


def remove_trusted_publisher(name: str) -> bool:
    """Remove a publisher from the trusted set."""
    publishers = get_trusted_publishers()
    if name not in publishers:
        return False
    del publishers[name]
    _TRUSTED_KEYS_FILE.write_text(json.dumps(publishers, indent=2))
    return True


def is_trusted_publisher(pubkey_b64: str) -> str | None:
    """Check if a public key is trusted. Returns the publisher name or None."""
    for name, key in get_trusted_publishers().items():
        if key == pubkey_b64:
            return name
    return None
