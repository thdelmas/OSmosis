<p align="center">
  <img src="frontend/public/logo.png" alt="OSmosis logo" width="180" />
</p>

# OSmosis

**Install any OS on any device.** CLI and web UI.

OSmosis gives you real ownership of your hardware. Your device, your choice of operating system. Whether you're installing a privacy OS on a phone, reviving an old tablet, or escaping a locked-down ecosystem — OSmosis handles the flashing, you make the choices.

## Quick start

```bash
git clone https://github.com/thdelmas/OSmosis.git ~/OSmosis || true \
  && cd ~/OSmosis \
  && git pull --recurse-submodules \
  && make install \
  && make serve
```

Plug in your device via USB. OSmosis detects it and walks you through the rest.

> **Requirements:** Python 3.10+, Node.js, a USB data cable. Linux recommended, macOS works, Windows via WSL2. See [detailed requirements](#requirements) below.

## What can I flash?

OSmosis supports **phones, tablets, SBCs, scooters, routers, microcontrollers**, and more. Here are the most common:

| Device | What you can install | Status |
|--------|---------------------|--------|
| Samsung Galaxy | LineageOS, /e/OS, LETHE, CalyxOS | **Supported** |
| Google Pixel | GrapheneOS, CalyxOS, LineageOS, LETHE | **Supported** |
| OnePlus / Xiaomi / Fairphone / Motorola / Sony / Nothing | LineageOS, /e/OS, LETHE | **Supported** |
| PinePhone / Librem 5 | PostmarketOS, Mobian, UBports | **Supported** |
| Raspberry Pi & SBCs | Ubuntu, DietPi, Home Assistant | **Supported** |
| Electric scooters (Ninebot, Xiaomi) | Custom firmware via BLE/ST-Link | **Supported** |
| Routers | OpenWrt, DD-WRT | **Supported** |

See the **[full device catalog](docs/devices/SUPPORTED.md)** for 200+ device types including laptops, game consoles, e-readers, cameras, lab equipment, and more.

## Looking for LETHE?

**[LETHE](lethe/)** is a privacy-first OS that runs on your existing phone — no new hardware needed. It bundles financial protection ([PreuJust](lethe/)), health data guardianship ([Bios](lethe/)), and an on-device AI companion, all designed to give you back control of your digital life.

**Install LETHE with OSmosis:**

```bash
# 1. Set up OSmosis (quick start above), then:
make serve
# 2. Plug in your phone via USB
# 3. Select "LETHE" from the OS list when prompted
```

LETHE works on Samsung Galaxy, Google Pixel, OnePlus, Xiaomi, Fairphone, Motorola, Sony, and Nothing phones. See the [LETHE documentation](lethe/) for details.

[![Discord](https://img.shields.io/badge/Discord-LETHE%20community-5865F2?logo=discord&logoColor=white)](https://discord.gg/s6gJBsHqgf)

## Community

[![Discord](https://img.shields.io/badge/Discord-Join%20us-5865F2?logo=discord&logoColor=white)](https://discord.gg/vWqxwvRpJe)

## Usage

### Web UI (recommended)

```bash
make serve
# Opens http://localhost:5000
```

The web UI detects your device, shows compatible OS options, and guides you through flashing with real-time progress and physical button instructions.

### CLI

```bash
./osmosis.sh            # interactive menu
./osmosis.sh --dry-run  # preview commands without executing
./osmosis.sh --help     # show help
```

## Features

- **Auto-detect** connected devices via USB
- **Pre-flight checks** — battery level, backup status, storage space
- **Guided flashing** — step-by-step with physical button instructions and countdown timers
- **Backup & restore** — partition backups before flashing
- **ROM downloads** — built-in firmware registry with SHA256 verification
- **Scooter support** — BLE scan, firmware flash, ST-Link recovery
- **OS Builder** — build custom Debian, Arch, Fedora, NixOS, or Alpine images
- **IPFS distribution** — decentralized firmware hosting and pinning

## Requirements

```bash
# Core
sudo apt install -y heimdall-flash adb unzip wget

# Optional
sudo apt install -y lz4 curl python3 python3-venv

# Scooter flashing (BLE)
pip install --user bleak

# Scooter flashing (ST-Link)
sudo apt install -y stlink-tools
```

## Data directories

| Path | Contents |
|------|----------|
| `~/.osmosis/logs/` | Session logs |
| `~/.osmosis/backups/` | Partition backups |
| `~/Osmosis-downloads/` | Downloaded ROMs and firmware |

## Project structure

| Path | What it does |
|------|-------------|
| `osmosis.sh` | CLI wizard |
| `osmosis-web.sh` | Web UI launcher |
| `web/` | Flask backend |
| `frontend/` | Vue 3 frontend |
| `profiles/` | Device profiles (YAML) |
| `lethe/` | LETHE privacy OS overlay |
| `docs/` | Device docs, guides, research |

## Support the project

OSmosis is free, open source, and not monetized. If it's useful to you, consider supporting the work:

- 💛 [**theophile.world/sponsor**](https://theophile.world/sponsor) — tip jar or recurring support.
- ⭐ Star the repo and share it with someone who'd benefit.
- 🐛 [Open an issue](https://github.com/thdelmas/OSmosis/issues) or [join the Discord](https://discord.gg/vWqxwvRpJe).

## Credits

OSmosis wraps and integrates upstream tools — the real work happens in the communities we depend on. See [CREDITS.md](docs/CREDITS.md) for the full list, including:

- [Heimdall](https://github.com/Benjamin-Dobell/Heimdall), [fastboot/adb](https://developer.android.com/tools), [Magisk](https://github.com/topjohnwu/Magisk)
- [LineageOS](https://lineageos.org/), [GrapheneOS](https://grapheneos.org/), [CalyxOS](https://calyxos.org/), [/e/OS](https://e.foundation/), [PostmarketOS](https://postmarketos.org/)
- [ScooterHacking](https://scooterhacking.org/) community
- [Flask](https://palletsprojects.com/p/flask/), [Vue 3](https://vuejs.org/), [Vite](https://vite.dev/)

Read the **[Manifesto](docs/project/MANIFESTO.md)** — the seven principles behind OSmosis.

> We support Windows only so you can escape from it.
