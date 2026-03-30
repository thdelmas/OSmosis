<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import staticProfiles from '@/data/device-profiles.json'
const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const activeArticle = ref(null)
const searchQuery = ref('')
const focusedCardIndex = ref(-1)
const deviceProfiles = ref(staticProfiles)

const articles = [
  // ── Devices & Hardware ──
  {
    id: 'android-devices',
    title: 'Android Phones & Tablets',
    summary: 'Samsung, Pixel, OnePlus, Xiaomi, Motorola, Sony, Fairphone, and more. 40+ supported devices.',
    category: 'devices',
    related: ['bootloader', 'rom', 'custom-os'],
    body: `<p>OSmosis supports flashing custom ROMs, recoveries, and stock firmware on <strong>40+ Android devices</strong> from major manufacturers.</p>
<h3>Supported Brands</h3>
<table class="wiki-table">
  <thead><tr><th>Brand</th><th>Flash Method</th><th>Example Devices</th></tr></thead>
  <tbody>
    <tr><td>Samsung</td><td>Odin/Heimdall + TWRP</td><td>Galaxy Tab S, Galaxy S series</td></tr>
    <tr><td>Google Pixel</td><td>Fastboot</td><td>Pixel 6 through Pixel 9 Pro</td></tr>
    <tr><td>OnePlus</td><td>Fastboot</td><td>OnePlus 8, 9, 10, 11, 12</td></tr>
    <tr><td>Xiaomi</td><td>Fastboot / MIAssistant</td><td>Mi 11 Lite, POCO, Redmi Note series</td></tr>
    <tr><td>Motorola</td><td>Fastboot</td><td>Moto G, Edge series</td></tr>
    <tr><td>Sony</td><td>Fastboot</td><td>Xperia 1, 5 series</td></tr>
    <tr><td>Fairphone</td><td>Fastboot</td><td>Fairphone 4, 5</td></tr>
    <tr><td>Nothing</td><td>Fastboot</td><td>Nothing Phone 1, 2</td></tr>
  </tbody>
</table>
<h3>Bootloader Unlocking</h3>
<p>Most Android devices require an <strong>unlocked bootloader</strong> before custom software can be installed. The process varies by brand:</p>
<ul>
  <li><strong>Pixel, OnePlus, Sony:</strong> Unlock via Developer Options + fastboot command</li>
  <li><strong>Samsung:</strong> Enable OEM Unlock in Developer Options, then boot into download mode</li>
  <li><strong>Xiaomi:</strong> Requires Mi account + MiUnlockTool (Linux) or Mi Unlock (Windows). May have a 7-30 day waiting period. <em>Tip: OSmosis can extract the device token via MIAssistant protocol even on bricked devices.</em></li>
  <li><strong>Motorola:</strong> Request unlock code from Motorola's website</li>
</ul>
<h3>Xiaomi MIAssistant (locked bootloader recovery)</h3>
<p>MIUI Recovery 5.0 has a "Connect with MIAssistant" mode that lets you flash official stock ROMs on <strong>locked</strong> Xiaomi devices. OSmosis implements this protocol natively. Key points:</p>
<ul>
  <li>Uses a proprietary USB protocol (not standard ADB sideload)</li>
  <li>ROM must match the device's region (EEA, Global, China, etc.) and model</li>
  <li>Xiaomi's server validates the ROM before the device accepts the transfer</li>
  <li>Will not work for cross-flashed devices (wrong firmware on wrong hardware) &mdash; bootloader unlock or EDL is needed instead</li>
</ul>
<h3>What You Can Do</h3>
<ul>
  <li>Install privacy-focused ROMs like GrapheneOS, CalyxOS, or /e/OS</li>
  <li>Extend device life with LineageOS when official updates stop</li>
  <li>Flash stock firmware to recover bricked devices</li>
  <li>Install custom recovery (TWRP) for full device management</li>
  <li>Recover cross-flashed Xiaomi devices via bootloader unlock + correct firmware</li>
</ul>`
  },
  {
    id: 'linux-phones',
    title: 'Linux Phones',
    summary: 'PinePhone, PinePhone Pro, PineTab 2, and Librem 5. Devices built to run desktop Linux.',
    category: 'devices',
    related: ['linux-phone-os', 'sbc', 'android-devices'],
    body: `<p>Linux phones are devices designed to run <strong>mainline Linux distributions</strong> natively, rather than Android. They boot from SD cards or eMMC and support multiple operating systems.</p>
<h3>Supported Devices</h3>
<table class="wiki-table">
  <thead><tr><th>Device</th><th>SoC</th><th>RAM</th><th>Boot Method</th></tr></thead>
  <tbody>
    <tr><td>PinePhone</td><td>Allwinner A64</td><td>2/3 GB</td><td>microSD / eMMC</td></tr>
    <tr><td>PinePhone Pro</td><td>Rockchip RK3399</td><td>4 GB</td><td>microSD / eMMC</td></tr>
    <tr><td>PineTab 2</td><td>Rockchip RK3566</td><td>4/8 GB</td><td>microSD / eMMC</td></tr>
    <tr><td>Librem 5</td><td>NXP i.MX 8M</td><td>3 GB</td><td>eMMC / microSD</td></tr>
  </tbody>
</table>
<h3>Privacy Features</h3>
<ul>
  <li><strong>Hardware kill switches:</strong> PinePhone has 6 DIP switches (modem, WiFi, mic, cameras, headphone). Librem 5 has 3 physical side switches.</li>
  <li><strong>Separate chips:</strong> Librem 5 uses removable M.2 cards for WiFi, modem, and GPS &mdash; not integrated into the SoC</li>
  <li><strong>No proprietary blobs:</strong> Librem 5's i.MX 8M has open-source GPU drivers (etnaviv)</li>
</ul>
<h3>Dual Booting</h3>
<p>Flash one OS to eMMC and another to microSD. Boot order prioritizes the SD card, making it easy to test new systems without touching your main install.</p>`
  },
  {
    id: 'sbc',
    title: 'Single-Board Computers',
    summary: 'Raspberry Pi, Pine64, Orange Pi, ODROID, Jetson, and RISC-V boards. 25+ devices.',
    category: 'devices',
    related: ['sbc-os', 'linux-phones', 'microcontrollers'],
    body: `<p>OSmosis supports writing OS images and managing firmware for <strong>25+ single-board computers</strong>. SBCs boot from SD cards, eMMC, or NVMe drives.</p>
<h3>Raspberry Pi</h3>
<table class="wiki-table">
  <thead><tr><th>Device</th><th>SoC</th><th>RAM</th><th>Boot</th></tr></thead>
  <tbody>
    <tr><td>Pi 5</td><td>BCM2712 (Cortex-A76)</td><td>4/8 GB</td><td>microSD / NVMe</td></tr>
    <tr><td>Pi 4 Model B</td><td>BCM2711 (Cortex-A72)</td><td>1-8 GB</td><td>microSD / USB</td></tr>
    <tr><td>Pi Zero 2 W</td><td>RP3A0 (Cortex-A53)</td><td>512 MB</td><td>microSD</td></tr>
  </tbody>
</table>
<h3>Other Supported SBCs</h3>
<table class="wiki-table">
  <thead><tr><th>Family</th><th>Examples</th><th>Architecture</th></tr></thead>
  <tbody>
    <tr><td>Pine64</td><td>ROCK64, ROCKPro64, Quartz64, Star64</td><td>ARM64, RISC-V</td></tr>
    <tr><td>Orange Pi</td><td>Orange Pi 5, 5 Plus, 3B</td><td>ARM64</td></tr>
    <tr><td>Radxa</td><td>ROCK 5B, ROCK 3A, Zero</td><td>ARM64</td></tr>
    <tr><td>ODROID</td><td>ODROID-N2+, C4, M1</td><td>ARM64</td></tr>
    <tr><td>NVIDIA Jetson</td><td>Nano, Xavier NX, Orin Nano</td><td>ARM64</td></tr>
  </tbody>
</table>
<h3>Key Notes</h3>
<ul>
  <li><strong>Pi 5</strong> supports NVMe via the M.2 HAT &mdash; significant performance over SD cards</li>
  <li><strong>Pi 4 USB boot</strong> requires a one-time bootloader update</li>
  <li><strong>RISC-V:</strong> Star64 and VisionFive 2 are the first supported RISC-V SBCs</li>
</ul>`
  },
  {
    id: 'scooters',
    title: 'Electric Scooters',
    summary: 'Ninebot, Xiaomi, Okai, NIU, and 50+ other scooters. Custom firmware and diagnostics.',
    category: 'devices',
    related: ['scooter-fw', 'safety', 'ebikes'],
    body: `<p>OSmosis supports flashing custom firmware (CFW) and stock firmware on <strong>50+ electric scooter models</strong>. Scooter firmware controls speed limits, acceleration, braking, battery management, and dashboard settings.</p>
<h3>Communication Protocols</h3>
<table class="wiki-table">
  <thead><tr><th>Protocol</th><th>Header</th><th>Used By</th></tr></thead>
  <tbody>
    <tr><td>Ninebot</td><td>0x5AA5</td><td>Ninebot-branded, newer Xiaomi (1S, 3, Pro 2)</td></tr>
    <tr><td>Xiaomi</td><td>0x55AA</td><td>Original M365 and Mi Pro</td></tr>
  </tbody>
</table>
<h3>Flash Methods</h3>
<table class="wiki-table">
  <thead><tr><th>Method</th><th>Description</th></tr></thead>
  <tbody>
    <tr><td>BLE</td><td>Bluetooth Low Energy firmware push &mdash; most common</td></tr>
    <tr><td>ST-Link</td><td>SWD debug probe for ESC chip (STM32/AT32)</td></tr>
    <tr><td>UART</td><td>Serial connection via TX/RX pads (Xiaomi Mi 4+)</td></tr>
  </tbody>
</table>
<h3>Popular Models</h3>
<ul>
  <li><strong>Ninebot Max G30</strong> &mdash; most mature CFW support via max.cfw.sh</li>
  <li><strong>Xiaomi M365 / Pro</strong> &mdash; original custom firmware scene</li>
  <li><strong>Ninebot F-series</strong> &mdash; F20A through F65, newer platform</li>
  <li><strong>Ninebot E-series</strong> &mdash; budget models, limited CFW</li>
</ul>
<h3>Safety Warning</h3>
<p>Modifying scooter firmware affects speed limits, braking, and battery management. OSmosis includes built-in safety checks, but always understand the changes you are making and test in a safe environment.</p>`
  },
  {
    id: 'ebikes',
    title: 'E-Bike Controllers',
    summary: 'Bafang, Tongsheng TSDZ2, VESC, and 30+ controllers. Open-source motor firmware.',
    category: 'devices',
    related: ['scooters', 'microcontrollers', 'safety'],
    body: `<p>OSmosis supports flashing open-source firmware on <strong>30+ e-bike motor controllers and displays</strong>.</p>
<h3>Supported Controllers</h3>
<table class="wiki-table">
  <thead><tr><th>Controller</th><th>Flash Method</th><th>Firmware</th><th>Status</th></tr></thead>
  <tbody>
    <tr><td>Bafang BBSHD / BBS02</td><td>ST-Link</td><td>bbs-fw</td><td>Supported</td></tr>
    <tr><td>Tongsheng TSDZ2</td><td>ST-Link</td><td>TSDZ2 Open Source Firmware</td><td>Supported</td></tr>
    <tr><td>VESC</td><td>USB / UART</td><td>VESC firmware</td><td>Supported</td></tr>
    <tr><td>CYC X1 Pro / Stealth</td><td>UART</td><td>CYC config tool</td><td>Experimental</td></tr>
    <tr><td>Kunteng (KT)</td><td>UART</td><td>OpenSource EBike</td><td>Experimental</td></tr>
  </tbody>
</table>
<h3>What Open Firmware Provides</h3>
<ul>
  <li>Configurable pedal assist levels (speed and torque)</li>
  <li>Street-legal and off-road profiles</li>
  <li>Adjustable speed limits per assist level</li>
  <li>Battery voltage cutoff protection</li>
  <li>Temperature monitoring and throttle management</li>
</ul>
<h3>Safety Warning</h3>
<p>Incorrect firmware settings can cause motor overheating, battery damage, or loss of braking. Always test changes in a safe environment before riding in traffic.</p>`
  },
  {
    id: 'microcontrollers',
    title: 'Microcontrollers',
    summary: 'Arduino, ESP32, RPi Pico, STM32, Teensy, and 60+ boards. Compile and flash firmware.',
    category: 'devices',
    related: ['sbc', 'ebikes', 'bootloader'],
    body: `<p>OSmosis supports compiling and flashing firmware to <strong>60+ microcontroller boards</strong> across multiple ecosystems.</p>
<h3>Flash Tools</h3>
<table class="wiki-table">
  <thead><tr><th>Tool</th><th>Boards</th></tr></thead>
  <tbody>
    <tr><td>arduino-cli</td><td>Arduino, Adafruit, Seeed, Teensy</td></tr>
    <tr><td>esptool</td><td>ESP32, ESP8266, all Espressif chips</td></tr>
    <tr><td>picotool</td><td>Raspberry Pi Pico, RP2040/RP2350</td></tr>
    <tr><td>stflash</td><td>STM32 boards via ST-Link</td></tr>
    <tr><td>dfu-util</td><td>STM32 (DFU mode), flight controllers</td></tr>
  </tbody>
</table>
<h3>Board Families</h3>
<table class="wiki-table">
  <thead><tr><th>Family</th><th>Examples</th><th>Architecture</th></tr></thead>
  <tbody>
    <tr><td>Arduino (AVR)</td><td>Uno, Mega, Nano, Leonardo</td><td>ATmega</td></tr>
    <tr><td>Arduino (ARM)</td><td>Uno R4, Due, Zero, MKR</td><td>Cortex-M</td></tr>
    <tr><td>Espressif</td><td>ESP32, ESP32-S3, ESP32-C3, ESP8266</td><td>Xtensa / RISC-V</td></tr>
    <tr><td>Raspberry Pi Pico</td><td>Pico, Pico W, Pico 2</td><td>ARM Cortex-M0+ / RISC-V</td></tr>
    <tr><td>STM32</td><td>Blue Pill, Nucleo, Black Pill</td><td>Cortex-M</td></tr>
    <tr><td>LoRa / Meshtastic</td><td>TTGO LoRa32, Heltec, RAK</td><td>ESP32-based</td></tr>
  </tbody>
</table>
<h3>Special Use Cases</h3>
<ul>
  <li><strong>Meshtastic:</strong> Off-grid mesh networking on LoRa boards</li>
  <li><strong>3D printing:</strong> Marlin/Klipper firmware on SKR, BTT, Duet boards</li>
  <li><strong>Flight controllers:</strong> Betaflight/INAV on STM32-based FC boards</li>
</ul>`
  },
  {
    id: 'apple-t2',
    title: 'Apple T2 Macs',
    summary: 'MacBook Pro/Air 2018-2020, iMac, Mac Pro, Mac mini. T2 security chip management.',
    category: 'devices',
    related: ['t2-walkthrough', 't2-linux', 't2-troubleshoot'],
    body: `<p>OSmosis supports backup, restore, and diagnostics for the <strong>Apple T2 Security Chip</strong> found in 12 Mac models from 2018&ndash;2020.</p>
<h3>What the T2 Chip Controls</h3>
<ul>
  <li><strong>SSD encryption:</strong> All internal storage is encrypted by the T2. The SSD cannot be read without it.</li>
  <li><strong>Secure Boot:</strong> Verifies the macOS boot chain (Full, Medium, or No Security)</li>
  <li><strong>Touch ID:</strong> Fingerprint data processed in a Secure Enclave</li>
  <li><strong>SMC:</strong> Fan control, power management, keyboard backlight</li>
  <li><strong>Audio / Camera:</strong> Handles mic, speaker, and FaceTime camera processing</li>
</ul>
<h3>Supported Models</h3>
<table class="wiki-table">
  <thead><tr><th>Category</th><th>Models</th></tr></thead>
  <tbody>
    <tr><td>MacBook Pro</td><td>13" and 15"/16" from 2018, 2019, 2020</td></tr>
    <tr><td>MacBook Air</td><td>2018, 2019, 2020</td></tr>
    <tr><td>iMac</td><td>27" 2020 (Retina 5K)</td></tr>
    <tr><td>iMac Pro</td><td>2017 (first Mac with T2)</td></tr>
    <tr><td>Mac Pro</td><td>2019</td></tr>
    <tr><td>Mac mini</td><td>2018</td></tr>
  </tbody>
</table>
<h3>What OSmosis Can Do</h3>
<ul>
  <li>Query T2 firmware version and Secure Boot status</li>
  <li>Back up and restore T2 configuration</li>
  <li>Diagnose T2-related boot issues</li>
  <li>Flash T2 firmware via DFU mode (Apple Configurator 2 workflow)</li>
</ul>`
  },
  {
    id: 't2-walkthrough',
    title: 'T2 Walkthrough: Backup & Restore',
    summary: 'Step-by-step guide to backing up and restoring your T2 chip firmware using OSmosis.',
    category: 'devices',
    related: ['apple-t2', 't2-linux', 't2-troubleshoot'],
    body: `<p>This walkthrough covers the full process of backing up and restoring the Apple T2 security chip using OSmosis. Follow these steps to protect your Mac before making changes to Secure Boot, installing Linux, or recovering from a corrupted T2.</p>

<h3>What you need</h3>
<ul>
  <li>A <strong>second computer</strong> running OSmosis (Linux or macOS). This is the "host" computer that communicates with the T2.</li>
  <li>A <strong>USB-C cable</strong> that supports data transfer (not a charge-only cable)</li>
  <li><strong>t2tool</strong> installed on the host &mdash; OSmosis will warn you if it's missing. Install from <a href="https://github.com/t2linux/apple-t2-tool" target="_blank" rel="noopener noreferrer">github.com/t2linux/apple-t2-tool</a></li>
  <li><strong>libusb</strong> installed on the host (<code>sudo apt install libusb-1.0-0-dev</code> on Debian/Ubuntu)</li>
  <li>Optional: <strong>lsusb</strong> (from <code>usbutils</code>) for better USB device detection</li>
</ul>

<h3>Step 1: Enter DFU mode</h3>
<p>DFU (Device Firmware Update) mode lets the host computer talk directly to the T2 chip over USB. The Mac's screen stays completely black &mdash; this is normal.</p>
<p><strong>For MacBook Pro / MacBook Air:</strong></p>
<ol>
  <li>Shut down the Mac completely</li>
  <li>Connect the USB-C cable from the host to the Mac's <strong>left Thunderbolt port closest to you</strong></li>
  <li>Press and hold the <strong>Power button</strong> (Touch ID) for exactly 10 seconds, then release</li>
  <li>Wait 3 seconds</li>
  <li>Press and hold <strong>Right Shift + Left Option + Left Control + Power</strong> together for 10 seconds</li>
  <li>Release all keys. The screen stays black &mdash; DFU is active.</li>
</ol>
<p><strong>For desktop Macs (iMac, Mac mini, Mac Pro):</strong></p>
<ol>
  <li>Disconnect all power and peripherals</li>
  <li>Connect the USB-C cable to the Thunderbolt port <strong>closest to the Ethernet port</strong> (iMac), <strong>HDMI port</strong> (Mac mini), or <strong>power connector</strong> (Mac Pro)</li>
  <li>Plug in power while holding the power button</li>
  <li>Release after 3 seconds</li>
</ol>

<h3>Step 2: Detect the T2 chip</h3>
<p>In OSmosis, go to <strong>Wizard &rarr; Apple T2</strong> and click <strong>Detect T2 chip</strong>. OSmosis scans the USB bus for the T2's DFU identifier (USB VID:PID <code>05ac:1881</code>).</p>
<p>If detection fails, check:</p>
<ul>
  <li>Is the Mac's screen completely black? If it's showing anything, it's not in DFU mode.</li>
  <li>Are you using the correct USB-C port on the Mac?</li>
  <li>Try a different USB-C cable &mdash; not all cables carry data.</li>
  <li>Re-do the DFU key sequence from step 1.</li>
</ul>

<h3>Step 3: Select your Mac model</h3>
<p>Optional but recommended. Selecting your model labels the backup so you can identify it later. OSmosis groups models by product line (MacBook Pro, MacBook Air, iMac, etc.).</p>

<h3>Step 4: Back up</h3>
<p>Select which regions to save:</p>
<table class="wiki-table">
  <thead><tr><th>Region</th><th>What it contains</th><th>Size</th></tr></thead>
  <tbody>
    <tr><td><strong>firmware</strong></td><td>bridgeOS &mdash; the T2's own operating system. Most critical.</td><td>~200-400 KB</td></tr>
    <tr><td><strong>nvram</strong></td><td>Startup disk, display resolution, kernel boot args</td><td>~32 KB</td></tr>
    <tr><td><strong>sep</strong></td><td>Secure Enclave &mdash; Touch ID and encryption key metadata</td><td>~64 KB</td></tr>
  </tbody>
</table>
<p><strong>Keep all three selected</strong> unless you have a specific reason not to. Click <strong>Back up T2 chip</strong> and wait for the terminal to show success.</p>
<p>Backups are saved to <code>~/.osmosis/t2-backups/</code> with SHA-256 checksums and model metadata.</p>

<h3>Step 5: Restore (if needed)</h3>
<p>To restore from a backup:</p>
<ol>
  <li>Enter DFU mode again (same process as step 1)</li>
  <li>Detect the T2 chip</li>
  <li>Scroll to <strong>Restore from backup</strong> and select your backup from the dropdown</li>
  <li>Click <strong>Restore T2 firmware</strong></li>
</ol>
<p>OSmosis verifies the SHA-256 checksums before writing anything. If a checksum doesn't match, the restore is aborted to protect your T2.</p>
<p><strong>Do not unplug the cable or turn off either computer during the restore.</strong> If the process is interrupted, re-enter DFU mode and try again.</p>

<h3>After restore</h3>
<p>Hold the power button until the Mac restarts. The first boot after a restore may take longer than usual as the T2 re-initializes.</p>`
  },
  {
    id: 't2-linux',
    title: 'Installing Linux on T2 Macs',
    summary: 'How to run Linux on Intel Macs with a T2 chip. Secure Boot, drivers, and what works.',
    category: 'devices',
    related: ['apple-t2', 't2-walkthrough', 'linux-phones'],
    body: `<p>The <a href="https://t2linux.org/" target="_blank" rel="noopener noreferrer">T2 Linux project</a> provides kernel patches and drivers to run Linux on T2-equipped Macs. Standard Linux kernels lack drivers for the T2's keyboard, trackpad, audio, and Wi-Fi.</p>

<h3>Before you start</h3>
<ul>
  <li><strong>Back up your T2 firmware first</strong> using OSmosis (see the T2 Walkthrough)</li>
  <li><strong>Back up your data</strong> &mdash; Time Machine or any external backup</li>
</ul>

<h3>Step 1: Change Secure Boot settings</h3>
<ol>
  <li>Boot to macOS Recovery: restart and hold <strong>Command + R</strong></li>
  <li>Open <strong>Startup Security Utility</strong> from the Utilities menu</li>
  <li>Set Secure Boot to <strong>No Security</strong></li>
  <li>Set Allowed Boot Media to <strong>Allow booting from external or removable media</strong></li>
</ol>

<h3>Step 2: Install a T2-patched distro</h3>
<p>Use a distribution with T2 kernel patches pre-applied:</p>
<table class="wiki-table">
  <thead><tr><th>Distro</th><th>Method</th></tr></thead>
  <tbody>
    <tr><td><strong>Ubuntu</strong></td><td>Add the t2linux PPA, install <code>linux-t2</code> kernel</td></tr>
    <tr><td><strong>Fedora</strong></td><td>Add the t2linux COPR repo</td></tr>
    <tr><td><strong>Arch Linux</strong></td><td>Install <code>linux-t2</code> from t2linux packages</td></tr>
    <tr><td><strong>Manjaro</strong></td><td>Community builds available</td></tr>
  </tbody>
</table>

<h3>Step 3: Copy Wi-Fi firmware</h3>
<p>The T2 Mac's Wi-Fi chip requires proprietary firmware files that are not redistributable. You need to copy them from your macOS partition:</p>
<ol>
  <li>Mount the macOS partition from Linux</li>
  <li>Copy firmware files from <code>/usr/share/firmware/wifi/</code> to the Linux firmware directory</li>
  <li>The t2linux wiki has exact paths for each model</li>
</ol>

<h3>What works</h3>
<table class="wiki-table">
  <thead><tr><th>Feature</th><th>Status</th></tr></thead>
  <tbody>
    <tr><td>Internal keyboard &amp; trackpad</td><td>Works (with T2 patches)</td></tr>
    <tr><td>Touch Bar</td><td>Works (basic display, function keys)</td></tr>
    <tr><td>Audio (speakers &amp; headphone)</td><td>Works (with T2 patches)</td></tr>
    <tr><td>Wi-Fi</td><td>Works (requires firmware from macOS)</td></tr>
    <tr><td>Thunderbolt</td><td>Works</td></tr>
    <tr><td>Screen brightness</td><td>Works</td></tr>
    <tr><td>Fan control</td><td>Works (via <code>t2fanrd</code> daemon)</td></tr>
    <tr><td>Touch ID</td><td>Not supported (Secure Enclave won't expose fingerprint data)</td></tr>
  </tbody>
</table>`
  },
  {
    id: 't2-troubleshoot',
    title: 'T2 Troubleshooting',
    summary: 'Common T2 problems: Mac won\'t boot, DFU detection fails, restore errors, and recovery options.',
    category: 'devices',
    related: ['apple-t2', 't2-walkthrough', 'brick'],
    body: `<p>The T2 chip can fail for several reasons: interrupted macOS updates, power loss during firmware writes, or corrupted bridgeOS. Here's how to diagnose and fix common issues.</p>

<h3>Mac won't boot (blank screen, no chime)</h3>
<ol>
  <li><strong>Try an SMC reset first:</strong> Unplug power, wait 15 seconds. On MacBooks: press and hold Shift + Control + Option + Power for 10 seconds. On desktops: unplug, wait 15 seconds, replug.</li>
  <li><strong>Try NVRAM reset:</strong> Restart and immediately hold Option + Command + P + R for 20 seconds.</li>
  <li><strong>If still dead:</strong> Enter DFU mode and use OSmosis to detect and restore the T2. If you have a backup, restore it. If not, Apple Configurator 2 on another Mac can restore factory bridgeOS.</li>
</ol>

<h3>DFU detection fails ("T2 chip not found on USB")</h3>
<table class="wiki-table">
  <thead><tr><th>Symptom</th><th>Fix</th></tr></thead>
  <tbody>
    <tr><td>Mac's screen is on / showing Apple logo</td><td>Not in DFU mode. Shut down completely and redo the key sequence.</td></tr>
    <tr><td>Screen is black but no USB detection</td><td>Wrong port. Use the <strong>left Thunderbolt port closest to you</strong> on MacBooks.</td></tr>
    <tr><td>Right port, still nothing</td><td>Try a different USB-C cable. Charge-only cables won't work.</td></tr>
    <tr><td><code>lsusb</code> shows the device but OSmosis doesn't</td><td>Check that <code>t2tool</code> is installed and accessible. Run <code>which t2tool</code>.</td></tr>
    <tr><td>Permission denied errors</td><td>Run OSmosis with <code>sudo</code> or add a udev rule for the T2 USB VID/PID (<code>05ac:1881</code>).</td></tr>
  </tbody>
</table>

<h3>Backup fails ("Cannot communicate with T2 chip")</h3>
<ul>
  <li>The T2 may have <strong>dropped out of DFU mode</strong>. This can happen if you wait too long. Re-enter DFU and try again.</li>
  <li>Some <strong>USB hubs and docks</strong> don't pass through DFU connections. Connect directly.</li>
  <li>If using a VM, ensure <strong>USB passthrough</strong> is enabled for Apple devices.</li>
</ul>

<h3>Restore fails ("write failed" for a region)</h3>
<ul>
  <li><strong>Re-enter DFU mode</strong> and try restoring just the failed region.</li>
  <li>If the <strong>sep</strong> region fails, this is sometimes expected &mdash; the Secure Enclave may reject writes on some models. The firmware and nvram regions are more important.</li>
  <li>If the firmware region itself fails repeatedly, the T2 chip may have a hardware fault. Try <strong>Apple Configurator 2</strong> (requires a Mac) as a last resort.</li>
</ul>

<h3>After restore, Mac boots but Touch ID / FileVault broken</h3>
<p>This is expected. Restoring the SEP region does <strong>not</strong> restore fingerprints or FileVault encryption keys &mdash; the Secure Enclave prevents this for security reasons. You will need to:</p>
<ul>
  <li>Re-enroll fingerprints in System Preferences &rarr; Touch ID</li>
  <li>If FileVault was enabled, you may need your recovery key to unlock the disk</li>
</ul>

<h3>Nuclear option: Apple Configurator 2</h3>
<p>If OSmosis cannot communicate with the T2 at all, Apple Configurator 2 (free, macOS-only) can factory-reset the T2 and install the latest bridgeOS. This erases all T2 data including encryption keys &mdash; <strong>data on the internal SSD will be unrecoverable</strong> if you don't have a backup.</p>`
  },
  // ── Individual Device Profiles are loaded dynamically from /api/profiles ──
  // ── Operating Systems & Compatibility ──
  {
    id: 'lethe',
    title: 'Lethe',
    summary: 'L.E.T.H.E. (Logical Erasure & Total History Elimination) — Privacy-hardened Android fork by OSmosis. Dead man\'s switch, duress PIN, burner mode, tracker blocking, default-deny firewall.',
    category: 'os',
    related: ['custom-os', 'android-devices', 'bootloader'],
    body: `<p><strong>Lethe</strong> (L.E.T.H.E. &mdash; Logical Erasure &amp; Total History Elimination) is a privacy-focused Android fork built and maintained by the OSmosis project. It applies hardened overlays on top of <strong>LineageOS</strong>, inheriting support for 300+ devices while adding aggressive privacy defaults out of the box.</p>
<h3>Why Lethe?</h3>
<p>GrapheneOS is the gold standard for Android privacy &mdash; but it only runs on Google Pixel phones. If you own a Samsung, Nothing, Xiaomi, Fairphone, OnePlus, Motorola, or Sony, your best options were limited. Lethe fills that gap: <strong>GrapheneOS-level privacy intent, for everyone</strong>.</p>
<h3>Privacy Features</h3>
<table class="wiki-table">
  <thead><tr><th>Feature</th><th>What It Does</th></tr></thead>
  <tbody>
    <tr><td><strong>Tracker blocking</strong></td><td>System-level hosts file blocks Google, Facebook, and 50+ ad/analytics domains. Updated weekly via OTA.</td></tr>
    <tr><td><strong>Default-deny firewall</strong></td><td>Apps have no network access until you grant it. Uses nftables with per-app UID rules.</td></tr>
    <tr><td><strong>DNS-over-TLS</strong></td><td>All DNS queries encrypted via Quad9 (primary) and Mullvad (fallback). Cleartext DNS rejected.</td></tr>
    <tr><td><strong>Sensor permissions</strong></td><td>Camera, mic, and location prompt on first use. Background location and body sensors denied by default.</td></tr>
    <tr><td><strong>Full-disk encryption</strong></td><td>AES-256-XTS encryption enforced on first boot.</td></tr>
    <tr><td><strong>No Google services</strong></td><td>Play Services, Play Store, Maps, YouTube, and all Google telemetry removed at build time.</td></tr>
    <tr><td><strong>SELinux enforcing</strong></td><td>Tightened policies: untrusted apps cannot use raw network sockets or execute from data directories.</td></tr>
    <tr><td><strong>Privacy NTP/captive portal</strong></td><td>Uses Cloudflare NTP and GrapheneOS connectivity check instead of Google servers.</td></tr>
    <tr><td><strong>USB charge-only</strong></td><td>USB defaults to charging mode &mdash; no data exfiltration when plugging into unknown ports.</td></tr>
    <tr><td><strong>Scrambled PIN pad</strong></td><td>Lock screen PIN digits are randomized to prevent shoulder surfing.</td></tr>
    <tr><td><strong>Dead man&rsquo;s switch</strong></td><td>If you stop checking in, the device escalates: lock &rarr; wipe &rarr; brick. Timer runs on hardware RTC &mdash; powering off or pulling the SIM doesn&rsquo;t help. Configured during first boot.</td></tr>
    <tr><td><strong>Duress PIN</strong></td><td>A secondary unlock code that looks like it works normally. Behind the scenes it silently wipes everything while showing a fake home screen.</td></tr>
    <tr><td><strong>Burner mode</strong></td><td>Every reboot wipes all user data, rotates MAC/Android&nbsp;ID/serial, and boots a clean session. Enabled by default &mdash; can be turned off after first boot.</td></tr>
  </tbody>
</table>
<h3>Pre-installed Apps</h3>
<table class="wiki-table">
  <thead><tr><th>App</th><th>Replaces</th><th>Purpose</th></tr></thead>
  <tbody>
    <tr><td><strong>F-Droid</strong></td><td>Google Play Store</td><td>Free and open-source app store</td></tr>
    <tr><td><strong>Mull Browser</strong></td><td>Chrome</td><td>Privacy-hardened Firefox fork (by DivestOS)</td></tr>
    <tr><td><strong>DAVx5</strong></td><td>Google Contacts/Calendar sync</td><td>CalDAV/CardDAV sync with any provider</td></tr>
  </tbody>
</table>
<h3>Recommended Apps</h3>
<ul>
  <li><strong>Signal</strong> &mdash; encrypted messaging (replaces Google Messages)</li>
  <li><strong>NewPipe</strong> &mdash; YouTube without tracking or Google account</li>
  <li><strong>OsmAnd+</strong> &mdash; offline maps (replaces Google Maps)</li>
  <li><strong>K-9 Mail</strong> &mdash; open-source email client</li>
  <li><strong>Aegis</strong> &mdash; 2FA authenticator (replaces Google Authenticator)</li>
  <li><strong>Shelter</strong> &mdash; isolate apps in a work profile sandbox</li>
</ul>
<h3>Dead Man&rsquo;s Switch</h3>
<p>The dead man&rsquo;s switch is set up during first boot. If you stop checking in, the device assumes you&rsquo;ve lost control and protects itself. No outbound signal is ever sent &mdash; <strong>silence is the trigger</strong>.</p>
<h4>First-boot setup</h4>
<ol>
  <li>Choose a check-in interval: twice a day, once a day, every 2&ndash;3 days, or weekly</li>
  <li>Set a dead man passphrase (separate from your lock PIN)</li>
  <li>Optionally set a duress PIN &mdash; looks like a normal unlock but silently wipes everything</li>
  <li>Review the escalation stages and optionally enable the brick stage</li>
</ol>
<h4>How check-in works</h4>
<p>At check-in time, a quiet notification appears (&ldquo;Scheduled maintenance pending&rdquo;). Tap it, enter your passphrase, done. The notification looks like a system prompt &mdash; nothing that reveals it&rsquo;s a dead man&rsquo;s switch to anyone watching your screen.</p>
<h4>Escalation</h4>
<table class="wiki-table">
  <thead><tr><th>Stage</th><th>Trigger</th><th>What happens</th></tr></thead>
  <tbody>
    <tr><td>Grace period</td><td>Missed check-in</td><td>4-hour window. One more bland notification.</td></tr>
    <tr><td>Stage 1 &mdash; Lock</td><td>Grace expires</td><td>Device locks. Only your dead man passphrase unlocks it &mdash; no fingerprint, no face, no PIN.</td></tr>
    <tr><td>Stage 2 &mdash; Wipe</td><td>+1 hour</td><td>Full data wipe: apps, messages, photos, WiFi, Bluetooth, eSIM profiles. Same scope as burner mode.</td></tr>
    <tr><td>Stage 3 &mdash; Brick</td><td>+2 hours (opt-in)</td><td>Overwrites boot, recovery, and persist partitions with random data. Device becomes unbootable. Only OSmosis USB recovery can restore it.</td></tr>
  </tbody>
</table>
<h4>Why it works even if the device is off</h4>
<p>The timer uses the hardware real-time clock (RTC), not network time. On every boot, elapsed time since last check-in is calculated <strong>before /data is even mounted</strong>. An adversary who powers off the device, pulls the SIM, or puts it in a Faraday cage is still on the clock.</p>
<h4>Duress PIN</h4>
<p>If you&rsquo;re forced to unlock your phone, enter the duress PIN instead. The device unlocks to what looks like a normal home screen. Behind the scenes, it&rsquo;s already wiping everything. By the time the adversary realizes, the data is gone.</p>

<h3>Supported Devices</h3>
<p>Lethe inherits device support from LineageOS. Initial builds target:</p>
<table class="wiki-table">
  <thead><tr><th>Brand</th><th>Devices</th></tr></thead>
  <tbody>
    <tr><td>Google Pixel</td><td>Pixel 7, 7 Pro, 7a, 8, 8 Pro, 8a, 9, 9 Pro, 9 Pro Fold</td></tr>
    <tr><td>Nothing</td><td>Phone (1), Phone (2), Phone (2a)</td></tr>
    <tr><td>Samsung</td><td>Galaxy Tab S 10.5, Galaxy Note II</td></tr>
    <tr><td>Fairphone</td><td>Fairphone 4, 5</td></tr>
    <tr><td>OnePlus</td><td>8 Pro, 9, 9 Pro</td></tr>
    <tr><td>Xiaomi</td><td>Mi 11 Lite 4G, Mi 11 Lite 5G</td></tr>
    <tr><td>Motorola</td><td>Moto G7 Plus, Moto G52</td></tr>
    <tr><td>Sony</td><td>Xperia 1 II, Xperia 1 III</td></tr>
  </tbody>
</table>
<h3>How to Install</h3>
<ol>
  <li>Connect your device to OSmosis via USB</li>
  <li>Select <strong>Lethe</strong> in the software selection step</li>
  <li>OSmosis flashes LineageOS + the OSmosis privacy overlay automatically</li>
  <li>On first boot, the default-deny firewall and tracker blocking are already active</li>
  <li>The first-boot wizard asks if you want to enable the dead man&rsquo;s switch and walks you through passphrase setup</li>
</ol>
<h3>How It Works (Technical)</h3>
<p>Lethe is not a full ROM build from scratch. It is a <strong>flashable overlay ZIP</strong> applied on top of LineageOS:</p>
<ul>
  <li>Privacy system properties are injected into <code>build.prop</code></li>
  <li>A tracker-blocking <code>hosts</code> file replaces the system default</li>
  <li>nftables firewall rules are installed as a system service</li>
  <li>Dead man&rsquo;s switch and burner mode run as early-init services (<code>init.lethe-deadman.rc</code>, <code>init.lethe-burner.rc</code>) before Android userspace starts</li>
  <li>Check-in state and preferences are stored on <code>/persist</code>, which survives data wipes</li>
  <li>Google packages are removed from the system partition</li>
  <li>FOSS apps (F-Droid, Mull) are pre-installed as system apps</li>
</ul>
<p>This overlay approach means Lethe inherits all LineageOS security patches and device support without maintaining a separate source tree for each device.</p>`
  },
  {
    id: 'custom-os',
    title: 'Custom Android ROMs',
    summary: 'GrapheneOS, DivestOS, CalyxOS, iodéOS, /e/OS, LineageOS, Replicant, and more. Privacy ranking and device support.',
    category: 'os',
    related: ['lethe', 'android-devices', 'rom', 'bootloader'],
    body: `<p>Custom ROMs replace the manufacturer's Android with community-built alternatives. Each has a different focus:</p>
<h3>Privacy-Focused</h3>
<table class="wiki-table">
  <thead><tr><th>ROM</th><th>Devices</th><th>Focus</th></tr></thead>
  <tbody>
    <tr><td><strong>Lethe</strong></td><td>300+ devices (LineageOS base)</td><td>Privacy-hardened by OSmosis: tracker blocking, default-deny firewall, DNS-over-TLS, debloated, dead man&rsquo;s switch, duress PIN, burner mode. Built-in OSmosis integration for USB updates.</td></tr>
    <tr><td><strong>GrapheneOS</strong></td><td>Pixel only</td><td>Hardened security: sandboxed Google Play, per-app network toggles, memory-safe improvements. Gold standard for privacy.</td></tr>
    <tr><td><strong>DivestOS</strong></td><td>100+ devices</td><td>LineageOS fork with aggressive deblobbing, kernel hardening, and automated CVE patching. Best privacy option for non-Pixel devices.</td></tr>
    <tr><td><strong>CalyxOS</strong></td><td>Pixel, Fairphone, Motorola</td><td>Privacy with optional microG for app compatibility, ships with Datura firewall</td></tr>
    <tr><td><strong>iod&eacute;OS</strong></td><td>40+ devices</td><td>French project with built-in system-level ad and tracker blocker</td></tr>
    <tr><td><strong>/e/OS</strong></td><td>200+ devices</td><td>De-Googled with app store (App Lounge) and Murena cloud services</td></tr>
    <tr><td><strong>Replicant</strong></td><td>Older Samsung Galaxy</td><td>Fully free software (FSF-endorsed). No proprietary blobs &mdash; requires Replicant's own recovery, not TWRP.</td></tr>
    <tr><td><strong>CopperheadOS</strong></td><td>Pixel only</td><td>Commercial hardened Android (GrapheneOS originally forked from it). Enterprise-focused.</td></tr>
  </tbody>
</table>
<h3>Privacy Ranking</h3>
<p>Roughly ordered by strictness of privacy/security hardening:</p>
<ol>
  <li><strong>GrapheneOS</strong> &mdash; hardened kernel, verified boot, sandboxed Play, exploit mitigations</li>
  <li><strong>DivestOS</strong> &mdash; hardened LineageOS fork, automated patching, wide device support</li>
  <li><strong>CalyxOS</strong> &mdash; strong defaults with optional microG compatibility</li>
  <li><strong>iod&eacute;OS</strong> &mdash; system-level tracker blocking out of the box</li>
  <li><strong>/e/OS</strong> &mdash; de-Googled with cloud integration, wider device support</li>
  <li><strong>LineageOS</strong> &mdash; no Google services by default but not hardened</li>
  <li><strong>Replicant</strong> &mdash; fully free software but limited hardware support and older devices</li>
</ol>
<h3>Longevity & Features</h3>
<table class="wiki-table">
  <thead><tr><th>ROM</th><th>Devices</th><th>Focus</th></tr></thead>
  <tbody>
    <tr><td><strong>LineageOS</strong></td><td>300+ devices</td><td>Extend device life with continued updates and features</td></tr>
    <tr><td><strong>PixelExperience</strong></td><td>100+ devices</td><td>Stock Pixel look and feel on any device</td></tr>
    <tr><td><strong>crDroid</strong></td><td>100+ devices</td><td>Customization-heavy with many built-in tweaks</td></tr>
  </tbody>
</table>
<h3>Choosing a ROM</h3>
<ul>
  <li><strong>One-click privacy for any device?</strong> Lethe &mdash; built into OSmosis, works on 300+ devices</li>
  <li><strong>Maximum security?</strong> GrapheneOS on a Pixel</li>
  <li><strong>Privacy on non-Pixel hardware?</strong> DivestOS for the widest hardened device support</li>
  <li><strong>Privacy without friction?</strong> CalyxOS (microG for app compat) or /e/OS</li>
  <li><strong>Block trackers out of the box?</strong> iod&eacute;OS ships a system-level blocker</li>
  <li><strong>Fully free software?</strong> Replicant (limited to older Samsung devices)</li>
  <li><strong>Old device, keep it alive?</strong> LineageOS has the widest device support</li>
  <li><strong>Stock Pixel feel everywhere?</strong> PixelExperience</li>
</ul>`
  },
  {
    id: 'linux-phone-os',
    title: 'Linux Phone Operating Systems',
    summary: 'Mobian, postmarketOS, Manjaro ARM, PureOS, and Ubuntu Touch. Desktop Linux on your phone.',
    category: 'os',
    related: ['linux-phones', 'custom-os', 'sbc-os'],
    body: `<p>Linux phone OSes bring desktop Linux distributions to mobile devices with touch-friendly interfaces.</p>
<h3>Available Systems</h3>
<table class="wiki-table">
  <thead><tr><th>OS</th><th>Base</th><th>Devices</th><th>Best For</th></tr></thead>
  <tbody>
    <tr><td><strong>Mobian</strong></td><td>Debian</td><td>PinePhone, PinePhone Pro, Librem 5</td><td>Stability, familiar package management</td></tr>
    <tr><td><strong>postmarketOS</strong></td><td>Alpine</td><td>PinePhone, PPP, PineTab 2, Librem 5</td><td>Lightweight, well-documented</td></tr>
    <tr><td><strong>Manjaro ARM</strong></td><td>Arch</td><td>PinePhone, PinePhone Pro</td><td>Rolling release, latest packages</td></tr>
    <tr><td><strong>PureOS</strong></td><td>Debian</td><td>Librem 5</td><td>Default Librem 5 OS, privacy-by-design</td></tr>
    <tr><td><strong>Ubuntu Touch</strong></td><td>Ubuntu</td><td>PinePhone, some Android ports</td><td>Unity-based, app ecosystem</td></tr>
  </tbody>
</table>
<h3>Mobile UI Shells</h3>
<table class="wiki-table">
  <thead><tr><th>Shell</th><th>Description</th></tr></thead>
  <tbody>
    <tr><td><strong>Phosh</strong></td><td>GNOME-based, most polished. Default on Mobian and PureOS.</td></tr>
    <tr><td><strong>Plasma Mobile</strong></td><td>KDE's mobile shell. Feature-rich but heavier.</td></tr>
    <tr><td><strong>Sxmo</strong></td><td>Minimalist tiling WM (dwm/sway). For power users.</td></tr>
  </tbody>
</table>
<h3>Getting Started</h3>
<ul>
  <li><strong>New to Linux phones?</strong> Start with Mobian or postmarketOS</li>
  <li><strong>Want latest packages?</strong> Manjaro ARM or Arch Linux ARM</li>
  <li><strong>Convergence:</strong> Connect to a monitor via USB-C dock for a desktop experience</li>
</ul>`
  },
  {
    id: 'sbc-os',
    title: 'SBC Operating Systems',
    summary: 'Raspberry Pi OS, DietPi, LibreELEC, Home Assistant, RetroPie, and more for single-board computers.',
    category: 'os',
    related: ['sbc', 'linux-phone-os', 'cross-compilation'],
    body: `<p>Single-board computers support a huge range of operating systems, from general-purpose desktops to single-purpose appliances.</p>
<h3>General Purpose</h3>
<table class="wiki-table">
  <thead><tr><th>OS</th><th>Supports</th><th>Best For</th></tr></thead>
  <tbody>
    <tr><td><strong>Raspberry Pi OS</strong></td><td>All Pi models</td><td>Default choice, best hardware support</td></tr>
    <tr><td><strong>Ubuntu</strong></td><td>Pi 3+, 4, 5</td><td>Desktop and server, Canonical support</td></tr>
    <tr><td><strong>Manjaro ARM</strong></td><td>Pi 4, 5</td><td>Arch-based rolling release</td></tr>
    <tr><td><strong>Fedora</strong></td><td>Pi 3+, 4, 5</td><td>Workstation, SELinux</td></tr>
    <tr><td><strong>DietPi</strong></td><td>All Pi + many SBCs</td><td>Ultra-lightweight, optimized</td></tr>
  </tbody>
</table>
<h3>Special Purpose</h3>
<table class="wiki-table">
  <thead><tr><th>OS</th><th>Purpose</th></tr></thead>
  <tbody>
    <tr><td><strong>LibreELEC / OSMC</strong></td><td>Kodi media center</td></tr>
    <tr><td><strong>Home Assistant OS</strong></td><td>Smart home automation platform</td></tr>
    <tr><td><strong>OctoPi</strong></td><td>3D printer management (OctoPrint)</td></tr>
    <tr><td><strong>RetroPie / Recalbox</strong></td><td>Retro gaming emulation</td></tr>
    <tr><td><strong>Kali Linux</strong></td><td>Security and pentesting</td></tr>
    <tr><td><strong>Ubuntu Core</strong></td><td>Snap-based IoT deployments</td></tr>
  </tbody>
</table>
<h3>Choosing an OS</h3>
<ul>
  <li><strong>First time?</strong> Raspberry Pi OS or Ubuntu &mdash; best documentation and community support</li>
  <li><strong>Headless server?</strong> DietPi or Ubuntu Server &mdash; minimal footprint</li>
  <li><strong>Media center?</strong> LibreELEC &mdash; boots straight into Kodi</li>
  <li><strong>Smart home?</strong> Home Assistant OS &mdash; dedicated appliance image</li>
</ul>`
  },
  {
    id: 'scooter-fw',
    title: 'Scooter Firmware',
    summary: 'Custom firmware (CFW) for Ninebot and Xiaomi scooters. What it changes and how it works.',
    category: 'os',
    related: ['scooters', 'safety', 'ebikes'],
    body: `<p>Custom firmware (CFW) replaces the stock software on scooter controllers, dashboards, and battery management systems.</p>
<h3>What CFW Can Change</h3>
<ul>
  <li><strong>Speed limits:</strong> Remove or adjust the factory speed cap</li>
  <li><strong>Acceleration curve:</strong> Smoother or more aggressive throttle response</li>
  <li><strong>Braking strength:</strong> Adjust regenerative braking intensity</li>
  <li><strong>Motor start speed:</strong> Set the minimum speed before the motor engages</li>
  <li><strong>Battery management:</strong> Adjust voltage cutoff and power limits</li>
  <li><strong>Dashboard display:</strong> Customize speed, battery, and mode indicators</li>
</ul>
<h3>Firmware Sources</h3>
<table class="wiki-table">
  <thead><tr><th>Source</th><th>Scooters</th><th>Notes</th></tr></thead>
  <tbody>
    <tr><td><strong>max.cfw.sh</strong></td><td>Ninebot Max G30 family</td><td>Most mature CFW generator</td></tr>
    <tr><td><strong>ScooterHacking Utility</strong></td><td>Ninebot ES, Xiaomi M365</td><td>Android app for BLE flashing</td></tr>
    <tr><td><strong>SHFW</strong></td><td>Various Ninebot/Xiaomi</td><td>ScooterHacking firmware patches</td></tr>
  </tbody>
</table>
<h3>Components</h3>
<p>Most scooters have three separate microcontrollers that can each be flashed:</p>
<ul>
  <li><strong>ESC (Electronic Speed Controller):</strong> Controls the motor. ST-Link required for deep flashing.</li>
  <li><strong>Dashboard:</strong> Handles display and button input. Flashed via BLE.</li>
  <li><strong>BMS (Battery Management System):</strong> Manages charging and cell balancing. Flashed via BLE.</li>
</ul>`
  },
  // ── Flashing & Rooting ──
  {
    id: 'bootloader',
    title: 'Bootloader',
    summary: 'The first software that runs on your device. Unlocking it is the gateway to custom software.',
    category: 'flashing',
    related: ['rom', 'recovery', 'brick'],
    body: `<p>The bootloader is the first piece of software that runs when you turn on your device. It decides which operating system to load.</p>
<p>Most manufacturers <strong>lock</strong> the bootloader so you can only run their official software. Unlocking it lets you install custom ROMs and recoveries.</p>
<h3>Why unlock?</h3>
<ul>
  <li>Install custom operating systems (ROMs)</li>
  <li>Flash a custom recovery like TWRP</li>
  <li>Gain full control over your device</li>
</ul>
<h3>What to know first</h3>
<ul>
  <li>Unlocking usually <strong>wipes all data</strong> on the device</li>
  <li>Some manufacturers require requesting an unlock code</li>
  <li>A few devices cannot be unlocked at all</li>
</ul>
<h3>Xiaomi bootloader unlock on Linux</h3>
<p>Xiaomi uses a token-based unlock system. On Linux, use <code>MiUnlockTool</code> (<code>pip install miunlock</code>):</p>
<ol>
  <li>Check eligibility: <code>fastboot flashing get_unlock_ability</code> must return <code>1</code></li>
  <li>Login with any Mi account (2FA may be required)</li>
  <li>The tool sends the device token to Xiaomi's servers and receives an unlock key</li>
  <li>The key is staged via fastboot and the bootloader unlocks</li>
</ol>
<p><strong>Note:</strong> Xiaomi may impose a waiting period of 7-30 days for new devices. The 2FA email codes are rate-limited (~5/day).</p>`
  },
  {
    id: 'rom',
    title: 'ROMs',
    summary: 'The operating system on your device. Custom ROMs replace the manufacturer\'s software.',
    category: 'flashing',
    related: ['bootloader', 'recovery', 'custom-os'],
    body: `<p>A ROM (Read-Only Memory image) is the operating system installed on your device.</p>
<h3>Stock vs. Custom</h3>
<ul>
  <li><strong>Stock ROM</strong> &mdash; the OS that came with your device from the manufacturer</li>
  <li><strong>Custom ROM</strong> &mdash; an alternative OS built by the community, such as LineageOS, /e/OS, or GrapheneOS</li>
</ul>
<h3>Why use a custom ROM?</h3>
<ul>
  <li>Extend the life of older devices with continued updates</li>
  <li>Improve privacy by removing manufacturer tracking</li>
  <li>Remove bloatware and unnecessary apps</li>
  <li>Get features your stock OS doesn't offer</li>
</ul>`
  },
  {
    id: 'recovery',
    title: 'Custom Recovery',
    summary: 'A toolkit that runs before your OS boots. Used to install ROMs, make backups, and more.',
    category: 'flashing',
    related: ['rom', 'bootloader', 'sideload'],
    body: `<p>Recovery mode is a special boot environment separate from your main OS. The stock recovery is limited, but a <strong>custom recovery</strong> like TWRP gives you powerful features.</p>
<h3>What can you do with it?</h3>
<ul>
  <li>Install custom ROMs and mods</li>
  <li>Make full device backups (NANDroid backups)</li>
  <li>Wipe partitions and caches</li>
  <li>Access the file system</li>
</ul>
<p>Think of it as a toolkit that runs before your phone boots up.</p>`
  },
  {
    id: 'root',
    title: 'Root Access',
    summary: 'Full administrator control over your device, similar to "admin" on a computer.',
    category: 'flashing',
    related: ['bootloader', 'rom', 'partition'],
    body: `<p>Root access gives you full administrator control over your device. By default, Android restricts what apps and users can do.</p>
<h3>What root enables</h3>
<ul>
  <li>Remove system apps and bloatware</li>
  <li>Use advanced firewalls and automation tools</li>
  <li>Customize the system at any level</li>
  <li>Run apps that need deeper system access</li>
</ul>
<h3>How it works</h3>
<p>Tools like <strong>Magisk</strong> provide "systemless" root &mdash; they don't modify the system partition, which makes root easier to manage and hide from apps that check for it.</p>`
  },
  {
    id: 'adb',
    title: 'ADB (Android Debug Bridge)',
    summary: 'The bridge between your computer and Android device. Core tool for sideloading, debugging, and device management.',
    category: 'tools',
    related: ['sideload', 'fastboot-tool', 'recovery', 'heimdall-tool'],
    body: `<p><strong>ADB (Android Debug Bridge)</strong> is a command-line tool from Google's Android SDK that lets your computer communicate with an Android device over USB or Wi-Fi. It is the most fundamental tool in OSmosis for Android device management.</p>
<h3>What it does</h3>
<p>ADB creates a client-server connection between your computer and a connected Android device. Once connected, you can:</p>
<ul>
  <li>Install and uninstall apps (<code>adb install</code>, <code>adb uninstall</code>)</li>
  <li>Push and pull files (<code>adb push</code>, <code>adb pull</code>)</li>
  <li>Run shell commands on the device (<code>adb shell</code>)</li>
  <li>Sideload ROM and update ZIPs through recovery (<code>adb sideload</code>)</li>
  <li>Reboot into different modes (<code>adb reboot bootloader</code>, <code>adb reboot recovery</code>)</li>
  <li>Take screenshots and record the screen</li>
  <li>View device logs in real time (<code>adb logcat</code>)</li>
</ul>
<h3>Device modes</h3>
<p>ADB detects devices in several modes, shown in the OSmosis sidebar with color-coded indicators:</p>
<table class="wiki-table">
  <thead><tr><th>Mode</th><th>Meaning</th><th>What you can do</th></tr></thead>
  <tbody>
    <tr><td><strong>device</strong></td><td>Normal Android, USB debugging on</td><td>Full ADB access</td></tr>
    <tr><td><strong>recovery</strong></td><td>Booted into recovery (TWRP, stock)</td><td>Sideload, file access</td></tr>
    <tr><td><strong>sideload</strong></td><td>Recovery's sideload mode active</td><td>Push ZIP files only</td></tr>
    <tr><td><strong>unauthorized</strong></td><td>USB debugging on, but not approved</td><td>Nothing until you tap "Allow" on device</td></tr>
  </tbody>
</table>
<h3>Role in OSmosis</h3>
<p>OSmosis uses ADB for:</p>
<ul>
  <li><strong>Device detection</strong> &mdash; polling <code>adb devices</code> to show connected devices in the sidebar</li>
  <li><strong>Sideloading</strong> &mdash; pushing ROM ZIPs via <code>adb sideload</code> in the Sideload tool</li>
  <li><strong>App installation</strong> &mdash; batch-installing APKs in the Apps tool</li>
  <li><strong>Rebooting</strong> &mdash; switching device into recovery, bootloader, or download mode</li>
  <li><strong>Pre-flight checks</strong> &mdash; verifying USB debugging is enabled and the device is authorized</li>
</ul>
<h3>Setup</h3>
<p>Enable <strong>USB Debugging</strong> in your device's Developer Options (tap Build Number 7 times to unlock Developer Options), then connect via USB. On first connection, tap <strong>Allow</strong> on the device's USB debugging prompt. OSmosis handles all ADB communication automatically during workflows.</p>
<h3>Troubleshooting</h3>
<ul>
  <li><strong>Device shows "unauthorized":</strong> Check the device screen for the USB debugging authorization dialog</li>
  <li><strong>Device not detected at all:</strong> Try a different USB cable (data, not charge-only), different port, or restart the ADB server with <code>adb kill-server && adb start-server</code></li>
  <li><strong>Stale sessions:</strong> After disconnecting, old ADB sessions can linger. OSmosis auto-clears these but you can force it with <code>adb disconnect</code></li>
</ul>`
  },
  {
    id: 'brick',
    title: 'Bricking',
    summary: 'When a device stops working after a bad flash. Usually recoverable.',
    category: 'flashing',
    related: ['safety', 'partition', 'bootloader'],
    body: `<p>A "bricked" device is one that won't boot or function properly.</p>
<h3>Types</h3>
<ul>
  <li><strong>Soft brick</strong> &mdash; stuck in a boot loop or won't start the OS. Usually fixable by reflashing firmware through recovery or download mode.</li>
  <li><strong>Hard brick</strong> &mdash; the device won't turn on at all. Much harder to recover, sometimes requires special hardware tools.</li>
</ul>
<p>OSmosis includes safety checks and recovery tools to help prevent and fix bricking.</p>`
  },
  {
    id: 'partition',
    title: 'Partitions',
    summary: 'How your device\'s storage is divided into sections, each with a specific job.',
    category: 'flashing',
    related: ['bootloader', 'recovery', 'safety'],
    body: `<p>Your device's storage is divided into partitions, each with a specific purpose:</p>
<table class="wiki-table">
  <tr><td><strong>boot</strong></td><td>Kernel and startup files</td></tr>
  <tr><td><strong>system</strong></td><td>The operating system</td></tr>
  <tr><td><strong>data</strong></td><td>Your apps and personal files</td></tr>
  <tr><td><strong>recovery</strong></td><td>Recovery environment</td></tr>
  <tr><td><strong>EFS</strong></td><td>Device identity (IMEI, serial)</td></tr>
</table>
<p>When flashing firmware, you're writing new data to specific partitions. Always back up critical partitions like <strong>EFS</strong> before making changes &mdash; losing your IMEI can disable cellular connectivity.</p>`
  },
  {
    id: 'sideload',
    title: 'Sideloading',
    summary: 'Installing software from your computer to your device over USB.',
    category: 'flashing',
    related: ['adb', 'rom', 'recovery'],
    body: `<p>Sideloading means installing software on your device from a source other than the official app store &mdash; typically by pushing a file over USB.</p>
<h3>How ADB sideloading works</h3>
<ol>
  <li>Boot into recovery mode</li>
  <li>Select "ADB sideload" in the recovery menu</li>
  <li>Push the ROM or update ZIP from your computer</li>
</ol>
<p>OSmosis automates this process during flashing workflows.</p>`
  },
  {
    id: 'safety',
    title: 'Safety Tips',
    summary: 'Essential precautions to take before flashing anything on your device.',
    category: 'flashing',
    related: ['brick', 'partition', 'scooters'],
    body: `<ul class="wiki-checklist">
  <li><strong>Always back up</strong> before flashing &mdash; especially EFS/IMEI data</li>
  <li><strong>Charge to at least 50%</strong> before starting</li>
  <li><strong>Use a good USB cable</strong> &mdash; cheap or damaged cables cause failed flashes</li>
  <li><strong>Never unplug during a flash</strong> &mdash; this is the #1 cause of soft bricks</li>
  <li><strong>Download from official sources</strong> &mdash; verify checksums when possible</li>
  <li><strong>Read device-specific instructions</strong> &mdash; not all devices work the same way</li>
</ul>`
  },
  {
    id: 'lfs',
    title: 'Linux From Scratch',
    summary: 'Build a complete Linux OS entirely from source code. Learn how every piece fits together.',
    category: 'os-builder',
    related: ['lfs-stages', 'os-builder', 'cross-compilation'],
    body: `<p><strong>Linux From Scratch</strong> (LFS) is a project that teaches you how to build a complete Linux operating system entirely from source code.</p>
<p>Instead of installing a pre-made distribution, you compile every component yourself &mdash; from the kernel and C library to the shell and package manager.</p>
<h3>What is it?</h3>
<p>LFS is not a distribution &mdash; it's a <strong>book</strong> (available free online) that walks you through the process step by step. A typical build produces a bootable system with around 80 packages.</p>
<h3>Related projects</h3>
<ul>
  <li><strong>BLFS</strong> (Beyond LFS) &mdash; adds graphical environments and applications</li>
  <li><strong>CLFS</strong> (Cross LFS) &mdash; cross-compilation for different architectures</li>
  <li><strong>ALFS</strong> (Automated LFS) &mdash; scripts that automate the build</li>
</ul>`
  },
  {
    id: 'lfs-why',
    title: 'Why Build From Scratch?',
    summary: 'Total control, minimal footprint, and the deepest possible understanding of Linux.',
    category: 'os-builder',
    related: ['lfs', 'lfs-stages', 'os-builder'],
    body: `<p>Building from scratch is the most educational path to understanding Linux. But there are practical reasons too:</p>
<ul>
  <li><strong>Total control</strong> &mdash; you decide every package, every compile flag, every configuration option</li>
  <li><strong>Minimal footprint</strong> &mdash; an LFS system can be as small as 300 MB with no bloatware</li>
  <li><strong>Security through understanding</strong> &mdash; you know exactly what's running and why</li>
  <li><strong>Embedded and appliance use</strong> &mdash; ideal for kiosks, NAS boxes, routers, and single-purpose devices</li>
  <li><strong>Learning</strong> &mdash; there's no faster way to learn how Linux fits together</li>
</ul>`
  },
  {
    id: 'lfs-stages',
    title: 'Stages of an LFS Build',
    summary: 'The seven steps from host preparation to a bootable, self-hosting Linux system.',
    category: 'os-builder',
    related: ['lfs', 'lfs-why', 'os-builder'],
    body: `<ol>
  <li><strong>Host preparation</strong> &mdash; set up a partition, create a build user, verify required tools</li>
  <li><strong>Temporary toolchain</strong> &mdash; cross-compile a minimal toolchain (binutils, GCC, glibc) independent of the host</li>
  <li><strong>Chroot environment</strong> &mdash; enter a chroot and build the rest in isolation</li>
  <li><strong>Base system</strong> &mdash; compile core packages: kernel, coreutils, bash, grep, sed, and ~60 more</li>
  <li><strong>Kernel configuration</strong> &mdash; configure and compile a kernel for your hardware</li>
  <li><strong>Bootloader</strong> &mdash; install GRUB and generate boot configuration</li>
  <li><strong>Final configuration</strong> &mdash; set up fstab, networking, hostname, timezone, locale, and users</li>
</ol>
<p>After these stages you have a bootable, self-hosting Linux system.</p>`
  },
  {
    id: 'os-builder',
    title: 'OSmosis OS Builder',
    summary: 'Assemble custom OS images from a graphical interface. No command line required.',
    category: 'os-builder',
    related: ['os-builder-bases', 'os-builder-profiles', 'lfs'],
    body: `<p>The <strong>OS Builder</strong> lets you assemble custom operating system images visually.</p>
<h3>Build paths</h3>
<ul>
  <li><strong>From a base distro</strong> &mdash; start with Ubuntu, Debian, Arch, Alpine, Fedora, or NixOS and customize</li>
  <li><strong>From scratch (LFS)</strong> &mdash; automated Linux From Scratch pipeline <em>(Planned)</em></li>
  <li><strong>From a template</strong> &mdash; community-shared profiles for common use cases <em>(Planned)</em></li>
</ul>
<p>Configure architecture, packages, desktop environment, users, and networking, then get a flashable image for USB, SD card, or VM.</p>`
  },
  {
    id: 'os-builder-bases',
    title: 'Supported Base Distros',
    summary: 'Six distributions to build from: Ubuntu, Debian, Arch, Alpine, Fedora, and NixOS.',
    category: 'os-builder',
    related: ['os-builder', 'os-builder-profiles', 'debootstrap'],
    body: `<table class="wiki-table">
  <thead>
    <tr><th>Distro</th><th>Build tool</th><th>Architectures</th><th>Best for</th></tr>
  </thead>
  <tbody>
    <tr><td>Ubuntu</td><td>debootstrap</td><td>x86_64, ARM64</td><td>Desktop, general purpose</td></tr>
    <tr><td>Debian</td><td>debootstrap</td><td>x86_64, ARM64, armhf, RISC-V</td><td>Servers, embedded</td></tr>
    <tr><td>Arch Linux</td><td>pacstrap</td><td>x86_64</td><td>Rolling release</td></tr>
    <tr><td>Alpine</td><td>apk</td><td>x86_64, ARM64, armv7</td><td>Containers, minimal</td></tr>
    <tr><td>Fedora</td><td>dnf</td><td>x86_64, ARM64</td><td>Workstation, SELinux</td></tr>
    <tr><td>NixOS</td><td>nix-build</td><td>x86_64, ARM64</td><td>Reproducible builds</td></tr>
  </tbody>
</table>`
  },
  {
    id: 'os-builder-profiles',
    title: 'Build Profiles & Output',
    summary: 'Save, share, and reproduce OS builds. Export as disk images, tarballs, or ISOs.',
    category: 'os-builder',
    related: ['os-builder', 'os-builder-bases', 'ipfs-caching'],
    body: `<p>A <strong>build profile</strong> captures every choice needed to reproduce a build: base distro, architecture, packages, desktop, users, networking, and more.</p>
<h3>Output formats</h3>
<ul>
  <li><strong>.img</strong> &mdash; raw disk image for USB or SD card</li>
  <li><strong>.tar.gz</strong> &mdash; root filesystem for containers or chroots</li>
  <li><strong>.iso</strong> &mdash; bootable media for live/installer use</li>
</ul>
<h3>Target devices</h3>
<p>Generic PC (x86_64), Generic ARM64, Raspberry Pi 3/4/5, Pi Zero 2 W, and VMs (QEMU/VirtualBox).</p>`
  },
  {
    id: 'debootstrap',
    title: 'debootstrap & pacstrap',
    summary: 'The tools that bootstrap a minimal Debian/Ubuntu or Arch system from nothing.',
    category: 'os-builder',
    related: ['os-builder-bases', 'os-builder', 'cross-compilation'],
    body: `<h3>debootstrap</h3>
<p>Installs a minimal Debian or Ubuntu system into a directory by downloading and unpacking the base packages. The OS Builder uses it for Debian and Ubuntu builds, then applies your configuration on top.</p>
<p><strong>preseed</strong> is Debian's automation format &mdash; an answer file that pre-fills installer questions. OSmosis generates this from your build profile.</p>
<h3>pacstrap</h3>
<p>The Arch Linux equivalent. Installs a minimal Arch system using pacman, then runs configuration inside the chroot &mdash; the same steps as the Arch install guide, but automated.</p>`
  },
  {
    id: 'cross-compilation',
    title: 'Cross-Compilation',
    summary: 'Building software on one architecture to run on another, like ARM images from an x86 PC.',
    category: 'os-builder',
    related: ['os-builder-bases', 'lfs', 'os-builder'],
    body: `<p><strong>Cross-compilation</strong> means building software on one architecture (e.g., x86_64) to run on a different one (e.g., ARM64 or RISC-V).</p>
<p>The OS Builder handles this automatically using QEMU user-mode emulation to run target binaries inside a chroot on your host machine.</p>
<h3>Supported architectures</h3>
<ul>
  <li><strong>x86_64</strong> (amd64)</li>
  <li><strong>ARM64</strong> (aarch64)</li>
  <li><strong>ARMv7</strong> (armhf)</li>
  <li><strong>RISC-V 64</strong> (riscv64, Debian only)</li>
</ul>`
  },
  {
    id: 'ipfs-caching',
    title: 'IPFS Layer Caching',
    summary: 'Speed up repeated builds by caching base system layers on IPFS.',
    category: 'os-builder',
    related: ['os-builder', 'os-builder-profiles', 'os-builder-bases'],
    body: `<p>Building an OS image can be slow. The OS Builder uses <strong>IPFS layer caching</strong> to speed up repeated builds.</p>
<h3>How it works</h3>
<ol>
  <li>After a successful build, base layers are compressed and pinned to IPFS</li>
  <li>On the next build with the same base/suite/architecture, the cached layer is restored instead of rebuilt</li>
  <li>Build profiles record which CIDs were used, making builds <strong>reproducible</strong></li>
</ol>
<p>Caching is automatic when IPFS is available. Anyone with the same profile and IPFS access can reconstruct the same image.</p>`
  },
  // ── Tools & Protocols ──
  {
    id: 'heimdall-tool',
    title: 'Heimdall',
    summary: 'Open-source Samsung flashing tool. Replaces Odin on Linux and macOS for Download Mode flashing.',
    category: 'tools',
    related: ['adb', 'fastboot-tool', 'android-devices', 'brick'],
    body: `<p><strong>Heimdall</strong> is an open-source, cross-platform tool for flashing firmware on Samsung devices via <strong>Download Mode</strong> (also called Odin mode). It is the Linux/macOS alternative to Samsung's proprietary Odin tool (Windows-only).</p>
<h3>What it does</h3>
<p>Heimdall communicates with Samsung's bootloader protocol over USB. It can:</p>
<ul>
  <li>Flash partition images (boot, system, recovery, etc.) to Samsung devices</li>
  <li>Read the device's PIT (Partition Information Table) to understand the storage layout</li>
  <li>Flash multi-file firmware packages (BL, AP, CP, CSC)</li>
  <li>Print device info (serial, sales code, hardware revision)</li>
</ul>
<h3>Download Mode</h3>
<p>Samsung devices have a special "Download Mode" that Heimdall connects to. To enter it:</p>
<ol>
  <li>Power off the device completely</li>
  <li>Press and hold <strong>Volume Down + Power</strong> (varies by model; some require a third button)</li>
  <li>When you see a warning screen, press <strong>Volume Up</strong> to continue into Download Mode</li>
  <li>The screen shows a "Downloading..." message &mdash; the device is ready for Heimdall</li>
</ol>
<h3>Role in OSmosis</h3>
<p>OSmosis uses Heimdall for:</p>
<ul>
  <li><strong>Flash Stock</strong> &mdash; restoring factory Samsung firmware (AP, BL, CP, CSC partitions)</li>
  <li><strong>Flash Recovery</strong> &mdash; installing TWRP on Samsung devices via the recovery partition</li>
  <li><strong>PIT reading</strong> &mdash; understanding the device's partition layout before flashing</li>
  <li><strong>Pre-flight checks</strong> &mdash; detecting if a Samsung device is in Download Mode</li>
</ul>
<h3>Heimdall vs. Odin</h3>
<table class="wiki-table">
  <thead><tr><th>Feature</th><th>Heimdall</th><th>Odin</th></tr></thead>
  <tbody>
    <tr><td>Platform</td><td>Linux, macOS, Windows</td><td>Windows only</td></tr>
    <tr><td>License</td><td>Open source (MIT)</td><td>Proprietary (leaked)</td></tr>
    <tr><td>GUI</td><td>Optional (heimdall-frontend)</td><td>Yes</td></tr>
    <tr><td>Reliability</td><td>Very stable on Linux</td><td>Can have driver issues</td></tr>
  </tbody>
</table>
<h3>Troubleshooting</h3>
<ul>
  <li><strong>Device not detected:</strong> Check udev rules on Linux (<code>/etc/udev/rules.d/</code>). Samsung devices need a rule for the Download Mode USB VID/PID.</li>
  <li><strong>Download Mode loop:</strong> If the device reboots back into Download Mode after flashing, try a different CSC file or re-flash with the HOME_CSC variant to preserve data.</li>
  <li><strong>Transfer stalls:</strong> Use a short, high-quality USB cable directly connected to the computer (not through a hub).</li>
</ul>`
  },
  {
    id: 'fastboot-tool',
    title: 'Fastboot',
    summary: 'Google\'s bootloader-level flash protocol. Used for Pixel, OnePlus, Xiaomi, Motorola, and most non-Samsung Android devices.',
    category: 'tools',
    related: ['adb', 'heimdall-tool', 'bootloader', 'android-devices'],
    body: `<p><strong>Fastboot</strong> is a protocol and command-line tool from Google's Android SDK that communicates directly with a device's bootloader. It is the standard flashing method for most non-Samsung Android devices.</p>
<h3>What it does</h3>
<p>Fastboot operates at a lower level than ADB &mdash; it talks to the bootloader, not to Android. It can:</p>
<ul>
  <li>Flash partition images: boot, system, vendor, recovery, and more</li>
  <li>Unlock and relock the bootloader</li>
  <li>Erase partitions</li>
  <li>Boot a temporary image without flashing (<code>fastboot boot</code>)</li>
  <li>Flash full factory images via <code>fastboot flashall</code> or <code>fastboot update</code></li>
</ul>
<h3>Bootloader mode</h3>
<p>Fastboot requires the device to be in bootloader (fastboot) mode:</p>
<ol>
  <li>From Android: <code>adb reboot bootloader</code></li>
  <li>From powered off: hold <strong>Volume Down + Power</strong> (most devices)</li>
  <li>The device shows a "Fastboot Mode" or bootloader screen</li>
</ol>
<h3>Role in OSmosis</h3>
<p>OSmosis uses Fastboot for:</p>
<ul>
  <li><strong>Flash Stock</strong> &mdash; restoring factory firmware on Pixel, OnePlus, Xiaomi, Motorola, Sony, Fairphone, and Nothing devices</li>
  <li><strong>Flash Recovery</strong> &mdash; flashing TWRP or other custom recoveries to the recovery/boot partition</li>
  <li><strong>Bootloader unlock</strong> &mdash; sending the <code>fastboot flashing unlock</code> command (and OEM-specific variants)</li>
  <li><strong>Pixel flashing</strong> &mdash; dedicated Pixel workflow using Google's factory image scripts adapted for Linux</li>
  <li><strong>Xiaomi MiUnlock</strong> &mdash; extracting device tokens and sending unlock keys via fastboot</li>
  <li><strong>Pre-flight checks</strong> &mdash; detecting if a device is in fastboot mode</li>
</ul>
<h3>Fastboot vs. Fastbootd</h3>
<table class="wiki-table">
  <thead><tr><th>Feature</th><th>Fastboot (bootloader)</th><th>Fastbootd (userspace)</th></tr></thead>
  <tbody>
    <tr><td>Runs in</td><td>Bootloader</td><td>Recovery/userspace</td></tr>
    <tr><td>Required for</td><td>Boot, dtbo, vbmeta partitions</td><td>Dynamic (super) partitions on A/B devices</td></tr>
    <tr><td>Enter via</td><td><code>adb reboot bootloader</code></td><td><code>adb reboot fastboot</code></td></tr>
  </tbody>
</table>
<p>Newer devices with dynamic partitions (Pixel 4+, OnePlus 8+) need <strong>fastbootd</strong> for system/vendor partitions. OSmosis handles this transition automatically.</p>
<h3>Troubleshooting</h3>
<ul>
  <li><strong>Device not detected:</strong> Check USB cable (data-capable), try <code>fastboot devices</code>. On Linux, add udev rules for your device.</li>
  <li><strong>"FAILED (remote: unknown command)":</strong> The bootloader may not support that command. Some manufacturers restrict fastboot commands on locked bootloaders.</li>
  <li><strong>Flashing locked device:</strong> Unlock the bootloader first. This wipes all data.</li>
</ul>`
  },
  {
    id: 'twrp-tool',
    title: 'TWRP (Team Win Recovery Project)',
    summary: 'The most popular custom recovery for Android. Enables ROM installation, backups, and full device management.',
    category: 'tools',
    related: ['recovery', 'adb', 'heimdall-tool', 'fastboot-tool'],
    body: `<p><strong>TWRP</strong> (Team Win Recovery Project) is a custom recovery environment for Android devices. It replaces the limited stock recovery with a touch-based interface that provides full device management.</p>
<h3>What it does</h3>
<ul>
  <li><strong>Install ZIPs:</strong> Flash custom ROMs, Magisk, GApps, mods, and updates from ZIP files</li>
  <li><strong>NANDroid backups:</strong> Create full partition-level backups (boot, system, data, EFS) that can be restored exactly</li>
  <li><strong>Wipe &amp; format:</strong> Clear data, cache, dalvik, or format partitions</li>
  <li><strong>File manager:</strong> Browse and modify the device filesystem</li>
  <li><strong>ADB sideload:</strong> Receive files from a computer via <code>adb sideload</code></li>
  <li><strong>Terminal:</strong> Run shell commands directly on the device</li>
</ul>
<h3>Role in OSmosis</h3>
<p>OSmosis uses TWRP as the bridge between your computer and the device for ROM installation:</p>
<ul>
  <li><strong>Flash Recovery tool</strong> &mdash; installs TWRP itself onto the device (via Heimdall on Samsung, via Fastboot on others)</li>
  <li><strong>Sideload tool</strong> &mdash; pushes ROM ZIPs to the device while TWRP's sideload mode is active</li>
  <li><strong>Pre-flight checks</strong> &mdash; detects when a device is in TWRP recovery mode</li>
  <li><strong>Backup guidance</strong> &mdash; the wizard recommends NANDroid backups before any destructive flash</li>
</ul>
<h3>TWRP vs. stock recovery</h3>
<table class="wiki-table">
  <thead><tr><th>Feature</th><th>TWRP</th><th>Stock Recovery</th></tr></thead>
  <tbody>
    <tr><td>Install custom ROMs</td><td>Yes</td><td>No</td></tr>
    <tr><td>Full backups</td><td>Yes (NANDroid)</td><td>No</td></tr>
    <tr><td>ADB sideload</td><td>Yes</td><td>Limited (OTA only)</td></tr>
    <tr><td>File browser</td><td>Yes</td><td>No</td></tr>
    <tr><td>Touch interface</td><td>Yes</td><td>Volume/Power keys only</td></tr>
  </tbody>
</table>
<h3>Important notes</h3>
<ul>
  <li><strong>Device-specific builds:</strong> TWRP must be compiled for each device. Using the wrong build can brick your device. OSmosis matches the correct TWRP image to your device automatically.</li>
  <li><strong>Replicant ROMs:</strong> Replicant's ROM ZIPs require Replicant's own recovery, not standard TWRP. OSmosis warns you about this during the install workflow.</li>
  <li><strong>Encryption:</strong> On devices with encrypted storage, TWRP may ask for your PIN/password on boot to decrypt <code>/data</code>.</li>
</ul>`
  },
  {
    id: 'edl-tool',
    title: 'EDL (Qualcomm Emergency Download)',
    summary: 'Low-level rescue mode for Qualcomm-powered devices. Last resort for bricked phones that won\'t enter any other mode.',
    category: 'tools',
    related: ['fastboot-tool', 'adb', 'brick', 'android-devices'],
    body: `<p><strong>EDL</strong> (Emergency Download mode) is a Qualcomm-specific low-level flashing protocol built into the SoC hardware. It operates below the bootloader and is often the last resort for recovering bricked devices.</p>
<h3>What it does</h3>
<p>EDL communicates directly with the Qualcomm chip's Primary Bootloader (PBL) over USB. It can:</p>
<ul>
  <li>Flash raw partition images even when the bootloader is corrupted</li>
  <li>Unbrick devices that won't enter any other mode (no fastboot, no recovery, no download)</li>
  <li>Read and write individual partitions</li>
  <li>Restore stock firmware on hard-bricked Qualcomm devices</li>
</ul>
<h3>How to enter EDL mode</h3>
<p>Methods vary by device:</p>
<ul>
  <li><strong>ADB command:</strong> <code>adb reboot edl</code> (if the device is responsive)</li>
  <li><strong>Key combo:</strong> Some devices have a hardware button sequence (varies by manufacturer)</li>
  <li><strong>Test points:</strong> Shorting specific pads on the device's circuit board (requires opening the device)</li>
  <li><strong>Forced entry:</strong> On some devices, a damaged bootloader will automatically fall back to EDL</li>
</ul>
<h3>Firehose programmers</h3>
<p>EDL requires a <strong>firehose programmer</strong> &mdash; a signed binary (usually <code>.mbn</code> or <code>.elf</code>) that Qualcomm provides to manufacturers. This programmer authenticates the flashing session. Without a valid programmer for your chipset, EDL will not accept commands.</p>
<p>Programmers are typically found in:</p>
<ul>
  <li>Official firmware packages from the manufacturer</li>
  <li>Leaked collections for specific chipsets (e.g., MSM8953, SDM845, SM8150)</li>
</ul>
<h3>Role in OSmosis</h3>
<p>OSmosis uses EDL as a recovery option for:</p>
<ul>
  <li><strong>Hard-bricked Qualcomm devices</strong> that won't respond to ADB or fastboot</li>
  <li><strong>Cross-flashed Xiaomi devices</strong> with the wrong region firmware that can't be recovered via MIAssistant</li>
  <li><strong>Bootloader recovery</strong> when the bootloader itself is corrupted</li>
</ul>
<h3>Limitations</h3>
<ul>
  <li>Only works on <strong>Qualcomm</strong> SoCs (not MediaTek, Exynos, or Tensor)</li>
  <li>Requires a valid <strong>firehose programmer</strong> for the specific chipset</li>
  <li>Some manufacturers have locked EDL on newer devices, requiring authorization from the manufacturer</li>
</ul>`
  },
  {
    id: 'esptool-tool',
    title: 'esptool',
    summary: 'Flash firmware to ESP32, ESP8266, and all Espressif microcontrollers over USB serial.',
    category: 'tools',
    related: ['picotool-tool', 'arduino-tool', 'microcontrollers', 'openocd-tool'],
    body: `<p><strong>esptool</strong> is a Python-based command-line tool for flashing firmware to <strong>Espressif</strong> microcontrollers (ESP32, ESP8266, ESP32-S2, ESP32-S3, ESP32-C3, ESP32-H2, and more).</p>
<h3>What it does</h3>
<ul>
  <li>Flash compiled firmware binaries (<code>.bin</code>) to the chip's flash memory</li>
  <li>Erase flash memory (full or partial)</li>
  <li>Read flash contents back for backup</li>
  <li>Detect chip type, flash size, and MAC address</li>
  <li>Manage bootloader and partition table flashing</li>
</ul>
<h3>How it works</h3>
<p>Espressif chips have a built-in <strong>serial bootloader</strong> in ROM. When the chip enters download mode (GPIO0 held low during reset, or automatic via USB-CDC on newer boards), esptool communicates over the USB-serial connection to write firmware.</p>
<p>Most modern ESP32 dev boards handle the download mode entry automatically &mdash; you just click "flash" and it works.</p>
<h3>Role in OSmosis</h3>
<p>OSmosis uses esptool in the <strong>Microcontroller</strong> workflow for:</p>
<ul>
  <li>Flashing pre-compiled firmware (Meshtastic, ESPHome, Tasmota, WLED, etc.)</li>
  <li>Flashing user-compiled Arduino or PlatformIO projects</li>
  <li>Erasing flash before installing new firmware</li>
  <li>Detecting connected ESP boards and their chip type</li>
</ul>
<h3>Common firmware targets</h3>
<table class="wiki-table">
  <thead><tr><th>Firmware</th><th>Purpose</th><th>Common Boards</th></tr></thead>
  <tbody>
    <tr><td><strong>Meshtastic</strong></td><td>Off-grid LoRa mesh networking</td><td>TTGO LoRa32, Heltec, RAK</td></tr>
    <tr><td><strong>ESPHome</strong></td><td>Home Assistant device integration</td><td>ESP32, ESP8266</td></tr>
    <tr><td><strong>Tasmota</strong></td><td>Smart home device firmware</td><td>ESP8266, ESP32</td></tr>
    <tr><td><strong>WLED</strong></td><td>LED strip controller</td><td>ESP32, ESP8266</td></tr>
  </tbody>
</table>`
  },
  {
    id: 'picotool-tool',
    title: 'picotool',
    summary: 'Flash and inspect firmware on Raspberry Pi Pico and RP2040/RP2350 boards.',
    category: 'tools',
    related: ['esptool-tool', 'arduino-tool', 'microcontrollers', 'dfu-tool'],
    body: `<p><strong>picotool</strong> is the official Raspberry Pi tool for flashing firmware to <strong>RP2040</strong> and <strong>RP2350</strong> microcontrollers (Raspberry Pi Pico, Pico W, Pico 2, and compatible boards).</p>
<h3>What it does</h3>
<ul>
  <li>Flash UF2 firmware files to the Pico</li>
  <li>Inspect firmware metadata (version, build info, features)</li>
  <li>Reboot the Pico into BOOTSEL mode from the command line</li>
  <li>Read back flash contents</li>
  <li>Verify firmware integrity</li>
</ul>
<h3>BOOTSEL mode</h3>
<p>The Pico has a simple flashing mechanism: hold the <strong>BOOTSEL</strong> button while plugging in USB. The Pico appears as a USB mass storage drive, and you can drag-and-drop a <code>.uf2</code> file to flash it. picotool provides a command-line alternative that's faster for automated workflows.</p>
<h3>Role in OSmosis</h3>
<p>OSmosis uses picotool in the <strong>Microcontroller</strong> workflow for:</p>
<ul>
  <li>Flashing firmware to Pico boards (MicroPython, CircuitPython, custom firmware)</li>
  <li>Detecting Pico boards in BOOTSEL mode</li>
  <li>Inspecting what firmware is currently loaded</li>
</ul>
<h3>Pico vs. Pico W vs. Pico 2</h3>
<table class="wiki-table">
  <thead><tr><th>Board</th><th>Chip</th><th>Key Feature</th></tr></thead>
  <tbody>
    <tr><td>Pico</td><td>RP2040 (dual Cortex-M0+)</td><td>Base board, 264 KB SRAM</td></tr>
    <tr><td>Pico W</td><td>RP2040 + CYW43439</td><td>Wi-Fi + Bluetooth</td></tr>
    <tr><td>Pico 2</td><td>RP2350 (Cortex-M33 + RISC-V)</td><td>Dual-architecture, 520 KB SRAM</td></tr>
  </tbody>
</table>`
  },
  {
    id: 'openocd-tool',
    title: 'OpenOCD',
    summary: 'JTAG/SWD debug probe interface for programming and debugging microcontrollers and SoCs.',
    category: 'tools',
    related: ['esptool-tool', 'dfu-tool', 'microcontrollers', 'sbc'],
    body: `<p><strong>OpenOCD</strong> (Open On-Chip Debugger) is an open-source tool that connects to microcontrollers and processors via <strong>JTAG</strong> or <strong>SWD</strong> debug interfaces using a hardware probe (ST-Link, J-Link, CMSIS-DAP, etc.).</p>
<h3>What it does</h3>
<ul>
  <li>Flash firmware to microcontrollers via debug probes (ST-Link, J-Link, Bus Pirate, etc.)</li>
  <li>Debug running programs with GDB integration</li>
  <li>Read and write chip registers and memory</li>
  <li>Erase and verify flash contents</li>
  <li>Unlock flash protection on locked chips</li>
</ul>
<h3>When it's needed</h3>
<p>Most boards can be flashed via USB bootloader (esptool, picotool, dfu-util). OpenOCD is needed when:</p>
<ul>
  <li>The chip has <strong>no USB bootloader</strong> (bare STM32, Nordic nRF, etc.)</li>
  <li>The USB bootloader is <strong>corrupted or locked</strong></li>
  <li>You need to <strong>debug</strong> running firmware (breakpoints, stepping)</li>
  <li>Flashing <strong>e-bike or scooter ESC boards</strong> that only expose SWD pads</li>
</ul>
<h3>Role in OSmosis</h3>
<p>OSmosis uses OpenOCD for:</p>
<ul>
  <li><strong>E-bike controllers</strong> &mdash; flashing open-source firmware to Bafang BBSHD/BBS02 and Tongsheng TSDZ2 ESC boards via ST-Link</li>
  <li><strong>Scooter ESCs</strong> &mdash; flashing STM32/AT32 motor controllers on Ninebot and Xiaomi scooters</li>
  <li><strong>STM32 boards</strong> &mdash; programming Blue Pill, Black Pill, Nucleo, and bare STM32 chips</li>
  <li><strong>Recovery</strong> &mdash; unbricking microcontrollers with corrupted bootloaders</li>
</ul>
<h3>Common debug probes</h3>
<table class="wiki-table">
  <thead><tr><th>Probe</th><th>Interface</th><th>Price</th><th>Notes</th></tr></thead>
  <tbody>
    <tr><td><strong>ST-Link V2</strong></td><td>SWD, JTAG</td><td>~$3-10</td><td>Most common for STM32. Clones work fine.</td></tr>
    <tr><td><strong>J-Link</strong></td><td>SWD, JTAG</td><td>$20-500</td><td>Fast, wide chip support. EDU version is affordable.</td></tr>
    <tr><td><strong>CMSIS-DAP</strong></td><td>SWD</td><td>~$5-15</td><td>Open standard. DAPLink firmware runs on Pico.</td></tr>
  </tbody>
</table>`
  },
  {
    id: 'dfu-tool',
    title: 'dfu-util',
    summary: 'Flash firmware over USB DFU (Device Firmware Upgrade) protocol. Used for STM32, flight controllers, and more.',
    category: 'tools',
    related: ['openocd-tool', 'esptool-tool', 'microcontrollers', 'arduino-tool'],
    body: `<p><strong>dfu-util</strong> is a command-line tool that flashes firmware to devices using the <strong>USB DFU</strong> (Device Firmware Upgrade) standard. Many microcontrollers and embedded devices have a built-in DFU bootloader in ROM.</p>
<h3>What it does</h3>
<ul>
  <li>Flash firmware binaries to devices in DFU mode</li>
  <li>List connected DFU-capable devices</li>
  <li>Upload (read back) firmware from devices</li>
  <li>Reset devices after flashing</li>
</ul>
<h3>How DFU works</h3>
<p>DFU is a USB standard (not vendor-specific). When a device enters DFU mode, it presents itself as a special USB device that accepts firmware uploads. No debug probe is needed &mdash; just a USB cable.</p>
<h3>Entering DFU mode</h3>
<p>The method varies by device:</p>
<ul>
  <li><strong>STM32:</strong> Hold the BOOT0 button/jumper while resetting, or use <code>dfu-util -e</code> from running firmware</li>
  <li><strong>Flight controllers:</strong> Connect while holding the boot button (often labeled "DFU" or "BOOT")</li>
  <li><strong>Apple T2 Macs:</strong> Special key sequence puts the T2 chip into DFU mode</li>
</ul>
<h3>Role in OSmosis</h3>
<p>OSmosis uses dfu-util for:</p>
<ul>
  <li><strong>STM32 boards</strong> in DFU mode (alternative to OpenOCD/ST-Link when USB is available)</li>
  <li><strong>Flight controllers</strong> &mdash; flashing Betaflight, INAV, and ArduPilot firmware</li>
  <li><strong>3D printer boards</strong> &mdash; some SKR and BTT boards use DFU for initial firmware install</li>
</ul>`
  },
  {
    id: 'arduino-tool',
    title: 'arduino-cli',
    summary: 'Command-line interface for the Arduino ecosystem. Compile and flash sketches across 100+ board types.',
    category: 'tools',
    related: ['esptool-tool', 'picotool-tool', 'microcontrollers', 'dfu-tool'],
    body: `<p><strong>arduino-cli</strong> is the official command-line tool for the Arduino ecosystem. It handles board detection, library management, sketch compilation, and firmware upload for a huge range of microcontroller boards.</p>
<h3>What it does</h3>
<ul>
  <li>Compile Arduino sketches (<code>.ino</code>) for any supported board</li>
  <li>Upload compiled firmware to connected boards</li>
  <li>Manage board support packages (cores) for different architectures</li>
  <li>Install and manage libraries</li>
  <li>Detect connected boards and their serial ports</li>
</ul>
<h3>How it works</h3>
<p>arduino-cli wraps the same toolchain as the Arduino IDE but without the GUI. It downloads the correct compiler (avr-gcc, arm-none-eabi-gcc, xtensa-gcc, etc.) for the target board, compiles the sketch, and uploads it via the appropriate protocol (serial, USB HID, DFU, etc.).</p>
<h3>Role in OSmosis</h3>
<p>OSmosis uses arduino-cli in the <strong>Microcontroller</strong> workflow for:</p>
<ul>
  <li>Compiling and uploading Arduino sketches to connected boards</li>
  <li>Installing board support packages for non-standard boards (Adafruit, Seeed, Teensy, etc.)</li>
  <li>Detecting connected Arduino-compatible boards</li>
</ul>
<h3>Supported board families</h3>
<table class="wiki-table">
  <thead><tr><th>Core</th><th>Boards</th><th>Architecture</th></tr></thead>
  <tbody>
    <tr><td>arduino:avr</td><td>Uno, Mega, Nano, Leonardo</td><td>ATmega AVR</td></tr>
    <tr><td>arduino:samd</td><td>Zero, MKR, Nano 33 IoT</td><td>ARM Cortex-M0+</td></tr>
    <tr><td>arduino:renesas_uno</td><td>Uno R4 Minima, Uno R4 WiFi</td><td>ARM Cortex-M4 + Cortex-M23</td></tr>
    <tr><td>esp32:esp32</td><td>All ESP32 boards</td><td>Xtensa / RISC-V</td></tr>
    <tr><td>rp2040:rp2040</td><td>Pico, Pico W</td><td>ARM Cortex-M0+</td></tr>
    <tr><td>adafruit:samd</td><td>Feather, ItsyBitsy, QT Py</td><td>ARM Cortex-M0+/M4</td></tr>
    <tr><td>Seeeduino:samd</td><td>XIAO, Wio Terminal</td><td>ARM Cortex-M0+</td></tr>
  </tbody>
</table>`
  },
  {
    id: 't2tool-tool',
    title: 't2tool',
    summary: 'Apple T2 security chip management. Query, back up, and restore T2 firmware via USB DFU.',
    category: 'tools',
    related: ['apple-t2', 't2-walkthrough', 'dfu-tool', 't2-troubleshoot'],
    body: `<p><strong>t2tool</strong> is a community-developed tool from the <a href="https://t2linux.org/" target="_blank" rel="noopener noreferrer">t2linux project</a> for communicating with Apple's T2 security chip over USB DFU. It enables backup, restore, and diagnostics of the T2 firmware on Intel Macs from 2018&ndash;2020.</p>
<h3>What it does</h3>
<ul>
  <li>Detect the T2 chip on the USB bus (VID:PID <code>05ac:1881</code>)</li>
  <li>Query T2 firmware version and status</li>
  <li>Back up T2 regions: firmware (bridgeOS), NVRAM, and Secure Enclave metadata</li>
  <li>Restore T2 regions from a previous backup with SHA-256 verification</li>
  <li>Diagnose T2-related boot problems</li>
</ul>
<h3>How it works</h3>
<p>t2tool communicates with the T2 while the Mac is in <strong>DFU mode</strong> &mdash; a special state where the T2 chip accepts USB commands. The Mac's screen stays completely black during this process. t2tool uses <code>libusb</code> to send low-level USB commands to the chip.</p>
<h3>Role in OSmosis</h3>
<p>OSmosis uses t2tool in the <strong>Apple T2 wizard step</strong> for:</p>
<ul>
  <li><strong>Detection</strong> &mdash; scanning the USB bus for T2 chips in DFU mode</li>
  <li><strong>Backup</strong> &mdash; saving firmware, NVRAM, and SEP regions to <code>~/.osmosis/t2-backups/</code></li>
  <li><strong>Restore</strong> &mdash; writing backed-up regions back to the T2 with checksum verification</li>
  <li><strong>Diagnostics</strong> &mdash; reading T2 firmware version and Secure Boot status</li>
</ul>
<h3>Requirements</h3>
<ul>
  <li><strong>Two computers:</strong> A host running OSmosis and the target Mac with the T2</li>
  <li><strong>USB-C data cable:</strong> Must support data transfer (not charge-only)</li>
  <li><strong>libusb:</strong> <code>sudo apt install libusb-1.0-0-dev</code> on Debian/Ubuntu</li>
  <li><strong>Correct USB port:</strong> Left Thunderbolt port closest to you on MacBooks; nearest to Ethernet on iMac</li>
</ul>`
  },
  {
    id: 'ipfs-tool',
    title: 'IPFS (InterPlanetary File System)',
    summary: 'Peer-to-peer content distribution. Enables decentralized firmware sharing, offline transfer, and community seeding.',
    category: 'tools',
    related: ['ipfs-caching', 'adb', 'fastboot-tool'],
    body: `<p><strong>IPFS</strong> (InterPlanetary File System) is a peer-to-peer protocol for storing and sharing files in a distributed network. Instead of downloading from a central server, you fetch content from the nearest peer that has it.</p>
<h3>What it does</h3>
<p>IPFS addresses files by their <strong>content hash</strong> (CID), not their location. This means:</p>
<ul>
  <li>The same file always has the same address, regardless of who hosts it</li>
  <li>Content can be verified &mdash; if the hash matches, the file is authentic</li>
  <li>Multiple peers can serve the same file, creating redundancy</li>
  <li>Files can be transferred offline via CAR (Content Addressable aRchive) files on USB drives</li>
</ul>
<h3>Role in OSmosis</h3>
<p>IPFS is OSmosis's distribution backbone. It powers:</p>
<ul>
  <li><strong>Firmware distribution</strong> &mdash; ROM and firmware images are pinned to IPFS and fetched from the nearest peer</li>
  <li><strong>Community seeding</strong> &mdash; users who download firmware automatically share it with others (like BitTorrent)</li>
  <li><strong>Offline transfer</strong> &mdash; export pinned content as <code>.car</code> files for USB/sneakernet transfer to air-gapped machines</li>
  <li><strong>Config channels</strong> &mdash; subscribe to IPNS-based channels for device profile and registry updates</li>
  <li><strong>OS Builder caching</strong> &mdash; base system layers are cached on IPFS to speed up repeated builds</li>
  <li><strong>PubSub</strong> &mdash; real-time announcements from peers about new firmware and config updates</li>
</ul>
<h3>Key concepts</h3>
<table class="wiki-table">
  <thead><tr><th>Concept</th><th>What it is</th></tr></thead>
  <tbody>
    <tr><td><strong>CID</strong></td><td>Content Identifier &mdash; a hash that uniquely addresses a file (<code>Qm...</code> or <code>bafy...</code>)</td></tr>
    <tr><td><strong>Pinning</strong></td><td>Telling your IPFS node to keep a file permanently (otherwise it may be garbage-collected)</td></tr>
    <tr><td><strong>IPNS</strong></td><td>InterPlanetary Name System &mdash; mutable pointers to CIDs, used for config channels</td></tr>
    <tr><td><strong>Bitswap</strong></td><td>The protocol peers use to exchange blocks of data</td></tr>
    <tr><td><strong>CAR file</strong></td><td>Content Addressable aRchive &mdash; a portable bundle of IPFS blocks for offline transfer</td></tr>
  </tbody>
</table>
<h3>IPFS Network page</h3>
<p>OSmosis has a dedicated <strong>IPFS Network</strong> page (in the sidebar) where you can monitor node status, view Bitswap seeding stats, manage pinned content, export/import CAR files, manage config channel subscriptions, and see live PubSub messages from peers.</p>`
  },
  {
    id: 'tor-tool',
    title: 'Tor (The Onion Router)',
    summary: 'Anonymous network routing. Used in OSmosis to proxy Xiaomi API calls for privacy and region bypass.',
    category: 'tools',
    related: ['miassistant-tool', 'ipfs-tool', 'android-devices', 'adb'],
    body: `<p><strong>Tor</strong> (The Onion Router) is a free, open-source network that anonymizes internet traffic by routing it through multiple encrypted relays around the world. No single relay knows both the origin and destination of the traffic.</p>
<h3>What it does</h3>
<p>Tor encrypts your traffic and bounces it through at least three volunteer-operated relays (guard &rarr; middle &rarr; exit) before it reaches its destination. This provides:</p>
<ul>
  <li><strong>Anonymity:</strong> The destination server sees the exit relay's IP address, not yours</li>
  <li><strong>Privacy:</strong> Your ISP sees you connecting to the Tor network, but not what you're accessing</li>
  <li><strong>Censorship resistance:</strong> Tor can bypass regional blocks and network restrictions</li>
  <li><strong>Region bypass:</strong> Exit relays can be in different countries, bypassing geographic API restrictions</li>
</ul>
<h3>Role in OSmosis</h3>
<p>OSmosis integrates Tor as an optional <strong>SOCKS5 proxy</strong> for Xiaomi Mi account API calls. This is used when:</p>
<ul>
  <li><strong>Bootloader unlocking:</strong> Xiaomi's unlock API requires authenticating with a Mi account. Tor can route these requests through a different region if the API is blocked or rate-limited in your area.</li>
  <li><strong>MIAssistant ROM validation:</strong> Xiaomi's servers validate ROMs before the device accepts them. Tor provides privacy for these validation requests.</li>
  <li><strong>Privacy:</strong> Prevents Xiaomi from linking your IP address to your device serial number and Mi account during unlock and flash operations.</li>
</ul>
<h3>How OSmosis uses Tor</h3>
<p>In the <strong>Mi Account Manager</strong>, OSmosis can:</p>
<ol>
  <li>Detect if Tor is installed and whether the service is running</li>
  <li>Start the Tor service automatically (<code>systemctl start tor</code>)</li>
  <li>Route Xiaomi API traffic through Tor's SOCKS5 proxy (<code>socks5://127.0.0.1:9050</code>)</li>
  <li>Fall back to a custom proxy if you prefer a different SOCKS5/HTTP proxy</li>
</ol>
<p>When Tor is active, all Mi account API calls (login, 2FA, token exchange, unlock requests) are routed through the Tor network. Device-local operations (USB, ADB, fastboot) are <strong>not</strong> affected.</p>
<h3>Setup</h3>
<table class="wiki-table">
  <thead><tr><th>Distro</th><th>Install command</th></tr></thead>
  <tbody>
    <tr><td>Debian / Ubuntu</td><td><code>sudo apt install tor</code></td></tr>
    <tr><td>Fedora</td><td><code>sudo dnf install tor</code></td></tr>
    <tr><td>Arch</td><td><code>sudo pacman -S tor</code></td></tr>
  </tbody>
</table>
<p>After installing, Tor runs as a systemd service and listens on <strong>port 9050</strong> (SOCKS5). OSmosis detects it automatically.</p>
<h3>When to use Tor</h3>
<ul>
  <li>You want to keep Xiaomi API requests private</li>
  <li>The Xiaomi unlock API is rate-limited or blocked in your region</li>
  <li>You're on a restricted network that blocks Xiaomi's servers</li>
</ul>
<h3>When NOT to use Tor</h3>
<ul>
  <li><strong>Downloading large firmware files:</strong> Tor is slow for bulk transfers. Use IPFS or direct download instead.</li>
  <li><strong>Time-sensitive operations:</strong> Tor adds latency. If the Xiaomi 2FA code expires before the request completes, try without Tor.</li>
</ul>`
  },
  {
    id: 'miassistant-tool',
    title: 'MIAssistant Protocol',
    summary: 'Xiaomi\'s proprietary USB protocol for flashing stock ROMs on locked-bootloader devices via MIUI Recovery.',
    category: 'tools',
    related: ['fastboot-tool', 'adb', 'android-devices', 'edl-tool', 'tor-tool'],
    body: `<p><strong>MIAssistant</strong> is Xiaomi's proprietary USB protocol used by MIUI Recovery 5.0's "Connect with MIAssistant" mode. It allows flashing official stock ROMs on <strong>locked-bootloader</strong> Xiaomi devices without needing to unlock the bootloader first.</p>
<h3>What it does</h3>
<ul>
  <li>Transfers and flashes official Xiaomi ROMs to devices in MIUI Recovery mode</li>
  <li>Works on locked bootloaders &mdash; no unlock required</li>
  <li>Validates the ROM with Xiaomi's servers before the device accepts the transfer</li>
  <li>Can extract the device token for bootloader unlock procedures</li>
</ul>
<h3>How it works</h3>
<p>MIAssistant uses a proprietary USB protocol (not standard ADB sideload). The flow is:</p>
<ol>
  <li>Boot the Xiaomi device into MIUI Recovery</li>
  <li>Select "Connect with MIAssistant" from the recovery menu</li>
  <li>Connect via USB &mdash; the device exposes a special USB interface</li>
  <li>OSmosis sends the ROM package over the proprietary protocol</li>
  <li>The device validates the ROM signature with Xiaomi's servers</li>
  <li>If valid, the device flashes the ROM and reboots</li>
</ol>
<h3>Role in OSmosis</h3>
<p>OSmosis implements the MIAssistant protocol natively for:</p>
<ul>
  <li><strong>Locked-device recovery</strong> &mdash; reflashing stock firmware without bootloader unlock</li>
  <li><strong>Token extraction</strong> &mdash; reading the device token needed for MiUnlockTool</li>
  <li><strong>Bricked device recovery</strong> &mdash; when a Xiaomi device is stuck but can still enter MIUI Recovery</li>
</ul>
<h3>Limitations</h3>
<ul>
  <li><strong>Region matching:</strong> The ROM must match the device's region (EEA, Global, China, etc.) and exact model. A ROM for <code>courbet</code> (Mi 11 Lite 4G) will not work on <code>renoir</code> (Mi 11 Lite 5G) even though the names are similar.</li>
  <li><strong>Server validation:</strong> Requires internet access on the host computer for Xiaomi's server to validate the ROM.</li>
  <li><strong>USB conflicts:</strong> ADB and MIAssistant can conflict on the same USB interface. OSmosis kills ADB before starting a MIAssistant session.</li>
  <li><strong>Cross-flashed devices:</strong> Devices with wrong firmware (different hardware variant) cannot be recovered via MIAssistant &mdash; bootloader unlock or EDL is needed instead.</li>
</ul>`
  }
]

const categories = {
  devices: { label: 'Devices & Hardware', color: '#9b59b6' },
  os: { label: 'Operating Systems & Compatibility', color: '#27ae60' },
  flashing: { label: 'Flashing & Rooting', color: '#e67e22' },
  tools: { label: 'Tools & Protocols', color: '#e74c3c' },
  'os-builder': { label: 'Linux From Scratch & OS Builder', color: '#3498db' }
}

// ── Build wiki articles dynamically from device profiles ──

function escHtml(s) { return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;') }

function profileToArticle(p) {
  const title = p.brand ? `${p.brand} ${p.name}` : p.name
  const parts = []

  // Summary line
  const summaryParts = [p.model && `${p.model}`, p.codename && `(${p.codename})`, p.flash_tool && `${p.flash_tool}`, p.flash_method && `via ${p.flash_method}`].filter(Boolean)
  const summary = summaryParts.join(' ') || title

  // Intro
  parts.push(`<p><strong>${escHtml(title)}</strong>`)
  if (p.model) parts[0] += ` (${escHtml(p.model)}`
  if (p.codename) parts[0] += `, codename <em>${escHtml(p.codename)}</em>`
  if (p.model) parts[0] += ')'
  parts[0] += '.'
  if (p.notes) parts[0] += ` ${escHtml(p.notes)}`
  parts[0] += '</p>'

  // Specs table
  const specs = []
  if (p.extra?.soc) specs.push(['SoC', p.extra.soc])
  if (p.extra?.cpu) specs.push(['CPU', p.extra.cpu])
  if (p.extra?.gpu) specs.push(['GPU', p.extra.gpu])
  if (p.extra?.ram_mb) specs.push(['RAM', `${p.extra.ram_mb} MB`])
  if (p.extra?.ram) specs.push(['RAM', p.extra.ram])
  if (p.extra?.storage_mb) specs.push(['Storage', `${p.extra.storage_mb} MB`])
  if (p.extra?.display) specs.push(['Display', p.extra.display])
  if (p.flash_tool) specs.push(['Flash tool', p.flash_tool])
  if (p.flash_method) specs.push(['Flash method', p.flash_method])
  if (p.requires_unlock) specs.push(['Bootloader unlock', 'Required'])
  if (p.partitions?.length) specs.push(['Partitions', p.partitions.join(', ')])
  if (specs.length) {
    parts.push('<h3>Specs</h3>')
    parts.push('<table class="wiki-table"><thead><tr><th>Spec</th><th>Details</th></tr></thead><tbody>')
    for (const [k, v] of specs) parts.push(`<tr><td>${escHtml(k)}</td><td>${escHtml(String(v))}</td></tr>`)
    parts.push('</tbody></table>')
  }

  // Variants
  if (p.extra?.variants?.length) {
    parts.push('<h3>Variants</h3>')
    parts.push('<table class="wiki-table"><thead><tr><th>Model</th><th>Notes</th></tr></thead><tbody>')
    for (const v of p.extra.variants) {
      parts.push(`<tr><td>${escHtml(v.model || '')}</td><td>${escHtml(v.notes || '\u2014')}</td></tr>`)
    }
    parts.push('</tbody></table>')
  }

  // Available firmware
  if (p.firmware?.length) {
    parts.push('<h3>Available firmware</h3><ul>')
    for (const fw of p.firmware) {
      let line = `<li><strong>${escHtml(fw.name)}</strong>`
      if (fw.version) line += ` (${escHtml(fw.version)})`
      if (fw.tags?.length) line += ` \u2014 ${escHtml(fw.tags.join(', '))}`
      line += '</li>'
      parts.push(line)
    }
    parts.push('</ul>')
  }

  // Flash steps
  if (p.flash_steps?.length) {
    parts.push('<h3>Flash process</h3><ol>')
    for (const step of p.flash_steps) {
      let line = `<li><strong>${escHtml(step.name)}</strong>`
      if (step.description) line += ` \u2014 ${escHtml(step.description)}`
      line += '</li>'
      parts.push(line)
    }
    parts.push('</ol>')
  }

  // Known issues
  if (p.extra?.known_issues?.length) {
    parts.push('<h3>Known issues</h3><ul>')
    for (const issue of p.extra.known_issues) {
      const sev = issue.severity ? `<strong>${escHtml(issue.severity)}</strong> \u2014 ` : ''
      parts.push(`<li>${sev}${escHtml(issue.description || '')}</li>`)
      }
    parts.push('</ul>')
  }

  // pmOS status
  if (p.extra?.pmos_status) {
    const pm = p.extra.pmos_status
    parts.push(`<h3>postmarketOS status (${escHtml(pm.tier || '')})</h3>`)
    if (pm.working?.length) parts.push(`<p><strong>Working:</strong> ${escHtml(pm.working.join(', '))}</p>`)
    if (pm.broken?.length) parts.push(`<p><strong>Broken:</strong> ${escHtml(pm.broken.join(', '))}</p>`)
  }

  // Debloat presets
  if (p.extra?.debloat_presets) {
    parts.push('<h3>Debloat presets</h3><ul>')
    for (const [, preset] of Object.entries(p.extra.debloat_presets)) {
      parts.push(`<li><strong>${escHtml(preset.name || '')}</strong> \u2014 ${escHtml(preset.desc || '')} (${preset.packages?.length || 0} packages)</li>`)
    }
    parts.push('</ul>')
  }

  // Recommended apps
  if (p.extra?.recommended_apps?.length) {
    parts.push('<h3>Recommended apps</h3><ul>')
    for (const app of p.extra.recommended_apps) {
      parts.push(`<li><strong>${escHtml(app.name)}</strong> \u2014 ${escHtml(app.desc || '')}</li>`)
    }
    parts.push('</ul>')
  }

  // Sensors
  if (p.extra?.sensors?.length) {
    parts.push('<h3>Sensors</h3><ul>')
    for (const s of p.extra.sensors) parts.push(`<li>${escHtml(s)}</li>`)
    parts.push('</ul>')
  }

  // Related articles based on flash tool / category
  const related = []
  if (['phone', 'tablet'].includes(p.category)) related.push('android-devices')
  if (p.flash_tool === 'heimdall') related.push('heimdall')
  if (p.flash_tool === 'fastboot') related.push('fastboot')
  if (p.flash_method === 'sd-card') related.push('linux-phones')
  if (p.category === 'sbc') related.push('sbc')

  return {
    id: `device-${p.id}`,
    title,
    summary,
    category: 'devices',
    related,
    body: parts.join('\n'),
    _profileId: p.id,
  }
}

const profileArticles = computed(() => deviceProfiles.value.map(profileToArticle))

const allArticles = computed(() => {
  // Insert profile articles into the devices category, after the static device articles
  const spliceIdx = articles.findIndex(a => a.id === 'lethe' || a.id === 'spore') || articles.length
  return [...articles.slice(0, spliceIdx), ...profileArticles.value, ...articles.slice(spliceIdx)]
})

const filteredArticles = computed(() => {
  const all = allArticles.value
  if (!searchQuery.value.trim()) return all
  const q = searchQuery.value.toLowerCase()
  return all.filter(a =>
    a.title.toLowerCase().includes(q) ||
    a.summary.toLowerCase().includes(q) ||
    a.body.toLowerCase().includes(q)
  )
})

const groupedArticles = computed(() => {
  const groups = {}
  for (const a of filteredArticles.value) {
    if (!groups[a.category]) groups[a.category] = []
    groups[a.category].push(a)
  }
  return groups
})

const articleToc = computed(() => {
  if (!activeArticle.value) return []
  const regex = /<h3>(.*?)<\/h3>/g
  const headings = []
  let match
  while ((match = regex.exec(activeArticle.value.body)) !== null) {
    const text = match[1].replace(/<[^>]*>/g, '')
    headings.push({ id: text.toLowerCase().replace(/[^a-z0-9]+/g, '-'), text })
  }
  return headings
})

const bodyWithAnchors = computed(() => {
  if (!activeArticle.value) return ''
  let idx = 0
  return activeArticle.value.body.replace(/<h3>(.*?)<\/h3>/g, (_, content) => {
    const toc = articleToc.value[idx++]
    return toc ? `<h3 id="${toc.id}">${content}</h3>` : `<h3>${content}</h3>`
  })
})

function openArticle(id) {
  activeArticle.value = allArticles.value.find(a => a.id === id) || null
  focusedCardIndex.value = -1
  // Update URL for deep-linking without full navigation
  router.replace({ path: '/wiki', query: activeArticle.value ? { article: id } : {} })
  nextTick(() => {
    const main = document.querySelector('.app-main')
    if (main) main.scrollTo({ top: 0, behavior: 'smooth' })
  })
}

function back() {
  activeArticle.value = null
  focusedCardIndex.value = -1
  router.replace({ path: '/wiki', query: {} })
}

function scrollToHeading(id) {
  const el = document.getElementById(id)
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function getRelatedArticle(rid) {
  return allArticles.value.find(a => a.id === rid)
}

function categoryColor(cat) {
  return categories[cat]?.color || 'var(--accent)'
}

function handleKeydown(e) {
  if (e.key === 'Escape') {
    if (activeArticle.value) {
      back()
      e.preventDefault()
    }
    return
  }

  if (activeArticle.value) return

  const flat = filteredArticles.value
  if (!flat.length) return

  if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
    e.preventDefault()
    focusedCardIndex.value = Math.min(focusedCardIndex.value + 1, flat.length - 1)
    focusCard()
  } else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
    e.preventDefault()
    focusedCardIndex.value = Math.max(focusedCardIndex.value - 1, 0)
    focusCard()
  } else if (e.key === 'Enter' && focusedCardIndex.value >= 0) {
    e.preventDefault()
    openArticle(flat[focusedCardIndex.value].id)
  }
}

function focusCard() {
  nextTick(() => {
    const cards = document.querySelectorAll('.wiki-card')
    if (cards[focusedCardIndex.value]) {
      cards[focusedCardIndex.value].focus()
    }
  })
}

async function fetchProfiles() {
  try {
    const res = await fetch('/api/profiles')
    if (res.ok) deviceProfiles.value = await res.json()
  } catch { /* offline / backend down */ }
}

function openFromQuery() {
  const id = route.query.article
  if (id) {
    const found = allArticles.value.find(a => a.id === id)
    if (found) activeArticle.value = found
  }
}

onMounted(async () => {
  window.addEventListener('keydown', handleKeydown)
  await fetchProfiles()
  openFromQuery()
})

// Re-check deep-link when query changes (e.g. navigating from connected device page)
watch(() => route.query.article, (id) => {
  if (id) {
    const found = allArticles.value.find(a => a.id === id)
    if (found) activeArticle.value = found
  }
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<template>
  <main class="page-container" role="main">
    <!-- Article detail view -->
    <article v-if="activeArticle" class="wiki-article">
      <nav class="wiki-breadcrumb">
        <button class="wiki-back" @click="back">&larr; All topics</button>
        <span class="wiki-breadcrumb-sep">/</span>
        <span class="wiki-breadcrumb-cat" :style="{ color: categoryColor(activeArticle.category) }">
          {{ categories[activeArticle.category].label }}
        </span>
        <span class="wiki-breadcrumb-sep">/</span>
        <span>{{ activeArticle.title }}</span>
      </nav>

      <h1 class="wiki-article-title">{{ activeArticle.title }}</h1>

      <!-- Table of contents -->
      <nav v-if="articleToc.length > 1" class="wiki-toc">
        <h3 class="wiki-toc-title">On this page</h3>
        <ul class="wiki-toc-list">
          <li v-for="heading in articleToc" :key="heading.id">
            <button class="wiki-toc-link" @click="scrollToHeading(heading.id)">{{ heading.text }}</button>
          </li>
        </ul>
      </nav>

      <div class="wiki-article-body" v-html="bodyWithAnchors"></div>

      <nav v-if="activeArticle.related.length" class="wiki-related">
        <h3 class="wiki-related-title">Related topics</h3>
        <div class="wiki-related-links">
          <button
            v-for="rid in activeArticle.related"
            :key="rid"
            class="wiki-related-chip"
            @click="openArticle(rid)"
          >
            <span class="wiki-related-chip-title">{{ getRelatedArticle(rid)?.title }}</span>
            <span class="wiki-related-chip-summary">{{ getRelatedArticle(rid)?.summary }}</span>
          </button>
        </div>
      </nav>

      <!-- Quick nav: other topics in same category -->
      <nav class="wiki-quicknav">
        <h3 class="wiki-quicknav-title">More in {{ categories[activeArticle.category].label }}</h3>
        <div class="wiki-quicknav-links">
          <button
            v-for="a in allArticles.filter(a => a.category === activeArticle.category && a.id !== activeArticle.id)"
            :key="a.id"
            class="wiki-quicknav-chip"
            @click="openArticle(a.id)"
          >{{ a.title }}</button>
        </div>
      </nav>
    </article>

    <!-- Knowledge base index -->
    <div v-else>
      <h1>{{ t('nav.wiki', 'Wiki') }}</h1>
      <p class="page-lead">Learn about flashing, building, and taking control of your devices.</p>

      <div class="wiki-search-bar">
        <input
          v-model="searchQuery"
          type="search"
          class="wiki-search-input"
          placeholder="Search topics..."
          aria-label="Search wiki topics"
        />
      </div>

      <template v-for="(catArticles, catKey) in groupedArticles" :key="catKey">
        <h2 class="wiki-cat-title" :style="{ color: categoryColor(catKey) }">{{ categories[catKey].label }}</h2>
        <div class="wiki-grid">
          <button
            v-for="article in catArticles"
            :key="article.id"
            class="wiki-card"
            :class="{ focused: focusedCardIndex === filteredArticles.indexOf(article) }"
            :style="{ borderLeftColor: categoryColor(article.category) }"
            @click="openArticle(article.id)"
            :tabindex="0"
          >
            <span class="wiki-card-title">{{ article.title }}</span>
            <span class="wiki-card-summary">{{ article.summary }}</span>
          </button>
        </div>
      </template>

      <p v-if="filteredArticles.length === 0" class="wiki-no-results">
        No topics match your search.
      </p>
    </div>
  </main>
</template>
