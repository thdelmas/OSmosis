<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import TerminalOutput from '@/components/shared/TerminalOutput.vue'

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

// Unlock bootloader state
const unlockStatus = ref('')  // '' | 'form' | 'running' | 'done' | 'error'
const unlockMessages = ref([])
const unlockTaskId = ref(null)
const unlockEmail = ref('')
const unlockPassword = ref('')
const unlock2fa = ref('')
const unlockAbilityStatus = ref(null) // null | 'checking' | object with result

// Fastboot flash state
const fastbootStatus = ref('')  // '' | 'picking' | 'running' | 'done' | 'error'
const fastbootMessages = ref([])
const fastbootTaskId = ref(null)
const fastbootRoms = ref([])

// Active section for mode-aware UI
const activeSection = ref('')  // '' | 'restore' | 'unlock' | 'fastboot' | 'info'

const modeColors = {
  device: '#4caf50',
  recovery: '#ff9800',
  sideload: '#2196f3',
  fastboot: '#9c27b0',
  download: '#ff9800',
  unauthorized: '#f44336',
  flashing: '#e91e63',
}

const modeDescriptions = {
  sideload: 'Device is in MIAssistant sideload mode. You can flash an official recovery ROM to restore stock firmware without unlocking the bootloader.',
  fastboot: 'Device is in fastboot mode. You can flash factory firmware images.',
  recovery: 'Device is in recovery mode. You can sideload updates or wipe data.',
  device: 'Device is connected in normal ADB mode.',
  download: 'Device is in Samsung Download Mode. You can flash firmware via Heimdall.',
  unauthorized: 'Device is connected but not authorized. Check the phone screen and approve the USB debugging prompt.',
  flashing: 'A flash operation is in progress. Do not unplug the USB cable.',
}

const canFlash = computed(() => ['sideload', 'fastboot', 'download'].includes(device.value?.mode))
const isSideload = computed(() => device.value?.mode === 'sideload')
const isFastboot = computed(() => device.value?.mode === 'fastboot')
const isFlashing = computed(() => device.value?.mode === 'flashing')
const isRecovery = computed(() => device.value?.mode === 'recovery')

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

async function submitUnlock() {
  if (!unlockEmail.value || !unlockPassword.value) return
  unlockStatus.value = 'running'
  unlockMessages.value = []

  try {
    // NOTE: POST /api/miassistant/unlock endpoint needs to be created in the backend
    const res = await fetch('/api/miassistant/unlock', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: unlockEmail.value,
        password: unlockPassword.value,
        code_2fa: unlock2fa.value || undefined,
        serial: device.value?.serial,
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
  activeSection.value = ''
}

function backToActions() {
  activeSection.value = ''
  flashStatus.value = ''
  fastbootStatus.value = ''
  unlockStatus.value = ''
}

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
      <!-- Device header -->
      <div class="connected-header">
        <div class="connected-status-row">
          <span class="connected-dot" :style="{ background: modeColors[device.mode] || '#888' }"></span>
          <span class="connected-mode-label" :style="{ color: modeColors[device.mode] || '#888' }">
            {{ device.mode.toUpperCase() }}
          </span>
        </div>
        <h1 class="connected-title">{{ device.display_name || device.serial }}</h1>

        <!-- Layered device info -->
        <div class="device-layers">
          <div class="device-layer">
            <span class="layer-label">Hardware</span>
            <span class="layer-value">{{ device.display_name || 'Unknown' }}</span>
            <span v-if="device.serial" class="layer-detail mono">{{ device.serial }}</span>
          </div>
          <div class="device-layer">
            <span class="layer-label">Firmware</span>
            <span class="layer-value">
              {{ deviceParsed?.Device || device.codename || device.product || 'Unknown' }}
            </span>
            <span v-if="deviceParsed?.Version" class="layer-detail">{{ deviceParsed.Version }}</span>
            <span v-if="deviceParsed?.region_label" class="layer-detail">{{ deviceParsed.region_label }}</span>
          </div>
          <div class="device-layer">
            <span class="layer-label">Bootloader</span>
            <span v-if="device.unlocked === true" class="layer-value unlocked-text">Unlocked</span>
            <span v-else-if="device.unlocked === false" class="layer-value locked-text">Locked</span>
            <span v-else class="layer-value">{{ device.mode }}</span>
          </div>
        </div>

        <p class="connected-desc">{{ modeDescriptions[device.mode] || '' }}</p>
      </div>

      <!-- Flashing-in-progress banner -->
      <div v-if="isFlashing" class="banner banner-flashing">
        <strong>Flash in progress</strong> &mdash; the USB connection is locked. Do not unplug the cable or interact with the device until the operation completes.
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
      <div v-if="deviceParsed" class="connected-section">
        <h2>Device info</h2>
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
      <div class="connected-section">
        <h2>Actions</h2>

        <!-- Idle state: show action buttons based on device mode -->
        <div v-if="!activeSection" class="action-grid">

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
          </template>

          <!-- Recovery mode actions -->
          <template v-if="isRecovery">
            <button class="action-card">
              <div class="action-icon">&#x1F5D1;</div>
              <div class="action-label">Wipe data</div>
              <div class="action-desc">Factory reset from recovery mode</div>
            </button>
          </template>

          <!-- Flashing mode: no actions available -->
          <div v-if="isFlashing" class="action-locked-notice">
            No actions available while a flash operation is in progress.
          </div>

          <!-- Generic flash for download mode -->
          <template v-if="device.mode === 'download'">
            <button class="action-card action-primary" @click="startFlash">
              <div class="action-icon">&#x1F4E6;</div>
              <div class="action-label">Restore stock firmware</div>
              <div class="action-desc">Flash an official ROM to fix boot loops or restore factory state</div>
            </button>
          </template>
        </div>

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
              {{ unlockAbilityStatus.error }}
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

            <div class="unlock-form">
              <label class="form-label">
                Mi account email
                <input v-model="unlockEmail" type="email" class="form-input" placeholder="your@email.com" autocomplete="email" />
              </label>
              <label class="form-label">
                Password
                <input v-model="unlockPassword" type="password" class="form-input" placeholder="Mi account password" autocomplete="current-password" />
              </label>
              <label class="form-label">
                2FA code (if enabled)
                <input v-model="unlock2fa" type="text" class="form-input" placeholder="Optional" inputmode="numeric" autocomplete="one-time-code" />
              </label>
              <div class="unlock-form-actions">
                <button class="btn btn-primary" :disabled="!unlockEmail || !unlockPassword" @click="submitUnlock">
                  Start unlock
                </button>
                <button class="btn btn-link" @click="backToActions">&larr; Back to actions</button>
              </div>
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
            <div class="result-actions">
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

      </div>
    </template>
  </div>
</template>

<style scoped>
.connected-page {
  max-width: 760px;
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

/* Header */
.connected-header { margin-bottom: 2rem; }
.connected-status-row {
  display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;
}
.connected-dot {
  width: 12px; height: 12px; border-radius: 50%;
  animation: pulse-dot 2s ease-in-out infinite;
}
@keyframes pulse-dot {
  0%, 100% { opacity: 1; } 50% { opacity: 0.5; }
}
.connected-mode-label {
  font-size: calc(0.8rem * var(--font-scale));
  font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;
}
.connected-title {
  font-size: calc(1.8rem * var(--font-scale));
  font-weight: 700; margin: 0.25rem 0 0.75rem;
}
.connected-meta {
  display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 0.75rem;
}
.meta-chip {
  font-size: calc(0.8rem * var(--font-scale));
  padding: 0.2rem 0.6rem; border-radius: 999px;
  background: var(--bg-card); border: 1px solid var(--border);
  color: var(--text-dim);
}
.meta-chip.mono { font-family: monospace; }
.meta-chip.locked { color: #f44336; border-color: #f44336; }
.meta-chip.unlocked { color: #4caf50; border-color: #4caf50; }
/* Device layers */
.device-layers {
  display: flex; flex-wrap: wrap; gap: 0.75rem;
  margin-bottom: 1rem;
}
.device-layer {
  display: flex; align-items: center; gap: 0.4rem;
  padding: 0.45rem 0.75rem;
  border-radius: 8px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  font-size: calc(0.82rem * var(--font-scale));
}
.layer-label {
  font-weight: 700;
  font-size: calc(0.68rem * var(--font-scale));
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-dim);
  padding-right: 0.3rem;
  border-right: 1px solid var(--border);
  margin-right: 0.1rem;
}
.layer-value {
  font-weight: 600;
  color: var(--text);
}
.layer-detail {
  color: var(--text-dim);
  font-size: calc(0.78rem * var(--font-scale));
}
.layer-detail.mono { font-family: monospace; }
.locked-text { color: #f44336; }
.unlocked-text { color: #4caf50; }

.connected-desc {
  font-size: calc(0.9rem * var(--font-scale));
  color: var(--text-dim); line-height: 1.5;
}

/* Banners */
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
.banner-inline { margin-top: 0.75rem; }

/* Sections */
.connected-section { margin-bottom: 2rem; }
.connected-section h2 {
  font-size: calc(1.1rem * var(--font-scale));
  font-weight: 600; margin-bottom: 0.75rem;
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
.text-dim { opacity: 0.6; font-size: 0.85em; }
.raw-info-details { margin-top: 0.25rem; }
.raw-info-summary {
  font-size: calc(0.8rem * var(--font-scale));
  color: var(--text-dim); cursor: pointer;
}
.device-info-pre {
  font-family: monospace; font-size: calc(0.8rem * var(--font-scale));
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 8px; padding: 1rem; overflow-x: auto;
  white-space: pre-wrap; color: var(--text-dim);
  margin-top: 0.5rem;
}

/* Action grid */
.action-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 0.75rem;
}
.action-card {
  display: flex; flex-direction: column; align-items: flex-start;
  padding: 1.25rem; border-radius: 10px;
  border: 1px solid var(--border); background: var(--bg-card);
  cursor: pointer; text-align: left;
  transition: all 0.15s ease;
}
.action-card:hover {
  border-color: var(--accent);
  background: color-mix(in srgb, var(--accent) 8%, var(--bg-card));
}
.action-primary {
  border-color: var(--accent);
  background: color-mix(in srgb, var(--accent) 5%, var(--bg-card));
}
.action-icon { font-size: 1.5rem; margin-bottom: 0.5rem; }
.action-label {
  font-weight: 600; font-size: calc(0.95rem * var(--font-scale));
  margin-bottom: 0.25rem;
}
.action-desc {
  font-size: calc(0.8rem * var(--font-scale)); color: var(--text-dim); line-height: 1.4;
}
.action-locked-notice {
  padding: 1.5rem; text-align: center; color: var(--text-dim);
  font-style: italic;
}

/* ROM picker */
.rom-picker h3 {
  font-size: calc(1rem * var(--font-scale)); margin-bottom: 0.75rem;
}
.rom-grid { display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 1rem; }
.rom-card {
  display: flex; justify-content: space-between; align-items: center;
  padding: 0.85rem 1rem; border-radius: 8px;
  border: 1px solid var(--border); background: var(--bg-card);
  cursor: pointer; transition: all 0.15s ease;
}
.rom-card:hover {
  border-color: var(--accent);
  background: color-mix(in srgb, var(--accent) 8%, var(--bg-card));
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
  border-radius: 10px; border: 1px solid var(--border);
}
.flash-result-ok { background: color-mix(in srgb, #4caf50 8%, var(--bg-card)); }
.flash-result-err { background: color-mix(in srgb, #f44336 8%, var(--bg-card)); }
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
</style>
