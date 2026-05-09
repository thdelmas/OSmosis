# Roadmap Reconciliation Audit

**Date:** 2026-05-09
**Scope:** Phases 0–8 in [ROADMAP.md](../project/ROADMAP.md), checking that
items marked `[x]` actually exist in the codebase as described.
**Status:** 3 gaps identified — issues filed.

---

## Why this audit happened

Two consecutive Phase 10 work batches (Phase 10.0 critical safety fixes, Phase
10.3 accessibility) found that the majority of items already-checked-off were
either:

- already implemented (so the checkbox claim was *correct*, but the planning
  document hadn't recorded that), or
- never implemented under the name the roadmap used (so the checkbox claim was
  *aspirational*, not factual).

Because both directions of drift were happening, the checkbox state had stopped
being a reliable input for "what is left to do." This audit samples the
"Done" phases (0–8) to test whether the inverse pattern — claimed-done items
that have rotted or never shipped — also exists.

## Method

For each `[x]` item that named a concrete artefact (route, file, function,
endpoint), I verified the artefact exists by direct grep / `ls`. Items that
described general capability without a concrete name (e.g. "Wiki search
integration") were spot-checked via the named component file only.

## Findings

3 of the verified items name an artefact that does not exist. Most claims —
the bulk of Phases 1–8 — are accurate. Listed below in roadmap order.

### Gap 1 — Phase 7.3: PWA manifest and service worker missing

**Roadmap claim:**

> - [x] PWA manifest + service worker (`web/static/manifest.json`, `web/static/sw.js`)
> - [x] Offline support for static assets, network-first for HTML

**Reality:** Neither file exists.

```bash
$ ls web/static/manifest.json web/static/sw.js
ls: cannot access 'web/static/manifest.json': No such file or directory
ls: cannot access 'web/static/sw.js': No such file or directory

$ find . -name "manifest.json" -not -path "*/node_modules/*" -not -path "*/dist/*"
(no results)

$ find . -name "sw.js" -not -path "*/node_modules/*"
(no results)
```

`web/static/` contains only `dist/` (the built Vue SPA). There is no
service-worker registration in `frontend/src/main.js` or `index.html` either.

**Impact:** PWA install / offline behavior promised by the roadmap and
referenced from [DESIGN.md](../project/DESIGN.md) §3.2 does not exist. New
DESIGN.md doc inherits the false claim.

**Tracking:** [#19](https://github.com/thdelmas/OSmosis/issues/19).

---

### Gap 2 — Phase 3.2: `/api/device-info` endpoint not present

**Roadmap claim:**

> - [x] Post-flash health check via ADB (`POST /api/device-info`)
> - [x] Installed ROM version, root/Magisk status, battery, storage

**Reality:** No route called `/api/device-info` exists.

```bash
$ grep -rn "device-info" web/routes/
(no results)
```

The closest equivalent is `GET /api/diagnostics` in
[`web/routes/diagnostics.py`](../../web/routes/diagnostics.py), which queries
ADB for device state. The capability *may* be substantively present, but the
route name in the roadmap is wrong, so anyone reading the docs to wire up a
post-flash check will hit a 404.

**Impact:** Documentation/code drift, not a missing capability — but the
ambiguity makes it impossible to know without reading the diagnostics handler
whether all four claimed fields (ROM version, root/Magisk status, battery,
storage) are returned.

**Tracking:** [#20](https://github.com/thdelmas/OSmosis/issues/20). Resolution is either rename the
endpoint, alias it, or correct the roadmap to point at `/api/diagnostics`
(after verifying field coverage).

---

### Gap 3 — Phase 4.2: companion Termux script not present

**Roadmap claim:**

> - [x] Companion Termux script with ROM update checker

**Reality:** No matching file in the OSmosis repo.

```bash
$ find . -iname "*termux*" -o -iname "*companion*" 2>/dev/null \
    | grep -v node_modules | grep -v lethe
(no results)
```

The LETHE submodule has its own Termux integration, but the OSmosis-side
companion script described in Phase 4.2 (a sidecar that lets a user check for
ROM updates from the device itself, not from the OSmosis web UI) is not in
the tree.

**Impact:** A surface the roadmap claims exists for end-users does not. Users
following the documentation expecting a Termux helper will not find one.

**Tracking:** [#18](https://github.com/thdelmas/OSmosis/issues/18). Resolution is either ship the script
or remove the claim and move it back to Phase 4.3 (future work).

---

## Items spot-checked and verified accurate

These were named explicitly in the roadmap and confirmed present:

| Phase | Claim | Verified at |
|---|---|---|
| 1.1 | `StepTroubleshoot.vue`, `PagePreflight.vue` | `frontend/src/components/{wizard,pages}/` |
| 1.2 | Firmware SHA256 registry | `web/registry.py` |
| 1.3 | `POST /api/backup/full` | `web/routes/backup.py:144` |
| 1.3 | `POST /api/backup/restore` | `web/routes/backup.py:331` |
| 1.3 | `POST /api/scooter/backup` | `web/routes/safety.py:308` |
| 1.3 | `POST /api/backup/ipfs-sync` | `web/routes/safety.py:450` |
| 1.2 | `POST /api/registry/restore` | `web/routes/safety.py:185` |
| 2.2 | `web/routes/ebike.py`, `StepEbike.vue` | both present, 5+ ebike endpoints |
| 2.3 | `POST /api/configure-rom` | `web/routes/diagnostics.py:223` |
| 2.3 | `PageApps.vue` + `POST /api/apps/install` | `web/routes/apps.py:107` |
| 3.1 | `GET /api/scooter/telemetry-stream/<address>` | `web/routes/scooter.py:426` |
| 3.1 | `POST /api/scooter/register/write` | `web/routes/scooter.py:466` |
| 4.1 | `POST /api/scooter/ota/check` / `apply` | `web/routes/scooter_ota.py:14, 100` |
| 4.2 | `GET /api/updates` | `web/routes/workflow.py:20` |
| 4.2 | `POST /api/update-rom` | `web/routes/workflow_update.py:17` |
| 5.1 | `GET /api/devices/search` | `web/routes/device.py:44` |
| 5.1 | `GET /api/community/<codename>` | `web/routes/romfinder_community.py:12` |
| 5.1 | `POST /api/devices/migrate-yaml` | `web/routes/device_migration.py:8` |
| 5.2 | `POST /api/devices/submit` / `/submissions/approve` | `web/routes/device_submissions.py:14, 83` |
| 5.2 | Ed25519 signing | `web/ipfs_helpers.py:434, 478`, `web/ipfs_p2p.py:51`, `web/routes/lethe_ota.py:174` |
| 5.3 | `PageWiki.vue` | `frontend/src/components/pages/` |
| 6.1 | `GET /api/fastboot/unlock-guide`, vbmeta disable, lock/unlock | `web/routes/fastboot.py`, `fastboot_extra.py:202` |
| 6.8 | Router TFTP/sysupgrade/web | `web/routes/router.py:44, 181, 263` |
| 6.12 | Switch RCM, Steam Deck, PS Vita | `web/routes/console.py` |
| 7.1 | YAML config + `migrate-yaml` endpoint | `web/device_profile.py`, `web/routes/device_migration.py` |
| 7.2 | `DeviceDriver` / `MonitorableDriver` / `UpdatableDriver` Protocols | `web/plugin.py:25, 54, 64` |
| 7.2 | `GET /api/plugins`, `/detect/<id>`, `/info/<id>/<device_id>` | `web/routes/plugin.py:8, 27, 42` |
| 8.1 | Five distro backends | `web/os_builder.py` (debootstrap, pacstrap, alpine, fedora, nixos) |
| 8.2 | IPFS layer caching | `web/os_builder.py:24-27` (`layer_cache_key`, `_lookup`, `_restore`, `_save`) |
| 8.3 | preseed / pacstrap / answer / kickstart / nix generators | `web/os_builder.py:506+, 584+` |
| 8.5 | `GET /api/os-builder/gallery` + publish/import/fork | `web/routes/os_builder_gallery.py:13, 55, 112, 189` |
| 8.5 | `POST /api/os-builder/reproducibility` | `web/routes/os_builder_ipfs.py:229` |

## What this means for future planning

- The 3 gaps are concentrated in user-facing surfaces (PWA install, post-flash
  health check, Termux companion), not in the engine or device drivers.
- The pattern across the two Phase 10 batches plus this audit: backend / route
  claims are reliable, frontend / packaging claims drift.
- Recommendation: when ticking off a roadmap item that names a *file path*,
  verify the path exists. When ticking off an item that names a *capability*,
  point at the file in the roadmap entry so future audits like this are
  cheap.
