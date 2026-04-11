<script setup>
import { ref, watch, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import TerminalOutput from '@/components/shared/TerminalOutput.vue'
import MiAccountManager from '@/components/shared/MiAccountManager.vue'
import EdlEntryFlow from '@/components/shared/EdlEntryFlow.vue'
import DeviceFrame from '@/components/shared/DeviceFrame.vue'
import ScreenDownloadMode from '@/components/shared/device-screens/ScreenDownloadMode.vue'
import ScreenFastboot from '@/components/shared/device-screens/ScreenFastboot.vue'
import ScreenRecovery from '@/components/shared/device-screens/ScreenRecovery.vue'
import ScreenOff from '@/components/shared/device-screens/ScreenOff.vue'
import { useWizard } from '@/composables/useWizard'

const props = defineProps({
  serial: { type: String, required: true },
})

const router = useRouter()
const device = ref(null)
const loading = ref(true)
const availableRoms = ref([])
const flashTaskId = ref(null)
const flashStatus = ref('')  // '' | 'picking' | 'downloading' | 'running' | 'done' | 'error'
const flashMessages = ref([])
const deviceInfo = ref('')
const deviceParsed = ref(null)  // { Device, Version, region_code, region_label, rom_code }
const downloadMessages = ref([])
let pollTimer = null

// LETHE AI pairing
const pairProvider = ref('anthropic')
const pairKey = ref('')
const pairModel = ref('claude-sonnet-4-6')
const pairSending = ref(false)
const pairResult = ref('')

const pairModels = computed(() => {
  if (pairProvider.value === 'anthropic') return [
    { id: 'claude-opus-4-6', label: 'Claude Opus 4.6' },
    { id: 'claude-sonnet-4-6', label: 'Claude Sonnet 4.6' },
    { id: 'claude-haiku-4-5-20251001', label: 'Claude Haiku 4.5' },
  ]
  return [
    { id: 'anthropic/claude-sonnet-4-6', label: 'Claude Sonnet 4.6' },
    { id: 'qwen/qwen3-72b', label: 'Qwen 3 72B' },
    { id: 'google/gemini-2.5-pro', label: 'Gemini 2.5 Pro' },
  ]
})

async function sendPairToDevice() {
  pairSending.value = true
  pairResult.value = ''
  const { ok, data } = await post('/api/lethe/pair', {
    provider: pairProvider.value,
    key: pairKey.value,
    model: pairModel.value,
  })
  pairSending.value = false
  if (ok) {
    pairResult.value = 'Sent to phone. LETHE is ready to talk.'
    pairKey.value = ''
  } else {
    pairResult.value = data?.error || 'Failed to send. Is the phone connected?'
  }
}

// Unlock bootloader state
const unlockStatus = ref('')  // '' | 'form' | 'running' | 'done' | 'error'
const unlockMessages = ref([])
const unlockTaskId = ref(null)
const selectedUnlockAccount = ref(null)
const unlockAbilityStatus = ref(null) // null | 'checking' | object with result

// Fastboot flash state
const fastbootStatus = ref('')  // '' | 'picking' | 'running' | 'done' | 'error'
const fastbootMessages = ref([])
const fastbootTaskId = ref(null)
const fastbootRoms = ref([])

// Active section for mode-aware UI
const activeSection = ref('')  // '' | 'restore' | 'unlock' | 'fastboot' | 'edl' | 'info' | 'os-picker'

// Available OS options for recovery/normal mode
const deviceOsList = ref([])
const osLoading = ref(false)

// Samsung stock restore state
const samsungVersions = ref([])
const samsungLoading = ref(false)
const samsungRestoreTaskId = ref(null)
const samsungRestoreStatus = ref('') // '' | 'picking' | 'downloading' | 'flashing' | 'done' | 'error'
const samsungManualZip = ref('')

// EDL state
const edlReady = ref(false)

// Device profile for wiki link
const deviceProfile = ref(null)

async function fetchDeviceProfile() {
  // Try to match by codename, then by model-based ID
  const codename = (device.value?.codename || '').toLowerCase()
  const model = (device.value?.model || '').toLowerCase().replace(/\s+/g, '-')
  for (const id of [codename, model]) {
    if (!id) continue
    try {
      const res = await fetch(`/api/profiles/${encodeURIComponent(id)}`)
      if (res.ok) {
        deviceProfile.value = await res.json()
        return
      }
    } catch { /* ignore */ }
  }
}

const wikiArticleId = computed(() => {
  if (deviceProfile.value) return `device-${deviceProfile.value.id}`
  return null
})

const modeColors = {
  device: '#4caf50',
  recovery: '#ff9800',
  sideload: '#2196f3',
  fastboot: '#9c27b0',
  download: '#ff9800',
  unauthorized: '#f44336',
  flashing: '#e91e63',
  usb_no_adb: '#999',
}

const modeDescriptions = {
  sideload: 'Device is in MIAssistant sideload mode. You can flash an official recovery ROM to restore stock firmware without unlocking the bootloader.',
  fastboot: 'Device is in fastboot mode. You can flash factory firmware images.',
  recovery: 'Device is in recovery mode. You can sideload updates or wipe data.',
  device: 'Device is connected in normal ADB mode.',
  download: 'Device is in Samsung Download Mode. You can flash firmware via Heimdall.',
  unauthorized: 'Device is connected but not authorized. Check the phone screen and approve the USB debugging prompt.',
  flashing: 'A flash operation is in progress. Do not unplug the USB cable.',
  usb_no_adb: 'Device is connected via USB but is not reachable through ADB, fastboot, or download mode. You can enable USB Debugging, or use the physical button combinations below to enter recovery or flash mode.',
}

const canFlash = computed(() => ['sideload', 'fastboot', 'download'].includes(device.value?.mode))

// Detect when unlock failed because device isn't in fastboot mode
const unlockNeedsFastboot = computed(() => {
  if (unlockStatus.value !== 'error') return false
  const text = unlockMessages.value.map(m => m.msg || '').join(' ').toLowerCase()
  return text.includes('fastboot') && (text.includes('no device') || text.includes('reboot to fastboot'))
})

const isSideload = computed(() => device.value?.mode === 'sideload')
const isFastboot = computed(() => device.value?.mode === 'fastboot')
const isFlashing = computed(() => device.value?.mode === 'flashing')
const isRecovery = computed(() => device.value?.mode === 'recovery')
const isUsbNoAdb = computed(() => device.value?.mode === 'usb_no_adb')

const usbBrand = computed(() => (device.value?.brand || '').toLowerCase())
const isSamsungUsb = computed(() => usbBrand.value.includes('samsung'))
const isSamsungDevice = computed(() => {
  const brand = (device.value?.brand || '').toLowerCase()
  const model = (device.value?.model || '').toUpperCase()
  return brand.includes('samsung') || model.startsWith('GT-') || model.startsWith('SM-')
})

// Cross-flash detection: firmware codename differs from physical model
const isCrossFlashed = computed(() => {
  if (!deviceParsed.value || !device.value) return false
  const firmwareDevice = deviceParsed.value.Device
  const physicalCodename = device.value.codename
  if (!firmwareDevice || !physicalCodename) return false
  // Compare case-insensitively; they should match
  return firmwareDevice.toLowerCase() !== physicalCodename.toLowerCase()
})

const crossFlashInfo = computed(() => {
  if (!isCrossFlashed.value) return null
  return {
    firmware: deviceParsed.value.Device,
    physical: device.value.codename,
  }
})

async function fetchDevice() {
  try {
    const res = await fetch('/api/devices/connected')
    if (!res.ok) return
    const data = await res.json()
    const found = (data.devices || []).find(d => (d.serial || d.mode) === props.serial)
    if (found) {
      device.value = found
      loading.value = false
    } else if (!device.value) {
      // Device disconnected before we ever saw it
      loading.value = false
    }
  } catch { /* ignore */ }
}

async function fetchRoms() {
  try {
    const res = await fetch('/api/miassistant/roms')
    if (res.ok) {
      const data = await res.json()
      availableRoms.value = data.roms || []
    }
  } catch { /* ignore */ }
}

async function fetchDeviceInfo() {
  if (device.value?.mode !== 'sideload') return
  activeSection.value = 'info'
  try {
    const res = await fetch('/api/miassistant/info')
    if (res.ok) {
      const data = await res.json()
      deviceInfo.value = data.output || ''
      deviceParsed.value = {
        ...(data.parsed || {}),
        region_code: data.region_code || '',
        region_label: data.region_label || '',
        rom_code: data.rom_code || '',
      }
    }
  } catch { /* ignore */ }
}

async function fetchRomsForRegion() {
  const region = deviceParsed.value?.region_code || ''
  try {
    // Fetch with region hint but backend returns all ROMs with compatibility flag
    const res = await fetch(`/api/miassistant/roms${region ? `?region=${region}` : ''}`)
    if (res.ok) {
      const data = await res.json()
      availableRoms.value = data.roms || []
    }
  } catch { /* ignore */ }
}

async function fetchFastbootRoms() {
  const codename = device.value?.codename || ''
  try {
    const res = await fetch(`/api/fastboot/roms${codename ? `?codename=${codename}` : ''}`)
    if (res.ok) {
      const data = await res.json()
      fastbootRoms.value = data.roms || []
    }
  } catch { /* ignore */ }
}

async function fetchDeviceOs() {
  // Try to find OS options for this device from devices.cfg
  const model = (device.value?.model || '').toLowerCase().replace(/\s+/g, '-')
  const codename = (device.value?.codename || '').toLowerCase()
  if (!model && !codename) return

  osLoading.value = true
  // Try model-based ID first (matches devices.cfg id format), then codename
  for (const id of [model, codename]) {
    if (!id) continue
    try {
      const res = await fetch(`/api/devices/${encodeURIComponent(id)}/os`)
      if (res.ok) {
        const data = await res.json()
        if (data.os_list?.length) {
          deviceOsList.value = data.os_list
          osLoading.value = false
          return
        }
      }
    } catch { /* ignore */ }
  }
  osLoading.value = false
}

function startOsInstall(os) {
  // Navigate to wizard with device and ROM pre-selected
  const { setDevice, setRom } = useWizard()
  const d = device.value
  setDevice({
    id: (d.model || '').toLowerCase().replace(/\s+/g, '-'),
    label: d.display_name || d.model || '',
    model: d.model || '',
    codename: d.codename || '',
    brand: d.brand || '',
    serial: d.serial || '',
  })
  if (os.type === 'rom') {
    setRom(os)
  }
  router.push('/wizard/install')
}

async function startSamsungRestore() {
  activeSection.value = 'samsung-restore'
  samsungRestoreStatus.value = 'picking'
  samsungLoading.value = true
  samsungVersions.value = []

  const model = device.value?.model || ''
  if (!model) {
    samsungLoading.value = false
    return
  }

  try {
    const res = await fetch(`/api/samsung/stock/${encodeURIComponent(model)}`)
    if (res.ok) {
      const data = await res.json()
      samsungVersions.value = data.versions || []
    }
  } catch { /* ignore */ }
  samsungLoading.value = false
}

async function flashSamsungStock(firmware) {
  samsungRestoreStatus.value = 'flashing'
  samsungRestoreTaskId.value = null

  const body = {
    model: device.value?.model || '',
    region: firmware?.region || '',
    version: firmware?.version || '',
  }

  try {
    const res = await fetch('/api/flash/stock-auto', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    const data = await res.json()
    if (data.task_id) {
      samsungRestoreTaskId.value = data.task_id
    } else {
      samsungRestoreStatus.value = 'error'
    }
  } catch {
    samsungRestoreStatus.value = 'error'
  }
}

async function flashSamsungManual() {
  const zipPath = samsungManualZip.value.trim()
  if (!zipPath) return

  samsungRestoreStatus.value = 'flashing'
  samsungRestoreTaskId.value = null

  try {
    const res = await fetch('/api/flash/stock-auto', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ fw_zip: zipPath, model: device.value?.model || '' }),
    })
    const data = await res.json()
    if (data.task_id) {
      samsungRestoreTaskId.value = data.task_id
    } else {
      samsungRestoreStatus.value = 'error'
    }
  } catch {
    samsungRestoreStatus.value = 'error'
  }
}

// Known recovery ROM versions per region for renoir
const knownVersionsByRegion = {
  MI: [
    { version: 'V14.0.7.0.TKIMIXM', filename: 'miui_RENOIRGlobal_V14.0.7.0.TKIMIXM_cac144253c_13.0.zip', android: '13.0' },
    { version: 'V14.0.6.0.TKIMIXM', filename: 'miui_RENOIRGlobal_V14.0.6.0.TKIMIXM_d2e3f4a5b6_13.0.zip', android: '13.0' },
  ],
  EU: [
    { version: 'V14.0.9.0.TKIEUXM', filename: 'miui_RENOIREEAGlobal_V14.0.9.0.TKIEUXM_59de628db6_13.0.zip', android: '13.0' },
    { version: 'V14.0.8.0.TKIEUXM', filename: 'miui_RENOIREEAGlobal_V14.0.8.0.TKIEUXM_c39c64055a_13.0.zip', android: '13.0' },
  ],
}

const knownVersions = computed(() => {
  const region = deviceParsed.value?.region_code || 'MI'
  return knownVersionsByRegion[region] || knownVersionsByRegion['MI'] || []
})

const mergedRoms = computed(() => {
  const downloaded = new Set(availableRoms.value.map(r => r.version))
  const result = []
  for (const rom of availableRoms.value) {
    result.push({ ...rom, downloaded: true })
  }
  for (const kv of knownVersions.value) {
    if (!downloaded.has(kv.version)) {
      result.push({ version: kv.version, filename: kv.filename, android: kv.android, downloaded: false, size_mb: 0 })
    }
  }
  return result
})

async function startFlash() {
  activeSection.value = 'restore'
  flashStatus.value = 'picking'
  if (device.value?.mode === 'sideload') {
    if (!deviceParsed.value) await fetchDeviceInfo()
    fetchRomsForRegion()
  }
}

async function downloadRom(rom) {
  flashStatus.value = 'downloading'
  downloadMessages.value = []

  try {
    const res = await fetch('/api/miassistant/download', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ version: rom.version, filename: rom.filename }),
    })
    const data = await res.json()

    if (data.status === 'exists') {
      // Already downloaded
      downloadMessages.value.push({ level: 'success', msg: `Already downloaded (${data.size_mb} MB)` })
      await fetchRoms()
      flashStatus.value = 'picking'
      return
    }

    if (data.task_id) {
      streamDownload(data.task_id)
    } else {
      downloadMessages.value.push({ level: 'error', msg: data.error || 'Failed to start download' })
      flashStatus.value = 'picking'
    }
  } catch (e) {
    downloadMessages.value.push({ level: 'error', msg: e.message })
    flashStatus.value = 'picking'
  }
}

function streamDownload(taskId) {
  const evtSource = new EventSource(`/api/stream/${taskId}`)
  evtSource.onmessage = (e) => {
    if (!e.data || e.data === '{}') return
    try {
      const msg = JSON.parse(e.data)
      if (msg.level === 'done') {
        evtSource.close()
        fetchRoms()
        flashStatus.value = 'picking'
        return
      }
      if (msg.msg) downloadMessages.value.push(msg)
    } catch { /* ignore */ }
  }
  evtSource.onerror = () => {
    evtSource.close()
    flashStatus.value = 'picking'
  }
}

async function flashRom(rom) {
  flashStatus.value = 'running'
  flashMessages.value = []

  const endpoint = device.value.mode === 'sideload'
    ? '/api/miassistant/sideload'
    : '/api/fastboot/flash-stock'

  const body = device.value.mode === 'sideload'
    ? { zip_path: rom.path, codename: device.value.codename || 'unknown' }
    : { flash_dir: rom.path, codename: device.value.codename || 'unknown' }

  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    const data = await res.json()
    if (data.task_id) {
      flashTaskId.value = data.task_id
      streamTask(data.task_id, flashMessages, (s) => { flashStatus.value = s })
    } else {
      flashStatus.value = 'error'
      flashMessages.value = [{ level: 'error', msg: data.error || 'Failed to start flash' }]
    }
  } catch (e) {
    flashStatus.value = 'error'
    flashMessages.value = [{ level: 'error', msg: e.message }]
  }
}

// Fastboot flash
async function startFastbootFlash() {
  activeSection.value = 'fastboot'
  fastbootStatus.value = 'picking'
  await fetchFastbootRoms()
}

async function flashFastbootRom(rom) {
  fastbootStatus.value = 'running'
  fastbootMessages.value = []

  try {
    const res = await fetch('/api/fastboot/flash-stock', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ flash_dir: rom.path, codename: device.value.codename || 'unknown' }),
    })
    const data = await res.json()
    if (data.task_id) {
      fastbootTaskId.value = data.task_id
      streamTask(data.task_id, fastbootMessages, (s) => { fastbootStatus.value = s })
    } else {
      fastbootStatus.value = 'error'
      fastbootMessages.value = [{ level: 'error', msg: data.error || 'Failed to start flash' }]
    }
  } catch (e) {
    fastbootStatus.value = 'error'
    fastbootMessages.value = [{ level: 'error', msg: e.message }]
  }
}

// Bootloader unlock
async function startUnlock() {
  activeSection.value = 'unlock'
  unlockStatus.value = 'form'
  unlockMessages.value = []
  unlockAbilityStatus.value = 'checking'

  try {
    const res = await fetch('/api/miassistant/unlock-ability')
    if (res.ok) {
      const data = await res.json()
      unlockAbilityStatus.value = data
    } else {
      unlockAbilityStatus.value = { error: 'Could not check unlock ability' }
    }
  } catch {
    unlockAbilityStatus.value = { error: 'Could not reach backend' }
  }
}

function onUnlockAccountSelect(account) {
  selectedUnlockAccount.value = account
}

function onUnlockSessionReady(account) {
  selectedUnlockAccount.value = account
}

async function submitUnlock() {
  if (!selectedUnlockAccount.value?.id) return
  unlockStatus.value = 'running'
  unlockMessages.value = []

  try {
    const res = await fetch('/api/miassistant/unlock', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        account_id: selectedUnlockAccount.value.id,
      }),
    })
    const data = await res.json()
    if (data.task_id) {
      unlockTaskId.value = data.task_id
      streamTask(data.task_id, unlockMessages, (s) => { unlockStatus.value = s })
    } else {
      unlockStatus.value = 'error'
      unlockMessages.value = [{ level: 'error', msg: data.error || 'Failed to start unlock' }]
    }
  } catch (e) {
    unlockStatus.value = 'error'
    unlockMessages.value = [{ level: 'error', msg: e.message }]
  }
}

// Generic task streamer reused for flash, unlock, fastboot
function streamTask(taskId, messagesRef, setStatus) {
  const evtSource = new EventSource(`/api/stream/${taskId}`)
  evtSource.onmessage = (e) => {
    if (!e.data || e.data === '{}') return
    try {
      const msg = JSON.parse(e.data)
      if (msg.level === 'done') {
        setStatus(msg.msg === 'ok' ? 'done' : 'error')
        evtSource.close()
        return
      }
      if (msg.msg !== undefined) {
        messagesRef.value.push(msg)
      }
    } catch { /* ignore */ }
  }
  evtSource.onerror = () => {
    evtSource.close()
    setStatus('error')
  }
}

function retry() {
  flashStatus.value = ''
  flashMessages.value = []
  flashTaskId.value = null
  fastbootStatus.value = ''
  fastbootMessages.value = []
  fastbootTaskId.value = null
  unlockStatus.value = ''
  unlockMessages.value = []
  unlockTaskId.value = null
  selectedUnlockAccount.value = null
  activeSection.value = ''
  rebootStatus.value = ''
  pendingAfterFastboot.value = ''
  waitingForFastboot.value = false
}

function backToActions() {
  activeSection.value = ''
  flashStatus.value = ''
  fastbootStatus.value = ''
  unlockStatus.value = ''
  selectedUnlockAccount.value = null
  rebootStatus.value = ''
  pendingAfterFastboot.value = ''
  waitingForFastboot.value = false
}

// Reboot — works from fastboot or ADB (sideload/recovery/device)
const rebootStatus = ref('')  // '' | 'rebooting' | 'done' | 'error'
const rebootTarget = ref('')
const rebootError = ref('')

async function rebootDevice(target) {
  rebootStatus.value = 'rebooting'
  rebootTarget.value = target
  rebootError.value = ''

  const mode = device.value?.mode

  // Pick the right endpoint based on current device mode
  let endpoint
  if (mode === 'download') {
    endpoint = '/api/reboot-from-download'
  } else if (mode === 'fastboot') {
    endpoint = '/api/fastboot/reboot'
  } else {
    endpoint = '/api/adb/reboot'
  }

  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target }),
    })
    const data = await res.json()
    if (data.ok) {
      rebootStatus.value = 'done'
    } else {
      rebootStatus.value = 'error'
      rebootError.value = data.message || data.error || 'Reboot command failed.'
    }
  } catch (e) {
    rebootStatus.value = 'error'
    rebootError.value = e.message
  }
}

// Keep backward compat alias
function fastbootReboot(target) { rebootDevice(target) }

// Pending action after reboot to fastboot
const pendingAfterFastboot = ref('')  // '' | 'unlock' | 'edl'
const waitingForFastboot = ref(false)

async function rebootToFastbootAndUnlock() {
  pendingAfterFastboot.value = 'unlock'
  waitingForFastboot.value = true
  unlockStatus.value = ''
  unlockMessages.value = []
  unlockAbilityStatus.value = null
  await rebootDevice('bootloader')
}

async function rebootToFastbootAndEdl() {
  pendingAfterFastboot.value = 'edl'
  waitingForFastboot.value = true
  await rebootDevice('bootloader')
}

// Watch for device mode change — resume pending actions & clear stale state
watch(() => device.value?.mode, (newMode, oldMode) => {
  if (!newMode || !oldMode || newMode === oldMode) return

  // Clear reboot banner once the device has actually changed mode
  if (rebootStatus.value) {
    rebootStatus.value = ''
  }

  // Resume pending action after fastboot reboot
  if (newMode === 'fastboot' && waitingForFastboot.value) {
    waitingForFastboot.value = false
    const pending = pendingAfterFastboot.value
    pendingAfterFastboot.value = ''
    if (pending === 'unlock') {
      startUnlock()
    } else if (pending === 'edl') {
      activeSection.value = 'edl'
    }
    return
  }

})

// Fetch OS options when device is detected in recovery or normal mode
watch(() => device.value?.mode, (mode) => {
  if ((mode === 'recovery' || mode === 'device') && !deviceOsList.value.length) {
    fetchDeviceOs()
  }
})

// Fetch device profile for wiki link when device info becomes available
watch(() => device.value?.codename || device.value?.model, (val) => {
  if (val && !deviceProfile.value) fetchDeviceProfile()
}, { immediate: true })

onMounted(() => {
  fetchDevice()
  pollTimer = setInterval(fetchDevice, 3000)
})
onUnmounted(() => clearInterval(pollTimer))
</script>

<template>
  <div class="connected-page">
    <button class="btn btn-link back-link" @click="router.push('/')">&larr; Back</button>

    <div v-if="loading" class="connected-loading">
      <span class="spinner-small"></span> Waiting for device...
    </div>

    <div v-else-if="!device" class="connected-disconnected">
      <div class="disconnect-icon">&#x26A0;</div>
      <h2>Device disconnected</h2>
      <p>The device with serial <code>{{ serial }}</code> is no longer connected.</p>
      <button class="btn btn-primary" @click="router.push('/')">Back to home</button>
    </div>

    <template v-else>
      <!-- Pokédex shell -->
      <div class="dex-shell">
        <!-- Top bar with indicator lights -->
        <div class="dex-top-bar">
          <div class="dex-lens" :style="{ '--lens-color': modeColors[device.mode] || '#888' }">
            <div class="dex-lens-inner"></div>
          </div>
          <div class="dex-indicators">
            <span class="dex-led dex-led-red"></span>
            <span class="dex-led dex-led-yellow"></span>
            <span class="dex-led dex-led-green" :class="{ 'dex-led-active': device.mode === 'device' || device.mode === 'recovery' || device.mode === 'sideload' || device.mode === 'fastboot' || device.mode === 'download' }"></span>
          </div>
          <div class="dex-entry-number" v-if="device.serial">
            No. {{ device.serial.slice(-6).toUpperCase() }}
          </div>
        </div>

        <!-- Main viewport row -->
        <div class="dex-viewport-row">
          <!-- Device frame -->
          <div class="dex-device-frame">
            <DeviceFrame>
              <ScreenDownloadMode v-if="device.mode === 'download'" />
              <ScreenFastboot v-else-if="device.mode === 'fastboot'" :codename="device.codename || device.product || ''" :unlocked="device.unlocked === true" />
              <ScreenRecovery v-else-if="device.mode === 'recovery'" />
              <ScreenRecovery v-else-if="device.mode === 'sideload'" :selected="3" />
              <ScreenOff v-else-if="device.mode === 'usb_no_adb' || device.mode === 'unauthorized'" />
              <div v-else class="screen-connected">
                <div class="screen-connected-dot"></div>
                <div class="screen-connected-label">Connected</div>
              </div>
            </DeviceFrame>
          </div>

          <!-- Stats panel -->
          <div class="dex-stats">
            <div class="dex-name-row">
              <h1 class="dex-device-name">{{ device.display_name || device.serial }}</h1>
              <span
                class="dex-type-badge"
                :style="{ background: modeColors[device.mode] || '#888', color: '#fff' }"
              >
                {{ { usb_no_adb: 'USB ONLY', download: 'DOWNLOAD', fastboot: 'FASTBOOT', recovery: 'RECOVERY', sideload: 'SIDELOAD', device: 'CONNECTED', unauthorized: 'UNAUTHORIZED', flashing: 'FLASHING' }[device.mode] || device.mode.toUpperCase() }}
              </span>
            </div>

            <div class="dex-stat-grid">
              <div v-if="device.brand" class="dex-stat">
                <span class="dex-stat-label">Brand</span>
                <span class="dex-stat-value">{{ device.brand }}</span>
                <div class="dex-stat-bar">
                  <div class="dex-stat-bar-fill" style="width: 100%"></div>
                </div>
              </div>
              <div class="dex-stat">
                <span class="dex-stat-label">Model</span>
                <span class="dex-stat-value">{{ device.model || device.product || device.display_name || 'Unknown' }}</span>
                <div class="dex-stat-bar">
                  <div class="dex-stat-bar-fill" style="width: 85%"></div>
                </div>
              </div>
              <div v-if="device.codename" class="dex-stat">
                <span class="dex-stat-label">Codename</span>
                <span class="dex-stat-value mono">{{ device.codename }}</span>
                <div class="dex-stat-bar">
                  <div class="dex-stat-bar-fill" style="width: 70%"></div>
                </div>
              </div>
              <div v-if="device.serial" class="dex-stat">
                <span class="dex-stat-label">Serial</span>
                <span class="dex-stat-value mono">{{ device.serial }}</span>
                <div class="dex-stat-bar">
                  <div class="dex-stat-bar-fill" style="width: 60%"></div>
                </div>
              </div>
              <div v-if="device.imei" class="dex-stat">
                <span class="dex-stat-label">IMEI</span>
                <span class="dex-stat-value mono">{{ device.imei }}</span>
                <div class="dex-stat-bar">
                  <div class="dex-stat-bar-fill" style="width: 55%"></div>
                </div>
              </div>
              <div v-if="device.lethe" class="dex-stat">
                <span class="dex-stat-label">LETHE</span>
                <span class="dex-stat-value">v{{ device.lethe.version }}</span>
                <div class="dex-stat-bar">
                  <div class="dex-stat-bar-fill" style="width: 100%; background: #22e8a0"></div>
                </div>
              </div>
              <div v-if="device.lethe" class="dex-stat">
                <span class="dex-stat-label">Privacy</span>
                <span class="dex-stat-value">
                  {{ device.lethe.tor === 'true' ? 'Tor' : '' }}{{ device.lethe.tor === 'true' && device.lethe.burner_mode === 'true' ? ' · ' : '' }}{{ device.lethe.burner_mode === 'true' ? 'Burner' : '' }}{{ device.lethe.deadman === 'true' ? ' · DMS' : '' }}
                </span>
                <div class="dex-stat-bar">
                  <div class="dex-stat-bar-fill" style="width: 90%; background: #22e8a0"></div>
                </div>
              </div>
              <div v-if="device.mode !== 'download' && device.mode !== 'usb_no_adb'" class="dex-stat">
                <span class="dex-stat-label">Firmware</span>
                <span class="dex-stat-value">{{ deviceParsed?.Version || deviceParsed?.Device || device.codename || device.product || '—' }}</span>
                <div class="dex-stat-bar">
                  <div class="dex-stat-bar-fill" style="width: 75%"></div>
                </div>
              </div>
              <div class="dex-stat">
                <span class="dex-stat-label">Bootloader</span>
                <span class="dex-stat-value">
                  <span v-if="device.unlocked === true" class="unlocked-text">Unlocked</span>
                  <span v-else-if="device.unlocked === false" class="locked-text">Locked</span>
                  <span v-else-if="device.mode === 'download' || device.mode === 'usb_no_adb'" class="text-dim">N/A</span>
                  <span v-else>{{ device.mode }}</span>
                </span>
                <div class="dex-stat-bar">
                  <div class="dex-stat-bar-fill" :style="{ width: device.unlocked === true ? '100%' : '30%' }"></div>
                </div>
              </div>
            </div>

            <p class="dex-desc">{{ modeDescriptions[device.mode] || '' }}</p>
            <router-link
              v-if="wikiArticleId"
              :to="{ path: '/wiki', query: { article: wikiArticleId } }"
              class="dex-wiki-link"
            >
              View device wiki page &rarr;
            </router-link>
          </div>
        </div>

        <!-- Bottom ridge / hinge detail -->
        <div class="dex-hinge"></div>
      </div>

      <!-- LETHE AI Provider Setup -->
      <div v-if="device && device.lethe" class="lethe-pair-section">
        <h3 class="section-title" style="color: #22e8a0">Set up LETHE AI</h3>
        <p class="text-dim" style="margin-bottom: 0.8rem; font-size: 0.85em">
          Enter an API key here and it will be sent to your phone over USB. No typing on the phone needed.
        </p>
        <div class="form-group" style="margin-bottom: 0.5rem">
          <label class="form-label">Provider</label>
          <select v-model="pairProvider" class="form-input">
            <option value="anthropic">Anthropic (Claude)</option>
            <option value="openrouter">OpenRouter (many models)</option>
          </select>
        </div>
        <div class="form-group" style="margin-bottom: 0.5rem">
          <label class="form-label">API Key</label>
          <input v-model="pairKey" type="password" class="form-input"
                 :placeholder="pairProvider === 'anthropic' ? 'sk-ant-...' : 'sk-or-...'" />
        </div>
        <div class="form-group" style="margin-bottom: 0.8rem">
          <label class="form-label">Model</label>
          <select v-model="pairModel" class="form-input">
            <option v-for="m in pairModels" :key="m.id" :value="m.id">{{ m.label }}</option>
          </select>
        </div>
        <button class="btn btn-primary" :disabled="!pairKey || pairSending" @click="sendPairToDevice"
                style="width: 100%">
          {{ pairSending ? 'Sending...' : 'Send to phone' }}
        </button>
        <div v-if="pairResult" class="info-box info-box--success" style="margin-top: 0.5rem">
          {{ pairResult }}
        </div>
      </div>

      <!-- Flashing-in-progress banner -->
      <div v-if="isFlashing" class="banner banner-flashing">
        <strong>Flash in progress</strong> &mdash; the USB connection is locked. Do not unplug the cable or interact with the device until the operation completes.
      </div>

      <!-- Waiting for fastboot reboot -->
      <div v-if="waitingForFastboot" class="banner banner-info">
        <span class="spinner-small"></span>
        <strong>Rebooting to fastboot...</strong> waiting for the device to reconnect. The unlock flow will continue automatically.
      </div>

      <!-- Cross-flash warning -->
      <div v-if="isCrossFlashed" class="banner banner-crossflash">
        <div class="banner-title">Firmware/hardware mismatch detected</div>
        <p>
          This device's firmware reports codename <strong>{{ crossFlashInfo.firmware }}</strong>,
          but the physical hardware is <strong>{{ crossFlashInfo.physical }}</strong>.
          The device appears to have been cross-flashed with firmware meant for a different model.
        </p>
        <p>
          MIAssistant sideload will not work in this case &mdash; the recovery ROM will be rejected
          because the firmware codename does not match the hardware.
          You need to <strong>unlock the bootloader</strong> and then flash the correct firmware via fastboot.
        </p>
      </div>

      <!-- Device info (MIAssistant parsed) -->
      <div v-if="deviceParsed" class="dex-detail-section">
        <h2 class="dex-section-title">Device info</h2>
        <div class="device-info-grid">
          <div v-if="deviceParsed.Device" class="info-item">
            <span class="info-label">Device</span>
            <span class="info-value">{{ deviceParsed.Device }}</span>
          </div>
          <div v-if="deviceParsed.Version" class="info-item">
            <span class="info-label">Version</span>
            <span class="info-value">{{ deviceParsed.Version }}</span>
          </div>
          <div v-if="deviceParsed.Serial" class="info-item">
            <span class="info-label">Serial</span>
            <span class="info-value mono">{{ deviceParsed.Serial }}</span>
          </div>
          <div v-if="deviceParsed.region_label" class="info-item">
            <span class="info-label">Region</span>
            <span class="info-value">{{ deviceParsed.region_label }} <span class="text-dim">({{ deviceParsed.region_code }})</span></span>
          </div>
          <div v-if="deviceParsed.rom_code" class="info-item">
            <span class="info-label">ROM zone</span>
            <span class="info-value mono">{{ deviceParsed.rom_code }}</span>
          </div>
        </div>
        <!-- Raw output toggle -->
        <details class="raw-info-details">
          <summary class="raw-info-summary">Show raw output</summary>
          <pre class="device-info-pre">{{ deviceInfo }}</pre>
        </details>
      </div>

      <!-- Actions -->
      <div class="dex-actions-section">
        <h2 class="dex-section-title">Actions</h2>

        <!-- Idle state: show action buttons based on device mode -->
        <!-- Keep action grid visible when samsung-restore or os-picker is open (they show below) -->
        <div v-if="!activeSection || activeSection === 'samsung-restore' || activeSection === 'os-picker'" class="action-grid">

          <!-- Sideload mode actions -->
          <template v-if="isSideload">
            <button class="action-card action-primary" @click="startFlash">
              <div class="action-icon">&#x1F4E6;</div>
              <div class="action-label">Restore stock firmware</div>
              <div class="action-desc">Flash an official ROM to fix boot loops or restore factory state</div>
            </button>
            <button class="action-card" @click="fetchDeviceInfo">
              <div class="action-icon">&#x1F50D;</div>
              <div class="action-label">Read device info</div>
              <div class="action-desc">Query device details via MIAssistant protocol</div>
            </button>
            <button class="action-card" @click="startUnlock">
              <div class="action-icon">&#x1F513;</div>
              <div class="action-label">Unlock bootloader</div>
              <div class="action-desc">Required for cross-flashed devices or custom ROM installation</div>
            </button>
            <button class="action-card" @click="rebootDevice('bootloader')">
              <div class="action-icon">&#x26A1;</div>
              <div class="action-label">Reboot to fastboot</div>
              <div class="action-desc">Switch to fastboot mode for low-level firmware flashing</div>
            </button>
            <button class="action-card" @click="rebootDevice('recovery')">
              <div class="action-icon">&#x1F504;</div>
              <div class="action-label">Reboot to recovery</div>
              <div class="action-desc">Enter recovery mode for OTA updates, wipe, or safe mode</div>
            </button>
            <button class="action-card" @click="rebootDevice('system')">
              <div class="action-icon">&#x1F4F1;</div>
              <div class="action-label">Reboot to system</div>
              <div class="action-desc">Boot normally into the OS</div>
            </button>
            <button class="action-card" @click="activeSection = 'edl'">
              <div class="action-icon">&#x26A0;</div>
              <div class="action-label">Enter EDL mode</div>
              <div class="action-desc">Emergency Download mode for deep recovery with EDL cable</div>
            </button>
          </template>

          <!-- Fastboot mode actions -->
          <template v-if="isFastboot">
            <button class="action-card action-primary" @click="startFastbootFlash">
              <div class="action-icon">&#x26A1;</div>
              <div class="action-label">Flash via fastboot</div>
              <div class="action-desc">Flash factory firmware images to restore stock state</div>
            </button>
            <button v-if="device.unlocked === false" class="action-card" @click="startUnlock">
              <div class="action-icon">&#x1F513;</div>
              <div class="action-label">Unlock bootloader</div>
              <div class="action-desc">Unlock before flashing custom or cross-region firmware</div>
            </button>
            <button class="action-card" @click="rebootDevice('recovery')">
              <div class="action-icon">&#x1F504;</div>
              <div class="action-label">Reboot to recovery</div>
              <div class="action-desc">Enter MIUI Recovery 5.0 for OTA updates, wipe, or safe mode</div>
            </button>
            <button class="action-card" @click="rebootDevice('system')">
              <div class="action-icon">&#x1F4F1;</div>
              <div class="action-label">Reboot to system</div>
              <div class="action-desc">Boot normally into the OS</div>
            </button>
            <button class="action-card" @click="activeSection = 'edl'">
              <div class="action-icon">&#x26A0;</div>
              <div class="action-label">Enter EDL mode</div>
              <div class="action-desc">Emergency Download mode for deep recovery with EDL cable</div>
            </button>
          </template>

          <!-- Recovery mode actions -->
          <template v-if="isRecovery">
            <button v-if="deviceOsList.filter(o => o.type === 'rom').length" class="action-card action-primary" @click="activeSection = 'os-picker'">
              <div class="action-icon">&#x1F4BE;</div>
              <div class="action-label">Install an OS</div>
              <div class="action-desc">Choose from available operating systems for this device</div>
            </button>
            <button class="action-card" :class="{ 'action-primary': !deviceOsList.filter(o => o.type === 'rom').length && !isSamsungDevice }" @click="router.push('/sideload')">
              <div class="action-icon">&#x1F4E4;</div>
              <div class="action-label">Sideload a file</div>
              <div class="action-desc">Send a ZIP (ROM, update, mod) to the device via ADB sideload</div>
            </button>
            <button v-if="isSamsungDevice" class="action-card" :class="{ 'action-primary': !deviceOsList.filter(o => o.type === 'rom').length }" @click="startSamsungRestore">
              <div class="action-icon">&#x1F4E6;</div>
              <div class="action-label">Restore stock firmware</div>
              <div class="action-desc">Download and flash official Samsung firmware via Heimdall</div>
            </button>
            <button class="action-card" @click="rebootDevice('bootloader')">
              <div class="action-icon">&#x26A1;</div>
              <div class="action-label">Reboot to fastboot</div>
              <div class="action-desc">Switch to fastboot mode for firmware flashing or bootloader unlock</div>
            </button>
            <button v-if="isSamsungDevice" class="action-card" @click="rebootDevice('download')">
              <div class="action-icon">&#x1F4E5;</div>
              <div class="action-label">Reboot to download</div>
              <div class="action-desc">Enter Samsung Download Mode for Heimdall flashing</div>
            </button>
            <button class="action-card" @click="rebootDevice('system')">
              <div class="action-icon">&#x1F4F1;</div>
              <div class="action-label">Reboot to system</div>
              <div class="action-desc">Boot normally into the OS</div>
            </button>
          </template>

          <!-- Normal ADB mode actions -->
          <template v-if="device?.mode === 'device'">
            <button class="action-card" @click="rebootDevice('bootloader')">
              <div class="action-icon">&#x26A1;</div>
              <div class="action-label">Reboot to fastboot</div>
              <div class="action-desc">Switch to fastboot mode for firmware flashing or bootloader unlock</div>
            </button>
            <button class="action-card" @click="rebootDevice('recovery')">
              <div class="action-icon">&#x1F504;</div>
              <div class="action-label">Reboot to recovery</div>
              <div class="action-desc">Enter recovery mode for OTA updates, wipe, or safe mode</div>
            </button>
            <button class="action-card" @click="rebootDevice('download')">
              <div class="action-icon">&#x1F4E5;</div>
              <div class="action-label">Reboot to download</div>
              <div class="action-desc">Enter Samsung Download Mode (Odin/Heimdall)</div>
            </button>
          </template>

          <!-- Flashing mode: no actions available -->
          <div v-if="isFlashing" class="action-locked-notice">
            No actions available while a flash operation is in progress.
          </div>

          <!-- Download mode actions -->
          <template v-if="device.mode === 'download'">
            <button class="action-card action-primary" @click="startFlash">
              <div class="action-icon">&#x1F4E6;</div>
              <div class="action-label">Restore stock firmware</div>
              <div class="action-desc">Flash an official ROM via Heimdall to fix boot loops or restore factory state</div>
            </button>
            <button class="action-card" @click="rebootDevice('system')">
              <div class="action-icon">&#x1F4F1;</div>
              <div class="action-label">Reboot to system</div>
              <div class="action-desc">Exit Download Mode and boot normally into the OS</div>
            </button>
            <details class="action-card usb-guide-card">
              <summary class="action-summary">
                <span class="action-icon">&#x1F504;</span>
                <span>
                  <span class="action-label">Enter Recovery Mode (manual)</span>
                  <span class="action-desc">Use physical button combos if software reboot doesn't work</span>
                </span>
              </summary>
              <ol class="usb-guide-steps">
                <li><strong>Unplug</strong> the USB cable</li>
                <li>Hold <strong>Power for 10+ seconds</strong> until the screen goes black</li>
                <li>Immediately hold <strong>Volume Up + Home + Power</strong> (or <strong>Volume Up + Bixby + Power</strong> on newer models)</li>
                <li>Release all buttons when the Samsung logo appears</li>
                <li>Wait for the recovery menu, then plug USB back in</li>
              </ol>
            </details>
          </template>

          <!-- USB-only (no ADB) — guide user to enable debugging or enter flash mode -->
          <template v-if="isUsbNoAdb">
            <details class="action-card action-primary usb-guide-card" open>
              <summary class="action-summary">
                <span class="action-icon">&#x1F4F1;</span>
                <span>
                  <span class="action-label">Enable USB Debugging</span>
                  <span class="action-desc">Turn on developer access so OSmosis can communicate with your device</span>
                </span>
              </summary>
              <ol class="usb-guide-steps">
                <li>On your device, open <strong>Settings</strong></li>
                <li>Go to <strong>About Phone</strong> (or <strong>Software Information</strong>)</li>
                <li>Tap <strong>Build Number</strong> 7 times until you see "You are now a developer"</li>
                <li>Go back to <strong>Settings &gt; Developer Options</strong></li>
                <li>Turn on <strong>USB Debugging</strong></li>
                <li>If prompted on screen, tap <strong>Allow</strong></li>
              </ol>
              <p class="usb-guide-note">The device will appear as connected once debugging is enabled.</p>
            </details>

            <details v-if="isSamsungUsb" class="action-card usb-guide-card">
              <summary class="action-summary">
                <span class="action-icon">&#x1F4E5;</span>
                <span>
                  <span class="action-label">Enter Download Mode</span>
                  <span class="action-desc">For Heimdall/Odin firmware flashing via physical buttons</span>
                </span>
              </summary>
              <ol class="usb-guide-steps">
                <li><strong>Power off</strong> the device completely</li>
                <li><strong>Unplug</strong> the USB cable</li>
                <li>Hold <strong>Volume Down + Home + Power</strong> simultaneously (or <strong>Volume Down + Bixby + Power</strong> on newer models)</li>
                <li>When you see a warning screen, press <strong>Volume Up</strong> to confirm</li>
                <li>Plug the USB cable back in</li>
              </ol>
            </details>

            <details v-if="isSamsungUsb" class="action-card usb-guide-card">
              <summary class="action-summary">
                <span class="action-icon">&#x1F504;</span>
                <span>
                  <span class="action-label">Enter Recovery Mode</span>
                  <span class="action-desc">For sideloading updates, factory reset, or safe mode</span>
                </span>
              </summary>
              <ol class="usb-guide-steps">
                <li><strong>Power off</strong> the device completely</li>
                <li>Hold <strong>Volume Up + Home + Power</strong> simultaneously (or <strong>Volume Up + Bixby + Power</strong> on newer models)</li>
                <li>Release all buttons when the Samsung logo appears</li>
                <li>Wait for the recovery menu to load</li>
              </ol>
            </details>

            <details v-if="!isSamsungUsb" class="action-card usb-guide-card">
              <summary class="action-summary">
                <span class="action-icon">&#x26A1;</span>
                <span>
                  <span class="action-label">Enter Fastboot Mode</span>
                  <span class="action-desc">For firmware flashing or bootloader unlock via physical buttons</span>
                </span>
              </summary>
              <ol class="usb-guide-steps">
                <li><strong>Power off</strong> the device completely</li>
                <li><strong>Unplug</strong> the USB cable</li>
                <li>Hold <strong>Volume Down + Power</strong> until the fastboot screen appears</li>
                <li>Plug the USB cable back in</li>
              </ol>
            </details>

            <details v-if="!isSamsungUsb" class="action-card usb-guide-card">
              <summary class="action-summary">
                <span class="action-icon">&#x1F504;</span>
                <span>
                  <span class="action-label">Enter Recovery Mode</span>
                  <span class="action-desc">For sideloading updates, factory reset, or safe mode</span>
                </span>
              </summary>
              <ol class="usb-guide-steps">
                <li><strong>Power off</strong> the device completely</li>
                <li>Hold <strong>Volume Up + Power</strong> until the device vibrates or the logo appears</li>
                <li>Release Power but keep holding Volume Up until the recovery menu loads</li>
              </ol>
            </details>
          </template>
        </div>

        <!-- ==================== OS PICKER (Recovery/Normal mode) ==================== -->
        <template v-if="activeSection === 'os-picker'">
          <div class="os-picker">
            <h3>Available operating systems</h3>
            <p class="text-dim">Choose an OS to install on {{ device.display_name || device.model || 'your device' }}.</p>

            <div class="os-picker-grid">
              <button
                v-for="os in deviceOsList.filter(o => o.type === 'rom')"
                :key="os.id"
                class="os-picker-card"
                @click="startOsInstall(os)"
              >
                <div class="os-picker-name">{{ os.name }}</div>
                <div class="os-picker-desc">{{ os.desc }}</div>
                <div v-if="os.tags?.length" class="os-picker-tags">
                  <span v-for="tag in os.tags" :key="tag" class="os-tag">{{ tag }}</span>
                </div>
              </button>
            </div>

            <div v-if="deviceOsList.filter(o => o.type === 'recovery').length" class="os-picker-recoveries">
              <h4>Available recoveries</h4>
              <div class="os-picker-grid">
                <div
                  v-for="rec in deviceOsList.filter(o => o.type === 'recovery')"
                  :key="rec.id"
                  class="os-picker-card os-picker-card-secondary"
                >
                  <div class="os-picker-name">{{ rec.name }}</div>
                  <div class="os-picker-desc">{{ rec.desc }}</div>
                </div>
              </div>
            </div>

            <div class="os-picker-actions">
              <button class="btn btn-secondary" @click="activeSection = ''">
                Close
              </button>
            </div>
          </div>
        </template>

        <!-- ==================== SAMSUNG STOCK RESTORE (Recovery mode) ==================== -->
        <template v-if="activeSection === 'samsung-restore'">

          <!-- Picking firmware version -->
          <div v-if="samsungRestoreStatus === 'picking'">
            <h3>Restore stock firmware</h3>
            <p class="text-dim">Download and flash official Samsung firmware for {{ device.display_name || device.model }}.</p>

            <div v-if="samsungLoading" class="install-loading">
              <span class="spinner-small"></span> Checking Samsung servers for available firmware...
            </div>

            <div v-else>
              <div v-if="samsungVersions.length" class="samsung-fw-list">
                <p class="text-dim" style="margin-bottom: 0.5rem;">Available firmware versions (choose your region):</p>
                <div class="os-picker-grid">
                  <button
                    v-for="fw in samsungVersions"
                    :key="fw.version + fw.region"
                    class="os-picker-card"
                    @click="flashSamsungStock(fw)"
                  >
                    <div class="os-picker-name">{{ fw.version }}</div>
                    <div class="os-picker-desc">
                      Region: {{ fw.region_label }} ({{ fw.region }})
                      <span v-if="fw.alt_regions?.length"> &mdash; also available in {{ fw.alt_regions.map(r => r.label).join(', ') }}</span>
                    </div>
                  </button>
                </div>
              </div>

              <div v-else class="info-box info-box--warn" style="margin-top: 0.75rem;">
                <p>Could not find firmware on Samsung's servers automatically.</p>
                <p class="text-dim">This can happen with older or region-specific models.</p>
              </div>

              <!-- Manual firmware path -->
              <div class="samsung-manual" style="margin-top: 1.25rem;">
                <label class="section-label">Use a firmware ZIP you already downloaded</label>
                <p class="text-dim" style="margin-bottom: 0.5rem;">
                  Download firmware from <a :href="'https://samfw.com/firmware/' + (device.model || '')" target="_blank" rel="noopener">samfw.com</a>,
                  then paste the path to the ZIP file below.
                </p>
                <div style="display: flex; gap: 0.5rem; align-items: center;">
                  <input
                    v-model="samsungManualZip"
                    type="text"
                    class="input-path"
                    placeholder="/home/user/Downloads/GT-I8160_XEF_firmware.zip"
                    style="flex: 1;"
                  />
                  <button class="btn btn-primary" :disabled="!samsungManualZip.trim()" @click="flashSamsungManual">
                    Flash &rarr;
                  </button>
                </div>
              </div>
            </div>

            <div class="os-picker-actions" style="margin-top: 1rem;">
              <button class="btn btn-secondary" @click="activeSection = ''">
                Close
              </button>
            </div>
          </div>

          <!-- Flashing in progress -->
          <div v-else-if="samsungRestoreStatus === 'flashing'">
            <h3>Restoring stock firmware...</h3>
            <p class="text-dim">OSmosis will download the firmware, reboot to Download Mode, and flash via Heimdall. Do not unplug the USB cable.</p>
            <div v-if="samsungRestoreTaskId" class="task-section">
              <TerminalOutput :taskId="samsungRestoreTaskId" />
            </div>
            <div v-else class="install-loading">
              <span class="spinner-small"></span> Starting...
            </div>
          </div>

          <!-- Error -->
          <div v-else-if="samsungRestoreStatus === 'error'">
            <div class="info-box info-box--warn">
              <p>Stock restore failed. Check the terminal output above for details.</p>
            </div>
            <div class="os-picker-actions" style="margin-top: 1rem;">
              <button class="btn btn-secondary" @click="samsungRestoreStatus = 'picking'">
                &larr; Try again
              </button>
            </div>
          </div>
        </template>

        <!-- ==================== RESTORE STOCK FIRMWARE ==================== -->
        <template v-if="activeSection === 'restore'">

          <!-- Picking ROM -->
          <div v-if="flashStatus === 'picking'" class="rom-picker">
            <h3>Select a ROM version to flash</h3>
            <div v-if="deviceParsed" class="picker-info">
              <div class="picker-hint">
                Firmware: <strong>{{ deviceParsed.Version || 'unknown' }}</strong>
                &middot; Region: <strong>{{ deviceParsed.region_label || 'unknown' }}</strong>
                <span class="picker-region-code">({{ deviceParsed.rom_code }})</span>
              </div>
              <p class="picker-hint">
                Showing ROMs compatible with your device's region. Choose a <strong>different</strong> version — same-version reinstall may be rejected.
              </p>
            </div>

            <div v-if="isCrossFlashed" class="banner banner-crossflash banner-inline">
              MIAssistant sideload may fail on this device due to firmware/hardware mismatch.
              Consider using <strong>bootloader unlock + fastboot flash</strong> instead.
            </div>

            <div class="rom-grid">
              <div
                v-for="rom in mergedRoms"
                :key="rom.version || rom.filename"
                class="rom-card"
                :class="{ 'rom-not-downloaded': !rom.downloaded, 'rom-other-region': rom.compatible === false }"
              >
                <div class="rom-card-left">
                  <div class="rom-version">
                    {{ rom.version }}
                    <span v-if="rom.region_label" class="rom-region-tag">{{ rom.region_label }}</span>
                    <span v-if="rom.compatible === true" class="badge badge-compatible">Compatible</span>
                    <span v-if="rom.compatible === false" class="badge badge-incompatible">Incompatible</span>
                    <span v-if="rom.android" class="rom-android">Android {{ rom.android }}</span>
                  </div>
                  <div class="rom-name-small">{{ rom.name || rom.filename }}</div>
                  <div v-if="rom.compatible === false" class="rom-warn">Different region than detected — may not install</div>
                </div>
                <div class="rom-card-right">
                  <button v-if="rom.downloaded" class="btn-rom-flash" @click="flashRom(rom)">
                    Flash
                  </button>
                  <button v-else class="btn-rom-download" @click="downloadRom(rom)">
                    Download
                  </button>
                  <div v-if="rom.downloaded" class="rom-meta">{{ rom.size_mb }} MB</div>
                </div>
              </div>
            </div>
            <button class="btn btn-link" @click="backToActions">&larr; Back to actions</button>
          </div>

          <!-- Downloading ROM -->
          <div v-else-if="flashStatus === 'downloading'" class="flash-progress">
            <div class="flash-header-row">
              <span class="spinner-small"></span>
              <span>Downloading firmware...</span>
            </div>
            <div class="flash-terminal">
              <div
                v-for="(msg, i) in downloadMessages"
                :key="i"
                class="term-line"
                :class="'term-' + (msg.level || 'info')"
              >{{ msg.msg }}</div>
            </div>
          </div>

          <!-- Flashing in progress -->
          <div v-else-if="flashStatus === 'running'" class="flash-progress">
            <div class="flash-header-row">
              <span class="spinner-small"></span>
              <span>Flashing firmware...</span>
            </div>
            <div class="flash-terminal">
              <div
                v-for="(msg, i) in flashMessages"
                :key="i"
                class="term-line"
                :class="'term-' + (msg.level || 'info')"
              >{{ msg.msg }}</div>
            </div>
          </div>

          <!-- Done -->
          <div v-else-if="flashStatus === 'done'" class="flash-result flash-result-ok">
            <div class="result-icon">&#x2705;</div>
            <h3>Firmware restored successfully!</h3>
            <p>The device will verify and install the ROM. This may take several minutes. Do not unplug the USB cable.</p>
            <p>First boot after a full flash can take 5-10 minutes.</p>
            <button class="btn btn-primary" @click="retry">Done</button>
          </div>

          <!-- Error -->
          <div v-else-if="flashStatus === 'error'" class="flash-result flash-result-err">
            <div class="result-icon">&#x274C;</div>
            <h3>Flash failed</h3>
            <div class="flash-terminal flash-terminal-short">
              <div
                v-for="(msg, i) in flashMessages.slice(-10)"
                :key="i"
                class="term-line"
                :class="'term-' + (msg.level || 'info')"
              >{{ msg.msg }}</div>
            </div>
            <div class="result-actions">
              <button class="btn btn-primary" @click="retry">Try again</button>
              <button class="btn btn-link" @click="router.push('/')">Back to home</button>
            </div>
          </div>
        </template>

        <!-- ==================== UNLOCK BOOTLOADER ==================== -->
        <template v-if="activeSection === 'unlock'">

          <!-- Unlock form -->
          <div v-if="unlockStatus === 'form'" class="unlock-section">
            <h3>Unlock bootloader</h3>

            <div class="unlock-status-row">
              <span class="info-label">Current lock status:</span>
              <span v-if="device.unlocked === true" class="meta-chip unlocked">Unlocked</span>
              <span v-else-if="device.unlocked === false" class="meta-chip locked">Locked</span>
              <span v-else class="meta-chip">Unknown</span>
            </div>

            <div v-if="unlockAbilityStatus === 'checking'" class="unlock-ability-check">
              <span class="spinner-small"></span> Checking unlock eligibility...
            </div>
            <div v-else-if="unlockAbilityStatus && unlockAbilityStatus.error" class="unlock-ability-result unlock-ability-error">
              <template v-if="unlockAbilityStatus.error.toLowerCase().includes('fastboot')">
                <div class="fastboot-required-notice">
                  <strong>Fastboot mode required</strong>
                  <p>Bootloader unlock must be performed in fastboot mode. Your device is currently in {{ device?.mode || 'a different' }} mode.</p>
                  <button class="btn btn-primary" @click="rebootToFastbootAndUnlock">Reboot to fastboot and unlock</button>
                  <p class="notice-hint">The device will reboot, then the unlock flow will continue automatically.</p>
                </div>
              </template>
              <template v-else>
                {{ unlockAbilityStatus.error }}
              </template>
            </div>
            <div v-else-if="unlockAbilityStatus && unlockAbilityStatus.eligible === true" class="unlock-ability-result unlock-ability-ok">
              Device is eligible for bootloader unlock.
              <span v-if="unlockAbilityStatus.wait_hours"> Wait time remaining: {{ unlockAbilityStatus.wait_hours }} hours.</span>
            </div>
            <div v-else-if="unlockAbilityStatus && unlockAbilityStatus.eligible === false" class="unlock-ability-result unlock-ability-error">
              Device is not currently eligible for unlock.
              <span v-if="unlockAbilityStatus.reason"> Reason: {{ unlockAbilityStatus.reason }}</span>
            </div>

            <div class="banner banner-warn">
              Unlocking the bootloader will <strong>erase all data</strong> on the device.
              You need a Mi account linked to this device. Xiaomi may enforce a waiting period (72h-360h)
              before the unlock is allowed.
            </div>

            <p class="unlock-account-label">Select a Mi account with an active session to use for unlock:</p>

            <MiAccountManager
              :selectable="true"
              :device-region="deviceParsed?.region_code || ''"
              :selected-account-id="selectedUnlockAccount?.id || ''"
              @select="onUnlockAccountSelect"
              @session-ready="onUnlockSessionReady"
            />

            <div class="unlock-form-actions">
              <button
                class="btn btn-primary"
                :disabled="!selectedUnlockAccount || !selectedUnlockAccount.session_active"
                @click="submitUnlock"
              >
                Unlock Bootloader
              </button>
              <span v-if="selectedUnlockAccount && !selectedUnlockAccount.session_active" class="unlock-session-hint">
                Log in to this account first to establish a session.
              </span>
              <button class="btn btn-link" @click="backToActions">&larr; Back to actions</button>
            </div>
          </div>

          <!-- Unlock running -->
          <div v-else-if="unlockStatus === 'running'" class="flash-progress">
            <div class="flash-header-row">
              <span class="spinner-small"></span>
              <span>Unlocking bootloader...</span>
            </div>
            <div class="flash-terminal">
              <div
                v-for="(msg, i) in unlockMessages"
                :key="i"
                class="term-line"
                :class="'term-' + (msg.level || 'info')"
              >{{ msg.msg }}</div>
            </div>
          </div>

          <!-- Unlock done -->
          <div v-else-if="unlockStatus === 'done'" class="flash-result flash-result-ok">
            <div class="result-icon">&#x2705;</div>
            <h3>Bootloader unlocked</h3>
            <p>The device bootloader has been unlocked. You can now flash firmware via fastboot.</p>
            <p>The device will reboot and perform a factory reset. This is normal.</p>
            <div class="result-actions">
              <button class="btn btn-primary" @click="retry">Done</button>
            </div>
          </div>

          <!-- Unlock error -->
          <div v-else-if="unlockStatus === 'error'" class="flash-result flash-result-err">
            <div class="result-icon">&#x274C;</div>
            <h3>Unlock failed</h3>
            <div class="flash-terminal flash-terminal-short">
              <div
                v-for="(msg, i) in unlockMessages.slice(-10)"
                :key="i"
                class="term-line"
                :class="'term-' + (msg.level || 'info')"
              >{{ msg.msg }}</div>
            </div>
            <div v-if="unlockNeedsFastboot" class="fastboot-required-notice">
              <p>Bootloader unlock requires fastboot mode. Your device is currently in {{ device?.mode || 'a different' }} mode.</p>
              <button class="btn btn-primary" @click="rebootToFastbootAndUnlock">Reboot to fastboot and unlock</button>
              <p class="notice-hint">The device will reboot, then the unlock flow will continue automatically.</p>
            </div>
            <div v-else class="result-actions">
              <button class="btn btn-primary" @click="startUnlock">Try again</button>
              <button class="btn btn-link" @click="backToActions">&larr; Back to actions</button>
            </div>
          </div>
        </template>

        <!-- ==================== FASTBOOT FLASH ==================== -->
        <template v-if="activeSection === 'fastboot'">

          <!-- Fastboot ROM picker -->
          <div v-if="fastbootStatus === 'picking'" class="rom-picker">
            <h3>Select firmware to flash via fastboot</h3>

            <div v-if="device.unlocked === false" class="banner banner-warn">
              The bootloader is locked. Fastboot flash requires an unlocked bootloader.
              Go back and unlock the bootloader first.
            </div>

            <div v-if="fastbootRoms.length === 0" class="rom-empty">
              No fastboot-flashable ROMs found on disk. Download the correct factory image for your device first.
            </div>
            <div v-else class="rom-grid">
              <div
                v-for="rom in fastbootRoms"
                :key="rom.version || rom.filename"
                class="rom-card"
                :class="{ 'rom-other-region': rom.compatible === false }"
              >
                <div class="rom-card-left">
                  <div class="rom-version">
                    {{ rom.version || rom.filename }}
                    <span v-if="rom.region_label" class="rom-region-tag">{{ rom.region_label }}</span>
                    <span v-if="rom.compatible === true" class="badge badge-compatible">Compatible</span>
                    <span v-if="rom.compatible === false" class="badge badge-incompatible">Incompatible</span>
                  </div>
                  <div class="rom-name-small">{{ rom.name || rom.filename }}</div>
                </div>
                <div class="rom-card-right">
                  <button class="btn-rom-flash" :disabled="device.unlocked === false" @click="flashFastbootRom(rom)">
                    Flash
                  </button>
                  <div v-if="rom.size_mb" class="rom-meta">{{ rom.size_mb }} MB</div>
                </div>
              </div>
            </div>
            <button class="btn btn-link" @click="backToActions">&larr; Back to actions</button>
          </div>

          <!-- Fastboot flashing in progress -->
          <div v-else-if="fastbootStatus === 'running'" class="flash-progress">
            <div class="flash-header-row">
              <span class="spinner-small"></span>
              <span>Flashing via fastboot...</span>
            </div>
            <div class="flash-terminal">
              <div
                v-for="(msg, i) in fastbootMessages"
                :key="i"
                class="term-line"
                :class="'term-' + (msg.level || 'info')"
              >{{ msg.msg }}</div>
            </div>
          </div>

          <!-- Fastboot done -->
          <div v-else-if="fastbootStatus === 'done'" class="flash-result flash-result-ok">
            <div class="result-icon">&#x2705;</div>
            <h3>Firmware flashed successfully!</h3>
            <p>The device will reboot and install the firmware. First boot may take 5-10 minutes.</p>
            <button class="btn btn-primary" @click="retry">Done</button>
          </div>

          <!-- Fastboot error -->
          <div v-else-if="fastbootStatus === 'error'" class="flash-result flash-result-err">
            <div class="result-icon">&#x274C;</div>
            <h3>Fastboot flash failed</h3>
            <div class="flash-terminal flash-terminal-short">
              <div
                v-for="(msg, i) in fastbootMessages.slice(-10)"
                :key="i"
                class="term-line"
                :class="'term-' + (msg.level || 'info')"
              >{{ msg.msg }}</div>
            </div>
            <div class="result-actions">
              <button class="btn btn-primary" @click="startFastbootFlash">Try again</button>
              <button class="btn btn-link" @click="backToActions">&larr; Back to actions</button>
            </div>
          </div>
        </template>

        <!-- ==================== REBOOT STATUS ==================== -->
        <!-- Only show reboot banners when no active section is open -->
        <template v-if="!activeSection && !waitingForFastboot">
          <div v-if="rebootStatus === 'rebooting'" class="banner banner-info">
            <span class="spinner-small"></span>
            Sending reboot command ({{ rebootTarget }})...
          </div>
          <div v-if="rebootStatus === 'done'" class="banner banner-success">
            <template v-if="rebootTarget === 'recovery'">
              Reboot to recovery sent. The device will enter recovery mode shortly.
            </template>
            <template v-else-if="rebootTarget === 'bootloader' || rebootTarget === 'fastboot'">
              Reboot to fastboot sent. The device will enter fastboot mode shortly. This page will update when it reconnects.
            </template>
            <template v-else-if="rebootTarget === 'download'">
              Reboot to download mode sent. The device will enter Samsung Download Mode shortly.
            </template>
            <template v-else>
              Reboot sent. The device will boot into the OS shortly.
            </template>
            <div style="margin-top: 0.5rem">
              <button class="btn btn-link" @click="rebootStatus = ''">&larr; Back to actions</button>
            </div>
          </div>
          <div v-if="rebootStatus === 'error'" class="banner banner-warn">
            Reboot failed: {{ rebootError }}
            <div style="margin-top: 0.5rem">
              <button class="btn btn-link" @click="rebootStatus = ''">&larr; Back</button>
            </div>
          </div>
        </template>

        <!-- ==================== EDL ENTRY ==================== -->
        <template v-if="activeSection === 'edl'">
          <button class="btn btn-link" @click="activeSection = ''" style="margin-bottom: 1rem">&larr; Back to actions</button>
          <EdlEntryFlow
            :active="activeSection === 'edl'"
            :device-mode="device?.mode || ''"
            @edl-ready="edlReady = true"
            @cancel="activeSection = ''"
            @reboot-to-fastboot="rebootToFastbootAndEdl"
          />
        </template>

      </div>
    </template>
  </div>
</template>

<style scoped>
/* =============================================
   Pokédex-inspired layout — OSmosis flavor
   ============================================= */

.connected-page {
  max-width: 800px;
  margin: 0 auto;
  padding: 1rem;
}
.back-link { margin-bottom: 1rem; }

.connected-loading, .connected-disconnected {
  text-align: center;
  padding: 3rem 0;
  color: var(--text-dim);
}
.disconnect-icon { font-size: 3rem; margin-bottom: 1rem; }
.spinner-small {
  display: inline-block;
  width: 1rem; height: 1rem;
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ---- Pokédex Shell ---- */
.dex-shell {
  background: var(--bg-card);
  border: 2px solid var(--border);
  border-radius: 18px;
  overflow: hidden;
  box-shadow: var(--shadow), inset 0 1px 0 color-mix(in srgb, var(--text) 5%, transparent);
  margin-bottom: 1.5rem;
}

/* Top bar — indicator lights row */
.dex-top-bar {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1.25rem;
  background: color-mix(in srgb, var(--accent) 6%, var(--bg-card));
  border-bottom: 2px solid var(--border);
}

/* Main lens (Pokédex "big blue eye") */
.dex-lens {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: color-mix(in srgb, var(--lens-color, var(--accent)) 25%, var(--bg));
  border: 3px solid color-mix(in srgb, var(--lens-color, var(--accent)) 50%, var(--border));
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  position: relative;
}
.dex-lens-inner {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--lens-color, var(--accent));
  box-shadow: 0 0 10px var(--lens-color, var(--accent)), inset 0 -2px 4px rgba(0,0,0,0.3);
  animation: lens-glow 3s ease-in-out infinite;
}
@keyframes lens-glow {
  0%, 100% { opacity: 1; box-shadow: 0 0 10px var(--lens-color, var(--accent)), inset 0 -2px 4px rgba(0,0,0,0.3); }
  50% { opacity: 0.7; box-shadow: 0 0 18px var(--lens-color, var(--accent)), inset 0 -2px 4px rgba(0,0,0,0.3); }
}

/* Small LED indicators */
.dex-indicators {
  display: flex;
  gap: 0.4rem;
}
.dex-led {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  opacity: 0.35;
}
.dex-led-red { background: #f44336; }
.dex-led-yellow { background: #fcc53a; }
.dex-led-green { background: #4caf50; }
.dex-led-active {
  opacity: 1;
  box-shadow: 0 0 6px #4caf50;
  animation: led-blink 2s ease-in-out infinite;
}
@keyframes led-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* Entry number — like a Pokédex serial */
.dex-entry-number {
  margin-left: auto;
  font-family: monospace;
  font-size: calc(0.72rem * var(--font-scale));
  color: var(--text-dim);
  letter-spacing: 0.08em;
  font-weight: 600;
  opacity: 0.7;
}

/* Viewport row: device frame + stats side by side */
.dex-viewport-row {
  display: flex;
  gap: 1.25rem;
  padding: 1.25rem;
  align-items: flex-start;
}

/* Device frame — displayed bigger without container */
.dex-device-frame {
  flex-shrink: 0;
}
.dex-device-frame :deep(.device-frame) {
  width: 170px;
}

/* Stats panel */
.dex-stats {
  flex: 1;
  min-width: 0;
}
.dex-name-row {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  flex-wrap: wrap;
  margin-bottom: 0.75rem;
}
.dex-device-name {
  font-size: calc(1.35rem * var(--font-scale));
  font-weight: 700;
  margin: 0;
  line-height: 1.2;
}

/* Type badge — like Pokémon type chips */
.dex-type-badge {
  display: inline-block;
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
  font-size: calc(0.65rem * var(--font-scale));
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  white-space: nowrap;
  box-shadow: 0 1px 3px rgba(0,0,0,0.3);
}

/* Stat rows with bars */
.dex-stat-grid {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  margin-bottom: 0.75rem;
}
.dex-stat {
  display: grid;
  grid-template-columns: 80px 1fr;
  grid-template-rows: auto auto;
  column-gap: 0.6rem;
  row-gap: 0;
  align-items: baseline;
  padding: 0.2rem 0;
}
.dex-stat-label {
  font-size: calc(0.68rem * var(--font-scale));
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-dim);
  grid-row: 1;
  grid-column: 1;
}
.dex-stat-value {
  font-size: calc(0.85rem * var(--font-scale));
  font-weight: 500;
  grid-row: 1;
  grid-column: 2;
  word-break: break-word;
}
.dex-stat-value.mono { font-family: monospace; }
.dex-stat-bar {
  grid-column: 1 / -1;
  height: 3px;
  border-radius: 2px;
  background: color-mix(in srgb, var(--border) 40%, transparent);
  overflow: hidden;
  margin-top: 0.15rem;
}
.dex-stat-bar-fill {
  height: 100%;
  border-radius: 2px;
  background: var(--accent);
  opacity: 0.5;
  transition: width 0.6s ease;
}

.text-dim { color: var(--text-dim); }
.locked-text { color: #f44336; }
.unlocked-text { color: #4caf50; }

.dex-desc {
  font-size: calc(0.82rem * var(--font-scale));
  color: var(--text-dim);
  line-height: 1.5;
  margin: 0;
  padding-top: 0.25rem;
  border-top: 1px solid color-mix(in srgb, var(--border) 40%, transparent);
}

.dex-wiki-link {
  display: inline-block;
  margin-top: 0.5rem;
  font-size: calc(0.8rem * var(--font-scale));
  color: var(--accent);
  text-decoration: none;
}
.dex-wiki-link:hover { text-decoration: underline; }

/* Hinge detail at bottom of shell */
.dex-hinge {
  height: 6px;
  background: linear-gradient(
    to bottom,
    var(--border),
    color-mix(in srgb, var(--accent) 15%, var(--border)),
    var(--border)
  );
}

/* Screen overlay for normal "connected" mode */
.screen-connected {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.3rem;
}
.screen-connected-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #4caf50;
  box-shadow: 0 0 6px #4caf50;
}
.screen-connected-label {
  font-size: 0.55rem;
  color: #4caf50;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Responsive: stack vertically on narrow screens */
@media (max-width: 520px) {
  .dex-viewport-row {
    flex-direction: column;
    align-items: center;
    text-align: center;
  }
  .dex-name-row { justify-content: center; }
  .dex-stat {
    grid-template-columns: 70px 1fr;
    text-align: left;
  }
}

/* ---- Banners ---- */
.banner {
  border-radius: 8px; padding: 1rem; margin-bottom: 1.25rem;
  font-size: calc(0.85rem * var(--font-scale)); line-height: 1.6;
}
.banner-crossflash {
  background: color-mix(in srgb, #f44336 10%, var(--bg-card));
  border: 1px solid #f44336;
  color: var(--text);
}
.banner-crossflash .banner-title {
  font-weight: 700; font-size: calc(0.95rem * var(--font-scale));
  margin-bottom: 0.5rem; color: #f44336;
}
.banner-crossflash p { margin: 0.4rem 0; }
.banner-flashing {
  background: color-mix(in srgb, #e91e63 10%, var(--bg-card));
  border: 1px solid #e91e63;
}
.banner-warn {
  background: color-mix(in srgb, #ff9800 10%, var(--bg-card));
  border: 1px solid #ff9800;
}
.banner-info {
  background: color-mix(in srgb, #2196f3 10%, var(--bg-card));
  border: 1px solid #2196f3;
  display: flex; align-items: center; gap: 0.5rem;
}
.banner-success {
  background: color-mix(in srgb, #4caf50 10%, var(--bg-card));
  border: 1px solid #4caf50;
}
.banner-inline { margin-top: 0.75rem; }

/* ---- Sections (info + actions) ---- */
.dex-detail-section {
  margin-bottom: 1.5rem;
}
.dex-actions-section {
  margin-bottom: 2rem;
}
.dex-section-title {
  font-size: calc(1rem * var(--font-scale));
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--accent);
  margin-bottom: 0.75rem;
  padding-bottom: 0.4rem;
  border-bottom: 2px solid color-mix(in srgb, var(--accent) 30%, transparent);
}

/* Device info grid */
.device-info-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 0.5rem 1.5rem; margin-bottom: 0.75rem;
}
.info-item {
  display: flex; flex-direction: column; gap: 0.15rem;
  padding: 0.5rem 0;
}
.info-label {
  font-size: calc(0.72rem * var(--font-scale));
  color: var(--text-dim); text-transform: uppercase;
  letter-spacing: 0.04em; font-weight: 600;
}
.info-value {
  font-size: calc(0.9rem * var(--font-scale));
  font-weight: 500;
}
.raw-info-details { margin-top: 0.25rem; }
.raw-info-summary {
  font-size: calc(0.8rem * var(--font-scale));
  color: var(--text-dim); cursor: pointer;
}
.device-info-pre {
  font-family: monospace; font-size: calc(0.8rem * var(--font-scale));
  background: var(--bg); border: 1px solid var(--border);
  border-radius: 8px; padding: 1rem; overflow-x: auto;
  white-space: pre-wrap; color: var(--text-dim);
  margin-top: 0.5rem;
}

/* ---- Action grid — tactile Pokédex buttons ---- */
.action-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 0.75rem;
}
.action-card {
  display: flex; flex-direction: column; align-items: flex-start;
  padding: 1rem 1.1rem;
  border-radius: 12px;
  border: 2px solid var(--border);
  background: var(--bg-card);
  cursor: pointer; text-align: left;
  transition: all 0.15s ease;
  position: relative;
  overflow: hidden;
}
/* Subtle left accent stripe */
.action-card::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 4px;
  background: var(--border);
  transition: background 0.15s ease;
}
.action-card:hover {
  border-color: var(--accent);
  background: color-mix(in srgb, var(--accent) 6%, var(--bg-card));
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}
.action-card:hover::before {
  background: var(--accent);
}
.action-primary {
  border-color: var(--accent);
  background: color-mix(in srgb, var(--accent) 5%, var(--bg-card));
}
.action-primary::before {
  background: var(--accent);
}
.action-icon {
  font-size: 1.4rem;
  margin-bottom: 0.4rem;
  filter: drop-shadow(0 1px 2px rgba(0,0,0,0.2));
}
.action-label {
  font-weight: 600; font-size: calc(0.9rem * var(--font-scale));
  margin-bottom: 0.2rem;
}
.action-desc {
  font-size: calc(0.78rem * var(--font-scale)); color: var(--text-dim); line-height: 1.4;
}
.action-locked-notice {
  padding: 1.5rem; text-align: center; color: var(--text-dim);
  font-style: italic;
}

/* ---- ROM picker ---- */
.rom-picker h3 {
  font-size: calc(1rem * var(--font-scale)); margin-bottom: 0.75rem;
}
.rom-grid { display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 1rem; }
.rom-card {
  display: flex; justify-content: space-between; align-items: center;
  padding: 0.85rem 1rem; border-radius: 10px;
  border: 2px solid var(--border); background: var(--bg-card);
  cursor: pointer; transition: all 0.15s ease;
}
.rom-card:hover {
  border-color: var(--accent);
  background: color-mix(in srgb, var(--accent) 6%, var(--bg-card));
}
.rom-card-left { flex: 1; min-width: 0; }
.rom-version {
  font-size: calc(0.95rem * var(--font-scale)); font-weight: 600;
  display: flex; align-items: center; flex-wrap: wrap; gap: 0.3rem;
}
.rom-name-small {
  font-size: calc(0.72rem * var(--font-scale)); color: var(--text-dim);
  word-break: break-all; margin-top: 0.15rem;
}
.rom-name {
  font-size: calc(0.85rem * var(--font-scale)); font-weight: 500;
  word-break: break-all;
}

/* OS picker */
.os-picker { max-width: 700px; }
.os-picker h3 { font-size: calc(1rem * var(--font-scale)); margin-bottom: 0.25rem; }
.os-picker h4 { font-size: calc(0.9rem * var(--font-scale)); margin: 1.25rem 0 0.5rem; color: var(--text-dim); }
.os-picker-grid {
  display: grid; grid-template-columns: 1fr; gap: 0.5rem;
}
.os-picker-card {
  display: block; width: 100%; text-align: left;
  padding: 0.85rem 1rem; border-radius: 10px;
  border: 2px solid var(--border); background: var(--bg-card);
  cursor: pointer; transition: all 0.15s ease;
}
.os-picker-card:hover {
  border-color: var(--accent);
  background: color-mix(in srgb, var(--accent) 6%, var(--bg-card));
}
.os-picker-card-secondary { cursor: default; opacity: 0.8; }
.os-picker-card-secondary:hover { border-color: var(--border); background: var(--bg-card); }
.os-picker-name { font-weight: 600; font-size: calc(0.95rem * var(--font-scale)); margin-bottom: 0.2rem; }
.os-picker-desc { font-size: calc(0.82rem * var(--font-scale)); color: var(--text-dim); }
.os-picker-tags { display: flex; gap: 0.35rem; margin-top: 0.4rem; flex-wrap: wrap; }
.os-tag {
  font-size: calc(0.68rem * var(--font-scale)); padding: 0.1rem 0.45rem;
  border-radius: 4px; background: color-mix(in srgb, var(--accent) 15%, transparent);
  color: var(--accent);
}
.os-picker-actions { margin-top: 1rem; }

/* Samsung stock restore */
.input-path {
  padding: 0.5rem 0.75rem; border-radius: 6px;
  border: 1px solid var(--border); background: var(--bg-card);
  color: var(--text); font-family: var(--font-mono, monospace);
  font-size: calc(0.85rem * var(--font-scale));
}
.input-path:focus { outline: none; border-color: var(--accent); }
.install-loading { display: flex; align-items: center; gap: 0.5rem; padding: 1rem 0; color: var(--text-dim); }

.picker-info { margin-bottom: 1rem; }
.picker-hint {
  font-size: calc(0.85rem * var(--font-scale)); color: var(--text-dim);
  margin-bottom: 0.35rem; line-height: 1.5;
}
.picker-region-code {
  font-family: monospace; font-size: calc(0.75rem * var(--font-scale));
  opacity: 0.7;
}
.rom-meta {
  font-size: calc(0.75rem * var(--font-scale)); color: var(--text-dim);
  white-space: nowrap; margin-left: 1rem;
}
.rom-card-right {
  display: flex; flex-direction: column; align-items: flex-end; gap: 0.3rem;
  flex-shrink: 0;
}
.rom-not-downloaded {
  opacity: 0.7; border-style: dashed;
}
.rom-not-downloaded:hover { opacity: 1; }
.rom-other-region {
  opacity: 0.6; border-color: var(--warning, #ff9800);
}
.rom-region-tag {
  font-size: calc(0.68rem * var(--font-scale));
  padding: 0.1rem 0.4rem; border-radius: 999px;
  background: color-mix(in srgb, var(--accent) 15%, transparent);
  color: var(--accent); font-weight: 600;
}
.rom-warn {
  font-size: calc(0.72rem * var(--font-scale));
  color: var(--warning, #ff9800); margin-top: 0.2rem;
}
.rom-android {
  font-size: calc(0.7rem * var(--font-scale)); color: var(--text-dim);
  font-weight: 400;
}
.rom-empty {
  padding: 1.5rem; text-align: center; color: var(--text-dim);
  font-style: italic;
}

/* Badges */
.badge {
  font-size: calc(0.65rem * var(--font-scale));
  padding: 0.1rem 0.4rem; border-radius: 999px;
  font-weight: 600; text-transform: uppercase; letter-spacing: 0.03em;
}
.badge-compatible {
  background: color-mix(in srgb, #4caf50 15%, transparent);
  color: #4caf50;
}
.badge-incompatible {
  background: color-mix(in srgb, #f44336 15%, transparent);
  color: #f44336;
}

/* ROM buttons */
.btn-rom-flash, .btn-rom-download {
  padding: 0.35rem 0.85rem; border-radius: 6px;
  font-size: calc(0.8rem * var(--font-scale)); font-weight: 600;
  cursor: pointer; border: none; transition: all 0.15s ease;
}
.btn-rom-flash {
  background: var(--accent); color: white;
}
.btn-rom-flash:hover { filter: brightness(1.1); }
.btn-rom-flash:disabled {
  opacity: 0.4; cursor: not-allowed; filter: none;
}
.btn-rom-download {
  background: transparent; color: var(--accent);
  border: 1px solid var(--accent);
}
.btn-rom-download:hover {
  background: color-mix(in srgb, var(--accent) 10%, transparent);
}

/* Flash progress */
.flash-header-row {
  display: flex; align-items: center; gap: 0.5rem;
  font-weight: 600; margin-bottom: 0.75rem;
}
.flash-terminal {
  background: #0d1117; color: #c9d1d9;
  border-radius: 8px; padding: 1rem;
  font-family: monospace; font-size: calc(0.78rem * var(--font-scale));
  max-height: 400px; overflow-y: auto;
  line-height: 1.6;
}
.flash-terminal-short { max-height: 200px; }
.term-line { white-space: pre-wrap; }
.term-info { color: #c9d1d9; }
.term-success { color: #3fb950; }
.term-warn { color: #d29922; }
.term-error { color: #f85149; }
.term-cmd { color: #79c0ff; }

/* Results */
.flash-result {
  text-align: center; padding: 2rem 1rem;
  border-radius: 12px; border: 2px solid var(--border);
}
.flash-result-ok { background: color-mix(in srgb, #4caf50 8%, var(--bg-card)); border-color: #4caf50; }
.flash-result-err { background: color-mix(in srgb, #f44336 8%, var(--bg-card)); border-color: #f44336; }
.result-icon { font-size: 2.5rem; margin-bottom: 0.5rem; }
.result-actions { display: flex; gap: 1rem; justify-content: center; margin-top: 1rem; }

/* Unlock section */
.unlock-section h3 {
  font-size: calc(1rem * var(--font-scale)); margin-bottom: 0.75rem;
}
.unlock-status-row {
  display: flex; align-items: center; gap: 0.5rem;
  margin-bottom: 1rem;
}
.unlock-ability-check {
  display: flex; align-items: center; gap: 0.5rem;
  margin-bottom: 1rem; color: var(--text-dim);
  font-size: calc(0.85rem * var(--font-scale));
}
.unlock-ability-result {
  font-size: calc(0.85rem * var(--font-scale));
  padding: 0.6rem 0.85rem; border-radius: 6px; margin-bottom: 1rem;
  line-height: 1.5;
}
.unlock-ability-ok {
  background: color-mix(in srgb, #4caf50 10%, var(--bg-card));
  border: 1px solid #4caf50;
}
.unlock-ability-error {
  background: color-mix(in srgb, #f44336 10%, var(--bg-card));
  border: 1px solid #f44336;
}
.unlock-form {
  display: flex; flex-direction: column; gap: 0.75rem;
  max-width: 400px; margin-top: 1rem;
}
.form-label {
  display: flex; flex-direction: column; gap: 0.3rem;
  font-size: calc(0.85rem * var(--font-scale));
  font-weight: 500;
}
.form-input {
  padding: 0.5rem 0.7rem; border-radius: 6px;
  border: 1px solid var(--border); background: var(--bg-card);
  color: var(--text); font-size: calc(0.85rem * var(--font-scale));
}
.form-input:focus {
  outline: none; border-color: var(--accent);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--accent) 20%, transparent);
}
.unlock-form-actions {
  display: flex; align-items: center; gap: 1rem; margin-top: 0.5rem;
}

/* ---- Tablet & landscape ---- */
@media (min-width: 900px) {
  .connected-page { max-width: 1060px; padding: 1.5rem 2rem; }

  .action-grid { grid-template-columns: repeat(3, 1fr); }

  .rom-grid { grid-template-columns: repeat(2, 1fr); gap: 1rem; }
  .rom-picker { max-width: none; }

  .device-info-grid { grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); }
}

/* Landscape on touch devices */
@media (min-width: 900px) and (orientation: landscape) and (pointer: coarse) {
  .connected-page { max-width: 1200px; }

  .dex-shell { margin-bottom: 1rem; }
  .dex-viewport-row { padding: 1rem; }
  .dex-device-name { font-size: calc(1.2rem * var(--font-scale)); }
  .dex-actions-section { margin-bottom: 1rem; }
  .dex-section-title { margin-bottom: 0.5rem; }
  .action-card { padding: 0.85rem; }
  .action-icon { font-size: 1.3rem; }

  .flash-terminal { max-height: 180px; }
}

/* Fastboot required notice */
.fastboot-required-notice {
  margin-top: 1rem;
  padding: 1rem;
  border-radius: 8px;
  background: color-mix(in srgb, #9c27b0 8%, var(--bg-card));
  border: 1px solid color-mix(in srgb, #9c27b0 40%, var(--border));
}
.fastboot-required-notice strong {
  display: block;
  margin-bottom: 0.4rem;
  font-size: calc(0.95rem * var(--font-scale));
}
.fastboot-required-notice p {
  margin: 0.4rem 0;
  font-size: calc(0.85rem * var(--font-scale));
  color: var(--text-dim);
  line-height: 1.5;
}
.fastboot-required-notice .btn {
  margin: 0.75rem 0 0.25rem;
}
.fastboot-required-notice .notice-hint {
  font-size: calc(0.8rem * var(--font-scale));
  color: var(--text-dim);
  opacity: 0.8;
}

.usb-guide-card {
  cursor: default;
  text-align: left;
}
.usb-guide-card .action-desc {
  white-space: normal;
}
details.usb-guide-card {
  grid-column: 1 / -1;
}
details.usb-guide-card > summary {
  list-style: none;
  cursor: pointer;
  display: flex;
  align-items: flex-start;
  gap: 0.6rem;
}
details.usb-guide-card > summary::-webkit-details-marker {
  display: none;
}
details.usb-guide-card > summary::after {
  content: '\25B6';
  font-size: 0.65rem;
  margin-left: auto;
  transition: transform 0.2s;
  color: var(--text-dim);
  flex-shrink: 0;
  margin-top: 0.15rem;
}
details[open].usb-guide-card > summary::after {
  transform: rotate(90deg);
}
.action-summary .action-label {
  display: block;
}
.action-summary .action-desc {
  display: block;
  font-size: calc(0.78rem * var(--font-scale, 1));
  color: var(--text-dim);
  margin-top: 0.15rem;
}
.usb-guide-steps {
  margin: 0.75rem 0 0.25rem;
  padding-left: 1.4rem;
  line-height: 1.8;
  font-size: calc(0.85rem * var(--font-scale, 1));
}
.usb-guide-steps li {
  margin-bottom: 0.15rem;
}
.usb-guide-note {
  margin: 0.5rem 0 0;
  font-size: calc(0.82rem * var(--font-scale, 1));
  color: var(--text-dim);
}
</style>
