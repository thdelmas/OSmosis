/**
 * Composable for streaming background task output via SSE.
 */
import { ref, readonly } from 'vue'

export function useTask() {
  const lines = ref([])
  const status = ref('idle') // idle | running | done | error | reconnecting
  const taskId = ref(null)
  let eventSource = null
  let reconnectAttempts = 0
  let reconnectTimer = null
  const MAX_RECONNECT = 5

  function connect(id) {
    eventSource = new EventSource(`/api/stream/${id}`)
    eventSource.onmessage = (e) => {
      if (!e.data || e.data === '{}') return
      try {
        const data = JSON.parse(e.data)
        if (data.level === 'done') {
          eventSource.close()
          eventSource = null
          reconnectAttempts = 0
          status.value = data.msg === 'done' ? 'done' : 'error'
          return
        }
        if (data.msg) {
          // Clear reconnect state on successful message
          if (reconnectAttempts > 0) {
            reconnectAttempts = 0
            lines.value.push({ msg: 'Connection restored.', level: 'info' })
          }
          status.value = 'running'
          lines.value.push({ msg: data.msg, level: data.level || 'info' })
        }
      } catch { /* ignore parse errors */ }
    }
    eventSource.onerror = () => {
      eventSource.close()
      eventSource = null
      if (reconnectAttempts < MAX_RECONNECT) {
        reconnectAttempts++
        status.value = 'reconnecting'
        lines.value.push({ msg: `Connection lost. Reconnecting (attempt ${reconnectAttempts}/${MAX_RECONNECT})...`, level: 'warn' })
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts - 1), 10000)
        reconnectTimer = setTimeout(() => connect(id), delay)
      } else {
        lines.value.push({ msg: 'Connection lost after multiple retries. Check your connection and refresh the page.', level: 'error' })
        status.value = 'error'
      }
    }
  }

  function stream(id) {
    taskId.value = id
    status.value = 'running'
    lines.value = []
    reconnectAttempts = 0
    if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null }
    connect(id)
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
    if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null }
    reconnectAttempts = 0
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
