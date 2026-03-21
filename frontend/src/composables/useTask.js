/**
 * Composable for streaming background task output via SSE.
 */
import { ref, readonly } from 'vue'

export function useTask() {
  const lines = ref([])
  const status = ref('idle') // idle | running | done | error
  const taskId = ref(null)
  let eventSource = null

  function stream(id) {
    taskId.value = id
    status.value = 'running'
    lines.value = []

    eventSource = new EventSource(`/api/stream/${id}`)
    eventSource.onmessage = (e) => {
      if (!e.data || e.data === '{}') return
      try {
        const data = JSON.parse(e.data)
        if (data.level === 'done') {
          eventSource.close()
          eventSource = null
          status.value = data.msg === 'done' ? 'done' : 'error'
          return
        }
        if (data.msg) {
          lines.value.push({ msg: data.msg, level: data.level || 'info' })
        }
      } catch { /* ignore parse errors */ }
    }
    eventSource.onerror = () => {
      eventSource.close()
      eventSource = null
      lines.value.push({ msg: 'Connection lost.', level: 'error' })
      status.value = 'error'
    }
  }

  async function cancel() {
    if (taskId.value) {
      await fetch(`/api/task/${taskId.value}/cancel`, { method: 'POST' })
    }
  }

  function reset() {
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
    lines.value = []
    status.value = 'idle'
    taskId.value = null
  }

  return {
    lines: readonly(lines),
    status: readonly(status),
    taskId: readonly(taskId),
    stream,
    cancel,
    reset,
  }
}
