<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { useWizard } from '@/composables/useWizard'
import TerminalOutput from '@/components/shared/TerminalOutput.vue'

const { t } = useI18n()
const router = useRouter()
const { get, post } = useApi()
const { state } = useWizard()

// Scooter model list
const models = ref([])
const modelsError = ref(null)
const selectedModel = ref('')

// Scan
const scanTaskId = ref(null)
const scanning = ref(false)
const scanError = ref(null)
const scanResults = ref([])
const selectedAddress = ref(null)

// Firmware
const fwPath = ref('')
const selectedComponent = ref('ESC')
const components = ['ESC/DRV', 'BLE', 'BMS']

// Flash
const flashTaskId = ref(null)
const flashing = ref(false)
const flashError = ref(null)

onMounted(async () => {
  const { ok, data } = await get('/api/scooters')
  if (ok && Array.isArray(data)) {
    models.value = data
  } else {
    modelsError.value = data?.error || t('step.scooter.models_error', 'Could not load scooter models.')
  }
})

async function scan() {
  scanning.value = true
  scanError.value = null
  scanResults.value = []
  selectedAddress.value = null
  scanTaskId.value = null

  const { ok, data } = await post('/api/scooter/scan', {
    model: selectedModel.value || undefined,
  })

  scanning.value = false

  if (ok && data?.task_id) {
    scanTaskId.value = data.task_id
  } else {
    scanError.value = data?.error || t('step.scooter.scan_error', 'Scan failed. Make sure Bluetooth is enabled and the scooter is powered on.')
  }
}

function onScanDone(status) {
  // task.lines is exposed on the TerminalOutput component but results come
  // from the task stream. The API may return a final JSON summary line;
  // parse it from the last line if present.
  // For now we surface whatever scan results arrive via the event payload.
  if (status === 'done' && scanTaskRef.value) {
    const lines = scanTaskRef.value.task?.lines?.value ?? []
    const jsonLine = [...lines].reverse().find(l => {
      try { return Array.isArray(JSON.parse(l.msg)) } catch { return false }
    })
    if (jsonLine) {
      try { scanResults.value = JSON.parse(jsonLine.msg) } catch { /* ignore */ }
    }
  }
}

const scanTaskRef = ref(null)

async function flash() {
  if (!selectedAddress.value) return

  flashing.value = true
  flashError.value = null
  flashTaskId.value = null

  const { ok, data } = await post('/api/scooter/flash', {
    address: selectedAddress.value,
    fw_path: fwPath.value || undefined,
    component: selectedComponent.value,
  })

  flashing.value = false

  if (ok && data?.task_id) {
    flashTaskId.value = data.task_id
  } else {
    flashError.value = data?.error || t('step.scooter.flash_error', 'Flash failed. Check the connection and try again.')
  }
}
</script>

<template>
  <h2 class="step-title">{{ t('step.scooter.title', 'Flash scooter firmware') }}</h2>
  <p class="step-desc">
    {{ t('step.scooter.desc', 'Install custom or stock firmware on your electric scooter over Bluetooth.') }}
  </p>

  <!-- Info box -->
  <div class="info-box info-box--info">
    <strong>{{ t('step.scooter.info_label', 'Before scanning:') }}</strong>
    {{ t('step.scooter.info', 'Turn on your scooter and make sure Bluetooth is enabled on this computer. Keep the scooter within 2 metres.') }}
  </div>

  <!-- Model selector -->
  <div class="form-group">
    <label class="form-label" for="scooter-model">
      {{ t('step.scooter.model_label', 'Scooter model') }}
    </label>
    <select
      id="scooter-model"
      v-model="selectedModel"
      class="form-input"
    >
      <option value="">{{ t('step.scooter.model_placeholder', '— Select model (optional) —') }}</option>
      <option
        v-for="model in models"
        :key="model.id ?? model"
        :value="model.id ?? model"
      >
        {{ model.name ?? model }}
      </option>
    </select>
    <p v-if="modelsError" class="form-hint form-hint--error">{{ modelsError }}</p>
    <p v-else class="form-hint">
      {{ t('step.scooter.model_hint', 'Choosing a model narrows the Bluetooth scan and firmware options.') }}
    </p>
  </div>

  <!-- Scan button -->
  <div class="step-actions">
    <button
      class="btn btn-primary"
      :class="{ 'btn-loading': scanning }"
      :disabled="scanning"
      @click="scan"
    >
      <span class="btn-icon">&#x1F4F6;</span>
      <span>{{ t('step.scooter.scan_btn', 'Scan for scooters') }}</span>
    </button>
  </div>

  <div v-if="scanError" class="detect-box not-found">
    {{ scanError }}
  </div>

  <!-- Scan terminal -->
  <TerminalOutput
    ref="scanTaskRef"
    :task-id="scanTaskId"
    @done="onScanDone"
  />

  <!-- Scan results -->
  <div v-if="scanResults.length > 0" class="scooter-results">
    <h3 class="checklist-title">{{ t('step.scooter.results_title', 'Found scooters — pick one') }}</h3>
    <div class="goal-grid">
      <div
        v-for="scooter in scanResults"
        :key="scooter.address"
        class="goal-card"
        :class="{ 'goal-card--selected': selectedAddress === scooter.address }"
        role="button"
        tabindex="0"
        @click="selectedAddress = scooter.address"
        @keydown.enter="selectedAddress = scooter.address"
        @keydown.space.prevent="selectedAddress = scooter.address"
      >
        <div class="goal-icon">&#x1F6F4;</div>
        <h3>{{ scooter.name ?? scooter.address }}</h3>
        <p v-if="scooter.model">{{ scooter.model }}</p>
        <p class="text-dim">{{ scooter.address }}</p>
        <div v-if="selectedAddress === scooter.address" class="goal-tag">Selected</div>
      </div>
    </div>
  </div>

  <!-- Firmware & component (shown once a scooter is selected) -->
  <template v-if="selectedAddress">
    <div class="form-group">
      <label class="form-label" for="scooter-fw-path">
        {{ t('step.scooter.fw_label', 'Firmware file (.zip or .bin) — optional') }}
      </label>
      <input
        id="scooter-fw-path"
        v-model="fwPath"
        type="text"
        class="form-input"
        :placeholder="t('step.scooter.fw_placeholder', 'Leave blank to use the recommended firmware for this model')"
      />
      <p class="form-hint">
        {{ t('step.scooter.fw_hint', 'Provide a local path to a .zip or .bin firmware file only if you have a specific build.') }}
      </p>
    </div>

    <div class="form-group">
      <label class="form-label">{{ t('step.scooter.component_label', 'Component to flash') }}</label>
      <div class="btn-group">
        <button
          v-for="comp in components"
          :key="comp"
          class="btn btn-secondary"
          :class="{ 'btn-secondary--active': selectedComponent === comp }"
          @click="selectedComponent = comp"
        >
          {{ comp }}
        </button>
      </div>
      <p class="form-hint">
        {{ t('step.scooter.component_hint', 'ESC/DRV controls motor and speed. BLE is the Bluetooth module. BMS manages the battery.') }}
      </p>
    </div>

    <!-- Flash error -->
    <div v-if="flashError" class="detect-box not-found">
      {{ flashError }}
    </div>

    <!-- Flash button -->
    <div class="step-actions">
      <button
        class="btn btn-large btn-primary"
        :class="{ 'btn-loading': flashing }"
        :disabled="flashing || flashTaskId !== null"
        @click="flash"
      >
        <span class="btn-icon">&#x26A1;</span>
        <span>{{ t('step.scooter.flash_btn', 'Flash firmware') }}</span>
      </button>
    </div>

    <!-- Flash terminal -->
    <TerminalOutput :task-id="flashTaskId" />
  </template>

  <!-- Navigation -->
  <div class="step-nav">
    <button class="btn btn-secondary" @click="router.push('/wizard/goal')">&larr; {{ t('nav.back', 'Back') }}</button>
  </div>
</template>
