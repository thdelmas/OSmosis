/**
 * Composable for API calls to the Flask backend.
 */
import { ref, readonly } from 'vue'

const BASE = '' // same origin, proxied via Vite dev server

// Shared reactive state for backend connectivity
const backendOnline = ref(true)
let _healthCheckTimer = null

async function _checkHealth() {
  try {
    const res = await fetch(`${BASE}/api/status`, { signal: AbortSignal.timeout(5000) })
    backendOnline.value = res.ok
  } catch {
    backendOnline.value = false
  }
}

function _startHealthPolling() {
  if (_healthCheckTimer) return
  _healthCheckTimer = setInterval(_checkHealth, 8000)
}

function _stopHealthPolling() {
  if (_healthCheckTimer) { clearInterval(_healthCheckTimer); _healthCheckTimer = null }
}

export function useApi() {
  const loading = ref(false)
  const error = ref(null)

  async function api(url, opts = {}) {
    loading.value = true
    error.value = null
    try {
      if (opts.body && typeof opts.body === 'object') {
        opts.headers = { 'Content-Type': 'application/json', ...opts.headers }
        opts.body = JSON.stringify(opts.body)
      }
      const res = await fetch(`${BASE}${url}`, opts)
      const data = await res.json()
      // Backend responded — mark as online, stop polling
      if (!backendOnline.value) {
        backendOnline.value = true
        _stopHealthPolling()
      }
      if (!res.ok) {
        error.value = data.error || `HTTP ${res.status}`
        return { ok: false, data, status: res.status }
      }
      return { ok: true, data, status: res.status }
    } catch (e) {
      error.value = e.message
      backendOnline.value = false
      _startHealthPolling()
      return { ok: false, data: null, status: 0 }
    } finally {
      loading.value = false
    }
  }

  async function get(url) {
    return api(url)
  }

  async function post(url, body) {
    return api(url, { method: 'POST', body })
  }

  function retryConnection() {
    _checkHealth()
  }

  return { api, get, post, loading, error, backendOnline: readonly(backendOnline), retryConnection }
}
