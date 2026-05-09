<script setup>
import { ref, computed, watch, nextTick, onUnmounted } from 'vue'
import { useTask } from '@/composables/useTask'
import { parseErrorType, parseTerminalHints } from '@/composables/useErrorGuide'

const props = defineProps({
  taskId: { type: String, default: null },
})

const emit = defineEmits(['done'])

const termEl = ref(null)
const task = useTask()
const pinned = ref(true)
const confirmingAbort = ref(false)
const expanded = ref(false)

watch(() => props.taskId, (id) => {
  if (id) {
    pinned.value = true
    confirmingAbort.value = false
    expanded.value = false
    task.stream(id)
  }
}, { immediate: true })

watch(task.status, (s) => {
  if (s === 'done' || s === 'error') emit('done', s)
})

// Auto-scroll only when pinned
watch(() => task.lines.value.length, async () => {
  if (!pinned.value || !expanded.value) return
  await nextTick()
  if (termEl.value) {
    termEl.value.scrollTop = termEl.value.scrollHeight
  }
})

function handleScroll() {
  if (!termEl.value) return
  const el = termEl.value
  const atBottom = (el.scrollHeight - el.scrollTop - el.clientHeight) < 30
  pinned.value = atBottom
}

function scrollToBottom() {
  pinned.value = true
  if (termEl.value) termEl.value.scrollTop = termEl.value.scrollHeight
}

function requestAbort() {
  confirmingAbort.value = true
}

function confirmAbort() {
  confirmingAbort.value = false
  task.cancel()
}

function cancelAbort() {
  confirmingAbort.value = false
}

// Human-readable status summary from the last few log lines
const statusSummary = computed(() => {
  const lines = task.lines.value
  if (!lines.length) return 'Starting...'

  // Walk backwards to find the most recent meaningful line
  for (let i = lines.length - 1; i >= Math.max(0, lines.length - 5); i--) {
    const msg = lines[i].msg?.trim()
    if (!msg) continue

    // Extract percentage if present
    const pctMatch = msg.match(/(\d{1,3})%/)
    if (pctMatch) return `${pctMatch[1]}% complete`

    // Shorten to first 80 chars for display
    if (msg.length > 80) return msg.slice(0, 77) + '...'
    return msg
  }

  return 'Working...'
})

const statusIcon = computed(() => {
  const s = task.status.value
  if (s === 'done') return '\u2705'   // check mark
  if (s === 'error') return '\u274C'  // cross mark
  if (s === 'reconnecting') return '\u26A0\uFE0F' // warning
  return '\u23F3'                      // hourglass
})

const statusLabel = computed(() => {
  const s = task.status.value
  if (s === 'done') return 'Finished!'
  if (s === 'error') return 'Something went wrong'
  if (s === 'reconnecting') return 'Reconnecting...'
  return 'In progress'
})

// Rough progress percentage from log lines
const progressPct = computed(() => {
  const lines = task.lines.value
  for (let i = lines.length - 1; i >= Math.max(0, lines.length - 10); i--) {
    const pctMatch = lines[i].msg?.match(/(\d{1,3})%/)
    if (pctMatch) {
      const val = parseInt(pctMatch[1], 10)
      if (val >= 0 && val <= 100) return val
    }
  }
  if (task.status.value === 'done') return 100
  return null
})

// Transfer speed and ETA from common tool output (wget, curl, ipfs).
// Speed: "1.23M/s", "456K/s", "2.1 MB/s", "789 kB/s".
// ETA: "eta 5s", "eta 1m 30s", "ETA 02:15".
const transferStats = computed(() => {
  const lines = task.lines.value
  let speed = null
  let eta = null
  for (let i = lines.length - 1; i >= Math.max(0, lines.length - 10); i--) {
    const msg = lines[i].msg || ''
    if (!speed) {
      const m = msg.match(/(\d+(?:\.\d+)?)\s*([KMG])i?B?\/s/i)
      if (m) speed = `${m[1]} ${m[2].toUpperCase()}B/s`
    }
    if (!eta) {
      const m = msg.match(/eta\s+([0-9hms: ]+?)(?:\s|$|,|\)|\])/i)
      if (m) eta = m[1].trim()
    }
    if (speed && eta) break
  }
  if (!speed && !eta) return null
  return { speed, eta }
})

// Elapsed time tracker for indeterminate progress
const elapsed = ref(0)
let elapsedTimer = null

watch(task.status, (s) => {
  if (s === 'running' && !elapsedTimer) {
    elapsed.value = 0
    elapsedTimer = setInterval(() => { elapsed.value++ }, 1000)
  } else if (s !== 'running' && elapsedTimer) {
    clearInterval(elapsedTimer)
    elapsedTimer = null
  }
})

onUnmounted(() => {
  if (elapsedTimer) clearInterval(elapsedTimer)
})

const elapsedLabel = computed(() => {
  const s = elapsed.value
  if (s < 60) return `${s}s`
  const m = Math.floor(s / 60)
  const rem = s % 60
  return `${m}m ${rem}s`
})

// Stage indicator — most recent `[N/M] Label (PCT%)` line emitted by
// `Task.progress()`. We render a compact stepper so users can see what
// the operation is doing now and how many stages remain.
const currentStage = computed(() => {
  const lines = task.lines.value
  for (let i = lines.length - 1; i >= Math.max(0, lines.length - 40); i--) {
    const msg = lines[i].msg || ''
    const m = msg.match(/^\s*\[(\d+)\/(\d+)\]\s+(.+?)\s*(?:\((\d{1,3})%\))?\s*$/)
    if (m) {
      const total = parseInt(m[2], 10)
      if (total < 2) return null
      let label = m[3].trim()
      // Strip trailing em-dash + detail so the headline stays compact.
      const dashIdx = label.indexOf(' — ')
      if (dashIdx > 0) label = label.slice(0, dashIdx)
      return {
        step: parseInt(m[1], 10),
        total,
        label,
      }
    }
  }
  return null
})

// Retry status — most recent __retry:N/M marker in the last few lines.
// Cleared once a fresh non-retry line arrives (so a successful resume
// hides the banner without waiting for the task to end).
const retryStatus = computed(() => {
  const lines = task.lines.value
  for (let i = lines.length - 1; i >= Math.max(0, lines.length - 8); i--) {
    const msg = lines[i].msg || ''
    const m = msg.match(/__retry:(\d+)\/(\d+)/)
    if (m) return { attempt: parseInt(m[1], 10), max: parseInt(m[2], 10) }
    // If we hit a substantial post-retry line (progress, success), stop.
    if (/\d+%|Command succeeded|fetched|saved/i.test(msg)) return null
  }
  return null
})

// Error guide shown after task failure
const errorGuide = computed(() => {
  if (task.status.value !== 'error') return null
  return parseErrorType(task.lines.value)
})

const errorHints = computed(() => {
  if (task.status.value !== 'error') return []
  return parseTerminalHints(task.lines.value)
})

defineExpose({ task })
</script>

<template>
  <div v-if="task.lines.value.length > 0 || task.status.value === 'running'" class="terminal-wrapper">
    <!-- Human-friendly status bar -->
    <div class="terminal-status" :class="'terminal-status--' + task.status.value" aria-live="polite">
      <span class="terminal-status-icon" aria-hidden="true">{{ statusIcon }}</span>
      <div class="terminal-status-info">
        <strong class="terminal-status-label">{{ statusLabel }}</strong>
        <span class="terminal-status-summary">{{ statusSummary }}</span>
        <span v-if="task.status.value === 'running'" class="terminal-status-elapsed">{{ elapsedLabel }}</span>
      </div>
      <button
        class="terminal-toggle"
        @click="expanded = !expanded"
        :aria-expanded="expanded"
        aria-label="Show or hide technical details"
      >
        {{ expanded ? 'Hide details' : 'Show details' }}
      </button>
    </div>

    <!-- Stage indicator (rendered when the backend emits [N/M] markers via task.progress) -->
    <div v-if="currentStage && task.status.value === 'running'" class="terminal-stage" aria-live="polite">
      <ol class="terminal-stage-dots" :aria-label="`Step ${currentStage.step} of ${currentStage.total}: ${currentStage.label}`">
        <li
          v-for="n in currentStage.total"
          :key="n"
          class="terminal-stage-dot"
          :class="{
            'terminal-stage-dot--done': n < currentStage.step,
            'terminal-stage-dot--current': n === currentStage.step,
          }"
          aria-hidden="true"
        ></li>
      </ol>
      <span class="terminal-stage-text">
        <strong>Step {{ currentStage.step }} of {{ currentStage.total }}</strong>
        <span class="terminal-stage-label">— {{ currentStage.label }}</span>
      </span>
    </div>

    <!-- Retry banner (visible during inter-attempt waits and the next attempt) -->
    <div v-if="retryStatus && task.status.value === 'running'" class="terminal-retry" role="status" aria-live="polite">
      <span class="terminal-retry-icon" aria-hidden="true">&#x21bb;</span>
      <span class="terminal-retry-text">
        Retrying after a transient failure — <strong>attempt {{ retryStatus.attempt }} of {{ retryStatus.max }}</strong>.
      </span>
      <div v-if="confirmingAbort" class="abort-confirm" style="margin-left: auto;">
        <span class="abort-confirm-label">Give up?</span>
        <button class="btn-abort btn-abort-yes" @click="confirmAbort">Yes, give up</button>
        <button class="btn-abort-no" @click="cancelAbort">Keep retrying</button>
      </div>
      <button v-else class="btn-abort" style="margin-left: auto;" @click="requestAbort">Give up</button>
    </div>

    <!-- Error guide (shown on failure) -->
    <div v-if="errorGuide" class="terminal-error-guide" role="alert">
      <strong class="terminal-error-guide-title">{{ errorGuide.title }}</strong>
      <p class="terminal-error-guide-msg">{{ errorGuide.message }}</p>
      <ol v-if="errorGuide.steps" class="terminal-error-guide-steps">
        <li v-for="(step, i) in errorGuide.steps" :key="i">{{ step }}</li>
      </ol>
    </div>
    <div v-else-if="errorHints.length" class="terminal-error-hints" role="alert">
      <strong>Possible fixes:</strong>
      <ul>
        <li v-for="(hint, i) in errorHints" :key="i">{{ hint }}</li>
      </ul>
    </div>

    <!-- Progress bar (determinate if percentage detected, indeterminate otherwise) -->
    <template v-if="task.status.value === 'running'">
      <div class="terminal-progress">
        <div v-if="progressPct !== null" class="terminal-progress-bar" :style="{ width: progressPct + '%' }" role="progressbar" :aria-valuenow="progressPct" aria-valuemin="0" aria-valuemax="100">
          {{ progressPct }}%
        </div>
        <div v-else class="terminal-progress-bar terminal-progress-indeterminate" role="progressbar" aria-label="Operation in progress"></div>
      </div>
      <div v-if="transferStats" class="terminal-progress-stats" aria-live="polite">
        <span v-if="transferStats.speed">{{ transferStats.speed }}</span>
        <span v-if="transferStats.eta">ETA {{ transferStats.eta }}</span>
      </div>
    </template>

    <!-- Collapsible terminal -->
    <div v-show="expanded" ref="termEl" class="terminal active" @scroll="handleScroll">
      <div class="line info" v-if="task.lines.value.length === 0 && task.status.value === 'running'">
        Connecting...
      </div>
      <div
        v-for="(line, i) in task.lines.value"
        :key="i"
        class="line"
        :class="line.level"
      >
        {{ line.msg }}
      </div>
    </div>
    <div v-if="expanded" class="terminal-controls">
      <button
        v-if="!pinned && task.status.value === 'running'"
        class="btn-scroll-bottom"
        @click="scrollToBottom"
        aria-label="Scroll to bottom"
      >&#x2193; Latest</button>
      <template v-if="task.status.value === 'running'">
        <div v-if="confirmingAbort" class="abort-confirm">
          <span class="abort-confirm-label">Stop this operation?</span>
          <button class="btn-abort btn-abort-yes" @click="confirmAbort">Yes, stop</button>
          <button class="btn-abort-no" @click="cancelAbort">Keep going</button>
        </div>
        <button v-else class="btn-abort" @click="requestAbort">Abort</button>
      </template>
    </div>
  </div>
</template>
