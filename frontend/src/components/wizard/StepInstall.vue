<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { useWizard } from '@/composables/useWizard'
import TerminalOutput from '@/components/shared/TerminalOutput.vue'

const { t } = useI18n()
const router = useRouter()
const { post, loading } = useApi()
const { state, deviceLabel } = useWizard()

const romPath = ref('')
const gappsPath = ref('')
const taskId = ref(null)
const installError = ref(null)
const flashError = ref(null)

async function startInstall() {
  if (!romPath.value.trim()) return
  installError.value = null
  taskId.value = null

  const { ok, data } = await post('/api/sideload', {
    zip_path: romPath.value.trim(),
    label: 'Custom ROM',
  })

  if (ok && data?.task_id) {
    taskId.value = data.task_id
  } else {
    installError.value = data?.error || t('step.install.error.sideload', 'Failed to start installation.')
  }
}

async function downloadAndFlash() {
  flashError.value = null
  taskId.value = null

  const { ok, data } = await post('/api/download-and-flash', {})

  if (ok && data?.task_id) {
    taskId.value = data.task_id
  } else {
    flashError.value = data?.error || t('step.install.error.flash', 'Failed to start download & flash.')
  }
}
</script>

<template>
  <h2 class="step-title">{{ t('step.install.title', 'Install a new operating system') }}</h2>

  <div v-if="deviceLabel" class="detect-box found">
    <strong>{{ deviceLabel }}</strong>
    <span v-if="state.detectedDevice?.serial"> &mdash; {{ state.detectedDevice.serial }}</span>
  </div>

  <p class="step-desc">
    {{ t('step.install.desc', 'Select a ROM ZIP to sideload, or use Download & Flash to fetch a supported image automatically.') }}
  </p>

  <div class="form-group">
    <label class="form-label" for="rom-path">
      {{ t('step.install.rom_label', 'ROM ZIP file path') }}
    </label>
    <input
      id="rom-path"
      v-model="romPath"
      class="form-input"
      type="text"
      :placeholder="t('step.install.rom_placeholder', '/path/to/lineageos.zip')"
    />
  </div>

  <div class="form-group">
    <label class="form-label" for="gapps-path">
      {{ t('step.install.gapps_label', 'GApps ZIP file path (optional)') }}
    </label>
    <input
      id="gapps-path"
      v-model="gappsPath"
      class="form-input"
      type="text"
      :placeholder="t('step.install.gapps_placeholder', '/path/to/gapps.zip')"
    />
  </div>

  <div v-if="installError" class="detect-box not-found">{{ installError }}</div>

  <div class="step-actions">
    <button
      class="btn btn-large btn-primary"
      :class="{ 'btn-loading': loading }"
      :disabled="loading || !romPath.trim()"
      @click="startInstall"
    >
      {{ t('step.install.btn_start', 'Start installation') }}
    </button>

    <button
      class="btn btn-secondary"
      :class="{ 'btn-loading': loading }"
      :disabled="loading"
      @click="downloadAndFlash"
    >
      {{ t('step.install.btn_flash', 'Download & Flash') }}
    </button>
  </div>

  <div v-if="flashError" class="detect-box not-found">{{ flashError }}</div>

  <TerminalOutput v-if="taskId" :task-id="taskId" />

  <div class="step-nav">
    <button class="btn btn-secondary" @click="router.push('/wizard/goal')">&larr; {{ t('nav.back', 'Back') }}</button>
  </div>
</template>
