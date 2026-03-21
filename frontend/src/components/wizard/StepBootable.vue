<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import TerminalOutput from '@/components/shared/TerminalOutput.vue'

const { t } = useI18n()
const router = useRouter()
const { get, post } = useApi()

// --- Block device list ---
const devices = ref([])
const devicesLoading = ref(false)
const devicesError = ref(null)
const selectedDevice = ref(null)

async function loadDevices() {
  devicesLoading.value = true
  devicesError.value = null
  const { ok, data } = await get('/api/blockdevices')
  devicesLoading.value = false
  if (ok && Array.isArray(data)) {
    devices.value = data
  } else {
    devicesError.value = data?.error || t('bootable.error.devices', 'Could not load block devices.')
  }
}

onMounted(loadDevices)

function selectDevice(device) {
  if (writing.value) return
  selectedDevice.value = device
}

// --- Form fields ---
const imagePath = ref('')
const blockSize = ref('4M')
const skipVerify = ref(false)

const blockSizes = ['512', '1M', '4M', '8M', '16M', '32M', '64M']

// --- Write operation ---
const writing = ref(false)
const writeError = ref(null)
const taskId = ref(null)

function formatSize(bytes) {
  if (!bytes) return ''
  const gb = bytes / 1024 / 1024 / 1024
  if (gb >= 1) return `${gb.toFixed(1)} GB`
  const mb = bytes / 1024 / 1024
  return `${mb.toFixed(0)} MB`
}

async function writeToDevice() {
  if (!imagePath.value.trim()) {
    writeError.value = t('bootable.error.no_image', 'Please enter an image path.')
    return
  }
  if (!selectedDevice.value) {
    writeError.value = t('bootable.error.no_device', 'Please select a target device.')
    return
  }

  writeError.value = null
  writing.value = true
  taskId.value = null

  const { ok, data } = await post('/api/bootable', {
    image_path: imagePath.value.trim(),
    target_device: selectedDevice.value.path,
    block_size: blockSize.value,
    skip_verify: skipVerify.value,
  })

  if (ok && data?.task_id) {
    taskId.value = data.task_id
  } else {
    writing.value = false
    writeError.value = data?.error || t('bootable.error.start', 'Failed to start write operation.')
  }
}

function onTaskDone(status) {
  writing.value = false
}
</script>

<template>
  <h2 class="step-title">{{ t('step.bootable.title', 'Write image to USB / SD card') }}</h2>
  <p class="step-desc">
    {{ t('step.bootable.desc', 'Select an ISO or IMG file and the target device, then write.') }}
  </p>

  <!-- Image path input -->
  <div class="form-group">
    <label for="image-path">{{ t('bootable.label.image', 'Image path (.iso / .img)') }}</label>
    <input
      id="image-path"
      v-model="imagePath"
      type="text"
      :placeholder="t('bootable.placeholder.image', '/home/user/downloads/system.iso')"
      :disabled="writing"
    />
  </div>

  <!-- Block device selector -->
  <div class="form-group">
    <div class="devices-header">
      <label>{{ t('bootable.label.device', 'Target device') }}</label>
      <button
        class="btn btn-link"
        :class="{ 'btn-loading': devicesLoading }"
        :disabled="devicesLoading || writing"
        @click="loadDevices"
      >
        {{ t('bootable.btn.refresh', 'Refresh') }}
      </button>
    </div>

    <p v-if="devicesError" class="warning-hint">{{ devicesError }}</p>

    <p v-if="!devicesLoading && devices.length === 0 && !devicesError" class="text-dim" style="font-size: 0.9rem; margin-top: 0.5rem;">
      {{ t('bootable.devices.empty', 'No removable block devices found. Insert a USB drive or SD card and refresh.') }}
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
        :tabindex="writing || device.is_system ? -1 : 0"
        :aria-pressed="selectedDevice?.path === device.path"
        :aria-disabled="device.is_system || writing"
        @click="!device.is_system && selectDevice(device)"
        @keydown.enter="!device.is_system && selectDevice(device)"
        @keydown.space.prevent="!device.is_system && selectDevice(device)"
      >
        <div class="device-card__icon">
          <span v-if="device.path.includes('sd') || device.path.includes('mmcblk')">&#x1F4BE;</span>
          <span v-else>&#x1F5B4;</span>
        </div>
        <div class="device-card__info">
          <div class="device-card__name">{{ device.name || device.path }}</div>
          <div class="device-card__path text-dim">{{ device.path }}</div>
          <div v-if="device.model" class="device-card__model text-dim">{{ device.model }}</div>
          <div class="device-card__size">{{ formatSize(device.size) }}</div>
        </div>
        <div class="device-card__badges">
          <span v-if="device.is_system" class="device-badge device-badge--danger">
            {{ t('bootable.badge.system', 'SYSTEM') }}
          </span>
          <span v-if="device.large_drive" class="device-badge device-badge--warn">
            {{ t('bootable.badge.large', '>128 GB') }}
          </span>
          <span v-if="device.mounted" class="device-badge device-badge--warn">
            {{ t('bootable.badge.mounted', 'Mounted') }}
          </span>
        </div>
      </div>
    </div>

    <!-- Warnings for the selected device -->
    <div v-if="selectedDevice?.large_drive" class="detect-box not-found" style="margin-top: 0.75rem;">
      <strong>{{ t('bootable.warn.large.title', 'Large drive selected') }}</strong><br>
      {{ t('bootable.warn.large.body', 'This device is larger than 128 GB. Make sure this is the correct target — writing will overwrite all data.') }}
    </div>
    <div v-if="selectedDevice?.mounted" class="detect-box not-found" style="margin-top: 0.75rem;">
      <strong>{{ t('bootable.warn.mounted.title', 'Device is mounted') }}</strong><br>
      {{ t('bootable.warn.mounted.body', 'This device is currently mounted. Unmount it before writing, or data may be corrupted.') }}
    </div>
  </div>

  <!-- Block size selector -->
  <div class="form-group">
    <label for="block-size">{{ t('bootable.label.block_size', 'Block size') }}</label>
    <select id="block-size" v-model="blockSize" :disabled="writing">
      <option v-for="bs in blockSizes" :key="bs" :value="bs">{{ bs }}</option>
    </select>
  </div>

  <!-- Skip verification checkbox -->
  <div class="checkbox-group" style="margin-bottom: 1rem;">
    <label>
      <input v-model="skipVerify" type="checkbox" :disabled="writing" />
      {{ t('bootable.label.skip_verify', 'Skip verification after write') }}
    </label>
  </div>

  <!-- Write error -->
  <p v-if="writeError" class="warning-hint" style="margin-bottom: 0.75rem;">{{ writeError }}</p>

  <!-- Write button -->
  <div class="step-actions">
    <button
      class="btn btn-large btn-primary"
      :class="{ 'btn-loading': writing }"
      :disabled="writing || !imagePath.trim() || !selectedDevice || selectedDevice.is_system"
      @click="writeToDevice"
    >
      <span class="btn-icon">&#x1F4BE;</span>
      <span>{{ writing ? t('bootable.btn.writing', 'Writing...') : t('bootable.btn.write', 'Write to device') }}</span>
    </button>
  </div>

  <!-- Terminal output -->
  <TerminalOutput :task-id="taskId" @done="onTaskDone" />

  <!-- Back navigation -->
  <div class="step-nav">
    <button class="btn btn-secondary" :disabled="writing" @click="router.push('/wizard/goal')">&larr; {{ t('nav.back', 'Back') }}</button>
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
  /* Override form-group label block display inside flex parent */
  display: inline;
}

.device-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 0.75rem;
  margin-top: 0.5rem;
}

/* Extend goal-card for device cards */
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

.device-card__path,
.device-card__model {
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
