# Lab & Test Equipment

OSmosis documents firmware modifications, unlock procedures, and open-source driver options for oscilloscopes, signal generators, spectrum analyzers, and logic analyzers. Most entries involve either SCPI command unlocks (no reflash required) or open-source USB drivers for clone hardware.

**Important:** Modifying firmware on precision instruments can affect calibration data. Before making any changes, back up calibration constants if your instrument stores them in user-accessible flash. Recalibration after a firmware change may require professional equipment.

---

## Support Levels

| Level | Meaning |
|-------|---------|
| **Research** | Procedure documented. OSmosis does not yet provide an automated wizard for this category. |
| **Planned** | OSmosis intends to add wizard support. Community tooling exists. |
| **Not supported** | Listed for awareness. No open firmware or unlock path available. |

---

## Rigol

Rigol oscilloscopes are the most popular targets for software-based unlocking. Several models store option license keys that can be generated or obtained to enable bandwidth and feature upgrades.

### DS1054Z

| Feature | Default | Unlocked |
|---------|---------|---------|
| Bandwidth | 50 MHz | 100 MHz |
| Channels | 4 | 4 |
| Memory depth | 12 Mpts | 12 Mpts |
| Serial decode (I2C, SPI, UART) | Disabled | Enabled |
| Advanced math | Disabled | Enabled |

| Device | Unlock Method | Status |
|--------|--------------|--------|
| Rigol DS1054Z | SCPI key command via USB or LAN | Research |

**Unlock procedure:**

1. Connect to the DS1054Z via USB-TMC or LAN.
2. Use a SCPI terminal (e.g., `python-usbtmc`, Rigol's UltraSigma, or any SCPI-capable tool).
3. Query the instrument ID: `:*IDN?`
4. Send the unlock key using: `:SYST:OPT:INST <key_string>`
5. The 100 MHz bandwidth and software options activate immediately without reboot on most firmware versions.

Keys have been published in the community. The instrument performs no online validation — the key is checked locally against the serial number.

### MSO5000 Series

| Device | Access Method | Status |
|--------|--------------|--------|
| Rigol MSO5000 | SSH root via LAN | Research |

The MSO5000 runs an embedded Linux system. The root password for the SSH service is known to the community and does not require any firmware modification to use. Once logged in, users have full filesystem access and can:

- Enable disabled bandwidth options by modifying license files
- Access raw calibration data
- Install additional tools

**Note:** The SSH root access is a factory/debug feature that Rigol has not patched in current firmware. This may change in future firmware updates.

---

## Siglent

Siglent instruments use a license key system similar to Rigol. Keys are delivered via SCPI commands and unlock bandwidth tiers, channel counts, and software options.

### Oscilloscopes (SDS Series)

| Device | Unlock Type | What It Unlocks | Status |
|--------|------------|----------------|--------|
| Siglent SDS1104X-E | SCPI license key | 100 MHz → 200 MHz bandwidth | Research |
| Siglent SDS1204X-E | SCPI license key | Additional decode options | Research |
| Siglent SDS2000X Plus | SCPI license key | Bandwidth tiers, serial decode | Research |

### Signal Generators (SDG Series)

| Device | Unlock Type | What It Unlocks | Status |
|--------|------------|----------------|--------|
| Siglent SDG1032X | SCPI license key | Frequency range extension | Research |
| Siglent SDG2042X | SCPI license key | IQ modulation option | Research |

### Spectrum Analyzers (SSA/SVA Series)

| Device | Unlock Type | What It Unlocks | Status |
|--------|------------|----------------|--------|
| Siglent SSA3021X | SCPI license key | Tracking generator, EMC presets | Research |
| Siglent SVA1015X | SCPI license key | VNA mode, cable/antenna analysis | Research |

**General Siglent procedure:**

1. Connect via USB or LAN.
2. Open a SCPI terminal.
3. Query: `*IDN?` to confirm connection.
4. Send: `SYST:OPT:INST <option_string>` with the appropriate key.

Community-sourced keys and keygen tools exist for most of these models. See the EEVblog forums for model-specific threads.

---

## Hantek 6022BE and FX2-Based Logic Analyzers

The Hantek 6022BE is a low-cost USB oscilloscope based on the Cypress FX2LP USB microcontroller. The same FX2LP chip is used in many low-cost Saleae Logic clone analyzers sold on AliExpress.

### FX2LP-Based Devices

| Device | Chip | Open Driver | Status |
|--------|------|------------|--------|
| Hantek 6022BE | Cypress FX2LP | [fx2lafw](https://sigrok.org/wiki/Fx2lafw) + sigrok | Planned |
| Saleae Logic clone (24MHz, 8ch) | Cypress FX2LP | fx2lafw + sigrok | Planned |
| Saleae Logic clone (100MHz, 16ch) | Cypress FX2LP | fx2lafw + sigrok | Planned |
| Generic "USB Logic Analyzer" clones | Cypress FX2LP | fx2lafw + sigrok | Planned |

### How fx2lafw Works

[fx2lafw](https://sigrok.org/wiki/Fx2lafw) is an open-source firmware for Cypress FX2LP chips. When you plug in a Hantek or Saleae clone:

1. The device presents as a USB device running the stock vendor firmware.
2. sigrok (via `libsigrok`) uploads the fx2lafw firmware to the device's RAM over USB — the FX2LP supports this without soldering.
3. The device re-enumerates as a sigrok-compatible logic analyzer.
4. You use PulseView (sigrok's GUI) or `sigrok-cli` for captures.

**The firmware upload is RAM-only** — it does not modify the device's flash. Every time you plug in the device, sigrok uploads fx2lafw fresh.

### What sigrok/PulseView Provides

- Protocol decoders for 100+ protocols (UART, SPI, I2C, 1-Wire, CAN, USB, PS/2, and more)
- Trigger support
- Export to CSV, VCD, and other formats
- Linux, Windows, macOS support

---

## Fnirsi

Fnirsi makes low-cost handheld oscilloscopes and multimeters built on STM32 microcontrollers. Community members have developed binary patches for some models.

| Device | MCU | Modification | Status |
|--------|-----|-------------|--------|
| Fnirsi 1013D | STM32 | Binary patch to enable additional timebase options | Research |
| Fnirsi 5012H | STM32 | Community-patched firmware for bug fixes | Research |
| Fnirsi DSO152 | STM32 | Open alternative firmware in development | Research |

### Key Details

- **Binary patching:** Fnirsi does not release source code. Community modifications are binary patches applied to the official firmware image using a hex editor or patch tool.
- **Flash method:** Fnirsi handhelds typically expose a DFU or USB mass storage bootloader. The patched `.bin` file is loaded via the manufacturer's update utility or direct DFU.
- **Risk:** Binary patches can desync with new official firmware versions. Always patch the specific firmware version the patch was written for.

---

## General Notes

### SCPI Connection Tools

| Tool | Platform | Use |
|------|---------|-----|
| `python-usbtmc` | Linux/macOS/Windows | USB-TMC SCPI from Python scripts |
| `python-vxi11` | Linux/macOS/Windows | LAN-based SCPI (VXI-11 protocol) |
| Rigol UltraSigma | Windows | Official Rigol SCPI terminal |
| `scpi-cli` | Linux | Lightweight command-line SCPI tool |
| PulseView / sigrok-cli | All | sigrok capture and analysis frontend |

### Calibration Warning

SCPI-based unlocks (Rigol, Siglent) do not touch calibration data — they only flip option flags. SSH-based modifications (Rigol MSO5000) can modify any file on the system, including calibration constants. Exercise caution.

### Legal Note

Unlocking paid software options that you have not licensed may violate the manufacturer's terms of service or end-user license agreement. Research the legal situation in your jurisdiction before proceeding.

---

## Links

| Resource | URL |
|---------|-----|
| sigrok project | https://sigrok.org/ |
| fx2lafw firmware | https://sigrok.org/wiki/Fx2lafw |
| PulseView (sigrok GUI) | https://sigrok.org/wiki/PulseView |
| EEVblog forum (Rigol/Siglent unlock threads) | https://www.eevblog.com/forum/ |
| python-usbtmc | https://github.com/python-ivi/python-usbtmc |
