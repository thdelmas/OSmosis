/**
 * Composable for wizard state: selected category, detected device, etc.
 * Shared across all wizard step components.
 * State is automatically persisted to localStorage on every change
 * and restored on page load so refreshes don't lose progress.
 */
import { reactive, ref, computed, watch } from 'vue'

const STORAGE_KEY = 'osmosis-wizard'

const state = reactive({
  category: null, // phone, computer, scooter, etc.
  brand: null,
  model: null,
  serial: null,
  detectedDevice: null,
  selectedOs: null, // chosen OS from the os-pick step
  selectedGoal: null,
  selectedRom: null,
  selectedGapps: null,
  selectedApps: [],    // apps to install after flashing (e.g. F-Droid for Replicant)
  _route: null, // last wizard route path for restore-on-refresh
})

// Sub-phase label shown below the progress bar (not persisted)
const subPhase = ref(null)

// Auto-save to localStorage whenever state changes
let _saveEnabled = false
watch(
  () => ({ ...state }),
  () => {
    if (!_saveEnabled) return
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
    } catch {}
  },
  { deep: true },
)

export function useWizard() {
  function setCategory(cat) {
    state.category = cat
  }

  function setDevice(dev) {
    state.detectedDevice = dev
    // Save to recent devices in localStorage
    if (dev && (dev.id || dev.model || dev.label)) {
      try {
        const key = 'osmosis-recent-devices'
        const recent = JSON.parse(localStorage.getItem(key) || '[]')
        const entry = {
          id: dev.id || '',
          label: dev.label || dev.display_name || dev.model || '',
          model: dev.model || '',
          codename: dev.codename || '',
          brand: dev.brand || '',
          timestamp: Date.now(),
        }
        // Dedupe by id or model
        const deduped = recent.filter(r =>
          (entry.id && r.id !== entry.id) || (!entry.id && r.model !== entry.model)
        )
        deduped.unshift(entry)
        localStorage.setItem(key, JSON.stringify(deduped.slice(0, 10)))
      } catch (_) { /* localStorage unavailable */ }
    }
  }

  function getRecentDevices() {
    try {
      return JSON.parse(localStorage.getItem('osmosis-recent-devices') || '[]')
    } catch (_) { return [] }
  }

  function setGoal(goal) {
    state.selectedGoal = goal
  }

  function setRom(rom) {
    state.selectedRom = rom
  }

  function setOs(os) {
    state.selectedOs = os
  }

  function setHardware({ brand, model, serial }) {
    state.brand = brand || null
    state.model = model || null
    state.serial = serial || null
  }

  function setGapps(gapps) {
    state.selectedGapps = gapps
  }

  function setApps(apps) {
    state.selectedApps = apps || []
  }

  function setSubPhase(label) {
    subPhase.value = label
  }

  function setRoute(path) {
    state._route = path
  }

  function reset() {
    state.category = null
    state.brand = null
    state.model = null
    state.serial = null
    state.detectedDevice = null
    state.selectedOs = null
    state.selectedGoal = null
    state.selectedRom = null
    state.selectedGapps = null
    state.selectedApps = []
    state._route = null
  }

  function save() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
    } catch {}
  }

  /**
   * Peek at saved wizard state without restoring it.
   * Returns { route, deviceLabel } if a saved session exists, null otherwise.
   */
  function peek() {
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}')
      if (!saved._route || !saved._route.startsWith('/wizard/')) return null
      const dev = saved.detectedDevice
      const label = dev
        ? (dev.display_name || dev.friendly_name || dev.label || dev.model || 'Unknown device')
        : null
      return { route: saved._route, deviceLabel: label }
    } catch {
      return null
    }
  }

  /**
   * Restore wizard state from localStorage.
   * Returns the saved route path (if any) so the caller can navigate back.
   */
  function restore() {
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}')
      for (const key of Object.keys(state)) {
        if (saved[key] !== undefined) {
          state[key] = saved[key]
        }
      }
      _saveEnabled = true
      return saved._route || null
    } catch {
      _saveEnabled = true
      return null
    }
  }

  /**
   * Discard saved wizard state and enable saving for a fresh session.
   */
  function discard() {
    try { localStorage.removeItem(STORAGE_KEY) } catch {}
    _saveEnabled = true
  }

  const deviceLabel = computed(() => {
    if (!state.detectedDevice) return ''
    const d = state.detectedDevice
    const match = d.match || {}
    return d.display_name || d.friendly_name || d.label || d.model || match.model || d.codename || match.codename || ''
  })

  return {
    state,
    subPhase,
    setCategory,
    setDevice,
    setGoal,
    setRom,
    setOs,
    setHardware,
    setGapps,
    setApps,
    setSubPhase,
    setRoute,
    reset,
    save,
    peek,
    restore,
    discard,
    deviceLabel,
    getRecentDevices,
  }
}
