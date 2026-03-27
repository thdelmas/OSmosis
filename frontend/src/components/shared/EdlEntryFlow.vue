<script setup>
import { ref, watch, onUnmounted } from 'vue'

const props = defineProps({
  active: { type: Boolean, default: false },
})

const emit = defineEmits(['edl-ready', 'cancel'])

// States: ready | countdown | holding | waiting | success | timeout | error
const state = ref('ready')
const messages = ref([])
const errorMsg = ref('')
const holdCountdown = ref('')  // "Keep holding... 8s" — updated in place
let eventSource = null
let pollTimer = null

watch(() => props.active, (val) => {
  if (val) {
    reset()
  } else {
    cleanup()
  }
})

function reset() {
  state.value = 'ready'
  messages.value = []
  errorMsg.value = ''
  cleanup()
}

function cleanup() {
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

onUnmounted(cleanup)

async function startEdlEntry() {
  state.value = 'countdown'
  messages.value = []
  errorMsg.value = ''

  try {
    const res = await fetch('/api/edl/enter', { method: 'POST' })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      errorMsg.value = data.error || `Request failed (${res.status})`
      state.value = 'error'
      return
    }

    const data = await res.json()
    const taskId = data.task_id
    if (!taskId) {
      errorMsg.value = 'No task ID returned from server.'
      state.value = 'error'
      return
    }

    // Stream task output via SSE
    eventSource = new EventSource(`/api/stream/${taskId}`)
    eventSource.onmessage = (e) => {
      if (!e.data || e.data === '{}') return
      try {
        const msg = JSON.parse(e.data)
        if (msg.level === 'done') {
          eventSource.close()
          eventSource = null
          if (msg.msg === 'done') {
            state.value = 'success'
            startEdlPolling()
          } else {
            state.value = 'timeout'
          }
          return
        }
        if (msg.msg !== undefined) {
          // "Keep holding..." messages update in place, not appended
          if (msg.msg.startsWith('Keep holding')) {
            holdCountdown.value = msg.msg
            if (state.value !== 'holding') state.value = 'holding'
          } else if (msg.msg.includes('release the button')) {
            holdCountdown.value = ''
            state.value = 'waiting'
            messages.value.push(msg)
          } else {
            messages.value.push(msg)
            // Update visual state based on message content
            if (msg.msg.includes('PRESS') && msg.msg.includes('HOLD')) {
              state.value = 'countdown'
            } else if (msg.msg.includes('Scanning USB')) {
              if (state.value !== 'waiting') state.value = 'waiting'
            }
          }
        }
      } catch { /* ignore parse errors */ }
    }
    eventSource.onerror = () => {
      eventSource.close()
      eventSource = null
      if (state.value === 'countdown' || state.value === 'waiting') {
        errorMsg.value = 'Lost connection to server.'
        state.value = 'error'
      }
    }
  } catch (err) {
    errorMsg.value = err.message || 'Network error'
    state.value = 'error'
  }
}

function startEdlPolling() {
  // Confirm EDL is still present, then emit ready
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

  // Stop polling after 10s — device should already be confirmed
  setTimeout(() => {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
      // Already in success state, emit anyway
      emit('edl-ready')
    }
  }, 10000)
}

function retry() {
  reset()
}

function cancel() {
  cleanup()
  reset()
  emit('cancel')
}
</script>

<template>
  <div v-if="active" class="edl-flow">
    <!-- Ready state -->
    <div v-if="state === 'ready'" class="edl-card">
      <h3 class="edl-title">Enter EDL Mode</h3>
      <div class="edl-instructions">
        <p>This will guide you through entering <strong>Qualcomm EDL (Emergency Download) mode</strong> using a deep flash cable.</p>
        <div class="banner banner-info edl-prereqs">
          <strong>Before you start:</strong>
          <ol>
            <li>Your device must be in <strong>fastboot mode</strong>.</li>
            <li>Connect the <strong>EDL / deep flash cable</strong> between your PC and device.</li>
            <li>Locate the <strong>button on the cable</strong> that shorts the USB D+/D- pins.</li>
            <li>When prompted, <strong>press and hold the cable button for at least 10 seconds</strong>.</li>
          </ol>
        </div>
        <div class="banner banner-warn edl-timing-note">
          <strong>Timing:</strong> When the countdown reaches zero, <strong>press and hold the cable button for 10 seconds</strong>.
          Do not release early. The shorted D+/D- pins force the Qualcomm SoC into EDL mode before the bootloader loads.
          The system will tell you when to release.
        </div>
      </div>
      <div class="edl-actions">
        <button class="btn btn-primary" @click="startEdlEntry">Start EDL Entry</button>
        <button class="btn btn-link" @click="cancel">Cancel</button>
      </div>
    </div>

    <!-- Countdown state -->
    <div v-if="state === 'countdown'" class="edl-card edl-card-countdown">
      <h3 class="edl-title">EDL Entry in Progress</h3>
      <div class="edl-countdown-display">
        <div v-for="(msg, i) in messages" :key="i" class="edl-msg" :class="'edl-msg-' + msg.level">
          <span v-if="msg.msg.match(/^[321]\.\.\.$/)" class="edl-big-number">{{ msg.msg }}</span>
          <span v-else-if="msg.msg.includes('PRESS')" class="edl-press-now">{{ msg.msg }}</span>
          <span v-else>{{ msg.msg }}</span>
        </div>
      </div>
      <div class="edl-actions">
        <button class="btn btn-link" @click="cancel">Cancel</button>
      </div>
    </div>

    <!-- Holding state — big countdown in place -->
    <div v-if="state === 'holding'" class="edl-card edl-card-holding">
      <h3 class="edl-title">Hold the button!</h3>
      <div class="edl-hold-display">
        <div class="edl-hold-countdown">{{ holdCountdown }}</div>
        <p class="edl-hold-hint">Do not release until told</p>
      </div>
      <div class="edl-actions">
        <button class="btn btn-link" @click="cancel">Cancel</button>
      </div>
    </div>

    <!-- Waiting state -->
    <div v-if="state === 'waiting'" class="edl-card edl-card-waiting">
      <h3 class="edl-title">Waiting for EDL Device</h3>
      <div class="edl-waiting-display">
        <span class="spinner-small"></span>
        <p>Scanning USB for Qualcomm 9008 device...</p>
      </div>
      <div class="edl-log">
        <div v-for="(msg, i) in messages" :key="i" class="edl-msg" :class="'edl-msg-' + msg.level">
          {{ msg.msg }}
        </div>
      </div>
      <div class="edl-actions">
        <button class="btn btn-link" @click="cancel">Cancel</button>
      </div>
    </div>

    <!-- Success state -->
    <div v-if="state === 'success'" class="edl-card edl-card-success">
      <div class="edl-success-icon">&#x2714;</div>
      <h3 class="edl-title">EDL Mode Detected</h3>
      <p>Device is in Qualcomm 9008 (EDL) mode and ready for flashing.</p>
    </div>

    <!-- Timeout state -->
    <div v-if="state === 'timeout'" class="edl-card edl-card-timeout">
      <h3 class="edl-title">EDL Device Not Detected</h3>
      <div class="banner banner-warn">
        <p>The Qualcomm 9008 device was not found after 30 seconds.</p>
        <p><strong>Common causes:</strong></p>
        <ul>
          <li>The cable button was not pressed at the right moment.</li>
          <li>The deep flash cable is not wired correctly (D+ and D- must be shorted).</li>
          <li>The device rebooted normally instead of entering EDL.</li>
        </ul>
      </div>
      <div class="edl-physical-check">
        <strong>Physical checks:</strong>
        <ul>
          <li>Make sure the cable button clicks firmly and makes contact.</li>
          <li>Try pressing the button slightly <em>before</em> the reboot command is sent.</li>
          <li>If using a DIY cable, verify the short between D+ (green) and D- (white) with a multimeter.</li>
        </ul>
      </div>
      <div class="edl-log">
        <div v-for="(msg, i) in messages" :key="i" class="edl-msg" :class="'edl-msg-' + msg.level">
          {{ msg.msg }}
        </div>
      </div>
      <div class="edl-actions">
        <button class="btn btn-primary" @click="retry">Retry</button>
        <button class="btn btn-link" @click="cancel">Cancel</button>
      </div>
    </div>

    <!-- Error state -->
    <div v-if="state === 'error'" class="edl-card edl-card-error">
      <h3 class="edl-title">Error</h3>
      <div class="banner banner-warn">
        <p>{{ errorMsg || 'An unexpected error occurred.' }}</p>
      </div>
      <div class="edl-actions">
        <button class="btn btn-primary" @click="retry">Retry</button>
        <button class="btn btn-link" @click="cancel">Cancel</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.edl-flow {
  margin: 1rem 0;
}

.edl-card {
  background: var(--bg-card, #1e1e2e);
  border: 1px solid var(--border, #333);
  border-radius: 12px;
  padding: 1.5rem;
  max-width: 640px;
}

.edl-title {
  margin: 0 0 1rem 0;
  font-size: 1.2rem;
}

.edl-instructions p {
  margin: 0.5rem 0;
  line-height: 1.5;
}

.edl-prereqs {
  margin: 1rem 0;
  padding: 1rem 1.25rem;
}

.edl-prereqs ol {
  margin: 0.5rem 0 0 1.25rem;
  padding: 0;
}

.edl-prereqs li {
  margin: 0.35rem 0;
}

.edl-timing-note {
  font-size: 0.9rem;
  opacity: 0.8;
  font-style: italic;
}

.edl-actions {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  margin-top: 1.25rem;
}

.edl-countdown-display {
  min-height: 120px;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.edl-big-number {
  font-size: 2.5rem;
  font-weight: bold;
  font-family: monospace;
  color: var(--color-warn, #ff9800);
}

.edl-press-now {
  font-size: 1.4rem;
  font-weight: bold;
  color: var(--color-error, #f44336);
  animation: edl-pulse 0.5s ease-in-out infinite alternate;
}

@keyframes edl-pulse {
  from { opacity: 1; }
  to { opacity: 0.5; }
}

.edl-hold-display {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 140px;
  gap: 0.5rem;
}

.edl-hold-countdown {
  font-size: 2rem;
  font-weight: bold;
  font-family: monospace;
  color: var(--color-warn, #ff9800);
  animation: edl-pulse 0.5s ease-in-out infinite alternate;
}

.edl-hold-hint {
  font-size: 0.95rem;
  opacity: 0.7;
}

.edl-waiting-display {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.edl-log {
  max-height: 200px;
  overflow-y: auto;
  font-family: monospace;
  font-size: 0.85rem;
  margin-top: 1rem;
  padding: 0.5rem;
  background: var(--bg-terminal, #111);
  border-radius: 6px;
}

.edl-msg {
  padding: 0.15rem 0;
  white-space: pre-wrap;
}

.edl-msg-warn {
  color: var(--color-warn, #ff9800);
}

.edl-msg-error {
  color: var(--color-error, #f44336);
}

.edl-msg-success {
  color: var(--color-success, #4caf50);
}

.edl-msg-cmd {
  color: var(--color-cmd, #888);
}

.edl-success-icon {
  font-size: 3rem;
  color: var(--color-success, #4caf50);
  text-align: center;
  margin-bottom: 0.5rem;
}

.edl-card-success {
  text-align: center;
  border-color: var(--color-success, #4caf50);
}

.edl-card-timeout {
  border-color: var(--color-warn, #ff9800);
}

.edl-card-error {
  border-color: var(--color-error, #f44336);
}

.edl-physical-check {
  margin-top: 1rem;
  font-size: 0.9rem;
}

.edl-physical-check ul {
  margin: 0.35rem 0 0 1.25rem;
  padding: 0;
}

.edl-physical-check li {
  margin: 0.25rem 0;
}
</style>
