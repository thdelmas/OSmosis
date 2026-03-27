# IPFS Roadmap

How Osmosis uses IPFS to decentralize firmware distribution, accelerate builds,
and enable community sharing — without depending on any central server.

This roadmap maps IPFS capabilities to the phases in the main
[ROADMAP.md](ROADMAP.md). Each item references the phase it enables and can be
implemented independently.

---

## Current State

What's already shipping:

- [x] Pin/unpin ROMs to local IPFS node
- [x] Fetch ROMs by CID with HTTP fallback
- [x] Local CID index (`~/.osmosis/ipfs-index.json`) with file locking
- [x] Integrity verification after fetch (SHA256 vs firmware registry)
- [x] CID format validation, path restrictions, filename sanitization
- [x] Kubo auto-installer with latest-version fetch and hardened config
- [x] Remote pinning support (`osmosis-pin` service)
- [x] Index health check (detect stale/unpinned CIDs)
- [x] Manifest export/import for sharing CID collections
- [x] OS builder publish-to-IPFS toggle
- [x] Backup directory sync to IPFS
- [x] Progress streaming for large IPFS operations
- [x] Frontend: pin/unpin, fetch by CID, status, IPFS storage panel

---

## Tier 1 — Wire Up What Exists (done)

*Effort: small. No new IPFS features, just connecting existing infra.*

### 1.1 Surface hidden features in the UI

- [x] Add IPFS health check to the IPFS storage panel
- [x] Add remote pinning status + trigger button
- [x] Add "Sync to IPFS" button on backup pages
- [x] Show manifest export/import in IPFS panel

### 1.2 Auto-pin CFW builds

- [x] Pin scooter CFW output ZIP after build
- [x] Include build parameters in the index entry (patch toggles, speed limits)

### 1.3 Firmware version history with IPFS fetch

- [x] `POST /api/registry/restore` — fetch old firmware by CID with SHA256 verification

---

## Tier 2 — IPFS as Download Fallback (done)

### 2.1 Check IPFS index before HTTP download

- [x] `ipfs_index_lookup(codename, filename)` helper
- [x] Integrated into `romfinder.py` and `workflow.py` as first-choice path
- [x] Shows "Found in local IPFS cache" in terminal output

### 2.2 Imported manifests as ROM sources

- [x] Imported entries appear in ROM finder with `source: "community-ipfs"`
- [x] Distinct magenta badge in UI for community-sourced ROMs

### 2.3 Device config distribution

- [x] `POST /api/ipfs/publish-configs` — pin all config files
- [x] `GET /api/ipfs/config-status` — check which configs are pinned
- [x] Config channel subscription model with update checking and applying

---

## Tier 3 — Build Layer Caching via IPFS

*Effort: large. New build architecture. Highest impact on build time.*

### The problem

Every OS build downloads everything from scratch:

| Build step | What it downloads | Size | Time |
|---|---|---|---|
| `debootstrap` (Debian/Ubuntu) | Base system from archive.ubuntu.com | 200-300 MB | 2-5 min |
| `pacstrap` (Arch) | Base + kernel from mirrors | 400-600 MB | 3-8 min |
| `apk add` (Alpine) | Minirootfs tarball from CDN | 5-10 MB | <1 min |
| `dnf install` (Fedora) | Base system packages | 300-400 MB | 3-7 min |
| Package installation | Desktop env + extras via apt/pacman/dnf | 400-2000 MB | 5-30 min |
| Kernel | `linux-image-*` or `linux` package | 100-200 MB | included above |

A GNOME desktop build on Ubuntu 24.04 downloads ~1.5 GB every time. Two builds
with the same base but different users/hostnames repeat 100% of that work.

### The insight

Builds are layered. Each layer is deterministic given its inputs:

```
Layer 0: base rootfs      = f(distro, suite, arch)
Layer 1: + packages        = f(Layer 0, package list, desktop)
Layer 2: + user config     = f(Layer 1, hostname, users, locale, network, ...)
Layer 3: + output format   = f(Layer 2, img/iso/rootfs, image_size, partitioning)
```

Layers 0 and 1 are **fully deterministic** — same inputs always produce the
same output (modulo upstream mirror timing, handled by pinning). Layer 2 adds
user-specific config. Layer 3 adds disk layout.

IPFS gives us content-addressed layer caching for free: tar up a layer, pin it,
and its CID **is** its cache key.

### 3.1 Cache base rootfs layers

- [x] Debian/Ubuntu, Arch, Alpine, Fedora all check IPFS for cached base layer
- [x] Cache key: `os-layer/base-{distro}-{suite}-{arch}-{hash}`
- [x] Cache miss: build normally, tar + pin the result
- [x] Cache hit: `ipfs get` + extract, skip bootstrap entirely

### 3.2 Cache package layers

- [x] Debian/Ubuntu caches full rootfs after package installation
- [x] Cache key includes distro, suite, arch, desktop, and sorted package hash
- [x] Unmount/remount virtual filesystems around tar operations

### 3.3 Share layers between users via IPFS

- [x] `GET /api/os-builder/layers` — list all cached layers
- [x] `GET /api/os-builder/layers/manifest` — export layers as signed manifest
- [x] `POST /api/os-builder/layers/prefetch` — pre-fetch layers from a shared
      profile or manifest
- [x] Build profiles include `layer_cids` for reproducibility tracking

### 3.4 Package cache via IPFS

- [x] `_restore_pkg_cache()` / `_save_pkg_cache()` helpers
- [x] apt package cache bind-mounted from `~/.osmosis/os-builder/pkg-cache/`
- [x] Cache pinned to IPFS after build, restored before next build
- [x] Complementary to layer caching — packages reused even on layer miss

### Build time impact summary

| Scenario | Without cache | With Layer 0 | With Layer 0+1 |
|---|---|---|---|
| First build (Ubuntu GNOME) | 15-40 min | 15-40 min | 15-40 min |
| Second build (same profile) | 15-40 min | 10-35 min | 2-5 min |
| Different user, same base+pkgs | 15-40 min | 10-35 min | 2-5 min |
| Same base, different desktop | 15-40 min | 10-35 min | 8-25 min |
| Same base, different packages | 15-40 min | 10-35 min | 10-35 min |
| Peer on LAN built same base | 15-40 min | 1-3 min | 1-3 min |

---

## Tier 4 — Community & Ecosystem (done)

### 4.1 CFW manifest sharing

- [x] `GET /api/cfw/manifest/export/<scooter_id>` — export all CFW builds with
      build configs and CIDs
- [x] `POST /api/cfw/manifest/import` — import, validate CIDs, merge into index

### 4.2 Device config as IPFS documents

- [x] Config channel subscription: `POST /api/ipfs/config-channel` to subscribe
      by manifest CID
- [x] `GET /api/ipfs/config-channel/check` — compare local vs channel CIDs
- [x] `POST /api/ipfs/config-channel/apply` — fetch and apply updated configs

### 4.3 Peer discovery for ROM availability

- [x] `ipfs_find_providers()` helper using `ipfs dht findprovs`
- [x] `GET /api/ipfs/providers/<cid>` endpoint
- [x] ROM finder UI lazily loads peer counts for IPFS-pinned ROMs

### 4.4 Signed manifests for trust

- [x] Ed25519 keypair auto-generated on first use (`~/.osmosis/signing-key.pem`)
- [x] Manifest export includes signature + public key
- [x] Manifest import verifies signature, reports trusted/untrusted publisher
- [x] `GET /api/ipfs/identity` — this node's public key
- [x] `GET/POST/DELETE /api/ipfs/trust` — manage trusted publishers list

---

## Tier 5 — Reproducible Build Distribution (done)

### 5.1 Build reproducibility via CID

- [x] `_collect_layer_cids()` populates `profile.layer_cids` before profile save
- [x] `POST /api/os-builder/reproducibility` — compare a profile's layer CIDs
      against local cache to verify reproducibility

### 5.2 Community build gallery

- [x] `GET /api/os-builder/gallery` — browse published builds with filtering
      by distro, arch, desktop
- [x] `POST /api/os-builder/gallery/publish` — export a build as a signed manifest
- [x] `POST /api/os-builder/gallery/import` — import a published build with
      signature verification and trust checking
- [x] `POST /api/os-builder/gallery/fork` — fork a gallery build into a new
      editable profile

---

## Implementation Status

| Item | Effort | Enables | Status |
|---|---|---|---|
| 1.1 Surface hidden UI features | S | Phase 1 | Done |
| 1.2 Auto-pin CFW builds | S | Phase 2 | Done |
| 1.3 Firmware version history fetch | S | Phase 1.2 | Done |
| 2.1 IPFS-first download fallback | M | Phase 1.2 | Done |
| 2.2 Imported manifests as ROM sources | M | Phase 5 | Done |
| 2.3 Device config distribution | M | Phase 5.2 | Done |
| 3.1 Cache base rootfs layers | M | Phase 8 | Done |
| 3.2 Cache package layers | L | Phase 8 | Done |
| 3.3 Share layers between users | M | Phase 8 | Done |
| 3.4 Package cache via IPFS | M | Phase 8 | Done |
| 4.1 CFW manifest sharing | M | Phase 2 + 5 | Done |
| 4.2 Device config as IPFS documents | M | Phase 5 + 7 | Done |
| 4.3 Peer discovery for availability | S | Phase 5 | Done |
| 4.4 Signed manifests | M | Phase 5.2 | Done |
| 5.1 Reproducible builds via CID | L | Phase 8 | Done |
| 5.2 Community build gallery | L | Phase 8.6 | Done |

---

## Tier 6 — Leverage Full IPFS Capabilities

*Use IPFS as more than a content-addressed file store. IPNS gives us mutable
pointers, CAR files give us offline portability, PubSub gives us real-time
notifications, and Bitswap stats make the peer-to-peer network visible.*

### 6.1 IPNS for config channels

**Problem:** The current config channel system requires manually exchanging
CIDs. Every time configs update, the channel CID changes and subscribers have
no way to discover the new one without out-of-band communication.

**Solution:** Each publisher gets an IPNS name (derived from their signing key
or a dedicated IPNS key). Publishing updates the IPNS pointer to the latest
config manifest CID. Subscribers resolve the IPNS name to always get the
current version — no more CID chasing.

- [x] `ipfs_helpers.py`: `ipns_publish(cid, key_name)` — publish a CID under
      an IPNS key
- [x] `ipfs_helpers.py`: `ipns_resolve(ipns_name)` — resolve an IPNS name to
      its current CID
- [x] `ipfs_helpers.py`: `ipns_key_create(name)` — create a dedicated IPNS key
      for config publishing
- [x] `POST /api/ipfs/publish-configs` — publishes configs and updates the
      IPNS pointer under the `osmosis-configs` key
- [x] Migrate `POST /api/ipfs/config-channel` to accept IPNS names in addition
      to raw CIDs
- [x] `GET /api/ipfs/config-channel/check` resolves IPNS before comparing CIDs
- [x] Store `ipns_name` in channel subscription file alongside `channel_cid`

### 6.2 CAR export/import for offline transfer

**Problem:** IPFS requires a live network connection and a running daemon.
Users in offline environments, restricted networks, or sneakernet scenarios
cannot transfer firmware between machines.

**Solution:** CAR (Content Addressable aRchive) files bundle IPFS blocks into
a single portable file. Export a manifest + all its firmware as a `.car` file,
carry it on a USB stick, and import it on another machine — no internet needed.

- [x] `ipfs_helpers.py`: `ipfs_dag_export(cid, dest_path)` — export a CID's
      DAG to a `.car` file
- [x] `ipfs_helpers.py`: `ipfs_dag_import(car_path)` — import a `.car` file
      and pin its roots
- [x] `POST /api/ipfs/car/export` — export selected index entries (or full
      manifest) as a downloadable `.car` file
- [x] `POST /api/ipfs/car/import` — import a `.car` file, pin roots, merge
      into IPFS index
- [x] Frontend: "Export for offline transfer" button in IPFS storage panel
- [x] Frontend: "Import .car file" upload in IPFS storage panel

### 6.3 PubSub for real-time update notifications

**Problem:** Config channel updates are poll-based. Users must manually check
for updates or periodically hit the check endpoint. No real-time awareness of
new firmware availability from peers.

**Solution:** IPFS PubSub lets peers subscribe to a topic and receive messages
in real time. When a publisher pins new firmware or updates configs, they
broadcast a notification to the `osmosis-updates` topic. Online subscribers
hear about it immediately.

- [x] `ipfs_helpers.py`: `pubsub_publish(topic, message)` — publish a JSON
      message to an IPFS PubSub topic
- [x] `ipfs_helpers.py`: `pubsub_subscribe(topic)` — subscribe and yield
      messages from a topic
- [x] `POST /api/ipfs/pubsub/publish` — broadcast an update notification
      (new firmware, config change)
- [x] `GET /api/ipfs/pubsub/subscribe` — SSE endpoint that relays PubSub
      messages to the frontend
- [x] Auto-publish on config-channel publish and manifest export
- [x] Frontend: notification badge when PubSub update arrives

### 6.4 Bitswap stats for community seeding visibility

**Problem:** Users have no visibility into their contribution to the IPFS
network. There's no way to see how much firmware they've served to peers
or how the community network is functioning.

**Solution:** Surface `ipfs bitswap stat` data in the UI. Show bytes
sent/received, number of peers, and seeding ratio. Turns passive users into
visible community participants.

- [x] `ipfs_helpers.py`: `ipfs_bitswap_stat()` — parse bitswap statistics
- [x] `GET /api/ipfs/bitswap` — return bitswap stats (blocks/bytes
      sent/received, peer count, seeding ratio)
- [x] Frontend: community contribution panel showing seeding stats

---

## Implementation Status

| Item | Effort | Enables | Status |
|---|---|---|---|
| 1.1 Surface hidden UI features | S | Phase 1 | Done |
| 1.2 Auto-pin CFW builds | S | Phase 2 | Done |
| 1.3 Firmware version history fetch | S | Phase 1.2 | Done |
| 2.1 IPFS-first download fallback | M | Phase 1.2 | Done |
| 2.2 Imported manifests as ROM sources | M | Phase 5 | Done |
| 2.3 Device config distribution | M | Phase 5.2 | Done |
| 3.1 Cache base rootfs layers | M | Phase 8 | Done |
| 3.2 Cache package layers | L | Phase 8 | Done |
| 3.3 Share layers between users | M | Phase 8 | Done |
| 3.4 Package cache via IPFS | M | Phase 8 | Done |
| 4.1 CFW manifest sharing | M | Phase 2 + 5 | Done |
| 4.2 Device config as IPFS documents | M | Phase 5 + 7 | Done |
| 4.3 Peer discovery for availability | S | Phase 5 | Done |
| 4.4 Signed manifests | M | Phase 5.2 | Done |
| 5.1 Reproducible builds via CID | L | Phase 8 | Done |
| 5.2 Community build gallery | L | Phase 8.6 | Done |
| 6.1 IPNS for config channels | M | Phase 5 + 7 | Done |
| 6.2 CAR export/import | M | Offline/portable | Done |
| 6.3 PubSub + auto-publish | M | Phase 5 + 7 | Done |
| 6.3 PubSub notification badge | S | Phase 5 + 7 | Done |
| 6.4 Bitswap stats | S | Community | Done |

---

## Principles

1. **IPFS is always optional.** Every feature works without it. IPFS adds
   speed, resilience, and sharing — never gates functionality.
2. **Local first.** IPFS index is local. Builds work offline. Remote pinning
   is opt-in.
3. **Content-addressed everything.** If two files have the same bytes, they
   have the same CID. No duplication, no version confusion.
4. **Cache, don't rebuild.** The fastest build is the one that doesn't happen.
   Layer caching turns 30-minute builds into 2-minute cache restores.
5. **Share by default, trust explicitly.** Pinning is automatic. Fetching from
   untrusted peers always verifies against the firmware registry.
