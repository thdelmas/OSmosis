/**
 * Composable for wizard state: selected category, detected device, etc.
 * Shared across all wizard step components.
 */
import { reactive, computed } from 'vue'

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
})

export function useWizard() {
  function setCategory(cat) {
    state.category = cat
  }

  function setDevice(dev) {
    state.detectedDevice = dev
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
  }

  function save() {
    try {
      localStorage.setItem('osmosis-wizard', JSON.stringify(state))
    } catch {}
  }

  function restore() {
    try {
      const saved = JSON.parse(localStorage.getItem('osmosis-wizard') || '{}')
      if (saved.category) state.category = saved.category
      if (saved.detectedDevice) state.detectedDevice = saved.detectedDevice
      if (saved.selectedGoal) state.selectedGoal = saved.selectedGoal
    } catch {}
  }

  const deviceLabel = computed(() => {
    if (!state.detectedDevice) return ''
    return state.detectedDevice.friendly_name || state.detectedDevice.model || 'Unknown device'
  })

  return {
    state,
    setCategory,
    setDevice,
    setGoal,
    setRom,
    setOs,
    setHardware,
    setGapps,
    reset,
    save,
    restore,
    deviceLabel,
  }
}
