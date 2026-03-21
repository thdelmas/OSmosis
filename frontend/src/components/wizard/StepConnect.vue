<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { useWizard } from '@/composables/useWizard'

const { t } = useI18n()
const router = useRouter()
const { get } = useApi()
const { setDevice } = useWizard()

const detecting = ref(false)
const detected = ref(null)
const detectError = ref(null)

async function detect() {
  detecting.value = true
  detected.value = null
  detectError.value = null

  const { ok, data } = await get('/api/detect')
  detecting.value = false

  if (ok && data && (data.model || data.serial)) {
    detected.value = data
    setDevice(data)
  } else {
    detectError.value = data?.error || 'No device found. Make sure it is connected and unlocked.'
  }
}

function proceed() {
  router.push('/wizard/goal')
}
</script>

<template>
  <h2 class="step-title">{{ t('step.connect.title', 'Connect your device') }}</h2>
  <p class="step-desc">
    Plug your device into this computer using a USB cable.<br>
    Make sure the device is turned on and the screen is unlocked.
  </p>

  <div class="step-illustration">
    <div class="illustration-box">
      <div class="plug-icon">&#x1F50C;</div>
      <div class="arrow-icon">&rarr;</div>
      <div class="device-icon">&#x1F4F1;</div>
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

  <!-- Detection result -->
  <div v-if="detected" class="detect-box found">
    <strong>{{ detected.friendly_name || detected.model }}</strong>
    <span v-if="detected.serial"> ({{ detected.serial }})</span>
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
    <button class="btn btn-secondary" @click="router.push('/wizard/category')">&larr; Back</button>
  </div>
</template>
