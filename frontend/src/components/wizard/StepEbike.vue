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

// Controller model list
const models = ref([])
const modelsError = ref(null)
const selectedModel = ref('')

// Brand icons
const brandIcons = {
  Bafang: '\u{2699}',
  Tongsheng: '\u{1F527}',
  Kunteng: '\u{1F50C}',
  VESC: '\u{26A1}',
  Flipsky: '\u{26A1}',
  Lishui: '\u{2699}',
}

// Brand display order
const brandOrder = ['Bafang', 'Tongsheng', 'Kunteng', 'VESC', 'Flipsky']

// Group models by brand
const modelsByBrand = computed(() => {
  const groups = {}
  for (const m of models.value) {
    const brand = m.brand || 'Other'
    if (!groups[brand]) groups[brand] = []
    groups[brand].push(m)
  }
  const sorted = {}
  for (const b of brandOrder) {
    if (groups[b]) sorted[b] = groups[b]
  }
  const otherModels = []
  for (const [b, list] of Object.entries(groups)) {
    if (!brandOrder.includes(b)) otherModels.push(...list)
  }
  if (otherModels.length) sorted['Other'] = otherModels
  return sorted
})

// Selected model's full data
const selectedModelData = computed(() => {
  if (!selectedModel.value) return null
  return models.value.find(m => m.id === selectedModel.value) || null
})

// Compatibility info
const compatibility = computed(() => {
  const m = selectedModelData.value
  if (!m) return null
  const method = (m.flash_method || '').toLowerCase()
  return {
    stlink: method.includes('stlink'),
    uart: method.includes('uart'),
    usb: method.includes('usb'),
    fwProject: m.fw_project || '',
    fwUrl: (m.fw_url || '').trim(),
    supported: (m.support_status || '').toLowerCase() === 'supported',
    experimental: (m.support_status || '').toLowerCase() === 'experimental',
    planned: (m.support_status || '').toLowerCase() === 'planned',
    notes: (m.notes || '').trim(),
    controller: m.controller || '',
  }
})

// Active brand filter tab
const activeBrandTab = ref(null)

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

// Tools check
const tools = ref(null)

// Firmware path
const fwPath = ref('')

// Detect (ST-Link probe)
const detectTaskId = ref(null)

// Backup
const backupTaskId = ref(null)
const backingUp = ref(false)

// Flash
const flashTaskId = ref(null)
const flashing = ref(false)
const flashError = ref(null)

onMounted(async () => {
  const [modelsRes, toolsRes] = await Promise.all([
    get('/api/ebikes'),
    get('/api/ebike/tools'),
  ])
  if (modelsRes.ok && Array.isArray(modelsRes.data)) {
    models.value = modelsRes.data
  } else {
    modelsError.value = modelsRes.data?.error || 'Could not load e-bike controller list.'
  }
  if (toolsRes.ok) {
    tools.value = toolsRes.data
  }
})

async function detect() {
  detectTaskId.value = null
  const { ok, data } = await get('/api/ebike/detect')
  if (ok && data?.task_id) {
    detectTaskId.value = data.task_id
  }
}

async function backup() {
  backingUp.value = true
  backupTaskId.value = null
  const { ok, data } = await post('/api/ebike/backup', {
    controller: selectedModel.value || '',
  })
  backingUp.value = false
  if (ok && data?.task_id) {
    backupTaskId.value = data.task_id
  }
}

async function flash() {
  if (!fwPath.value.trim()) return

  flashing.value = true
  flashError.value = null
  flashTaskId.value = null

  const { ok, data } = await post('/api/ebike/flash', {
    fw_path: fwPath.value.trim(),
    controller: selectedModel.value || '',
  })

  flashing.value = false

  if (ok && data?.task_id) {
    flashTaskId.value = data.task_id
  } else {
    flashError.value = data?.error || 'Flash failed. Check the ST-Link connection and try again.'
  }
}
</script>

<template>
  <h2 class="step-title">{{ t('step.ebike.title', 'Flash e-bike controller') }}</h2>
  <p class="step-desc">
    {{ t('step.ebike.desc', 'Install open-source firmware on your electric bike motor controller via ST-Link.') }}
  </p>

  <!-- Tool status -->
  <div v-if="tools && !tools.stflash" class="info-box info-box--warn">
    <strong>ST-Link tools not found.</strong>
    Install with: <code>sudo apt install stlink-tools</code> (Debian/Ubuntu)
    or <code>sudo pacman -S stlink</code> (Arch).
    An ST-Link V2 programmer is required for flashing.
  </div>

  <div v-if="tools && tools.stflash" class="info-box info-box--info">
    <strong>Before flashing:</strong>
    Connect the ST-Link V2 programmer to your controller's SWD/SWIM header.
    Ensure the controller is powered (battery connected) and the ST-Link is plugged into USB.
  </div>

  <!-- Controller selector -->
  <div class="form-group">
    <label class="form-label">
      {{ t('step.ebike.model_label', 'Motor controller') }}
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
          All
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

      <!-- Brand sections with controller cards -->
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
            :class="{ 'goal-card--selected': selectedModel === model.id }"
            role="button"
            tabindex="0"
            @click="selectModel(model.id)"
            @keydown.enter="selectModel(model.id)"
            @keydown.space.prevent="selectModel(model.id)"
          >
            <div class="goal-icon">{{ brandIcons[model.brand] || '\u{2699}' }}</div>
            <h3>{{ model.label }}</h3>
            <p class="text-dim">{{ model.controller }}</p>

            <!-- Status badges -->
            <div class="scooter-badges">
              <span v-if="(model.support_status || '').toLowerCase() === 'supported'" class="scooter-badge scooter-badge--ok">
                {{ model.fw_project }}
              </span>
              <span v-else-if="(model.support_status || '').toLowerCase() === 'experimental'" class="scooter-badge scooter-badge--planned">
                Experimental
              </span>
              <span v-else class="scooter-badge scooter-badge--no">
                Planned
              </span>
            </div>

            <div v-if="selectedModel === model.id" class="goal-tag">Selected</div>
          </div>
        </div>
      </div>

      <p class="form-hint">
        {{ t('step.ebike.model_hint', 'Select your controller to see compatibility and firmware options.') }}
      </p>
    </template>

    <p v-else class="form-hint">
      Loading e-bike controllers...
    </p>
  </div>

  <!-- Compatibility panel -->
  <div v-if="selectedModelData && compatibility" class="scooter-compat">
    <h3 class="scooter-compat-title">
      {{ selectedModelData.label }} — Compatibility
    </h3>

    <div class="scooter-compat-grid">
      <div class="scooter-compat-item" :class="{ 'scooter-compat-item--ok': compatibility.stlink }">
        <span class="scooter-compat-icon">{{ compatibility.stlink ? '\u2705' : '\u274C' }}</span>
        <div>
          <strong>ST-Link</strong>
          <p>{{ compatibility.stlink ? 'Flash via ST-Link V2 (SWD/SWIM)' : 'ST-Link not supported' }}</p>
        </div>
      </div>

      <div v-if="compatibility.uart" class="scooter-compat-item scooter-compat-item--ok">
        <span class="scooter-compat-icon">{{ '\u2705' }}</span>
        <div>
          <strong>UART</strong>
          <p>Serial flashing via USB-to-serial adapter</p>
        </div>
      </div>

      <div v-if="compatibility.usb" class="scooter-compat-item scooter-compat-item--ok">
        <span class="scooter-compat-icon">{{ '\u2705' }}</span>
        <div>
          <strong>USB</strong>
          <p>Direct USB connection (VESC Tool)</p>
        </div>
      </div>

      <div class="scooter-compat-item" :class="{
        'scooter-compat-item--ok': compatibility.supported,
        'scooter-compat-item--planned': compatibility.experimental || compatibility.planned
      }">
        <span class="scooter-compat-icon">{{ compatibility.supported ? '\u2705' : compatibility.experimental ? '\u{1F9EA}' : '\u{1F552}' }}</span>
        <div>
          <strong>Open Firmware</strong>
          <p v-if="compatibility.supported">{{ compatibility.fwProject }} is available</p>
          <p v-else-if="compatibility.experimental">{{ compatibility.fwProject || 'Firmware' }} — experimental</p>
          <p v-else>Not yet available</p>
        </div>
      </div>
    </div>

    <!-- Firmware project link -->
    <a
      v-if="compatibility.fwUrl"
      :href="compatibility.fwUrl"
      target="_blank"
      rel="noopener noreferrer"
      class="btn btn-secondary scooter-cfw-link"
    >
      <span class="btn-icon">&#x1F517;</span>
      Open {{ compatibility.fwProject }} project
      <span class="text-dim">({{ compatibility.fwUrl }})</span>
    </a>

    <!-- Notes -->
    <div v-if="compatibility.notes" class="info-box info-box--info scooter-notes">
      <strong>&#x2139; Note:</strong> {{ compatibility.notes }}
    </div>

    <!-- VESC notice -->
    <div v-if="compatibility.controller === 'vesc'" class="info-box info-box--info">
      <strong>VESC controllers</strong> are configured via the
      <a href="https://vesc-project.com/" target="_blank" rel="noopener noreferrer">VESC Tool</a>
      desktop application over USB. Osmosis can detect the device and verify the connection,
      but full configuration should be done through VESC Tool.
    </div>
  </div>

  <!-- ST-Link detect -->
  <div class="step-actions">
    <button
      class="btn btn-primary"
      :disabled="!tools?.stflash"
      @click="detect"
    >
      <span class="btn-icon">&#x1F50D;</span>
      <span>Probe ST-Link connection</span>
    </button>

    <button
      v-if="selectedModel"
      class="btn btn-secondary"
      :class="{ 'btn-loading': backingUp }"
      :disabled="backingUp || !tools?.stflash"
      @click="backup"
    >
      <span class="btn-icon">&#x1F4BE;</span>
      <span>Backup current firmware</span>
    </button>
  </div>

  <TerminalOutput :task-id="detectTaskId" />
  <TerminalOutput :task-id="backupTaskId" />

  <!-- Firmware file input -->
  <div class="form-group">
    <label class="form-label" for="ebike-fw-path">
      Firmware file (.bin or .hex)
    </label>
    <input
      id="ebike-fw-path"
      v-model="fwPath"
      type="text"
      class="form-input"
      placeholder="Absolute path to firmware binary, e.g. /home/user/bbs-fw.bin"
    />
    <p class="form-hint">
      Download firmware from the project linked above, then provide the path to the .bin file.
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
      :disabled="flashing || !fwPath.trim() || flashTaskId !== null || !tools?.stflash"
      @click="flash"
    >
      <span class="btn-icon">&#x26A1;</span>
      <span>Flash firmware</span>
    </button>
  </div>

  <TerminalOutput :task-id="flashTaskId" />

  <!-- Navigation -->
  <div class="step-nav">
    <button class="btn btn-secondary" @click="router.push('/wizard/identify')">&larr; Back</button>
  </div>
</template>
