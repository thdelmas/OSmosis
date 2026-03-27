/**
 * Global IPFS PubSub composable — shared singleton state.
 *
 * Connects to /api/ipfs/pubsub/subscribe once and exposes reactive
 * messages + unread count to any component that imports it.
 */
import { ref, readonly, computed } from 'vue'

const messages = ref([])
const unreadCount = ref(0)
const connected = ref(false)
let source = null
let retryTimer = null
const MAX_MESSAGES = 100

function connect() {
  if (source) return
  source = new EventSource('/api/ipfs/pubsub/subscribe')
  connected.value = true

  source.onmessage = (e) => {
    try {
      const msg = JSON.parse(e.data)
      messages.value.unshift(msg)
      if (messages.value.length > MAX_MESSAGES) messages.value.pop()
      unreadCount.value++
    } catch { /* ignore non-JSON */ }
  }

  source.onerror = () => {
    source.close()
    source = null
    connected.value = false
    // Retry after 15s — PubSub is best-effort
    retryTimer = setTimeout(connect, 15000)
  }
}

function disconnect() {
  if (retryTimer) { clearTimeout(retryTimer); retryTimer = null }
  if (source) { source.close(); source = null }
  connected.value = false
}

function clearUnread() {
  unreadCount.value = 0
}

const hasUnread = computed(() => unreadCount.value > 0)

export function usePubsub() {
  return {
    messages: readonly(messages),
    unreadCount: readonly(unreadCount),
    hasUnread,
    connected: readonly(connected),
    connect,
    disconnect,
    clearUnread,
  }
}
