<script setup>
import { ref, computed, inject, watch, onMounted, onUnmounted, onBeforeUnmount, nextTick } from 'vue'
import { useRouter, onBeforeRouteLeave } from 'vue-router'
import { useApi } from '@/composables/useApi'
import { useWizard } from '@/composables/useWizard'
import TerminalOutput from '@/components/shared/TerminalOutput.vue'
import GlossaryTip from '@/components/shared/GlossaryTip.vue'
import { parseErrorType, parseTerminalHints } from '@/composables/useErrorGuide'

const router = useRouter()
const { get, post, loading } = useApi()
const { state, deviceLabel, setSubPhase } = useWizard()
const registerTask = inject('registerTask', () => {})

const codename = computed(() => state.detectedDevice?.codename || state.detectedDevice?.match?.codename || '')
const brand = computed(() => (state.detectedDevice?.brand || state.detectedDevice?.match?.brand || '').toLowerCase())
const isSamsung = computed(() => brand.value.includes('samsung'))

// Fallback device label: use codename rather than showing "Unknown device"
const safeDeviceLabel = computed(() => {
  const label = deviceLabel.value
  if (label && label !== 'Unknown device') return label
  if (codename.value) return codename.value
  return 'your device'
})

const selectedRom = computed(() => state.selectedRom)
const downloadDest = computed(() => state._downloadDest || '')
const recoveryImgPath = computed(() => state._recoveryImgPath || '')
const recoveryChoice = computed(() => state._recoveryChoice || '')
const recoverySource = computed(() => state._recoverySource || null)

const phase = ref('overview') // overview | confirm | flash-recovery | flash-rom | done
const error = ref(null)
const taskId = ref(null)
const termRef = ref(null)
const confirmedAction = ref(null) // 'recovery' | 'sideload'

// Battery check before flash
const batteryLevel = ref(null)
const batteryPlugged = ref(false)
const batteryChecked = ref(false)

async function checkBattery() {
  const resp = await get('/api/battery-check')
  if (resp.ok && resp.data) {
    batteryLevel.value = resp.data.level
    batteryPlugged.value = resp.data.plugged
    batteryChecked.value = true
  }
}

// Smart error state
const signatureFailure = ref(false)
const incompleteTransfer = ref(false)
const errorGuide = ref(null)
const lastProgressPct = ref(null)
const sideloadFailCount = ref(0)
const lastMethod = ref('sideload')

// Warn before leaving during active flash operations
const activePhases = ['flash-recovery', 'flash-rom']

function beforeUnloadHandler(e) {
  if (activePhases.includes(phase.value)) {
    e.preventDefault()
    e.returnValue = ''
  }
}

onMounted(() => {
  window.addEventListener('beforeunload', beforeUnloadHandler)
  // Check battery early so the user sees the status before they commit
  checkBattery()
})
onUnmounted(() => window.removeEventListener('beforeunload', beforeUnloadHandler))

onBeforeRouteLeave(() => {
  if (activePhases.includes(phase.value)) {
    return window.confirm('A flash operation is in progress. Leaving now could damage your device. Are you sure?')
  }
})

function requestConfirm(action) {
  confirmedAction.value = action
  phase.value = 'confirm'
  checkBattery()
}

// Explicit data loss acknowledgment
const dataLossAcknowledged = ref(false)

// Hold-to-confirm: user must hold the button for 1.5s to proceed
const holdTimer = ref(null)
const holding = ref(false)

function startHold() {
  holding.value = true
  holdTimer.value = setTimeout(() => {
    holding.value = false
    executeConfirmed()
  }, 1500)
}
function cancelHold() {
  holding.value = false
  if (holdTimer.value) { clearTimeout(holdTimer.value); holdTimer.value = null }
}
onBeforeUnmount(() => cancelHold())

function executeConfirmed() {
  if (confirmedAction.value === 'recovery') flashRecovery()
  else flashRom('sideload')
}

function waitForTask(tid, cb, timeoutMs = 300000) {
  const start = Date.now()
  const poll = setInterval(async () => {
    if (Date.now() - start > timeoutMs) {
      clearInterval(poll)
      cb('error')
      return
    }
    const resp = await get('/api/tasks')
    if (!resp.ok) return
    const task = resp.data?.find(t => t.id === tid)
    if (!task || task.status === 'running') return
    clearInterval(poll)
    cb(task.status)
  }, 2000)
}

// Extract last progress percentage from terminal output
function getLastProgress() {
  const lines = termRef.value?.task?.lines?.value || []
  for (let i = lines.length - 1; i >= Math.max(0, lines.length - 20); i--) {
    const match = lines[i].msg?.match(/(\d{1,3})%/)
    if (match) {
      const val = parseInt(match[1], 10)
      if (val >= 0 && val <= 100) return val
    }
  }
  return null
}

// Analyze terminal output for specific error types after a flash failure
function analyzeFlashError() {
  const checkForErrorType = () => {
    const lines = termRef.value?.task?.lines?.value || []
    const allText = lines.map(l => (l.msg || '').toLowerCase()).join(' ')

    // Capture progress at time of failure
    const pct = getLastProgress()
    if (pct !== null) lastProgressPct.value = pct

    // Check for signature verification failure
    const hasSignatureError =
      allText.includes('__error_type:signature_verification_failed') ||
      allText.includes('rejected this rom') ||
      allText.includes('rom rejected') ||
      allText.includes('rejected by recovery') ||
      allText.includes('require a custom recovery')
    if (hasSignatureError) {
      signatureFailure.value = true
      incompleteTransfer.value = false
      errorGuide.value = null
      error.value = null
      return
    }

    // Check for incomplete transfer
    const hasIncompleteTransfer =
      allText.includes('__error_type:incomplete_transfer') ||
      allText.includes('transfer ended at') ||
      allText.includes('total xfer:')
    if (hasIncompleteTransfer) {
      incompleteTransfer.value = true
      signatureFailure.value = false
      errorGuide.value = null
      error.value = null
      return
    }

    // If transfer stopped partway (has progress but not 100%), treat as incomplete
    if (pct !== null && pct > 0 && pct < 95) {
      incompleteTransfer.value = true
      signatureFailure.value = false
      errorGuide.value = null
      error.value = null
      return
    }

    // Check for other typed errors via the shared parser
    const guide = parseErrorType(lines)
    if (guide) {
      errorGuide.value = guide
      error.value = null
      return
    }

    // Parse terminal for actionable hints
    const hints = parseTerminalHints(lines)
    if (hints.length) {
      error.value = 'Software transfer failed.\n\n' + hints.join('\n')
    }
  }

  // Check repeatedly as stream lines arrive asynchronously
  setTimeout(checkForErrorType, 300)
  setTimeout(checkForErrorType, 1000)
  setTimeout(checkForErrorType, 2000)
  setTimeout(checkForErrorType, 4000)
  // Set fallback error only after final check
  setTimeout(() => {
    if (!signatureFailure.value && !incompleteTransfer.value && !errorGuide.value && !error.value) {
      const pct = lastProgressPct.value
      if (pct !== null && pct > 0) {
        error.value = `Transfer stopped at ${pct}%. Make sure your device is still connected and in the correct mode, then try again.`
      } else {
        error.value = 'Software transfer failed. Make sure your device is still connected and in the correct mode, then try again.'
      }
    }
  }, 5000)
}

function clearErrorState() {
  error.value = null
  signatureFailure.value = false
  incompleteTransfer.value = false
  errorGuide.value = null
  lastProgressPct.value = null
}

// --- Flash recovery (if downloaded) ---
async function flashRecovery() {
  if (!recoveryImgPath.value) return
  clearErrorState()
  phase.value = 'flash-recovery'

  const { ok, data } = await post('/api/flash/recovery', {
    recovery_img: recoveryImgPath.value,
    fix_boot: isSamsung.value,
  })

  if (ok && data?.task_id) {
    taskId.value = data.task_id
    registerTask(data.task_id, `Flash ${recoverySource.value?.name || 'Recovery'}`)
    waitForTask(data.task_id, (status) => {
      if (status === 'done') {
        phase.value = 'flash-rom'
      } else {
        error.value = 'Recovery install failed. Click "Show details" above for more information, or try unplugging and reconnecting your device.'
      }
    })
  } else {
    error.value = data?.error || 'Failed to start recovery flash.'
  }
}

// --- Flash ROM (sideload or push) ---
async function flashRom(method = 'sideload') {
  clearErrorState()
  lastMethod.value = method
  phase.value = 'flash-rom'

  const zipPath = downloadDest.value || selectedRom.value?.manual_path || ''
  if (!zipPath) {
    error.value = 'No ROM file available.'
    return
  }

  const endpoint = method === 'push' ? '/api/flash/push-install' : '/api/sideload'
  const { ok, data } = await post(endpoint, {
    zip_path: zipPath,
    label: selectedRom.value?.name || 'ROM',
  })

  if (ok && data?.task_id) {
    taskId.value = data.task_id
    registerTask(data.task_id, `${method === 'push' ? 'Push' : 'Sideload'} ${selectedRom.value?.name || 'ROM'}`)
    waitForTask(data.task_id, (status) => {
      if (status === 'done') {
        sideloadFailCount.value = 0
        phase.value = 'done'
      } else {
        if (method === 'sideload') sideloadFailCount.value++
        analyzeFlashError()
      }
    })
  } else {
    error.value = data?.error || 'Failed to start flash.'
  }
}

// Auto-switch recommendation: after 2 sideload failures, suggest push
const shouldRecommendPush = computed(() => sideloadFailCount.value >= 2 && lastMethod.value === 'sideload')

function proceed() {
  router.push('/wizard/install')
}

// Update sub-phase label in progress bar
const loadPhaseLabels = { overview: 'Review', confirm: 'Confirm', 'flash-recovery': 'Flashing recovery...', 'flash-rom': 'Installing...', done: 'Done' }
watch(phase, (p) => setSubPhase(loadPhaseLabels[p] || null), { immediate: true })
onUnmounted(() => setSubPhase(null))
</script>

<template>
  <h2 class="step-title">Load software onto {{ safeDeviceLabel }}</h2>

  <!-- ===== Overview ===== -->
  <div v-if="phase === 'overview'">
    <div class="install-guide-box">
      <h3>Ready to load</h3>
      <p>The following will be transferred to your device:</p>
      <ol class="install-steps">
        <li v-if="recoveryImgPath"><strong>{{ recoverySource?.name || 'Recovery' }}</strong> &rarr; <GlossaryTip term="flash">install</GlossaryTip> via <GlossaryTip term="Download Mode" /></li>
        <li><strong>{{ selectedRom?.name || 'ROM' }}</strong> &rarr; install via <GlossaryTip term="sideload" /></li>
      </ol>
    </div>

    <div v-if="batteryChecked && batteryLevel !== null && batteryLevel < 50 && !batteryPlugged" class="info-box info-box--error">
      Battery is at <strong>{{ batteryLevel }}%</strong>. Charge to at least 50% before flashing to prevent a failed update that could leave your device unbootable.
    </div>
    <div v-else-if="batteryChecked && batteryLevel !== null" class="info-box info-box--success">
      Battery: <strong>{{ batteryLevel }}%</strong>{{ batteryPlugged ? ' (charging)' : '' }}
    </div>

    <div class="install-action">
      <button v-if="recoveryImgPath" class="btn btn-large btn-primary" :disabled="loading" @click="requestConfirm('recovery')">
        Flash {{ recoverySource?.name || 'Recovery' }} first &rarr;
      </button>
      <button v-else class="btn btn-large btn-primary" :disabled="loading" @click="requestConfirm('sideload')">
        Start installing software &rarr;
      </button>
    </div>

    <div class="step-nav">
      <button class="btn btn-secondary" @click="router.push('/wizard/connect')">&larr; Back</button>
    </div>
  </div>

  <!-- ===== Confirm before flash ===== -->
  <div v-if="phase === 'confirm'" class="confirm-flash">
    <div class="info-box info-box--warn">
      <h3>Are you sure?</h3>
      <p v-if="confirmedAction === 'recovery'">
        This will flash <strong>{{ recoverySource?.name || 'Recovery' }}</strong> to your device.
        Flashing the wrong recovery can make your device unbootable.
      </p>
      <p v-else>
        This will install <strong>{{ selectedRom?.name || 'ROM' }}</strong> on <strong>{{ safeDeviceLabel }}</strong>.
        This replaces the current operating system and <strong>all data will be erased</strong>.
      </p>
    </div>

    <div v-if="batteryChecked && batteryLevel !== null && batteryLevel < 50 && !batteryPlugged" class="info-box info-box--error" style="margin-top: 0.75rem;">
      Battery is at <strong>{{ batteryLevel }}%</strong>. Charge to at least 50% before flashing to prevent a failed update that could leave your device unbootable.
    </div>
    <div v-else-if="batteryChecked && batteryLevel !== null" class="info-box info-box--success" style="margin-top: 0.75rem;">
      Battery: <strong>{{ batteryLevel }}%</strong>{{ batteryPlugged ? ' (charging)' : '' }}
    </div>

    <div class="confirm-checklist">
      <h4>Pre-flash checklist</h4>
      <label class="confirm-check-item">
        <input type="checkbox" v-model="dataLossAcknowledged" />
        <span>I understand this will erase all data on the device and cannot be undone</span>
      </label>
      <div class="confirm-reminders">
        <p>Make sure:</p>
        <ul>
          <li>The USB cable is plugged in securely (directly to your computer, not a hub)</li>
          <li>You won't need to move or unplug the device during the process</li>
          <li>Your computer won't go to sleep (disable sleep if needed)</li>
          <li>Your device's screen timeout is set to at least 10 minutes (Settings &rarr; Display &rarr; Screen timeout)</li>
        </ul>
      </div>
    </div>

    <div class="confirm-actions">
      <button class="btn btn-secondary" @click="phase = 'overview'; dataLossAcknowledged = false">&larr; Go back</button>
      <button
        class="btn btn-large btn-primary btn-danger btn-hold-confirm"
        :class="{ holding }"
        :disabled="!dataLossAcknowledged || (batteryChecked && batteryLevel !== null && batteryLevel < 50 && !batteryPlugged)"
        :aria-label="holding ? 'Keep holding to confirm flash operation' : 'Press and hold for 1.5 seconds to confirm flash'"
        @mousedown="startHold"
        @mouseup="cancelHold"
        @mouseleave="cancelHold"
        @touchstart.prevent="startHold"
        @touchend="cancelHold"
        @touchcancel="cancelHold"
        @keydown.enter.prevent="startHold"
        @keyup.enter="cancelHold"
      >
        {{ holding ? 'Hold to confirm...' : 'Hold to proceed with flash' }}
      </button>
    </div>
  </div>

  <!-- ===== Flash Recovery ===== -->
  <div v-if="phase === 'flash-recovery'">
    <div class="install-guide-box">
      <h3>Flashing {{ recoverySource?.name || 'Recovery' }}...</h3>
      <p>Make sure your device is in <strong><GlossaryTip term="Download Mode" /></strong>.</p>
    </div>

    <div v-if="taskId" class="task-section">
      <TerminalOutput ref="termRef" :task-id="taskId" />
    </div>

    <div v-if="error" class="info-box info-box--error">
      {{ error }}
      <button class="btn btn-secondary" style="margin-top: 0.5rem;" @click="flashRecovery">Retry</button>
    </div>

    <div class="step-nav">
      <button class="btn btn-secondary" @click="phase = 'overview'">&larr; Back</button>
    </div>
  </div>

  <!-- ===== Flash ROM ===== -->
  <div v-if="phase === 'flash-rom'">
    <div class="install-guide-box">
      <h3>Installing {{ selectedRom?.name || 'ROM' }}...</h3>
      <p>Sending the ROM to your device. <strong>Do not disconnect.</strong></p>
    </div>

    <div v-if="taskId" class="task-section">
      <TerminalOutput ref="termRef" :task-id="taskId" />
    </div>

    <!-- Signature verification failure -->
    <div v-if="signatureFailure" class="install-guide-box install-guide-tip">
      <h3>Your recovery rejected this ROM</h3>
      <p>Stock recovery only accepts manufacturer-signed updates. To install <strong>{{ selectedRom?.name }}</strong>, you need a custom recovery{{ recoverySource ? ` (${recoverySource.name})` : '' }}.</p>
      <p>Your device is safe &mdash; nothing was changed.</p>
      <div class="load-error-actions">
        <button class="btn btn-primary" @click="clearErrorState(); router.push('/wizard/install')">
          Install {{ recoverySource?.name || 'custom recovery' }} &rarr;
        </button>
        <button class="btn btn-secondary" @click="clearErrorState(); flashRom('sideload')">
          Retry sideload
        </button>
      </div>
    </div>

    <!-- Incomplete transfer -->
    <div v-if="incompleteTransfer" class="install-guide-box install-guide-tip">
      <h3>Transfer {{ lastProgressPct ? `stopped at ${lastProgressPct}%` : 'may be incomplete' }}</h3>
      <p>The transfer was interrupted before finishing. Check your device screen first:</p>
      <ul class="install-steps">
        <li>If your device shows <strong>"Install complete"</strong>: tap <strong>Reboot System</strong> &mdash; you're done!</li>
        <li>If your device shows <strong>"Zip corrupt"</strong> or an error: the transfer was cut short.</li>
      </ul>
      <p><strong>USB troubleshooting:</strong></p>
      <ul class="install-steps">
        <li>Use a shorter, higher-quality USB cable (not charge-only)</li>
        <li>Connect directly to your computer &mdash; avoid USB hubs</li>
        <li>Avoid moving or bumping the cable during transfer</li>
        <li>Try a different USB port on your computer</li>
      </ul>
      <div class="load-error-actions">
        <button v-if="shouldRecommendPush" class="btn btn-primary" @click="clearErrorState(); flashRom('push')">
          Switch to push method (recommended) &rarr;
        </button>
        <button v-else class="btn btn-primary" @click="clearErrorState(); flashRom('push')">
          Try push method (more reliable for unstable USB)
        </button>
        <button class="btn btn-secondary" @click="clearErrorState(); flashRom('sideload')">
          Retry sideload
        </button>
        <button class="btn btn-secondary" @click="phase = 'done'">
          It worked &mdash; continue
        </button>
      </div>
    </div>

    <!-- Typed error guide from backend -->
    <div v-if="errorGuide" class="install-guide-box install-guide-tip">
      <h3>{{ errorGuide.title }}</h3>
      <p>{{ errorGuide.message }}</p>
      <ol class="install-steps">
        <li v-for="(step, i) in errorGuide.steps" :key="i">{{ step }}</li>
      </ol>
      <div class="load-error-actions">
        <button class="btn btn-primary" @click="clearErrorState(); flashRom('sideload')">Retry sideload</button>
        <button class="btn btn-secondary" @click="clearErrorState(); flashRom('push')">Try push method</button>
      </div>
    </div>

    <!-- Auto-switch recommendation after repeated sideload failures -->
    <div v-if="shouldRecommendPush && !incompleteTransfer && !signatureFailure && !errorGuide && error" class="install-guide-box install-guide-tip">
      <p>Sideload has failed multiple times. The <strong>push method</strong> transfers the file differently and is often more reliable with unstable USB connections.</p>
      <div class="load-error-actions">
        <button class="btn btn-primary" @click="clearErrorState(); sideloadFailCount = 0; flashRom('push')">
          Switch to push method &rarr;
        </button>
      </div>
    </div>

    <!-- Generic error -->
    <div v-if="error" class="info-box info-box--error" style="white-space: pre-line;">
      {{ error }}
      <div class="load-error-actions">
        <button class="btn btn-primary" @click="clearErrorState(); flashRom('push')">
          Try push method (more reliable)
        </button>
        <button class="btn btn-secondary" @click="clearErrorState(); flashRom('sideload')">
          Retry sideload
        </button>
      </div>
    </div>

    <div v-if="!taskId || error || signatureFailure || incompleteTransfer || errorGuide" class="step-nav">
      <button class="btn btn-secondary" @click="phase = 'overview'">&larr; Back</button>
    </div>
  </div>

  <!-- ===== Done ===== -->
  <div v-if="phase === 'done'">
    <div class="install-guide-box install-guide-success">
      <h3>Transfer complete!</h3>
      <p><strong>{{ selectedRom?.name }}</strong> has been loaded onto {{ safeDeviceLabel }}.</p>
      <p class="done-hint">Your device may still be processing the installation. Check the device screen before continuing.</p>
    </div>

    <div class="install-action">
      <button class="btn btn-large btn-primary" @click="proceed">
        Continue to final steps &rarr;
      </button>
    </div>
  </div>
</template>
