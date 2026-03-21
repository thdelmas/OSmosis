<script setup>
import { ref, computed, onMounted } from 'vue'
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

// Brand icons (text-based, no emoji)
const brandIcons = {
  Ninebot: '\u{1F6F4}',
  Xiaomi: '\u{1F4F1}',
  Okai: '\u{1F6E0}',
}

// Brand display order
const brandOrder = ['Ninebot', 'Xiaomi']

// Group models by brand
const modelsByBrand = computed(() => {
  const groups = {}
  for (const m of models.value) {
    const brand = m.brand || 'Other'
    if (!groups[brand]) groups[brand] = []
    groups[brand].push(m)
  }
  // Sort brands: known brands first, then "Other" for anything else
  const sorted = {}
  for (const b of brandOrder) {
    if (groups[b]) sorted[b] = groups[b]
  }
  // Collect remaining brands under "Other"
  const otherModels = []
  for (const [b, list] of Object.entries(groups)) {
    if (!brandOrder.includes(b)) otherModels.push(...list)
  }
  if (otherModels.length) sorted['Other'] = otherModels
  return sorted
})

// Currently selected model's full data
const selectedModelData = computed(() => {
  if (!selectedModel.value) return null
  return models.value.find(m => m.id === selectedModel.value) || null
})

// Compatibility info derived from the selected model
const compatibility = computed(() => {
  const m = selectedModelData.value
  if (!m) return null
  const flashMethod = (m.flash_method || '').toLowerCase()
  return {
    ble: flashMethod.includes('ble'),
    stlink: flashMethod.includes('stlink'),
    uart: flashMethod.includes('uart'),
    cfwAvailable: !!(m.cfw_url && m.cfw_url.trim()),
    shfwSupported: (m.shfw_supported || '').toLowerCase() === 'yes',
    shfwPlanned: (m.shfw_supported || '').toLowerCase() === 'planned',
    cfwUrl: (m.cfw_url || '').trim(),
    hasGd32Warning: /gd32/i.test(m.notes || ''),
    notes: (m.notes || '').trim(),
  }
})

// Active brand filter tab
const activeBrandTab = ref(null)

// Filtered brand list based on active tab
const filteredBrands = computed(() => {
  if (!activeBrandTab.value) return modelsByBrand.value
  const result = {}
  if (modelsByBrand.value[activeBrandTab.value]) {
    result[activeBrandTab.value] = modelsByBrand.value[activeBrandTab.value]
  }
  return result
})

function selectModel(id) {
  selectedModel.value = selectedModel.value === id ? '' : id
}

function hasGd32(model) {
  return /gd32/i.test(model.notes || '')
}

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

  <!-- Model selector — visual card grid organized by brand -->
  <div class="form-group">
    <label class="form-label">
      {{ t('step.scooter.model_label', 'Scooter model') }}
    </label>

    <p v-if="modelsError" class="form-hint form-hint--error">{{ modelsError }}</p>

    <template v-else-if="models.length > 0">
      <!-- Brand filter tabs -->
      <div class="scooter-brand-tabs">
        <button
          class="btn btn-secondary btn-sm"
          :class="{ 'btn-secondary--active': !activeBrandTab }"
          @click="activeBrandTab = null"
        >
          {{ t('step.scooter.all_brands', 'All') }}
        </button>
        <button
          v-for="brand in Object.keys(modelsByBrand)"
          :key="brand"
          class="btn btn-secondary btn-sm"
          :class="{ 'btn-secondary--active': activeBrandTab === brand }"
          @click="activeBrandTab = brand"
        >
          {{ brand }}
        </button>
      </div>

      <!-- Brand sections with model cards -->
      <div v-for="(brandModels, brand) in filteredBrands" :key="brand" class="scooter-brand-section">
        <h3 class="scooter-brand-heading">
          <span class="scooter-brand-icon">{{ brandIcons[brand] || '\u{2699}' }}</span>
          {{ brand }}
          <span class="scooter-brand-count">({{ brandModels.length }})</span>
        </h3>
        <div class="goal-grid">
          <div
            v-for="model in brandModels"
            :key="model.id"
            class="goal-card scooter-model-card"
            :class="{
              'goal-card--selected': selectedModel === model.id,
            }"
            role="button"
            tabindex="0"
            @click="selectModel(model.id)"
            @keydown.enter="selectModel(model.id)"
            @keydown.space.prevent="selectModel(model.id)"
          >
            <div class="goal-icon">{{ brandIcons[model.brand] || '\u{2699}' }}</div>
            <h3>{{ model.label }}</h3>
            <p class="text-dim">{{ model.id }}</p>

            <!-- Status badges -->
            <div class="scooter-badges">
              <span v-if="(model.shfw_supported || '').toLowerCase() === 'yes'" class="scooter-badge scooter-badge--ok">
                SHFW
              </span>
              <span v-else-if="(model.shfw_supported || '').toLowerCase() === 'planned'" class="scooter-badge scooter-badge--planned">
                Planned
              </span>
              <span v-else class="scooter-badge scooter-badge--no">
                No CFW
              </span>
              <span v-if="hasGd32(model)" class="scooter-badge scooter-badge--warn">
                GD32
              </span>
            </div>

            <div v-if="selectedModel === model.id" class="goal-tag">Selected</div>
          </div>
        </div>
      </div>

      <p class="form-hint">
        {{ t('step.scooter.model_hint', 'Choosing a model narrows the Bluetooth scan and firmware options.') }}
      </p>
    </template>

    <p v-else class="form-hint">
      {{ t('step.scooter.loading', 'Loading scooter models...') }}
    </p>
  </div>

  <!-- Compatibility check panel (shown when a model is selected) -->
  <div v-if="selectedModelData && compatibility" class="scooter-compat">
    <h3 class="scooter-compat-title">
      {{ selectedModelData.label }} — {{ t('step.scooter.compat_title', 'Compatibility') }}
    </h3>

    <div class="scooter-compat-grid">
      <!-- Flash methods -->
      <div class="scooter-compat-item" :class="{ 'scooter-compat-item--ok': compatibility.ble }">
        <span class="scooter-compat-icon">{{ compatibility.ble ? '\u2705' : '\u274C' }}</span>
        <div>
          <strong>{{ t('step.scooter.compat_ble', 'BLE Flash') }}</strong>
          <p>{{ compatibility.ble ? 'Wireless flashing over Bluetooth' : 'Not supported' }}</p>
        </div>
      </div>

      <div class="scooter-compat-item" :class="{ 'scooter-compat-item--ok': compatibility.stlink }">
        <span class="scooter-compat-icon">{{ compatibility.stlink ? '\u2705' : '\u274C' }}</span>
        <div>
          <strong>{{ t('step.scooter.compat_stlink', 'ST-Link') }}</strong>
          <p>{{ compatibility.stlink ? 'Wired flashing via ST-Link adapter' : 'Not supported' }}</p>
        </div>
      </div>

      <div v-if="compatibility.uart" class="scooter-compat-item scooter-compat-item--ok">
        <span class="scooter-compat-icon">{{ '\u2705' }}</span>
        <div>
          <strong>{{ t('step.scooter.compat_uart', 'UART') }}</strong>
          <p>Serial flashing (use external tool)</p>
        </div>
      </div>

      <!-- CFW availability -->
      <div class="scooter-compat-item" :class="{ 'scooter-compat-item--ok': compatibility.cfwAvailable }">
        <span class="scooter-compat-icon">{{ compatibility.cfwAvailable ? '\u2705' : '\u274C' }}</span>
        <div>
          <strong>{{ t('step.scooter.compat_cfw', 'CFW Available') }}</strong>
          <p v-if="compatibility.cfwAvailable">Custom firmware builds exist</p>
          <p v-else>No custom firmware available yet</p>
        </div>
      </div>

      <!-- SHFW support -->
      <div class="scooter-compat-item" :class="{
        'scooter-compat-item--ok': compatibility.shfwSupported,
        'scooter-compat-item--planned': compatibility.shfwPlanned
      }">
        <span class="scooter-compat-icon">{{ compatibility.shfwSupported ? '\u2705' : compatibility.shfwPlanned ? '\u{1F552}' : '\u274C' }}</span>
        <div>
          <strong>{{ t('step.scooter.compat_shfw', 'SHFW Supported') }}</strong>
          <p v-if="compatibility.shfwSupported">ScooterHacking firmware is available</p>
          <p v-else-if="compatibility.shfwPlanned">Support is planned / in development</p>
          <p v-else>Not supported by ScooterHacking</p>
        </div>
      </div>
    </div>

    <!-- CFW Builder link -->
    <a
      v-if="compatibility.cfwUrl"
      :href="compatibility.cfwUrl"
      target="_blank"
      rel="noopener noreferrer"
      class="btn btn-secondary scooter-cfw-link"
    >
      <span class="btn-icon">&#x1F517;</span>
      {{ t('step.scooter.cfw_builder_link', 'Open CFW Builder') }}
      <span class="text-dim">({{ compatibility.cfwUrl }})</span>
    </a>

    <!-- Warning badges for notes / GD32 -->
    <div v-if="compatibility.hasGd32Warning" class="info-box info-box--warn scooter-warning">
      <strong>&#x26A0; GD32 chip detected in some units:</strong>
      Scooters with GD32 chips cannot be flashed via ST-Link. Check your ESC controller chip
      before attempting a wired flash. Only STM32/AT32 chips are supported.
    </div>

    <div v-if="compatibility.notes && !compatibility.hasGd32Warning" class="info-box info-box--info scooter-notes">
      <strong>&#x2139; Note:</strong> {{ compatibility.notes }}
    </div>

    <div v-if="compatibility.notes && compatibility.hasGd32Warning" class="info-box info-box--info scooter-notes">
      <strong>&#x2139; Additional info:</strong> {{ compatibility.notes }}
    </div>
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
