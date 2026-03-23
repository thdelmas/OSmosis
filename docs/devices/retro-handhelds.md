# Retro Handhelds & Arcade

OSmosis documents custom OS and firmware options for retro gaming handhelds, FPGA arcade boards, and emulation-focused portable devices. All devices in this category use SD card flashing — no soldering, debug probes, or bootloader exploits are required for the custom OS options listed here.

Most entries are **Planned** for OSmosis wizard support. The community tools referenced here work today.

---

## Support Levels

| Level | Meaning |
|-------|---------|
| **Planned** | OSmosis wizard in development. SD card flash works today via community tools. |
| **Experimental** | Custom OS exists but is unstable or incomplete for this specific device. |
| **Not supported** | No custom OS available. |

---

## Flash Method: SD Card

All devices on this page use the same fundamental flash method:

1. Download the custom OS image.
2. Flash the image to a microSD card using a tool like Balena Etcher, `dd`, or the Raspberry Pi Imager.
3. Insert the SD card into the handheld and power on.
4. The device boots from the SD card directly.

Most of these devices boot from SD card without any modification to the internal storage. Stock firmware on internal storage is usually preserved and accessible by booting without the SD card.

---

## Anbernic RG35XX Family

Anbernic's RG35XX line is one of the most popular platforms for custom handheld OS development.

| Device | SoC | Custom OS Options | Status |
|--------|-----|-----------------|--------|
| Anbernic RG35XX (original) | Allwinner H700 | GarlicOS, muOS | Planned |
| Anbernic RG35XX Plus | Allwinner H700 | GarlicOS 2.0, muOS, KNULLI | Planned |
| Anbernic RG35XX H | Allwinner H700 | GarlicOS 2.0, muOS, KNULLI | Planned |
| Anbernic RG35XX SP | Allwinner H700 | GarlicOS 2.0, muOS, KNULLI | Planned |

### GarlicOS

[GarlicOS](https://www.patreon.com/baxysquared) is a custom OS for RG35XX devices focused on simplicity and performance. It provides:

- Cleaned-up EmulationStation frontend
- Optimized emulator cores (RetroArch-based)
- Minimal boot time
- Theme support

GarlicOS 2.0 expanded support to the Plus, H, and SP variants.

### muOS

[muOS](https://muos.dev/) is a more feature-rich custom OS for the RG35XX family. Key features:

- Custom-built frontend (not EmulationStation)
- Advanced theme and font customization
- Network time sync, SSH access
- Port support (DOOM, Quake, ScummVM)
- Active development with frequent releases

---

## Anbernic RG353 Family

The RG353 series uses Rockchip RK3566 and supports a broader range of custom OS options.

| Device | SoC | Custom OS Options | Status |
|--------|-----|-----------------|--------|
| Anbernic RG353P | Rockchip RK3566 | KNULLI, ArkOS, ROCKNIX | Planned |
| Anbernic RG353V | Rockchip RK3566 | KNULLI, ArkOS, ROCKNIX | Planned |
| Anbernic RG353VS | Rockchip RK3566 | KNULLI, ArkOS, ROCKNIX | Planned |
| Anbernic RG353M | Rockchip RK3566 | KNULLI, ArkOS, ROCKNIX | Planned |

### ArkOS

[ArkOS](https://github.com/christianhaitian/arkos) is a Debian-based custom OS with a long history on Rockchip handhelds. It provides:

- EmulationStation frontend
- Good emulator compatibility across a wide range of systems
- Retroachievements support
- Networking, SSH, Samba

### ROCKNIX

[ROCKNIX](https://rocknix.org/) (formerly JelOS) is an immutable Linux distribution for Rockchip-based handhelds. It provides:

- Read-only root filesystem for stability
- Batocera-like experience
- Strong emulator support including PS2 (PCSX2) and GameCube/Wii (Dolphin)
- Overlays and shaders

---

## Anbernic RG556

| Device | SoC | Custom OS Options | Status |
|--------|-----|-----------------|--------|
| Anbernic RG556 | Unisoc T618 | KNULLI (experimental) | Experimental |

The RG556 is a newer, higher-powered device. KNULLI support is in development but not yet stable for daily use.

---

## Miyoo Mini / Miyoo Mini Plus

The Miyoo Mini and Mini Plus are ultra-portable handhelds with a strong custom OS community. The stock OS is considered poor, making custom OS effectively the default recommendation.

| Device | SoC | Custom OS Options | Status |
|--------|-----|-----------------|--------|
| Miyoo Mini (v1/v2/v3/v4) | ARM Cortex-A7 | Onion OS, MiniUI | Planned |
| Miyoo Mini Plus | ARM Cortex-A7 | Onion OS, MiniUI | Planned |
| Miyoo Flip | ARM | Onion OS (early support) | Experimental |

### Onion OS

[Onion OS](https://onionui.github.io/) is the dominant custom OS for the Miyoo Mini. It provides:

- RetroArch with optimized per-core settings for each emulated system
- GameSwitcher (quick save/resume between games)
- Themes and UI customization
- Search functionality across the entire game library
- Networking (Wi-Fi via the Mini Plus's built-in adapter)
- Package manager for additional apps and tweaks

### MiniUI

[MiniUI](https://github.com/shauninman/MiniUI) is a minimalist alternative to Onion OS. It prioritizes:

- Extremely fast boot and game launch times
- Dead-simple interface — no menus, just a game picker
- Low RAM footprint
- Ideal for users who want a dedicated game-playing experience with no friction

---

## MiSTer FPGA

[MiSTer FPGA](https://MiSTerFPGA.org/) is an open-source FPGA platform for cycle-accurate hardware emulation of classic computers and consoles. It runs on a Terasic DE10-Nano board (Intel Cyclone V FPGA) with optional I/O boards.

| Component | Flash Method | Status |
|-----------|-------------|--------|
| MiSTer Linux SD card image | SD card | Planned |
| Individual FPGA cores (.rbf files) | Update_All script / manual copy | Planned |
| I/O board firmware | USB | Planned |

### What MiSTer Provides

- **500+ open FPGA cores** replicating arcade hardware, game consoles (NES, SNES, Genesis, N64, PS1), and home computers (Amiga, C64, ZX Spectrum, Atari ST) at the hardware level — not software emulation
- Cycle-accurate timing, so games behave identically to original hardware
- **Analog video output** (HDMI and VGA/RGBS via I/O board) compatible with CRTs
- USB controller support and original controller adapters (DB9, SNES/NES, etc.)
- Jamma interface for arcade cabinet integration (with additional I/O board)

### Update_All

[Update_All](https://github.com/theypsilon/Update_All_MiSTer) is a community script that updates all installed cores, the MiSTer Linux image, and optional extras in one command. It is the standard maintenance tool for MiSTer users.

### Key Details

- **Not a handheld:** MiSTer is a desktop/cabinet platform. It requires a DE10-Nano board, an SD card, and optionally a USB hub and I/O board.
- **Core quality varies:** Some cores (SNES, Genesis, Amiga) are extremely mature and accurate. Others are experimental.
- **Hardware cost:** DE10-Nano + basic I/O board is approximately $150–250 USD.

---

## TrimUI Smart Pro / TrimUI Brick

TrimUI devices are compact handhelds with HDMI output (Smart Pro) or a pocketable design (Brick). KNULLI and MinUI support these platforms.

| Device | SoC | Custom OS Options | Status |
|--------|-----|-----------------|--------|
| TrimUI Smart Pro | Allwinner A133P | KNULLI, MinUI | Planned |
| TrimUI Brick | Allwinner A133 | KNULLI, MinUI | Planned |

---

## Powkiddy

Powkiddy makes a range of handhelds across different form factors and SoC tiers.

| Device | SoC | Custom OS Options | Status |
|--------|-----|-----------------|--------|
| Powkiddy RGB30 | Rockchip RK3566 | KNULLI, ROCKNIX, ArkOS | Planned |
| Powkiddy X55 | Rockchip RK3566 | KNULLI, ROCKNIX, ArkOS | Planned |
| Powkiddy RGB20S | Allwinner H700 | GarlicOS, muOS | Planned |
| Powkiddy RGB10 Max 3 | Rockchip RK3566 | KNULLI, ROCKNIX | Planned |

---

## KNULLI (Cross-Platform Custom OS)

[KNULLI](https://knulli.org/) deserves special mention because it targets the widest range of handhelds of any single custom OS project. It is a Batocera-based distribution with device-specific adaptations.

### KNULLI Key Features

- Batocera UI and game library management
- Retroachievements integration
- Netplay support
- Per-game video filters and shaders
- SSH, Samba, and scraper support
- Regularly updated with new device support

### KNULLI Supported Devices (subset listed above)

Allwinner H700 (RG35XX family), Rockchip RK3566 (RG353, RGB30, X55), Unisoc T618 (RG556 experimental), Allwinner A133/A133P (TrimUI family).

---

## General Notes

### SD Card Recommendations

| SD Card | Notes |
|---------|-------|
| Samsung PRO Endurance | Best choice for write-heavy workloads (saves, states) |
| SanDisk Endurance or Ultra | Good reliability and speed |
| Any A1-rated card | Minimum recommended class for OS images |

Cheap unbranded SD cards frequently cause corruption, especially with the frequent small writes that emulator save states generate. Use a reputable brand.

### Stock Firmware Preservation

All devices on this page boot the custom OS from the SD card slot. The internal storage (if any) retains the stock OS. To return to stock:

- Power on without the SD card, or
- Hold the device's recovery key combination during boot (device-specific)

### BIOS Files

Most emulators require system BIOS files for accurate emulation (PS1, Sega CD, Neo Geo, etc.). These files are not distributed with custom OS images due to copyright. You must provide your own BIOS files extracted from hardware you own.

---

## Links

| Resource | URL |
|---------|-----|
| KNULLI | https://knulli.org/ |
| ROCKNIX | https://rocknix.org/ |
| GarlicOS | https://www.patreon.com/baxysquared |
| muOS | https://muos.dev/ |
| Onion OS (Miyoo Mini) | https://onionui.github.io/ |
| MiniUI | https://github.com/shauninman/MiniUI |
| MiSTer FPGA | https://MiSTerFPGA.org/ |
| Update_All (MiSTer) | https://github.com/theypsilon/Update_All_MiSTer |
| ArkOS | https://github.com/christianhaitian/arkos |
