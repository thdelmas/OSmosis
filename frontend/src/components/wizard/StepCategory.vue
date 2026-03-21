<script setup>
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useWizard } from '@/composables/useWizard'

const { t } = useI18n()
const router = useRouter()
const { setCategory } = useWizard()

const categories = [
  { id: 'phone', icon: '\u{1F4F1}', title: 'Phone or tablet', desc: 'Samsung, Google Pixel, Xiaomi, Fairphone, PinePhone, and other mobile devices.' },
  { id: 'computer', icon: '\u{1F4BB}', title: 'Computer or SBC', desc: 'Bootable USB/SD for PCs, Raspberry Pi, Jetson, and single-board computers.' },
  { id: 'network', icon: '\u{1F5A7}', title: 'Router or NAS', desc: 'Flash OpenWrt on routers, PXE boot servers, or network storage devices.' },
  { id: 'car', icon: '\u{1F697}', title: 'Car or vehicle', desc: 'Android Auto head units, Raspberry Pi dashboards, and OBD2 devices.' },
  { id: 'marine', icon: '\u26F5', title: 'Boat or marine', desc: 'Chart plotters, NMEA 2000 gateways, SignalK hubs, and marine electronics.' },
  { id: 'iot', icon: '\u{1F4E1}', title: 'IoT or wearable', desc: 'ESP32, smart home devices, IP cameras, PineTime, and other embedded hardware.' },
  { id: 'console', icon: '\u{1F3AE}', title: 'Game console or media', desc: 'Nintendo Switch, Steam Deck, Chromecast, Fire TV, Kindle, and similar devices.' },
  { id: 'gps', icon: '\u{1F4CD}', title: 'GPS or navigation', desc: 'Garmin, TomTom, drone controllers, and standalone navigation devices.' },
  { id: 'scooter', icon: '\u{1F6F4}', title: 'Electric scooter', desc: 'Ninebot, Xiaomi, Segway, and other e-scooters. Flash custom firmware over Bluetooth or ST-Link.' },
  { id: 'ebike', icon: '\u{1F6B2}', title: 'Electric bike', desc: 'Bafang, TSDZ2, Kunteng, and VESC motor controllers. Flash open-source firmware via ST-Link.', tag: 'New' },
  { id: 'microcontroller', icon: '\u{1F9F0}', title: 'Microcontroller or SBC', desc: 'Arduino, Raspberry Pi, ESP32, STM32, Teensy, and other dev boards. Flash firmware via USB, ST-Link, or UF2.', tag: 'New' },
  { id: 'build-os', icon: '\u{1F3D7}', title: 'Build your own OS', desc: 'Assemble a custom Linux image from Debian, Ubuntu, Arch, Alpine, Fedora, or NixOS. Configure everything, export a flashable image.', tag: 'New' },
]

function pick(cat) {
  // OS builder doesn't need device connection — go straight there
  if (cat === 'build-os') {
    setCategory(cat)
    router.push('/wizard/os-builder')
    return
  }
  setCategory(cat)
  router.push('/wizard/connect')
}
</script>

<template>
  <h2 class="step-title">{{ t('step.category.title', 'What kind of device?') }}</h2>
  <p class="step-desc">{{ t('step.category.desc', 'Different devices need different tools. Pick the category that matches your device.') }}</p>

  <div class="goal-grid category-grid" role="list" aria-label="Device categories">
    <div
      v-for="cat in categories"
      :key="cat.id"
      class="goal-card"
      role="listitem"
      tabindex="0"
      :aria-label="cat.title + '. ' + cat.desc"
      @click="pick(cat.id)"
      @keydown.enter="pick(cat.id)"
      @keydown.space.prevent="pick(cat.id)"
    >
      <div class="goal-icon" aria-hidden="true">{{ cat.icon }}</div>
      <h3>{{ cat.title }}</h3>
      <p>{{ cat.desc }}</p>
      <div v-if="cat.tag" class="goal-tag" aria-label="Tag: new">{{ cat.tag }}</div>
    </div>
  </div>

  <div class="step-skip">
    <router-link to="/wizard/identify" class="btn btn-link">&larr; Back to hardware identification</router-link>
  </div>
</template>
