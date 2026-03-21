<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import ModalOverlay from '@/components/shared/ModalOverlay.vue'
import TerminalOutput from '@/components/shared/TerminalOutput.vue'
import { useApi } from '@/composables/useApi'

const { t } = useI18n()
const router = useRouter()
const { get, post } = useApi()

const activeModal = ref(null)
const taskId = ref(null)

// Preflight state
const preflightType = ref('phone')
const preflightResult = ref(null)
const preflightLoading = ref(false)

// Registry state
const registryEntries = ref([])
const registryLoading = ref(false)

// Recovery guides state
const recoveryGuides = ref([])
const activeGuide = ref(null)
const guidesLoading = ref(false)

// Flash stock form
const fwZipPath = ref('')
// Flash recovery form
const recoveryImgPath = ref('')
// Sideload form
const sideloadZipPath = ref('')
const sideloadLabel = ref('Custom ROM')

const sections = [
  {
    title: 'Custom Firmware Builder',
    cards: [
      { action: 'cfw-builder', icon: '\u{1F527}', title: 'CFW Builder', desc: 'Build custom scooter firmware: speed, power, braking, cruise control, and more' },
    ],
  },
  {
    title: 'Flashing',
    cards: [
      { action: 'flash-stock', icon: '\u{1F4E6}', title: 'Stock Firmware', desc: 'Restore stock Samsung firmware from a ZIP via Heimdall' },
      { action: 'flash-recovery', icon: '\u{1F6E0}', title: 'Custom Recovery', desc: 'Flash TWRP or other custom recovery .img via Heimdall' },
      { action: 'sideload', icon: '\u{1F4E5}', title: 'ADB Sideload', desc: 'Sideload a custom ROM, GApps, or other ZIP via adb' },
    ],
  },
  {
    title: 'Device Management',
    cards: [
      { action: 'presets', icon: '\u{1F4CB}', title: 'Device Presets', desc: 'Download firmware, TWRP, ROM, and GApps from devices.cfg presets' },
      { action: 'detect', icon: '\u{1F50D}', title: 'Auto-Detect', desc: 'Detect connected device via ADB and match to a preset' },
      { action: 'backup', icon: '\u{1F4BE}', title: 'Backup Partitions', desc: 'Back up boot, recovery, EFS and other partitions' },
    ],
  },
  {
    title: 'Workflow & Tools',
    cards: [
      { action: 'workflow', icon: '\u26A1', title: 'Full Workflow', desc: 'Guided session: stock restore + TWRP + ROM + GApps in one go' },
      { action: 'magisk', icon: '\u{1F9EA}', title: 'Magisk Patch', desc: 'Patch boot.img with Magisk for root access' },
      { action: 'ipfs', icon: '\u{1F310}', title: 'IPFS Storage', desc: 'Store and retrieve ROMs on IPFS for decentralized sharing' },
      { action: 'bootable', icon: '\u{1F4BF}', title: 'Bootable Device', desc: 'Write an ISO or IMG to a USB drive or SD card' },
      { action: 'pxe', icon: '\u{1F5A7}', title: 'PXE Boot Server', desc: 'Set up a network boot server for PXE installs' },
      { action: 'os-builder', icon: '\u{1F3D7}', title: 'OS Builder', desc: 'Build a custom OS image from Debian, Ubuntu, Arch, or Alpine' },
    ],
  },
  {
    title: 'Safety & Recovery',
    cards: [
      { action: 'preflight', icon: '\u2705', title: 'Pre-Flight Check', desc: 'Run safety checklist before flashing' },
      { action: 'registry', icon: '\u{1F4DC}', title: 'Firmware Registry', desc: 'View all firmware Osmosis has flashed, with SHA256 hashes' },
      { action: 'recovery-guide', icon: '\u{1F6DF}', title: 'Recovery Guides', desc: 'Step-by-step guides for recovering bricked devices' },
    ],
  },
  {
    title: 'Information & Tools',
    cards: [
      { action: 'diagnostics', icon: '\u{1FA7A}', title: 'Device Diagnostics', desc: 'Battery health, storage, bootloader status, OS info' },
      { action: 'community', icon: '\u{1F465}', title: 'Community Links', desc: 'Forums, wikis, repair guides, and specs for your device' },
      { action: 'companion', icon: '\u{1F9F0}', title: 'Companion Tools', desc: 'Android scripts, platform tools, and helper apps' },
    ],
  },
]

async function openCard(action) {
  // Some cards navigate to wizard steps instead of modals
  if (action === 'os-builder') {
    router.push('/wizard/os-builder')
    return
  }
  if (action === 'bootable') {
    router.push('/wizard/bootable')
    return
  }
  if (action === 'recovery-guide') {
    router.push('/wizard/troubleshoot')
    return
  }
  activeModal.value = action

  // Load data for certain modals
  if (action === 'registry') {
    registryLoading.value = true
    const { ok, data } = await get('/api/registry')
    registryLoading.value = false
    if (ok) registryEntries.value = data
  }
}

async function runPreflight() {
  preflightLoading.value = true
  preflightResult.value = null
  const { ok, data } = await post(`/api/preflight/${preflightType.value}`, {})
  preflightLoading.value = false
  if (ok) preflightResult.value = data
}

async function flashStock() {
  const { ok, data } = await post('/api/flash/stock', { zip_path: fwZipPath.value })
  if (ok && data.task_id) taskId.value = data.task_id
}

async function flashRecovery() {
  const { ok, data } = await post('/api/flash/recovery', { img_path: recoveryImgPath.value })
  if (ok && data.task_id) taskId.value = data.task_id
}

async function startSideload() {
  const { ok, data } = await post('/api/sideload', { zip_path: sideloadZipPath.value, label: sideloadLabel.value })
  if (ok && data.task_id) taskId.value = data.task_id
}
</script>

<template>
  <main id="advanced-mode">
    <nav class="adv-topbar">
      <button class="btn btn-secondary" @click="router.push('/')">&larr; Back to guided mode</button>
      <span class="text-dim">Advanced mode — all tools</span>
    </nav>

    <template v-for="section in sections" :key="section.title">
      <div class="section-title">{{ section.title }}</div>
      <div class="card-grid">
        <div
          v-for="card in section.cards"
          :key="card.action"
          class="card"
          role="button"
          tabindex="0"
          @click="openCard(card.action)"
          @keydown.enter="openCard(card.action)"
        >
          <div class="card-header">
            <div class="card-icon">{{ card.icon }}</div>
            <h3>{{ card.title }}</h3>
          </div>
          <p>{{ card.desc }}</p>
        </div>
      </div>
    </template>
  </main>

  <!-- Flash Stock Modal -->
  <ModalOverlay :model-value="activeModal === 'flash-stock'" title="Restore Stock Firmware" @update:model-value="activeModal = null">
    <div class="form-group">
      <label>Path to firmware ZIP</label>
      <input v-model="fwZipPath" type="text" placeholder="/home/user/Downloads/firmware.zip">
    </div>
    <p class="warning-hint">Ensure the device is in Download Mode before starting.</p>
    <button class="btn btn-primary" @click="flashStock">Start Flash</button>
    <TerminalOutput :task-id="taskId" />
  </ModalOverlay>

  <!-- Flash Recovery Modal -->
  <ModalOverlay :model-value="activeModal === 'flash-recovery'" title="Flash Custom Recovery" @update:model-value="activeModal = null">
    <div class="form-group">
      <label>Path to recovery .img</label>
      <input v-model="recoveryImgPath" type="text" placeholder="/home/user/twrp.img">
    </div>
    <p class="warning-hint">Ensure the device is in Download Mode before starting.</p>
    <button class="btn btn-primary" @click="flashRecovery">Flash Recovery</button>
    <TerminalOutput :task-id="taskId" />
  </ModalOverlay>

  <!-- ADB Sideload Modal -->
  <ModalOverlay :model-value="activeModal === 'sideload'" title="ADB Sideload" @update:model-value="activeModal = null">
    <div class="form-group">
      <label>Type</label>
      <select v-model="sideloadLabel">
        <option value="Custom ROM">Custom ROM</option>
        <option value="GApps">GApps</option>
        <option value="Other">Other ZIP</option>
      </select>
    </div>
    <div class="form-group">
      <label>Path to ZIP</label>
      <input v-model="sideloadZipPath" type="text" placeholder="/home/user/rom.zip">
    </div>
    <button class="btn btn-primary" @click="startSideload">Start Sideload</button>
    <TerminalOutput :task-id="taskId" />
  </ModalOverlay>

  <!-- Pre-Flight Check Modal -->
  <ModalOverlay :model-value="activeModal === 'preflight'" title="Pre-Flight Safety Check" @update:model-value="activeModal = null">
    <p style="margin-bottom: 1rem; color: var(--text-dim);">Run a safety checklist before flashing. Select your device type:</p>
    <div class="form-group">
      <label>Device type</label>
      <select v-model="preflightType" class="form-input">
        <option value="phone">Phone / Tablet (ADB)</option>
        <option value="scooter">Scooter (BLE)</option>
        <option value="pixel">Google Pixel (Fastboot)</option>
      </select>
    </div>
    <button class="btn btn-primary" :class="{ 'btn-loading': preflightLoading }" :disabled="preflightLoading" @click="runPreflight">
      Run checks
    </button>

    <div v-if="preflightResult" style="margin-top: 1rem;">
      <div :class="['info-box', preflightResult.passed ? 'info-box--success' : 'info-box--warn']">
        <strong>{{ preflightResult.passed ? 'All required checks passed' : 'Some checks failed' }}</strong>
        &mdash; {{ preflightResult.passed_count }}/{{ preflightResult.total }} passed
      </div>
      <div v-for="check in preflightResult.checks" :key="check.id" class="preflight-check">
        <span class="preflight-icon">{{ check.passed ? '\u2705' : (check.required ? '\u274C' : '\u26A0\uFE0F') }}</span>
        <div>
          <strong>{{ check.label }}</strong>
          <span v-if="!check.required" class="text-dim"> (optional)</span>
          <div class="text-dim" style="font-size: 0.85em;">{{ check.detail }}</div>
        </div>
      </div>
    </div>
  </ModalOverlay>

  <!-- Firmware Registry Modal -->
  <ModalOverlay :model-value="activeModal === 'registry'" title="Firmware Registry" @update:model-value="activeModal = null">
    <p style="margin-bottom: 1rem; color: var(--text-dim);">Every firmware file Osmosis has flashed, with SHA256 hashes for verification.</p>
    <div v-if="registryLoading" class="text-dim">Loading...</div>
    <div v-else-if="registryEntries.length === 0" class="text-dim">No firmware has been registered yet. Flash a device to start building the registry.</div>
    <div v-else>
      <div v-for="(entry, i) in registryEntries" :key="i" class="registry-entry">
        <div class="registry-header">
          <strong>{{ entry.device_label || entry.filename }}</strong>
          <span v-if="entry.version" class="text-dim">v{{ entry.version }}</span>
        </div>
        <div class="registry-details text-dim">
          <div>{{ entry.filename }} ({{ Math.round(entry.size / 1024) }}K)</div>
          <div class="registry-hash">SHA256: {{ entry.sha256 }}</div>
          <div v-if="entry.flash_method">Method: {{ entry.flash_method }}</div>
          <div v-if="entry.flashed_at">{{ new Date(entry.flashed_at).toLocaleString() }}</div>
        </div>
      </div>
    </div>
  </ModalOverlay>
</template>
