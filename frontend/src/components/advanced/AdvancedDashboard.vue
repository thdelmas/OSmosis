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

function openCard(action) {
  // Some cards navigate to wizard steps instead of modals
  if (action === 'os-builder') {
    router.push('/wizard/os-builder')
    return
  }
  if (action === 'bootable') {
    router.push('/wizard/bootable')
    return
  }
  activeModal.value = action
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
</template>
