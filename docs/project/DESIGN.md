# OSmosis Design

How OSmosis is put together. Read [MANIFESTO.md](MANIFESTO.md) for the *why*
and [ROADMAP.md](ROADMAP.md) for the *what's next*. This document covers the
*how*: the architectural choices that shape the codebase.

---

## 1. Goals that drive the design

These manifesto principles directly shape architectural decisions:

- **Local-first, no central server** (Manifesto §8) — there is no OSmosis
  cloud. The web UI runs on `localhost`. Firmware moves over IPFS, not a CDN.
  The tool keeps working offline once assets are cached.
- **Complexity is our problem** (Manifesto §4) — the engine absorbs the
  divergence between flash protocols (Heimdall, fastboot, adb sideload,
  esptool, ST-Link, BLE, TFTP, RCM…) so the user sees one wizard.
- **Teach, don't hide** (Manifesto §9) — every command is shown, dry-run is
  first-class, and session logs are retained.
- **Open source or go home** (Manifesto §7) — we wrap upstream tools rather
  than reimplement them. OSmosis is glue, not a vendor stack.
- **CLI/Web parity** — the CLI (`osmosis.sh`) and web UI must expose the
  same operations. Logic lives behind HTTP endpoints; both surfaces call them.

---

## 2. Top-level shape

```
┌────────────────────────┐        ┌────────────────────────┐
│   CLI  (osmosis.sh)    │        │  Web UI  (Vue 3 SPA)   │
│   bash wizard          │        │  http://localhost:5000 │
└──────────┬─────────────┘        └───────────┬────────────┘
           │                                  │
           └────────────────┬─────────────────┘
                            ▼
                ┌───────────────────────┐
                │  Flask backend (web/) │
                │  routes/  + engines   │
                └───────────┬───────────┘
                            ▼
   ┌────────────────────────────────────────────────────────┐
   │  External tools: heimdall, adb, fastboot, esptool,     │
   │  st-flash, bleak (BLE), dnsmasq (TFTP), debootstrap,   │
   │  pacstrap, nix-build, ipfs, ...                        │
   └────────────────────────────────────────────────────────┘
                            ▼
   ┌────────────────────────────────────────────────────────┐
   │  Device profiles (profiles/*.yaml) + legacy *.cfg      │
   │  Firmware registry + IPFS pins                         │
   │  ~/.osmosis/  and  ~/Osmosis-downloads/                │
   └────────────────────────────────────────────────────────┘
```

Two surfaces, one engine, profile-driven, wrapping upstream tools.

---

## 3. Components

### 3.1 Backend — `web/`

A Flask app composed of route modules and stateless engine modules. Entry
point: [web/app.py](../../web/app.py).

**Route modules** (`web/routes/`) — one per device family or workflow. Each
exposes a small HTTP surface (e.g. [`scooter.py`](../../web/routes/scooter.py),
[`fastboot.py`](../../web/routes/fastboot.py),
[`os_builder.py`](../../web/routes/os_builder.py)). New device families are
added by dropping a new route module + a profile, not by editing a
monolith.

**Engine modules** (`web/*.py`) — cross-cutting capabilities the routes
compose:

| Module | Responsibility |
|---|---|
| [`core.py`](../../web/core.py) | Subprocess execution, dry-run, logging |
| [`device_profile.py`](../../web/device_profile.py) | YAML/cfg profile loader |
| [`flow_engine.py`](../../web/flow_engine.py) + [`flow_loader.py`](../../web/flow_loader.py) | Declarative multi-step flash flows |
| [`plugin.py`](../../web/plugin.py) | `DeviceDriver` / `MonitorableDriver` / `UpdatableDriver` protocols + auto-discovery of `web/plugins/` |
| [`registry.py`](../../web/registry.py) | Firmware SHA256 registry + version history |
| [`integrity.py`](../../web/integrity.py) | Verification, scheduled re-checks |
| [`safety.py`](../../web/safety.py) | Pre-flight checks (battery, storage, backup) |
| [`ipfs_helpers.py`](../../web/ipfs_helpers.py), [`ipfs_p2p.py`](../../web/ipfs_p2p.py) | IPFS fetch/pin, P2P config channels |
| [`trusted_publishers.py`](../../web/trusted_publishers.py) | Ed25519 signature verification for community manifests |
| [`os_builder.py`](../../web/os_builder.py) | Distro chroot builds (debootstrap, pacstrap, apk, dnf, nix) |
| [`cfw_builder.py`](../../web/cfw_builder.py) | Scooter custom-firmware patch composer |

The split is deliberate: routes are thin and device-shaped; engines are
generic and reusable. Adding a device that reuses ST-Link should not touch
`core.py`; adding a new dry-run capability should not touch a route file.

### 3.2 Frontend — `frontend/`

Vue 3 + Vite SPA, served as static assets from `web/static/dist/` in
production and via Vite dev server (port 5173, proxied to Flask) during
development.

**Layout:**

- [`components/wizard/`](../../frontend/src/components/wizard/) — the linear
  install path: `StepGoal → StepCategory → StepIdentify → StepConnect →
  StepSoftware → StepBackup → StepLoad → StepInstall → StepFix /
  StepTroubleshoot`. Family-specific steps (`StepScooter`, `StepEbike`,
  `StepBootable`, `StepEreader`, `StepMicrocontroller`, `StepSbcSetup`,
  `StepOsBuilder`, `StepMediacat`, `StepT2`, `StepPixel`) branch off
  `StepCategory`.
- [`components/pages/`](../../frontend/src/components/pages/) — non-wizard
  utilities: `PageRegistry`, `PageIpfs`, `PageWiki`, `PageApps`,
  `PageConnectedDevice`, `PageFlashStock`, `PageFlashRecovery`,
  `PageSideload`, `PagePreflight`, etc.
- [`components/shared/`](../../frontend/src/components/shared/) — reusable UI
  (terminal output, task bars, glossary tips, error info-boxes).
- [`composables/`](../../frontend/src/composables/) — `useApi` (HTTP),
  `useTask` (long-running ops via SSE/polling), `useWizard` (step machine
  state), `useErrorGuide` (parse backend error types into actionable copy),
  `usePubsub`, `useTheme`.
- [`i18n/`](../../frontend/src/i18n/) — translations; every user-visible
  string passes through here.

The wizard is a finite state machine driven by `useWizard.js`. State
persists to `localStorage` so an interrupted flash can be resumed (with
explicit confirmation — see Phase 10.0 in the roadmap for the open work
on safe restoration).

PWA: [`web/static/manifest.json`](../../web/static/manifest.json) +
[`web/static/sw.js`](../../web/static/sw.js) — offline shell, network-first
for HTML.

### 3.3 CLI — `osmosis.sh`

Bash wizard at the repo root, with companion scripts (`recover-t0lte.sh`,
`recover-sm-t805.sh`, `bootloop-diagnose.sh`) that wrap specific recovery
flows. The CLI calls the same shell tools the backend does (`heimdall`,
`adb`, `fastboot`, `esptool`, …) so a CLI-only flash is reproducible
without Flask running.

`--dry-run` is honored end-to-end: every command is printed, no device
state changes.

### 3.4 Device profiles — `profiles/*.yaml`

Profiles are the source of truth for what OSmosis knows about a device.
Adding a device should mean adding a YAML file, not editing Python.

A profile declares:

- Identity: `id`, `brand`, `category`, `model`, `codename`, `usb_vid`
- Flash protocol: `flash_tool` (heimdall / fastboot / adb / esptool / …),
  `flash_method`, `partitions`
- Per-device protocol detail (e.g. Samsung's `heimdall_partition_map` —
  Samsung partition naming differs across generations)
- Firmware catalog: stock + alternative ROMs, each with `url`,
  `ipfs_cid`, `sha256`, `tags`
- `flash_steps[]`: an ordered list with `tool`, `command`, human-readable
  `description` (used by the wizard to render "what's about to happen")
- `post_flash[]`: idempotent follow-ups (`adb reboot`, etc.)
- Free-form `notes` for device-specific gotchas

Example structure: [`profiles/samsung-t0lte.yaml`](../../profiles/samsung-t0lte.yaml).

Legacy `*.cfg` files (`devices.cfg`, `ebikes.cfg`, `microcontrollers.cfg`,
`scooters.cfg`, etc.) coexist with YAML; loaders prefer YAML and fall back
to `.cfg`. Migration endpoint: `POST /api/devices/migrate-yaml`.

### 3.5 Plugin architecture — `web/plugins/`

For device families that don't fit the YAML profile model
(complex protocol, dynamic detection, custom UI), [`web/plugin.py`](../../web/plugin.py)
defines protocols a Python module can implement:

- `DeviceDriver` — `detect`, `flash`, `backup`, `info`
- `MonitorableDriver` — adds telemetry streaming
- `UpdatableDriver` — adds OTA check/apply

Plugins drop into [`web/plugins/`](../../web/plugins/) and are auto-discovered;
they're surfaced via `GET /api/plugins`. This keeps the door open for
community-contributed protocols (Vsett UART, NIU BLE, etc.) without merging
them into the core.

### 3.6 LETHE — `lethe/`

A git submodule containing the privacy-first agent OS. From OSmosis's
perspective LETHE is just another flash target listed in profiles for
supported phones. Its internal architecture (Rust agent, sepolicy, avatar
pipeline) is documented inside the submodule and is intentionally out of
scope for this document.

OSmosis and LETHE are separate scopes (per `feedback_repo_scope`): work on
LETHE's agent or UI does not belong in OSmosis route files, and vice versa.

---

## 4. Cross-cutting concerns

### 4.1 Distribution & integrity

OSmosis pushes everything through SHA256 + IPFS:

- Every firmware entry in the registry has a SHA256. Pre-flash verification
  is enforced (`web/integrity.py`).
- `ipfs_cid` is a first-class field on firmware entries. Downloads prefer
  IPFS; HTTP URLs are the fallback.
- Community manifests (firmware, CFW configs, OS-builder profiles, device
  submissions) are signed Ed25519 and verified against
  [`web/trusted_publishers.py`](../../web/trusted_publishers.py).
- Backups are pinned to IPFS on demand, so a phone can be restored from any
  machine with the same OSmosis install.

### 4.2 Long-running operations

Flashing is slow. The backend exposes long-running ops through:

- **SSE streams** for telemetry and live build logs (e.g. scooter
  `GET /api/scooter/telemetry-stream/<address>`, OS-builder build log).
- **Task pattern** for jobs the user navigates away from — `useTask.js`
  polls a status endpoint, surfaces progress, and renders a `TaskBar`.

Every long-running op should be **resumable** (Phase 12 goal): split into
discrete stages (`download → verify → flash → post-configure`), each
idempotent, each with its own status. Re-running a completed stage is a
no-op.

### 4.3 Safety model

Layered, with the failure modes ranked worst-first:

1. **Dry-run** — `--dry-run` and the web UI's preview mode print every
   command without executing. Safe to use to learn.
2. **Pre-flight checks** — battery > 25%, storage available, USB working,
   ADB authorized, backup present, signature verified. Encoded in
   [`safety.py`](../../web/safety.py) and wired into every flash route.
3. **Backup-before-flash** — full NAND for Samsung; firmware read-back for
   scooters; cached factory image for fastboot devices.
4. **Structured error guides** — `useErrorGuide.js` maps backend error
   types (`stale_session`, `usb_no_adb`, `permission_denied`,
   `signature_verification_failed`, `low_battery`, `locked_bootloader`)
   to human-readable recovery copy. Generic "command failed" messages are
   a bug.
5. **Physical button instructions with countdowns** — when the user has
   to press Power+Vol-Down etc., a timer is shown (per
   `feedback_button_timing`). No silent waits.
6. **Reversibility** — every operation should have a documented undo path.
   Bricks are bugs in the workflow, not user error.

### 4.4 Accessibility

Manifesto §5 makes accessibility a baseline, not an opt-in feature (per
`feedback_no_easy_mode`). Concretely:

- Plain language, no jargon-without-glossary (`GlossaryTip` component).
- WCAG AA targets for contrast and focus visibility.
- Keyboard navigation on all interactive elements (open work in Phase 10.3).
- `aria-live` regions for status updates, `aria-busy` on loading buttons.
- Tap targets ≥ 44×44 CSS pixels.
- Every screen answers "What is happening? What do I do next? Is it safe?"
  without the user asking.

### 4.5 Internationalization

All user-visible strings live in [`frontend/src/i18n/`](../../frontend/src/i18n/).
Backend error codes are stable identifiers; the frontend translates them.
Adding a language is adding a JSON file.

### 4.6 Filesystem layout

| Path | Contents |
|---|---|
| `~/.osmosis/logs/` | Session logs (every command + output) |
| `~/.osmosis/backups/` | Partition backups, Ed25519-signed manifests |
| `~/Osmosis-downloads/` | Downloaded ROMs, firmware, IPFS pinned content |
| `<repo>/profiles/*.yaml` | Device profiles |
| `<repo>/keys/` | Local trust roots |
| `<repo>/patches/`, `<repo>/roms/` | Bundled patch sets and ROM metadata |

Nothing OSmosis-specific is written outside `~/.osmosis/`,
`~/Osmosis-downloads/`, and the repo. No daemons, no system services
(except optional hardening scripts in [`scripts/setup-*.sh`](../../scripts/)
that the user runs explicitly).

### 4.7 Security posture

OSmosis is local-by-default. The Flask app binds to `localhost:5000` and
ships with no authentication because there's no untrusted caller — the
user owns the machine.

For self-hosted / always-on deployments (the Phase 11 use case), the
hardening scripts under [`scripts/`](../../scripts/) add nginx + TLS,
firewall rules, fail2ban, and unprivileged-user execution. The default
single-user mode is intentionally simple; the hardening is opt-in and
explicit.

### 4.8 Testing & quality gates

- [`tests/`](../../tests/) — pytest suites covering engine modules and
  route handlers. External tool calls are stubbed; we don't unit-test
  Heimdall.
- Real-device validation is part of the workflow for any change touching
  flash protocols (see Samsung notes in `project_samsung_*` memories).
  Unit tests cannot replace plugging in a Note II.
- [`scripts/code-quality-check.sh`](../../scripts/code-quality-check.sh)
  and [`scripts/check-file-length.sh`](../../scripts/check-file-length.sh)
  enforce baseline hygiene.

---

## 5. Adding a new device family — the canonical path

This is the test of the architecture. To add support for a new family:

1. **Profile** — drop `profiles/<vendor>-<codename>.yaml` describing the
   device's flash protocol, partitions, firmware list, and step sequence.
2. **Route** (only if existing routes don't fit) — add
   `web/routes/<family>.py` exposing the operations the wizard needs.
   Reuse `core.py` for subprocess execution, `safety.py` for pre-flight,
   `registry.py` for firmware verification.
3. **Plugin** (only if the protocol is too dynamic for YAML) — implement
   `DeviceDriver` in `web/plugins/<family>.py`.
4. **Wizard step** (only if existing steps don't fit) — add a Vue
   component under `frontend/src/components/wizard/` that branches off
   `StepCategory`.
5. **i18n strings** for any new UI copy.
6. **Recovery doc** in `docs/devices/`.
7. **Tests** for new engine logic.

If steps 2–4 are needed, that's a signal the family has a genuinely new
shape. If only step 1 is needed, the architecture is doing its job.

---

## 6. Non-goals

To keep the scope honest:

- **No cloud backend.** Ever. (Manifesto §8.)
- **No proprietary blob dependencies.** (Manifesto §7.) Wrapping a
  proprietary tool the vendor distributes is acceptable when there is no
  open alternative; bundling it is not.
- **No reimplementation of upstream flash tools.** OSmosis wraps Heimdall;
  it does not become Heimdall. If Heimdall has a bug, we file it
  upstream.
- **No telemetry.** OSmosis does not phone home. Session logs stay on
  disk.
- **No medical or financial advice surfaces** — these belong to LETHE's
  Bios/PreuJust modules and are scoped as informational only by design
  (Phase 9c regulatory constraints).

---

## 7. Where to read next

- [MANIFESTO.md](MANIFESTO.md) — the nine principles
- [ROADMAP.md](ROADMAP.md) — phased plan, current status
- [VISUAL-IDENTITY.md](VISUAL-IDENTITY.md) — colors, typography, voice
- [IPFS-ROADMAP.md](IPFS-ROADMAP.md) — distribution architecture detail
- [TERRARIUM-PROTOCOL-UX.md](TERRARIUM-PROTOCOL-UX.md) — community config
  channel UX
- [../devices/SUPPORTED.md](../devices/SUPPORTED.md) — full device catalog
- [../research/](../research/) — protocol notes, RE writeups
