/**
 * Composable for API calls to the Flask backend.
 */
import { ref } from 'vue'

const BASE = '' // same origin, proxied via Vite dev server

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
      if (!res.ok) {
        error.value = data.error || `HTTP ${res.status}`
        return { ok: false, data, status: res.status }
      }
      return { ok: true, data, status: res.status }
    } catch (e) {
      error.value = e.message
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

  return { api, get, post, loading, error }
}
