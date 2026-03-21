# IPFS Integration Audit

**Date:** 2026-03-21
**Scope:** All IPFS usage across OSmosis (backend helpers, routes, frontend, installer)
**Status:** All 15 findings resolved

---

## Overview

OSmosis uses a local Kubo (go-ipfs) node to pin, retrieve, and share firmware/ROM files over IPFS. The integration spans:

| Component | Files |
|---|---|
| Core helpers | `web/ipfs_helpers.py` |
| IPFS routes | `web/routes/ipfs.py` |
| ROM finder + download | `web/routes/romfinder.py` |
| Download-and-flash | `web/routes/workflow.py` |
| OS builder publish | `web/routes/os_builder.py` |
| Backup sync | `web/routes/safety.py` (`/api/backup/ipfs-sync`) |
| Firmware registry | `web/registry.py` (`update_ipfs_cid`) |
| Kubo installer | `web/routes/system.py` (`_install_ipfs`) |
| Frontend | `web/static/app.js`, `web/templates/index.html` |
| Local index | `~/.osmosis/ipfs-index.json` |

---

## Findings

### 1. Security

#### 1.1 No CID integrity verification after fetch

**Severity: High** | **Status: Fixed**

**Problem:** When retrieving files via `ipfs get`, the returned content was never verified against a known-good hash. A SHA256 was computed and displayed but never compared to the firmware registry. A user could be tricked into flashing a malicious file fetched via a socially-engineered CID.

**Fix:** Added `verify_fetched_file()` in `ipfs_helpers.py` which computes SHA256 and looks it up in the firmware registry. All three fetch paths (`ipfs.py:api_ipfs_fetch`, `romfinder.py:api_romfinder_download`, `workflow.py:api_download_and_flash`) now call this after download and emit a success or warning message depending on whether the hash is known.

#### 1.2 Arbitrary file path in pin endpoint

**Severity: High** | **Status: Fixed**

**Problem:** `/api/ipfs/pin` accepted any `filepath` from the request body and passed it to `ipfs add` with no path restrictions. An attacker with network access could pin sensitive files (SSH keys, `/etc/shadow`, config) to IPFS, making them publicly retrievable.

**Fix:** Added `_path_allowed_for_pin()` with an allowlist of directories (`~/Osmosis-downloads/`, `~/.osmosis/backups/`, `~/.osmosis/scooter-backups/`). Paths are resolved before comparison to prevent symlink bypasses. Requests for paths outside these roots return `403`.

#### 1.3 Fetch destination path traversal

**Severity: Medium** | **Status: Fixed**

**Problem:** `/api/ipfs/fetch`, `/api/romfinder/download`, and `/api/download-and-flash` all accepted `filename` from user input and joined it directly into a file path. A crafted filename like `../../.bashrc` could write outside the intended download directory.

**Fix:** All three endpoints now sanitize `filename` using `Path(...).name` to extract only the basename, stripping any directory components. Filenames starting with `.` are rejected and replaced with `rom.zip`.

#### 1.4 CID input not validated

**Severity: Medium** | **Status: Fixed**

**Problem:** CID values from user input were passed directly to subprocess calls and stored in JSON without format validation. Malformed CIDs caused long timeouts; crafted values posed a theoretical injection risk if future code used string interpolation.

**Fix:** Added `is_valid_cid()` in `ipfs_helpers.py` with a regex matching CIDv0 (`Qm...`) and CIDv1 (`bafy...`, `bafk...`, etc.). Applied at `/api/ipfs/fetch`, `/api/ipfs/remote-pin`, `/api/registry/ipfs-link`, and `/api/ipfs/manifest/import`.

#### 1.5 IPFS daemon exposed without authentication

**Severity: Medium** | **Status: Fixed**

**Problem:** The Kubo installer started the daemon with default settings after `ipfs init`. While the default API listens on `127.0.0.1`, there were no explicit CORS restrictions, and nothing prevented a user from changing the listen address to a public interface.

**Fix:** `_install_ipfs()` in `system.py` now explicitly configures the API and Gateway to localhost-only after `ipfs init`, and sets `Access-Control-Allow-Origin` to `http://127.0.0.1:5001` with restricted HTTP methods.

---

### 2. Reliability

#### 2.1 No content availability / replication strategy

**Severity: High** | **Status: Fixed**

**Problem:** Files were pinned only on the local node. If the machine went offline, CIDs shared with others became unretrievable. There was no integration with remote pinning services.

**Fix:** Added `ipfs_remote_pin()` and `ipfs_remote_pin_configured()` helpers using Kubo's Remote Pinning API with service name `osmosis-pin`. New endpoints: `/api/ipfs/remote-pin` (POST to pin a CID remotely) and `/api/ipfs/remote-pin/status` (check if a service is configured). Users set up their service with `ipfs pin remote service add osmosis-pin <endpoint> <key>`.

#### 2.2 IPFS index is a single JSON file with no locking

**Severity: Medium** | **Status: Fixed**

**Problem:** `ipfs-index.json` was read and written without file locking. Concurrent background tasks (e.g. two simultaneous ROM downloads that both auto-pin) could race, with one write silently overwriting the other's entry.

**Fix:** `ipfs_index_save()` now acquires an exclusive `fcntl.flock` on `~/.osmosis/.ipfs-index.lock`, writes to a temporary file via `tempfile.mkstemp`, calls `fsync`, and atomically replaces the index with `os.replace`. If the write fails, the temp file is cleaned up and the lock released.

#### 2.3 No garbage collection awareness

**Severity: Low** | **Status: Fixed**

**Problem:** The index could reference CIDs that were no longer locally pinned (e.g. after `ipfs repo gc`), with no way to detect this.

**Fix:** Added `/api/ipfs/health` endpoint that iterates over all indexed CIDs, calls `ipfs pin ls` for each, and returns counts of healthy vs stale entries along with details of any stale CIDs.

#### 2.4 Hardcoded Kubo version in installer

**Severity: Low** | **Status: Fixed**

**Problem:** `_install_ipfs` hardcoded Kubo `v0.33.2` with no upgrade path or staleness detection.

**Fix:** The installer now fetches `https://dist.ipfs.tech/kubo/versions`, filters out release candidates, and uses the latest stable version. Falls back to `v0.33.2` if the version list is unreachable.

---

### 3. Architecture / Code Quality

#### 3.1 Duplicated auto-pin logic

**Severity: Medium** | **Status: Fixed**

**Problem:** The "pin file to IPFS + update index" pattern was copy-pasted across three locations (`romfinder.py`, `workflow.py`, `os_builder.py`) with minor variations. Each duplicated the index-entry dict structure.

**Fix:** Extracted `ipfs_pin_and_index()` into `ipfs_helpers.py`. Takes `filepath`, `key`, and metadata kwargs; handles `ipfs_add`, index load/save, and timestamping in one place. Accepts an optional `task` parameter to use `ipfs_add_with_progress()` for streaming output. All three callers refactored to use it.

#### 3.2 Blocking subprocess calls in request handlers

**Severity: Medium** | **Status: Fixed**

**Problem:** `/api/ipfs/status` and `/api/ipfs/unpin` ran `subprocess.run` synchronously in the Flask request thread, blocking other requests for up to 30 seconds.

**Fix:** Both endpoints now use a module-level `ThreadPoolExecutor(max_workers=2)`. The status endpoint submits the subprocess work to the executor and waits with a timeout. The unpin endpoint fires the `ipfs pin rm` call to the executor without waiting (the index is updated synchronously since it's fast).

#### 3.3 Silent exception swallowing

**Severity: Medium** | **Status: Fixed**

**Problem:** Nearly every IPFS operation caught broad `Exception` and returned `False`/`None` with `pass`, making failures invisible and debugging very difficult.

**Fix:** Added `logging.getLogger(__name__)` to `ipfs_helpers.py`. All exception handlers now log at appropriate levels: `debug` for expected failures (daemon not running), `warning` for subprocess failures with stderr details, `error` for unexpected exceptions with tracebacks.

---

### 4. UX / Functionality Gaps

#### 4.1 No progress reporting for large files

**Severity: Medium** | **Status: Fixed**

**Problem:** IPFS add/get for multi-GB ROM files could take minutes with no feedback — just "Pinning to IPFS..." then success or failure.

**Fix:** Added `ipfs_add_with_progress()` which runs `ipfs add --progress` via `subprocess.Popen` and streams each progress line to the Task. Parses the final `added <CID> <filename>` line to extract the CID. Used by the pin endpoint via the `task` parameter on `ipfs_pin_and_index()`.

#### 4.2 Gateway URL points to public gateway

**Severity: Low** | **Status: Fixed**

**Problem:** Gateway links emitted `https://ipfs.io/ipfs/{cid}`, which is rate-limited, slow, and won't serve content that's only pinned locally.

**Fix:** All gateway URLs changed to `http://localhost:8080/ipfs/{cid}` (the local Kubo gateway).

#### 4.3 No way to share CIDs between users

**Severity: Low** | **Status: Fixed**

**Problem:** The IPFS index was local-only with no export/import mechanism, limiting the peer-to-peer value of IPFS pinning.

**Fix:** Added two endpoints:
- `GET /api/ipfs/manifest/export` — returns the full index as a versioned manifest with a SHA256 integrity hash
- `POST /api/ipfs/manifest/import` — accepts a manifest + SHA256, validates integrity, validates each CID format, and merges new entries into the local index (existing keys are not overwritten)

---

## Summary

| # | Issue | Severity | Category | Status |
|---|---|---|---|---|
| 1.1 | No CID integrity verification after fetch | High | Security | Fixed |
| 1.2 | Arbitrary file path in pin endpoint | High | Security | Fixed |
| 1.3 | Fetch destination path traversal | Medium | Security | Fixed |
| 1.4 | CID input not validated | Medium | Security | Fixed |
| 1.5 | IPFS daemon exposed without auth | Medium | Security | Fixed |
| 2.1 | No replication / remote pinning | High | Reliability | Fixed |
| 2.2 | Index file has no locking | Medium | Reliability | Fixed |
| 2.3 | No GC awareness | Low | Reliability | Fixed |
| 2.4 | Hardcoded Kubo version | Low | Reliability | Fixed |
| 3.1 | Duplicated auto-pin logic | Medium | Code quality | Fixed |
| 3.2 | Blocking subprocess in request handlers | Medium | Code quality | Fixed |
| 3.3 | Silent exception swallowing | Medium | Code quality | Fixed |
| 4.1 | No progress for large files | Medium | UX | Fixed |
| 4.2 | Gateway URL points to public gateway | Low | UX | Fixed |
| 4.3 | No CID sharing between users | Low | UX | Fixed |

### New API endpoints added

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/ipfs/remote-pin` | POST | Pin a CID to a configured remote pinning service |
| `/api/ipfs/remote-pin/status` | GET | Check if remote pinning is configured |
| `/api/ipfs/health` | GET | Verify all indexed CIDs are still pinned locally |
| `/api/ipfs/manifest/export` | GET | Export index as a shareable manifest |
| `/api/ipfs/manifest/import` | POST | Import entries from a shared manifest |
