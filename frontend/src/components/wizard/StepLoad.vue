<script setup>
import { ref, computed, inject, watch, onMounted, onUnmounted, onBeforeUnmount } from 'vue'
import { useRouter, onBeforeRouteLeave } from 'vue-router'
import { useApi } from '@/composables/useApi'
import { useWizard } from '@/composables/useWizard'
import TerminalOutput from '@/components/shared/TerminalOutput.vue'
import GlossaryTip from '@/components/shared/GlossaryTip.vue'

const router = useRouter()
const { get, post, loading } = useApi()
const { state, deviceLabel, setSubPhase } = useWizard()
const registerTask = inject('registerTask', () => {})

const codename = computed(() => state.detectedDevice?.codename || state.detectedDevice?.match?.codename || '')
const brand = computed(() => (state.detectedDevice?.brand || state.detectedDevice?.match?.brand || '').toLowerCase())
const isSamsung = computed(() => brand.value.includes('samsung'))

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

// Warn before leaving during active flash operations
const activePhases = ['flash-recovery', 'flash-rom']

function beforeUnloadHandler(e) {
  if (activePhases.includes(phase.value)) {
    e.preventDefault()
    e.returnValue = ''
  }
}

onMounted(() => window.addEventListener('beforeunload', beforeUnloadHandler))
onUnmounted(() => window.removeEventListener('beforeunload', beforeUnloadHandler))

onBeforeRouteLeave(() => {
  if (activePhases.includes(phase.value)) {
    return window.confirm('A flash operation is in progress. Leaving now could damage your device. Are you sure?')
  }
})

function requestConfirm(action) {
  confirmedAction.value = action
  phase.value = 'confirm'
}

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

// --- Flash recovery (if downloaded) ---
async function flashRecovery() {
  if (!recoveryImgPath.value) return
  error.value = null
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
  error.value = null
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
        phase.value = 'done'
      } else {
        error.value = 'Software transfer failed. Click "Show details" above for more information. You can try the alternative method, or unplug and reconnect your device and retry.'
      }
    })
  } else {
    error.value = data?.error || 'Failed to start flash.'
  }
}

function proceed() {
  router.push('/wizard/install')
}

// Update sub-phase label in progress bar
const loadPhaseLabels = { overview: 'Review', confirm: 'Confirm', 'flash-recovery': 'Flashing recovery...', 'flash-rom': 'Installing...', done: 'Done' }
watch(phase, (p) => setSubPhase(loadPhaseLabels[p] || null), { immediate: true })
onUnmounted(() => setSubPhase(null))
</script>

<template>
  <h2 class="step-title">Load software onto {{ deviceLabel || 'your device' }}</h2>

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
        This will install <strong>{{ selectedRom?.name || 'ROM' }}</strong> on <strong>{{ deviceLabel || 'your device' }}</strong>.
        This replaces the current operating system and <strong>all data may be erased</strong>.
      </p>
      <p>Make sure your device is connected and has sufficient battery (50%+).</p>
    </div>
    <div class="confirm-actions">
      <button class="btn btn-secondary" @click="phase = 'overview'">&larr; Go back</button>
      <button
        class="btn btn-large btn-primary btn-danger btn-hold-confirm"
        :class="{ holding }"
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

    <div v-if="error" class="info-box info-box--error">
      {{ error }}
      <div style="margin-top: 0.5rem; display: flex; gap: 0.5rem;">
        <button class="btn btn-primary" @click="flashRom('push')">Try alternative method</button>
        <button class="btn btn-secondary" @click="flashRom('sideload')">Retry transfer</button>
      </div>
    </div>

    <div class="step-nav">
      <button class="btn btn-secondary" @click="phase = 'overview'">&larr; Back</button>
    </div>
  </div>

  <!-- ===== Done ===== -->
  <div v-if="phase === 'done'">
    <div class="install-guide-box install-guide-success">
      <h3>Transfer complete!</h3>
      <p><strong>{{ selectedRom?.name }}</strong> has been loaded onto your device.</p>
    </div>

    <div class="install-action">
      <button class="btn btn-large btn-primary" @click="proceed">
        Finish installation &rarr;
      </button>
    </div>
  </div>
</template>
