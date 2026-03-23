# Synthesizers & Audio

OSmosis documents open-source firmware and alternative firmware options for synthesizer modules, effects processors, and audio hardware. This category ranges from fully open-source Eurorack modules (where alternate firmware is a design goal) to commercial instruments with official open SDKs.

---

## Support Levels

| Level | Meaning |
|-------|---------|
| **Supported** | Open-source firmware available and well-documented. Community-tested flash procedure. |
| **Planned** | OSmosis wizard in development. Tools exist today for manual flashing. |
| **Research** | Community modifications documented but limited, incomplete, or hardware-specific. |
| **Not supported** | Proprietary. No open firmware. Listed for awareness. |

---

## Mutable Instruments Eurorack Modules

[Mutable Instruments](https://mutable-instruments.net/) (MI) published the full hardware and software source code for all of their Eurorack modules before closing in 2022. This means:

- Official firmware is open source (MIT/CC-BY-SA licensed)
- Community alternate firmware (e.g. Parasites, Supercell, Dead Man's Catch) exists for many modules
- Flash method is an audio bootloader: a WAV file played into the module's audio input

### Flash Method: Audio Bootloader

All Mutable Instruments modules with firmware support the same WAV-based bootloader:

1. Enter bootloader mode by holding a specific button combination while powering on (module-specific).
2. Connect a 3.5mm cable from your audio interface or phone to the module's audio input.
3. Play the firmware WAV file at full volume (0 dBFS) with no processing.
4. The module flashes itself from the incoming audio signal, then reboots.

No programmer hardware is needed. The process takes 30–90 seconds.

### Supported Modules

| Module | Function | Alt Firmware | Status | Notes |
|--------|---------|-------------|--------|-------|
| Plaits | Macro oscillator | [Dead Man's Catch](https://github.com/NickBuryak/miRack), community patches | Supported | 16 synthesis engines. Alt firmware adds extra modes. |
| Braids (discontinued) | Macro oscillator | [Braids alt firmware](https://github.com/timchurches/Mutated-Mutables) | Supported | Original macro oscillator. Many alt firmware variants. |
| Clouds | Granular processor | [Parasites](https://mqtthiqs.github.io/parasites/clouds.html), [Supercell](https://www.parasiticdesign.com/supercell) | Supported | Most popular alt firmware target. Parasites adds Oliverb, Kammerl Beat, etc. |
| Rings | Resonator | [Rings alt firmware](https://github.com/timchurches/Mutated-Mutables) | Supported | Physical modelling resonator. |
| Beads | Granular processor | Community patches | Supported | Spiritual successor to Clouds. |
| Marbles | Random sampler | Community patches | Supported | Random gates and voltages. |
| Stages | Segment generator | [Stages alt firmware](https://github.com/qiemem/stages) | Supported | Alt firmware adds harmonic oscillator mode. |
| Tides | Function generator | Parasites (Tides) | Supported | |
| Warps | Wavefolder/modulator | Parasites (Warps) | Supported | Parasites adds BEES-IN-THE-TREES and other modes. |
| Elements | Modal synthesizer | Community patches | Supported | Full physical model. |
| Peaks | Utility module | [Dead Man's Catch (Peaks)](https://mqtthiqs.github.io/parasites/peaks.html) | Supported | |

### Key Details

- **Official source code:** All MI module source is on [GitHub (pichenettes)](https://github.com/pichenettes).
- **WAV files:** Firmware WAV files are typically included in each project's releases. Use at 48kHz, 16-bit minimum. Do not transcode or re-encode.
- **Eurorack clones:** Many manufacturers (e.g. Instruo, Tall Dog) produce licensed or clone MI modules. Most accept the same firmware. Some clones have different MCUs and require different firmware builds.
- **MI hardware is no longer manufactured** by Mutable Instruments. The designs are open, and several manufacturers sell licensed clones.

---

## Korg logue SDK

Korg published an official open SDK for their logue platform synthesizers. This allows users to develop and install custom oscillators and effects directly from Korg's own development tools — no jailbreak required.

### Supported Devices

| Device | Type | SDK Support | Status |
|--------|------|------------|--------|
| Korg NTS-1 | Desktop synthesizer | Full oscillator + effect SDK | Planned |
| Korg Minilogue XD | Polyphonic synthesizer | User oscillator + effect slots | Planned |
| Korg Prologue | Polyphonic synthesizer | User oscillator + effect slots | Planned |

### What the logue SDK Provides

- **Custom oscillators:** Replace any of the built-in oscillator slots with your own C/C++ DSP code.
- **Custom effects:** Write modulation, reverb, and delay effects.
- **Official tools:** Korg provides the `logue-sdk` toolchain and a `logue-unit` package manager.
- **Patch management:** Custom units are loaded via Korg's official Librarian software or the device's USB MIDI interface.

### Key Details

- **No firmware replacement:** The logue SDK loads code *into* the stock firmware's user slots. The underlying OS is not replaced.
- **Official Korg support:** This is an officially sanctioned platform. Using the SDK does not void warranties.
- **NTS-1 MK2:** The second-generation NTS-1 uses a different SDK version. Some MK1 units are not cross-compatible.

---

## MOD Audio (MOD Dwarf / MOD Duo)

[MOD Audio](https://mod.audio/) devices run a full Debian Linux distribution and support [LV2 plugins](https://lv2plug.in/). These are the most open commercial audio processors available.

| Device | OS | Plugin Format | Status |
|--------|-----|-------------|--------|
| MOD Dwarf | Debian Linux (armhf) | LV2 | Planned |
| MOD Duo | Debian Linux (armhf) | LV2 | Planned |
| MOD Duo X | Debian Linux (armhf) | LV2 | Planned |

### What MOD Provides

- **Full Linux access:** SSH into the device, install Debian packages, run scripts.
- **LV2 plugin ecosystem:** Install any LV2 plugin that compiles for ARM. Thousands of free plugins are pre-packaged in MOD's plugin store.
- **Web-based patchbay:** Configure signal routing, chaining, and parameter mapping from a browser.
- **MIDI:** Full MIDI I/O, MIDI learn, expression pedal mapping.

### Key Details

- **Not firmware flashing in the traditional sense:** MOD devices are already open. Accessing their Linux shell is a supported, documented feature.
- **Plugin installation:** Use the MOD web interface or SSH to install plugins. MOD provides a curated plugin store; you can also compile your own LV2 plugins.
- **Snapshots:** MOD's preset system saves entire signal chains ("pedalboards") including plugin settings and routing.

---

## Teenage Engineering OP-1

The Teenage Engineering OP-1 is a closed-source portable synthesizer/sampler. The main community tool is `op1repacker`, which allows patching the official firmware.

| Device | Tool | What It Does | Status |
|--------|------|-------------|--------|
| OP-1 (original) | [op1repacker](https://github.com/op1hacks/op1repacker) | Patches official firmware to enable hidden features | Research |
| OP-1 Field | — | Newer secure firmware. op1repacker not compatible. | Not supported |

### What op1repacker Provides

op1repacker modifies the official OP-1 firmware `.op1` package to enable:

- Disabled synthesis engines and effects (CWO, Dr. Wave, GRID)
- Disabled LFO shapes
- Modified sequencer modes

**op1repacker does not replace the firmware** — it patches the official firmware image before loading it onto the device via USB mass storage. The OP-1 mounts as a USB drive; the patched `.op1` file is dropped into the `tape` folder.

### Key Details

- **OP-1 Field:** Teenage Engineering hardened the Field with a secure bootloader and signature verification. op1repacker does not work on it.
- **Community source:** [op1hacks GitHub organization](https://github.com/op1hacks) hosts op1repacker and related tools.

---

## Zoom Pedals

Zoom multi-effects pedals use a proprietary firmware format. The community [Zoom Firmware Editor](https://github.com/Zoom-Firmware-Editor) project allows inspecting and modifying firmware images.

| Device | Tool | Status | Notes |
|--------|------|--------|-------|
| Zoom MS-50G | Zoom Firmware Editor | Research | Effect parameter unlocks, DSP modifications |
| Zoom MS-70CDR | Zoom Firmware Editor | Research | |
| Zoom G1 Four / G1X Four | Zoom Firmware Editor | Research | |
| Zoom B1 Four / B1X Four | Zoom Firmware Editor | Research | |

### Key Details

- The Zoom Firmware Editor is a reverse-engineered tool. Stability varies by model and firmware version.
- Modifications are typically effect parameter unlocks (raising limits, enabling hidden effect combinations) rather than full firmware replacements.
- Flash via Zoom's official update tool using the modified firmware file.

---

## Not Supported

| Brand | Reason |
|-------|--------|
| Line 6 (Helix, HX Stomp, POD Go) | Encrypted firmware, no open tooling |
| Elektron (Digitakt, Digitone, Octatrack) | Proprietary OS, no community firmware |
| Roland (Boutique series, MC-707) | Encrypted firmware |
| Native Instruments (Maschine hardware) | Host-dependent, no standalone firmware target |
| Novation (Circuit, Launchpad Pro) | Some community research, no firmware replacement |

---

## General Notes

### Eurorack Safety

Eurorack modules use ±12V and +5V power rails. Audio bootloaders are safe to use but:

- Use a proper 3.5mm audio cable — not a splitter or cheaply shielded cable
- Play the WAV file at 0 dBFS without any limiting, compression, or EQ on the playback chain
- If the flash fails partway through, retry from the beginning; the bootloader is robust

### MI Alt Firmware Catalogue

A community-maintained catalogue of MI alternative firmware is available at the links below. It covers every module and lists every known alt firmware variant with descriptions.

---

## Links

| Resource | URL |
|---------|-----|
| Mutable Instruments source code (pichenettes) | https://github.com/pichenettes |
| MI alt firmware catalogue | https://github.com/v7b1/mi-UGens (and linked resources) |
| Parasites alt firmware (Clouds, Warps, Peaks, Tides) | https://mqtthiqs.github.io/parasites/ |
| Supercell (Clouds alt firmware) | https://www.parasiticdesign.com/supercell |
| Korg logue SDK | https://github.com/korginc/logue-sdk |
| MOD Audio | https://mod.audio/ |
| MOD Audio developer documentation | https://wiki.mod.audio/ |
| op1repacker | https://github.com/op1hacks/op1repacker |
| Zoom Firmware Editor | https://github.com/Zoom-Firmware-Editor |
