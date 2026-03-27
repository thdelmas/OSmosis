<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useApi } from '@/composables/useApi'
import TerminalOutput from '@/components/shared/TerminalOutput.vue'

const router = useRouter()
const route = useRoute()
const { get, post } = useApi()

// --- Steps ---
const step = ref('os')  // os → config → device → flash

// --- Profile & OS selection ---
const profile = ref(null)
const profileLoading = ref(true)
const selectedOs = ref(null)

const deviceId = computed(() => route.params.deviceId || 'rpi-3b')

async function loadProfile() {
  profileLoading.value = true
  const { ok, data } = await get(`/api/profiles/${deviceId.value}`)
  profileLoading.value = false
  if (ok && data) {
    profile.value = data
  }
}

onMounted(loadProfile)

function selectOs(fw) {
  selectedOs.value = fw
  step.value = 'config'
}

// --- Configuration ---
const config = ref({
  hostname: 'raspberrypi',
  username: '',
  password: '',
  ssh_enabled: true,
  ssh_pubkey: '',
  wifi_ssid: '',
  wifi_password: '',
  wifi_country: 'FR',
  timezone: 'Europe/Paris',
  keymap: 'fr',
})

const showAdvanced = ref(false)

function nextToDevice() {
  if (!config.value.username || !config.value.password) {
    configError.value = 'Username and password are required (no default pi user since 2022).'
    return
  }
  configError.value = null
  step.value = 'device'
  loadDevices()
}

const configError = ref(null)

// Try to load SSH public key
onMounted(async () => {
  const { ok, data } = await get('/api/system/ssh-pubkey')
  if (ok && data?.pubkey) {
    config.value.ssh_pubkey = data.pubkey
  }
})

// --- Block device selection ---
const devices = ref([])
const devicesLoading = ref(false)
const selectedDevice = ref(null)

async function loadDevices() {
  devicesLoading.value = true
  const { ok, data } = await get('/api/blockdevices')
  devicesLoading.value = false
  if (ok && Array.isArray(data)) {
    devices.value = data
  }
}

function selectDevice(device) {
  if (device.is_system) return
  selectedDevice.value = device
}

function formatSize(sizeStr) {
  return sizeStr || ''
}

// --- Flash ---
const flashing = ref(false)
const flashError = ref(null)
const taskId = ref(null)

async function startFlash() {
  if (!selectedDevice.value || !selectedOs.value) return

  flashError.value = null
  flashing.value = true
  step.value = 'flash'

  const payload = {
    image_url: selectedOs.value.url,
    target_device: selectedDevice.value.path,
    config: config.value,
  }

  const { ok, data } = await post('/api/sbc/flash', payload)
  if (ok && data?.task_id) {
    taskId.value = data.task_id
  } else {
    flashing.value = false
    flashError.value = data?.error || 'Failed to start flash operation.'
  }
}

function onTaskDone(status) {
  flashing.value = false
}
</script>

<template>
  <div class="sbc-setup">

    <!-- Step 1: Select OS -->
    <template v-if="step === 'os'">
      <h2 class="step-title">Choose an operating system</h2>
      <p class="step-desc" v-if="profile">
        {{ profile.device?.name || deviceId }} &mdash; select which OS to install.
      </p>
      <p v-if="profileLoading" class="text-dim">Loading device profile...</p>

      <div v-if="profile?.firmware" class="os-grid">
        <div
          v-for="fw in profile.firmware"
          :key="fw.id"
          class="goal-card os-card"
          :class="{ 'os-card--selected': selectedOs?.id === fw.id }"
          role="button"
          tabindex="0"
          @click="selectOs(fw)"
          @keydown.enter="selectOs(fw)"
        >
          <div class="os-card__name">{{ fw.name }}</div>
          <div v-if="fw.version" class="os-card__version text-dim">v{{ fw.version }}</div>
          <div v-if="fw.tags" class="os-card__tags">
            <span v-for="tag in fw.tags" :key="tag" class="os-tag">{{ tag }}</span>
          </div>
        </div>
      </div>

      <div class="step-nav">
        <button class="btn btn-secondary" @click="router.push('/wizard/identify')">&larr; Back</button>
      </div>
    </template>

    <!-- Step 2: Configure -->
    <template v-if="step === 'config'">
      <h2 class="step-title">Configure first boot</h2>
      <p class="step-desc">
        Set up {{ selectedOs?.name }} so the Pi boots ready to use.
        <strong>Username and password are required</strong> (no default user since 2022).
      </p>

      <div class="config-form">
        <div class="form-group">
          <label for="cfg-hostname">Hostname</label>
          <input id="cfg-hostname" v-model="config.hostname" type="text" placeholder="raspberrypi" />
        </div>

        <div class="form-row">
          <div class="form-group">
            <label for="cfg-user">Username *</label>
            <input id="cfg-user" v-model="config.username" type="text" placeholder="mia" />
          </div>
          <div class="form-group">
            <label for="cfg-pass">Password *</label>
            <input id="cfg-pass" v-model="config.password" type="password" placeholder="password" />
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label for="cfg-ssid">WiFi SSID</label>
            <input id="cfg-ssid" v-model="config.wifi_ssid" type="text" placeholder="MyNetwork" />
          </div>
          <div class="form-group">
            <label for="cfg-wifipass">WiFi password</label>
            <input id="cfg-wifipass" v-model="config.wifi_password" type="password" placeholder="secret" />
          </div>
        </div>

        <div class="checkbox-group">
          <label>
            <input v-model="config.ssh_enabled" type="checkbox" />
            Enable SSH
          </label>
        </div>

        <div class="checkbox-group" style="margin-bottom: 0.75rem;">
          <label>
            <input v-model="showAdvanced" type="checkbox" />
            Show advanced settings
          </label>
        </div>

        <template v-if="showAdvanced">
          <div class="form-row">
            <div class="form-group">
              <label for="cfg-tz">Timezone</label>
              <input id="cfg-tz" v-model="config.timezone" type="text" placeholder="Europe/Paris" />
            </div>
            <div class="form-group">
              <label for="cfg-keymap">Keyboard layout</label>
              <input id="cfg-keymap" v-model="config.keymap" type="text" placeholder="fr" />
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label for="cfg-country">WiFi country code</label>
              <input id="cfg-country" v-model="config.wifi_country" type="text" placeholder="FR" maxlength="2" />
            </div>
          </div>

          <div class="form-group" v-if="config.ssh_enabled">
            <label for="cfg-pubkey">SSH public key (optional)</label>
            <textarea id="cfg-pubkey" v-model="config.ssh_pubkey" rows="2" placeholder="ssh-ed25519 AAAA..." style="font-family: monospace; font-size: 0.8rem;" />
          </div>
        </template>

        <p v-if="configError" class="warning-hint">{{ configError }}</p>
      </div>

      <div class="step-actions">
        <button class="btn btn-large btn-primary" @click="nextToDevice">
          Next: Select SD card &rarr;
        </button>
      </div>

      <div class="step-nav">
        <button class="btn btn-secondary" @click="step = 'os'">&larr; Back to OS selection</button>
      </div>
    </template>

    <!-- Step 3: Select SD card -->
    <template v-if="step === 'device'">
      <h2 class="step-title">Select SD card</h2>
      <p class="step-desc">
        Choose the SD card to write <strong>{{ selectedOs?.name }}</strong> to.
        All data on the card will be erased.
      </p>

      <div class="devices-header">
        <span></span>
        <button
          class="btn btn-link"
          :class="{ 'btn-loading': devicesLoading }"
          :disabled="devicesLoading"
          @click="loadDevices"
        >
          Refresh
        </button>
      </div>

      <p v-if="!devicesLoading && devices.length === 0" class="text-dim" style="font-size: 0.9rem;">
        No removable devices found. Insert an SD card and click Refresh.
      </p>

      <div class="device-grid">
        <div
          v-for="device in devices"
          :key="device.path"
          class="goal-card device-card"
          :class="{
            'device-card--selected': selectedDevice?.path === device.path,
            'device-card--system': device.is_system,
          }"
          role="button"
          :tabindex="device.is_system ? -1 : 0"
          @click="selectDevice(device)"
          @keydown.enter="selectDevice(device)"
        >
          <div class="device-card__name">{{ device.model || device.name }}</div>
          <div class="device-card__path text-dim">{{ device.path }}</div>
          <div class="device-card__size">{{ formatSize(device.size) }}</div>
          <div class="device-card__badges">
            <span v-if="device.is_system" class="device-badge device-badge--danger">SYSTEM</span>
            <span v-if="device.large_drive" class="device-badge device-badge--warn">&gt;128 GB</span>
            <span v-if="device.mounted" class="device-badge device-badge--warn">Mounted</span>
          </div>
        </div>
      </div>

      <!-- Summary before flash -->
      <div v-if="selectedDevice" class="flash-summary">
        <h3>Ready to flash</h3>
        <table class="summary-table">
          <tr><td>OS</td><td><strong>{{ selectedOs?.name }}</strong></td></tr>
          <tr><td>Target</td><td><strong>{{ selectedDevice.path }}</strong> ({{ selectedDevice.size }})</td></tr>
          <tr><td>Hostname</td><td>{{ config.hostname }}</td></tr>
          <tr><td>User</td><td>{{ config.username }}</td></tr>
          <tr v-if="config.wifi_ssid"><td>WiFi</td><td>{{ config.wifi_ssid }}</td></tr>
          <tr><td>SSH</td><td>{{ config.ssh_enabled ? 'Enabled' : 'Disabled' }}</td></tr>
        </table>
      </div>

      <p v-if="flashError" class="warning-hint">{{ flashError }}</p>

      <div class="step-actions">
        <button
          class="btn btn-large btn-primary"
          :disabled="!selectedDevice || selectedDevice.is_system"
          @click="startFlash"
        >
          Flash SD card
        </button>
      </div>

      <div class="step-nav">
        <button class="btn btn-secondary" @click="step = 'config'">&larr; Back to config</button>
      </div>
    </template>

    <!-- Step 4: Flashing -->
    <template v-if="step === 'flash'">
      <h2 class="step-title">Flashing {{ selectedOs?.name }}</h2>
      <p class="step-desc">
        Writing to {{ selectedDevice?.path }}. Do not remove the SD card.
      </p>

      <TerminalOutput :task-id="taskId" @done="onTaskDone" />

      <div v-if="!flashing && taskId" class="step-nav" style="margin-top: 1rem;">
        <button class="btn btn-secondary" @click="router.push('/')">Done</button>
      </div>
    </template>

  </div>
</template>

<style scoped>
.os-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 0.75rem;
  margin: 1rem 0;
}

.os-card {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  padding: 0.85rem 1rem;
  cursor: pointer;
  text-align: left;
}

.os-card--selected {
  border-color: var(--accent);
  background: var(--bg-hover);
  box-shadow: 0 0 0 2px var(--accent);
}

.os-card__name {
  font-weight: 600;
  font-size: calc(0.95rem * var(--font-scale));
}

.os-card__version {
  font-size: calc(0.8rem * var(--font-scale));
}

.os-card__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
  margin-top: 0.25rem;
}

.os-tag {
  display: inline-block;
  padding: 0.1rem 0.4rem;
  border-radius: var(--radius-pill);
  font-size: calc(0.7rem * var(--font-scale));
  background: var(--bg-hover);
  border: 1px solid var(--border);
  color: var(--text-dim);
}

.config-form {
  margin: 1rem 0;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}

.devices-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.device-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 0.75rem;
  margin-top: 0.5rem;
}

.device-card {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  padding: 0.85rem 1rem;
  cursor: pointer;
  text-align: left;
}

.device-card--selected {
  border-color: var(--accent);
  background: var(--bg-hover);
  box-shadow: 0 0 0 2px var(--accent);
}

.device-card--system {
  opacity: 0.5;
  cursor: not-allowed;
}

.device-card__name {
  font-weight: 600;
  font-size: calc(0.95rem * var(--font-scale));
}

.device-card__path {
  font-size: calc(0.78rem * var(--font-scale));
  font-family: 'Courier New', Courier, monospace;
}

.device-card__size {
  font-size: calc(0.85rem * var(--font-scale));
  font-weight: 600;
  color: var(--accent);
}

.device-card__badges {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
  margin-top: 0.25rem;
}

.device-badge {
  display: inline-block;
  padding: 0.1rem 0.45rem;
  border-radius: var(--radius-pill);
  font-size: calc(0.7rem * var(--font-scale));
  font-weight: 700;
  text-transform: uppercase;
}

.device-badge--warn {
  background: rgba(252, 197, 58, 0.15);
  color: var(--yellow);
  border: 1px solid var(--yellow);
}

.device-badge--danger {
  background: rgba(255, 133, 133, 0.15);
  color: var(--red);
  border: 1px solid var(--red);
}

.flash-summary {
  margin: 1.25rem 0;
  padding: 1rem;
  background: var(--bg-hover);
  border: 1px solid var(--border);
  border-radius: var(--radius);
}

.flash-summary h3 {
  margin: 0 0 0.5rem 0;
  font-size: calc(1rem * var(--font-scale));
}

.summary-table {
  width: 100%;
  border-collapse: collapse;
}

.summary-table td {
  padding: 0.25rem 0.5rem;
  font-size: calc(0.88rem * var(--font-scale));
}

.summary-table td:first-child {
  color: var(--text-dim);
  width: 80px;
}
</style>
