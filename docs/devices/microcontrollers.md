# Microcontrollers

OSmosis supports flashing firmware to a wide range of microcontroller development boards. This includes compiling and uploading Arduino sketches, flashing ESP32/ESP8266 firmware, programming RP2040 boards, and flashing STM32 via ST-Link.

---

## Flash Tools

| Tool | Boards | Description |
|------|--------|-------------|
| **arduino-cli** | Arduino, Adafruit, Seeed, some Teensy | Arduino ecosystem compile-and-upload tool |
| **esptool** | ESP32, ESP8266, all Espressif chips | Espressif's serial flash utility |
| **picotool** | Raspberry Pi Pico family, RP2040 boards | UF2 bootloader flash tool |
| **stflash** | STM32 boards | Open-source ST-Link flash utility |
| **teensy_loader_cli** | Teensy boards | PJRC's Teensy upload tool |
| **dfu-util** | STM32 (DFU mode), BBC micro:bit, flight controllers | USB DFU protocol flash tool |
| **avrdude** | Legacy AVR boards | AVR ISP programmer (used as fallback) |

---

## Arduino Boards

The Arduino ecosystem is the largest hobbyist microcontroller platform. OSmosis uses `arduino-cli` to compile and upload sketches.

### AVR-Based (Classic)

| Board | MCU | Clock | USB Chip | FQBN | Status |
|-------|-----|-------|----------|------|--------|
| Arduino Uno | ATmega328P | 16 MHz | ATmega16U2 | `arduino:avr:uno` | Supported |
| Arduino Mega 2560 | ATmega2560 | 16 MHz | ATmega16U2 | `arduino:avr:mega` | Supported |
| Arduino Nano | ATmega328P | 16 MHz | FTDI/CH340 | `arduino:avr:nano` | Supported |
| Arduino Nano Every | ATmega4809 | 20 MHz | SAMD11 | `arduino:megaavr:nona4809` | Supported |
| Arduino Leonardo | ATmega32U4 | 16 MHz | Native USB | `arduino:avr:leonardo` | Supported |
| Arduino Micro | ATmega32U4 | 16 MHz | Native USB | `arduino:avr:micro` | Supported |

### ARM-Based

| Board | MCU | Clock | FQBN | Status |
|-------|-----|-------|------|--------|
| Arduino Uno R4 Minima | Renesas RA4M1 | 48 MHz | `arduino:renesas_uno:minima` | Supported |
| Arduino Uno R4 WiFi | RA4M1 + ESP32-S3 | 48 MHz | `arduino:renesas_uno:unor4wifi` | Supported |
| Arduino Due | SAM3X8E | 84 MHz | `arduino:sam:arduino_due_x` | Supported |
| Arduino Zero | SAMD21G18 | 48 MHz | `arduino:samd:arduino_zero_edbg` | Supported |
| Arduino Nano 33 IoT | SAMD21 + NINA-W102 | 48 MHz | `arduino:samd:nano_33_iot` | Supported |
| Arduino MKR WiFi 1010 | SAMD21 + NINA-W102 | 48 MHz | `arduino:samd:mkrwifi1010` | Supported |

### nRF52-Based

| Board | MCU | FQBN | Status |
|-------|-----|------|--------|
| Arduino Nano 33 BLE | nRF52840 | `arduino:mbed_nano:nano33ble` | Supported |

### RP2040-Based

| Board | MCU | FQBN | Status |
|-------|-----|------|--------|
| Arduino Nano RP2040 Connect | RP2040 + NINA-W102 | `arduino:mbed_nano:nanorp2040connect` | Supported |

### ESP32-Based

| Board | MCU | FQBN | Status |
|-------|-----|------|--------|
| Arduino Nano ESP32 | ESP32-S3 | `arduino:esp32:nano_nora` | Supported |

### Key Details

- **Arduino Nano old bootloader:** Some Nano clones use the old bootloader (57600 baud instead of 115200). OSmosis detects this automatically.
- **Leonardo/Micro auto-reset:** These boards use ATmega32U4 native USB. They reset automatically when the serial port is opened at 1200 baud — this is how the upload process works.
- **Uno R4 WiFi:** Has both a Renesas RA4M1 (main MCU) and an ESP32-S3 (WiFi/BT coprocessor). OSmosis flashes the RA4M1 by default.

---

## Espressif (ESP32 / ESP8266)

Espressif's chips are the most popular WiFi/BT microcontrollers. All are flashed via `esptool` over USB serial.

### ESP32 Family

| Board | Chip | Cores | Key Features | Status |
|-------|------|-------|-------------|--------|
| ESP32 DevKit v1 | ESP32 | 2x Xtensa LX6 | WiFi + BT Classic + BLE, 240 MHz | Supported |
| ESP32-S2 DevKit | ESP32-S2 | 1x Xtensa LX7 | WiFi only, native USB, 240 MHz | Supported |
| ESP32-S3 DevKit | ESP32-S3 | 2x Xtensa LX7 | WiFi + BLE, native USB, AI acceleration | Supported |
| ESP32-C3 DevKit | ESP32-C3 | 1x RISC-V | WiFi + BLE, 160 MHz | Supported |
| ESP32-C6 DevKit | ESP32-C6 | 1x RISC-V | WiFi 6 + BLE + Thread/Zigbee | Supported |
| ESP32-H2 DevKit | ESP32-H2 | 1x RISC-V | Thread/Zigbee only (no WiFi) | Supported |
| ESP32-C2 DevKit | ESP32-C2 | 1x RISC-V | WiFi + BLE, ultra-low-cost (also sold as ESP8684) | Supported |

### ESP8266

| Board | Chip | Key Features | Status |
|-------|------|-------------|--------|
| NodeMCU ESP8266 | ESP8266 | WiFi, CP2102 USB-UART | Supported |
| Wemos D1 Mini | ESP8266 | WiFi, CH340 USB-UART, compact | Supported |

### Choosing an ESP32 Variant

| Need | Recommended Chip |
|------|-----------------|
| General purpose WiFi + BLE | **ESP32** (classic) or **ESP32-S3** |
| AI / ML inference on-device | **ESP32-S3** (vector extensions) |
| Low cost, simple WiFi + BLE | **ESP32-C3** |
| WiFi 6 or Thread/Zigbee | **ESP32-C6** |
| Thread/Zigbee only (no WiFi) | **ESP32-H2** |
| Legacy projects | **ESP8266** (WiFi only, no BLE) |

### Key Details

- **esptool command:** `esptool.py --chip <chip> --port <port> write_flash 0x0 firmware.bin`
- **Boot mode:** Hold the BOOT button while pressing RESET to enter download mode. Many dev boards handle this automatically via USB-serial DTR/RTS.
- **USB-UART chip:** Classic ESP32 boards use CP2102 or CH340. Newer S2/S3/C3/C6 boards have native USB.
- **Partition table:** ESP32 firmware images often include a partition table, bootloader, and app binary. OSmosis handles this automatically.

---

## Raspberry Pi Pico (RP2040 / RP2350)

Raspberry Pi's microcontroller family. Flashed via UF2 drag-and-drop or `picotool`.

| Board | MCU | Key Features | Status |
|-------|-----|-------------|--------|
| Raspberry Pi Pico | RP2040 | Dual Cortex-M0+, 264 KB SRAM | Supported |
| Raspberry Pi Pico W | RP2040 + CYW43439 | WiFi + BT | Supported |
| Raspberry Pi Pico 2 | RP2350 | Dual Cortex-M33, security features | Supported |
| Raspberry Pi Pico 2 W | RP2350 + CYW43439 | WiFi + BT, Cortex-M33 | Supported |

### Key Details

- **UF2 bootloader:** Hold BOOTSEL while plugging in USB. The board appears as a USB drive. Drag a `.uf2` file onto it.
- **picotool:** Command-line alternative to drag-and-drop. OSmosis uses this.
- **PIO (Programmable I/O):** Unique to RP2040/RP2350. Hardware state machines that can implement custom protocols (SPI, I2S, WS2812, etc.)
- **RP2350 improvements:** Cortex-M33 (faster, with DSP and FPU), hardware security features (Secure Boot, ARM TrustZone).
- **MicroPython / CircuitPython:** Both supported. Flash the MicroPython/CircuitPython UF2, then copy Python scripts to the board.

---

## STM32 Boards

STM32 boards are flashed via ST-Link SWD programmer using `stflash` or `openocd`.

| Board | MCU | Clock | Key Features | Status |
|-------|-----|-------|-------------|--------|
| STM32 Blue Pill | STM32F103C8T6 | 72 MHz | Cheapest ARM board, 64 KB flash | Supported |
| STM32 Black Pill | STM32F411CEU6 | 100 MHz | USB, 512 KB flash | Supported |
| Nucleo-F401RE | STM32F401RE | 84 MHz | Integrated ST-Link | Supported |
| Nucleo-F446RE | STM32F446RE | 180 MHz | Integrated ST-Link, FPU | Supported |
| Nucleo-L476RG | STM32L476RG | 80 MHz | Low-power, integrated ST-Link | Supported |
| STM32F4 Discovery | STM32F407VGT6 | 168 MHz | Accelerometer, audio, USB | Supported |

### Key Details

- **Flash command:** `st-flash write firmware.bin 0x08000000`
- **Blue Pill clones:** Many cheap Blue Pills have 128 KB flash (instead of 64 KB) despite the datasheet. Some have CKS32 clones instead of genuine STM32.
- **Nucleo boards:** Include an integrated ST-Link debugger — no external programmer needed. Just plug in USB.
- **STM32CubeIDE:** STMicroelectronics' official IDE. OSmosis can flash binaries generated by CubeIDE or any other toolchain.

---

## Teensy Boards

Teensy boards from PJRC are high-performance ARM boards popular for audio, USB HID, and real-time applications.

| Board | MCU | Clock | Key Features | Status |
|-------|-----|-------|-------------|--------|
| Teensy 4.0 | i.MX RT1062 | 600 MHz | Fastest hobbyist MCU, USB | Supported |
| Teensy 4.1 | i.MX RT1062 | 600 MHz | Ethernet, SD card, extra pins | Supported |
| Teensy 3.6 | MK66FX1M0 | 180 MHz | FPU, USB host, SD card | Supported |

### Key Details

- **600 MHz:** Teensy 4.0/4.1 run at 600 MHz — faster than most SBCs' CPUs.
- **Teensy Loader:** Upload via `teensy_loader_cli` or the Teensy Loader GUI.
- **Audio library:** Teensy has a powerful audio synthesis/processing library. Popular for synths and effects.
- **USB:** Can emulate any USB device (HID, MIDI, serial, mass storage, raw HID).

---

## Adafruit Boards

Adafruit's boards are designed for education and rapid prototyping, with excellent documentation and CircuitPython support.

| Board | MCU | Key Features | Flash Tool | Status |
|-------|-----|-------------|-----------|--------|
| Feather M0 | SAMD21G18 | WiFi/BLE variants available | arduino-cli | Supported |
| Feather M4 | SAMD51J19 | 120 MHz, USB, CircuitPython | arduino-cli | Supported |
| Feather RP2040 | RP2040 | Feather form factor, Stemma QT | picotool | Supported |
| QT Py ESP32-S3 | ESP32-S3 | Tiny, Stemma QT, WiFi/BLE | esptool | Supported |
| Trinkey QT2040 | RP2040 | USB key form factor, Stemma QT | picotool | Supported |

### Key Details

- **Feather ecosystem:** Standardized form factor with stackable "Wings" (add-on boards) for displays, sensors, motor drivers, etc.
- **CircuitPython:** Adafruit's Python fork for microcontrollers. Flash the CircuitPython UF2, then edit `code.py` on the USB drive.
- **Stemma QT:** I2C connector standard (compatible with Qwiic) for plug-and-play sensors.

---

## Seeed Studio Boards

Seeed's XIAO series are ultra-compact boards (21x17mm) with surprising capability.

| Board | MCU | Key Features | Flash Tool | Status |
|-------|-----|-------------|-----------|--------|
| XIAO ESP32S3 | ESP32-S3 | WiFi/BLE, tiny, camera support | esptool | Supported |
| XIAO RP2040 | RP2040 | Tiny, USB-C, 264 KB SRAM | picotool | Supported |
| XIAO nRF52840 | nRF52840 | BLE, ultra-low power | arduino-cli | Supported |

---

## LILYGO Boards

LILYGO specializes in ESP32 boards with built-in displays and LoRa radios. Popular for Meshtastic.

| Board | MCU | Key Features | Flash Tool | Status |
|-------|-----|-------------|-----------|--------|
| T-Display | ESP32 | 1.14" TFT display | esptool | Supported |
| T-Display S3 | ESP32-S3 | 1.9" touch TFT | esptool | Supported |
| T-Beam | ESP32 + SX1276 | LoRa + GPS, Meshtastic | esptool | Supported |
| T-Beam Supreme S3 | ESP32-S3 + SX1262 | LoRa + GPS, Meshtastic | esptool | Supported |
| T-Echo | nRF52840 + SX1262 | E-ink + LoRa, Meshtastic | arduino-cli | Supported |

---

## M5Stack Boards

M5Stack produces integrated ESP32 development kits with screens, speakers, IMUs, and cases.

| Board | MCU | Key Features | Flash Tool | Status |
|-------|-----|-------------|-----------|--------|
| M5Stack Core2 | ESP32 | 2" touch LCD, IMU, speaker | esptool | Supported |
| M5Stack CoreS3 | ESP32-S3 | 2" touch LCD, camera | esptool | Supported |
| ATOM Lite | ESP32-Pico | Tiny (24x24mm), RGB LED | esptool | Supported |
| AtomS3 | ESP32-S3 | 0.85" LCD, tiny | esptool | Supported |
| M5Stamp C3 | ESP32-C3 | Stamp form factor | esptool | Supported |

---

## LoRa / Meshtastic Boards

These boards combine a microcontroller with a LoRa radio for long-range mesh networking. Popular with the Meshtastic project.

| Board | MCU | Radio | Key Features | Flash Tool | Status |
|-------|-----|-------|-------------|-----------|--------|
| Heltec WiFi LoRa 32 V3 | ESP32-S3 | SX1262 | OLED display | esptool | Supported |
| Heltec Wireless Tracker | ESP32-S3 | SX1262 | GPS + TFT display | esptool | Supported |
| RAK WisBlock 4631 | nRF52840 | SX1262 | Modular, low power | arduino-cli | Supported |
| RAK WisBlock 11200 | nRF52840 | SX1262 | GPS tracker variant | arduino-cli | Supported |

### Meshtastic

[Meshtastic](https://meshtastic.org/) is an open-source mesh networking project that runs on these boards. It provides:
- Long-range text messaging (several km without line of sight)
- GPS position sharing
- Encrypted communications
- No cellular or WiFi infrastructure needed
- OSmosis can flash Meshtastic firmware to any supported board

---

## 3D Printer MCU Boards

These STM32-based boards run 3D printer firmware (Klipper or Marlin). OSmosis can flash compiled firmware binaries.

| Board | MCU | Key Features | Flash Tool | Status |
|-------|-----|-------------|-----------|--------|
| BTT SKR Mini E3 V3 | STM32G0B1 | Popular Ender 3 upgrade | stflash | Supported |
| BTT Octopus V1.1 | STM32F446 | 8 stepper drivers | stflash | Supported |
| BTT Manta M8P | STM32G0B1 | CB1 compute module compatible | stflash | Supported |
| Creality 4.2.7 Board | STM32F103 | Stock Ender 3 V2 board | stflash | Supported |

### Key Details

- **Klipper:** Runs the real-time motion control on the MCU and the higher-level logic on a host (Raspberry Pi). OSmosis flashes the MCU firmware.
- **Marlin:** Standalone firmware that runs entirely on the MCU. Compiled from source using PlatformIO.
- **SD card flashing:** Some boards also support placing `firmware.bin` on an SD card and rebooting. OSmosis supports both methods.

---

## Flight Controllers

These STM32-based boards run Betaflight or iNav for drone flight control.

| Board | MCU | Key Features | Flash Tool | Status |
|-------|-----|-------------|-----------|--------|
| SpeedyBee F405 V4 | STM32F405 | Betaflight/iNav, barometer | dfu-util | Supported |
| Matek H743-SLIM | STM32H743 | Betaflight/iNav/ArduPilot, high-perf | dfu-util | Supported |

### Key Details

- **DFU mode:** Bridge the boot pads (or press the boot button) and connect USB. The board appears as a DFU device.
- **Betaflight Configurator:** Desktop app for configuring flight parameters. OSmosis handles the firmware flash; configuration is done in Betaflight Configurator.

---

## SDR Dongles

Software-Defined Radio dongles for receiving (and in some cases transmitting) radio signals.

| Device | Chipset | Frequency Range | Flash Tool | Status |
|--------|---------|----------------|-----------|--------|
| RTL-SDR Blog V3 | RTL2832U + R820T2 | 500 kHz - 1.7 GHz | rtl_sdr | Supported |
| RTL-SDR Blog V4 | RTL2832U + R828D | 500 kHz - 1.7 GHz | rtl_sdr | Supported |
| HackRF One | LPC4320 | 1 MHz - 6 GHz | hackrf_spiflash | Supported |

### Key Details

- **RTL-SDR:** Receive-only. Used for ADS-B (aircraft tracking), FM radio, weather satellites, amateur radio, and more.
- **HackRF One:** Half-duplex TX/RX. Can transmit on any frequency from 1 MHz to 6 GHz (with appropriate licensing).
- **Firmware updates:** RTL-SDR dongles rarely need firmware updates. HackRF One firmware can be updated via `hackrf_spiflash`.

---

## USB Identification

OSmosis uses USB Vendor ID (VID) and Product ID (PID) to auto-detect connected boards:

| VID | PID | Board(s) |
|-----|-----|----------|
| `2341` | `0043` | Arduino Uno |
| `2341` | `0042` | Arduino Mega 2560 |
| `2341` | `0069` | Arduino Uno R4 Minima |
| `2341` | `1002` | Arduino Uno R4 WiFi |
| `2E8A` | `0003` | Raspberry Pi Pico / Pico W |
| `2E8A` | `000F` | Raspberry Pi Pico 2 / Pico 2 W |
| `10C4` | `EA60` | CP2102 USB-UART (ESP32, many boards) |
| `1A86` | `7523` | CH340 USB-UART (Wemos D1 Mini, clones) |
| `303A` | `0002` | ESP32-S2 (native USB) |
| `303A` | `1001` | ESP32-S3/C3/C6/H2/C2 (native USB) |
| `0483` | `3748` | ST-Link V2 (STM32 boards) |
| `0483` | `374B` | ST-Link V2-1 (Nucleo boards) |
| `0483` | `DF11` | STM32 DFU mode (flight controllers) |
| `16C0` | `0478` | Teensy |
| `239A` | various | Adafruit boards |
| `2886` | `8029` | Seeed XIAO nRF52840 |
| `0D28` | `0204` | BBC micro:bit |
| `0BDA` | `2838` | RTL-SDR |
| `1D50` | `6089` | HackRF One |
