# Keyboards & Input Devices

OSmosis documents open-source firmware flashing and configuration for keyboards, mice, and other input devices. This category is unusually healthy: QMK, ZMK, and VIA have established, well-maintained toolchains that cover hundreds of boards.

Most keyboards listed here are **Planned** (wizard in development) or effectively already accessible via their own official tools. Gaming mice and Stream Deck are also covered.

---

## Support Levels

| Level | Meaning |
|-------|---------|
| **Supported** | Full flashing workflow available in OSmosis. |
| **Planned** | Device recognized by OSmosis. Flashing works via community tools today; OSmosis wizard in progress. |
| **Not supported** | Proprietary firmware. Listed for awareness. |

---

## QMK Keyboards

[QMK (Quantum Mechanical Keyboard)](https://qmk.fm/) is the dominant open-source keyboard firmware. It runs on AVR (ATmega32U4), ARM (STM32, RP2040), and other MCUs, and supports nearly every feature a keyboard could need.

### Keychron

Keychron ships several of their keyboards with QMK/VIA pre-installed or as a QMK-compatible variant.

| Model | MCU | Flash Method | Firmware | Status |
|-------|-----|-------------|---------|--------|
| Keychron Q1 Pro | STM32 | QMK Toolbox / `qmk flash` | QMK | Planned |
| Keychron Q2 Pro | STM32 | QMK Toolbox / `qmk flash` | QMK | Planned |
| Keychron Q3 Pro | STM32 | QMK Toolbox / `qmk flash` | QMK | Planned |
| Keychron Q5 Pro | STM32 | QMK Toolbox / `qmk flash` | QMK | Planned |
| Keychron V1 | STM32 | QMK Toolbox / `qmk flash` | QMK | Planned |
| Keychron V2 | STM32 | QMK Toolbox / `qmk flash` | QMK | Planned |
| Keychron V3 | STM32 | QMK Toolbox / `qmk flash` | QMK | Planned |
| Keychron V6 | STM32 | QMK Toolbox / `qmk flash` | QMK | Planned |

### GMMK Pro

| Model | MCU | Flash Method | Firmware | Status |
|-------|-----|-------------|---------|--------|
| Glorious GMMK Pro | STM32F303 | QMK Toolbox (DFU mode) | QMK | Planned |

### Drop

| Model | MCU | Flash Method | Firmware | Status |
|-------|-----|-------------|---------|--------|
| Drop CTRL | STM32F303 | QMK Toolbox | QMK | Planned |
| Drop ALT | STM32F303 | QMK Toolbox | QMK | Planned |
| Drop SHIFT | STM32F303 | QMK Toolbox | QMK | Planned |
| Drop ENTR | STM32F303 | QMK Toolbox | QMK | Planned |

### Ortholinear & Compact

| Model | MCU | Flash Method | Firmware | Status |
|-------|-----|-------------|---------|--------|
| Planck EZ | STM32F303 | QMK Toolbox | QMK | Planned |
| Planck (OLKB) | ATmega32U4 | `avrdude` / QMK Toolbox | QMK | Planned |
| Preonic | ATmega32U4 | QMK Toolbox | QMK | Planned |

### Ergonomic & Split

| Model | MCU | Flash Method | Firmware | Status |
|-------|-----|-------------|---------|--------|
| ErgoDox EZ | ATmega32U4 (×2) | QMK Toolbox (each half) | QMK | Planned |
| Moonlander MK1 | STM32F303 (×2) | QMK Toolbox | QMK | Planned |
| Kyria | Pro Micro / Elite-C | QMK Toolbox | QMK | Planned |
| Sofle | Pro Micro | QMK Toolbox | QMK | Planned |
| Corne (crkbd) | Pro Micro / Elite-C | QMK Toolbox | QMK | Planned |
| Lily58 | Pro Micro | QMK Toolbox | QMK | Planned |
| Dactyl Manuform | Pro Micro / Elite-C | QMK Toolbox | QMK | Planned |

### QMK Flash Methods

| Method | Used For | Notes |
|--------|---------|-------|
| QMK Toolbox | Most QMK keyboards | GUI tool for Windows/macOS. Detects connected keyboard and flashes `.hex` or `.bin`. |
| `qmk flash` | Command line | Cross-platform. Part of the QMK CLI (`pip install qmk`). |
| `avrdude` | AVR boards (ATmega32U4) | Used under the hood by QMK Toolbox for AVR targets. |
| DFU-util | STM32 boards | Used for STM32 DFU bootloader. QMK Toolbox wraps this automatically. |
| Bootmagic reset | All QMK boards | Hold a corner key (usually top-left) while plugging in to enter bootloader. |

---

## VIA / VIAL (No Flash Required)

[VIA](https://www.caniusevia.com/) and [VIAL](https://get.vial.today/) are real-time keyboard configuration tools that communicate with the keyboard over USB HID. **No firmware flash is required** — VIA/VIAL support is baked into the keyboard's existing QMK firmware.

| Tool | What It Does | Persistence |
|------|-------------|------------|
| VIA | Remap keys, configure layers, macros, and lighting via a browser-based UI | Saved to keyboard EEPROM |
| VIAL | VIA superset. Adds tap-dance, combos, key overrides, and more. Open-source GUI. | Saved to keyboard EEPROM |

### VIA-Compatible Keyboards (Selection)

Any keyboard that ships with VIA-enabled QMK firmware works without flashing:

| Model | Notes |
|-------|-------|
| Keychron Q/V series | Ships with VIA enabled |
| GMMK Pro | VIA support in stock firmware |
| Drop CTRL/ALT | VIA support in stock firmware |
| KBDfans boards | Most ship VIA-enabled |
| Any QMK keyboard with `VIA_ENABLE = yes` | |

**Workflow:** Open [usevia.app](https://usevia.app/) in Chrome/Edge, plug in your keyboard, and configure. No drivers, no install, no flashing.

---

## ZMK (Wireless Keyboards)

[ZMK Firmware](https://zmk.dev/) is the open-source firmware ecosystem for wireless split keyboards. Unlike QMK, ZMK is built on Zephyr RTOS and targets Bluetooth Low Energy keyboards.

### nice!nano and Compatible Controllers

| Controller | MCU | Flash Method | Firmware | Status |
|------------|-----|-------------|---------|--------|
| nice!nano v2 | nRF52840 | UF2 drag-and-drop | ZMK | Planned |
| nice!nano v1 | nRF52840 | UF2 drag-and-drop | ZMK | Planned |
| Seeed XIAO BLE | nRF52840 | UF2 drag-and-drop | ZMK | Planned |
| nRFMicro | nRF52840 | UF2 drag-and-drop | ZMK | Planned |

### UF2 Flash Method

ZMK builds produce `.uf2` files. Flashing is entirely drag-and-drop:

1. Double-tap the reset button on the controller to enter the UF2 bootloader.
2. The controller mounts as a USB mass storage device.
3. Copy the `.uf2` file to the drive.
4. The controller reboots automatically with the new firmware.

### ZMK Keyboards (Selection)

| Model | Controller | Status |
|-------|-----------|--------|
| Corne Wireless | nice!nano | Planned |
| Sofle Wireless | nice!nano | Planned |
| Lily58 Wireless | nice!nano | Planned |
| Kyria Wireless | nice!nano | Planned |
| Sweep | nice!nano | Planned |
| Zen | nRF52840 | Planned |

### Building ZMK Firmware

ZMK firmware is built via GitHub Actions using the [zmk-config](https://zmk.dev/docs/user-setup) pattern — you fork a template repo, edit a keymap file in YAML, and GitHub builds the `.uf2` for you. No local toolchain needed.

---

## Ploopy Trackballs

[Ploopy](https://ploopy.co/) makes open-source, open-hardware trackballs that ship with QMK firmware from the factory.

| Model | MCU | Flash Method | Firmware | Status |
|-------|-----|-------------|---------|--------|
| Ploopy Classic Trackball | ATmega32U4 | QMK Toolbox | QMK (official) | Planned |
| Ploopy Nano Trackball | ATmega32U4 | QMK Toolbox | QMK (official) | Planned |
| Ploopy Adept Trackball | ATmega32U4 | QMK Toolbox | QMK (official) | Planned |
| Ploopy Thumb Trackball | ATmega32U4 | QMK Toolbox | QMK (official) | Planned |

Ploopy hardware designs and firmware are fully open source. KiCad schematics and QMK keymaps are published on GitHub.

---

## Gaming Mice

Gaming mice have proprietary DPI, RGB, and macro settings stored in onboard flash. Several open-source tools provide Linux-compatible configuration without vendor software.

| Tool | Supported Brands | Method | Status |
|------|----------------|--------|--------|
| [openRazer](https://openrazer.github.io/) | Razer | Linux kernel driver + daemon | Planned |
| [rivalcfg](https://github.com/flozz/rivalcfg) | SteelSeries | Python CLI/library | Planned |
| [libratbag](https://github.com/libratbag/libratbag) / Piper GUI | Logitech, Razer, SteelSeries, ROCCAT, and more | D-Bus daemon + GTK GUI | Planned |

### openRazer

openRazer is a Linux kernel driver and userspace daemon for Razer peripherals. It exposes device settings (DPI, lighting, macros, polling rate) via `/sys/bus/hid/drivers/razerkbd/` and a D-Bus API.

- Supports 100+ Razer mice, keyboards, headsets, and mousepads
- Works with Polychromatic (GUI) or command-line tools
- No firmware replacement — configures the device's onboard hardware

### rivalcfg

rivalcfg is a Python tool for SteelSeries mice. It supports DPI stages, polling rate, LED color, and button configuration across SteelSeries Rival, Sensei, and Prime series.

### libratbag / Piper

libratbag is a hardware abstraction library for gaming mice. Piper is its GTK frontend. Together they support a broad range of mice from multiple vendors with a consistent interface.

---

## Stream Deck

The Elgato Stream Deck is a macro pad with per-key LCD displays. The open-source [streamdeck-ui](https://timothycrosley.github.io/streamdeck-ui/) project provides full Linux support without Elgato's software.

| Model | Keys | Status |
|-------|------|--------|
| Stream Deck Original (15-key) | 15 | Planned |
| Stream Deck Mini (6-key) | 6 | Planned |
| Stream Deck XL (32-key) | 32 | Planned |
| Stream Deck MK.2 | 15 | Planned |
| Stream Deck Plus (dials + keys) | 8 + 4 dials | Planned |

### streamdeck-ui

[streamdeck-ui](https://timothycrosley.github.io/streamdeck-ui/) is a Python application using the `python-elgato-streamdeck` library. It provides:

- Per-key image and label assignment
- Multi-page layouts
- Shell command, keyboard shortcut, and text injection actions
- System tray integration
- Works without any Elgato account or cloud connectivity

**Flash note:** Stream Deck does not involve firmware flashing. streamdeck-ui is a host-side configuration application.

---

## General Notes

### Entering Bootloader on QMK Keyboards

There are three common methods to enter the QMK bootloader:

1. **Bootmagic Lite:** Hold a configured key (usually top-left) while plugging in the USB cable.
2. **RESET keycode:** If your current keymap has a RESET key assigned, press it.
3. **Physical reset button:** Many PCBs have a small reset button accessible through the bottom plate.

### Flashing Both Halves of a Split

For split keyboards (ErgoDox, Moonlander, Corne, etc.), each half has its own MCU. You must flash each half separately:

1. Plug in the left half, enter bootloader, flash.
2. Plug in the right half, enter bootloader, flash with the same or mirror firmware.

### EEPROM and Configuration Persistence

QMK stores dynamic configuration (VIA remaps, RGB settings, EEPROM-persisted values) in the MCU's EEPROM. Flashing new firmware does not automatically clear EEPROM. If you experience unexpected behavior after a firmware update, use `EEP_RST` (EEPROM reset) to clear stored settings.

---

## Links

| Resource | URL |
|---------|-----|
| QMK Firmware | https://qmk.fm/ |
| QMK documentation | https://docs.qmk.fm/ |
| QMK Toolbox | https://github.com/qmk/qmk_toolbox |
| VIA configurator | https://usevia.app/ |
| VIAL configurator | https://get.vial.today/ |
| ZMK Firmware | https://zmk.dev/ |
| Ploopy open-source hardware | https://github.com/ploopyco |
| openRazer | https://openrazer.github.io/ |
| rivalcfg | https://github.com/flozz/rivalcfg |
| libratbag / Piper | https://github.com/libratbag/libratbag |
| streamdeck-ui | https://timothycrosley.github.io/streamdeck-ui/ |
