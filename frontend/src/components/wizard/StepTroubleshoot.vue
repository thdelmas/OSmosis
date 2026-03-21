<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'

const { t } = useI18n()
const router = useRouter()
const { get } = useApi()

const guides = ref([])
const activeGuide = ref(null)
const loading = ref(true)
const selectedSymptom = ref(null)

const symptoms = [
  {
    id: 'bootloop',
    icon: '\u{1F504}',
    title: 'Device stuck in bootloop',
    desc: 'Keeps restarting, never reaches home screen',
    guideIds: ['samsung', 'pixel'],
  },
  {
    id: 'brick',
    icon: '\u{1F9F1}',
    title: 'Device won\'t turn on',
    desc: 'No response, black screen, appears dead',
    guideIds: ['samsung', 'pixel', 'scooter'],
  },
  {
    id: 'no-detect',
    icon: '\u{1F50C}',
    title: 'Computer doesn\'t detect device',
    desc: 'USB not recognized, no ADB/fastboot response',
    guideIds: ['samsung', 'pixel'],
  },
  {
    id: 'flash-failed',
    icon: '\u26A0\uFE0F',
    title: 'Flash failed mid-way',
    desc: 'Flashing started but stopped with an error',
    guideIds: ['samsung', 'pixel', 'scooter', 'bootable'],
  },
  {
    id: 'no-signal',
    icon: '\u{1F4F6}',
    title: 'Lost cellular / Wi-Fi',
    desc: 'No signal, IMEI issues, EFS corruption',
    guideIds: ['samsung'],
  },
  {
    id: 'scooter-error',
    icon: '\u{1F6F4}',
    title: 'Scooter error code',
    desc: 'Dashboard shows error 14, 15, or other code',
    guideIds: ['scooter'],
  },
  {
    id: 'scooter-ble',
    icon: '\u{1F4E1}',
    title: 'Scooter not found via Bluetooth',
    desc: 'BLE scan finds nothing, can\'t connect',
    guideIds: ['scooter'],
  },
  {
    id: 'boot-usb',
    icon: '\u{1F4BF}',
    title: 'USB/SD won\'t boot',
    desc: 'Created bootable media but system ignores it',
    guideIds: ['bootable'],
  },
]

onMounted(async () => {
  const { ok, data } = await get('/api/recovery')
  loading.value = false
  if (ok) guides.value = data
})

async function openGuide(guideId) {
  const { ok, data } = await get(`/api/recovery/${guideId}`)
  if (ok) activeGuide.value = { id: guideId, ...data }
}

function selectSymptom(symptom) {
  selectedSymptom.value = symptom
}

function backToSymptoms() {
  selectedSymptom.value = null
  activeGuide.value = null
}

function backToGuideList() {
  activeGuide.value = null
}
</script>

<template>
  <h2 class="step-title">What went wrong?</h2>
  <p class="step-desc">
    Select your symptom or browse recovery guides to get back on track.
  </p>

  <!-- Level 1: Symptom selection -->
  <template v-if="!selectedSymptom && !activeGuide">
    <h3 style="margin: 1.25rem 0 0.5rem;">Describe the problem</h3>
    <div class="symptom-grid">
      <div
        v-for="symptom in symptoms"
        :key="symptom.id"
        class="symptom-card"
        role="button"
        tabindex="0"
        @click="selectSymptom(symptom)"
        @keydown.enter="selectSymptom(symptom)"
      >
        <span class="symptom-icon">{{ symptom.icon }}</span>
        <div>
          <strong>{{ symptom.title }}</strong>
          <div class="text-dim">{{ symptom.desc }}</div>
        </div>
      </div>
    </div>

    <h3 style="margin: 1.5rem 0 0.5rem;">Or browse all recovery guides</h3>
    <div v-if="loading" class="text-dim">Loading guides...</div>
    <div v-else class="guide-list">
      <div
        v-for="guide in guides"
        :key="guide.id"
        class="guide-card"
        role="button"
        tabindex="0"
        @click="openGuide(guide.id)"
        @keydown.enter="openGuide(guide.id)"
      >
        <h3>{{ guide.title }}</h3>
        <div class="text-dim">{{ guide.step_count }} steps</div>
      </div>
    </div>
  </template>

  <!-- Level 2: Symptom-filtered guide list -->
  <template v-else-if="selectedSymptom && !activeGuide">
    <div class="info-box">
      <strong>{{ selectedSymptom.icon }} {{ selectedSymptom.title }}</strong>
    </div>
    <p style="margin-bottom: 0.75rem; color: var(--text-dim);">
      These recovery guides may help with your issue:
    </p>
    <div class="guide-list">
      <div
        v-for="guide in guides.filter(g => selectedSymptom.guideIds.includes(g.id))"
        :key="guide.id"
        class="guide-card"
        role="button"
        tabindex="0"
        @click="openGuide(guide.id)"
        @keydown.enter="openGuide(guide.id)"
      >
        <h3>{{ guide.title }}</h3>
        <div class="text-dim">{{ guide.step_count }} steps</div>
      </div>
    </div>
    <button class="btn btn-secondary" @click="backToSymptoms">&larr; Back to symptoms</button>
  </template>

  <!-- Level 3: Full recovery guide -->
  <template v-else-if="activeGuide">
    <div class="info-box">
      <strong>{{ activeGuide.title }}</strong>
    </div>

    <div v-for="(step, i) in activeGuide.steps" :key="i" class="recovery-step">
      <h4>{{ i + 1 }}. {{ step.title }}</h4>
      <p>{{ step.description }}</p>
      <div v-if="step.warning" class="recovery-warning">
        <strong>Warning:</strong> {{ step.warning }}
      </div>
    </div>

    <div class="step-nav" style="margin-top: 1.5rem;">
      <button class="btn btn-secondary" @click="selectedSymptom ? backToGuideList() : backToSymptoms()">
        &larr; {{ selectedSymptom ? 'Back to guides' : 'Back to symptoms' }}
      </button>
    </div>
  </template>

  <!-- Bottom nav -->
  <div class="step-nav" style="margin-top: 1rem;">
    <button class="btn btn-secondary" @click="router.push('/wizard/goal')">&larr; Back to wizard</button>
  </div>
</template>
