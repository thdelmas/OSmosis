"""IPFS utility functions shared by route modules."""

import base64 as _b64
import fcntl
import hashlib as _hashlib
import json
import logging
import os
import re
import subprocess
import tempfile

from web.core import IPFS_INDEX, cmd_exists
from web.registry import lookup as registry_lookup
from web.registry import sha256_file

log = logging.getLogger(__name__)

# CIDv0 (Qm...) or CIDv1 (bafy..., bafk..., etc.)
_CID_RE = re.compile(r"^(Qm[1-9A-HJ-NP-Za-km-z]{44,}|b[a-z2-7]{58,})$")


def is_valid_cid(cid: str) -> bool:
    """Check if a string looks like a valid IPFS CID."""
    return bool(cid and _CID_RE.match(cid))


def ipfs_available() -> bool:
    """Check if the IPFS CLI (kubo) is installed and the daemon is reachable."""
    if not cmd_exists("ipfs"):
        return False
    try:
        r = subprocess.run(
            ["ipfs", "id"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return r.returncode == 0
    except Exception as e:
        log.debug("ipfs_available check failed: %s", e)
        return False


_INDEX_LOCK = IPFS_INDEX.parent / ".ipfs-index.lock"


def ipfs_index_load() -> dict:
    """Load the local IPFS CID index."""
    if IPFS_INDEX.exists():
        try:
            return json.loads(IPFS_INDEX.read_text())
        except (json.JSONDecodeError, OSError) as e:
            log.warning("Failed to load IPFS index %s: %s", IPFS_INDEX, e)
    return {}


def ipfs_index_save(index: dict) -> None:
    """Atomically write the IPFS index with file locking."""
    IPFS_INDEX.parent.mkdir(parents=True, exist_ok=True)
    lock_fd = os.open(str(_INDEX_LOCK), os.O_CREAT | os.O_RDWR)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        tmp_path = None
        try:
            fd, tmp_path = tempfile.mkstemp(dir=str(IPFS_INDEX.parent), suffix=".tmp")
            with os.fdopen(fd, "w") as f:
                json.dump(index, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, str(IPFS_INDEX))
        except BaseException:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)


def ipfs_add(filepath: str) -> str | None:
    """Add a file to IPFS and return its CID, or None on failure."""
    try:
        r = subprocess.run(
            ["ipfs", "add", "-Q", "--pin", filepath],
            capture_output=True,
            text=True,
            timeout=600,
        )
        if r.returncode == 0:
            return r.stdout.strip()
        log.warning("ipfs add failed (exit %d): %s", r.returncode, r.stderr.strip())
    except Exception as e:
        log.error("ipfs add exception for %s: %s", filepath, e)
    return None


def ipfs_add_with_progress(filepath: str, task) -> str | None:
    """Add a file to IPFS with progress output streamed to a Task.

    Falls back to ipfs_add if progress streaming fails.
    """
    try:
        proc = subprocess.Popen(
            ["ipfs", "add", "--pin", "--progress", filepath],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        cid = None
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            # Progress lines look like: " 123.45 MB / 456.78 MB [====>   ] 27.01%"
            # Final line: "added <CID> <filename>"
            if line.startswith("added "):
                parts = line.split()
                if len(parts) >= 2:
                    cid = parts[1]
                task.emit(line, "success")
            else:
                task.emit(line)
        proc.wait()
        if proc.returncode == 0 and cid:
            return cid
        log.warning("ipfs add --progress failed (exit %d)", proc.returncode)
    except Exception as e:
        log.error("ipfs add --progress exception: %s", e)
    return None


def ipfs_cat_to_file(cid: str, dest: str) -> bool:
    """Retrieve a file from IPFS by CID and write it to dest."""
    try:
        r = subprocess.run(
            ["ipfs", "get", "-o", dest, cid],
            capture_output=True,
            text=True,
            timeout=600,
        )
        if r.returncode != 0:
            log.warning("ipfs get failed for %s (exit %d): %s", cid, r.returncode, r.stderr.strip())
        return r.returncode == 0
    except Exception as e:
        log.error("ipfs get exception for %s: %s", cid, e)
        return False


def ipfs_pin_ls(cid: str) -> bool:
    """Check if a CID is pinned locally."""
    try:
        r = subprocess.run(
            ["ipfs", "pin", "ls", "--type=recursive", cid],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return r.returncode == 0 and cid in r.stdout
    except Exception as e:
        log.debug("ipfs pin ls failed for %s: %s", cid, e)
        return False


def ipfs_remote_pin(cid: str, name: str = "") -> bool:
    """Pin a CID to configured remote pinning services.

    Uses the IPFS Remote Pinning API (ipfs pin remote add).
    Returns True if at least one remote pin succeeded, False otherwise.
    """
    try:
        r = subprocess.run(
            ["ipfs", "pin", "remote", "ls", "--service=osmosis-pin", "--enc=json"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if r.returncode != 0:
            log.debug("Remote pin service check failed: %s", r.stderr.strip())
            return False
    except Exception as e:
        log.debug("Remote pin service check exception: %s", e)
        return False

    try:
        cmd = ["ipfs", "pin", "remote", "add", "--service=osmosis-pin"]
        if name:
            cmd.extend(["--name", name])
        cmd.append(cid)
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            log.warning("Remote pin failed for %s: %s", cid, r.stderr.strip())
        return r.returncode == 0
    except Exception as e:
        log.error("Remote pin exception for %s: %s", cid, e)
        return False


def ipfs_remote_pin_configured() -> bool:
    """Check if any remote pinning service is configured."""
    try:
        r = subprocess.run(
            ["ipfs", "pin", "remote", "service", "ls"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return r.returncode == 0 and "osmosis-pin" in r.stdout
    except Exception as e:
        log.debug("Remote pin service check exception: %s", e)
        return False


def ipfs_find_providers(cid: str, max_providers: int = 5, timeout_secs: int = 10) -> list[str]:
    """Query the IPFS DHT for peers providing a CID.

    Returns a list of peer IDs (may be empty).
    """
    if not is_valid_cid(cid):
        return []
    try:
        r = subprocess.run(
            ["ipfs", "dht", "findprovs", f"--num-providers={max_providers}", cid],
            capture_output=True,
            text=True,
            timeout=timeout_secs + 2,
        )
        if r.returncode == 0 and r.stdout.strip():
            return [line.strip() for line in r.stdout.strip().splitlines() if line.strip()]
    except subprocess.TimeoutExpired:
        log.debug("DHT findprovs timed out for %s", cid)
    except Exception as e:
        log.debug("DHT findprovs failed for %s: %s", cid, e)
    return []


def ipfs_pin_and_index(
    filepath: str,
    *,
    key: str,
    codename: str = "",
    rom_id: str = "",
    rom_name: str = "",
    version: str = "",
    extra: dict | None = None,
    task=None,
) -> str | None:
    """Pin a file to IPFS and record it in the index. Returns CID or None.

    If ``task`` is provided, streams progress output via ipfs_add_with_progress.
    """
    import datetime
    from pathlib import Path

    if task:
        cid = ipfs_add_with_progress(filepath, task)
    else:
        cid = ipfs_add(filepath)
    if not cid:
        return None

    p = Path(filepath)
    index = ipfs_index_load()
    entry = {
        "cid": cid,
        "size": p.stat().st_size,
        "filename": p.name,
        "codename": codename,
        "rom_id": rom_id,
        "rom_name": rom_name,
        "version": version,
        "pinned_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    if extra:
        entry.update(extra)
    index[key] = entry
    ipfs_index_save(index)
    return cid


def ipfs_index_lookup(codename: str, filename: str) -> dict | None:
    """Look up a CID in the IPFS index by codename and filename.

    Returns the index entry dict if found, or None.
    """
    index = ipfs_index_load()
    # Direct key match
    key = f"{codename}/{filename}"
    if key in index:
        return index[key]
    # Scan for matching codename + filename
    for _key, entry in index.items():
        if entry.get("codename") == codename and entry.get("filename") == filename:
            return entry
    return None


def verify_fetched_file(filepath: str) -> dict:
    """Verify a fetched file against the firmware registry.

    Returns {"sha256": ..., "known": bool, "matches": [...]}.
    """
    sha256 = sha256_file(filepath)
    matches = registry_lookup(sha256)
    return {"sha256": sha256, "known": len(matches) > 0, "matches": matches}


# ---------------------------------------------------------------------------
# Build layer caching via IPFS
# ---------------------------------------------------------------------------


def layer_cache_key(layer_type: str, **kwargs) -> str:
    """Compute a deterministic cache key for a build layer.

    layer_type: "base" or "packages"
    kwargs: distro, suite, arch, packages (list), desktop, etc.
    """
    parts = [layer_type]
    for k in sorted(kwargs):
        v = kwargs[k]
        if isinstance(v, (list, tuple)):
            v = ",".join(sorted(str(x) for x in v))
        parts.append(f"{k}={v}")
    raw = "|".join(parts)
    h = _hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"os-layer/{layer_type}-{kwargs.get('distro', 'unknown')}-{kwargs.get('suite', '')}-{kwargs.get('arch', '')}-{h}"


def layer_cache_lookup(cache_key: str) -> str | None:
    """Check if a build layer is cached in IPFS. Returns CID or None."""
    index = ipfs_index_load()
    entry = index.get(cache_key)
    if entry and entry.get("cid"):
        if ipfs_available() and ipfs_pin_ls(entry["cid"]):
            return entry["cid"]
    return None


def layer_cache_save(tarball_path: str, cache_key: str, metadata: dict | None = None) -> str | None:
    """Pin a layer tarball to IPFS and record it in the index."""
    return ipfs_pin_and_index(
        tarball_path,
        key=cache_key,
        codename="os-layer",
        rom_name=cache_key,
        extra=metadata or {},
    )


def layer_cache_restore(cid: str, rootfs_path: str, task=None) -> bool:
    """Restore a cached layer from IPFS by extracting its tarball into rootfs_path.

    Returns True on success.
    """
    import tempfile as _tempfile
    from pathlib import Path

    dest_dir = Path(rootfs_path)
    dest_dir.mkdir(parents=True, exist_ok=True)

    with _tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        ok = ipfs_cat_to_file(cid, tmp_path)
        if not ok:
            if task:
                task.emit("Failed to fetch layer from IPFS.", "warn")
            return False

        rc = subprocess.run(
            ["tar", "xzf", tmp_path, "-C", str(dest_dir)],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if rc.returncode != 0:
            log.warning("Layer extract failed: %s", rc.stderr.strip())
            if task:
                task.emit(f"Layer extract failed: {rc.stderr.strip()}", "warn")
            return False

        return True
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Manifest signing (Ed25519)
# ---------------------------------------------------------------------------

_KEYFILE = IPFS_INDEX.parent / "signing-key.pem"
_TRUSTED_KEYS_FILE = IPFS_INDEX.parent / "trusted-publishers.json"


def _get_or_create_signing_key():
    """Load or generate an Ed25519 signing keypair."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    if _KEYFILE.exists():
        pem = _KEYFILE.read_bytes()
        return serialization.load_pem_private_key(pem, password=None)

    key = Ed25519PrivateKey.generate()
    _KEYFILE.parent.mkdir(parents=True, exist_ok=True)
    _KEYFILE.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    _KEYFILE.chmod(0o600)
    return key


def get_public_key_b64() -> str:
    """Return this node's Ed25519 public key as base64."""
    from cryptography.hazmat.primitives import serialization

    key = _get_or_create_signing_key()
    pub_bytes = key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    return _b64.b64encode(pub_bytes).decode()


def sign_manifest(payload: str) -> str:
    """Sign a manifest JSON string, returning a base64 signature."""
    key = _get_or_create_signing_key()
    sig = key.sign(payload.encode())
    return _b64.b64encode(sig).decode()


def verify_manifest_signature(payload: str, signature_b64: str, pubkey_b64: str) -> bool:
    """Verify an Ed25519 signature on a manifest."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    try:
        pub_bytes = _b64.b64decode(pubkey_b64)
        sig_bytes = _b64.b64decode(signature_b64)
        pub_key = Ed25519PublicKey.from_public_bytes(pub_bytes)
        pub_key.verify(sig_bytes, payload.encode())
        return True
    except Exception:
        return False


def get_trusted_publishers() -> dict[str, str]:
    """Load trusted publisher keys. Returns {name: pubkey_b64}."""
    if _TRUSTED_KEYS_FILE.exists():
        try:
            return json.loads(_TRUSTED_KEYS_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


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
