<script setup>
import { ref, computed, watch, onUnmounted } from 'vue'
import DeviceFrame from '@/components/shared/DeviceFrame.vue'
import ScreenOff from '@/components/shared/device-screens/ScreenOff.vue'
import ScreenFastboot from '@/components/shared/device-screens/ScreenFastboot.vue'
import ScreenEdl from '@/components/shared/device-screens/ScreenEdl.vue'

const props = defineProps({
  active: { type: Boolean, default: false },
  deviceMode: { type: String, default: '' },
})

const emit = defineEmits(['edl-ready', 'cancel'])

// Steps: preflight | trying | cable | success | timeout | error
const step = ref('preflight')
const messages = ref([])
const errorMsg = ref('')
const scanRemaining = ref(0)
let eventSource = null
let pollTimer = null

watch(() => props.active, (val) => {
  if (val) reset()
  else cleanup()
}, { immediate: true })

function reset() {
  messages.value = []
  errorMsg.value = ''
  scanRemaining.value = 0
  cleanup()
  // Start immediately — backend accepts any mode (ADB or fastboot)
  startEdlEntry()
}

function cleanup() {
  if (eventSource) { eventSource.close(); eventSource = null }
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

onUnmounted(cleanup)

async function startEdlEntry() {
  step.value = 'trying'
  messages.value = []
  errorMsg.value = ''

  try {
    const res = await fetch('/api/edl/enter', { method: 'POST' })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      errorMsg.value = data.error || `Request failed (${res.status})`
      step.value = 'error'
      return
    }

    const data = await res.json()
    const taskId = data.task_id
    if (!taskId) {
      errorMsg.value = 'No task ID returned from server.'
      step.value = 'error'
      return
    }

    eventSource = new EventSource(`/api/stream/${taskId}`)
    eventSource.onmessage = (e) => {
      if (!e.data || e.data === '{}') return
      try {
        const msg = JSON.parse(e.data)
        if (msg.level === 'done') {
          eventSource.close()
          eventSource = null
          if (msg.msg === 'done') {
            step.value = 'success'
            startEdlPolling()
          } else {
            step.value = 'timeout'
          }
          return
        }
        if (msg.msg !== undefined) {
          if (msg.msg === 'NEED_CABLE') {
            step.value = 'cable'
          } else if (msg.msg === 'EDL_DETECTED') {
            step.value = 'success'
          } else if (msg.msg === 'DIRECT_ACCEPTED') {
            // Direct command worked, waiting for device — stay on trying
          } else if (msg.msg.startsWith('SCANNING:')) {
            const secs = parseInt(msg.msg.split(':')[1])
            if (!isNaN(secs)) scanRemaining.value = secs
          } else if (msg.msg === 'SCAN_TIMEOUT') {
            step.value = 'timeout'
          } else if (msg.msg.trim() === '') {
            // skip blank
          } else if (step.value === 'trying') {
            messages.value.push(msg)
          }
        }
      } catch { /* ignore */ }
    }
    eventSource.onerror = () => {
      eventSource.close()
      eventSource = null
      if (['trying', 'cable'].includes(step.value)) {
        errorMsg.value = 'Lost connection to server.'
        step.value = 'error'
      }
    }
  } catch (err) {
    errorMsg.value = err.message || 'Network error'
    step.value = 'error'
  }
}

function startEdlPolling() {
  pollTimer = setInterval(async () => {
    try {
      const res = await fetch('/api/edl/status')
      if (res.ok) {
        const data = await res.json()
        if (data.edl_detected) {
          clearInterval(pollTimer)
          pollTimer = null
          emit('edl-ready')
        }
      }
    } catch { /* ignore */ }
  }, 1000)

  setTimeout(() => {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
      emit('edl-ready')
    }
  }, 10000)
}

function retry() {
  startEdlEntry()
}

function cancel() { cleanup(); step.value = 'trying'; emit('cancel') }

const needsDevice = computed(() =>
  step.value === 'error' && errorMsg.value.toLowerCase().includes('no device')
)
</script>

<template>
  <div v-if="active" class="edl-flow">

    <!-- Trying EDL commands (ADB + fastboot) -->
    <div v-if="step === 'trying'" class="edl-card">
      <div class="edl-visual-row">
        <DeviceFrame>
          <ScreenFastboot codename="device" />
        </DeviceFrame>
        <div class="edl-visual-text">
          <h3 class="edl-title">Entering EDL mode...</h3>
          <div class="edl-trying-display">
            <span class="spinner-small"></span>
            <span>Trying ADB and fastboot EDL commands</span>
          </div>
          <div v-if="messages.length" class="edl-try-log">
            <div
              v-for="(msg, i) in messages"
              :key="i"
              class="edl-msg"
              :class="'edl-msg-' + (msg.level || 'info')"
            >{{ msg.msg }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Cable: direct commands failed, guide user through cold-plug -->
    <div v-if="step === 'cable'" class="edl-card edl-card-cable">
      <div class="edl-scanning-bar">
        <span class="spinner-small"></span>
        <span>Scanning for EDL device</span>
        <span v-if="scanRemaining > 0" class="scan-remaining">{{ scanRemaining }}s</span>
      </div>

      <h3 class="edl-title">Enter EDL with deep flash cable</h3>

      <div class="edl-cable-steps">
        <div class="cable-step">
          <span class="cable-step-num">1</span>
          <div class="cable-step-body">
            <div class="cable-step-text">
              <strong>Unplug USB and power off the device</strong>
              <p>Hold the power button for 15 seconds until the screen goes black, then wait 5 more seconds.</p>
            </div>
            <DeviceFrame :highlight-buttons="['power']" button-label="Hold 15s" pulse class="cable-step-device">
              <ScreenOff />
            </DeviceFrame>
          </div>
        </div>
        <div class="cable-step">
          <span class="cable-step-num">2</span>
          <div class="cable-step-body">
            <div class="cable-step-text">
              <strong>Hold the cable button, then plug in</strong>
              <p>Press and hold the D+/D- short button on the cable. While holding, plug USB into the powered-off device.</p>
            </div>
            <DeviceFrame class="cable-step-device">
              <ScreenOff />
            </DeviceFrame>
          </div>
        </div>
        <div class="cable-step">
          <span class="cable-step-num">3</span>
          <div class="cable-step-body">
            <div class="cable-step-text">
              <strong>Keep holding for 10 seconds</strong>
              <p>The device will be detected automatically. You can release once this page updates.</p>
            </div>
            <DeviceFrame class="cable-step-device">
              <ScreenEdl />
            </DeviceFrame>
          </div>
        </div>
      </div>

      <details class="edl-cable-help">
        <summary>What is a deep flash cable?</summary>
        <p>A modified USB cable with a button or switch that shorts the D+ and D- data pins.
        When the Qualcomm SoC powers on with D+/D- shorted, it enters Emergency Download (EDL) mode
        instead of booting normally. This bypasses a locked bootloader.</p>
      </details>
    </div>

    <!-- Success -->
    <div v-if="step === 'success'" class="edl-card edl-card-success">
      <div class="edl-visual-row">
        <DeviceFrame>
          <ScreenEdl />
        </DeviceFrame>
        <div class="edl-visual-text">
          <div class="edl-success-icon">&#x2714;</div>
          <h3 class="edl-title">EDL mode detected</h3>
          <p>Device is in Qualcomm 9008 (EDL) mode and ready for flashing.</p>
          <p class="edl-explain">You can release the cable button now.</p>
        </div>
      </div>
    </div>

    <!-- Timeout -->
    <div v-if="step === 'timeout'" class="edl-card edl-card-timeout">
      <h3 class="edl-title">EDL device not detected</h3>

      <div class="edl-timeout-sections">
        <div class="timeout-section">
          <strong>If you have a deep flash cable:</strong>
          <ul class="timeout-checks">
            <li>Verify the cable shorts D+/D- — use a multimeter (near-zero resistance between the green and white wires when the button is pressed).</li>
            <li>The device must be fully off (hold power 15s), not sleeping or in fastboot.</li>
            <li>Hold the cable button <em>before</em> plugging in, not after.</li>
          </ul>
          <div class="edl-actions" style="margin-top: 0.75rem">
            <button class="btn btn-secondary" @click="retry">Try cable method again</button>
          </div>
        </div>

        <div class="timeout-section">
          <strong>If the cable method keeps failing:</strong>
          <p class="timeout-explain">
            Some newer Qualcomm SoCs (including the Snapdragon 780G in this device) may have
            D+/D- EDL detection disabled in the primary bootloader. In that case, the deep flash
            cable will not work regardless of timing.
          </p>
          <p class="timeout-explain"><strong>Alternatives:</strong></p>
          <ul class="timeout-checks">
            <li><strong>EDL test point</strong> — open the phone and short specific pads on the motherboard. Search for "renoir EDL test point" for the exact location.</li>
            <li><strong>Bootloader unlock</strong> — if OEM unlocking is enabled in Developer Options, you can unlock via Mi account from fastboot instead of using EDL.</li>
            <li><strong>Xiaomi authorized service</strong> — service centers have authorized EDL tools that bypass the PBL restriction.</li>
          </ul>
        </div>
      </div>

      <div class="edl-actions">
        <button class="btn btn-link" @click="cancel">Back to actions</button>
      </div>
    </div>

    <!-- Error -->
    <div v-if="step === 'error'" class="edl-card edl-card-error">
      <template v-if="needsDevice">
        <h3 class="edl-title">No device connected</h3>
        <p>Make sure the device is connected via USB and visible in ADB or fastboot.</p>
      </template>
      <template v-else>
        <h3 class="edl-title">Something went wrong</h3>
        <p class="edl-error-msg">{{ errorMsg || 'An unexpected error occurred.' }}</p>
      </template>
      <div class="edl-actions">
        <button class="btn btn-primary" @click="retry">Try again</button>
        <button class="btn btn-link" @click="cancel">Cancel</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.edl-flow {
  margin: 1rem 0;
}

/* Card */
.edl-card {
  background: var(--bg-card, #1e1e2e);
  border: 1px solid var(--border, #333);
  border-radius: 12px;
  padding: 1.5rem;
  max-width: 640px;
}

.edl-title {
  margin: 0 0 0.75rem 0;
  font-size: calc(1.15rem * var(--font-scale, 1));
}

.edl-explain {
  line-height: 1.6;
  margin: 0 0 0.5rem;
  color: var(--text-dim, #aaa);
  font-size: calc(0.9rem * var(--font-scale, 1));
}

.edl-actions {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  margin-top: 1.25rem;
}

/* Trying state */
.edl-trying-display {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}
.edl-try-log {
  font-family: monospace;
  font-size: 0.8rem;
  padding: 0.5rem;
  background: var(--bg-terminal, #111);
  border-radius: 6px;
  max-height: 150px;
  overflow-y: auto;
}
.edl-msg {
  padding: 0.15rem 0;
  white-space: pre-wrap;
}
.edl-msg-warn { color: var(--color-warn, #ff9800); }
.edl-msg-error { color: var(--color-error, #f44336); }
.edl-msg-success { color: var(--color-success, #4caf50); }
.edl-msg-cmd { color: var(--text-dim, #888); }

/* Visual row layout — device frame + text side by side */
.edl-visual-row {
  display: flex;
  gap: 1.25rem;
  align-items: flex-start;
}
.edl-visual-text {
  flex: 1;
  min-width: 0;
}

@media (max-width: 520px) {
  .edl-visual-row {
    flex-direction: column;
    align-items: center;
  }
}

/* Cable steps */
.edl-card-cable {
  border-color: var(--color-warn, #ff9800);
  max-width: 720px;
}
.edl-cable-steps {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin: 1rem 0;
}
.cable-step {
  display: flex;
  gap: 0.85rem;
  align-items: flex-start;
  padding: 0.75rem;
  border-radius: 8px;
  background: color-mix(in srgb, var(--border, #333) 30%, transparent);
}
.cable-step-num {
  flex-shrink: 0;
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 50%;
  background: var(--accent, #7c5cfc);
  color: #fff;
  font-size: 0.75rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 0.1rem;
}
.cable-step-body {
  display: flex;
  gap: 1rem;
  align-items: center;
  flex: 1;
  min-width: 0;
}
.cable-step-text {
  flex: 1;
  min-width: 0;
}
.cable-step-device {
  width: 90px;
  flex-shrink: 0;
}
.cable-step strong {
  display: block;
  margin-bottom: 0.15rem;
}
.cable-step p {
  margin: 0;
  font-size: calc(0.85rem * var(--font-scale, 1));
  color: var(--text-dim, #aaa);
  line-height: 1.5;
}

@media (max-width: 520px) {
  .cable-step-body {
    flex-direction: column;
  }
  .cable-step-device {
    width: 70px;
  }
}

/* Cable help */
.edl-cable-help {
  margin-top: 1rem;
  font-size: calc(0.85rem * var(--font-scale, 1));
  color: var(--text-dim, #aaa);
}
.edl-cable-help summary {
  cursor: pointer;
  color: var(--text, #eee);
  font-weight: 500;
}
.edl-cable-help p {
  margin: 0.5rem 0 0;
  line-height: 1.6;
}

/* Scanning bar */
.edl-scanning-bar {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  margin-bottom: 1.25rem;
  border-radius: 8px;
  background: color-mix(in srgb, var(--accent, #7c5cfc) 8%, var(--bg-card, #1e1e2e));
  border: 1px solid color-mix(in srgb, var(--accent, #7c5cfc) 25%, var(--border, #333));
  font-size: calc(0.9rem * var(--font-scale, 1));
}
.scan-remaining {
  margin-left: auto;
  font-family: monospace;
  color: var(--text-dim, #aaa);
}

/* Success */
.edl-card-success {
  border-color: var(--color-success, #4caf50);
}
.edl-card-success .edl-visual-text {
  text-align: left;
}
.edl-success-icon {
  font-size: 3rem;
  color: var(--color-success, #4caf50);
  margin-bottom: 0.5rem;
}

/* Timeout */
.edl-card-timeout {
  border-color: var(--color-warn, #ff9800);
}
.edl-timeout-sections {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  margin-top: 0.75rem;
}
.timeout-section {
  padding: 1rem;
  border-radius: 8px;
  background: color-mix(in srgb, var(--border, #333) 25%, transparent);
  font-size: calc(0.9rem * var(--font-scale, 1));
  line-height: 1.6;
}
.timeout-checks {
  margin: 0.4rem 0 0 1.25rem;
  padding: 0;
}
.timeout-checks li {
  margin: 0.35rem 0;
}
.timeout-explain {
  margin: 0.4rem 0;
  color: var(--text-dim, #aaa);
}

/* Checklist */
.edl-checklist {
  margin: 0.5rem 0 0;
  padding: 0 0 0 1.5rem;
  list-style: none;
  counter-reset: checklist;
}
.edl-checklist li {
  counter-increment: checklist;
  position: relative;
  margin-bottom: 0.85rem;
  line-height: 1.6;
}
.edl-checklist li::before {
  content: counter(checklist);
  position: absolute;
  left: -1.5rem;
  width: 1.2rem;
  height: 1.2rem;
  border-radius: 50%;
  background: var(--accent, #7c5cfc);
  color: #fff;
  font-size: 0.7rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  top: 0.2rem;
}
.edl-check-detail {
  display: block;
  color: var(--text-dim, #aaa);
  font-size: calc(0.85rem * var(--font-scale, 1));
  margin-top: 0.15rem;
}

/* Error */
.edl-card-error {
  border-color: var(--color-error, #f44336);
}
.edl-error-msg {
  color: var(--color-error, #f44336);
  font-weight: 500;
}

/* Utilities */
.spinner-small {
  display: inline-block;
  width: 1rem; height: 1rem;
  border: 2px solid var(--border, #333);
  border-top-color: var(--accent, #7c5cfc);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
  flex-shrink: 0;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
