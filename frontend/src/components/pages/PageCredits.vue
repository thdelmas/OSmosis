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
