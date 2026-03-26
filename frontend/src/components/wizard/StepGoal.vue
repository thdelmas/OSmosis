<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useWizard } from '@/composables/useWizard'

const { t } = useI18n()
const router = useRouter()
const { state, setGoal, deviceLabel } = useWizard()

const goals = [
  // Phone/tablet
  { id: 'install', cats: ['phone'], icon: '\u{1F680}', title: 'Install a new operating system', desc: 'Replace the current software with a new one — like LineageOS, /e/OS, or another custom ROM.', tag: 'Most popular' },
  { id: 'backup', cats: ['phone'], icon: '\u{1F4BE}', title: 'Back up my device', desc: 'Save a copy of important system files before making changes.' },
  { id: 'fix', cats: ['phone'], icon: '\u{1F527}', title: 'Fix a broken device', desc: 'Your device is stuck, boot-looping, or won\'t start properly.' },
  { id: 'restore-stock', cats: ['phone'], icon: '\u{1F4E6}', title: 'Restore stock firmware', desc: 'Flash the original manufacturer firmware back to your device. Useful for returning to stock before selling, warranty repair, or starting fresh.' },
  // Computer
  { id: 'bootable', cats: ['computer'], icon: '\u{1F4BF}', title: 'Create a bootable USB or SD card', desc: 'Write an ISO or IMG to a USB drive or SD card.', tag: 'Most popular' },
  { id: 'os-builder', cats: ['computer'], icon: '\u{1F3D7}', title: 'Build your own OS', desc: 'Assemble a custom OS image from scratch: pick a base, configure packages, export a flashable image.', tag: 'New' },
  { id: 'medicat', cats: ['computer'], icon: '\u{1F3E5}', title: 'Create Medicat USB', desc: 'Build a bootable Medicat USB drive for PC repair, diagnostics, antivirus rescue, and recovery tools. Uses Ventoy as boot manager.' },
  { id: 'pxe', cats: ['computer', 'network'], icon: '\u{1F5A7}', title: 'Set up network boot (PXE)', desc: 'Start a PXE server so other machines can boot from this computer.' },
  // Router/NAS
  { id: 'bootable', cats: ['network'], icon: '\u{1F4BF}', title: 'Flash firmware', desc: 'Write a firmware image to flash storage — for routers, NAS, or embedded systems.' },
  // Car
  { id: 'bootable', cats: ['car'], icon: '\u{1F4BF}', title: 'Create bootable media for dashboard', desc: 'Write OpenAuto, Crankshaft, or Android Auto to an SD card.' },
  { id: 'install', cats: ['car', 'console'], icon: '\u{1F680}', title: 'Flash a new OS via USB', desc: 'Install or replace the OS on a connected device using ADB, fastboot, or Heimdall.' },
  // Marine
  { id: 'bootable', cats: ['marine'], icon: '\u{1F4BF}', title: 'Set up a marine hub', desc: 'Write OpenPlotter, SignalK, or OpenCPN to an SD card.' },
  { id: 'pxe', cats: ['marine'], icon: '\u{1F5A7}', title: 'Network boot for onboard systems', desc: 'Set up PXE to boot instruments from a central server.' },
  // IoT
  { id: 'bootable', cats: ['iot'], icon: '\u{1F4BF}', title: 'Flash firmware to device', desc: 'Write Tasmota, ESPHome, WLED, or other firmware to ESP32, smart plugs, or IP cameras.' },
  // Console
  { id: 'bootable', cats: ['console'], icon: '\u{1F4BF}', title: 'Create bootable media', desc: 'Write custom firmware or OS to SD card for Switch, Steam Deck, or other consoles.' },
  // GPS
  { id: 'bootable', cats: ['gps'], icon: '\u{1F4BF}', title: 'Update firmware or maps', desc: 'Flash firmware updates or custom maps to Garmin, TomTom, or other GPS devices.' },
  // Scooter
  { id: 'scooter-flash', cats: ['scooter'], icon: '\u26A1', title: 'Flash custom firmware (CFW/SHFW)', desc: 'Install ScooterHacking firmware or custom firmware via Bluetooth.', tag: 'Most popular' },
  { id: 'scooter-info', cats: ['scooter'], icon: '\u{1F50D}', title: 'Read scooter info', desc: 'Connect via Bluetooth and read serial number, firmware versions, UID, and model info.' },
  { id: 'scooter-restore', cats: ['scooter'], icon: '\u{1F527}', title: 'Restore stock firmware', desc: 'Roll back to the original Ninebot/Xiaomi firmware.' },
  // E-Bike
  { id: 'ebike-flash', cats: ['ebike'], icon: '\u26A1', title: 'Flash open-source firmware', desc: 'Install bbs-fw, TSDZ2 OSF, Stancecoke, or other open firmware via ST-Link.', tag: 'Most popular' },
  { id: 'ebike-backup', cats: ['ebike'], icon: '\u{1F4BE}', title: 'Backup controller firmware', desc: 'Read and save the current firmware from your motor controller before making changes.' },
  { id: 'ebike-detect', cats: ['ebike'], icon: '\u{1F50D}', title: 'Detect controller', desc: 'Probe the ST-Link connection to identify your controller chip.' },
  // Apple T2
  { id: 't2-backup', cats: ['computer'], icon: '\u{1F4BE}', title: 'Back up T2 chip', desc: 'Save the T2 security chip firmware from an Intel Mac (2018\u20132020). Essential before installing Linux, changing secure boot, or if the Mac has boot problems. Requires a USB-C cable and DFU mode.' },
  { id: 't2-restore', cats: ['computer'], icon: '\u{1F527}', title: 'Restore T2 chip', desc: 'Write a previously saved T2 backup back to the chip to recover a Mac that won\u2019t boot or has a corrupted T2. Requires DFU mode and a USB-C cable from a second computer.' },
  // Microcontroller
  { id: 'mcu-flash', cats: ['microcontroller'], icon: '\u26A1', title: 'Flash firmware', desc: 'Upload firmware to an Arduino, ESP32, Raspberry Pi Pico, STM32, or other microcontroller board.', tag: 'Most popular' },
  { id: 'bootable', cats: ['microcontroller'], icon: '\u{1F4BF}', title: 'Write SD card image', desc: 'Write Raspberry Pi OS, Ubuntu, or another image to an SD card for a Raspberry Pi or other SBC.' },
  { id: 'os-builder', cats: ['microcontroller'], icon: '\u{1F3D7}', title: 'Build a custom OS image', desc: 'Build a custom Linux image for a Raspberry Pi or other ARM SBC.', tag: 'New' },
  // Universal — available for all categories
  { id: 'troubleshoot', cats: ['phone', 'scooter', 'ebike', 'computer', 'network', 'car', 'marine', 'iot', 'console', 'gps', 'microcontroller'], icon: '\u{1F6DF}', title: 'Something went wrong', desc: 'Device bricked, bootloop, flash failed? Get guided recovery help.' },
]

const visibleGoals = computed(() => {
  if (!state.category) return goals
  return goals.filter(g => g.cats.includes(state.category))
})

const goalRoutes = {
  install: 'install',
  backup: 'backup',
  fix: 'fix',
  bootable: 'bootable',
  'os-builder': 'os-builder',
  pxe: 'bootable', // TODO: dedicated PXE step
  'restore-stock': 'install',
  'scooter-flash': 'scooter',
  'scooter-info': 'scooter',
  'scooter-restore': 'scooter',
  'ebike-flash': 'ebike',
  'ebike-backup': 'ebike',
  'ebike-detect': 'ebike',
  't2-backup': 't2',
  't2-restore': 't2',
  medicat: 'medicat',
  'mcu-flash': 'microcontroller',
  troubleshoot: 'troubleshoot',
}

function pick(goal) {
  setGoal(goal)
  const route = goalRoutes[goal] || 'install'
  router.push(`/wizard/${route}`)
}
</script>

<template>
  <h2 class="step-title">{{ t('step.goal.title', 'What would you like to do?') }}</h2>
  <p v-if="deviceLabel.value" class="step-desc">{{ deviceLabel.value }}</p>

  <div class="goal-grid" role="list" aria-label="Available actions">
    <div
      v-for="(goal, i) in visibleGoals"
      :key="`${goal.id}-${i}`"
      class="goal-card"
      role="listitem"
      tabindex="0"
      :aria-label="goal.title + '. ' + goal.desc"
      @click="pick(goal.id)"
      @keydown.enter="pick(goal.id)"
      @keydown.space.prevent="pick(goal.id)"
    >
      <div class="goal-icon" aria-hidden="true">{{ goal.icon }}</div>
      <h3>{{ goal.title }}</h3>
      <p>{{ goal.desc }}</p>
      <div v-if="goal.tag" class="goal-tag">{{ goal.tag }}</div>
    </div>
  </div>

  <div class="step-nav">
    <button class="btn btn-secondary" @click="router.push('/wizard/connect')">&larr; Back</button>
  </div>
</template>
