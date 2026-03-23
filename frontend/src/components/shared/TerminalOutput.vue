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
    <div v-if="task.status.value === 'running'" class="terminal-progress">
      <div v-if="progressPct !== null" class="terminal-progress-bar" :style="{ width: progressPct + '%' }" role="progressbar" :aria-valuenow="progressPct" aria-valuemin="0" aria-valuemax="100">
        {{ progressPct }}%
      </div>
      <div v-else class="terminal-progress-bar terminal-progress-indeterminate" role="progressbar" aria-label="Operation in progress"></div>
    </div>

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
