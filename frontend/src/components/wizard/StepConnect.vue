<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { useWizard } from '@/composables/useWizard'
import GlossaryTip from '@/components/shared/GlossaryTip.vue'

const { t } = useI18n()
const router = useRouter()
const { get, post } = useApi()
const { state, setDevice, setSubPhase } = useWizard()

const detecting = ref(false)
const detected = ref(null)
const detectError = ref(null)
const downloadMode = ref(null)
const mcuDevices = ref([])
const rebooting = ref(false)
const skipAcknowledged = ref(false)

const isMcu = computed(() => state.category === 'microcontroller')

async function detect() {
  detecting.value = true
  detected.value = null
  detectError.value = null
  downloadMode.value = null
  mcuDevices.value = []
  setSubPhase('Scanning...')

  if (isMcu.value) {
    // Use microcontroller detection (serial ports + UF2)
    const { ok, data } = await get('/api/microcontrollers/detect')
    detecting.value = false
    setSubPhase(null)

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
      detectError.value = 'No microcontroller detected. Try these steps:\n1. Unplug and re-plug the USB cable\n2. Try a different USB port\n3. For boards with a BOOTSEL button, hold it while plugging in'
    }
  } else {
    // Default ADB detection for phones/tablets
    const { ok, data } = await get('/api/detect')
    detecting.value = false
    setSubPhase(null)

    if (ok && data && (data.model || data.serial)) {
      detected.value = data
      setDevice(data)
    } else if (data?.error === 'download_mode') {
      downloadMode.value = data
      detectError.value = null
    } else if (data?.error === 'usb_no_adb') {
      const names = (data.usb_devices || []).map(d => d.name).join(', ')
      detectError.value = `Device detected via USB (${names || 'unknown'}) but it is not ready for communication. You need to enable USB debugging on your device: open Settings, tap About Phone, tap Build Number 7 times, then go back to Settings > Developer Options and turn on USB Debugging.`
    } else {
      detectError.value = data?.error === 'no_device'
        ? 'No device found. Try these steps:\n1. Make sure the USB cable is plugged in firmly on both ends\n2. Unlock the screen on your device\n3. If you see a "Trust this computer?" popup on your device, tap Allow\n4. Try a different USB cable — some cables only charge and cannot transfer data'
        : (data?.error || 'No device found. Check that the USB cable is connected and the device screen is unlocked.')
    }
  }
}

const rebootWaitMsg = ref('')

async function rebootFromDownload() {
  rebooting.value = true
  rebootWaitMsg.value = 'Sending reboot command...'
  await post('/api/reboot-from-download')

  // Poll for the device to come back instead of a blind timeout
  rebootWaitMsg.value = 'Waiting for your device to restart (this can take up to 30 seconds)...'
  let attempts = 0
  const maxAttempts = 15
  const poll = setInterval(async () => {
    attempts++
    const { ok, data } = await get('/api/detect')
    if (ok && data && !data.error) {
      clearInterval(poll)
      rebooting.value = false
      rebootWaitMsg.value = ''
      downloadMode.value = null
      detected.value = data
      setDevice(data)
    } else if (attempts >= maxAttempts) {
      clearInterval(poll)
      rebooting.value = false
      rebootWaitMsg.value = ''
      downloadMode.value = null
      detectError.value = 'Device did not respond after reboot. It may still be starting up — wait a moment and tap "Find my device" to try again.'
    }
  }, 2000)
}

function proceed() {
  router.push('/wizard/load')
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
    For <GlossaryTip term="UF2" /> boards (Raspberry Pi Pico, Adafruit), hold <GlossaryTip term="BOOTSEL" /> while connecting.
  </p>

  <div class="step-illustration" aria-hidden="true">
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
      :aria-label="detecting ? 'Detecting device...' : 'Find my device'"
    >
      <span class="btn-icon" aria-hidden="true">&#x1F50D;</span>
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

  <!-- Download Mode detected -->
  <div v-if="downloadMode" class="detect-box found">
    <div>
      <strong>{{ downloadMode.usb_name || 'Device' }}</strong>
      <span class="badge badge-warn" style="margin-left: 0.5rem;"><GlossaryTip term="Download Mode" /></span>
    </div>
    <p class="download-mode-explain">Your device is in <strong>Download Mode</strong> — a special state used for flashing firmware. It's not broken, but OSmosis can't identify the exact model while in this mode.</p>
    <p v-if="downloadMode.hint" style="margin: 0.25rem 0 0; font-size: calc(0.9rem * var(--font-scale, 1)); color: var(--text-dim);">{{ downloadMode.hint }}</p>
    <div style="margin-top: 0.75rem; display: flex; gap: 0.5rem; flex-wrap: wrap;">
      <button class="btn btn-primary" :disabled="rebooting" @click="rebootFromDownload">
        {{ rebooting ? 'Rebooting...' : 'Reboot to normal mode' }}
      </button>
      <button class="btn btn-secondary" @click="proceed">
        Continue in <GlossaryTip term="Download Mode" /> &rarr;
      </button>
    </div>
    <div v-if="rebootWaitMsg" class="info-box" style="margin-top: 0.5rem;">
      <span class="spinner-small" aria-hidden="true"></span> {{ rebootWaitMsg }}
    </div>
    <details class="download-mode-manual" style="margin-top: 0.75rem;">
      <summary>If automatic reboot doesn't work</summary>
      <ol class="download-mode-steps">
        <li><strong>Unplug the USB cable</strong></li>
        <li>Hold <strong>Power for 10+ seconds</strong> until the screen goes black</li>
        <li>If the device has a removable battery: remove it, wait 10 seconds, reinsert</li>
        <li>Press Power to boot normally <strong>without USB plugged in</strong></li>
        <li>Once you see the home screen, plug USB back in and tap "Find my device"</li>
      </ol>
    </details>
  </div>

  <div v-if="detectError" class="detect-box not-found" style="white-space: pre-line;">
    {{ detectError }}
  </div>

  <div class="step-skip">
    <span class="text-dim">Don't have a device right now?</span>
    <button v-if="!skipAcknowledged" class="btn btn-link" @click="skipAcknowledged = true">Skip to next step</button>
    <div v-if="skipAcknowledged" class="skip-warning">
      <p class="skip-warning-text">Flashing will fail without a connected device. Only skip if you want to explore the interface.</p>
      <div class="skip-warning-actions">
        <button class="btn btn-secondary btn-small" @click="proceed">I understand, continue anyway</button>
        <button class="btn btn-link btn-small" @click="skipAcknowledged = false">Cancel</button>
      </div>
    </div>
  </div>

  <div class="step-nav">
    <button class="btn btn-secondary" @click="router.push('/wizard/software')">&larr; Back</button>
  </div>
</template>

<style scoped>
.skip-warning {
  margin-top: 0.5rem;
  padding: 0.75rem 1rem;
  border-radius: var(--radius-card, 12px);
  border: 1px solid var(--yellow, #fbbf24);
  background: rgba(251, 191, 36, 0.08);
  font-size: calc(0.9rem * var(--font-scale, 1));
}

.skip-warning-text {
  margin: 0 0 0.5rem;
  color: var(--text, #eee);
  line-height: 1.4;
}

.skip-warning-actions {
  display: flex;
  gap: 0.75rem;
  align-items: center;
}

.download-mode-explain {
  margin: 0.5rem 0 0;
  font-size: calc(0.9rem * var(--font-scale, 1));
  line-height: 1.5;
  color: var(--text, #eee);
}

.download-mode-manual {
  font-size: calc(0.85rem * var(--font-scale, 1));
  color: var(--text-dim);
}

.download-mode-manual summary {
  cursor: pointer;
  font-weight: 500;
}

.download-mode-steps {
  margin: 0.5rem 0;
  padding-left: 1.5rem;
  line-height: 1.8;
}
</style>
