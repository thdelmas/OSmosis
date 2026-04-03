# Gladys Assistant

Privacy-first, open-source home automation platform. Relevant to OSmosis as a
reference for local-first IoT device management, lightweight deployment on
constrained hardware, and community-driven device support.

- Site: `https://gladysassistant.com/`
- GitHub: `https://github.com/GladysAssistant/Gladys`
- License: Apache 2.0
- Stars: ~3,000
- Created: June 2015 by Pierre-Gilles Leymarie (France)

---

## Overview

Gladys lets users monitor and control smart home devices (lights, sensors,
cameras, locks, thermostats) from a single web dashboard. Scenes and
automations are created through the UI without coding. Supports chat/voice
interaction via Telegram, Google Home, Alexa, and Siri.

Core philosophy: **local-first, no cloud dependency, design-first UX, built to
last decades**. No config files or terminal needed after initial install.

---

## Tech Stack

| Layer        | Technology                                          |
|--------------|-----------------------------------------------------|
| Backend      | Node.js 22.x (JavaScript)                           |
| Database     | SQLite (via Sequelize ORM with migrations)           |
| Frontend     | Preact SPA (Axios, ApexCharts, Day.js, HLS.js)      |
| Deployment   | Docker (auto-updates)                                |
| Testing      | Mocha, NYC (coverage), Cypress (E2E)                 |
| Docs         | Docusaurus v3                                        |

Monorepo structure: `/server` (backend) and `/front` (frontend).

---

## Hardware Support

Runs on **anything that supports Docker**:

- Raspberry Pi (historically the primary target)
- Mini-PCs (currently recommended)
- Synology NAS
- Unraid servers
- Freebox Delta (French ISP box)
- Any generic Linux machine, old laptops, etc.

---

## Integrations (39+)

- **Protocols:** Zigbee (via Zigbee2MQTT), Matter, Matterbridge, MQTT, Z-Wave
  (via zwave-js-ui), USB, Bluetooth, LAN discovery
- **Brands:** Philips Hue, Shelly, Sonos, Xiaomi, TP-Link, Tuya, Tasmota,
  Nuki, Broadlink, MELCloud, Netatmo, eWeLink
- **Voice/Assistants:** Google Actions, Alexa, HomeKit, Google Cast, Airplay
- **Cameras:** RTSP
- **Messaging:** Telegram, Nextcloud Talk, CallMeBot, Free Mobile (SMS)
- **Energy:** Enedis, EDF Tempo, Ecowatt, energy monitoring
- **Calendar:** CalDAV
- **Automation:** Node-RED
- **AI/LLM:** MCP (Model Context Protocol) service directory
- **Weather:** OpenWeather

---

## Privacy Architecture

This is the project's core differentiator:

- 100% local by default -- all data stays on the user's machine
- No tracking, no data selling, no third-party servers in the base install
- SQLite database -- no external DB server, easy backup
- **Gladys Plus** (optional paid subscription): secure remote access with
  end-to-end encryption, plus iOS/Android apps. Revenue model. Users without
  it can use VPN or reverse proxy instead.

---

## Comparison to Home Assistant

| Aspect          | Gladys                     | Home Assistant                |
|-----------------|----------------------------|-------------------------------|
| Philosophy      | Simplicity, polish, curated| Max flexibility, huge ecosystem|
| Config          | GUI-only, no YAML          | YAML + GUI                    |
| Integrations    | ~39 built-in               | 2,000+                        |
| Language        | JavaScript / Node.js       | Python                        |
| Database        | SQLite                     | SQLite + PostgreSQL option    |
| Community       | Smaller, French-centric    | Massive, global               |
| UI              | Clean, opinionated         | Functional, customizable      |
| Learning curve  | Lower                      | Higher                        |
| Revenue         | Gladys Plus (remote access)| Nabu Casa (remote + voice)    |

---

## Community & Maintenance

- **Primary maintainer:** Pierre-Gilles Leymarie (2,171 commits vs. 139 for
  next contributor)
- **Community:** Discourse forum at `community.gladysassistant.com`
- **Status (April 2026):** Actively maintained. v4.71.0 released March 20,
  2026. Releases every 2-4 weeks. 11 years of continuous development.
- **Risk:** Single-maintainer project with a small contributor base.

---

## Relevance to OSmosis

### What we can learn

1. **Local-first as a feature, not a compromise.** Gladys proves that
   privacy-first design can be a competitive differentiator, not just an
   ideology. Their paid cloud layer (Gladys Plus) shows how to monetize
   without compromising the local-first core.

2. **Docker as the universal deployment target.** "If Docker runs on it,
   Gladys runs on it" -- a simple, effective hardware support story. Relevant
   for LETHE's deployment strategy on diverse hardware.

3. **SQLite for simplicity.** No external database server needed. Easy backup,
   easy migration. A pattern worth considering for device profiles and
   telemetry storage.

4. **Curated integrations over quantity.** 39 well-maintained integrations
   beats 2,000 half-broken ones for a small team. Aligns with OSmosis's
   approach to quality device support.

5. **Matter/Matterbridge support.** Gladys is already integrating the Matter
   smart home standard -- relevant for OSmosis's IoT device support roadmap.

### Where OSmosis differs

- OSmosis targets **firmware flashing and device liberation**, not ongoing
  home automation. The overlap is in IoT device management, not the day-to-day
  smart home control loop.
- Gladys assumes devices run manufacturer firmware with standard APIs. OSmosis
  assumes you want to **replace** the firmware entirely.
- Gladys's MQTT/Zigbee/Z-Wave integrations are relevant to OSmosis's gap
  analysis item #11 (Home Automation Integration), but only once OSmosis has
  post-flash device management.

### Potential integration points

- Gladys could be a **downstream consumer** of OSmosis-flashed IoT devices --
  flash with OSmosis, manage with Gladys.
- Gladys's Matter support could inform OSmosis's approach to IoT device
  discovery and communication.
- The Gladys Plus E2E encryption model is a reference for LETHE's secure
  remote access design.
