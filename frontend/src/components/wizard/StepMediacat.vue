<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import TerminalOutput from '@/components/shared/TerminalOutput.vue'

const { t } = useI18n()
const router = useRouter()
const { get, post } = useApi()

// --- Profiles ---
const profiles = ref([])
const selectedProfile = ref(null)

// --- Tools ---
const tools = ref(null)

// --- Block devices ---
const devices = ref([])
const devicesLoading = ref(false)
const selectedDevice = ref(null)

// --- Ventoy status ---
const ventoyStatus = ref(null)
const checkingVentoy = ref(false)

// --- Medicat source path ---
const medicatPath = ref('')

// --- Task state ---
const ventoyTaskId = ref(null)
const copyTaskId = ref(null)
const installingVentoy = ref(false)
const copyingFiles = ref(false)
const error = ref(null)

// --- Steps tracking ---
const ventoyInstalled = ref(false)

const selectedProfileData = computed(() => {
  if (!selectedProfile.value) return null
  return profiles.value.find(p => p.id === selectedProfile.value) || null
})

const minUsbBytes = computed(() => {
  if (!selectedProfileData.value) return 0
  return selectedProfileData.value.min_usb_gb * 1024 * 1024 * 1024
})

function formatSize(bytes) {
  if (!bytes) return ''
  const gb = bytes / 1024 / 1024 / 1024
  if (gb >= 1) return `${gb.toFixed(1)} GB`
  const mb = bytes / 1024 / 1024
  return `${mb.toFixed(0)} MB`
}

function deviceTooSmall(device) {
  if (!minUsbBytes.value || !device.size_bytes) return false
  return device.size_bytes < minUsbBytes.value
}

async function loadDevices() {
  devicesLoading.value = true
  const { ok, data } = await get('/api/blockdevices')
  devicesLoading.value = false
  if (ok && Array.isArray(data)) {
    devices.value = data
  }
}

async function selectDevice(device) {
  if (installingVentoy.value || copyingFiles.value) return
  if (deviceTooSmall(device)) return
  selectedDevice.value = device
  ventoyStatus.value = null
  ventoyInstalled.value = false
  await checkVentoy()
}

async function checkVentoy() {
  if (!selectedDevice.value) return
  checkingVentoy.value = true
  const { ok, data } = await post('/api/medicat/check-ventoy', {
    device: selectedDevice.value.path,
  })
  checkingVentoy.value = false
  if (ok) {
    ventoyStatus.value = data
    ventoyInstalled.value = data.installed
  }
}

async function installVentoy() {
  if (!selectedDevice.value) return
  installingVentoy.value = true
  ventoyTaskId.value = null
  error.value = null
  const { ok, data } = await post('/api/medicat/install-ventoy', {
    device: selectedDevice.value.path,
  })
  if (ok && data?.task_id) {
    ventoyTaskId.value = data.task_id
  } else {
    installingVentoy.value = false
    error.value = data?.error || 'Failed to start Ventoy installation.'
  }
}

function onVentoyDone(status) {
  installingVentoy.value = false
  if (status === 'done') {
    ventoyInstalled.value = true
  }
}

async function copyFiles() {
  if (!selectedDevice.value || !medicatPath.value.trim()) return
  copyingFiles.value = true
  copyTaskId.value = null
  error.value = null
  const { ok, data } = await post('/api/medicat/copy-files', {
    device: selectedDevice.value.path,
    medicat_path: medicatPath.value.trim(),
  })
  if (ok && data?.task_id) {
    copyTaskId.value = data.task_id
  } else {
    copyingFiles.value = false
    error.value = data?.error || 'Failed to start file copy.'
  }
}

function onCopyDone() {
  copyingFiles.value = false
}

onMounted(async () => {
  const [profilesRes, toolsRes] = await Promise.all([
    get('/api/medicat/profiles'),
    get('/api/medicat/tools'),
  ])
  if (profilesRes.ok && Array.isArray(profilesRes.data)) {
    profiles.value = profilesRes.data
    if (profiles.value.length > 0) {
      selectedProfile.value = profiles.value[0].id
    }
  }
  if (toolsRes.ok) {
    tools.value = toolsRes.data
  }
  await loadDevices()
})
</script>

<template>
  <h2 class="step-title">{{ t('step.medicat.title', 'Create Medicat USB') }}</h2>
  <p class="step-desc">
    {{ t('step.medicat.desc', 'Build a bootable Medicat USB drive for PC repair, diagnostics, and recovery. Medicat uses Ventoy as its boot manager.') }}
  </p>

  <!-- What is Medicat? -->
  <div class="info-box info-box--info">
    <strong>What is Medicat USB?</strong>
    Medicat USB is an all-in-one bootable toolkit for PC technicians. It includes
    Mini Windows 10/11 PE environments, antivirus rescue disks (Kaspersky, ESET,
    Malwarebytes), disk utilities (GParted, Clonezilla, DBAN), password recovery
    tools, hardware diagnostics, and boot repair utilities &mdash; all bootable from
    a single USB drive via the Ventoy boot manager.
  </div>

  <!-- Tool availability -->
  <div v-if="tools && !tools.ventoy" class="info-box info-box--warn">
    <strong>Ventoy not found.</strong>
    Medicat USB requires Ventoy to be installed on your system.
    Download it from
    <a href="https://ventoy.net" target="_blank" rel="noopener noreferrer">ventoy.net</a>
    and make sure <code>Ventoy2Disk.sh</code> or <code>ventoy</code> is on your PATH.
  </div>

  <!-- Step 1: Select profile -->
  <div class="form-group">
    <label class="form-label">Step 1: Select Medicat edition</label>
    <div class="goal-grid">
      <div
        v-for="profile in profiles"
        :key="profile.id"
        class="goal-card"
        :class="{ 'goal-card--selected': selectedProfile === profile.id }"
        role="button"
        tabindex="0"
        @click="selectedProfile = profile.id"
        @keydown.enter="selectedProfile = profile.id"
        @keydown.space.prevent="selectedProfile = profile.id"
      >
        <div class="goal-icon">&#x1F3E5;</div>
        <h3>{{ profile.label }}</h3>
        <p class="text-dim">{{ profile.notes }}</p>
        <p class="text-dim">Minimum USB size: {{ profile.min_usb_gb }} GB</p>
        <div v-if="selectedProfile === profile.id" class="goal-tag">Selected</div>
      </div>
    </div>
  </div>

  <!-- Step 2: Select USB drive -->
  <div class="form-group">
    <div class="devices-header">
      <label class="form-label">Step 2: Select USB drive</label>
      <button
        class="btn btn-link"
        :class="{ 'btn-loading': devicesLoading }"
        :disabled="devicesLoading || installingVentoy || copyingFiles"
        @click="loadDevices"
      >
        Refresh
      </button>
    </div>

    <p v-if="!devicesLoading && devices.length === 0" class="text-dim" style="font-size: 0.9rem; margin-top: 0.5rem;">
      No removable block devices found. Insert a USB drive and click Refresh.
    </p>

    <div class="device-grid">
      <div
        v-for="device in devices"
        :key="device.path"
        class="goal-card device-card"
        :class="{
          'device-card--selected': selectedDevice?.path === device.path,
          'device-card--system': device.is_system || deviceTooSmall(device),
        }"
        role="button"
        :tabindex="device.is_system || deviceTooSmall(device) ? -1 : 0"
        :aria-pressed="selectedDevice?.path === device.path"
        :aria-disabled="device.is_system || deviceTooSmall(device)"
        @click="!device.is_system && !deviceTooSmall(device) && selectDevice(device)"
        @keydown.enter="!device.is_system && !deviceTooSmall(device) && selectDevice(device)"
        @keydown.space.prevent="!device.is_system && !deviceTooSmall(device) && selectDevice(device)"
      >
        <div class="device-card__icon">&#x1F4BE;</div>
        <div class="device-card__info">
          <div class="device-card__name">{{ device.model || device.name }}</div>
          <div class="device-card__path text-dim">{{ device.path }}</div>
          <div class="device-card__size">{{ formatSize(device.size_bytes) || device.size }}</div>
        </div>
        <div class="device-card__badges">
          <span v-if="device.is_system" class="device-badge device-badge--danger">SYSTEM</span>
          <span v-if="deviceTooSmall(device)" class="device-badge device-badge--danger">TOO SMALL</span>
          <span v-if="device.mounted" class="device-badge device-badge--warn">Mounted</span>
        </div>
      </div>
    </div>

    <!-- Ventoy status for selected device -->
    <div v-if="selectedDevice && checkingVentoy" class="text-dim" style="margin-top: 0.75rem;">
      Checking for Ventoy...
    </div>
    <div v-if="selectedDevice && ventoyStatus && !checkingVentoy" style="margin-top: 0.75rem;">
      <div v-if="ventoyStatus.installed" class="info-box info-box--info">
        <strong>Ventoy is already installed</strong> on this drive. You can skip to copying Medicat files.
      </div>
      <div v-else class="info-box info-box--warn">
        <strong>Ventoy is not installed</strong> on this drive. Install it below before copying Medicat files.
        This will erase all data on the drive.
      </div>
    </div>
  </div>

  <!-- Step 3: Install Ventoy (if needed) -->
  <div v-if="selectedDevice && !ventoyInstalled" class="form-group">
    <label class="form-label">Step 3: Install Ventoy</label>
    <p class="step-desc">
      Ventoy formats the drive and creates a boot manager. After installation, you simply
      copy ISO/VHD files to the drive and Ventoy presents them as a boot menu.
    </p>

    <p v-if="error" class="warning-hint">{{ error }}</p>

    <div class="step-actions">
      <button
        class="btn btn-large btn-primary"
        :class="{ 'btn-loading': installingVentoy }"
        :disabled="installingVentoy || copyingFiles || !tools?.ventoy"
        @click="installVentoy"
      >
        <span class="btn-icon">&#x1F4BF;</span>
        <span>{{ installingVentoy ? 'Installing Ventoy...' : 'Install Ventoy on drive' }}</span>
      </button>
    </div>

    <TerminalOutput v-if="ventoyTaskId" :task-id="ventoyTaskId" @done="onVentoyDone" />
  </div>

  <!-- Step 4: Copy Medicat files -->
  <div v-if="selectedDevice && ventoyInstalled" class="form-group">
    <label class="form-label">{{ ventoyStatus?.installed ? 'Step 3' : 'Step 4' }}: Copy Medicat files</label>
    <p class="step-desc">
      Point to your downloaded Medicat files. This can be a directory containing ISOs and VHDs,
      or a single ISO file. Medicat is not redistributable &mdash; you must supply your own download.
    </p>

    <div class="form-group">
      <label for="medicat-path">Medicat files path</label>
      <input
        id="medicat-path"
        v-model="medicatPath"
        type="text"
        placeholder="/home/user/Downloads/Medicat"
        :disabled="copyingFiles"
      />
    </div>

    <p v-if="error" class="warning-hint">{{ error }}</p>

    <div class="step-actions">
      <button
        class="btn btn-large btn-primary"
        :class="{ 'btn-loading': copyingFiles }"
        :disabled="copyingFiles || !medicatPath.trim()"
        @click="copyFiles"
      >
        <span class="btn-icon">&#x1F4E6;</span>
        <span>{{ copyingFiles ? 'Copying files...' : 'Copy Medicat to USB' }}</span>
      </button>
    </div>

    <TerminalOutput v-if="copyTaskId" :task-id="copyTaskId" @done="onCopyDone" />
  </div>

  <!-- Navigation -->
  <div class="step-nav">
    <button
      class="btn btn-secondary"
      :disabled="installingVentoy || copyingFiles"
      @click="router.push('/wizard/identify')"
    >&larr; {{ t('nav.back', 'Back') }}</button>
  </div>
</template>

<style scoped>
.devices-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.devices-header label {
  display: inline;
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
  gap: 0.35rem;
  padding: 0.85rem 1rem;
  cursor: pointer;
  position: relative;
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

.device-card__icon {
  font-size: 1.5rem;
  line-height: 1;
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
  margin-top: 0.1rem;
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
  letter-spacing: 0.05em;
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
</style>
