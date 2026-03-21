# Device Compatibility Wiki

OSmosis supports flashing, configuring, and managing firmware across a wide range of device categories. This wiki documents every supported device, the operating systems and firmware available for it, and compatibility notes.

## Device Categories

| Category | Devices | Description |
|----------|---------|-------------|
| [Android Phones & Tablets](android-phones-tablets.md) | 40+ | Samsung, Google Pixel, OnePlus, Xiaomi, Motorola, Sony, Fairphone, Nothing |
| [Linux Phones](linux-phones.md) | 4 | PinePhone, PinePhone Pro, PineTab 2, Librem 5 |
| [Single-Board Computers](single-board-computers.md) | 25+ | Raspberry Pi, Pine64, Orange Pi, Radxa, ODROID, NVIDIA Jetson, RISC-V |
| [Electric Scooters](scooters.md) | 50+ | Ninebot, Xiaomi, Okai, Pure, NIU, Navee, Vsett, Dualtron |
| [E-Bike Controllers](ebikes.md) | 30+ | Bafang, Tongsheng TSDZ2, Kunteng, VESC, CYC, plus locked systems |
| [Microcontrollers](microcontrollers.md) | 60+ | Arduino, ESP32, RPi Pico, STM32, Teensy, Adafruit, LoRa/Meshtastic, 3D printer boards |
| [Apple T2 Macs](apple-t2.md) | 12 | MacBook Pro/Air 2018-2020, iMac, iMac Pro, Mac Pro, Mac mini |
| [Alternative Tools](alternative-tools.md) | -- | Flipper Zero, HackRF, Bus Pirate, component salvage, repurposing guides |

## Support Levels

OSmosis uses the following support levels across all device categories:

| Level | Meaning |
|-------|---------|
| **Supported** | Full flashing workflow available in the wizard. Tested by the community. |
| **Experimental** | Flashing works but has limited testing. May require manual steps. |
| **Planned** | Device is recognized by OSmosis but firmware/flashing support is not yet implemented. |
| **Not supported** | Listed for awareness only. Proprietary/locked system with no open firmware. |

## Flash Methods

Different device categories use different flashing methods:

| Method | Used by | Description |
|--------|---------|-------------|
| **Odin/Heimdall** | Samsung Android devices | Samsung's download mode protocol |
| **Fastboot** | Pixel, OnePlus, Xiaomi, Motorola, Sony | Android bootloader flashing |
| **Recovery (TWRP)** | Most Android devices | Flash ZIPs via custom recovery |
| **BLE** | Ninebot/Xiaomi scooters | Bluetooth Low Energy firmware push |
| **ST-Link** | Scooters, e-bikes, STM32 MCUs | SWD debug probe for STM32/STM8 chips |
| **UART** | Xiaomi Mi 4+, e-bikes, some scooters | Serial connection flashing |
| **USB DFU** | Apple T2, STM32, flight controllers | USB Device Firmware Upgrade protocol |
| **esptool** | ESP32/ESP8266 boards | Espressif's serial flash tool |
| **picotool** | Raspberry Pi Pico family | RP2040/RP2350 UF2 bootloader |
| **arduino-cli** | Arduino and compatible boards | Arduino ecosystem flash tool |
| **SD card** | SBCs, Linux phones | Write image to SD/eMMC and boot |

## How to Use This Wiki

- **Looking for your device?** Browse the category pages above or use your browser's search (Ctrl+F) on the relevant page.
- **Want to know what OS options you have?** Each device entry lists all compatible operating systems and firmware, with links to downloads and project pages.
- **Checking if your device is flashable?** Look at the support level. "Supported" and "Experimental" devices can be flashed today. "Planned" devices are on the roadmap.
