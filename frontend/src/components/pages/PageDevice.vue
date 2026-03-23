<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useApi } from '@/composables/useApi'
import { useWizard } from '@/composables/useWizard'

const route = useRoute()
const router = useRouter()
const { get } = useApi()
const { setDevice, setCategory, setHardware } = useWizard()

const deviceType = computed(() => route.params.type)
const deviceId = computed(() => route.params.id)

const loading = ref(true)
const device = ref(null)
const osList = ref([])
const community = ref([])
const error = ref(null)

onMounted(async () => {
  await loadDevice()
})

async function loadDevice() {
  loading.value = true
  error.value = null

  if (deviceType.value === 'phone') {
    // Load device OS options
    const osResp = await get(`/api/devices/${deviceId.value}/os`)
    if (osResp.ok && osResp.data.device) {
      device.value = osResp.data.device
      osList.value = osResp.data.os_list || []
    } else {
      error.value = 'Device not found'
    }

    // Load community links
    const codename = device.value?.codename || deviceId.value
    const model = device.value?.model || ''
    const comResp = await get(`/api/community/${codename}?model=${encodeURIComponent(model)}`)
    if (comResp.ok) {
      community.value = comResp.data.links || []
    }
  } else if (deviceType.value === 'scooter') {
    const resp = await get('/api/scooters')
    if (resp.ok) {
      device.value = resp.data.find(s => s.id === deviceId.value)
      if (!device.value) error.value = 'Scooter not found'
    }
  } else if (deviceType.value === 'ebike') {
    const resp = await get('/api/ebikes')
    if (resp.ok) {
      device.value = resp.data.find(e => e.id === deviceId.value)
      if (!device.value) error.value = 'E-bike not found'
    }
  } else if (deviceType.value === 'microcontroller') {
    const resp = await get('/api/microcontrollers')
    if (resp.ok) {
      device.value = resp.data.find(b => b.id === deviceId.value)
      if (!device.value) error.value = 'Board not found'
    }
  } else if (deviceType.value === 't2') {
    const resp = await get('/api/t2/models')
    if (resp.ok) {
      device.value = resp.data.find(m => m.id === deviceId.value)
      if (!device.value) error.value = 'Model not found'
    }
  } else {
    error.value = 'Unknown device type'
  }

  loading.value = false
}

function goFlash() {
  // Set device info in wizard state before navigating
  if (device.value) {
    const d = device.value
    setDevice({
      id: d.id || deviceId.value,
      label: d.label || d.name || d.model || deviceId.value,
      model: d.model || '',
      codename: d.codename || '',
      brand: d.brand || '',
      display_name: d.label || d.name || d.model || deviceId.value,
      rom_url: d.rom_url || '',
      twrp_url: d.twrp_url || '',
      eos_url: d.eos_url || '',
      stock_url: d.stock_url || '',
      gapps_url: d.gapps_url || '',
    })
    setCategory(deviceType.value || 'phone')
    setHardware({ brand: d.brand || '', model: d.model || '', serial: '' })
  }

  const routes = {
    phone: '/wizard/software',
    scooter: '/wizard/scooter',
    ebike: '/wizard/ebike',
    microcontroller: '/wizard/microcontroller',
    t2: '/wizard/t2',
  }
  router.push(routes[deviceType.value] || '/wizard/identify')
}

const typeLabels = {
  phone: 'Phone / Tablet',
  scooter: 'Electric Scooter',
  ebike: 'E-Bike',
  microcontroller: 'Microcontroller',
  t2: 'Apple T2 Mac',
}
</script>

<template>
  <div class="device-page">
    <button class="btn btn-link back-link" @click="router.push('/wizard/identify')">&larr; Back to search</button>

    <div v-if="loading" class="device-loading">
      <span class="spinner-small"></span> Loading device info...
    </div>

    <div v-else-if="error" class="device-error">
      <p>{{ error }}</p>
      <button class="btn btn-primary" @click="router.push('/wizard/identify')">Back to search</button>
    </div>

    <div v-else-if="device" class="device-detail">
      <!-- Header -->
      <div class="device-header">
        <span class="device-type-badge">{{ typeLabels[deviceType] || deviceType }}</span>
        <h1 class="device-title">{{ device.label || device.id }}</h1>
        <div class="device-meta-row">
          <span v-if="device.model" class="device-meta-item">{{ device.model }}</span>
          <span v-if="device.codename" class="device-meta-item">{{ device.codename }}</span>
          <span v-if="device.brand" class="device-meta-item">{{ device.brand }}</span>
          <span v-if="device.arch" class="device-meta-item">{{ device.arch }}</span>
          <span v-if="device.controller" class="device-meta-item">{{ device.controller }}</span>
          <span v-if="device.board_id" class="device-meta-item">{{ device.board_id }}</span>
        </div>
      </div>

      <!-- Quick action -->
      <div class="device-actions">
        <button class="btn btn-large btn-primary" @click="goFlash">
          Flash this device &rarr;
        </button>
      </div>

      <!-- Available OS (phones) -->
      <section v-if="osList.length" class="device-section">
        <h2>Available operating systems</h2>
        <div class="os-grid">
          <div v-for="os in osList" :key="os.id" class="os-card">
            <div class="os-card-header">
              <strong>{{ os.name }}</strong>
              <span v-if="os.type" class="os-type-tag">{{ os.type }}</span>
            </div>
            <p class="os-desc">{{ os.desc }}</p>
            <div v-if="os.tags && os.tags.length" class="os-tags">
              <span v-for="tag in os.tags" :key="tag" class="os-tag">{{ tag }}</span>
            </div>
            <a v-if="os.url" :href="os.url" target="_blank" rel="noopener" class="btn btn-link">Download &nearr;</a>
          </div>
        </div>
      </section>

      <!-- Device-specific info -->
      <section v-if="device.flash_method || device.flash_tool || device.protocol" class="device-section">
        <h2>Technical details</h2>
        <table class="device-table">
          <tr v-if="device.flash_method"><td>Flash method</td><td>{{ device.flash_method }}</td></tr>
          <tr v-if="device.flash_tool"><td>Flash tool</td><td>{{ device.flash_tool }}</td></tr>
          <tr v-if="device.protocol"><td>Protocol</td><td>{{ device.protocol }}</td></tr>
          <tr v-if="device.bootloader"><td>Bootloader</td><td>{{ device.bootloader }}</td></tr>
          <tr v-if="device.usb_vid"><td>USB VID:PID</td><td>{{ device.usb_vid }}:{{ device.usb_pid }}</td></tr>
          <tr v-if="device.cfw_url"><td>Custom firmware</td><td><a :href="device.cfw_url" target="_blank" rel="noopener">{{ device.cfw_url }}</a></td></tr>
          <tr v-if="device.fw_url"><td>Firmware project</td><td><a :href="device.fw_url" target="_blank" rel="noopener">{{ device.fw_project || device.fw_url }}</a></td></tr>
          <tr v-if="device.bridge_os_url"><td>BridgeOS</td><td><a :href="device.bridge_os_url" target="_blank" rel="noopener">Download</a></td></tr>
          <tr v-if="device.support_status"><td>Support</td><td>{{ device.support_status }}</td></tr>
          <tr v-if="device.shfw_supported"><td>SHFW</td><td>{{ device.shfw_supported }}</td></tr>
        </table>
      </section>

      <!-- Notes -->
      <section v-if="device.notes" class="device-section">
        <h2>Notes</h2>
        <p class="device-notes">{{ device.notes }}</p>
      </section>

      <!-- Community links (phones) -->
      <section v-if="community.length" class="device-section">
        <h2>Community &amp; resources</h2>
        <div class="community-grid">
          <a
            v-for="link in community"
            :key="link.id"
            :href="link.device_url || link.url"
            target="_blank"
            rel="noopener"
            class="community-card"
          >
            <strong>{{ link.name }}</strong>
            <span class="community-desc">{{ link.desc }}</span>
          </a>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.device-page {
  max-width: 960px;
  margin: 0 auto;
  padding: 0 1rem;
}

.back-link {
  margin-bottom: 1rem;
}

.device-loading {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 2rem 0;
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
@keyframes spin { to { transform: rotate(360deg); } }

.device-error {
  padding: 2rem 0;
  text-align: center;
  color: var(--text-dim);
}

/* Header */
.device-header {
  margin-bottom: 1.5rem;
}

.device-type-badge {
  display: inline-block;
  font-size: calc(0.75rem * var(--font-scale));
  padding: 0.2rem 0.6rem;
  border-radius: var(--radius-pill);
  background: rgba(54, 216, 183, 0.15);
  color: var(--accent);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.5rem;
}

.device-title {
  font-size: calc(1.8rem * var(--font-scale));
  font-weight: 700;
  margin: 0.25rem 0 0.5rem;
}

.device-meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.device-meta-item {
  font-size: calc(0.85rem * var(--font-scale));
  color: var(--text-dim);
  padding: 0.15rem 0.5rem;
  border-radius: var(--radius-pill);
  background: var(--bg-card);
  border: 1px solid var(--border);
}

/* Actions */
.device-actions {
  margin-bottom: 2rem;
}

/* Sections */
.device-section {
  margin-bottom: 2rem;
}

.device-section h2 {
  font-size: calc(1.1rem * var(--font-scale));
  font-weight: 600;
  margin-bottom: 0.75rem;
  color: var(--text);
}

/* OS grid */
.os-grid {
  display: grid;
  gap: 0.75rem;
}

.os-card {
  padding: 1rem 1.25rem;
  border-radius: var(--radius-card);
  border: 1px solid var(--border);
  background: var(--bg-card);
}

.os-card-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.35rem;
}

.os-type-tag {
  font-size: calc(0.7rem * var(--font-scale));
  padding: 0.1rem 0.4rem;
  border-radius: var(--radius-pill);
  background: var(--bg-hover);
  color: var(--text-dim);
}

.os-desc {
  font-size: calc(0.85rem * var(--font-scale));
  color: var(--text-dim);
  margin: 0 0 0.5rem;
}

.os-tags {
  display: flex;
  gap: 0.3rem;
  margin-bottom: 0.5rem;
}

.os-tag {
  font-size: calc(0.7rem * var(--font-scale));
  padding: 0.1rem 0.4rem;
  border-radius: var(--radius-pill);
  background: rgba(54, 216, 183, 0.15);
  color: var(--accent);
  font-weight: 600;
}

/* Tech table */
.device-table {
  width: 100%;
  border-collapse: collapse;
}

.device-table td {
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid var(--border);
  font-size: calc(0.9rem * var(--font-scale));
}

.device-table td:first-child {
  color: var(--text-dim);
  width: 40%;
  font-weight: 500;
}

.device-table a {
  color: var(--accent);
  word-break: break-all;
}

.device-notes {
  color: var(--text-dim);
  font-size: calc(0.9rem * var(--font-scale));
  line-height: 1.5;
}

/* Community */
.community-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 0.75rem;
}

.community-card {
  display: block;
  padding: 0.85rem 1rem;
  border-radius: var(--radius-card);
  border: 1px solid var(--border);
  background: var(--bg-card);
  text-decoration: none;
  color: var(--text);
  transition: border-color var(--transition-fast);
}

.community-card:hover {
  border-color: var(--accent);
}

.community-desc {
  display: block;
  font-size: calc(0.8rem * var(--font-scale));
  color: var(--text-dim);
  margin-top: 0.2rem;
}
</style>
