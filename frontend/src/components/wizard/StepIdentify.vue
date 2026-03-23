<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { useWizard } from '@/composables/useWizard'

const { t } = useI18n()
const router = useRouter()
const { get, post } = useApi()
const { state, setCategory, setDevice, setHardware, getRecentDevices } = useWizard()

const recentDevices = ref(getRecentDevices())

const categories = [
  { id: 'phone', icon: '\u{1F4F1}', label: 'Phone / Tablet', desc: 'Android phones, tablets, and e-readers' },
  { id: 'computer', icon: '\u{1F4BB}', label: 'Computer / SBC', desc: 'Desktops, laptops, Raspberry Pi, and other single-board computers' },
  { id: 'network', icon: '\u{1F5A7}', label: 'Router / NAS', desc: 'Home routers, access points, and network storage' },
  { id: 'car', icon: '\u{1F697}', label: 'Car / Vehicle', desc: 'Head units, OBD adapters, and vehicle electronics' },
  { id: 'marine', icon: '\u26F5', label: 'Boat / Marine', desc: 'Marine electronics, chartplotters, and navigation' },
  { id: 'iot', icon: '\u{1F4E1}', label: 'IoT / Wearable', desc: 'Smart home devices, smartwatches, and sensors' },
  { id: 'console', icon: '\u{1F3AE}', label: 'Game console / Media', desc: 'Consoles, handhelds, streaming sticks, and e-readers' },
  { id: 'gps', icon: '\u{1F4CD}', label: 'GPS / Navigation', desc: 'GPS units, drones, and flight controllers' },
  { id: 'scooter', icon: '\u{1F6F4}', label: 'Electric scooter', desc: 'Kick scooters and personal electric vehicles' },
  { id: 'ebike', icon: '\u{1F6B2}', label: 'Electric bike', desc: 'E-bike controllers, displays, and motor firmware' },
  { id: 'microcontroller', icon: '\u{1F9F0}', label: 'Microcontroller', desc: 'Arduino, ESP32, STM32, Pi Pico, and dev boards' },
]

const brandSuggestions = {
  phone: ['Samsung', 'Google', 'Xiaomi', 'OnePlus', 'Fairphone', 'Pine64', 'Motorola', 'Sony', 'LG', 'Huawei', 'Nothing', 'ASUS'],
  computer: ['Raspberry Pi', 'NVIDIA Jetson', 'Intel', 'AMD', 'Pine64', 'Orange Pi', 'Banana Pi', 'BeagleBone', 'Libre Computer'],
  network: ['TP-Link', 'Netgear', 'Linksys', 'ASUS', 'MikroTik', 'Ubiquiti', 'Synology', 'QNAP', 'GL.iNet'],
  car: ['Android Auto', 'Raspberry Pi', 'Arduino', 'OBDLink', 'Carlinkit'],
  marine: ['Raspberry Pi', 'OpenPlotter', 'Victron', 'Actisense', 'Digital Yacht'],
  iot: ['Espressif (ESP32)', 'Raspberry Pi Pico', 'Arduino', 'Sonoff', 'Shelly', 'Pine64 PineTime', 'Tuya'],
  console: ['Nintendo', 'Valve (Steam Deck)', 'Amazon (Fire TV)', 'Google (Chromecast)', 'Amazon (Kindle)', 'Anbernic', 'Miyoo'],
  gps: ['Garmin', 'TomTom', 'DJI', 'Matek', 'Holybro'],
  scooter: ['Ninebot', 'Xiaomi', 'Segway', 'Vsett', 'Kaabo', 'Dualtron'],
  ebike: ['Bosch', 'Shimano', 'Bafang', 'Yamaha', 'Specialized (Turbo)', 'Giant', 'Trek', 'Rad Power Bikes', 'VanMoof'],
  microcontroller: ['Arduino', 'Raspberry Pi', 'Espressif (ESP32)', 'STMicro (STM32)', 'PJRC (Teensy)', 'Adafruit', 'Seeed Studio', 'SparkFun', 'BBC (micro:bit)'],
}

// --- Quick search (top bar, searches all devices) ---
const quickQuery = ref('')
const quickSearching = ref(false)
const quickResults = ref([])
const quickSearched = ref(false)
const searchInputRef = ref(null)

const typeIcons = {
  phone: '\u{1F4F1}',
  scooter: '\u{1F6F4}',
  ebike: '\u{1F6B2}',
  microcontroller: '\u{1F9F0}',
  t2: '\u{1F4BB}',
}

let quickTimeout = null
watch(quickQuery, (val) => {
  if (quickTimeout) clearTimeout(quickTimeout)
  if (!val.trim()) {
    quickResults.value = []
    quickSearched.value = false
    return
  }
  quickTimeout = setTimeout(quickSearch, 300)
})

async function quickSearch() {
  const q = quickQuery.value.trim()
  if (!q) return
  quickSearching.value = true
  quickSearched.value = false

  const { ok, data } = await get(`/api/search?q=${encodeURIComponent(q)}`)
  quickSearching.value = false
  quickSearched.value = true
  if (ok && Array.isArray(data)) {
    quickResults.value = data
  }
}

function quickPick(dev) {
  router.push(`/device/${dev.type}/${dev.id}`)
}

// --- Auto-detect on page load ---
const autoDetecting = ref(false)
const autoDetected = ref(null)
const autoDetectError = ref(null)
const waitingForReboot = ref(false)

onMounted(() => {
  autoDetect()
})

async function autoDetect() {
  autoDetecting.value = true
  autoDetected.value = null
  autoDetectError.value = null

  // Try ADB first (phones)
  const { ok, data } = await get('/api/detect')
  if (ok && data && !data.error) {
    const adbState = data.adb_state || 'device'
    autoDetected.value = {
      source: (adbState === 'sideload' || adbState === 'recovery') ? adbState : 'adb',
      display_name: data.display_name || data.model || 'Android device',
      brand: data.brand || '',
      model: data.model || '',
      codename: data.codename || '',
      match: data.match || null,
      multiple: data.multiple || false,
      devices: data.devices || null,
      adb_state: adbState,
      hint: data.hint || '',
      serial: data.serial || '',
    }
    autoDetecting.value = false
    return
  }

  // Device in Download Mode (Samsung/Heimdall)
  if (data?.error === 'download_mode') {
    autoDetected.value = {
      source: 'download_mode',
      display_name: data.usb_name || 'Device (Download Mode)',
      brand: data.brand || '',
      model: '',
      codename: '',
      match: null,
      hint: data.hint,
    }
    autoDetecting.value = false
    return
  }

  // Device connected but unauthorized (common in recovery mode)
  if (data?.error === 'unauthorized') {
    autoDetected.value = {
      source: 'unauthorized',
      display_name: 'Device connected (authorization needed)',
      brand: '',
      model: '',
      codename: '',
      match: null,
      hint: data.hint,
      serial: data.serial,
    }
    autoDetecting.value = false
    return
  }

  // Try microcontroller detection
  const mcu = await get('/api/microcontrollers/detect')
  if (mcu.ok && mcu.data.devices && mcu.data.devices.length) {
    const first = mcu.data.devices[0]
    autoDetected.value = {
      source: 'mcu',
      display_name: first.match?.label || first.product || first.brand || 'Microcontroller',
      port: first.port || first.mount || '',
      match: first.match,
      devices: mcu.data.devices,
    }
    autoDetecting.value = false
    return
  }

  autoDetecting.value = false
  autoDetectError.value = 'none'
}

const rebootTaskId = ref(null)
const rebootAttempts = ref(0)

async function rebootNormalAndDetect() {
  autoDetected.value = null
  autoDetecting.value = true

  const { ok, data } = await post('/api/reboot-normal')
  if (ok && data?.task_id) {
    rebootTaskId.value = data.task_id
    const poll = setInterval(async () => {
      const t = await get('/api/tasks')
      if (!t.ok) return
      const task = t.data?.find(x => x.id === data.task_id)
      if (!task || task.status === 'running') return
      clearInterval(poll)
      rebootTaskId.value = null
      if (task.status === 'done') {
        waitingForReboot.value = true
        setTimeout(() => { waitingForReboot.value = false; autoDetect() }, 2000)
      } else {
        autoDetecting.value = false
        autoDetectError.value = 'reboot_failed'
      }
    }, 2000)
  } else {
    autoDetecting.value = false
  }
}

async function rebootAndRedetect() {
  autoDetected.value = null
  autoDetecting.value = true
  rebootTaskId.value = null
  rebootAttempts.value++

  const { ok, data } = await post('/api/reboot-from-download')
  if (ok && data?.task_id) {
    rebootTaskId.value = data.task_id
    const poll = setInterval(async () => {
      const t = await get(`/api/tasks`)
      if (!t.ok) return
      const task = t.data?.find(x => x.id === data.task_id)
      if (!task || task.status === 'running') return
      clearInterval(poll)
      rebootTaskId.value = null
      if (task.status === 'done') {
        // Wait for device to settle, then re-detect
        waitingForReboot.value = true
        setTimeout(() => { waitingForReboot.value = false; autoDetect() }, 5000)
      } else {
        autoDetecting.value = false
        autoDetectError.value = 'stale_session'
      }
    }, 2000)
  } else {
    autoDetecting.value = false
    autoDetectError.value = 'none'
  }
}

function selectRecentDevice(dev) {
  setDevice({
    id: dev.id,
    label: dev.label,
    model: dev.model,
    codename: dev.codename,
    brand: dev.brand,
    display_name: dev.label,
  })
  setCategory('phone')
  setHardware({ brand: dev.brand || '', model: dev.model || '', serial: '' })
  router.push('/wizard/software')
}

const selectedMultiDevice = ref(null)

function useSelectedMultiDevice() {
  if (selectedMultiDevice.value === null || !autoDetected.value?.devices) return
  const dev = autoDetected.value.devices[selectedMultiDevice.value]
  const device = dev.match
    ? { ...dev.match, display_name: dev.display_name || dev.model, brand: dev.brand }
    : { custom: true, model: dev.model, codename: dev.codename, label: dev.display_name || dev.model, display_name: dev.display_name || dev.model, brand: dev.brand }
  setDevice(device)
  setCategory('phone')
  setHardware({ brand: dev.brand || '', model: dev.model || '', serial: dev.serial || '' })
  router.push('/wizard/software')
}

function useDetected() {
  if (!autoDetected.value) return
  const d = autoDetected.value

  if (d.source === 'adb') {
    const dev = d.match
      ? { ...d.match, display_name: d.display_name, brand: d.brand }
      : { custom: true, model: d.model, codename: d.codename, label: d.display_name, display_name: d.display_name, brand: d.brand }
    setDevice(dev)
    setCategory('phone')
    setHardware({ brand: d.brand || '', model: d.model, serial: '' })
    router.push('/wizard/software')
  } else if (d.source === 'download_mode') {
    // In Download Mode we can't query ADB for the exact model.
    // Pre-fill the search with brand and focus the input.
    selectedCategory.value = 'phone'
    setCategory('phone')
    brand.value = d.brand || ''
    setHardware({ brand: d.brand || '', model: '', serial: '' })
    quickQuery.value = d.brand || ''
    nextTick(() => {
      searchInputRef.value?.focus()
      searchInputRef.value?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    })
  } else if (d.source === 'mcu') {
    setDevice({ port: d.port, label: d.display_name, match: d.match })
    setCategory('microcontroller')
    router.push('/wizard/microcontroller')
  }
}

// --- Category-based flow (existing) ---
const selectedCategory = ref(state.category || null)
const brand = ref(state.brand || '')
const model = ref(state.model || '')
const serial = ref(state.serial || '')

const searching = ref(false)
const results = ref([])
const hasSearched = ref(false)
const selectedDevice = ref(null)
const useCustom = ref(false)

const currentBrands = computed(() => brandSuggestions[selectedCategory.value] || [])
const canSearch = computed(() => selectedCategory.value && (brand.value || model.value || serial.value))
const canProceed = computed(() => selectedDevice.value !== null || useCustom.value)

function pickCategory(cat) {
  selectedCategory.value = cat
  brand.value = ''
  model.value = ''
  serial.value = ''
  results.value = []
  hasSearched.value = false
  selectedDevice.value = null
  useCustom.value = false
}

function pickBrand(b) {
  brand.value = b
  selectedDevice.value = null
  useCustom.value = false
  hasSearched.value = false
}

let searchTimeout = null
function scheduleSearch() {
  selectedDevice.value = null
  useCustom.value = false
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => { if (canSearch.value) search() }, 400)
}

watch([brand, model, serial], scheduleSearch)

async function search() {
  if (!canSearch.value) return
  searching.value = true
  hasSearched.value = false
  results.value = []

  const params = new URLSearchParams()
  if (selectedCategory.value) params.set('category', selectedCategory.value)
  if (brand.value) params.set('brand', brand.value)
  if (model.value) params.set('model', model.value)
  if (serial.value) params.set('serial', serial.value)

  const { ok, data } = await get(`/api/devices/search?${params}`)
  searching.value = false
  hasSearched.value = true

  if (ok && Array.isArray(data)) {
    results.value = data
  }
}

function selectDevice(dev) {
  selectedDevice.value = dev
  useCustom.value = false
}

function selectCustom() {
  useCustom.value = true
  selectedDevice.value = null
}

function proceed() {
  setCategory(selectedCategory.value)
  setHardware({ brand: brand.value, model: model.value, serial: serial.value })

  if (selectedDevice.value) {
    setDevice(selectedDevice.value)
  } else if (useCustom.value) {
    setDevice({
      custom: true,
      brand: brand.value,
      model: model.value,
      serial: serial.value,
      label: [brand.value, model.value].filter(Boolean).join(' ') || 'Custom device',
    })
  }

  router.push('/wizard/software')
}
</script>

<template>
  <h2 class="step-title">{{ t('step.identify.title', 'What device do you have?') }}</h2>

  <!-- Auto-detect banner -->
  <div class="detect-banner" :class="{ 'detect-found': autoDetected, 'detect-scanning': autoDetecting }">
    <div v-if="autoDetecting" class="detect-content">
      <span class="spinner-small"></span>
      <span v-if="waitingForReboot">Waiting for your device to restart... This can take up to 30 seconds.</span>
      <span v-else>Scanning for connected devices...</span>
    </div>
    <div v-else-if="autoDetected && autoDetected.source === 'download_mode'" class="detect-content detect-content-wrap">
      <span class="detect-icon" aria-hidden="true">&#x26A0;&#xFE0F;</span>
      <div class="detect-info">
        <strong>{{ autoDetected.brand || 'Device' }} in Download Mode</strong>
        <span class="detect-meta"> &mdash; can't auto-detect model in this mode</span>
      </div>

      <div v-if="rebootAttempts > 0" class="install-guide-box detect-guide-box">
        <p><strong>Device is stuck in Download Mode.</strong> It needs a manual restart:</p>
        <ol class="detect-steps">
          <li><strong>Unplug the USB cable</strong></li>
          <li v-if="autoDetected.brand === 'Samsung'"><strong>Remove the battery</strong> (if removable), wait 10 seconds, reinsert it. If the battery is not removable, hold <strong>Power + Vol Down for 10+ seconds</strong> to force restart.</li>
          <li v-else>Hold <strong>Power for 15+ seconds</strong> (or <strong>Power + Vol Down</strong>) until the screen goes black</li>
          <li>Let the device boot normally <strong>without USB</strong></li>
          <li>Once you see the home screen, plug USB back in</li>
        </ol>
        <div class="detect-btn-row">
          <button class="btn btn-primary btn-small" @click="autoDetect">I've rebooted — detect again</button>
          <button class="btn btn-secondary btn-small" @click="useDetected">Search for my model instead</button>
        </div>
      </div>

      <div v-else class="detect-btn-row detect-full-row">
        <button class="btn btn-primary btn-small" @click="rebootAndRedetect">Reboot to detect automatically</button>
        <button class="btn btn-secondary btn-small" @click="useDetected">Search for my model</button>
      </div>
    </div>
    <div v-else-if="autoDetected && (autoDetected.source === 'sideload' || autoDetected.source === 'recovery') && !autoDetected.model" class="detect-content detect-content-wrap">
      <span class="detect-icon" aria-hidden="true">&#x1F4F1;</span>
      <div class="detect-info">
        <strong>Device in {{ autoDetected.source === 'sideload' ? 'sideload' : 'recovery' }} mode</strong>
        <span class="detect-meta"> &mdash; can't identify model in this mode</span>
      </div>
      <div class="detect-detail-block">
        <p>To detect your device model, it needs to boot into its normal OS first. You can also search manually.</p>
        <div class="detect-btn-row">
          <button class="btn btn-primary btn-small" @click="rebootNormalAndDetect">Reboot to identify</button>
          <button class="btn btn-secondary btn-small" @click="useDetected">Search manually</button>
        </div>
      </div>
    </div>
    <div v-else-if="autoDetected && autoDetected.source === 'unauthorized'" class="detect-content detect-content-wrap">
      <span class="detect-icon" aria-hidden="true">&#x1F513;</span>
      <div class="detect-info">
        <strong>Device connected but not authorized</strong>
      </div>
      <div class="detect-detail-block">
        <p>Your device is connected but ADB access isn't authorized. Try:</p>
        <ol class="detect-steps">
          <li>Check your device screen for an <strong>authorization prompt</strong> and tap Allow</li>
          <li>If in recovery mode: look for <strong>ADB Sideload</strong> or <strong>Enable ADB</strong> option</li>
          <li>If the device just booted: wait a moment and try again</li>
        </ol>
        <div class="detect-btn-row">
          <button class="btn btn-primary btn-small" @click="autoDetect">Retry detection</button>
          <button class="btn btn-secondary btn-small" @click="useDetected">Search for my model</button>
        </div>
      </div>
    </div>
    <div v-else-if="autoDetected && autoDetected.multiple && autoDetected.devices && autoDetected.devices.length > 1" class="detect-content detect-content-wrap">
      <span class="detect-icon" aria-hidden="true">&#x1F50C;</span>
      <div class="detect-info">
        <strong>{{ autoDetected.devices.length }} devices detected</strong>
        <span class="detect-meta"> &mdash; select the one you want to work with</span>
      </div>
      <div class="detect-multi-list">
        <button
          v-for="(dev, i) in autoDetected.devices"
          :key="dev.serial || dev.codename || i"
          class="detect-multi-card"
          :class="{ selected: selectedMultiDevice === i }"
          @click="selectedMultiDevice = i"
        >
          <div class="detect-multi-name">
            <strong>{{ dev.display_name || dev.model || dev.friendly_name || 'Device ' + (i + 1) }}</strong>
            <span v-if="dev.codename" class="detect-meta"> &middot; {{ dev.codename }}</span>
          </div>
          <div v-if="dev.serial" class="detect-multi-serial">Serial: {{ dev.serial }}</div>
        </button>
      </div>
      <button
        class="btn btn-primary btn-small"
        :disabled="selectedMultiDevice === null"
        @click="useSelectedMultiDevice"
      >Use selected device</button>
    </div>
    <div v-else-if="autoDetected" class="detect-content">
      <span class="detect-icon" aria-hidden="true">&#x2705;</span>
      <div class="detect-info">
        <strong>{{ autoDetected.display_name }}</strong>
        <span v-if="autoDetected.codename" class="detect-meta"> &middot; {{ autoDetected.codename }}</span>
      </div>
      <button class="btn btn-primary btn-small" @click="useDetected">Use this device</button>
    </div>
    <div v-else-if="autoDetectError === 'stale_session'" class="detect-content detect-none detect-content-wrap">
      <div>
        <strong>Device stuck in Download Mode</strong> — the session has gone stale.
      </div>
      <ol class="detect-steps detect-steps-small">
        <li>Unplug the USB cable</li>
        <li>Hold <strong>Power for 10+ seconds</strong> until the screen goes black</li>
        <li>Press Power to boot normally, then plug USB back in</li>
      </ol>
      <button class="btn btn-link btn-small" @click="autoDetect">Retry detection</button>
    </div>
    <div v-else class="detect-content detect-none detect-content-wrap">
      <div class="detect-row">
        <span class="detect-icon" aria-hidden="true">&#x1F50C;</span>
        <span>No device detected via USB.</span>
        <button class="btn btn-link btn-small" @click="autoDetect">Retry</button>
      </div>
      <div class="detect-troubleshoot">
        <details>
          <summary>Troubleshooting tips</summary>
          <ul class="detect-steps">
            <li>Make sure the USB cable supports data (not charge-only)</li>
            <li>Try a different USB port (avoid hubs)</li>
            <li>On Android: enable <strong>USB Debugging</strong> in Developer Options</li>
            <li>If your device was in <strong>sideload mode</strong>: that session has expired. Go back into your recovery and restart ADB Sideload</li>
            <li>If in recovery: look for an <strong>ADB</strong> or <strong>Sideload</strong> option in the menu</li>
          </ul>
        </details>
      </div>
    </div>
  </div>

  <!-- Recent devices -->
  <div v-if="recentDevices.length" class="recent-devices">
    <h4 class="recent-title">Recent devices</h4>
    <div class="recent-list">
      <button
        v-for="dev in recentDevices"
        :key="dev.id || dev.model"
        class="recent-device-btn"
        @click="selectRecentDevice(dev)"
      >
        <strong>{{ dev.label }}</strong>
        <span v-if="dev.model && dev.model !== dev.label" class="detect-meta"> &middot; {{ dev.model }}</span>
      </button>
    </div>
  </div>

  <!-- Quick search bar -->
  <div class="quick-search">
    <input
      ref="searchInputRef"
      v-model="quickQuery"
      type="text"
      class="quick-search-input"
      placeholder="Search any device... (e.g. Galaxy S24, Pixel 9, Raspberry Pi 5)"
    >
    <span v-if="quickSearching" class="spinner-small quick-search-spinner"></span>
  </div>

  <!-- Quick search results -->
  <div v-if="quickSearched && quickQuery.trim()" class="quick-results">
    <div v-if="quickResults.length" class="quick-results-header">
      <span class="quick-results-count">{{ quickResults.length }} result{{ quickResults.length === 1 ? '' : 's' }}</span>
      <button class="btn btn-link btn-small" @click="searchInputRef?.focus(); searchInputRef?.scrollIntoView({ behavior: 'smooth', block: 'center' })">Edit search</button>
    </div>
    <div v-if="quickResults.length" class="quick-results-grid">
      <button
        v-for="dev in quickResults"
        :key="dev.type + '-' + dev.id"
        class="quick-result-card"
        @click="quickPick(dev)"
      >
        <div class="quick-result-top">
          <span class="quick-type-icon">{{ typeIcons[dev.type] || '\u{1F4E6}' }}</span>
          <span v-if="dev.brand" class="quick-result-brand">{{ dev.brand }}</span>
        </div>
        <div class="quick-result-name">{{ dev.label }}</div>
        <div v-if="dev.subtitle" class="quick-result-meta">{{ dev.subtitle }}</div>
        <div class="quick-result-tags">
          <span class="identify-tag identify-tag-type">{{ dev.type }}</span>
          <span v-if="dev.has_rom" class="identify-tag">ROM</span>
          <span v-if="dev.has_eos" class="identify-tag">/e/OS</span>
          <span v-if="dev.has_twrp" class="identify-tag">TWRP</span>
        </div>
      </button>
    </div>
    <p v-else class="quick-no-results">No devices found. Try browsing by category below.</p>
  </div>

  <div v-if="!quickQuery.trim()" class="browse-divider">
    <span>or browse by category</span>
  </div>

  <!-- Category selection -->
  <div v-if="!quickQuery.trim()">
  <label class="identify-section-label">What kind of device is it?</label>
  <div class="identify-categories">
    <button
      v-for="cat in categories"
      :key="cat.id"
      class="identify-chip"
      :class="{ selected: selectedCategory === cat.id }"
      @click="pickCategory(cat.id)"
    >
      <span class="identify-chip-icon">{{ cat.icon }}</span>
      <span class="identify-chip-text">
        <span class="identify-chip-label">{{ cat.label }}</span>
        <span v-if="cat.desc" class="identify-chip-desc">{{ cat.desc }}</span>
      </span>
    </button>
  </div>

  <!-- Hardware details -->
  <transition name="fade">
    <div v-if="selectedCategory" class="identify-details">
      <div class="form-group">
        <label>Who made it?</label>
        <div v-if="currentBrands.length" class="identify-brand-chips">
          <button
            v-for="b in currentBrands"
            :key="b"
            class="identify-brand-chip"
            :class="{ selected: brand === b }"
            @click="pickBrand(b)"
          >{{ b }}</button>
        </div>
        <input
          v-model="brand"
          type="text"
          :placeholder="t('step.identify.brand_placeholder', 'e.g. Samsung, Raspberry Pi, Ninebot')"
        >
      </div>

      <div class="form-group">
        <label>What model is it?</label>
        <input
          v-model="model"
          type="text"
          :placeholder="t('step.identify.model_placeholder', 'e.g. Galaxy S24, Pi 5, Max G30')"
        >
      </div>

      <div class="form-group">
        <label>Serial number <span class="text-dim">(optional - skip if you're not sure)</span></label>
        <input
          v-model="serial"
          type="text"
          :placeholder="t('step.identify.serial_placeholder', 'You can leave this empty if you don\'t know it')"
        >
      </div>

      <!-- Search results -->
      <div v-if="searching" class="identify-searching">
        <span class="spinner-small"></span> Searching devices...
        <div class="skeleton-list" aria-hidden="true">
          <div class="skeleton-card" v-for="n in 3" :key="n">
            <div class="skeleton-line skeleton-line-wide"></div>
            <div class="skeleton-line skeleton-line-narrow"></div>
          </div>
        </div>
      </div>

      <div v-else-if="hasSearched" class="identify-results">
        <label class="identify-section-label">
          {{ results.length ? 'Select your device' : 'No matching devices found' }}
        </label>

        <div v-if="results.length" class="identify-device-list">
          <button
            v-for="dev in results"
            :key="dev.id"
            class="identify-device-card"
            :class="{ selected: selectedDevice && selectedDevice.id === dev.id }"
            @click="selectDevice(dev)"
          >
            <div class="identify-device-name">{{ dev.label }}</div>
            <div class="identify-device-meta">
              <span v-if="dev.model">{{ dev.model }}</span>
              <span v-if="dev.codename"> &middot; {{ dev.codename }}</span>
            </div>
            <div v-if="dev.rom_url || dev.eos_url" class="identify-device-tags">
              <span v-if="dev.rom_url" class="identify-tag">ROM</span>
              <span v-if="dev.eos_url" class="identify-tag">/e/OS</span>
              <span v-if="dev.twrp_url" class="identify-tag">TWRP</span>
            </div>
          </button>
        </div>

        <!-- Custom hardware option -->
        <button
          class="identify-device-card identify-custom-card"
          :class="{ selected: useCustom }"
          @click="selectCustom"
        >
          <div class="identify-device-name">I don't see my device here</div>
          <div class="identify-device-meta">
            That's okay! You can continue and set things up yourself in the next steps.
          </div>
        </button>
      </div>

      <!-- Custom-only path when no search input yet -->
      <div v-else-if="selectedCategory && !canSearch" class="identify-results">
        <button
          class="identify-device-card identify-custom-card"
          :class="{ selected: useCustom }"
          @click="selectCustom"
        >
          <div class="identify-device-name">Skip this step</div>
          <div class="identify-device-meta">
            I'll set up the details myself later.
          </div>
        </button>
      </div>
    </div>
  </transition>

  <div class="step-actions">
    <button
      class="btn btn-large btn-primary"
      :disabled="!canProceed"
      @click="proceed"
    >
      Continue &rarr;
    </button>
  </div>

  <div class="step-skip">
    <router-link to="/wizard/category" class="btn btn-link">I want to build my own operating system</router-link>
  </div>
  </div>
</template>

<style scoped>
/* Auto-detect banner */
.detect-banner {
  padding: 0.75rem 1rem;
  border-radius: var(--radius-card);
  border: 1px solid var(--border);
  background: var(--bg-card);
  margin-bottom: 1rem;
}

.detect-banner.detect-found {
  border-color: var(--accent);
  background: rgba(54, 216, 183, 0.08);
}

.detect-content {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.detect-icon {
  font-size: 1.2em;
}

.detect-info {
  flex: 1;
}

.detect-meta {
  color: var(--text-dim);
  font-size: calc(0.85rem * var(--font-scale));
}

.detect-none {
  color: var(--text-dim);
}

.detect-content-wrap {
  flex-wrap: wrap;
  gap: 0.5rem;
}

.detect-guide-box {
  width: 100%;
  margin-top: 0.5rem;
  font-size: calc(0.9rem * var(--font-scale));
}

.detect-steps {
  margin: 0.5rem 0;
  padding-left: 1.5rem;
}

.detect-steps-small {
  font-size: calc(0.9rem * var(--font-scale));
}

.detect-btn-row {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.detect-full-row {
  width: 100%;
  margin-top: 0.25rem;
}

.detect-detail-block {
  width: 100%;
  font-size: calc(0.9rem * var(--font-scale));
  margin-top: 0.25rem;
}

.detect-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.detect-troubleshoot {
  width: 100%;
  font-size: calc(0.85rem * var(--font-scale));
  color: var(--text-dim);
  margin-top: 0.25rem;
}

.detect-troubleshoot summary {
  cursor: pointer;
}

/* Multi-device picker */
.detect-multi-list {
  width: 100%;
  display: grid;
  gap: 0.5rem;
  margin: 0.25rem 0;
}

.detect-multi-card {
  display: block;
  width: 100%;
  text-align: left;
  padding: 0.75rem 1rem;
  border-radius: var(--radius-card);
  border: 2px solid var(--border);
  background: var(--bg-card);
  color: var(--text);
  cursor: pointer;
  transition: all var(--transition-fast);
  min-height: 48px;
}

.detect-multi-card:hover {
  border-color: var(--accent);
  background: var(--bg-hover);
}

.detect-multi-card.selected {
  border-color: var(--accent);
  background: var(--bg-hover);
  box-shadow: inset 3px 0 0 var(--accent);
}

.detect-multi-serial {
  font-size: calc(0.8rem * var(--font-scale));
  color: var(--text-dim);
  margin-top: 0.15rem;
  font-family: monospace;
}

/* Quick search */
.quick-search {
  position: relative;
  margin-bottom: 1rem;
}

.quick-search-input {
  width: 100%;
  padding: 0.85rem 1.1rem;
  font-size: calc(1.05rem * var(--font-scale));
  border-radius: var(--radius-pill);
  border: 2px solid var(--border);
  background: var(--bg-card);
  color: var(--text);
  transition: border-color var(--transition-fast);
}

.quick-search-input:focus {
  outline: none;
  border-color: var(--accent);
}

.quick-search-input::placeholder {
  color: var(--text-dim);
}

.quick-search-spinner {
  position: absolute;
  right: 1rem;
  top: 50%;
  transform: translateY(-50%);
}

.quick-results {
  margin-bottom: 1.5rem;
}

.quick-results-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.quick-results-count {
  font-size: calc(0.85rem * var(--font-scale));
  color: var(--text-dim);
  font-weight: 500;
}

.quick-results-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 0.75rem;
}

.quick-result-card {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  padding: 0.85rem 1rem;
  border-radius: var(--radius-card);
  border: 2px solid var(--border);
  background: var(--bg-card);
  color: var(--text);
  cursor: pointer;
  text-align: left;
  transition: all var(--transition-fast);
}

.quick-result-card:hover {
  background: var(--bg-hover);
  border-color: var(--accent);
}

.quick-result-top {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.quick-type-icon {
  font-size: 1.3em;
  flex-shrink: 0;
}

.quick-result-brand {
  font-size: calc(0.7rem * var(--font-scale));
  color: var(--accent);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.quick-result-body {
  flex: 1;
  min-width: 0;
}

.quick-result-name {
  font-weight: 600;
  font-size: calc(0.95rem * var(--font-scale));
  line-height: 1.3;
}

.quick-result-meta {
  font-size: calc(0.8rem * var(--font-scale));
  color: var(--text-dim);
}

.quick-no-results {
  color: var(--text-dim);
  padding: 0.5rem 0;
}

.quick-type-icon {
  margin-right: 0.3rem;
}

.quick-result-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
  margin-top: auto;
}

.quick-result-tags .identify-tag {
  font-size: calc(0.65rem * var(--font-scale));
  padding: 0.1rem 0.4rem;
}

.identify-tag-type {
  background: rgba(100, 150, 255, 0.15);
  color: #6496ff;
}

.browse-divider {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin: 1rem 0;
  color: var(--text-dim);
  font-size: calc(0.85rem * var(--font-scale));
}

.browse-divider::before,
.browse-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border);
}

.btn-small {
  padding: 0.35rem 0.8rem;
  font-size: calc(0.85rem * var(--font-scale));
}

.identify-section-label {
  display: block;
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: var(--text);
  font-size: calc(0.95rem * var(--font-scale));
}

.identify-categories {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
}

.identify-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.65rem 1.1rem;
  border-radius: var(--radius-pill);
  border: 2px solid var(--border);
  background: var(--bg-card);
  color: var(--text);
  cursor: pointer;
  font-size: calc(1rem * var(--font-scale));
  transition: all var(--transition-fast);
  min-height: 48px;
}

.identify-chip:hover {
  background: var(--bg-hover);
  border-color: var(--accent);
}

.identify-chip.selected {
  background: var(--accent);
  color: #000;
  border-color: var(--accent);
  font-weight: 600;
}

.identify-chip-icon {
  font-size: 1.3em;
}

.identify-details {
  margin-top: 0.5rem;
}

.identify-brand-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-bottom: 0.5rem;
}

.identify-brand-chip {
  padding: 0.45rem 0.9rem;
  border-radius: var(--radius-pill);
  border: 1px solid var(--border);
  background: var(--bg);
  color: var(--text-dim);
  cursor: pointer;
  font-size: calc(0.9rem * var(--font-scale));
  transition: all var(--transition-fast);
  min-height: 40px;
}

.identify-brand-chip:hover {
  color: var(--text);
  border-color: var(--accent);
}

.identify-brand-chip.selected {
  background: var(--bg-hover);
  color: var(--accent);
  border-color: var(--accent);
  font-weight: 600;
}

/* Search status */
.identify-searching {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem 0;
  color: var(--text-dim);
}

.spinner-small {
  display: inline-block;
  width: 1rem;
  height: 1rem;
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Device result list */
.identify-results {
  margin-top: 1rem;
}

.identify-device-list {
  display: grid;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.identify-device-card {
  display: block;
  width: 100%;
  text-align: left;
  padding: 1rem 1.25rem;
  border-radius: var(--radius-card);
  border: 2px solid var(--border);
  background: var(--bg-card);
  color: var(--text);
  cursor: pointer;
  transition: all var(--transition-fast);
  min-height: 56px;
}

.identify-device-card:hover {
  background: var(--bg-hover);
  border-color: var(--accent);
}

.identify-device-card.selected {
  border-color: var(--accent);
  background: var(--bg-hover);
  box-shadow: inset 3px 0 0 var(--accent);
}

.identify-device-name {
  font-weight: 600;
  font-size: calc(1rem * var(--font-scale));
}

.identify-device-meta {
  font-size: calc(0.85rem * var(--font-scale));
  color: var(--text-dim);
  margin-top: 0.15rem;
}

.identify-device-tags {
  display: flex;
  gap: 0.3rem;
  margin-top: 0.4rem;
}

.identify-tag {
  font-size: calc(0.7rem * var(--font-scale));
  padding: 0.15rem 0.5rem;
  border-radius: var(--radius-pill);
  background: rgba(54, 216, 183, 0.15);
  color: var(--accent);
  font-weight: 600;
}

.identify-custom-card {
  border-style: dashed;
}

/* Recent devices */
.recent-devices {
  margin: 0.75rem 0;
}
.recent-title {
  font-size: 0.85rem;
  color: var(--text-dim, #888);
  margin: 0 0 0.5rem 0;
  font-weight: 500;
}
.recent-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.recent-device-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.4rem 0.75rem;
  border-radius: var(--radius-sm, 6px);
  border: 1px solid var(--border, #333);
  background: var(--surface, #1a1a2e);
  color: var(--text, #eee);
  cursor: pointer;
  font-size: 0.85rem;
  transition: border-color 0.15s, background 0.15s;
}
.recent-device-btn:hover {
  border-color: var(--accent, #36d8b7);
  background: rgba(54, 216, 183, 0.08);
}

/* Loading skeleton */
.skeleton-list {
  display: grid;
  gap: 0.75rem;
  margin-top: 0.75rem;
}
.skeleton-card {
  padding: 0.85rem 1rem;
  border-radius: var(--radius-btn, 8px);
  border: 1px solid var(--border);
  background: var(--bg-card);
}
.skeleton-line {
  height: 0.85rem;
  border-radius: 4px;
  background: linear-gradient(90deg, var(--border) 25%, var(--bg-hover) 50%, var(--border) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}
.skeleton-line-wide {
  width: 70%;
  margin-bottom: 0.5rem;
}
.skeleton-line-narrow {
  width: 40%;
}
@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* Transitions */
.fade-enter-active, .fade-leave-active {
  transition: opacity var(--transition-med);
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
</style>
