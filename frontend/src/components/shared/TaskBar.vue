<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useApi } from '@/composables/useApi'

const { get } = useApi()

const activeTasks = ref([])
const expanded = ref(null) // task id being viewed
const taskLines = ref({})
const visible = ref(false)

let pollInterval = null

function startPolling() {
  if (pollInterval) return
  pollInterval = setInterval(loadTasks, 5000)
}

function stopPolling() {
  if (pollInterval) { clearInterval(pollInterval); pollInterval = null }
}

function handleVisibility() {
  if (document.hidden) {
    stopPolling()
  } else {
    loadTasks()
    startPolling()
  }
}

onMounted(() => {
  loadTasks()
  startPolling()
  document.addEventListener('visibilitychange', handleVisibility)
})

onUnmounted(() => {
  stopPolling()
  document.removeEventListener('visibilitychange', handleVisibility)
  for (const es of Object.values(eventSources)) {
    es.close()
  }
})

async function loadTasks() {
  // Check localStorage for known task IDs
  const stored = getStoredTasks()
  if (stored.length === 0) {
    visible.value = false
    return
  }

  // Check backend for their status
  const { ok, data } = await get('/api/tasks')
  if (!ok) return

  const backendMap = {}
  for (const t of data) {
    backendMap[t.id] = t
  }

  // Update stored tasks with backend status
  const updated = []
  for (const st of stored) {
    const backend = backendMap[st.id]
    if (backend) {
      updated.push({ ...st, status: backend.status })
    } else {
      // Task no longer on backend — mark as lost
      updated.push({ ...st, status: 'lost' })
    }
  }

  // Clean out old finished tasks (keep for 5 minutes)
  const now = Date.now()
  activeTasks.value = updated.filter(t => {
    if (t.status === 'running') return true
    if (t.status === 'lost') return (now - (t.startedAt || 0)) < 60000
    return (now - (t.finishedAt || now)) < 300000
  })

  saveStoredTasks(activeTasks.value)
  visible.value = activeTasks.value.length > 0

  // Auto-stream running tasks
  for (const t of activeTasks.value) {
    if (t.status === 'running' && !eventSources[t.id]) {
      streamTask(t.id)
    }
  }
}

const eventSources = {}

function streamTask(id) {
  if (eventSources[id]) return
  taskLines.value[id] = taskLines.value[id] || []

  const es = new EventSource(`/api/stream/${id}`)
  eventSources[id] = es

  es.onmessage = (e) => {
    if (!e.data || e.data === '{}') return
    try {
      const data = JSON.parse(e.data)
      if (data.level === 'done') {
        es.close()
        delete eventSources[id]
        // Update task status
        const task = activeTasks.value.find(t => t.id === id)
        if (task) {
          task.status = data.msg === 'done' ? 'done' : 'error'
          task.finishedAt = Date.now()
          saveStoredTasks(activeTasks.value)
        }
        return
      }
      if (data.msg) {
        if (!taskLines.value[id]) taskLines.value[id] = []
        taskLines.value[id].push({ msg: data.msg, level: data.level || 'info' })
        // Keep last 200 lines
        if (taskLines.value[id].length > 200) {
          taskLines.value[id] = taskLines.value[id].slice(-200)
        }
      }
    } catch { /* ignore */ }
  }

  es.onerror = () => {
    es.close()
    delete eventSources[id]
  }
}

function toggleExpand(id) {
  expanded.value = expanded.value === id ? null : id
  if (expanded.value && !eventSources[id]) {
    const task = activeTasks.value.find(t => t.id === id)
    if (task?.status === 'running') streamTask(id)
  }
}

function dismiss(id) {
  activeTasks.value = activeTasks.value.filter(t => t.id !== id)
  saveStoredTasks(activeTasks.value)
  if (eventSources[id]) {
    eventSources[id].close()
    delete eventSources[id]
  }
  delete taskLines.value[id]
  if (activeTasks.value.length === 0) visible.value = false
}

function dismissAll() {
  for (const id of Object.keys(eventSources)) {
    eventSources[id].close()
    delete eventSources[id]
  }
  activeTasks.value = []
  taskLines.value = {}
  saveStoredTasks([])
  visible.value = false
}

// --- localStorage ---
function getStoredTasks() {
  try {
    return JSON.parse(localStorage.getItem('osmosis-tasks') || '[]')
  } catch { return [] }
}

function saveStoredTasks(tasks) {
  try {
    localStorage.setItem('osmosis-tasks', JSON.stringify(tasks))
  } catch { /* ignore */ }
}

// Public: register a new task from anywhere
function registerTask(id, label) {
  const entry = { id, label: label || 'Task', status: 'running', startedAt: Date.now() }
  activeTasks.value.push(entry)
  saveStoredTasks(activeTasks.value)
  visible.value = true
  streamTask(id)
}

defineExpose({ registerTask })

const statusIcon = (s) => {
  if (s === 'running') return '\u23F3'
  if (s === 'done') return '\u2705'
  if (s === 'error') return '\u274C'
  return '\u2753'
}
</script>

<template>
  <Teleport to="body">
    <div v-if="visible" class="taskbar">
      <div class="taskbar-header">
        <strong>Tasks ({{ activeTasks.filter(t => t.status === 'running').length }} running)</strong>
        <button class="taskbar-clear" @click="dismissAll" v-if="activeTasks.every(t => t.status !== 'running')">Clear all</button>
      </div>
      <div
        v-for="task in activeTasks"
        :key="task.id"
        class="taskbar-item"
        :class="'taskbar-' + task.status"
      >
        <div class="taskbar-item-header" @click="toggleExpand(task.id)">
          <span class="taskbar-icon">{{ statusIcon(task.status) }}</span>
          <span class="taskbar-label">{{ task.label }}</span>
          <span class="taskbar-id">{{ task.id }}</span>
          <button
            v-if="task.status !== 'running'"
            class="taskbar-dismiss"
            @click.stop="dismiss(task.id)"
          >&times;</button>
        </div>
        <div v-if="expanded === task.id" class="taskbar-terminal">
          <div v-if="task.status === 'lost'" class="taskbar-lost-guide">
            This task is no longer tracked by the server. It may have completed while OSmosis was restarting, or the server was restarted.
            <button class="taskbar-retry-link" @click.stop="dismiss(task.id)">Dismiss</button>
          </div>
          <div
            v-for="(line, i) in (taskLines[task.id] || []).slice(-50)"
            :key="i"
            class="taskbar-line"
            :class="line.level"
          >{{ line.msg }}</div>
          <div v-if="!taskLines[task.id]?.length && task.status !== 'lost'" class="taskbar-line info">No output yet.</div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.taskbar {
  position: fixed;
  bottom: 0;
  right: 1rem;
  width: min(400px, calc(100vw - 2rem));
  max-height: 50vh;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-bottom: none;
  border-radius: var(--radius-card) var(--radius-card) 0 0;
  box-shadow: 0 -4px 20px rgba(0,0,0,0.3);
  z-index: 1000;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.taskbar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.6rem 0.85rem;
  border-bottom: 1px solid var(--border);
  font-size: calc(0.85rem * var(--font-scale));
  color: var(--text);
  flex-shrink: 0;
}

.taskbar-clear {
  background: none;
  border: none;
  color: var(--text-dim);
  cursor: pointer;
  font-size: calc(0.8rem * var(--font-scale));
}
.taskbar-clear:hover { color: var(--accent); }

.taskbar-item {
  border-bottom: 1px solid var(--border);
}

.taskbar-item-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.85rem;
  cursor: pointer;
  transition: background var(--transition-fast);
}
.taskbar-item-header:hover { background: var(--bg-hover); }

.taskbar-icon { font-size: 1em; }
.taskbar-label { flex: 1; font-size: calc(0.85rem * var(--font-scale)); font-weight: 500; }
.taskbar-id { font-size: calc(0.7rem * var(--font-scale)); color: var(--text-dim); font-family: monospace; }
.taskbar-dismiss {
  background: none;
  border: none;
  color: var(--text-dim);
  cursor: pointer;
  font-size: 1.1em;
  padding: 0 0.2rem;
}
.taskbar-dismiss:hover { color: var(--text); }

.taskbar-terminal {
  max-height: 200px;
  overflow-y: auto;
  padding: 0.4rem 0.85rem;
  background: var(--bg);
  font-family: monospace;
  font-size: calc(0.75rem * var(--font-scale));
  line-height: 1.5;
}

.taskbar-line { color: var(--text-dim); }
.taskbar-line.success { color: var(--green, #4ade80); }
.taskbar-line.error { color: var(--red, #f87171); }
.taskbar-line.warn { color: var(--yellow, #fbbf24); }
.taskbar-line.cmd { color: var(--accent); }

.taskbar-running .taskbar-label { color: var(--accent); }
.taskbar-done .taskbar-label { color: var(--green, #4ade80); }
.taskbar-error .taskbar-label { color: var(--red, #f87171); }
.taskbar-lost .taskbar-label { color: var(--text-dim); }

.taskbar-lost-guide {
  color: var(--text-dim);
  font-family: inherit;
  font-size: calc(0.8rem * var(--font-scale, 1));
  line-height: 1.5;
  padding: 0.25rem 0 0.5rem;
}

.taskbar-retry-link {
  background: none;
  border: none;
  color: var(--accent, #36d8b7);
  cursor: pointer;
  font-size: inherit;
  padding: 0;
  text-decoration: underline;
  margin-top: 0.25rem;
  display: block;
}
</style>
