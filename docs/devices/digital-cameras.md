# Digital Cameras

OSmosis documents third-party firmware, patches, and tools for digital cameras. Unlike phones or microcontrollers, camera firmware modification spans a wide range of approaches — from SD-card-resident overlays that leave stock firmware untouched, to binary patches applied directly to internal flash, to official experimental firmware from manufacturers.

**Important:** Camera firmware modification can brick hardware, void warranties, and in the case of drone firmware, may have legal implications in your jurisdiction. Read the per-family notes carefully before proceeding.

---

## Support Levels

This page uses the standard OSmosis support levels plus one additional level specific to camera and drone research:

| Level | Meaning |
|-------|---------|
| **Supported** | Full flashing workflow available in the wizard. Tested by the community. |
| **Experimental** | Works but has limited testing. May require manual steps. |
| **Research** | Tools exist and are documented by the community, but OSmosis does not yet provide a guided wizard. Use the linked external tools directly. |
| **Not supported** | Listed for awareness. No open firmware or tooling available. |

All families on this page are currently **Research** status.

---

## Flash Methods

| Method | Description | Used by |
|--------|-------------|---------|
| **SD/CF card load** | Firmware overlay copied to storage card; loaded at boot without touching internal flash | Magic Lantern (Canon DSLRs), CHDK (Canon P&S) |
| **SD card install** | Per-model port installed to SD card; camera's own update mechanism invoked | CHDK |
| **App sideload** | Signed or unsigned APK pushed to Android-based camera over USB | OpenMemories (Sony PMCA) |
| **Binary patch** | Internal firmware downloaded, patched in place, and re-flashed | Nikon-Patch |
| **Official OTA** | Manufacturer-distributed experimental build flashed through normal update path | GoPro Labs |
| **DFU / USB bulk** | Firmware archive flashed over USB using vendor protocol | DUMLdore (DJI) |

---

## Canon DSLRs — Magic Lantern

[Magic Lantern](https://magiclantern.fm/) is an open-source firmware add-on that runs entirely from the SD or CF card. The camera's internal firmware is never modified; Magic Lantern is loaded by the bootloader at startup and runs alongside stock firmware in RAM. This makes it among the safest camera modifications available.

### Processor Generation Support

| DIGIC Generation | Magic Lantern Status | Notes |
|-----------------|---------------------|-------|
| DIGIC 4 | Stable | Long-established, well-tested builds |
| DIGIC 5 | Stable | Includes 5D Mark III, 6D |
| DIGIC 6 | Nightly (2025) | Active development; no stable release |
| DIGIC 7 | Nightly (2025) | Active development; no stable release |
| DIGIC 8+ | Not supported | Signed bootloader; no known bypass |

### Supported Devices

| Device | DIGIC | Flash Method | Status | Notes |
|--------|-------|-------------|--------|-------|
| 5D Mark II | DIGIC 4 | SD card load | Research | Stable build available |
| 5D Mark III | DIGIC 5 | CF/SD card load | Research | Stable build available |
| 6D | DIGIC 5 | SD card load | Research | Stable build available |
| 6D Mark II | DIGIC 7 | SD card load | Research | Nightly only |
| 7D | DIGIC 4+4 | CF card load | Research | Stable build available |
| 7D Mark II | DIGIC 6+6 | CF card load | Research | Nightly only |
| 50D | DIGIC 4 | CF card load | Research | Stable build available |
| 60D | DIGIC 4 | SD card load | Research | Stable build available |
| 70D | DIGIC 5+ | SD card load | Research | Stable build available |
| 100D | DIGIC 5 | SD card load | Research | Stable build available |
| 200D | DIGIC 7 | SD card load | Research | Nightly only |
| 650D | DIGIC 5 | SD card load | Research | Stable build available |
| 700D | DIGIC 5 | SD card load | Research | Stable build available |
| 750D | DIGIC 6 | SD card load | Research | Nightly only |
| 1100D | DIGIC 4 | SD card load | Research | Stable build available |

### Key Features

- **RAW video:** Continuous lossless RAW recording beyond Canon's built-in limits on supported bodies
- **Focus peaking and zebras:** Live view overlays for manual focus and exposure
- **Intervalometer and HDR:** Built-in scripting for time-lapse and exposure bracketing
- **Dual ISO:** Alternates sensor readout between two ISOs per frame for extended dynamic range
- **LUA scripting:** Extensible scripting engine for custom automation

### Key Details

- **Install:** Copy the Magic Lantern zip to the root of a FAT32-formatted SD/CF card. Run the Canon firmware update utility once to enable the ML bootflag. Subsequent boots load ML automatically.
- **No internal flash changes:** Because ML lives on the card, removing the card fully removes ML.
- **Per-camera builds:** Each Canon body has its own build tied to a specific stock firmware version. Verify your camera's firmware version before downloading.
- **DIGIC 6/7 nightly warning:** Nightly builds may have incomplete features and occasional instability. Back up important shoots before using nightly builds in the field.

---

## Canon Point-and-Shoots — CHDK

[CHDK (Canon Hack Development Kit)](https://chdk.fandom.com/wiki/CHDK) is an SD-card-resident firmware add-on for Canon PowerShot cameras. Like Magic Lantern, it does not modify internal flash. CHDK provides a port per camera model and per firmware version; coverage spans the DIGIC II through DIGIC 4 era.

### Processor Generation Coverage

| DIGIC Generation | CHDK Coverage |
|-----------------|--------------|
| DIGIC II | Good coverage |
| DIGIC III | Good coverage |
| DIGIC 4 | Good coverage |
| DIGIC 5+ | Sparse; few ports available |
| DIGIC 6+ | No support |

### Supported Device Families

| Family | Representative Models | Flash Method | Status | Notes |
|--------|-----------------------|-------------|--------|-------|
| PowerShot A series | A480, A490, A495, A1200, A2200, A2300, A2400, A3300, A3400, A4000 | SD card install | Research | Largest CHDK family; most models covered |
| PowerShot S series | S90, S95, S100, S110, S120 | SD card install | Research | Advanced compact; RAW and scripting popular |
| PowerShot G series | G10, G11, G12, G15, G16 | SD card install | Research | Prosumer compacts; strong community support |
| PowerShot SX series | SX130, SX150, SX160, SX230, SX240, SX260, SX280 | SD card install | Research | Bridge cameras; superzoom bodies |
| IXUS / ELPH series | IXUS 115, IXUS 130, IXUS 220, IXUS 240, ELPH 300, ELPH 310 | SD card install | Research | Entry-level; fewer ports than A/S/G |

### Key Features

- **RAW (DNG) capture:** Saves uncompressed sensor data alongside JPEG on supported models
- **Intervalometer:** Built-in time-lapse control without an external remote
- **Motion detection:** Trigger capture on pixel-change in a defined zone
- **USB remote control:** Trigger shutter via USB from a script or computer
- **UBASIC / LUA scripting:** Full scripting language for automated shooting sequences

### Key Details

- **Per-firmware versioning:** Each CHDK port is tied to a specific Canon firmware version string. Use the [CHDK Firmware Check](https://chdk.fandom.com/wiki/Firmware_Version) guide to confirm your camera's version before downloading.
- **Bootable SD card:** CHDK can be set to auto-boot from a specially prepared SD card using the `card tricks` method or the CHDK installer.
- **STICK tool:** The [STICK (Simple Tool for Installing CHDK)](https://www.eckler.ca/tools/stick/) automates card preparation on Windows/Mac/Linux.
- **Model lookup:** Use the [CHDK supported cameras list](https://chdk.fandom.com/wiki/CHDK_supported_Canon_cameras) to confirm whether a specific model/firmware combination has a port.

---

## Sony — OpenMemories

[OpenMemories](https://github.com/ma1co/OpenMemories-Tweak) targets Sony cameras built on the PMCA platform — an Android-derived application framework Sony used in the NEX / Alpha / RX lines from approximately 2012 to 2016. These cameras run a locked Android environment and include a vestigial "PlayMemories Camera Apps" store. OpenMemories exploits this to sideload unsigned apps and unlock hidden settings.

**This is not firmware replacement.** Stock Sony firmware is not modified. OpenMemories installs a settings-unlock app and enables sideloading additional tools.

### Tools

| Tool | Repository | Purpose |
|------|-----------|---------|
| **Sony-PMCA-RE** | [github.com/ma1co/Sony-PMCA-RE](https://github.com/ma1co/Sony-PMCA-RE) | PMCA platform research and app installer |
| **pmca-console** | Included in Sony-PMCA-RE | CLI for app install, settings dump, and device info |
| **OpenMemories-Tweak** | [github.com/ma1co/OpenMemories-Tweak](https://github.com/ma1co/OpenMemories-Tweak) | Settings unlock app (PAL region removal, video bitrate, etc.) |

### Supported Devices

| Device | Sensor | Flash Method | Status | Notes |
|--------|--------|-------------|--------|-------|
| NEX-5R | APS-C | App sideload | Research | Early PMCA camera; well-tested |
| NEX-6 | APS-C | App sideload | Research | Built-in EVF variant of NEX-5R |
| NEX-5T | APS-C | App sideload | Research | Last NEX-5 series body |
| A7 (Gen 1) | Full-frame | App sideload | Research | First full-frame E-mount |
| A7R (Gen 1) | Full-frame | App sideload | Research | 36 MP variant |
| A7S (Gen 1) | Full-frame | App sideload | Research | High-ISO / video-oriented |
| A7 Mark II | Full-frame | App sideload | Research | IBIS added |
| A7R Mark II | Full-frame | App sideload | Research | BSI sensor; check PMCA compatibility |
| A6000 | APS-C | App sideload | Research | High-speed AF; popular target |
| A5000 | APS-C | App sideload | Research | Entry-level; PMCA present |
| A5100 | APS-C | App sideload | Research | Touchscreen variant |
| RX100 III | 1" | App sideload | Research | Compact; PMCA confirmed |
| RX100 IV | 1" | App sideload | Research | Stacked sensor; PMCA confirmed |

### Key Details

- **Connection:** Connect the camera via USB in MTP/Mass Storage mode. `pmca-console` communicates over the PlayMemories USB channel.
- **What unlocks are available:** Depending on model — PAL region recording limit removal (29-min cap), clean HDMI output, video bitrate increase, extra picture profiles.
- **Firmware is untouched:** OpenMemories cannot unbrick a camera or change core sensor behavior. It modifies runtime settings exposed by the Android layer.
- **Post-PMCA bodies not supported:** A7 III / A7R III / A9 and newer use a different platform (XDNC/Linux-based) that OpenMemories does not target.

---

## Nikon — Nikon-Patch

[Nikon-Patch](https://nikonhacker.com/wiki/Nikon_Patch) is a binary patching tool that downloads a camera's internal firmware, applies targeted patches, and re-flashes it. Unlike Magic Lantern and CHDK, this **does modify internal flash** and carries a higher risk of bricking.

### Processor Generation Support

| EXPEED Generation | Support |
|------------------|---------|
| EXPEED 2 | Supported by Nikon-Patch |
| EXPEED 3 | Supported by Nikon-Patch |
| EXPEED 4 | Not cracked; no patch tool available |
| EXPEED 5+ | Not supported |

### Supported Devices

| Device | EXPEED | Flash Method | Status | Notes |
|--------|--------|-------------|--------|-------|
| D3100 | EXPEED 2 | Binary patch | Research | Entry-level; video bitrate unlock available |
| D3200 | EXPEED 3 | Binary patch | Research | 24 MP; video bitrate unlock |
| D5100 | EXPEED 2 | Binary patch | Research | Articulating screen; popular target |
| D5200 | EXPEED 3 | Binary patch | Research | 24 MP; video and NEF patches |
| D7000 | EXPEED 2 | Binary patch | Research | Dual card slots; well-documented |
| D7100 | EXPEED 3 | Binary patch | Research | 24 MP; most complete patch set |
| D600 | EXPEED 3 | Binary patch | Research | Full-frame entry; also covers D610 |
| D610 | EXPEED 3 | Binary patch | Research | D600 revision |
| D800 | EXPEED 3 | Binary patch | Research | 36 MP; NEF compression removal patch |
| D800E | EXPEED 3 | Binary patch | Research | AA-filterless variant of D800 |
| D4 | EXPEED 3 | Binary patch | Research | Pro body; video bitrate and timecode patches |

### Available Patches

| Patch | Description | Applies to |
|-------|-------------|-----------|
| Video bitrate unlock | Increases H.264 bitrate beyond stock ceiling | Most EXPEED 2/3 bodies |
| NEF (RAW) lossless compression removal | Removes lossy compression from 14-bit RAW files | D800/D800E, D600/D610, D4 |
| 1080p 60fps unlock | Enables higher frame rates on bodies limited by firmware | Select bodies (D7100) |
| Clean HDMI | Disables on-screen overlays on HDMI output for external recording | Select bodies |

### Key Details

- **Higher risk than overlay loaders:** Because internal flash is patched, a failed flash or power loss during flashing can produce a non-bootable camera. Use a fully charged battery and do not interrupt the process.
- **Nikon Hacker wiki:** The [NikonHacker wiki](https://nikonhacker.com/wiki/) documents all patches, their status, and per-camera instructions. Consult it before applying any patch.
- **Reversible:** Re-flashing stock firmware via Nikon's official update tool restores the camera to factory state, provided it boots. Keep the official firmware zip on hand.
- **EXPEED 4+ wall:** Nikon introduced stronger firmware signing with EXPEED 4. No patches exist for D3300, D5300, D750, D810, or any newer body.

---

## GoPro — GoPro Labs

[GoPro Labs](https://community.gopro.com/s/article/GoPro-Labs) is an official experimental firmware program distributed by GoPro. It extends camera functionality with QR-code-driven scripting and hidden settings not available in stock firmware. Unlike the other families on this page, GoPro Labs firmware is signed and distributed by GoPro itself — there is no true third-party open firmware for GoPro cameras.

### Supported Devices

| Device | Flash Method | Status | Notes |
|--------|-------------|--------|-------|
| HERO4 Silver / Black | Official OTA | Research | Earliest supported Labs device |
| HERO5 Black / Session | Official OTA | Research | |
| HERO6 Black | Official OTA | Research | |
| HERO7 Black | Official OTA | Research | |
| HERO8 Black | Official OTA | Research | Largest Labs feature set for its era |
| HERO9 Black | Official OTA | Research | |
| HERO10 Black | Official OTA | Research | |
| HERO11 Black / Mini | Official OTA | Research | |
| HERO12 Black | Official OTA | Research | |
| HERO13 Black | Official OTA | Research | Latest supported body |
| MAX (360) | Official OTA | Research | 360-degree camera; Labs supported |

### Key Features

- **QR code scripting:** Point the camera at a QR code to set parameters, trigger actions, or load scripts without connecting to a phone or computer
- **Extended controls:** Boot commands, lens correction toggles, log curve options, wireless controls not in stock menus
- **Sunrise/sunset scheduling:** Time-based triggers using GPS
- **Faster frame rates / higher bitrates:** Some bodies expose additional recording modes via Labs
- **Overlay and metadata extensions:** GPS metadata, accelerometer data embedding

### Key Details

- **Official but experimental:** GoPro Labs is maintained by GoPro engineers but receives no official support. Features may disappear or break in subsequent releases.
- **Install:** Download the Labs `.zip` from the [GoPro Labs releases page](https://community.gopro.com/s/article/GoPro-Labs), copy to the SD card root, and run the camera's standard firmware update procedure.
- **Reverts cleanly:** Installing a standard (non-Labs) firmware update replaces Labs firmware completely.
- **No hardware risk:** Because this is an official signed firmware, there is no risk of hard-bricking from a failed update — the camera's bootloader will retry.
- **QR generator:** GoPro provides an [online QR code generator](https://gopro.github.io/labs/control/custom/) for building camera control scripts.

---

## DJI Drones

The DJI ecosystem has several independent community tools for firmware archiving, flashing, and research. Newer DJI hardware uses increasingly strong RSA firmware signing, limiting what is possible on recent drones.

**Legal notice:** Using Super-Patcher or similar tools to circumvent No-Fly Zone (NFZ) restrictions or altitude limits may be illegal in your jurisdiction and may violate aviation regulations. OSmosis documents these tools for research and educational purposes only. Always comply with local aviation law.

### Tools

| Tool | Repository | Purpose |
|------|-----------|---------|
| **DUMLdore** | [github.com/o-gs/dji-firmware-tools](https://github.com/o-gs/dji-firmware-tools) | Archive firmware images and flash them to DJI hardware over USB |
| **Super-Patcher** | Community distributions (see DJI forums / GitHub) | Patches for altitude limit removal, NFZ unlock, video bitrate |
| **dji-firmware-tools** | [github.com/o-gs/dji-firmware-tools](https://github.com/o-gs/dji-firmware-tools) | Dissect, analyze, and re-pack DJI firmware images; research tool |

### Supported Devices

| Device | Flash Method | Status | Notes |
|--------|-------------|--------|-------|
| Phantom 4 | DUMLdore | Research | Well-documented; most patches available |
| Phantom 4 Pro | DUMLdore | Research | Extended lens variant; same toolchain |
| Mavic Pro | DUMLdore | Research | Most popular DUMLdore target |
| Spark | DUMLdore | Research | Mini drone; weaker signing than Mavic 2 era |
| Inspire 2 | DUMLdore | Research | Pro cinema platform; limited patch set |
| Mavic Air | DUMLdore | Research | Intermediate signing; partial patch support |
| Mavic 2 Pro | DUMLdore | Research | Hasselblad sensor; stronger signing, reduced patch set |
| Mavic 2 Zoom | DUMLdore | Research | Optical zoom variant; same signing as Pro |

### Signing Generations

| Generation | Example Models | Community Tool Access |
|-----------|---------------|----------------------|
| Early signing (V1) | Phantom 4, Mavic Pro, Spark | Full firmware read/write; DUMLdore and Super-Patcher functional |
| Mid signing (V2) | Mavic Air, Mavic 2 series | Partial; some modules patchable, others not |
| Strong signing (V3+) | Mini 3, Mini 4, Mavic 3, Air 3 | Not cracked; DUMLdore read-only for research |

### Key Details

- **DUMLdore workflow:** Connect the drone over USB in DFU/download mode. DUMLdore enumerates connected modules (flight controller, gimbal, camera, remote) and can push firmware archives to each.
- **dji-firmware-tools for research:** This is the primary tool for reverse engineering DJI firmware images — unpacking encrypted modules, extracting file systems, and comparing versions. It is not a flashing GUI.
- **Mini 3 and newer:** DJI moved to RSA-signed per-module firmware with hardware-bound keys on Mini 3 and later. No community patches currently work on these platforms.
- **Backup before patching:** DUMLdore can dump existing firmware modules. Always save a copy before applying any patch so you can restore to a known-good state.

---

## External Links

| Project | URL |
|---------|-----|
| Magic Lantern | https://magiclantern.fm/ |
| Magic Lantern downloads | https://builds.magiclantern.fm/ |
| CHDK wiki | https://chdk.fandom.com/wiki/CHDK |
| CHDK supported cameras | https://chdk.fandom.com/wiki/CHDK_supported_Canon_cameras |
| OpenMemories-Tweak (GitHub) | https://github.com/ma1co/OpenMemories-Tweak |
| Sony-PMCA-RE (GitHub) | https://github.com/ma1co/Sony-PMCA-RE |
| Nikon Hacker wiki | https://nikonhacker.com/wiki/ |
| Nikon-Patch tool | https://nikonhacker.com/wiki/Nikon_Patch |
| GoPro Labs | https://community.gopro.com/s/article/GoPro-Labs |
| GoPro Labs QR generator | https://gopro.github.io/labs/control/custom/ |
| DUMLdore / dji-firmware-tools (GitHub) | https://github.com/o-gs/dji-firmware-tools |

---

## General Notes

### Before Modifying Camera Firmware

1. **Identify your exact firmware version.** Magic Lantern, CHDK, and Nikon-Patch all require version-specific builds. Using the wrong build can brick the camera.
2. **Use a fully charged battery.** Never flash during a firmware update with low battery. Most cameras will refuse to update below ~50%; heed this warning.
3. **Back up your existing firmware** where tools support it (DUMLdore, Nikon-Patch download step). Keep the official firmware zip from the manufacturer on hand for recovery.
4. **SD/CF card overlays (ML, CHDK) are the safest option.** If in doubt, prefer a card-based approach over internal flash patching.
5. **Understand what you are unlocking.** Removing video limits, bitrate caps, or compression removes engineering guardrails — heat, write speed, and battery consumption all increase under sustained high-load operation.
