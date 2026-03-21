<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { useWizard } from '@/composables/useWizard'
import TerminalOutput from '@/components/shared/TerminalOutput.vue'

const { t } = useI18n()
const router = useRouter()
const { get, post, loading } = useApi()
const { state } = useWizard()

// Device status
const deviceStatus = ref(null)
const statusError = ref(null)
const checking = ref(false)

// ROM selection
const selectedRom = ref('grapheneos')
const romOptions = [
  { id: 'grapheneos', name: 'GrapheneOS', desc: 'Privacy and security focused. Recommended for most users.' },
  { id: 'calyxos', name: 'CalyxOS', desc: 'Privacy-focused with optional microG support.' },
  { id: 'lineageos', name: 'LineageOS', desc: 'Community-driven, wide device support.' },
]

// Image path (for local ZIP)
const imageZip = ref('')

// Unlock
const unlockTaskId = ref(null)
const unlockError = ref(null)

// Flash
const flashTaskId = ref(null)
const flashError = ref(null)

// Preflight
const preflight = ref(null)
const preflightLoading = ref(false)

async function runPreflight() {
  preflightLoading.value = true
  preflight.value = null
  const { ok, data } = await post('/api/preflight/pixel', {
    fw_path: imageZip.value.trim(),
  })
  preflightLoading.value = false
  if (ok) preflight.value = data
}

onMounted(() => {
  checkDevice()
})

async function checkDevice() {
  checking.value = true
  statusError.value = null
  deviceStatus.value = null

  const { ok, data } = await get('/api/fastboot/status')
  checking.value = false

  if (ok && data) {
    deviceStatus.value = data
  } else {
    statusError.value = data?.error || t('step.pixel.status_error', 'Could not check fastboot status. Is fastboot installed?')
  }
}

async function unlockBootloader() {
  unlockError.value = null
  unlockTaskId.value = null

  const { ok, data } = await post('/api/fastboot/unlock', {})

  if (ok && data?.task_id) {
    unlockTaskId.value = data.task_id
  } else {
    unlockError.value = data?.error || t('step.pixel.unlock_error', 'Failed to start bootloader unlock.')
  }
}

async function flashDevice() {
  if (!imageZip.value.trim()) return

  // Run preflight first
  await runPreflight()
  if (preflight.value && !preflight.value.passed) return

  flashError.value = null
  flashTaskId.value = null

  const { ok, data } = await post('/api/fastboot/flash', {
    image_zip: imageZip.value.trim(),
    flash_type: selectedRom.value === 'factory' ? 'factory' : 'custom',
    wipe: true,
  })

  if (ok && data?.task_id) {
    flashTaskId.value = data.task_id
  } else {
    flashError.value = data?.error || t('step.pixel.flash_error', 'Failed to start flash process.')
  }
}
</script>

<template>
  <h2 class="step-title">{{ t('step.pixel.title', 'Flash Google Pixel') }}</h2>
  <p class="step-desc">
    {{ t('step.pixel.desc', 'Install a custom or factory ROM on your Google Pixel device using fastboot.') }}
  </p>

  <!-- Info box -->
  <div class="info-box info-box--info">
    <strong>{{ t('step.pixel.info_label', 'Before you begin:') }}</strong>
    {{ t('step.pixel.info', 'Boot your Pixel into fastboot mode: power off, then hold Power + Volume Down. Connect it via USB.') }}
  </div>

  <!-- Device status -->
  <div class="step-actions">
    <button
      class="btn btn-primary"
      :class="{ 'btn-loading': checking }"
      :disabled="checking"
      @click="checkDevice"
    >
      {{ t('step.pixel.check_btn', 'Check fastboot connection') }}
    </button>
  </div>

  <div v-if="statusError" class="detect-box not-found">
    {{ statusError }}
  </div>

  <div v-if="deviceStatus && deviceStatus.connected" class="detect-box found">
    <strong>{{ deviceStatus.product || 'Pixel device' }}</strong>
    <span v-if="deviceStatus.serial"> &mdash; {{ deviceStatus.serial }}</span>
    <div style="margin-top: 0.3rem">
      <span v-if="deviceStatus.unlocked" class="badge badge--success">Bootloader unlocked</span>
      <span v-else class="badge badge--warn">Bootloader locked</span>
    </div>
  </div>

  <div v-if="deviceStatus && !deviceStatus.connected" class="detect-box not-found">
    {{ t('step.pixel.not_found', 'No device in fastboot mode. Make sure your Pixel is in fastboot mode and connected via USB.') }}
  </div>

  <!-- Unlock bootloader section -->
  <template v-if="deviceStatus && deviceStatus.connected && !deviceStatus.unlocked">
    <h3 class="checklist-title">{{ t('step.pixel.unlock_title', 'Step 1: Unlock bootloader') }}</h3>
    <p class="step-desc">
      {{ t('step.pixel.unlock_desc', 'The bootloader must be unlocked before flashing a custom ROM. This will erase all data on the device.') }}
    </p>

    <div class="info-box info-box--warn">
      <strong>{{ t('step.pixel.unlock_prereq_label', 'Prerequisites:') }}</strong>
      {{ t('step.pixel.unlock_prereq', 'Enable "OEM Unlocking" in Settings > System > Developer Options before proceeding.') }}
    </div>

    <div v-if="unlockError" class="detect-box not-found">{{ unlockError }}</div>

    <div class="step-actions">
      <button
        class="btn btn-large btn-primary"
        :class="{ 'btn-loading': loading }"
        :disabled="loading || unlockTaskId !== null"
        @click="unlockBootloader"
      >
        {{ t('step.pixel.unlock_btn', 'Unlock bootloader') }}
      </button>
    </div>

    <TerminalOutput v-if="unlockTaskId" :task-id="unlockTaskId" />
  </template>

  <!-- Flash section (shown when bootloader is unlocked) -->
  <template v-if="deviceStatus && deviceStatus.connected && deviceStatus.unlocked">
    <h3 class="checklist-title">{{ t('step.pixel.rom_title', 'Select a ROM') }}</h3>

    <div class="goal-grid">
      <div
        v-for="rom in romOptions"
        :key="rom.id"
        class="goal-card"
        :class="{ 'goal-card--selected': selectedRom === rom.id }"
        role="button"
        tabindex="0"
        @click="selectedRom = rom.id"
        @keydown.enter="selectedRom = rom.id"
        @keydown.space.prevent="selectedRom = rom.id"
      >
        <h3>{{ rom.name }}</h3>
        <p>{{ rom.desc }}</p>
        <div v-if="selectedRom === rom.id" class="goal-tag">Selected</div>
      </div>
    </div>

    <div class="form-group">
      <label class="form-label" for="pixel-image-zip">
        {{ t('step.pixel.zip_label', 'ROM image ZIP file path') }}
      </label>
      <input
        id="pixel-image-zip"
        v-model="imageZip"
        class="form-input"
        type="text"
        :placeholder="t('step.pixel.zip_placeholder', '/path/to/grapheneos-factory.zip')"
      />
      <p class="form-hint">
        {{ t('step.pixel.zip_hint', 'Download the factory/ROM image for your device and provide the path to the ZIP file.') }}
      </p>
    </div>

    <!-- Preflight results -->
    <div v-if="preflight" style="margin-bottom: 1rem;">
      <div :class="['info-box', preflight.passed ? 'info-box--success' : 'info-box--warn']">
        <strong>{{ preflight.passed ? 'Pre-flight checks passed' : 'Pre-flight checks failed' }}</strong>
        &mdash; {{ preflight.passed_count }}/{{ preflight.total }} passed
      </div>
      <div v-for="check in preflight.checks" :key="check.id" class="preflight-check">
        <span class="preflight-icon">{{ check.passed ? '\u2705' : (check.required ? '\u274C' : '\u26A0\uFE0F') }}</span>
        <div>
          <strong>{{ check.label }}</strong>
          <span v-if="!check.required" class="text-dim"> (optional)</span>
          <div class="text-dim" style="font-size: 0.85em;">{{ check.detail }}</div>
        </div>
      </div>
      <button v-if="!preflight.passed" class="btn btn-secondary" style="margin-top: 0.5rem;" @click="runPreflight">
        Re-run checks
      </button>
    </div>

    <div v-if="flashError" class="detect-box not-found">{{ flashError }}</div>

    <div class="step-actions">
      <button
        class="btn btn-large btn-primary"
        :class="{ 'btn-loading': loading }"
        :disabled="loading || !imageZip.trim() || flashTaskId !== null"
        @click="flashDevice"
      >
        {{ t('step.pixel.flash_btn', 'Flash ROM') }}
      </button>
    </div>

    <TerminalOutput v-if="flashTaskId" :task-id="flashTaskId" />
  </template>

  <!-- Navigation -->
  <div class="step-nav">
    <button class="btn btn-secondary" @click="router.push('/wizard/goal')">&larr; {{ t('nav.back', 'Back') }}</button>
  </div>
</template>
