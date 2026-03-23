<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { useWizard } from '@/composables/useWizard'
import TerminalOutput from '@/components/shared/TerminalOutput.vue'

const { t } = useI18n()
const router = useRouter()
const { post, loading } = useApi()
const { state, deviceLabel } = useWizard()

const partitions = ref({
  boot: true,
  recovery: true,
  efs: false,
})

const taskId = ref(null)
const backupError = ref(null)

const selectedPartitions = computed(() =>
  Object.entries(partitions.value)
    .filter(([, checked]) => checked)
    .map(([name]) => name)
)

async function startBackup() {
  backupError.value = null
  taskId.value = null

  if (selectedPartitions.value.length === 0) {
    backupError.value = t('step.backup.error.none', 'Select at least one partition to back up.')
    return
  }

  const { ok, data } = await post('/api/backup', {
    partitions: selectedPartitions.value,
  })

  if (ok && data?.task_id) {
    taskId.value = data.task_id
  } else {
    backupError.value = data?.error || t('step.backup.error.start', 'Failed to start backup.')
  }
}
</script>

<template>
  <h2 class="step-title">{{ t('step.backup.title', 'Back up your device') }}</h2>

  <div v-if="deviceLabel" class="detect-box found">
    <strong>{{ deviceLabel }}</strong>
    <span v-if="state.detectedDevice?.serial"> &mdash; {{ state.detectedDevice.serial }}</span>
  </div>

  <p class="step-desc">
    {{ t('step.backup.desc', 'Choose which partitions to save before making changes. Backups will be written to the current working directory.') }}
  </p>

  <div class="form-group">
    <fieldset class="checkbox-group">
      <legend class="form-label">{{ t('step.backup.partitions_label', 'Partitions to back up') }}</legend>

      <label class="checkbox-row">
        <input v-model="partitions.boot" type="checkbox" />
        <span class="checkbox-name">boot</span>
        <span class="text-dim">{{ t('step.backup.boot_desc', 'Boot image — required to start Android') }}</span>
      </label>

      <label class="checkbox-row">
        <input v-model="partitions.recovery" type="checkbox" />
        <span class="checkbox-name">recovery</span>
        <span class="text-dim">{{ t('step.backup.recovery_desc', 'Recovery partition — used for flashing and wiping') }}</span>
      </label>

      <label class="checkbox-row">
        <input v-model="partitions.efs" type="checkbox" />
        <span class="checkbox-name">efs</span>
        <span class="text-dim">{{ t('step.backup.efs_desc', 'EFS partition — contains IMEI and modem calibration data') }}</span>
      </label>
    </fieldset>
  </div>

  <div v-if="backupError" class="detect-box not-found">{{ backupError }}</div>

  <div class="step-actions">
    <button
      class="btn btn-large btn-primary"
      :class="{ 'btn-loading': loading }"
      :disabled="loading || selectedPartitions.length === 0"
      @click="startBackup"
    >
      {{ t('step.backup.btn_start', 'Start backup') }}
    </button>
  </div>

  <TerminalOutput v-if="taskId" :task-id="taskId" />

  <div class="step-nav">
    <button class="btn btn-secondary" @click="router.push('/wizard/identify')">&larr; {{ t('nav.back', 'Back') }}</button>
  </div>
</template>
