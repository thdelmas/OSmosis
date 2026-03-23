<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { useWizard } from '@/composables/useWizard'
import TerminalOutput from '@/components/shared/TerminalOutput.vue'
import GlossaryTip from '@/components/shared/GlossaryTip.vue'

const { t } = useI18n()
const router = useRouter()
const { post } = useApi()
const { state } = useWizard()

const zipPath = ref('')
const taskId = ref(null)
const flashing = ref(false)
const flashError = ref(null)
const flashDone = ref(false)
const phase = ref('checklist') // checklist | confirm | flashing | done

const brand = computed(() => (state.detectedDevice?.brand || state.detectedDevice?.match?.brand || '').toLowerCase())
const isSamsung = computed(() => brand.value.includes('samsung'))

const downloadModeCombo = computed(() => {
  if (isSamsung.value) return 'Power + Home + Volume Down'
  if (brand.value.includes('google') || brand.value.includes('pixel')) return 'Power + Volume Down'
  if (brand.value.includes('motorola')) return 'Volume Down + Power'
  return 'Power + Volume Down (or check your device\'s manual)'
})

function proceedToConfirm() {
  phase.value = 'confirm'
}

async function restore() {
  phase.value = 'flashing'
  flashing.value = true
  flashError.value = null
  flashDone.value = false
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

function onTaskDone(status) {
  if (status === 'done') {
    flashDone.value = true
    phase.value = 'done'
  } else {
    flashError.value = t('step.fix.flash_failed', 'Restore failed. Check the details above. You may need to re-enter Download Mode and try again.')
  }
}
</script>

<template>
  <h2 class="step-title">{{ t('step.fix.title', 'Fix / Recover your device') }}</h2>
  <p class="step-desc">
    {{ t('step.fix.desc', 'Restore the factory software to bring a broken or stuck device back to life.') }}
  </p>

  <!-- Phase 1: Checklist -->
  <div v-if="phase === 'checklist'">
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
          <span>{{ t('step.fix.step1', 'Turn off the device completely.') }} If it won't turn off, hold the Power button for 15+ seconds.</span>
        </li>
        <li class="checklist-item">
          <span class="checklist-num">2</span>
          <span>
            Enter <GlossaryTip term="Download Mode" />: hold <kbd>{{ downloadModeCombo }}</kbd>.
            Hold until the Download Mode or Fastboot screen appears (this can take 10+ seconds).
          </span>
        </li>
        <li class="checklist-item">
          <span class="checklist-num">3</span>
          <span>{{ t('step.fix.step3', 'Connect the device to this computer with a USB cable.') }} Use a <GlossaryTip term="data cable">data cable</GlossaryTip>, not a charge-only cable.</span>
        </li>
        <li class="checklist-item">
          <span class="checklist-num">4</span>
          <span>Make sure the device has at least 25% battery. If the battery is dead, charge for 15 minutes first.</span>
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

    <!-- Actions -->
    <div class="step-actions">
      <button
        class="btn btn-large btn-primary"
        @click="proceedToConfirm"
      >
        Continue to restore
      </button>
    </div>
  </div>

  <!-- Phase 2: Confirm -->
  <div v-if="phase === 'confirm'">
    <div class="info-box info-box--warn">
      <h3>{{ t('step.fix.confirm_title', 'Are you sure?') }}</h3>
      <p>This will <strong>erase all data</strong> on your device and restore the factory software. This cannot be undone.</p>
      <p>Make sure your device is in <GlossaryTip term="Download Mode" /> and connected via USB.</p>
    </div>
    <div class="step-actions" style="gap: 1rem; display: flex; flex-wrap: wrap;">
      <button class="btn btn-secondary" @click="phase = 'checklist'">&larr; Go back</button>
      <button
        class="btn btn-large btn-primary"
        :class="{ 'btn-loading': flashing }"
        :disabled="flashing"
        @click="restore"
      >
        {{ t('step.fix.btn', 'Restore factory software') }}
      </button>
    </div>
  </div>

  <!-- Phase 3: Flashing -->
  <div v-if="phase === 'flashing'">
    <div class="install-guide-box">
      <h3>Restoring factory software...</h3>
      <p><strong>Do not disconnect your device.</strong> This may take several minutes.</p>
    </div>

    <!-- Error -->
    <div v-if="flashError" class="info-box info-box--error">
      {{ flashError }}
      <div style="margin-top: 0.5rem;">
        <button class="btn btn-secondary" @click="restore">Retry</button>
        <button class="btn btn-secondary" @click="phase = 'checklist'">Back to checklist</button>
      </div>
    </div>

    <!-- Terminal output -->
    <TerminalOutput :task-id="taskId" @done="onTaskDone" />
  </div>

  <!-- Phase 4: Done -->
  <div v-if="phase === 'done'">
    <div class="info-box info-box--success">
      <h3>Restore complete!</h3>
      <p>Your device's factory software has been restored. It should reboot automatically.</p>
      <p v-if="isSamsung">If your Samsung is stuck on the boot logo, hold <kbd>Power</kbd> for 10+ seconds to force restart.</p>
      <p v-else>If the device doesn't reboot, hold the Power button for 10+ seconds.</p>
    </div>
    <div class="step-actions">
      <button class="btn btn-primary" @click="router.push('/wizard/identify')">Start over with this device</button>
    </div>
  </div>

  <!-- Navigation (only in checklist/confirm) -->
  <div v-if="phase === 'checklist' || phase === 'confirm'" class="step-nav">
    <button class="btn btn-secondary" @click="router.push('/wizard/identify')">&larr; {{ t('nav.back', 'Back') }}</button>
  </div>
</template>
