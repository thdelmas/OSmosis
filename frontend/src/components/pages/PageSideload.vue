<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import TerminalOutput from '@/components/shared/TerminalOutput.vue'

const { t } = useI18n()
const { post, loading } = useApi()

const sideloadZipPath = ref('')
const sideloadLabel = ref('Custom ROM')
const taskId = ref(null)

async function startSideload() {
  const { ok, data } = await post('/api/sideload', { zip_path: sideloadZipPath.value, label: sideloadLabel.value })
  if (ok && data?.task_id) taskId.value = data.task_id
}
</script>

<template>
  <main class="page-content">
    <h2 class="step-title">{{ t('modal.sideload.title', 'ADB Sideload') }}</h2>
    <p class="step-desc">{{ t('adv.sideload.desc', 'Sideload a custom ROM, GApps, or other ZIP via adb') }}</p>

    <div class="form-group">
      <label class="form-label">{{ t('modal.sideload.type', 'Type') }}</label>
      <select v-model="sideloadLabel" class="form-input">
        <option value="Custom ROM">{{ t('modal.sideload.opt.rom', 'Custom ROM') }}</option>
        <option value="GApps">GApps</option>
        <option value="Other">{{ t('modal.sideload.opt.other', 'Other ZIP') }}</option>
      </select>
    </div>

    <div class="form-group">
      <label class="form-label">{{ t('modal.sideload.label', 'Path to ZIP file') }}</label>
      <input v-model="sideloadZipPath" type="text" class="form-input" placeholder="/home/user/rom.zip">
    </div>

    <p class="warning-hint">{{ t('modal.sideload.warn', 'Start ADB sideload on the device first (TWRP > Advanced > ADB Sideload).') }}</p>

    <div class="step-actions">
      <button
        class="btn btn-large btn-primary"
        :class="{ 'btn-loading': loading }"
        :disabled="loading || !sideloadZipPath"
        @click="startSideload"
      >
        {{ t('btn.sideload', 'Start Sideload') }}
      </button>
    </div>

    <TerminalOutput v-if="taskId" :task-id="taskId" />
  </main>
</template>
