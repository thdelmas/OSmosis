<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import TerminalOutput from '@/components/shared/TerminalOutput.vue'

const { t } = useI18n()
const { post, loading } = useApi()

const recoveryImgPath = ref('')
const taskId = ref(null)

async function flashRecovery() {
  const { ok, data } = await post('/api/flash/recovery', { img_path: recoveryImgPath.value })
  if (ok && data?.task_id) taskId.value = data.task_id
}
</script>

<template>
  <main class="page-content">
    <h2 class="step-title">{{ t('modal.recovery.title', 'Flash Custom Recovery') }}</h2>
    <p class="step-desc">{{ t('adv.recovery.desc', 'Flash TWRP or other custom recovery .img via Heimdall') }}</p>

    <div class="form-group">
      <label class="form-label">{{ t('modal.recovery.label', 'Path to recovery .img') }}</label>
      <input v-model="recoveryImgPath" type="text" class="form-input" placeholder="/home/user/twrp.img">
    </div>

    <p class="warning-hint">{{ t('modal.recovery.warn', 'Ensure the device is in Download Mode before starting.') }}</p>

    <div class="step-actions">
      <button
        class="btn btn-large btn-primary"
        :class="{ 'btn-loading': loading }"
        :disabled="loading || !recoveryImgPath"
        @click="flashRecovery"
      >
        {{ t('btn.flash.recovery', 'Flash Recovery') }}
      </button>
    </div>

    <TerminalOutput v-if="taskId" :task-id="taskId" />
  </main>
</template>
