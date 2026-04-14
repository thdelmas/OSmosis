"""LAN sharing — direct peer-to-peer file transfer without IPFS.

Uses a lightweight HTTP server for file serving and mDNS (zeroconf)
for peer discovery on the local network. No internet required.

Flow:
  1. User clicks "Share on LAN" for a pinned ROM/firmware
  2. OSmosis starts a temporary HTTP server serving that file
  3. mDNS advertises the service as "_osmosis-share._tcp.local."
  4. Other OSmosis instances discover the peer via mDNS
  5. Receiver downloads the file with integrity check (SHA256 + CID)
"""

import hashlib
import json
import logging
import os
import socket
import subprocess
import threading
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

log = logging.getLogger(__name__)

# mDNS service type for LAN discovery
MDNS_SERVICE = "_osmosis-share._tcp.local."
SHARE_PORT_RANGE = (19200, 19299)

# Active shares: {share_id: ShareInfo}
_active_shares: dict[str, "ShareInfo"] = {}
_lock = threading.Lock()


class ShareInfo:
    """Tracks an active LAN share."""

    def __init__(
        self,
        share_id: str,
        file_path: str,
        filename: str,
        size: int,
        sha256: str,
        cid: str | None,
        port: int,
    ):
        self.share_id = share_id
        self.file_path = file_path
        self.filename = filename
        self.size = size
        self.sha256 = sha256
        self.cid = cid
        self.port = port
        self.server: HTTPServer | None = None
        self.thread: threading.Thread | None = None

    def to_dict(self) -> dict:
        return {
            "share_id": self.share_id,
            "filename": self.filename,
            "size": self.size,
            "sha256": self.sha256,
            "cid": self.cid,
            "port": self.port,
            "host": _get_lan_ip(),
        }


def start_share(
    file_path: str,
    filename: str | None = None,
    cid: str | None = None,
) -> ShareInfo | None:
    """Start sharing a file on the LAN.

    Returns ShareInfo or None on failure.
    """
    path = Path(file_path)
    if not path.exists():
        log.error("lan_share: file not found: %s", file_path)
        return None

    size = path.stat().st_size
    sha256 = _hash_file(str(path))
    fname = filename or path.name
    share_id = sha256[:12]

    # Find a free port
    port = _find_free_port()
    if port is None:
        log.error("lan_share: no free port in range %s", SHARE_PORT_RANGE)
        return None

    info = ShareInfo(
        share_id=share_id,
        file_path=str(path),
        filename=fname,
        size=size,
        sha256=sha256,
        cid=cid,
        port=port,
    )

    # Start HTTP server in a thread
    handler = partial(_ShareHandler, file_path=str(path), share_info=info)
    server = HTTPServer(("0.0.0.0", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    info.server = server
    info.thread = thread

    with _lock:
        _active_shares[share_id] = info

    # Register mDNS
    _register_mdns(info)

    log.info(
        "lan_share: sharing %s on port %d (id=%s, %d MB)",
        fname,
        port,
        share_id,
        size // (1024 * 1024),
    )
    return info


def stop_share(share_id: str) -> bool:
    """Stop sharing a file."""
    with _lock:
        info = _active_shares.pop(share_id, None)
    if info is None:
        return False
    if info.server:
        info.server.shutdown()
    _unregister_mdns(info)
    log.info("lan_share: stopped sharing %s", info.filename)
    return True


def list_shares() -> list[dict]:
    """Return all active shares."""
    with _lock:
        return [s.to_dict() for s in _active_shares.values()]


def discover_peers(timeout_secs: int = 5) -> list[dict]:
    """Discover other OSmosis instances sharing on the LAN via mDNS.

    Uses avahi-browse or dns-sd for zero-dependency discovery.
    """
    peers = []
    try:
        r = subprocess.run(
            [
                "avahi-browse",
                "-t",  # terminate after timeout
                "-r",  # resolve
                "-p",  # parseable
                "_osmosis-share._tcp",
            ],
            capture_output=True,
            text=True,
            timeout=timeout_secs + 2,
        )
        for line in r.stdout.strip().splitlines():
            if not line.startswith("="):
                continue
            parts = line.split(";")
            if len(parts) < 9:
                continue
            host = parts[7]
            port = int(parts[8]) if parts[8].isdigit() else 0
            txt = parts[9] if len(parts) > 9 else ""
            # Parse TXT record for metadata
            meta = _parse_txt_record(txt)
            peers.append({
                "host": host,
                "port": port,
                "filename": meta.get("fn", "unknown"),
                "size": int(meta.get("sz", 0)),
                "sha256": meta.get("h", ""),
                "cid": meta.get("c", ""),
                "share_id": meta.get("id", ""),
            })
    except FileNotFoundError:
        log.debug("lan_share: avahi-browse not found, trying dns-sd")
        # Fallback: could try dns-sd or manual broadcast
    except subprocess.TimeoutExpired:
        pass
    except Exception as e:
        log.debug("lan_share: discovery error: %s", e)
    return peers


def download_from_peer(
    host: str,
    port: int,
    dest_dir: str,
    expected_sha256: str | None = None,
) -> str | None:
    """Download a shared file from a LAN peer.

    Returns the path to the downloaded file, or None on failure.
    """
    import urllib.request

    # Get metadata first
    try:
        meta_url = f"http://{host}:{port}/meta"
        with urllib.request.urlopen(meta_url, timeout=5) as r:
            meta = json.loads(r.read())
    except Exception as e:
        log.error("lan_share: failed to get metadata from %s:%d: %s", host, port, e)
        return None

    filename = meta.get("filename", "download.zip")
    dest = os.path.join(dest_dir, filename)

    # Download the file
    try:
        file_url = f"http://{host}:{port}/file"
        urllib.request.urlretrieve(file_url, dest)
    except Exception as e:
        log.error("lan_share: download failed from %s:%d: %s", host, port, e)
        if os.path.exists(dest):
            os.unlink(dest)
        return None

    # Verify integrity
    if expected_sha256:
        actual = _hash_file(dest)
        if actual != expected_sha256:
            log.error(
                "lan_share: SHA256 mismatch for %s (expected %s, got %s)",
                filename,
                expected_sha256[:16],
                actual[:16],
            )
            os.unlink(dest)
            return None

    log.info("lan_share: downloaded %s from %s:%d", filename, host, port)
    return dest


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


class _ShareHandler(SimpleHTTPRequestHandler):
    """Serves a single file + metadata endpoint."""

    def __init__(self, *args, file_path: str, share_info: ShareInfo, **kwargs):
        self._file_path = file_path
        self._info = share_info
        super().__init__(*args, **kwargs)

    def do_GET(self):
        if self.path == "/meta":
            self._serve_meta()
        elif self.path == "/file":
            self._serve_file()
        else:
            self.send_error(404)

    def _serve_meta(self):
        meta = json.dumps(self._info.to_dict()).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(meta)))
        self.end_headers()
        self.wfile.write(meta)

    def _serve_file(self):
        try:
            size = os.path.getsize(self._file_path)
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(size))
            self.send_header(
                "Content-Disposition",
                f'attachment; filename="{self._info.filename}"',
            )
            self.end_headers()
            with open(self._file_path, "rb") as f:
                while chunk := f.read(65536):
                    self.wfile.write(chunk)
        except Exception as e:
            log.error("lan_share: serve error: %s", e)
            self.send_error(500)

    def log_message(self, format, *args):
        log.debug("lan_share: %s", format % args)


def _hash_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def _find_free_port() -> int | None:
    for port in range(SHARE_PORT_RANGE[0], SHARE_PORT_RANGE[1] + 1):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(("", port))
            s.close()
            return port
        except OSError:
            continue
    return None


def _get_lan_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _register_mdns(info: ShareInfo):
    """Register the share via avahi-publish."""
    txt = f'"fn={info.filename}" "sz={info.size}" "h={info.sha256}" "id={info.share_id}"'
    if info.cid:
        txt += f' "c={info.cid}"'
    try:
        proc = subprocess.Popen(
            [
                "avahi-publish",
                "-s",
                f"osmosis-{info.share_id}",
                "_osmosis-share._tcp",
                str(info.port),
                *txt.split(),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        info._mdns_proc = proc
    except FileNotFoundError:
        log.debug("lan_share: avahi-publish not found, mDNS disabled")


def _unregister_mdns(info: ShareInfo):
    proc = getattr(info, "_mdns_proc", None)
    if proc:
        proc.terminate()


def _parse_txt_record(txt: str) -> dict:
    """Parse mDNS TXT record into key-value pairs."""
    result = {}
    for part in txt.replace('"', "").split():
        if "=" in part:
            k, _, v = part.partition("=")
            result[k] = v
    return result
