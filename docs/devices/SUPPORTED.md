## Supported & target device types

Osmosis's scope is **any hardware that runs a software or OS**. Here's the landscape:

### Phones & tablets

| Device type | Stock OS | Alternative OS | Flash method | Status |
|-------------|----------|----------------|--------------|--------|
| Samsung Galaxy (Exynos) | Samsung Android / One UI | LineageOS, /e/OS, CalyxOS, PostmarketOS | Heimdall (Download Mode) | **Supported** |
| Samsung Galaxy (Snapdragon) | Samsung Android / One UI | LineageOS, /e/OS | Odin / Heimdall | **Supported** |
| Google Pixel | Pixel Android | CalyxOS, GrapheneOS, LineageOS | fastboot | **Supported** |
| OnePlus | OxygenOS | LineageOS, /e/OS, Paranoid Android | fastboot | **Supported** |
| Xiaomi / Poco / Redmi | MIUI / HyperOS | LineageOS, /e/OS, Pixel Experience | fastboot (unlocked BL) | **Supported** |
| Fairphone | Fairphone OS | /e/OS, LineageOS, CalyxOS | fastboot | **Supported** |
| Motorola | Moto UI | LineageOS | fastboot | **Supported** |
| Sony Xperia | Sony Android | LineageOS, AOSP | fastboot | **Supported** |
| Nothing Phone | Nothing OS | LineageOS | fastboot | **Supported** |
| PinePhone / PineTab | Various Linux | PostmarketOS, Mobian, Manjaro ARM, UBports | SD card / Tow-Boot | **Supported** |
| Librem 5 | PureOS | Mobian, PostmarketOS | uuu / SD card | **Supported** |

### Single-board computers & DIY

| Device type | Stock OS | Alternative OS | Flash method | Status |
|-------------|----------|----------------|--------------|--------|
| Raspberry Pi | Raspberry Pi OS | Ubuntu, Fedora, LibreELEC, Home Assistant | SD card / rpiboot | **Supported** |
| Orange Pi / Banana Pi | Armbian | Ubuntu, Debian, DietPi | SD card / USB | **Supported** |
| Pine64 (ROCK64, ROCKPro64) | Armbian | Manjaro ARM, Debian | SD card / eMMC | **Supported** |
| Radxa ROCK 5 | Armbian | Ubuntu, Debian | SD card / eMMC | **Supported** |
| ODROID | Armbian | Ubuntu, Android | SD card / eMMC | **Supported** |
| NVIDIA Jetson | JetPack / L4T | Ubuntu, Yocto | sdkmanager / flash.sh | **Supported** |
| RISC-V SBCs (VisionFive, Milk-V) | Vendor Linux | Debian, Fedora | SD card / USB | **Supported** |
| BeagleBone | Debian | Yocto, Buildroot, FreeBSD | SD card / USB DFU | Planned |
| ESP32 / Arduino | None | MicroPython, ESPHome, Tasmota | esptool / serial | **Supported** |

### Cars & automotive

| Device type | Stock OS | Alternative OS | Flash method | Status |
|-------------|----------|----------------|--------------|--------|
| Tesla MCU | Tesla firmware | Custom Linux (research) | OTA / USB (limited) | Research |
| Android Auto head units | Android (locked) | LineageOS, custom AOSP | fastboot / scatter | Planned |
| Raspberry Pi car setups | N/A | OpenAuto Pro, Crankshaft, Android Auto | SD card | Planned |
| OBD2 / ECU tuning | Vendor firmware | Open-source tunes | CAN bus / J2534 | Research |

### GPS & navigation

| Device type | Stock OS | Alternative OS | Flash method | Status |
|-------------|----------|----------------|--------------|--------|
| Garmin handheld / auto | Garmin OS | Custom maps / firmware mods | USB mass storage | Planned |
| TomTom | TomTom NavCore | OpenTom (legacy) | USB / SD card | Planned |
| Marine chartplotters | Vendor firmware | OpenCPN (on compatible hw) | SD card / USB | Research |
| Drone controllers (DJI) | DJI firmware | Custom FW (research) | DUMLdore / USB | Research |

### Marine & boats

| Device type | Stock OS | Alternative OS | Flash method | Status |
|-------------|----------|----------------|--------------|--------|
| Raymarine / Garmin MFD | Vendor firmware | Firmware updates / mods | SD card / network | Research |
| NMEA 2000 devices | Vendor firmware | SignalK (on RPi gateway) | CAN bus / serial | Planned |
| Boat Raspberry Pi hubs | Various | OpenPlotter, SignalK, OpenCPN | SD card | Planned |
| AIS transponders | Vendor firmware | dAISy / custom (open hw) | Serial / USB | Research |

### Routers, NAS & networking

| Device type | Stock OS | Alternative OS | Flash method | Status |
|-------------|----------|----------------|--------------|--------|
| Consumer routers | Vendor firmware | OpenWrt, DD-WRT, FreshTomato | TFTP / web UI / serial | **Supported** |
| Synology / QNAP NAS | DSM / QTS | XPEnology, TrueNAS (on x86) | USB / bootloader | Planned |
| Managed switches | Vendor OS | OpenSwitch, SONiC | Serial / ONIE | Research |

### Game consoles & media

| Device type | Stock OS | Alternative OS | Flash method | Status |
|-------------|----------|----------------|--------------|--------|
| Nintendo Switch | HOS | Atmosphere (CFW), Ubuntu, Android | RCM / Hekate | Planned |
| Steam Deck | SteamOS | HoloISO, Bazzite, Windows | USB / SD | Planned |
| PS Vita | Sony firmware | HENkaku / Enso (CFW) | USB / FTP | Research |
| Chromecast / Fire TV | Vendor Android | LineageOS (some models) | fastboot / adb | Planned |
| Kindle | Fire OS | LineageOS (Fire tablets) | adb sideload / fastboot | Planned |

### Electric scooters & PEVs

| Device type | Stock OS | Alternative OS | Flash method | Status |
|-------------|----------|----------------|--------------|--------|
| Ninebot Max G30/G2/F2 | Ninebot firmware | SHFW, CFW (cfw.sh) | BLE OTA / ST-Link | **Supported** |
| Ninebot ESx/Ex series | Ninebot firmware | SHFW, CFW (esx.cfw.sh) | BLE OTA / ST-Link | **Supported** |
| Ninebot F/D series | Ninebot firmware | SHFW, CFW | BLE OTA / ST-Link | **Supported** |
| Ninebot G3/F3/GT3/ZT3 | Ninebot firmware | Pending SHFW | BLE OTA / ST-Link | Planned |
| Ninebot P65/P100S/GT1/GT2 | Segway firmware | Pending | BLE OTA / ST-Link | Planned |
| Xiaomi M365/Pro/1S/Pro2/3 | Xiaomi firmware | SHFW, CFW (mi.cfw.sh) | BLE OTA / ST-Link | **Supported** |
| Xiaomi Mi 4/4 Pro/4 Ultra | Xiaomi firmware | CFW (bw-patcher) | UART / ST-Link | **Supported** |
| Xiaomi Mi 5/5 Pro | Xiaomi firmware | Stock only (DFU verify fails) | UART | Research |
| Okai ES series | Okai firmware | Community R&D | ST-Link | Research |

### Wearables & IoT

| Device type | Stock OS | Alternative OS | Flash method | Status |
|-------------|----------|----------------|--------------|--------|
| PineTime | InfiniTime | Wasp-OS, custom | OTA BLE / SWD | Planned |
| ESP-based smart home | Vendor cloud FW | Tasmota, ESPHome, WLED | esptool / OTA | Planned |
| IP cameras | Vendor firmware | OpenIPC, Dafang Hacks | SD card / UART | Planned |
| Smart speakers (rooted) | Vendor OS | Custom (limited) | ADB / UART | Research |

### Desktop & laptop firmware

| Device type | Stock OS | Alternative OS | Flash method | Status |
|-------------|----------|----------------|--------------|--------|
| ThinkPad X60 / T60 | BIOS (Phoenix/IBM) | Libreboot (fully free, no blobs) | `flashrom` internal or SPI clip | Research |
| ThinkPad X200 / T400 / T500 | BIOS (Phoenix) | Libreboot (w/ `me_cleaner`) | `flashrom` internal or CH341A SPI clip | Research |
| ThinkPad X230 / T430 / T530 / W530 | BIOS (Phoenix) | Coreboot + SeaBIOS/GRUB | `flashrom` SPI clip or 1vyrain | Research |
| Chromebooks (Bay Trail–Jasperlake) | ChromeOS (Google BIOS) | Full ROM UEFI Coreboot via MrChromebox | MrChromebox `firmware-util.sh`, WP screw removal | Planned |
| System76 laptops (Galago, Lemur, Oryx, Darter) | System76 firmware | Open-source EC firmware | `system76-firmware-cli` / FWUPD | Planned |
| Framework Laptop 13 / 16 | AMI UEFI + open EC | `framework-ec` open-source EC firmware | `flash_ec` script (USB-C debug) | Planned |
| Protectli Vault (FW4B, VP2420, VP4630) | AMI BIOS or Coreboot | Coreboot (official Protectli build) | `flashrom` via Protectli Flashli script | Planned |
| PC Engines APU2/APU3/APU4 | Coreboot + SeaBIOS | Coreboot (community maintained) | `flashrom` internal SPI | Planned |

### Digital cameras

| Device type | Stock OS | Alternative OS | Flash method | Status |
|-------------|----------|----------------|--------------|--------|
| Canon DSLRs (5D Mk II/III, 6D, 7D, 50D–70D, 650D–750D) | Canon proprietary (DIGIC 4/5/6/7) | Magic Lantern (runs from SD card, stock untouched) | SD/CF card + firmware update menu | Research |
| Canon PowerShot (A/S/G/SX/IXUS series) | Canon proprietary (DIGIC II–4) | CHDK (Canon Hack Development Kit, runs from SD) | SD card autoboot (locked card trick) | Research |
| Sony Alpha (A6000, A7/A7R/A7S gen 1–2, RX100 III/IV) | Sony PMCA (Android-based) | OpenMemories-Tweak (settings unlock, app sideload) | USB via Sony-PMCA-RE / pmca-console | Research |
| Nikon DSLRs (D3100–D800, EXPEED 2/3) | Nikon proprietary | Nikon-Patch (video bitrate/feature unlocks) | Patched firmware via SD card + update menu | Research |
| GoPro (HERO4–HERO13, MAX) | GoPro proprietary (Ambarella) | GoPro Labs (official experimental firmware) | SD card + camera update menu | Research |
| DJI Phantom 4 / Mavic Pro / Spark / Inspire 2 | DJI proprietary (DUML) | DUMLdore, Super-Patcher (alt-limit/NFZ) | USB via DUMLdore (Windows) | Research |

### E-readers

| Device type | Stock OS | Alternative OS | Flash method | Status |
|-------------|----------|----------------|--------------|--------|
| Kobo (Clara, Libra, Sage, Forma, Elipsa, Nia) | Kobo Nickel (Linux) | KOReader + NickelMenu (no exploit needed) | USB mass storage — copy to `.adds/` | Planned |
| reMarkable 1 & 2 | reMarkable OS (Linux/Yocto) | Toltec package manager, KOReader, Remux/Oxide | SSH over USB (root enabled by default) | Planned |
| PocketBook (Touch HD 3, InkPad, Era, Verse) | PocketBook (Linux) | KOReader, custom SDK apps (no exploit needed) | USB mass storage — copy to `applications/` | Research |
| Kindle (Paperwhite 1–5, Oasis, Scribe, Colorsoft) | Amazon Kindle OS (Linux) | KOReader (after jailbreak: WinterBreak/Nosebleed) | Jailbreak + USB file transfer | Research |
| Onyx Boox (Note Air, Nova, Tab Ultra, Palma) | Android 10–12 (Boox UI) | APK sideloading (no exploit), Magisk root | ADB install or USB file transfer | Research |

### Smart TVs & streaming devices

| Device type | Stock OS | Alternative OS | Flash method | Status |
|-------------|----------|----------------|--------------|--------|
| Samsung Smart TV (2018–2023) | Tizen OS | SamyGO (extensions, not full replacement) | SSH via developer mode | Research |
| LG Smart TV (webOS 4.0+) | webOS | Homebrew Channel via rootmy.tv exploits | Browser-based exploit → Homebrew Channel | Research |
| Android TV / Google TV boxes (Shield, Mi Box) | Android TV / Google TV | Custom ROMs, Magisk root | ADB / fastboot / TWRP | Planned |
| Amazon Fire TV Stick | FireOS (Android-based) | Debloat, custom launcher, Magisk root | ADB (USB or Wi-Fi) + sideload | Planned |
| Apple TV HD / 4K 1st gen | tvOS | palera1n jailbreak (checkm8 exploit) | palera1n via USB from Linux/macOS | Research |

### Robot vacuums

| Device type | Stock OS | Alternative OS | Flash method | Status |
|-------------|----------|----------------|--------------|--------|
| Roborock S5 / S6 / S7 / Q7 | Roborock Linux (cloud) | Valetudo (local-only cloud replacement) | DustBuilder firmware → local OTA | Research |
| Dreame L10 Pro / L20 Ultra / L10s Pro Ultra | Dreame Linux | Valetudo | UART rooting + SSH; DustBuilder on gen3 | Research |
| Xiaomi Mi Robot Vacuum Gen 1 | Xiaomi/Rockrobo Linux | Valetudo / ValetudoRE via DustBuilder | DustBuilder firmware → local OTA | Research |
| Ecovacs Deebot (various) | Ecovacs Linux | Partial root (research by Dennis Giese) | Model-specific; see robotinfo.dev | Research |

### Lab & test equipment

| Device type | Stock OS | Alternative OS | Flash method | Status |
|-------------|----------|----------------|--------------|--------|
| Rigol DS1054Z | Rigol Linux | 100 MHz unlock (same hardware as DS1104Z) | SCPI license key injection via USB/LAN | Research |
| Rigol MSO5000 series | Rigol Linux | Bandwidth/option unlock via key file | SSH + license file (root on early firmware) | Research |
| Siglent SDS1104X-E / SDS2000X Plus | Siglent Linux | Bandwidth/option unlock via license keys | SCPI command over USB/LAN | Research |
| Siglent SDG/SSA/SVA series | Siglent Linux | Feature unlock via license keys | SCPI over LAN | Research |
| Hantek 6022BE (Cypress FX2 USB scope) | Cypress FX2 firmware | sigrok `fx2lafw` open firmware | `fxload` USB upload or EEPROM burn | Planned |
| Saleae Logic clones (Cypress FX2) | Generic FX2 firmware | sigrok `fx2lafw` open firmware | `fxload` USB upload or EEPROM burn | Planned |

### Keyboards & input devices

| Device type | Stock OS | Alternative OS | Flash method | Status |
|-------------|----------|----------------|--------------|--------|
| QMK keyboards (Keychron Q/V, GMMK Pro, Drop CTRL/ALT, ErgoDox, Planck) | Stock QMK or vendor firmware | Full QMK customization, VIA/VIAL live remap | QMK Toolbox / `dfu-util` (STM32 DFU) | Planned |
| ZMK keyboards (nice!nano, Corne, Lily58, Sofle wireless splits) | ZMK stock | Full ZMK customization | UF2 drag-and-drop (double-tap reset) | Planned |
| Ploopy trackballs & trackpad | QMK (factory default) | Full QMK (open-source hardware + firmware) | QMK Toolbox via DFU | Planned |
| Razer mice (most models) | Razer Synapse | openRazer driver + razergenie GUI (Linux) | Driver install, no firmware flash | Research |
| Elgato Stream Deck (all models) | Elgato proprietary | `streamdeck-ui` open-source controller | No flash; USB HID control | Research |

### Synthesizers & audio

| Device type | Stock OS | Alternative OS | Flash method | Status |
|-------------|----------|----------------|--------------|--------|
| Mutable Instruments Eurorack (Plaits, Clouds, Rings, Braids, Beads) | MI stock (STM32, open source) | Parasites, Supercell, community alt firmwares | Audio bootloader (WAV into audio in) or ST-Link | Research |
| Korg NTS-1 / Minilogue XD / Prologue | Korg + logue SDK | Custom oscillators/effects via logue-sdk (C/C++) | USB + Korg Sound Librarian | Research |
| MOD Dwarf / Duo | MOD OS (Debian Linux) | User-installable LV2 plugins (fully open source) | Web UI over USB; OTA updates | Research |
| Teenage Engineering OP-1 | TE proprietary | op1repacker (modified stock, custom presets) | USB Mass Storage (TE-boot mode) | Research |
| Zoom multi-effects (G3Xn, MS-50G, B3n) | Zoom proprietary | Zoom Firmware Editor (effect swapping) | USB via Zoom Guitar Lab; SD card on some | Research |

### Solar & energy devices

| Device type | Stock OS | Alternative OS | Flash method | Status |
|-------------|----------|----------------|--------------|--------|
| Hoymiles microinverters (HM/HMS series) | Hoymiles (S-Miles cloud) | OpenDTU / AhoyDTU (ESP32 gateway) | esptool (ESP32 gateway, not the inverter) | Research |
| Victron GX devices / RPi gateway | Venus OS | Venus OS (open-source, RPi-installable) | SD card (RPi); OTA on GX hardware | Research |
| JBD / Daly / JK BMS | Vendor stock (STM32) | ESPHome BMS monitoring; BLE parameter config | BLE / UART config; ST-Link for chip access | Research |
| OpenEVSE EV charger | OpenEVSE stock | OpenEVSE ESP32 firmware (open source) | esptool (ESP32); avrdude (ATmega328P) | Research |

### Calculators

| Device type | Stock OS | Alternative OS | Flash method | Status |
|-------------|----------|----------------|--------------|--------|
| TI-84 Plus CE | TI-OS 5.x | arTIfiCE jailbreak + Cesium shell + ASM/C programs | Send .8xv via TI Connect CE over USB | Research |
| TI-Nspire CX / CX II | TI-Nspire OS | Ndless native code executor; Linux bootable | TI-Nspire Student Software / TI Connect | Research |
| NumWorks N0110/N0115 (fw ≤ 16) | Epsilon (open source) | Omega / Upsilon custom firmware | WebDFU in browser (hardware DFU button) | Research |
| Casio fx-CG50 (Prizm) | Casio OS (SH4A) | Community add-ins via Casio SDK (.g3a) | USB file transfer (no full OS replacement) | Research |
| HP Prime G1 / G2 | HP Prime OS (ARM) | HP Connectivity Kit for updates; Rip'Em (experimental) | USB via HP Connectivity Kit | Research |

### Retro handhelds & arcade

| Device type | Stock OS | Alternative OS | Flash method | Status |
|-------------|----------|----------------|--------------|--------|
| Anbernic RG35XX (H/Plus/SP/2024) | Anbernic Linux (Allwinner H700) | GarlicOS, muOS, KNULLI | SD card image flash | Planned |
| Anbernic RG353 (V/M/VS/PS) | Anbernic Linux (RK3566) | KNULLI, ArkOS, ROCKNIX | SD card image flash | Planned |
| Miyoo Mini (Plus) | Miyoo Linux (Allwinner A33) | Onion OS, MiniUI | SD card (FAT32, extract to root) | Planned |
| MiSTer FPGA (DE10-Nano) | MiSTer Linux + FPGA | 500+ open hardware cores (NES, SNES, GBA, PS1, arcade) | SD card + Update_All script over network | Planned |
| TrimUI Smart Pro / Brick | TrimUI Linux (Allwinner) | KNULLI, MinUI | SD card image flash | Planned |
| Powkiddy RGB30 / X55 | Powkiddy Linux (RK3566) | KNULLI, ROCKNIX, ArkOS | SD card image flash | Planned |

### Server BMC/IPMI

| Device type | Stock OS | Alternative OS | Flash method | Status |
|-------------|----------|----------------|--------------|--------|
| Meta/Facebook server platforms (AST2500/AST2600) | Proprietary BMC or OpenBMC | OpenBMC | JTAG / BMC web UI / flashrom SPI | Research |
| IBM POWER9/POWER10 (Witherspoon, Rainier) | OpenBMC | OpenBMC | JTAG / in-band flash | Research |
| Supermicro IPMI (X10/X11/X12 boards) | ATEN IPMI firmware | OpenBMC (experimental on some X11) | Web UI / SUM CLI / flashrom | Research |

### Agricultural equipment

| Device type | Stock OS | Alternative OS | Flash method | Status |
|-------------|----------|----------------|--------------|--------|
| John Deere tractor ECUs | JD proprietary (locked) | None — FTC lawsuit pending (Jan 2025) | Dealer-only (Service ADVISOR tool) | Not supported |
| AgOpenGPS auto-steer (Arduino/ESP32) | N/A — open source | AgOpenGPS + esp32-aog | Arduino IDE / esptool over USB | Research |
| ArduPilot ag drones (PixHawk) | ArduPilot (open) | ArduPilot / PX4 | USB via Mission Planner / QGroundControl | Research |

### Powered wheelchairs & mobility

| Device type | Stock OS | Alternative OS | Flash method | Status |
|-------------|----------|----------------|--------------|--------|
| PG Drives R-NET / Curtis / Dynamic Controls | Proprietary (medical) | None — closed medical hardware | Dealer programmer only | Not supported |
| SuperHouse WMC (DIY wheelchair controller) | N/A — open source | WMC firmware (Arduino) | USB (arduino-cli / Arduino IDE) | Research |
| SuperHouse PWC (Permobil adapter, ESP32) | N/A — open source | PWC firmware (ESP32) | USB (esptool / Arduino IDE) | Research |

### Satellite / CubeSat

| Device type | Stock OS | Alternative OS | Flash method | Status |
|-------------|----------|----------------|--------------|--------|
| CubeSat flight computers (STM32/PixHawk) | FreeRTOS / bare-metal | ArduPilot / ChibiOS | USB DFU or JTAG/SWD | Research |
| SatNOGS ground station (RPi + SDR) | Raspbian / SatNOGS OS | SatNOGS client | SD card (standard RPi image) | Research |
| SatNOGS-COMMS (CubeSat comms subsystem) | Zephyr RTOS | SatNOGS-COMMS firmware (open source) | JTAG/SWD (STM32H743 + ZYNQ FPGA) | Research |

### Storage & GPU firmware

| Device type | Stock OS | Alternative OS | Flash method | Status |
|-------------|----------|----------------|--------------|--------|
| NVMe SSDs (Samsung, WD, Crucial) | Vendor proprietary | Stock updates only (no open alternative) | `nvme-cli` (`fw-download` + `fw-commit`) | Research |
| NVIDIA GeForce VBIOS (Turing/Ampere/Ada) | NVIDIA proprietary VBIOS | Modified VBIOS (power limit/OC unlock) | `nvflash` / `nvflashk` | Research |
| AMD Radeon VBIOS (RX 500–7000) | AMD proprietary VBIOS | Modified VBIOS (memory strap/power mods) | AMDVBFlash / ATIFlash | Research |

### Medical devices (data access)

> None of these involve replacing medical device firmware. All listed tools run on separate hardware (phones, RPis) for data access and automation alongside the device.

| Device type | Stock OS | Alternative OS | Flash method | Status |
|-------------|----------|----------------|--------------|--------|
| CPAP machines (ResMed AirSense, Philips DreamStation) | Vendor proprietary | OSCAR (data analysis via SD card export) | SD card read-only — no flash | Research |
| Insulin pumps (Medtronic 512–554, Omnipod) | Vendor proprietary | OpenAPS / AndroidAPS / Loop (closed-loop on phone) | Wireless radio/BLE from phone — no flash | Research |
| CGMs (Dexcom G5–G7, FreeStyle Libre 2/3) | Vendor proprietary | xDrip+ / Juggluco (data relay on phone) | Bluetooth intercept — no flash | Research |

### Legend

- **Supported** — works today in Osmosis
- **Verified** — supported and verified on real hardware by the OSmosis team
- **Planned** — on the roadmap, flash method is well-documented
- **Research** — feasible but requires reverse engineering or device-specific tooling
- **Not supported** — listed for awareness; proprietary/locked with no open firmware

