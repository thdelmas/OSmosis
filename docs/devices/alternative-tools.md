# Alternative & Repurposing Tools

When a device is too damaged, locked down, or obsolete to bring back to life with a firmware flash, these tools offer a second path: repurpose the hardware, harvest useful components, or replace the device with a dedicated hacking/tinkering platform.

## Multi-Tool Devices

| Device | Description | Use Cases |
|--------|-------------|-----------|
| **Flipper Zero** | Portable multi-tool for pentesters and tinkerers. Sub-GHz radio, NFC, RFID, infrared, iButton, GPIO, USB HID. | Read/clone access cards and remotes from dead devices, emulate IR remotes, interact with UART/SPI/I2C on salvaged boards |
| **HackRF One** | Wideband SDR transceiver (1 MHz - 6 GHz). | Analyze RF protocols from old IoT devices, replay signals, reverse-engineer proprietary wireless comms |
| **USB Rubber Ducky** | USB keystroke injection tool. | Automate firmware recovery sequences, script complex bootloader key combos |
| **Bus Pirate** | Universal bus interface (UART, SPI, I2C, JTAG, 1-Wire). | Debug and dump firmware from dead boards, read flash chips directly, bootstrap bricked microcontrollers |
| **CH341A Programmer** | Cheap SPI/I2C flash programmer. | Read/write BIOS chips from dead laptops, dump firmware from routers and IoT devices for analysis |

## Salvage & Component Harvesting

When a device is truly dead, individual components can still be valuable:

| Component | Where to Find It | Second Life |
|-----------|-------------------|-------------|
| **Flash/eMMC chips** | Phones, tablets, SBCs | Read with CH341A or Bus Pirate for data recovery; reuse in DIY projects |
| **Screens/displays** | Phones, tablets, laptops | Drive with Arduino/ESP32 + display controller board |
| **Batteries** | Phones, scooters, e-bikes | Reuse in power banks, solar setups, or DIY battery packs (with proper BMS) |
| **Motors & ESCs** | Scooters, e-bikes | Robotics projects, custom electric vehicles |
| **Sensors** | Phones, IoT devices | Accelerometers, gyroscopes, and barometers for microcontroller projects |

## Microcontroller Alternatives

If the original device's brain is dead but the body is fine, a microcontroller can sometimes take over:

| Scenario | Replacement | Notes |
|----------|-------------|-------|
| Dead scooter controller | **VESC** or **STM32 + custom firmware** | Open-source motor controller; community firmware available for many scooter motors |
| Dead e-bike display/controller | **Bafang open firmware** or **TSDZ2 OSF** | Replace locked controller with open alternative |
| Dead IoT hub / smart home device | **ESP32 + ESPHome** or **RPi + Home Assistant** | Replace proprietary cloud-dependent hardware with local-first open alternative |
| Dead handheld / portable console | **RPi Zero 2W + RetroPie** | Reuse the screen, buttons, and shell with a new brain |
| Dead laptop (beyond BIOS recovery) | **Raspberry Pi 5 + Pi-Top** or **Framework mainboard swap** | Reuse peripherals around a new compute module |

## Flipper Zero + OSmosis

Flipper Zero is especially relevant to OSmosis users because it can:

- **Read NFC/RFID from dead devices** to clone credentials before disposal
- **Capture IR codes** from remotes whose base station died, so you can replay them with a new hub
- **Act as a UART bridge** to talk to scooter/e-bike controllers, similar to OSmosis's serial flash workflow
- **Sub-GHz capture** of keyfobs and sensors for devices that can't be re-paired after a controller swap
- **GPIO breakout** for directly probing SWD/JTAG on boards that won't boot, as a lighter alternative to a full Bus Pirate setup

## When to Repair vs. Replace vs. Repurpose

| Signal | Recommendation |
|--------|---------------|
| Device boots but firmware is corrupt or locked | **Repair** -- try OSmosis flash workflow first |
| Device won't boot, known hardware failure (e.g. dead eMMC) | **Repurpose** -- swap the failed component or replace the brain |
| Device is physically intact but manufacturer-abandoned (no updates, cloud shutdown) | **Replace firmware** -- flash open-source alternative via OSmosis |
| Device is physically damaged beyond board-level repair | **Harvest** -- salvage components for other projects |
| Device category has no open firmware at all | **Replace** -- consider an open alternative from the start (e.g. Flipper Zero instead of proprietary RF tool) |
