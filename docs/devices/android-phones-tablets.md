# Android Phones & Tablets

OSmosis supports flashing custom ROMs, recoveries, and firmware on a wide range of Android devices. This page covers every supported Android device, its compatible operating systems, flash method, and current support status.

---

## Samsung Galaxy Tab S (Exynos 5420)

The original Galaxy Tab S family uses Samsung's Exynos 5420 SoC. These tablets are flashed via Odin/Heimdall into download mode, with TWRP custom recovery for ROM installation.

| Device | Model | Codename | Flash Method | Support |
|--------|-------|----------|-------------|---------|
| Galaxy Tab S 10.5 LTE | SM-T805 | `chagalllte` | Odin/Heimdall + TWRP | Supported |
| Galaxy Tab S 10.5 WiFi | SM-T800 | `chagallwifi` | Odin/Heimdall + TWRP | Supported |
| Galaxy Tab S 8.4 LTE | SM-T705 | `klimtlte` | Odin/Heimdall + TWRP | Supported |
| Galaxy Tab S 8.4 WiFi | SM-T700 | `klimtwifi` | Odin/Heimdall + TWRP | Supported |

### OS Compatibility

| OS | Android Version | Base | Status | Notes |
|----|----------------|------|--------|-------|
| **LineageOS 18.1** | 11 | AOSP | Unofficial builds available | Built by Exynos 5420 community on SourceForge |
| **/e/OS R** | 11 | LineageOS 18.1 | Unofficial builds available | De-Googled, privacy-focused. Built by ronnz98 |
| **Stock Samsung** | 6.0.1 (Marshmallow) | TouchWiz | Last official update | Available via SamFw |

### Recovery

| Recovery | Version | Notes |
|----------|---------|-------|
| **TWRP** | 3.6.2_9-0 | Required for ROM installation. Available for all four variants. |

### GApps

LineageOS builds do not include Google apps. If needed, flash **MindTheGapps** (ARM, Android 11) after the ROM. /e/OS includes its own app ecosystem (App Lounge) and does not need GApps.

### Key Details

- **SoC:** Exynos 5420 (quad-core Cortex-A15 + quad-core Cortex-A7)
- **Download mode:** Hold Volume Down + Home + Power while the device is off
- **Known issues:** GD32 chip variants in some replacement parts are not flashable
- **OSmosis wizard:** Full guided flow for LineageOS and /e/OS installation

---

## Samsung Galaxy Note II (Exynos 4412)

The Galaxy Note II is an older Samsung phone with an Exynos 4412 SoC and a removable battery. It is flashed via Heimdall into Download Mode. Replicant (a fully free/open Android distribution) has been successfully installed and verified on this device using Replicant's own custom recovery.

| Device | Model | Codename | Flash Method | Support |
|--------|-------|----------|-------------|---------|
| Galaxy Note II | GT-N7100 | `t03g` | Odin/Heimdall + Replicant Recovery | Verified |

### OS Compatibility

| OS | Android Version | Base | Status | Notes |
|----|----------------|------|--------|-------|
| **Replicant 6.0** | 6.0 | AOSP (fully free) | Verified | Fully free/open Android. Requires Replicant's own recovery. |
| **LineageOS 14.1** | 7.1 | AOSP | Community builds | Unofficial community builds |
| **Stock Samsung** | 4.3 (Jelly Bean) | TouchWiz | Last official update | Available via SamFw |

### Recovery

| Recovery | Version | Notes |
|----------|---------|-------|
| **Replicant Recovery** | 6.0 | Required for Replicant ROM installation. Do not use TWRP — Replicant ZIPs require Replicant's own recovery. |

### Key Details

- **SoC:** Exynos 4412 (quad-core Cortex-A9)
- **Download Mode:** Hold Volume Down + Home + Power while the device is off
- **Recovery Mode:** Hold Volume Up + Home + Power while the device is off
- **Removable battery:** Yes — battery pull is the most reliable way to force a restart
- **Heimdall sessions go stale** after one command — plan operations carefully
- **Verified install:** Replicant 6.0 + Replicant custom recovery on GT-N7100 (2026-03-24)
- See [Samsung Galaxy Note II device page](samsung-galaxy-note-2.md) for detailed troubleshooting

---

## Google Pixel (Fastboot)

Google Pixel devices use the standard Android fastboot protocol. They have unlockable bootloaders and are the primary targets for privacy-focused ROMs like GrapheneOS and CalyxOS.

| Device | Codename | Flash Method | Support |
|--------|----------|-------------|---------|
| Pixel 6 | `oriole` | Fastboot | Supported |
| Pixel 6a | `bluejay` | Fastboot | Supported |
| Pixel 7 | `panther` | Fastboot | Supported |
| Pixel 7a | `lynx` | Fastboot | Supported |
| Pixel 8 | `shiba` | Fastboot | Supported |
| Pixel 8a | `akita` | Fastboot | Supported |
| Pixel 9 | `tokay` | Fastboot | Supported |
| Pixel 9 Pro | `caiman` | Fastboot | Supported |

### OS Compatibility

| OS | Description | Notes |
|----|-------------|-------|
| **GrapheneOS** | Hardened Android with strong privacy/security | Recommended for Pixel devices. Official support for Pixel 6+ |
| **CalyxOS** | Privacy-focused Android with microG option | Includes F-Droid and Aurora Store by default |
| **Stock Android** | Google's factory images | Available from Google's developer site |

### Key Details

- **Bootloader unlock:** `Settings > Developer options > OEM unlocking`, then `fastboot flashing unlock`
- **Fastboot mode:** Hold Volume Down + Power while device is off
- **Re-lock:** Both GrapheneOS and CalyxOS support re-locking the bootloader after installation
- **Verified boot:** GrapheneOS maintains full verified boot with its own signing keys

---

## Samsung Galaxy S Series (Exynos/Snapdragon)

Samsung's flagship S series phones. Flash method depends on region — Exynos variants use Odin/Heimdall, Snapdragon variants may require additional steps. LineageOS provides official builds for these devices.

| Device | Model | Codename | Flash Method | Support |
|--------|-------|----------|-------------|---------|
| Galaxy S20 | SM-G981B | `x1s` | Odin/Heimdall | Supported |
| Galaxy S21 | SM-G991B | `o1s` | Odin/Heimdall | Supported |
| Galaxy S22 | SM-S901B | `r0s` | Odin/Heimdall | Supported |
| Galaxy S23 | SM-S911B | `dm1q` | Odin/Heimdall | Supported |
| Galaxy S24 | SM-S921B | `e1s` | Odin/Heimdall | Supported |

### OS Compatibility

| OS | Description | Notes |
|----|-------------|-------|
| **LineageOS** | Official builds | Available from LineageOS downloads |
| **Stock Samsung (One UI)** | Samsung's Android skin | Available via SamFw |

### Key Details

- **SoC:** Exynos (international) or Snapdragon (US/Korea) depending on model year and region
- **Model numbers listed are Exynos (B suffix).** Snapdragon variants have different model numbers.
- **Knox:** Flashing custom firmware trips the Knox counter permanently. This disables Samsung Pay and voids warranty.
- **Download mode:** Hold Volume Up + Volume Down while connecting USB cable

---

## Samsung Galaxy A Series (Mid-range)

Samsung's A series is the world's best-selling Android phone line. LineageOS provides official builds for several models.

| Device | Model | Codename | Flash Method | Support |
|--------|-------|----------|-------------|---------|
| Galaxy A51 | SM-A515F | `a51` | Odin/Heimdall | Supported |
| Galaxy A52 | SM-A525F | `a52q` | Odin/Heimdall | Supported |
| Galaxy A53 5G | SM-A536B | `a53x` | Odin/Heimdall | Supported |
| Galaxy A54 5G | SM-A546B | `a54x` | Odin/Heimdall | Supported |

### OS Compatibility

| OS | Description | Notes |
|----|-------------|-------|
| **LineageOS** | Official builds | Available from LineageOS downloads |
| **Stock Samsung (One UI)** | Samsung's Android skin | Available via SamFw |

### Key Details

- **Popular globally:** These devices are extremely common, especially in Europe, Asia, and Africa
- **Knox counter:** Same as S series — tripped permanently on custom flash
- **Bootloader unlock:** May require a waiting period after enabling OEM unlock

---

## Samsung Galaxy Tab A Series (Budget Tablets)

Samsung's budget tablet line. These devices have limited custom ROM support — OSmosis lists them primarily for stock firmware management.

| Device | Model | Codename | Flash Method | Support |
|--------|-------|----------|-------------|---------|
| Galaxy Tab A 10.1 (2019) WiFi | SM-T510 | `gta4lwifi` | Odin/Heimdall | Planned |
| Galaxy Tab A 10.1 (2019) LTE | SM-T515 | `gta4llte` | Odin/Heimdall | Planned |
| Galaxy Tab A 8.0 (2019) | SM-T290 | `gta2swifi` | Odin/Heimdall | Planned |
| Galaxy Tab A9 | SM-X200 | `gta9wifi` | Odin/Heimdall | Planned |

### OS Compatibility

| OS | Description | Notes |
|----|-------------|-------|
| **Stock Samsung** | Samsung's Android | Available via SamFw. Only option for most Tab A models. |

### Key Details

- **Limited ROM support:** No official LineageOS builds. Check XDA for device-specific unofficial ROMs.
- **Use case:** Stock firmware reinstallation and recovery

---

## OnePlus (Fastboot)

OnePlus devices are developer-friendly with easily unlockable bootloaders and strong LineageOS support.

| Device | Codename | Flash Method | Support |
|--------|----------|-------------|---------|
| OnePlus 6T | `fajita` | Fastboot | Supported |
| OnePlus 7 Pro | `guacamole` | Fastboot | Supported |
| OnePlus 8T | `kebab` | Fastboot | Supported |
| OnePlus 9 | `lemonade` | Fastboot | Supported |
| OnePlus Nord | `avicii` | Fastboot | Supported |
| OnePlus Nord 2 | `denniz` | Fastboot | Planned |

### OS Compatibility

| OS | Description | Notes |
|----|-------------|-------|
| **LineageOS** | Official builds (6T, 7 Pro, 8T, 9, Nord) | Nord 2 not yet available |
| **OxygenOS** | OnePlus stock firmware | Available from OnePlus |
| **Paranoid Android** | Popular alternative ROM | Community builds for select models |

### Key Details

- **Bootloader unlock:** `Settings > Developer options > OEM unlocking`, then `fastboot oem unlock`
- **No waiting period:** Unlike Samsung, OnePlus unlocks immediately
- **Fastboot mode:** Hold Volume Up + Power while device is off
- **MSM tool:** OnePlus provides an emergency unbrick tool for some models

---

## Xiaomi / Poco / Redmi (Fastboot)

Xiaomi ecosystem devices have a massive ROM community. Bootloader unlock requires requesting permission through Xiaomi's official tool and waiting a mandatory period.

| Device | Codename | Flash Method | Support |
|--------|----------|-------------|---------|
| Poco F1 | `beryllium` | Fastboot | Supported |
| Poco X3 Pro | `vayu` | Fastboot | Supported |
| Redmi Note 11 | `spes` | Fastboot | Supported |
| Redmi Note 12 Pro | `ruby` | Fastboot | Planned |
| Redmi Note 13 Pro | `garnet` | Fastboot | Planned |

### OS Compatibility

| OS | Description | Notes |
|----|-------------|-------|
| **LineageOS** | Official builds (Poco F1, X3 Pro, Note 11) | Huge community support |
| **MIUI / HyperOS** | Xiaomi stock firmware | Available from Xiaomi Firmware Updater |
| **Pixel Experience** | Pixel-like ROM | Popular choice for Xiaomi devices |
| **ArrowOS** | Lightweight AOSP-based | Community builds available |

### Key Details

- **Bootloader unlock process:** 1) Create Mi account, 2) Enable OEM unlock, 3) Use Mi Unlock Tool (Windows), 4) Wait 7-30 days, 5) Unlock
- **Anti-rollback:** Some models enforce anti-rollback protection. Flashing an older firmware can permanently brick the device. Always check before flashing.
- **Fastboot mode:** Hold Volume Down + Power while device is off
- **EDL mode:** Emergency Download mode (Qualcomm) available as a last resort for bricked devices, but requires authorized access

---

## Motorola (Fastboot)

Motorola devices use standard fastboot. Bootloader unlocking is available through Motorola's official process.

| Device | Codename | Flash Method | Support |
|--------|----------|-------------|---------|
| Moto G54 | `cancunf` | Fastboot | Planned |
| Moto G84 | `bangkk` | Fastboot | Planned |
| Moto G Power (2024) | `tesla24` | Fastboot | Planned |
| Moto Edge 40 | `lyriq` | Fastboot | Planned |

### OS Compatibility

| OS | Description | Notes |
|----|-------------|-------|
| **Stock Motorola** | Near-stock Android | Available from Lolinet firmware mirrors |
| **LineageOS** | Community builds for some models | Check LineageOS wiki for availability |

### Key Details

- **Bootloader unlock:** Request unlock code from Motorola's developer site using device IMEI
- **Rescue and Smart Assistant (RSA):** Motorola's official recovery/unbrick tool
- **Near-stock Android:** Motorola's firmware is close to AOSP with minimal customization

---

## Sony Xperia (Fastboot / Open Devices)

Sony runs an official Open Devices program, providing AOSP build guides and kernel sources. This makes Xperia devices some of the most developer-friendly on the market.

| Device | Codename | Flash Method | Support |
|--------|----------|-------------|---------|
| Xperia 1 III | `pdx215` | Fastboot | Supported |
| Xperia 5 III | `pdx214` | Fastboot | Supported |
| Xperia 10 IV | `pdx225` | Fastboot | Supported |

### OS Compatibility

| OS | Description | Notes |
|----|-------------|-------|
| **LineageOS** | Official builds | Available from LineageOS downloads |
| **Stock Sony** | Sony's Android | Available from Sony Open Devices |
| **AOSP** | Pure Android via Sony's build guides | Sony provides official AOSP build instructions |

### Key Details

- **Open Devices program:** Sony publishes kernel source, device trees, and AOSP build instructions
- **Bootloader unlock:** Through Sony's developer site. **Warning:** Unlocking disables DRM keys, which degrades camera quality (post-processing relies on DRM-protected algorithms)
- **Fastboot mode:** Hold Volume Up while connecting USB cable

---

## Fairphone (Ethical, Unlock-Friendly)

Fairphone is designed for longevity and repairability. Both models have easily unlockable bootloaders and official /e/OS and LineageOS support.

| Device | Codename | Flash Method | Support |
|--------|----------|-------------|---------|
| Fairphone 4 | `FP4` | Fastboot | Supported |
| Fairphone 5 | `FP5` | Fastboot | Supported |

### OS Compatibility

| OS | Description | Notes |
|----|-------------|-------|
| **LineageOS** | Official builds | Strong community support |
| **/e/OS** | De-Googled Android | Official /e/ Foundation builds |
| **Fairphone OS** | Stock Android | Available from Fairphone support |
| **CalyxOS** | Privacy-focused | Community builds available |
| **iodéOS** | Privacy-focused, de-bloated | Official support for Fairphone |

### Key Details

- **Modular design:** User-replaceable battery, screen, camera modules, speaker, USB-C port
- **Bootloader unlock:** Supported and documented by Fairphone — no voided warranty
- **Long software support:** Fairphone commits to 5+ years of updates
- **Ethical sourcing:** Fair-trade materials and responsible supply chain

---

## Nothing Phone

Nothing phones run NothingOS (near-stock Android with the Glyph interface). LineageOS provides official builds.

| Device | Codename | Flash Method | Support |
|--------|----------|-------------|---------|
| Nothing Phone (1) | `spacewar` | Fastboot | Supported |
| Nothing Phone (2) | `pong` | Fastboot | Supported |

### OS Compatibility

| OS | Description | Notes |
|----|-------------|-------|
| **LineageOS** | Official builds | Available from LineageOS downloads |
| **NothingOS** | Nothing's stock Android | Near-stock with Glyph customization |

### Key Details

- **Bootloader unlock:** Standard fastboot unlock process
- **Glyph interface:** LED light array on the back — only functional on NothingOS
- **Fastboot mode:** Hold Volume Down + Power while device is off
