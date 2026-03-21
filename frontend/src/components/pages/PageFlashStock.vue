<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import TerminalOutput from '@/components/shared/TerminalOutput.vue'

const { t } = useI18n()
const { post, loading } = useApi()

const fwZipPath = ref('')
const taskId = ref(null)

async function flashStock() {
  const { ok, data } = await post('/api/flash/stock', { zip_path: fwZipPath.value })
  if (ok && data?.task_id) taskId.value = data.task_id
}
</script>

<template>
  <main class="page-content">
    <h2 class="step-title">{{ t('modal.stock.title', 'Restore Stock Firmware') }}</h2>
    <p class="step-desc">{{ t('adv.stock.desc', 'Restore stock Samsung firmware from a ZIP via Heimdall') }}</p>

    <div class="form-group">
      <label class="form-label">{{ t('modal.stock.label', 'Path to firmware ZIP') }}</label>
      <input v-model="fwZipPath" type="text" class="form-input" placeholder="/home/user/Downloads/firmware.zip">
    </div>

    <p class="warning-hint">{{ t('modal.stock.warn', 'Ensure the device is in Download Mode before starting (Power + Home + Vol Down).') }}</p>

    <div class="step-actions">
      <button
        class="btn btn-large btn-primary"
        :class="{ 'btn-loading': loading }"
        :disabled="loading || !fwZipPath"
        @click="flashStock"
      >
        {{ t('btn.flash._self', 'Start Flash') }}
      </button>
    </div>

    <TerminalOutput v-if="taskId" :task-id="taskId" />
  </main>
</template>
