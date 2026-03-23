<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import TerminalOutput from '@/components/shared/TerminalOutput.vue'
import GlossaryTip from '@/components/shared/GlossaryTip.vue'

const { t } = useI18n()
const { post, loading } = useApi()

const recoveryImgPath = ref('')
const taskId = ref(null)
const flashDone = ref(false)
const flashError = ref(null)

async function flashRecovery() {
  flashError.value = null
  flashDone.value = false
  const { ok, data } = await post('/api/flash/recovery', { img_path: recoveryImgPath.value })
  if (ok && data?.task_id) {
    taskId.value = data.task_id
  } else {
    flashError.value = data?.error || t('modal.recovery.error', 'Failed to start flash. Make sure the device is connected and in Download Mode.')
  }
}

function onTaskDone(status) {
  if (status === 'done') {
    flashDone.value = true
  } else {
    flashError.value = t('modal.recovery.flash_failed', 'Flash failed. Check the details above for more information.')
  }
}
</script>

<template>
  <main class="page-content">
    <h2 class="step-title">{{ t('modal.recovery.title', 'Flash Custom Recovery') }}</h2>
    <p class="step-desc">{{ t('adv.recovery.desc', 'Flash a custom recovery .img to your device') }}</p>

    <!-- Pre-flight checklist -->
    <div class="step-checklist">
      <h3 class="checklist-title">{{ t('preflight.title', 'Before you start') }}</h3>
      <ol class="checklist">
        <li class="checklist-item">
          <span class="checklist-num">1</span>
          <span>Make sure the <GlossaryTip term="recovery">recovery image</GlossaryTip> (.img file) matches your exact device model.</span>
        </li>
        <li class="checklist-item">
          <span class="checklist-num">2</span>
          <span>Put your device in <GlossaryTip term="Download Mode" />. For Samsung: hold <kbd>Power</kbd> + <kbd>Home</kbd> + <kbd>Vol&nbsp;Down</kbd>.</span>
        </li>
        <li class="checklist-item">
          <span class="checklist-num">3</span>
          <span>Connect the device to this computer with a USB data cable (not charge-only).</span>
        </li>
        <li class="checklist-item">
          <span class="checklist-num">4</span>
          <span>Make sure battery is above 25%.</span>
        </li>
      </ol>
    </div>

    <div class="form-group">
      <label class="form-label">{{ t('modal.recovery.label', 'Path to recovery .img') }}</label>
      <input v-model="recoveryImgPath" type="text" class="form-input" placeholder="/home/user/recovery.img">
      <p class="form-hint">Download a recovery image from <a href="https://twrp.me/Devices/" target="_blank" rel="noopener">twrp.me</a> or your ROM's website.</p>
    </div>

    <!-- Error -->
    <div v-if="flashError" class="info-box info-box--error">
      {{ flashError }}
    </div>

    <!-- Success -->
    <div v-if="flashDone" class="info-box info-box--success">
      Recovery flashed successfully! Your device now has a custom recovery installed. You can reboot into recovery by holding the recovery key combo for your device.
    </div>

    <div class="step-actions">
      <button
        class="btn btn-large btn-primary"
        :class="{ 'btn-loading': loading }"
        :disabled="loading || !recoveryImgPath || flashDone"
        @click="flashRecovery"
      >
        {{ t('btn.flash.recovery', 'Flash Recovery') }}
      </button>
    </div>

    <TerminalOutput v-if="taskId" :task-id="taskId" @done="onTaskDone" />
  </main>
</template>
