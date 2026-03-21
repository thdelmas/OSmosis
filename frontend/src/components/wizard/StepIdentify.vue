<script setup>
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { useWizard } from '@/composables/useWizard'

const { t } = useI18n()
const router = useRouter()
const { get } = useApi()
const { state, setCategory, setDevice, setHardware } = useWizard()

const categories = [
  { id: 'phone', icon: '\u{1F4F1}', label: 'Phone / Tablet' },
  { id: 'computer', icon: '\u{1F4BB}', label: 'Computer / SBC' },
  { id: 'network', icon: '\u{1F5A7}', label: 'Router / NAS' },
  { id: 'car', icon: '\u{1F697}', label: 'Car / Vehicle' },
  { id: 'marine', icon: '\u26F5', label: 'Boat / Marine' },
  { id: 'iot', icon: '\u{1F4E1}', label: 'IoT / Wearable' },
  { id: 'console', icon: '\u{1F3AE}', label: 'Game console / Media' },
  { id: 'gps', icon: '\u{1F4CD}', label: 'GPS / Navigation' },
  { id: 'scooter', icon: '\u{1F6F4}', label: 'Electric scooter' },
  { id: 'microcontroller', icon: '\u{1F9F0}', label: 'Microcontroller / SBC' },
]

const brandSuggestions = {
  phone: ['Samsung', 'Google', 'Xiaomi', 'OnePlus', 'Fairphone', 'Pine64', 'Motorola', 'Sony', 'LG', 'Huawei', 'Nothing', 'ASUS'],
  computer: ['Raspberry Pi', 'NVIDIA Jetson', 'Intel', 'AMD', 'Pine64', 'Orange Pi', 'Banana Pi', 'BeagleBone', 'Libre Computer'],
  network: ['TP-Link', 'Netgear', 'Linksys', 'ASUS', 'MikroTik', 'Ubiquiti', 'Synology', 'QNAP', 'GL.iNet'],
  car: ['Android Auto', 'Raspberry Pi', 'Arduino', 'OBDLink', 'Carlinkit'],
  marine: ['Raspberry Pi', 'OpenPlotter', 'Victron', 'Actisense', 'Digital Yacht'],
  iot: ['Espressif (ESP32)', 'Raspberry Pi Pico', 'Arduino', 'Sonoff', 'Shelly', 'Pine64 PineTime', 'Tuya'],
  console: ['Nintendo', 'Valve (Steam Deck)', 'Amazon (Fire TV)', 'Google (Chromecast)', 'Amazon (Kindle)', 'Anbernic', 'Miyoo'],
  gps: ['Garmin', 'TomTom', 'DJI', 'Matek', 'Holybro'],
  scooter: ['Ninebot', 'Xiaomi', 'Segway', 'Vsett', 'Kaabo', 'Dualtron'],
  microcontroller: ['Arduino', 'Raspberry Pi', 'Espressif (ESP32)', 'STMicro (STM32)', 'PJRC (Teensy)', 'Adafruit', 'Seeed Studio', 'SparkFun', 'BBC (micro:bit)'],
}

const selectedCategory = ref(state.category || null)
const brand = ref(state.brand || '')
const model = ref(state.model || '')
const serial = ref(state.serial || '')

const searching = ref(false)
const results = ref([])
const hasSearched = ref(false)
const selectedDevice = ref(null)
const useCustom = ref(false)

const currentBrands = computed(() => brandSuggestions[selectedCategory.value] || [])
const canSearch = computed(() => selectedCategory.value && (brand.value || model.value || serial.value))
const canProceed = computed(() => selectedDevice.value !== null || useCustom.value)

function pickCategory(cat) {
  selectedCategory.value = cat
  brand.value = ''
  model.value = ''
  serial.value = ''
  results.value = []
  hasSearched.value = false
  selectedDevice.value = null
  useCustom.value = false
}

function pickBrand(b) {
  brand.value = b
  selectedDevice.value = null
  useCustom.value = false
  hasSearched.value = false
}

let searchTimeout = null
function scheduleSearch() {
  selectedDevice.value = null
  useCustom.value = false
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => { if (canSearch.value) search() }, 400)
}

watch([brand, model, serial], scheduleSearch)

async function search() {
  if (!canSearch.value) return
  searching.value = true
  hasSearched.value = false
  results.value = []

  const params = new URLSearchParams()
  if (selectedCategory.value) params.set('category', selectedCategory.value)
  if (brand.value) params.set('brand', brand.value)
  if (model.value) params.set('model', model.value)
  if (serial.value) params.set('serial', serial.value)

  const { ok, data } = await get(`/api/devices/search?${params}`)
  searching.value = false
  hasSearched.value = true

  if (ok && Array.isArray(data)) {
    results.value = data
  }
}

function selectDevice(dev) {
  selectedDevice.value = dev
  useCustom.value = false
}

function selectCustom() {
  useCustom.value = true
  selectedDevice.value = null
}

function proceed() {
  setCategory(selectedCategory.value)
  setHardware({ brand: brand.value, model: model.value, serial: serial.value })

  if (selectedDevice.value) {
    setDevice(selectedDevice.value)
  } else if (useCustom.value) {
    setDevice({
      custom: true,
      brand: brand.value,
      model: model.value,
      serial: serial.value,
      label: [brand.value, model.value].filter(Boolean).join(' ') || 'Custom device',
    })
  }

  router.push('/wizard/connect')
}
</script>

<template>
  <h2 class="step-title">{{ t('step.identify.title', 'What device do you have?') }}</h2>
  <p class="step-desc">{{ t('step.identify.desc', 'Pick the type of device you want to work with. We\'ll help you find everything you need.') }}</p>

  <!-- Category selection -->
  <label class="identify-section-label">What kind of device is it?</label>
  <div class="identify-categories">
    <button
      v-for="cat in categories"
      :key="cat.id"
      class="identify-chip"
      :class="{ selected: selectedCategory === cat.id }"
      @click="pickCategory(cat.id)"
    >
      <span class="identify-chip-icon">{{ cat.icon }}</span>
      {{ cat.label }}
    </button>
  </div>

  <!-- Hardware details -->
  <transition name="fade">
    <div v-if="selectedCategory" class="identify-details">
      <div class="form-group">
        <label>Who made it?</label>
        <div v-if="currentBrands.length" class="identify-brand-chips">
          <button
            v-for="b in currentBrands"
            :key="b"
            class="identify-brand-chip"
            :class="{ selected: brand === b }"
            @click="pickBrand(b)"
          >{{ b }}</button>
        </div>
        <input
          v-model="brand"
          type="text"
          :placeholder="t('step.identify.brand_placeholder', 'e.g. Samsung, Raspberry Pi, Ninebot')"
        >
      </div>

      <div class="form-group">
        <label>What model is it?</label>
        <input
          v-model="model"
          type="text"
          :placeholder="t('step.identify.model_placeholder', 'e.g. Galaxy S24, Pi 5, Max G30')"
        >
      </div>

      <div class="form-group">
        <label>Serial number <span class="text-dim">(optional - skip if you're not sure)</span></label>
        <input
          v-model="serial"
          type="text"
          :placeholder="t('step.identify.serial_placeholder', 'You can leave this empty if you don\'t know it')"
        >
      </div>

      <!-- Search results -->
      <div v-if="searching" class="identify-searching">
        <span class="spinner-small"></span> Searching devices...
      </div>

      <div v-else-if="hasSearched" class="identify-results">
        <label class="identify-section-label">
          {{ results.length ? 'Select your device' : 'No matching devices found' }}
        </label>

        <div v-if="results.length" class="identify-device-list">
          <button
            v-for="dev in results"
            :key="dev.id"
            class="identify-device-card"
            :class="{ selected: selectedDevice && selectedDevice.id === dev.id }"
            @click="selectDevice(dev)"
          >
            <div class="identify-device-name">{{ dev.label }}</div>
            <div class="identify-device-meta">
              <span v-if="dev.model">{{ dev.model }}</span>
              <span v-if="dev.codename"> &middot; {{ dev.codename }}</span>
            </div>
            <div v-if="dev.rom_url || dev.eos_url" class="identify-device-tags">
              <span v-if="dev.rom_url" class="identify-tag">ROM</span>
              <span v-if="dev.eos_url" class="identify-tag">/e/OS</span>
              <span v-if="dev.twrp_url" class="identify-tag">TWRP</span>
            </div>
          </button>
        </div>

        <!-- Custom hardware option -->
        <button
          class="identify-device-card identify-custom-card"
          :class="{ selected: useCustom }"
          @click="selectCustom"
        >
          <div class="identify-device-name">I don't see my device here</div>
          <div class="identify-device-meta">
            That's okay! You can continue and set things up yourself in the next steps.
          </div>
        </button>
      </div>

      <!-- Custom-only path when no search input yet -->
      <div v-else-if="selectedCategory && !canSearch" class="identify-results">
        <button
          class="identify-device-card identify-custom-card"
          :class="{ selected: useCustom }"
          @click="selectCustom"
        >
          <div class="identify-device-name">Skip this step</div>
          <div class="identify-device-meta">
            I'll set up the details myself later.
          </div>
        </button>
      </div>
    </div>
  </transition>

  <div class="step-actions">
    <button
      class="btn btn-large btn-primary"
      :disabled="!canProceed"
      @click="proceed"
    >
      Continue &rarr;
    </button>
  </div>

  <div class="step-skip">
    <router-link to="/wizard/category" class="btn btn-link">I want to build my own operating system</router-link>
  </div>
</template>

<style scoped>
.identify-section-label {
  display: block;
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: var(--text);
  font-size: calc(0.95rem * var(--font-scale));
}

.identify-categories {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
}

.identify-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.65rem 1.1rem;
  border-radius: var(--radius-pill);
  border: 2px solid var(--border);
  background: var(--bg-card);
  color: var(--text);
  cursor: pointer;
  font-size: calc(1rem * var(--font-scale));
  transition: all var(--transition-fast);
  min-height: 48px;
}

.identify-chip:hover {
  background: var(--bg-hover);
  border-color: var(--accent);
}

.identify-chip.selected {
  background: var(--accent);
  color: #000;
  border-color: var(--accent);
  font-weight: 600;
}

.identify-chip-icon {
  font-size: 1.3em;
}

.identify-details {
  margin-top: 0.5rem;
}

.identify-brand-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-bottom: 0.5rem;
}

.identify-brand-chip {
  padding: 0.45rem 0.9rem;
  border-radius: var(--radius-pill);
  border: 1px solid var(--border);
  background: var(--bg);
  color: var(--text-dim);
  cursor: pointer;
  font-size: calc(0.9rem * var(--font-scale));
  transition: all var(--transition-fast);
  min-height: 40px;
}

.identify-brand-chip:hover {
  color: var(--text);
  border-color: var(--accent);
}

.identify-brand-chip.selected {
  background: var(--bg-hover);
  color: var(--accent);
  border-color: var(--accent);
  font-weight: 600;
}

/* Search status */
.identify-searching {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem 0;
  color: var(--text-dim);
}

.spinner-small {
  display: inline-block;
  width: 1rem;
  height: 1rem;
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Device result list */
.identify-results {
  margin-top: 1rem;
}

.identify-device-list {
  display: grid;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.identify-device-card {
  display: block;
  width: 100%;
  text-align: left;
  padding: 1rem 1.25rem;
  border-radius: var(--radius-card);
  border: 2px solid var(--border);
  background: var(--bg-card);
  color: var(--text);
  cursor: pointer;
  transition: all var(--transition-fast);
  min-height: 56px;
}

.identify-device-card:hover {
  background: var(--bg-hover);
  border-color: var(--accent);
}

.identify-device-card.selected {
  border-color: var(--accent);
  background: var(--bg-hover);
  box-shadow: inset 3px 0 0 var(--accent);
}

.identify-device-name {
  font-weight: 600;
  font-size: calc(1rem * var(--font-scale));
}

.identify-device-meta {
  font-size: calc(0.85rem * var(--font-scale));
  color: var(--text-dim);
  margin-top: 0.15rem;
}

.identify-device-tags {
  display: flex;
  gap: 0.3rem;
  margin-top: 0.4rem;
}

.identify-tag {
  font-size: calc(0.7rem * var(--font-scale));
  padding: 0.15rem 0.5rem;
  border-radius: var(--radius-pill);
  background: rgba(54, 216, 183, 0.15);
  color: var(--accent);
  font-weight: 600;
}

.identify-custom-card {
  border-style: dashed;
}

/* Transitions */
.fade-enter-active, .fade-leave-active {
  transition: opacity var(--transition-med);
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
</style>
