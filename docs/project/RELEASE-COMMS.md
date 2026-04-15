# LETHE v1.0.0 Release Communications Playbook

**Target date: 2026-05-04**

This document is the checklist to run through on and after release day. Every
target list has its own conventions — verify the entry against the list's
current `CONTRIBUTING.md` before opening a PR (formats drift).

---

## Pre-release checklist (do before May 4)

- [ ] Fork each target repo below
- [ ] Prepare a local branch per repo with the entry staged
- [ ] Verify the repo's CONTRIBUTING.md hasn't changed format since drafting
- [ ] Confirm LETHE's GitHub repo is public and has: README, LICENSE, SECURITY.md
- [ ] Confirm release notes (RELEASE-LETHE-v1.0.0-DRAFT.md) are published as a GitHub Release
- [ ] Confirm screenshots or a demo GIF are attached to the release

## On release day

- [ ] Publish the GitHub Release
- [ ] Open PRs in the order below (highest reach first — lets momentum build)
- [ ] Tweet / Mastodon / Fediverse announcement
- [ ] Post to relevant subreddits (see "Social" section)

---

## Awesome-list submissions

### 1. awesome-selfhosted — highest-reach, strictest format

**Repo:** `https://github.com/awesome-selfhosted/awesome-selfhosted`

**Category:** *Personal Assistants* (or *Communication - Custom Communication Systems* — check current structure)

**Format rule (verify):** strict alphabetical within category; each line
requires a demo link, source link, language tag, and license badge via
shields.io.

**Draft entry:**

```markdown
- [LETHE](https://github.com/thdelmas/lethe) - Privacy-hardened
  Android OS where an embedded AI agent replaces the app-driven
  interface. Burner mode wipes on reboot; Tor-by-default networking;
  dead man's switch; multi-provider LLM routing (local, peer, cloud).
  Runs on 25+ devices including a decade-old Galaxy Note II.
  ([Source Code](https://github.com/thdelmas/lethe))
  `GPL-3.0` `Rust/Shell/JavaScript`
```

**Submission notes:**
- Maintainers are strict about the "self-hostable" criterion. LETHE qualifies because the OS itself runs on the user's hardware with no backend dependency.
- Add the shields.io license badge in the exact format the current README uses.

---

### 2. awesome-privacy — natural fit, clean process

**Repo:** `https://github.com/Lissy93/awesome-privacy`

**Category:** *Mobile Operating Systems* (alongside GrapheneOS, CalyxOS, /e/OS)

**Draft entry:**

```markdown
- **[LETHE](https://github.com/thdelmas/lethe)** - Privacy-hardened
  Android OS with an AI agent as the interface. Burner mode, Tor
  transparent proxy, dead man's switch, local-first LLM. Runs on
  25+ LineageOS-supported devices down to Android 7.1.
```

**Submission notes:**
- Positioning: *complementary to GrapheneOS, not competing.* GrapheneOS is a security-hardened Pixel distribution; LETHE is a privacy + agent-OS distribution for a wider device set.
- Include a comparison note in the PR description.

---

### 3. awesome-security — privacy + hardening angle

**Repo:** `https://github.com/sbilly/awesome-security`

**Category:** *Operating Systems* or *Privacy Online*

**Draft entry:**

```markdown
- [LETHE](https://github.com/thdelmas/lethe) - Privacy-hardened
  Android OS with burner mode, Tor-by-default, dead man's switch,
  and a local-first AI agent interface.
```

---

### 4. awesome-android — for OSmosis (not LETHE)

**Repo:** `https://github.com/JStumpp/awesome-android`

**What's submitted:** OSmosis (the flashing platform), not LETHE.
OSmosis's Android coverage (Samsung Heimdall, fastboot, ADB
sideload, TWRP) matches the list's scope.

**Draft entry:**

```markdown
- [OSmosis](https://github.com/thdelmas/OSmosis) - Universal device
  flashing and recovery platform. Samsung Heimdall, fastboot, ADB
  sideload, TWRP; also covers non-phone devices (scooters, ESP32,
  routers, SBCs).
```

---

### 5. awesome-linux-software — for OSmosis

**Repo:** `https://github.com/luong-komorebi/Awesome-Linux-Software`

**Category:** *System tools* or *Embedded*

**Draft entry:**

```markdown
- [OSmosis](https://github.com/thdelmas/OSmosis) - Multi-platform
  firmware flashing tool with a guided wizard. Phones, scooters,
  e-bikes, ESP32, routers, SBCs, game consoles.
```

---

### 6. awesome-selfhosted-ai — for LETHE

**Repo:** `https://github.com/awesome-selfhosted/awesome-selfhosted-ai`
(or the equivalent at time of submission — this list has been
shuffling between forks)

**Draft entry:**

```markdown
- [LETHE](https://github.com/thdelmas/lethe) - Self-hosted AI agent
  that runs as the entire OS, not an app. Local llama.cpp, peer
  inference via libp2p, optional cloud routing. Task-based router
  picks the right model per task (chat, vision, transcription).
```

---

### 7. awesome-open-source-security — defer to v1.0.1

Lower-reach, stricter review cycle. Submit after v1.0.0 is stable.

---

## Social announcements (release day)

**Mastodon / Fediverse** (primary — aligns with audience):

```
LETHE v1.0.0 is out.

It's an OS, not an app. The AI agent IS the interface. Burner mode
wipes on reboot. Tor by default. Runs on 25+ devices down to a
Galaxy Note II from 2012.

No Google. No telemetry. No cloud dependency unless you choose one.

https://github.com/thdelmas/lethe
```

**Subreddits** (pick 3–4, don't spam):

- `r/privacy` — privacy-first angle
- `r/linux` — alternative OS angle
- `r/selfhosted` — self-hosted AI angle
- `r/Android` — device/ROM angle (moderated; read rules first)
- `r/LineageOS` — downstream project etiquette; tag as derivative

**Hacker News:** single `Show HN: LETHE` post. Title should describe the
*what*, not the *why*:

```
Show HN: LETHE – Android OS where an AI agent replaces the app-driven interface
```

Do **not** cross-post HN and Reddit within the same hour — ranking penalties.

---

## Positioning notes (use consistently)

- **LETHE is not a GrapheneOS competitor.** GrapheneOS hardens security on
  Pixel hardware. LETHE is agent-as-OS on any LineageOS-supported device.
  Users pick based on their threat model and hardware.
- **LETHE is not Rabbit R1 / Humane Pin.** Those are dedicated hardware; LETHE
  runs on phones you already own or found in a drawer.
- **"The phone that forgets"** is the tagline. Use it.
- **Manifesto angle:** e-waste reduction. A decade-old phone becoming a
  useful AI device is the pitch that resonates with journalists.

## Anti-patterns

- Don't submit to >1 awesome-list in the same hour — maintainers notice and read it as astroturfing.
- Don't promise features not in v1.0.0. The "Local only" bootstrap download is a v1.1 feature; be explicit.
- Don't submit to lists where the criterion doesn't genuinely fit. Rejections hurt future submissions.
