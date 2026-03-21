<script setup>
import { ref, watch, nextTick } from 'vue'
import { useTask } from '@/composables/useTask'

const props = defineProps({
  taskId: { type: String, default: null },
})

const emit = defineEmits(['done'])

const termEl = ref(null)
const task = useTask()

watch(() => props.taskId, (id) => {
  if (id) task.stream(id)
})

watch(() => task.status.value, (s) => {
  if (s === 'done' || s === 'error') emit('done', s)
})

// Auto-scroll
watch(() => task.lines.value.length, async () => {
  await nextTick()
  if (termEl.value) {
    const el = termEl.value
    const atBottom = (el.scrollHeight - el.scrollTop - el.clientHeight) < 30
    if (atBottom) el.scrollTop = el.scrollHeight
  }
})

function handleCancel() {
  task.cancel()
}

defineExpose({ task })
</script>

<template>
  <div v-if="task.lines.value.length > 0 || task.status.value === 'running'" class="terminal-wrapper">
    <div ref="termEl" class="terminal active">
      <div
        v-for="(line, i) in task.lines.value"
        :key="i"
        class="line"
        :class="line.level"
      >
        {{ line.msg }}
      </div>
    </div>
    <div v-if="task.status.value === 'running'" class="terminal-controls">
      <button class="btn-abort" @click="handleCancel">Abort</button>
    </div>
  </div>
</template>
