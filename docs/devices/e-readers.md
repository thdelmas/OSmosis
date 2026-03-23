# E-Readers

OSmosis supports installing third-party reading software, custom launchers, and alternative firmware on a wide range of e-readers. Unlike phones and tablets, most e-reader modification does not require a traditional "flash" — it typically involves copying files over USB or accessing a root shell. This page documents every supported device family, the tools available, and current support status.

---

## Support Levels

| Level | Meaning |
|-------|---------|
| **Supported** | Full workflow available in the OSmosis wizard. Tested by the community. |
| **Research** | Modification is known to work, but OSmosis does not yet have a guided wizard for it. Manual steps required. |
| **Planned** | Device is recognized by OSmosis but tooling is not yet implemented. |
| **Not supported** | Listed for awareness only. No known open modification path. |

---

## Kobo

Kobo e-readers run Linux with Nickel as the UI shell. No exploit or jailbreak is needed — the device mounts as standard USB mass storage and accepts third-party software dropped directly onto the filesystem.

**Base OS:** Linux (Nickel UI)
**Modification method:** USB mass storage — copy files to the `.adds/` directory on the device root

| Device | Notes | Support |
|--------|-------|---------|
| Clara HD | | Planned |
| Clara 2E | | Planned |
| Clara BW | | Planned |
| Clara Colour | | Planned |
| Libra H2O | | Planned |
| Libra 2 | | Planned |
| Elipsa | | Planned |
| Elipsa 2E | | Planned |
| Sage | | Planned |
| Forma | | Planned |
| Aura | | Planned |
| Aura HD | | Planned |
| Aura H2O | | Planned |
| Nia | | Planned |

### Software & Tools

| Tool | Description | Notes |
|------|-------------|-------|
| **[KOReader](https://github.com/koreader/koreader)** | Feature-rich document reader | Supports EPUB, PDF, DJVU, CBZ, FB2, MOBI, and more. Installed to `.adds/koreader/` |
| **[KFMon](https://github.com/NiLuJe/kfmon)** | File-based launcher for Kobo | Watches for taps on specific books/icons in Nickel to launch KOReader and other tools |
| **[NickelMenu](https://github.com/pgaskin/NickelMenu)** | Adds custom entries to Nickel's built-in menus | Requires firmware 4.6 or later. **Not compatible with firmware 5.x.** |

### Key Details

- No jailbreak or exploit required on any Kobo device
- The `.adds/` directory on the device root is the conventional location for third-party software
- KFMon is the recommended launcher for KOReader; it integrates cleanly with the Nickel library UI
- NickelMenu is only available on firmware 4.6 and above and is not supported on the newer firmware 5.x branch
- Firmware version can be checked in the Kobo settings before proceeding

---

## reMarkable

reMarkable tablets run Linux (built with Yocto). Root SSH access is enabled by default — no exploit is needed. The SSH password is shown on-device under **Settings → Help → Copyright**.

**Base OS:** Linux (Yocto)
**Modification method:** Root SSH (enabled by default)

| Device | Notes | Support |
|--------|-------|---------|
| reMarkable 1 | Full Toltec support | Planned |
| reMarkable 2 | Requires rm2fb display shim | Planned |
| reMarkable Paper Pro | Different CPU; Toltec not yet supported. Vellum is an alternative. | Research |

### Software & Tools

| Tool | Description | Notes |
|------|-------------|-------|
| **[Toltec](https://toltec-dev.org/)** | Community package manager (opkg-based) | Provides KOReader, Remux, Oxide, and many other packages for rM1 and rM2 |
| **KOReader** | Document reader | Installable via Toltec |
| **Remux** | Window manager / app switcher | Enables running multiple apps side-by-side; installable via Toltec |
| **Oxide** | Alternative launcher | Full replacement for the stock reMarkable launcher; installable via Toltec |
| **rm2fb** | Display compatibility shim | Required for rM2 — the second-generation display uses a different framebuffer interface that rm2fb bridges for third-party software |
| **Vellum** | Alternative launcher for Paper Pro | Toltec does not support the Paper Pro's CPU; Vellum is the community alternative |

### Key Details

- Root SSH is on by default; no exploit or hardware modification is required
- Connect via USB, then `ssh root@10.11.99.1` — the password is shown in **Settings → Help → Copyright**
- The reMarkable 2 uses a different display framebuffer from rM1; any software that draws to the screen requires the rm2fb shim
- The Paper Pro uses a different CPU architecture, making it incompatible with the current Toltec package tree
- Official reMarkable software updates can overwrite installed packages; pin your firmware version before modifying

---

## PocketBook

PocketBook e-readers run Linux on Allwinner SoCs. PocketBook publishes an official SDK on GitHub. Third-party applications are installed by dropping them into the `/applications/` directory via USB — no exploit needed.

**Base OS:** Linux (Allwinner SoC)
**Modification method:** USB mass storage — copy apps to `/applications/`

| Device | Notes | Support |
|--------|-------|---------|
| Touch HD 3 | | Research |
| InkPad 3 | | Research |
| InkPad Color | | Research |
| Era | | Research |
| Era Color | | Research |
| Verse | | Research |
| Verse Pro | | Research |
| InkPad 4 | | Research |
| InkPad Color 3 | | Research |

### Software & Tools

| Tool | Description | Notes |
|------|-------------|-------|
| **[KOReader](https://github.com/koreader/koreader)** | Feature-rich document reader | PocketBook port available; install by dropping the application directory via USB |
| **CoolReader** | Lightweight e-book reader | Supports a wide range of formats; available for PocketBook |

### Key Details

- PocketBook publishes an official application SDK on GitHub, making app development and porting straightforward
- Applications are installed by copying them to the `/applications/` directory on the device over USB
- No jailbreak or exploit is required
- OSmosis support is currently Research status — the modification paths are known and documented, but no guided wizard exists yet

---

## Kindle

Kindle devices run a locked Linux-based OS. A jailbreak is required before any third-party software can be installed.

**Base OS:** Linux (locked)
**Modification method:** Jailbreak, then MRPI + KUAL launcher

| Device | Notes | Support |
|--------|-------|---------|
| Paperwhite 1 | kindle-legacy or kindle package | Research |
| Paperwhite 2 | kindlepw2 package | Research |
| Paperwhite 3 | kindlepw2 package | Research |
| Paperwhite 4 | kindlepw2 package | Research |
| Paperwhite 5 | kindlepw2 (fw ≤5.16.2.1.1) or kindlehf (fw ≥5.16.3) | Research |
| Oasis gen 2 | kindlepw2 or kindlehf depending on firmware | Research |
| Oasis gen 3 | kindlepw2 or kindlehf depending on firmware | Research |
| Scribe | kindlehf (fw ≥5.16.3) | Research |
| Colorsoft | kindlehf (fw ≥5.16.3) | Research |
| Basic gen 10 | kindle package | Research |
| Basic gen 11 | kindle package | Research |

### Jailbreaks

| Jailbreak | Firmware Range | Notes |
|-----------|---------------|-------|
| **WinterBreak** | All firmware versions, all models including 2024 releases | Released late 2024. Broadest compatibility. |
| **Nosebleed** | fw 5.16.4–5.18.6 | Released early 2026. More targeted; use WinterBreak if unsure. |

See [kindlemodding.org](https://kindlemodding.org/) for up-to-date jailbreak instructions and firmware compatibility tables.

### Post-Jailbreak Software & Tools

| Tool | Description | Notes |
|------|-------------|-------|
| **MRPI** (MobileRead Package Installer) | Package installer for Kindle | Required foundation for installing KOReader and other extensions |
| **KUAL** | Kindle Unified Application Launcher | App launcher UI; installed via MRPI |
| **[KOReader](https://github.com/koreader/koreader)** | Feature-rich document reader | Installed via KUAL; see package variant table below |

### KOReader Package Variants

KOReader ships separate packages for different Kindle generations due to firmware and hardware differences:

| Package | Target devices |
|---------|---------------|
| `kindle-legacy` | Kindle 2, 3, 4, 5 (K2–K5) |
| `kindle` | Kindle 4, Paperwhite 1 (K4–PW1) |
| `kindlepw2` | Paperwhite 2 and newer, firmware ≤5.16.2.1.1 |
| `kindlehf` | Paperwhite 2 and newer, firmware ≥5.16.3 |

### Key Details

- A jailbreak must be applied before any third-party software can run — there is no USB drop-in method like Kobo or PocketBook
- After jailbreaking, MRPI is installed first, then KUAL, then KOReader through KUAL
- Always check [kindlemodding.org](https://kindlemodding.org/) for the current recommended jailbreak before updating firmware
- Firmware updates from Amazon will remove the jailbreak; disable OTA updates after jailbreaking

---

## Onyx Boox

Onyx Boox e-readers run Android 10–12 with E Ink displays. APK sideloading is enabled out of the box — no exploit is needed for basic app installation.

**Base OS:** Android 10–12
**Modification method:** APK sideload (no exploit needed); optional Magisk root or Xposed modules

| Device | Android Version | Notes | Support |
|--------|----------------|-------|---------|
| Note Air | Android 10 | | Research |
| Note Air 2 | Android 11 | | Research |
| Note Air 3 | Android 12 | OnyxTweaks supported | Research |
| Nova Air | Android 11 | | Research |
| Nova Air C | Android 11 | Color E Ink display | Research |
| Poke 3 | Android 10 | | Research |
| Poke 4 | Android 11 | | Research |
| Poke 5 | Android 11 | | Research |
| Tab Ultra | Android 11 | | Research |
| Tab Ultra C | Android 12 | OnyxTweaks supported | Research |
| Go 10.3 | Android 12 | OnyxTweaks supported | Research |
| Go Color 7 | Android 12 | Color E Ink display; OnyxTweaks supported | Research |
| Palma | Android 11 | Pocket-sized form factor | Research |

### Software & Tools

| Tool | Description | Notes |
|------|-------------|-------|
| **F-Droid** | Open-source Android app repository | Sideload the F-Droid APK; no exploit needed |
| **[KOReader](https://github.com/koreader/koreader)** | Feature-rich document reader | Available via F-Droid or direct APK sideload |
| **Magisk** | Root management | Via boot.img patching. Bootloader is unlockable but **unlocking wipes all data.** |
| **[OnyxTweaks](https://github.com/Szybet/OnyxTweaks)** | Xposed/LSPosed module for Android 12 Boox devices | Tweaks system behavior and UI on Android 12 models; requires Magisk + LSPosed |

### Key Details

- APK sideloading is enabled by default — no developer mode toggle or exploit required
- Any Android APK compatible with Android 10–12 can be installed directly
- Root via Magisk requires patching the device's `boot.img` and re-flashing it; this is the standard Android Magisk installation flow
- Bootloader unlock is supported but **permanently wipes user data** — back up before proceeding
- OnyxTweaks requires Magisk root and LSPosed, and targets Android 12 Boox models specifically
- Google Play Services can be sideloaded but are not officially supported by Onyx

---

## Common Tools

| Tool | URL | Description |
|------|-----|-------------|
| KOReader | [github.com/koreader/koreader](https://github.com/koreader/koreader) | Cross-platform document reader; runs on Kobo, Kindle, PocketBook, reMarkable, and Boox |
| NickelMenu | [github.com/pgaskin/NickelMenu](https://github.com/pgaskin/NickelMenu) | Custom menu entries for Kobo's Nickel UI (fw 4.6+, not fw 5.x) |
| Toltec | [toltec-dev.org](https://toltec-dev.org/) | Community opkg package manager for reMarkable 1 and 2 |
| kindlemodding.org | [kindlemodding.org](https://kindlemodding.org/) | Authoritative Kindle jailbreak documentation and firmware compatibility tables |
| OnyxTweaks | [github.com/Szybet/OnyxTweaks](https://github.com/Szybet/OnyxTweaks) | Xposed/LSPosed module for Android 12 Onyx Boox devices |
