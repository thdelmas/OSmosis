# Routers & NAS Devices

## Overview

OSmosis supports flashing open-source firmware onto consumer routers, managed switches, and network-attached storage devices. The primary target is **OpenWrt**, but other firmware ecosystems are documented here as well.

## Flash Methods

| Method | Description |
|--------|-------------|
| **TFTP** | Upload firmware via TFTP during bootloader recovery |
| **Web UI** | Upload through the stock web administration interface |
| **SSH/SCP** | Push firmware over SSH to devices already running OpenWrt or similar |
| **Serial console** | UART access for recovery and initial flashing |

## Supported Firmware

| Firmware | Description |
|----------|-------------|
| [OpenWrt](https://openwrt.org/) | Linux-based router OS with 5000+ supported devices |
| [DD-WRT](https://dd-wrt.com/) | Linux-based alternative firmware for broadband routers |
| [FreshTomato](https://freshtomato.org/) | Fork of Tomato firmware for Broadcom-based routers |
| [OPNsense](https://opnsense.org/) | FreeBSD-based firewall/router OS (x86 hardware) |

## Supported Devices

> This page is a stub. Device-specific guides will be added as OSmosis support expands.

| Brand | Models | Status |
|-------|--------|--------|
| TP-Link | Archer series | Planned |
| Netgear | Nighthawk series | Planned |
| Linksys | WRT series | Planned |
| ASUS | RT series | Planned |
| GL.iNet | GL-MT series | Research |
| Synology | DSx series (NAS) | Research |
| QNAP | TS series (NAS) | Research |

## Recovery

Most routers can be recovered via TFTP failsafe mode — hold the reset button during power-on to enter the bootloader's TFTP server. Consult your device's OpenWrt wiki page for exact instructions.
