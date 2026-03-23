<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useApi } from '@/composables/useApi'

const props = defineProps({
  workflowId: { type: String, default: null },
  taskId: { type: String, default: null },
})

const emit = defineEmits(['done', 'resume'])

const { get, post } = useApi()

const workflow = ref(null)
const pollTimer = ref(null)

const stages = computed(() => workflow.value?.stages || [])
const currentStage = computed(() => workflow.value?.current_stage || '')
const workflowStatus = computed(() => workflow.value?.status || 'pending')

const statusIcon = (status) => {
  const icons = {
    pending: '\u25CB',
    in_progress: '\u23F3',
    completed: '\u2713',
    failed: '\u2717',
    skipped: '\u2014',
  }
  return icons[status] || '\u25CB'
}

const statusClass = (status) => {
  return `stage-${status}`
}

async function loadWorkflow() {
  if (!props.workflowId) return
  const { ok, data } = await get(`/api/workflows/${props.workflowId}`)
  if (ok) {
    workflow.value = data
    if (data.status === 'completed' || data.status === 'failed') {
      stopPolling()
      emit('done', data.status)
    }
  }
}

async function handleResume(stageId) {
  if (!props.workflowId) return
  const { ok, data } = await post(
    `/api/workflows/${props.workflowId}/resume?from=${stageId}`
  )
  if (ok) {
    emit('resume', { taskId: data.task_id, stageId })
    startPolling()
  }
}

function startPolling() {
  if (pollTimer.value) return
  pollTimer.value = setInterval(loadWorkflow, 2000)
}

function stopPolling() {
  if (pollTimer.value) {
    clearInterval(pollTimer.value)
    pollTimer.value = null
  }
}

watch(() => props.workflowId, (id) => {
  if (id) {
    loadWorkflow()
    startPolling()
  } else {
    stopPolling()
  }
}, { immediate: true })

onUnmounted(() => stopPolling())
</script>

<template>
  <div v-if="workflow" class="workflow-tracker">
    <div class="workflow-header">
      <span class="workflow-device">{{ workflow.device_id }}</span>
      <span class="workflow-status" :class="'wf-' + workflowStatus">
        {{ workflowStatus }}
      </span>
    </div>

    <div class="stages">
      <div
        v-for="(stage, i) in stages"
        :key="stage.id"
        class="stage"
        :class="[statusClass(stage.status), { active: stage.id === currentStage }]"
      >
        <div class="stage-connector" v-if="i > 0"></div>
        <div class="stage-indicator">
          <span class="stage-icon">{{ statusIcon(stage.status) }}</span>
        </div>
        <div class="stage-info">
          <span class="stage-name">{{ stage.name }}</span>
          <span v-if="stage.error" class="stage-error">{{ stage.error }}</span>
        </div>
        <button
          v-if="stage.status === 'failed'"
          class="btn-retry"
          @click="handleResume(stage.id)"
        >
          Retry
        </button>
      </div>
    </div>

    <div v-if="workflowStatus === 'failed'" class="workflow-actions">
      <button class="btn-resume" @click="handleResume('')">Resume</button>
    </div>
  </div>
</template>

<style scoped>
.workflow-tracker {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-card, 8px);
  padding: 1rem;
  margin: 1rem 0;
}

.workflow-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
  font-size: calc(0.9rem * var(--font-scale, 1));
}

.workflow-device {
  font-weight: 600;
  color: var(--text);
}

.workflow-status {
  font-size: calc(0.8rem * var(--font-scale, 1));
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.wf-running { background: var(--accent-dim, #1e3a5f); color: var(--accent, #60a5fa); }
.wf-completed { background: rgba(74, 222, 128, 0.15); color: var(--green, #4ade80); }
.wf-failed { background: rgba(248, 113, 113, 0.15); color: var(--red, #f87171); }
.wf-pending { background: var(--bg-hover); color: var(--text-dim); }

.stages {
  display: flex;
  flex-direction: column;
  gap: 0;
  position: relative;
}

.stage {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0;
  position: relative;
}

.stage-connector {
  position: absolute;
  left: 0.75rem;
  top: -0.25rem;
  width: 2px;
  height: 0.75rem;
  background: var(--border);
}

.stage-indicator {
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 0.8rem;
  border: 2px solid var(--border);
  background: var(--bg);
  transition: all 0.2s;
}

.stage-completed .stage-indicator { border-color: var(--green, #4ade80); color: var(--green, #4ade80); background: rgba(74, 222, 128, 0.1); }
.stage-in_progress .stage-indicator { border-color: var(--accent, #60a5fa); color: var(--accent, #60a5fa); background: rgba(96, 165, 250, 0.1); }
.stage-failed .stage-indicator { border-color: var(--red, #f87171); color: var(--red, #f87171); background: rgba(248, 113, 113, 0.1); }
.stage-skipped .stage-indicator { border-color: var(--text-dim); color: var(--text-dim); opacity: 0.5; }

.stage-info {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.stage-name {
  font-size: calc(0.85rem * var(--font-scale, 1));
  color: var(--text);
}

.stage-completed .stage-name { color: var(--green, #4ade80); }
.stage-failed .stage-name { color: var(--red, #f87171); }
.stage-in_progress .stage-name { color: var(--accent, #60a5fa); font-weight: 600; }
.stage-pending .stage-name { color: var(--text-dim); }
.stage-skipped .stage-name { color: var(--text-dim); text-decoration: line-through; }

.stage-error {
  font-size: calc(0.75rem * var(--font-scale, 1));
  color: var(--red, #f87171);
  margin-top: 0.15rem;
}

.active .stage-indicator {
  box-shadow: 0 0 0 3px rgba(96, 165, 250, 0.2);
}

.btn-retry, .btn-resume {
  padding: 0.3rem 0.75rem;
  border: 1px solid var(--accent, #60a5fa);
  background: transparent;
  color: var(--accent, #60a5fa);
  border-radius: 4px;
  cursor: pointer;
  font-size: calc(0.8rem * var(--font-scale, 1));
  transition: all 0.15s;
}

.btn-retry:hover, .btn-resume:hover {
  background: var(--accent, #60a5fa);
  color: var(--bg);
}

.workflow-actions {
  margin-top: 1rem;
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
}
</style>
