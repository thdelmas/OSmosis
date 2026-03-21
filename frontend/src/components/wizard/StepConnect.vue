<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { useWizard } from '@/composables/useWizard'

const { t } = useI18n()
const router = useRouter()
const { get } = useApi()
const { state, setDevice } = useWizard()

const detecting = ref(false)
const detected = ref(null)
const detectError = ref(null)
const mcuDevices = ref([])

const isMcu = computed(() => state.category === 'microcontroller')

async function detect() {
  detecting.value = true
  detected.value = null
  detectError.value = null
  mcuDevices.value = []

  if (isMcu.value) {
    // Use microcontroller detection (serial ports + UF2)
    const { ok, data } = await get('/api/microcontrollers/detect')
    detecting.value = false

    if (ok && data.devices && data.devices.length) {
      mcuDevices.value = data.devices
      // Set the first detected device
      const first = data.devices[0]
      setDevice({
        port: first.port || '',
        uf2_mount: first.mount || '',
        brand: first.brand || first.model || '',
        label: first.match?.label || first.product || first.brand || 'Microcontroller',
        match: first.match,
      })
    } else {
      detectError.value = 'No microcontroller detected. Make sure the board is connected via USB.'
    }
  } else {
    // Default ADB detection for phones/tablets
    const { ok, data } = await get('/api/detect')
    detecting.value = false

    if (ok && data && (data.model || data.serial)) {
      detected.value = data
      setDevice(data)
    } else {
      detectError.value = data?.error || 'No device found. Make sure it is connected and unlocked.'
    }
  }
}

function proceed() {
  router.push('/wizard/goal')
}
</script>

<template>
  <h2 class="step-title">{{ t('step.connect.title', 'Connect your device') }}</h2>
  <p class="step-desc" v-if="!isMcu">
    Plug your device into this computer using a USB cable.<br>
    Make sure the device is turned on and the screen is unlocked.
  </p>
  <p class="step-desc" v-else>
    Plug your microcontroller board into this computer via USB.<br>
    For UF2 boards (Raspberry Pi Pico, Adafruit), hold BOOTSEL while connecting.
  </p>

  <div class="step-illustration">
    <div class="illustration-box">
      <div class="plug-icon">&#x1F50C;</div>
      <div class="arrow-icon">&rarr;</div>
      <div class="device-icon" v-if="!isMcu">&#x1F4F1;</div>
      <div class="device-icon" v-else>&#x2699;&#xFE0F;</div>
    </div>
  </div>

  <div class="step-actions">
    <button
      class="btn btn-large btn-primary"
      :class="{ 'btn-loading': detecting }"
      :disabled="detecting"
      @click="detect"
    >
      <span class="btn-icon">&#x1F50D;</span>
      <span>{{ t('step.connect.btn', 'Find my device') }}</span>
    </button>
  </div>

  <!-- ADB detection result -->
  <div v-if="detected" class="detect-box found">
    <strong>{{ detected.friendly_name || detected.model }}</strong>
    <span v-if="detected.serial"> ({{ detected.serial }})</span>
    <div style="margin-top: 0.5rem">
      <button class="btn btn-primary" @click="proceed">Continue &rarr;</button>
    </div>
  </div>

  <!-- Microcontroller detection results -->
  <div v-if="mcuDevices.length" class="mcu-detect-results">
    <div v-for="dev in mcuDevices" :key="dev.port || dev.mount" class="detect-box found">
      <div v-if="dev.type === 'serial'">
        <strong>{{ dev.match?.label || dev.product || dev.brand }}</strong>
        <span class="text-dim"> &mdash; {{ dev.port }}</span>
        <span v-if="dev.vid" class="text-dim"> (VID:{{ dev.vid }} PID:{{ dev.pid }})</span>
      </div>
      <div v-else-if="dev.type === 'uf2'">
        <strong>UF2 Bootloader</strong>
        <span class="text-dim"> &mdash; {{ dev.model || dev.mount }}</span>
      </div>
    </div>
    <div style="margin-top: 0.5rem">
      <button class="btn btn-primary" @click="proceed">Continue &rarr;</button>
    </div>
  </div>

  <div v-if="detectError" class="detect-box not-found">
    {{ detectError }}
  </div>

  <div class="step-skip">
    <span class="text-dim">Don't have a device right now?</span>
    <button class="btn btn-link" @click="proceed">Skip to next step</button>
  </div>

  <div class="step-nav">
    <button class="btn btn-secondary" @click="router.push('/wizard/identify')">&larr; Back</button>
  </div>
</template>
