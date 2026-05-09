# Changelog

All notable, user-visible changes to OSmosis. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project
adheres to [Semantic Versioning](https://semver.org/).

## [0.2.0] — 2026-05-09

The "Usability & Accessibility" release. Phase 10 of the roadmap closes
end-to-end: every wizard surface answers "What is happening? What do I
do next? Is it safe?" without requiring the user to read terminal
output. See [docs/project/ROADMAP.md](docs/project/ROADMAP.md#phase-10--usability--accessibility-done)
for the full per-item record.

### Added
- **Stage indicator** above the terminal log. Backend `Task.progress(step,
  total, label)` lines are now rendered as a compact stepper (filled-green
  dots for done stages, pulsing accent for the current stage, hollow for
  upcoming) with a "Step N of M — Label" caption — visible without
  expanding technical details.
- **Automatic retry with exponential backoff** for ROM downloads, IPFS
  fetches, and workflow asset fetches. `Task.run_shell_with_retry` does up
  to 3 attempts with 5 → 10 → 20-second waits, emits structured
  `__retry:n/max` markers, and breaks out of the inter-attempt sleep
  immediately when the user hits Abort. Every `wget` invocation gained
  `-c` so retries resume rather than restart at byte 0 — meaningful for
  1–2 GB ROM ZIPs.
- **"Give up" button** rendered inline with the retry banner during
  inter-attempt waits, no longer hidden behind the technical-details
  toggle.
- **`download_failed` typed error guide** with concrete recovery steps
  ("check internet, wait a few minutes, try a different mirror, watch for
  captive portals"). Emitted at every site that exhausts the retry helper.
- **Try-again buttons** added inline to error states on PageFlashRecovery,
  PageFlashStock, and PageApps so users no longer have to scroll back to
  the still-enabled main action button.
- **PWA manifest and service worker** ([web/static/manifest.json](web/static/manifest.json),
  [web/static/sw.js](web/static/sw.js)) registered from
  [frontend/src/main.js](frontend/src/main.js). Network-first for HTML,
  cache-first for fingerprinted Vite build assets, `/api/*` never cached.
- **`/api/device-info`** route alias onto the diagnostics handler so
  external integrations using the documented name work.

### Changed
- **`.info-box--error` styling** no longer cascades `color: var(--red)` —
  body text and child buttons inside an error box keep their normal
  colors. Variant is visually distinct from `--warn` via a 4px red
  left-accent and an injected `!` badge.
- **TerminalOutput** renders the typed error guide AND any regex-matched
  hints together (was `v-else-if`). When both are present, the regex
  hints are introduced as "More specifically:" so a generic guide can
  still surface a stderr-derived cause like "Disk full" or "Connection
  refused" alongside it.
- **Samsung Download Mode panel** in StepConnect leads with "This is a
  stuck state, not an active download" and names Samsung explicitly so
  the "is my phone downloading something?" misconception is addressed
  upfront. Manual exit sequence stays in `<details>` under "If automatic
  reboot doesn't work".
- **Hold-to-confirm flash button** in StepLoad now supports both Enter
  and Space for keyboard activation, and the press-handler guards
  against autorepeat re-entry so a held key cannot fire the destructive
  flash twice. `@blur` cancels mid-hold if focus leaves the button.
- **Termux companion** demoted from Phase 4.2 to future work — LETHE
  (now a sibling repo at `~/Lethe`) provides on-device Termux integration
  already.
- **LETHE split** out of the OSmosis tree (commit `8caf0cc`). OSmosis no
  longer carries LETHE-specific release docs, submodule references, or
  build scripts. LETHE lives at its own GitHub repo.

### Fixed
- **Hold-to-confirm autorepeat leak** — a single press of Enter that the
  OS turned into a key-repeat stream used to leak `setTimeout`
  references and could fire `executeConfirmed` more than once. Each
  affected timer would have started a flash. The handler now refuses
  re-entry while a hold is in progress.
- **`PIT` partition name mismatches** across Samsung Heimdall partition
  flags between device generations are now resolved per-device via the
  YAML profile (`heimdall_partitions` map), not hardcoded.
- **Stale-session false positives** in the Samsung restore flow — the
  IPFS-pinned firmware row is preferred when FUS lookups return noise.

### Accessibility
- **Terminal-error contrast** verified against WCAG AA across all four
  themes for the actual red text in the error guide and terminal log
  lines: dark 4.72:1 / 5.25:1, light 4.99:1 / 5.49:1, hi-contrast both
  ≥ 5.5:1. `.terminal-status--error` is border-only (WCAG 1.4.11 → 3:1,
  comfortably exceeded).
- **`aria-live` regions** on TerminalOutput status, retry banner, stage
  indicator, and TaskBar header. Per-task containers flip
  `aria-busy="true"` while running.
- **Keyboard navigation** for card selections (StepGoal, StepCategory)
  and for the hold-to-confirm flash button.
- **Visibly disabled buttons** combine reduced opacity with
  `filter: saturate(0.3)` so the disabled state is unambiguous across
  every theme.
- **Glossary tooltips** open on focus (Enter/Space-after-Tab works for
  free) with `aria-expanded` / `role="tooltip"`.

### Documentation
- **Roadmap reconciliation audit** at
  [docs/audits/ROADMAP-RECONCILE-2026-05.md](docs/audits/ROADMAP-RECONCILE-2026-05.md)
  — verified Phase 0–8 checkbox claims against the actual codebase, found
  3 gaps (PWA, `/api/device-info`, Termux companion), all closed in this
  release.
- **DESIGN architecture doc** at [docs/project/DESIGN.md](docs/project/DESIGN.md).

## [0.1.0] — 2026-04-01

Initial public reference point. Phases 0–8 substantively complete: flash
tool, wizard, ROM discovery, IPFS, backup/restore, CFW builder, scooter
BLE telemetry, OTA updates, device community, fastboot/router/console
support, plugin architecture, OS builder. See
[docs/project/ROADMAP.md](docs/project/ROADMAP.md) for the per-phase
record.
