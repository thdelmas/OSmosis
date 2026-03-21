<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { useWizard } from '@/composables/useWizard'
import TerminalOutput from '@/components/shared/TerminalOutput.vue'

const { t } = useI18n()
const router = useRouter()
const { post } = useApi()
const { state } = useWizard()

const zipPath = ref('')
const taskId = ref(null)
const flashing = ref(false)
const flashError = ref(null)

async function restore() {
  flashing.value = true
  flashError.value = null
  taskId.value = null

  const { ok, data } = await post('/api/flash/stock', {
    zip_path: zipPath.value || undefined,
  })

  flashing.value = false

  if (ok && data?.task_id) {
    taskId.value = data.task_id
  } else {
    flashError.value = data?.error || t('step.fix.error', 'Failed to start restore. Check that the device is in Download Mode and connected.')
  }
}
</script>

<template>
  <h2 class="step-title">{{ t('step.fix.title', 'Fix / Recover your device') }}</h2>
  <p class="step-desc">
    {{ t('step.fix.desc', 'Restore the factory software to bring a broken or stuck device back to life.') }}
  </p>

  <!-- Warning -->
  <div class="info-box info-box--warning">
    <strong>{{ t('step.fix.warning_label', 'Warning:') }}</strong>
    {{ t('step.fix.warning', 'This will erase everything on the device. Back up any important data before continuing.') }}
  </div>

  <!-- Physical preparation steps -->
  <div class="step-checklist">
    <h3 class="checklist-title">{{ t('step.fix.checklist_title', 'Before you click Restore') }}</h3>
    <ol class="checklist">
      <li class="checklist-item">
        <span class="checklist-num">1</span>
        <span>{{ t('step.fix.step1', 'Turn off the device completely.') }}</span>
      </li>
      <li class="checklist-item">
        <span class="checklist-num">2</span>
        <span>
          {{ t('step.fix.step2', 'Enter Download Mode: hold') }}
          <kbd>Power</kbd> + <kbd>Home</kbd> + <kbd>Vol&nbsp;Down</kbd>
          {{ t('step.fix.step2b', 'simultaneously until the Download Mode screen appears.') }}
        </span>
      </li>
      <li class="checklist-item">
        <span class="checklist-num">3</span>
        <span>{{ t('step.fix.step3', 'Connect the device to this computer with a USB cable.') }}</span>
      </li>
    </ol>
  </div>

  <!-- Optional firmware file -->
  <div class="form-group">
    <label class="form-label" for="fix-zip-path">
      {{ t('step.fix.zip_label', 'Firmware file (.zip) — optional') }}
    </label>
    <input
      id="fix-zip-path"
      v-model="zipPath"
      type="text"
      class="form-input"
      :placeholder="t('step.fix.zip_placeholder', 'Leave blank to use the default stock firmware')"
    />
    <p class="form-hint">
      {{ t('step.fix.zip_hint', 'Provide a path to a local .zip firmware package only if you want a specific version.') }}
    </p>
  </div>

  <!-- Error -->
  <div v-if="flashError" class="detect-box not-found">
    {{ flashError }}
  </div>

  <!-- Actions -->
  <div class="step-actions">
    <button
      class="btn btn-large btn-primary"
      :class="{ 'btn-loading': flashing }"
      :disabled="flashing || (taskId !== null)"
      @click="restore"
    >
      <span class="btn-icon">&#x1F527;</span>
      <span>{{ t('step.fix.btn', 'Restore factory software') }}</span>
    </button>
  </div>

  <!-- Terminal output -->
  <TerminalOutput :task-id="taskId" />

  <!-- Navigation -->
  <div class="step-nav">
    <button class="btn btn-secondary" @click="router.push('/wizard/goal')">&larr; {{ t('nav.back', 'Back') }}</button>
  </div>
</template>
