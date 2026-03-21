<script setup>
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
</script>

<template>
  <main class="page-container" role="main">
    <h1>{{ t('nav.credits', 'Credits & Acknowledgments') }}</h1>
    <p class="page-lead">
      OSmosis is built on the shoulders of incredible open-source projects and communities.
      None of this would be possible without their work.
    </p>

    <section class="credits-section">
      <h2>Core Tools</h2>
      <ul class="credits-list">
        <li>
          <a href="https://github.com/Benjamin-Dobell/Heimdall" target="_blank" rel="noopener"><strong>Heimdall</strong></a>
          &mdash; Cross-platform tool for flashing firmware to Samsung devices via Download Mode.
        </li>
        <li>
          <a href="https://developer.android.com/tools" target="_blank" rel="noopener"><strong>Android Platform Tools</strong></a>
          &mdash; ADB and Fastboot, essential for communicating with Android devices over USB.
        </li>
        <li>
          <a href="https://github.com/topjohnwu/Magisk" target="_blank" rel="noopener"><strong>Magisk</strong></a>
          &mdash; The universal systemless root solution for Android.
        </li>
        <li>
          <a href="https://github.com/espressif/esptool" target="_blank" rel="noopener"><strong>esptool</strong></a>
          &mdash; Flashing firmware to ESP32 and ESP8266 microcontrollers.
        </li>
        <li>
          <a href="https://avrdude.github.io/" target="_blank" rel="noopener"><strong>avrdude</strong></a>
          &mdash; Programming AVR microcontrollers (Arduino and compatible boards).
        </li>
        <li>
          <a href="https://arduino.github.io/arduino-cli/" target="_blank" rel="noopener"><strong>arduino-cli</strong></a>
          &mdash; Command-line tool for compiling and uploading Arduino sketches.
        </li>
        <li>
          <a href="https://openocd.org/" target="_blank" rel="noopener"><strong>OpenOCD</strong></a>
          &mdash; On-chip debugging and programming via JTAG/SWD interfaces.
        </li>
        <li>
          <a href="https://github.com/stlink-org/stlink" target="_blank" rel="noopener"><strong>stlink</strong></a>
          &mdash; ST-Link V2 programmer tools for STM32/STM8 flashing and debugging.
        </li>
        <li>
          <a href="https://github.com/raspberrypi/picotool" target="_blank" rel="noopener"><strong>picotool</strong></a>
          &mdash; Inspecting and flashing Raspberry Pi Pico (RP2040) boards.
        </li>
        <li>
          <a href="https://www.pjrc.com/teensy/loader_cli.html" target="_blank" rel="noopener"><strong>teensy_loader_cli</strong></a>
          &mdash; Command-line firmware loader for Teensy microcontrollers.
        </li>
        <li>
          <a href="https://dfu-util.sourceforge.net/" target="_blank" rel="noopener"><strong>dfu-util</strong></a>
          &mdash; USB Device Firmware Upgrade tool for DFU-compatible devices.
        </li>
        <li>
          <a href="https://twrp.me/" target="_blank" rel="noopener"><strong>TWRP</strong></a>
          &mdash; Custom recovery for Android devices, enabling sideloading and backups.
        </li>
        <li>
          <a href="https://github.com/ipfs/kubo" target="_blank" rel="noopener"><strong>Kubo (IPFS)</strong></a>
          &mdash; Go implementation of IPFS, used for decentralized ROM distribution.
        </li>
      </ul>
    </section>

    <section class="credits-section">
      <h2>Custom ROMs & Operating Systems</h2>
      <ul class="credits-list">
        <li>
          <a href="https://lineageos.org/" target="_blank" rel="noopener"><strong>LineageOS</strong></a>
          &mdash; The most popular open-source Android distribution. Clean, fast, and well-maintained.
        </li>
        <li>
          <a href="https://grapheneos.org/" target="_blank" rel="noopener"><strong>GrapheneOS</strong></a>
          &mdash; Security and privacy-focused Android for Google Pixel devices.
        </li>
        <li>
          <a href="https://calyxos.org/" target="_blank" rel="noopener"><strong>CalyxOS</strong></a>
          &mdash; Privacy-focused Android with microG support.
        </li>
        <li>
          <a href="https://e.foundation/" target="_blank" rel="noopener"><strong>/e/OS</strong></a>
          &mdash; De-Googled Android with a built-in privacy ecosystem.
        </li>
        <li>
          <a href="https://postmarketos.org/" target="_blank" rel="noopener"><strong>postmarketOS</strong></a>
          &mdash; Real Linux on your phone. Alpine-based, community-driven.
        </li>
        <li>
          <a href="https://www.replicant.us/" target="_blank" rel="noopener"><strong>Replicant</strong></a>
          &mdash; Fully free software Android distribution.
        </li>
        <li>
          <a href="https://ubports.com/" target="_blank" rel="noopener"><strong>Ubuntu Touch</strong></a>
          &mdash; Ubuntu Linux for phones and tablets.
        </li>
      </ul>
    </section>

    <section class="credits-section">
      <h2>Communities</h2>
      <ul class="credits-list">
        <li>
          <a href="https://scooterhacking.org/" target="_blank" rel="noopener"><strong>ScooterHacking</strong></a>
          &mdash; Custom firmware and tools for Ninebot, Xiaomi, and Segway scooters.
        </li>
        <li>
          <a href="https://librescoot.org/" target="_blank" rel="noopener"><strong>LibreScoot</strong></a>
          &mdash; Open-source firmware for the unu Scooter Pro.
        </li>
        <li>
          <a href="https://endless-sphere.com/" target="_blank" rel="noopener"><strong>Endless Sphere</strong></a>
          &mdash; DIY electric vehicle forum covering e-bikes, scooters, and micromobility hacking.
        </li>
        <li>
          <a href="https://opensourceebikefirmware.bitbucket.io/" target="_blank" rel="noopener"><strong>OpenSource EBike Firmware</strong></a>
          &mdash; Open-source firmware for e-bike motor controllers, primarily the TSDZ2.
        </li>
        <li>
          <a href="https://github.com/openvehicles" target="_blank" rel="noopener"><strong>Open Vehicles</strong></a>
          &mdash; Reverse engineering tools for vehicle systems via CAN bus and OBD-II.
        </li>
        <li>
          <a href="https://xdaforums.com/" target="_blank" rel="noopener"><strong>XDA Developers</strong></a>
          &mdash; The largest community for Android development, ROMs, and device modding.
        </li>
        <li>
          <a href="https://www.ifixit.com/" target="_blank" rel="noopener"><strong>iFixit</strong></a>
          &mdash; Repair guides and right-to-repair advocacy.
        </li>
        <li>
          <a href="https://openwrt.org/" target="_blank" rel="noopener"><strong>OpenWrt</strong></a>
          &mdash; Open-source firmware for routers and network devices.
        </li>
        <li>
          <a href="https://dd-wrt.com/" target="_blank" rel="noopener"><strong>DD-WRT</strong></a>
          &mdash; Linux-based alternative firmware for routers.
        </li>
        <li>
          <a href="https://github.com/arendst/Tasmota" target="_blank" rel="noopener"><strong>Tasmota</strong></a>
          &mdash; Alternative firmware for ESP8266/ESP32 IoT devices with local-only control.
        </li>
        <li>
          <a href="https://esphome.io/" target="_blank" rel="noopener"><strong>ESPHome</strong></a>
          &mdash; YAML-based firmware framework for ESP devices with Home Assistant integration.
        </li>
        <li>
          <a href="https://hackaday.io/" target="_blank" rel="noopener"><strong>Hackaday.io</strong></a>
          &mdash; Hardware hacking and reverse engineering project community.
        </li>
      </ul>
    </section>

    <section class="credits-section">
      <h2>Built With</h2>
      <ul class="credits-list">
        <li><a href="https://vuejs.org/" target="_blank" rel="noopener"><strong>Vue.js</strong></a> &mdash; Progressive JavaScript framework.</li>
        <li><a href="https://flask.palletsprojects.com/" target="_blank" rel="noopener"><strong>Flask</strong></a> &mdash; Python web microframework powering the backend.</li>
        <li><a href="https://vitejs.dev/" target="_blank" rel="noopener"><strong>Vite</strong></a> &mdash; Fast build tool and dev server.</li>
      </ul>
    </section>
  </main>
</template>
