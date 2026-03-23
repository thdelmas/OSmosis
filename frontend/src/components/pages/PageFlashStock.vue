<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import TerminalOutput from '@/components/shared/TerminalOutput.vue'
import GlossaryTip from '@/components/shared/GlossaryTip.vue'

const { t } = useI18n()
const { post, loading } = useApi()

const fwZipPath = ref('')
const taskId = ref(null)
const flashDone = ref(false)
const flashError = ref(null)

async function flashStock() {
  flashError.value = null
  flashDone.value = false
  const { ok, data } = await post('/api/flash/stock', { zip_path: fwZipPath.value })
  if (ok && data?.task_id) {
    taskId.value = data.task_id
  } else {
    flashError.value = data?.error || t('modal.stock.error', 'Failed to start flash. Make sure the device is connected and in Download Mode or Fastboot.')
  }
}

function onTaskDone(status) {
  if (status === 'done') {
    flashDone.value = true
  } else {
    flashError.value = t('modal.stock.flash_failed', 'Flash failed. Check the details above for more information.')
  }
}
</script>

<template>
  <main class="page-content">
    <h2 class="step-title">{{ t('modal.stock.title', 'Restore Stock Firmware') }}</h2>
    <p class="step-desc">{{ t('adv.stock.desc', 'Restore stock firmware from a ZIP file') }}</p>

    <!-- Warning -->
    <div class="info-box info-box--warning">
      <strong>{{ t('step.fix.warning_label', 'Warning:') }}</strong>
      {{ t('modal.stock.data_warning', 'This will erase all data on the device and restore it to factory settings. Make sure you have backed up anything important.') }}
    </div>

    <!-- Pre-flight checklist -->
    <div class="step-checklist">
      <h3 class="checklist-title">{{ t('preflight.title', 'Before you start') }}</h3>
      <ol class="checklist">
        <li class="checklist-item">
          <span class="checklist-num">1</span>
          <span>Download the correct stock firmware for your exact device model and region.</span>
        </li>
        <li class="checklist-item">
          <span class="checklist-num">2</span>
          <span>
            Put your device in <GlossaryTip term="Download Mode" /> or <GlossaryTip term="fastboot">Fastboot mode</GlossaryTip>.
            For Samsung: hold <kbd>Power</kbd> + <kbd>Home</kbd> + <kbd>Vol&nbsp;Down</kbd>.
            For Pixel/OnePlus: hold <kbd>Power</kbd> + <kbd>Vol&nbsp;Down</kbd>.
          </span>
        </li>
        <li class="checklist-item">
          <span class="checklist-num">3</span>
          <span>Connect the device to this computer with a USB data cable.</span>
        </li>
        <li class="checklist-item">
          <span class="checklist-num">4</span>
          <span>Make sure battery is above 50% or the device is plugged into a charger.</span>
        </li>
      </ol>
    </div>

    <div class="form-group">
      <label class="form-label">{{ t('modal.stock.label', 'Path to firmware ZIP') }}</label>
      <input v-model="fwZipPath" type="text" class="form-input" placeholder="/home/user/Downloads/firmware.zip">
      <p class="form-hint">For Samsung devices, download firmware from <a href="https://samfw.com" target="_blank" rel="noopener">samfw.com</a> or <a href="https://www.sammobile.com" target="_blank" rel="noopener">SamMobile</a>.</p>
    </div>

    <!-- Error -->
    <div v-if="flashError" class="info-box info-box--error">
      {{ flashError }}
    </div>

    <!-- Success -->
    <div v-if="flashDone" class="info-box info-box--success">
      Stock firmware restored successfully! Your device will reboot automatically. If it doesn't, hold the Power button for 10 seconds to restart it.
    </div>

    <div class="step-actions">
      <button
        class="btn btn-large btn-primary"
        :class="{ 'btn-loading': loading }"
        :disabled="loading || !fwZipPath || flashDone"
        @click="flashStock"
      >
        {{ t('btn.flash._self', 'Start Flash') }}
      </button>
    </div>

    <TerminalOutput v-if="taskId" :task-id="taskId" @done="onTaskDone" />
  </main>
</template>
