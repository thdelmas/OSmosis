"""IPFS Tier 6 helpers — IPNS, CAR, PubSub, Bitswap.

Split from ipfs_helpers.py to keep modules under the 500-line limit.
All functions here depend on a running Kubo daemon.
"""

import json
import logging
import os
import subprocess

from web.ipfs_helpers import is_valid_cid

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# IPNS helpers
# ---------------------------------------------------------------------------


def ipns_key_list() -> dict[str, str]:
    """List all IPNS keys. Returns {name: peer_id}."""
    try:
        r = subprocess.run(
            ["ipfs", "key", "list", "-l"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if r.returncode != 0:
            return {}
        keys = {}
        for line in r.stdout.strip().splitlines():
            parts = line.split(None, 1)
            if len(parts) == 2:
                keys[parts[1]] = parts[0]
        return keys
    except Exception as e:
        log.debug("ipns_key_list failed: %s", e)
        return {}


def ipns_key_create(name: str) -> str | None:
    """Create a dedicated IPNS key. Returns the key ID or None."""
    existing = ipns_key_list()
    if name in existing:
        return existing[name]
    try:
        r = subprocess.run(
            ["ipfs", "key", "gen", "--type=ed25519", name],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if r.returncode == 0:
            return r.stdout.strip()
        log.warning("ipns_key_create failed: %s", r.stderr.strip())
    except Exception as e:
        log.error("ipns_key_create exception: %s", e)
    return None


def ipns_publish(cid: str, key_name: str = "self") -> str | None:
    """Publish a CID under an IPNS key. Returns the IPNS name or None."""
    if not is_valid_cid(cid):
        return None
    try:
        r = subprocess.run(
            ["ipfs", "name", "publish", "--key", key_name, f"/ipfs/{cid}"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if r.returncode == 0:
            # Output: "Published to <ipns_name>: /ipfs/<cid>"
            parts = r.stdout.strip().split()
            if len(parts) >= 3:
                return parts[2].rstrip(":")
            return r.stdout.strip()
        log.warning("ipns_publish failed: %s", r.stderr.strip())
    except Exception as e:
        log.error("ipns_publish exception: %s", e)
    return None


def ipns_resolve(ipns_name: str, timeout_secs: int = 30) -> str | None:
    """Resolve an IPNS name to a CID. Returns the CID or None."""
    try:
        r = subprocess.run(
            ["ipfs", "name", "resolve", ipns_name],
            capture_output=True,
            text=True,
            timeout=timeout_secs + 5,
        )
        if r.returncode == 0:
            resolved = r.stdout.strip()
            # Output is /ipfs/<cid> — extract just the CID
            if resolved.startswith("/ipfs/"):
                return resolved[6:]
            return resolved
        log.warning(
            "ipns_resolve failed for %s: %s", ipns_name, r.stderr.strip()
        )
    except subprocess.TimeoutExpired:
        log.debug("ipns_resolve timed out for %s", ipns_name)
    except Exception as e:
        log.error("ipns_resolve exception for %s: %s", ipns_name, e)
    return None


# ---------------------------------------------------------------------------
# CAR export/import
# ---------------------------------------------------------------------------


def ipfs_dag_export(cid: str, dest_path: str) -> bool:
    """Export a CID's DAG to a .car file."""
    if not is_valid_cid(cid):
        return False
    try:
        with open(dest_path, "wb") as f:
            r = subprocess.run(
                ["ipfs", "dag", "export", cid],
                stdout=f,
                stderr=subprocess.PIPE,
                timeout=600,
            )
        if r.returncode != 0:
            log.warning(
                "ipfs dag export failed for %s: %s",
                cid,
                r.stderr.decode().strip(),
            )
            if os.path.exists(dest_path):
                os.unlink(dest_path)
            return False
        return True
    except Exception as e:
        log.error("ipfs dag export exception for %s: %s", cid, e)
        if os.path.exists(dest_path):
            os.unlink(dest_path)
        return False


def ipfs_dag_import(car_path: str) -> list[str]:
    """Import a .car file and pin its roots. Returns list of root CIDs."""
    if not os.path.exists(car_path):
        return []
    try:
        r = subprocess.run(
            ["ipfs", "dag", "import", "--pin-roots", car_path],
            capture_output=True,
            text=True,
            timeout=600,
        )
        if r.returncode != 0:
            log.warning("ipfs dag import failed: %s", r.stderr.strip())
            return []
        # Output lines like: "Pinned root\t<cid>\tsuccess"
        roots = []
        for line in r.stdout.strip().splitlines():
            parts = line.split()
            for part in parts:
                if is_valid_cid(part):
                    roots.append(part)
                    break
        return roots
    except Exception as e:
        log.error("ipfs dag import exception: %s", e)
        return []


# ---------------------------------------------------------------------------
# PubSub helpers
# ---------------------------------------------------------------------------

PUBSUB_TOPIC = "osmosis-updates"


def pubsub_publish(topic: str, message: dict) -> bool:
    """Publish a JSON message to an IPFS PubSub topic."""
    try:
        payload = json.dumps(message)
        r = subprocess.run(
            ["ipfs", "pubsub", "pub", topic, payload],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if r.returncode != 0:
            log.warning("pubsub publish failed: %s", r.stderr.strip())
        return r.returncode == 0
    except Exception as e:
        log.error("pubsub publish exception: %s", e)
        return False


def pubsub_subscribe(topic: str, timeout_secs: int = 0):
    """Subscribe to an IPFS PubSub topic. Yields decoded JSON messages.

    If timeout_secs is 0, runs indefinitely (caller must manage the generator).
    """
    try:
        cmd = ["ipfs", "pubsub", "sub", topic]
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                log.debug(
                    "pubsub: non-JSON message on %s: %s", topic, line[:100]
                )
    except Exception as e:
        log.error("pubsub subscribe exception on %s: %s", topic, e)


# ---------------------------------------------------------------------------
# Bitswap stats
# ---------------------------------------------------------------------------


def ipfs_bitswap_stat() -> dict | None:
    """Return parsed bitswap statistics, or None if unavailable."""
    try:
        r = subprocess.run(
            ["ipfs", "bitswap", "stat"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if r.returncode != 0:
            return None

        stats = {}
        for line in r.stdout.strip().splitlines():
            line = line.strip()
            if ":" not in line:
                continue
            key, _, val = line.partition(":")
            key = key.strip().lower().replace(" ", "_")
            val = val.strip()
            # Try numeric conversion
            try:
                if "." in val:
                    stats[key] = float(val)
                else:
                    stats[key] = int(val)
            except ValueError:
                stats[key] = val

        # Compute seeding ratio
        sent = stats.get("blocks_sent", 0)
        received = stats.get("blocks_received", 0)
        if received > 0:
            stats["seeding_ratio"] = round(sent / received, 2)
        elif sent > 0:
            stats["seeding_ratio"] = float("inf")
        else:
            stats["seeding_ratio"] = 0.0

        return stats
    except Exception as e:
        log.debug("ipfs bitswap stat failed: %s", e)
        return None
