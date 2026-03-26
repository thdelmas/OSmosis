<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
const { t } = useI18n()

const activeArticle = ref(null)
const searchQuery = ref('')
const focusedCardIndex = ref(-1)

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
  // ── Operating Systems & Compatibility ──
  {
    id: 'custom-os',
    title: 'Custom Android ROMs',
    summary: 'LineageOS, GrapheneOS, CalyxOS, /e/OS, and more. What they offer and which devices they support.',
    category: 'os',
    related: ['android-devices', 'rom', 'bootloader'],
    body: `<p>Custom ROMs replace the manufacturer's Android with community-built alternatives. Each has a different focus:</p>
<h3>Privacy-Focused</h3>
<table class="wiki-table">
  <thead><tr><th>ROM</th><th>Devices</th><th>Focus</th></tr></thead>
  <tbody>
    <tr><td><strong>GrapheneOS</strong></td><td>Pixel only</td><td>Hardened security, no Google services by default</td></tr>
    <tr><td><strong>CalyxOS</strong></td><td>Pixel, Fairphone, Motorola</td><td>Privacy with optional microG for app compatibility</td></tr>
    <tr><td><strong>/e/OS</strong></td><td>200+ devices</td><td>De-Googled, privacy-focused with app store (App Lounge)</td></tr>
  </tbody>
</table>
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
  <li><strong>Maximum security?</strong> GrapheneOS on a Pixel</li>
  <li><strong>Privacy without friction?</strong> CalyxOS (microG for app compat) or /e/OS</li>
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
    title: 'ADB',
    summary: 'Android Debug Bridge lets your computer talk to your device over USB.',
    category: 'flashing',
    related: ['sideload', 'rom', 'recovery'],
    body: `<p>ADB (Android Debug Bridge) is a command-line tool that lets your computer communicate with an Android device over USB.</p>
<h3>Common uses</h3>
<ul>
  <li>Install apps and copy files</li>
  <li>Run shell commands on the device</li>
  <li>Sideload ROMs and firmware</li>
  <li>Take screenshots and record the screen</li>
</ul>
<h3>Setup</h3>
<p>Enable <strong>USB Debugging</strong> in your device's Developer Options, then connect via USB. OSmosis handles ADB communication for you during flashing workflows.</p>`
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
  }
]

const categories = {
  devices: { label: 'Devices & Hardware', color: '#9b59b6' },
  os: { label: 'Operating Systems & Compatibility', color: '#27ae60' },
  flashing: { label: 'Flashing & Rooting', color: '#e67e22' },
  'os-builder': { label: 'Linux From Scratch & OS Builder', color: '#3498db' }
}

const filteredArticles = computed(() => {
  if (!searchQuery.value.trim()) return articles
  const q = searchQuery.value.toLowerCase()
  return articles.filter(a =>
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
  activeArticle.value = articles.find(a => a.id === id) || null
  focusedCardIndex.value = -1
  nextTick(() => {
    const main = document.querySelector('.app-main')
    if (main) main.scrollTo({ top: 0, behavior: 'smooth' })
  })
}

function back() {
  activeArticle.value = null
  focusedCardIndex.value = -1
}

function scrollToHeading(id) {
  const el = document.getElementById(id)
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function getRelatedArticle(rid) {
  return articles.find(a => a.id === rid)
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

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
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
            v-for="a in articles.filter(a => a.category === activeArticle.category && a.id !== activeArticle.id)"
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
