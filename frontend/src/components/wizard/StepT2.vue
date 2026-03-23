<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { useWizard } from '@/composables/useWizard'
import TerminalOutput from '@/components/shared/TerminalOutput.vue'

const { t } = useI18n()
const router = useRouter()
const { get, post } = useApi()
const { state } = useWizard()

// Mac model list
const models = ref([])
const modelsError = ref(null)
const selectedModel = ref('')

// Tools check
const tools = ref(null)

// Regions for backup
const regions = ref({
  firmware: true,
  nvram: true,
  sep: true,
})

// Task IDs
const detectTaskId = ref(null)
const backupTaskId = ref(null)
const restoreTaskId = ref(null)

// Existing backups
const backups = ref([])
const selectedBackup = ref('')

// State
const backingUp = ref(false)
const restoring = ref(false)
const restoreError = ref(null)
const backupError = ref(null)

// Group models by product line
const modelsByType = computed(() => {
  const groups = {}
  for (const m of models.value) {
    // Extract product line: "MacBook Pro", "MacBook Air", "iMac", etc.
    const match = m.label.match(/^(MacBook Pro|MacBook Air|iMac Pro|iMac|Mac Pro|Mac mini)/)
    const type = match ? match[1] : 'Other'
    if (!groups[type]) groups[type] = []
    groups[type].push(m)
  }
  return groups
})

const typeIcons = {
  'MacBook Pro': '&#x1F4BB;',
  'MacBook Air': '&#x1F4BB;',
  'iMac': '&#x1F5A5;',
  'iMac Pro': '&#x1F5A5;',
  'Mac Pro': '&#x1F5A5;',
  'Mac mini': '&#x1F5A5;',
}

const selectedModelData = computed(() => {
  if (!selectedModel.value) return null
  return models.value.find(m => m.id === selectedModel.value) || null
})

const selectedRegions = computed(() =>
  Object.entries(regions.value)
    .filter(([, checked]) => checked)
    .map(([name]) => name)
)

const activeTypeTab = ref(null)

const filteredTypes = computed(() => {
  if (!activeTypeTab.value) return modelsByType.value
  const result = {}
  if (modelsByType.value[activeTypeTab.value]) {
    result[activeTypeTab.value] = modelsByType.value[activeTypeTab.value]
  }
  return result
})

const isGoalRestore = computed(() => state.goal === 't2-restore')

function selectModel(id) {
  selectedModel.value = selectedModel.value === id ? '' : id
}

onMounted(async () => {
  const [modelsRes, toolsRes, backupsRes] = await Promise.all([
    get('/api/t2/models'),
    get('/api/t2/tools'),
    get('/api/t2/backups'),
  ])
  if (modelsRes.ok && Array.isArray(modelsRes.data)) {
    models.value = modelsRes.data
  } else {
    modelsError.value = modelsRes.data?.error || 'Could not load T2 Mac model list.'
  }
  if (toolsRes.ok) {
    tools.value = toolsRes.data
  }
  if (backupsRes.ok && Array.isArray(backupsRes.data)) {
    backups.value = backupsRes.data
  }
})

async function detect() {
  detectTaskId.value = null
  const { ok, data } = await get('/api/t2/detect')
  if (ok && data?.task_id) {
    detectTaskId.value = data.task_id
  }
}

async function backup() {
  if (selectedRegions.value.length === 0) {
    backupError.value = 'Select at least one region to back up.'
    return
  }
  backingUp.value = true
  backupTaskId.value = null
  backupError.value = null
  const { ok, data } = await post('/api/t2/backup', {
    model: selectedModel.value || '',
    regions: selectedRegions.value,
  })
  backingUp.value = false
  if (ok && data?.task_id) {
    backupTaskId.value = data.task_id
  } else {
    backupError.value = data?.error || 'Backup failed. Check that the Mac is in DFU mode.'
  }
}

async function restore() {
  if (!selectedBackup.value) return
  restoring.value = true
  restoreError.value = null
  restoreTaskId.value = null
  const { ok, data } = await post('/api/t2/restore', {
    backup_name: selectedBackup.value,
  })
  restoring.value = false
  if (ok && data?.task_id) {
    restoreTaskId.value = data.task_id
  } else {
    restoreError.value = data?.error || 'Restore failed. Check that the Mac is in DFU mode.'
  }
}
</script>

<template>
  <h2 class="step-title">{{ t('step.t2.title', 'Apple T2 chip — backup & restore') }}</h2>
  <p class="step-desc">
    {{ t('step.t2.desc', 'Back up or restore the T2 security chip firmware on your Intel Mac. This is essential before installing Linux, modifying secure boot, or troubleshooting a Mac that won\'t start.') }}
  </p>

  <!-- ── What is the T2 chip? ── -->
  <div class="info-box info-box--info">
    <strong>What is the T2 chip?</strong>
    The Apple T2 is a dedicated security coprocessor built into Intel Macs from 2018 to 2020.
    It handles SSD encryption, secure boot, the camera and microphone hardware disconnect,
    Touch ID, and audio processing. Unlike normal firmware updates, the T2 runs its own
    operating system (bridgeOS) separate from macOS. If the T2 firmware becomes corrupted,
    the Mac may refuse to boot entirely &mdash; which is why backing it up is important.
  </div>

  <!-- ── Tool availability ── -->
  <div v-if="tools && !tools.t2tool" class="info-box info-box--warn">
    <strong>t2tool not found.</strong>
    This tool communicates with the T2 chip over USB when the Mac is in DFU mode.
    Install it from
    <a href="https://github.com/t2linux/apple-t2-tool" target="_blank" rel="noopener noreferrer">github.com/t2linux/apple-t2-tool</a>.
    You will also need <code>libusb</code> installed on this computer.
  </div>

  <div v-if="tools && !tools.lsusb && tools.t2tool" class="info-box info-box--warn">
    <strong>lsusb not found.</strong>
    Install with: <code>sudo apt install usbutils</code> (Debian/Ubuntu)
    or <code>sudo pacman -S usbutils</code> (Arch).
    This is optional but helps detect the T2 chip on the USB bus.
  </div>

  <!-- ── DFU mode instructions ── -->
  <div class="step-checklist">
    <h3 class="checklist-title">{{ t('step.t2.dfu_title', 'How to enter T2 DFU mode') }}</h3>
    <p class="text-dim" style="margin-bottom: 0.75rem;">
      DFU (Device Firmware Update) mode allows another computer to read from and write to the T2 chip
      directly over USB. The Mac's screen will stay black &mdash; this is expected.
    </p>
    <ol class="checklist">
      <li class="checklist-item">
        <span class="checklist-num">1</span>
        <span>
          Shut down the Mac completely. Unplug all cables except power (for desktops).
        </span>
      </li>
      <li class="checklist-item">
        <span class="checklist-num">2</span>
        <span>
          Connect a <strong>USB-C cable</strong> from this computer to the Mac you want to back up.
          Use the <strong>left-hand Thunderbolt port closest to you</strong> on MacBooks, or the
          Thunderbolt port nearest the Ethernet port on desktops.
        </span>
      </li>
      <li class="checklist-item">
        <span class="checklist-num">3</span>
        <span>
          Press and hold the <kbd>Power</kbd> button for exactly <strong>10 seconds</strong>,
          then release it. The screen will stay black. For MacBook models with Touch ID,
          the power button is the Touch ID button at the top-right of the keyboard.
        </span>
      </li>
      <li class="checklist-item">
        <span class="checklist-num">4</span>
        <span>
          Immediately press and release <kbd>Power</kbd> again, then hold
          <kbd>Right Shift</kbd> + <kbd>Left Option</kbd> + <kbd>Left Control</kbd>
          for about <strong>10 seconds</strong>. On the iMac Pro or Mac Pro,
          press the power button and immediately hold the key combination.
        </span>
      </li>
      <li class="checklist-item">
        <span class="checklist-num">5</span>
        <span>
          Release all keys. The Mac's screen will remain black &mdash; this means DFU mode is active.
          Click <strong>Detect T2 chip</strong> below to confirm the connection.
        </span>
      </li>
    </ol>
  </div>

  <!-- ── Detect ── -->
  <div class="step-actions">
    <button class="btn btn-primary" @click="detect">
      <span class="btn-icon">&#x1F50D;</span>
      <span>{{ t('step.t2.detect_btn', 'Detect T2 chip') }}</span>
    </button>
  </div>

  <TerminalOutput v-if="detectTaskId" :task-id="detectTaskId" />

  <!-- ── Model selector ── -->
  <div class="form-group">
    <label class="form-label">
      {{ t('step.t2.model_label', 'Mac model') }}
    </label>

    <p class="form-hint">
      Selecting your Mac model is optional, but it labels your backups so you can tell them apart later.
    </p>

    <p v-if="modelsError" class="form-hint form-hint--error">{{ modelsError }}</p>

    <template v-else-if="models.length > 0">
      <!-- Type filter tabs -->
      <div class="scooter-brand-tabs">
        <button
          class="btn btn-secondary btn-sm"
          :class="{ 'btn-secondary--active': !activeTypeTab }"
          @click="activeTypeTab = null"
        >
          All
        </button>
        <button
          v-for="typeName in Object.keys(modelsByType)"
          :key="typeName"
          class="btn btn-secondary btn-sm"
          :class="{ 'btn-secondary--active': activeTypeTab === typeName }"
          @click="activeTypeTab = typeName"
        >
          {{ typeName }}
        </button>
      </div>

      <!-- Model cards grouped by type -->
      <div v-for="(typeModels, typeName) in filteredTypes" :key="typeName" class="scooter-brand-section">
        <h3 class="scooter-brand-heading">
          <span class="scooter-brand-icon" v-html="typeIcons[typeName] || '&#x1F4BB;'"></span>
          {{ typeName }}
          <span class="scooter-brand-count">({{ typeModels.length }})</span>
        </h3>
        <div class="goal-grid">
          <div
            v-for="model in typeModels"
            :key="model.id"
            class="goal-card scooter-model-card"
            :class="{ 'goal-card--selected': selectedModel === model.id }"
            role="button"
            tabindex="0"
            @click="selectModel(model.id)"
            @keydown.enter="selectModel(model.id)"
            @keydown.space.prevent="selectModel(model.id)"
          >
            <div class="goal-icon" v-html="typeIcons[typeName] || '&#x1F4BB;'"></div>
            <h3>{{ model.label }}</h3>
            <p class="text-dim">{{ model.model }}</p>
            <p v-if="model.notes" class="text-dim">{{ model.notes }}</p>
            <div v-if="selectedModel === model.id" class="goal-tag">Selected</div>
          </div>
        </div>
      </div>
    </template>

    <p v-else class="form-hint">Loading Mac models...</p>
  </div>

  <!-- ── Compatibility panel ── -->
  <div v-if="selectedModelData" class="scooter-compat">
    <h3 class="scooter-compat-title">
      {{ selectedModelData.label }} &mdash; T2 Details
    </h3>

    <div class="scooter-compat-grid">
      <div class="scooter-compat-item scooter-compat-item--ok">
        <span class="scooter-compat-icon">&#x2705;</span>
        <div>
          <strong>T2 Chip</strong>
          <p>Apple T2 security coprocessor present</p>
        </div>
      </div>

      <div class="scooter-compat-item scooter-compat-item--ok">
        <span class="scooter-compat-icon">&#x2705;</span>
        <div>
          <strong>DFU Mode</strong>
          <p>Backup and restore supported via USB-C</p>
        </div>
      </div>

      <div class="scooter-compat-item" :class="{ 'scooter-compat-item--ok': tools?.t2tool }">
        <span class="scooter-compat-icon">{{ tools?.t2tool ? '&#x2705;' : '&#x274C;' }}</span>
        <div>
          <strong>t2tool</strong>
          <p>{{ tools?.t2tool ? 'Installed and ready' : 'Not installed (required)' }}</p>
        </div>
      </div>
    </div>

    <div v-if="selectedModelData.notes" class="info-box info-box--info scooter-notes">
      <strong>&#x2139; Note:</strong> {{ selectedModelData.notes }}
    </div>
  </div>

  <!-- ── Backup section ── -->
  <template v-if="!isGoalRestore">
    <h3 class="form-label" style="margin-top: 2rem;">{{ t('step.t2.backup_title', 'Back up T2 firmware') }}</h3>

    <p class="step-desc">
      The T2 stores its data in several regions. Select which ones to save.
      If you are unsure, keep all three selected &mdash; a complete backup gives you the best
      chance of recovery if something goes wrong.
    </p>

    <div class="form-group">
      <fieldset class="checkbox-group">
        <legend class="form-label">{{ t('step.t2.regions_label', 'Regions to back up') }}</legend>

        <label class="checkbox-row">
          <input v-model="regions.firmware" type="checkbox" />
          <span class="checkbox-name">firmware</span>
          <span class="text-dim">
            bridgeOS firmware &mdash; the T2 chip's own operating system.
            This is the most important region to back up. If corrupted, the Mac won't boot.
          </span>
        </label>

        <label class="checkbox-row">
          <input v-model="regions.nvram" type="checkbox" />
          <span class="checkbox-name">nvram</span>
          <span class="text-dim">
            Non-volatile RAM &mdash; stores startup disk selection, display resolution,
            kernel boot arguments, and other low-level settings.
            Small but useful to preserve your boot configuration.
          </span>
        </label>

        <label class="checkbox-row">
          <input v-model="regions.sep" type="checkbox" />
          <span class="checkbox-name">sep</span>
          <span class="text-dim">
            Secure Enclave Processor &mdash; manages Touch ID fingerprints,
            Apple Pay tokens, and FileVault encryption keys.
            Note: restoring SEP from a backup will <strong>not</strong> restore
            fingerprints or encryption keys for security reasons,
            but it can help recover a non-functional Secure Enclave.
          </span>
        </label>
      </fieldset>
    </div>

    <div v-if="backupError" class="detect-box not-found">{{ backupError }}</div>

    <div class="step-actions">
      <button
        class="btn btn-large btn-primary"
        :class="{ 'btn-loading': backingUp }"
        :disabled="backingUp || selectedRegions.length === 0 || !tools?.t2tool"
        @click="backup"
      >
        <span class="btn-icon">&#x1F4BE;</span>
        <span>{{ t('step.t2.backup_btn', 'Back up T2 chip') }}</span>
      </button>
    </div>

    <TerminalOutput v-if="backupTaskId" :task-id="backupTaskId" />
  </template>

  <!-- ── Restore section ── -->
  <template v-if="backups.length > 0">
    <h3 class="form-label" style="margin-top: 2rem;">{{ t('step.t2.restore_title', 'Restore from backup') }}</h3>

    <!-- Restore warning -->
    <div class="info-box info-box--warn">
      <strong>{{ t('step.t2.restore_warning_label', 'Before restoring:') }}</strong>
      Writing firmware to the T2 chip replaces the existing data in the selected regions.
      Make sure the Mac is still in DFU mode (screen stays black) and the USB-C cable is connected.
      Do not unplug the cable or turn off either computer during the restore process.
    </div>

    <div class="form-group">
      <label class="form-label" for="t2-backup-select">
        {{ t('step.t2.backup_select_label', 'Choose a backup') }}
      </label>
      <select id="t2-backup-select" v-model="selectedBackup" class="form-input">
        <option value="">-- Select a backup --</option>
        <option v-for="b in backups" :key="b.name" :value="b.name">
          {{ b.label }} &mdash; {{ b.name }} ({{ b.region_count }} region{{ b.region_count !== 1 ? 's' : '' }}, {{ b.total_size_kb }} KB)
        </option>
      </select>
      <p class="form-hint">
        Backups are stored in <code>~/.osmosis/t2-backups/</code>.
        Each backup includes checksums that are verified automatically before restoring.
      </p>
    </div>

    <div v-if="restoreError" class="detect-box not-found">{{ restoreError }}</div>

    <div class="step-actions">
      <button
        class="btn btn-large btn-primary"
        :class="{ 'btn-loading': restoring }"
        :disabled="restoring || !selectedBackup || !tools?.t2tool"
        @click="restore"
      >
        <span class="btn-icon">&#x1F527;</span>
        <span>{{ t('step.t2.restore_btn', 'Restore T2 firmware') }}</span>
      </button>
    </div>

    <TerminalOutput v-if="restoreTaskId" :task-id="restoreTaskId" />
  </template>

  <!-- No backups yet — nudge toward backup first -->
  <template v-if="backups.length === 0 && isGoalRestore">
    <div class="info-box info-box--warn" style="margin-top: 2rem;">
      <strong>No T2 backups found.</strong>
      You haven't made any T2 backups yet. Use the backup section above to save your T2 firmware first,
      or if you need to restore from an Apple-provided bridgeOS image, use Apple Configurator 2 on another Mac.
    </div>
  </template>

  <!-- Navigation -->
  <div class="step-nav">
    <button class="btn btn-secondary" @click="router.push('/wizard/identify')">&larr; {{ t('nav.back', 'Back') }}</button>
  </div>
</template>
