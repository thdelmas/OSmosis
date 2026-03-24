<script setup>
import { computed, ref, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useWizard } from '@/composables/useWizard'

const route = useRoute()
const router = useRouter()
const { state, subPhase, deviceLabel, reset } = useWizard()

const confirmingReset = ref(false)
const stepDirection = ref('forward') // 'forward' | 'back' for transition direction

function startOver() {
  confirmingReset.value = true
}
function confirmStartOver() {
  confirmingReset.value = false
  reset()
  router.push('/wizard/identify')
}
function cancelStartOver() {
  confirmingReset.value = false
}

// Track step changes for transition direction and scroll
let previousStepIndex = -1
watch(() => route.name, (newName) => {
  const newIdx = stepMap[newName] ?? 0
  stepDirection.value = newIdx >= previousStepIndex ? 'forward' : 'back'
  previousStepIndex = newIdx
  const el = document.getElementById('guided-mode')
  if (el) el.scrollTo({ top: 0, behavior: 'smooth' })
})

// Keyboard shortcuts for wizard navigation
function handleKeyboard(e) {
  // Don't intercept if user is typing in an input
  if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return
  if (e.altKey && e.key === 'ArrowLeft') {
    e.preventDefault()
    if (currentStepIndex.value > 0) goToStep(currentStepIndex.value - 1)
  }
}
onMounted(() => window.addEventListener('keydown', handleKeyboard))
onUnmounted(() => window.removeEventListener('keydown', handleKeyboard))

// Main 5-step flow: no device needed for steps 1-2, device needed for 3-5
const deviceSteps = [
  { name: 'identify', num: 1, label: 'Identify' },
  { name: 'software', num: 2, label: 'Software' },
  { name: 'connect', num: 3, label: 'Connect' },
  { name: 'load', num: 4, label: 'Load' },
  { name: 'install', num: 5, label: 'Install' },
]

// OS builder flow — no cable, no device detection
const builderSteps = [
  { name: 'category', num: 1, label: 'Start' },
  { name: 'os-builder', num: 2, label: 'Configure' },
  { name: 'build', num: 3, label: 'Build' },
  { name: 'flash', num: 4, label: 'Flash' },
]

const isBuilderFlow = computed(() => route.name === 'os-builder' || route.name === 'category')

const steps = computed(() => isBuilderFlow.value ? builderSteps : deviceSteps)

// Map route names to step indices
const stepMap = {
  identify: 0,
  software: 1,
  connect: 2,
  load: 3,
  install: 4,
  // Legacy routes map to closest new step
  goal: 1,
  backup: 3,
  fix: 3,
  scooter: 3,
  bootable: 3,
}

const currentStepIndex = computed(() => {
  const name = route.name

  if (isBuilderFlow.value) {
    if (name === 'category') return 0
    return 1
  }

  return stepMap[name] ?? 0
})

function goToStep(i) {
  if (i >= currentStepIndex.value) return
  const step = steps.value[i]
  if (step) router.push(`/wizard/${step.name}`)
}
</script>

<template>
  <main id="guided-mode" role="main" aria-label="Setup wizard">
    <!-- Progress bar -->
    <nav class="progress-bar" role="list" aria-label="Wizard progress">
      <template v-for="(step, i) in steps" :key="step.name">
        <div class="progress-step-wrap">
          <component
            :is="i < currentStepIndex ? 'button' : 'div'"
            class="progress-dot"
            :class="{ active: i <= currentStepIndex, clickable: i < currentStepIndex }"
            :aria-current="i === currentStepIndex ? 'step' : undefined"
            :aria-label="'Step ' + step.num + ': ' + step.label + (i < currentStepIndex ? ' (done) — click to go back' : i === currentStepIndex ? ' (current)' : '')"
            role="listitem"
            @click="goToStep(i)"
          >{{ step.num }}</component>
          <div class="progress-label" :class="{ active: i <= currentStepIndex }">
            {{ step.label }}
            <span v-if="i === currentStepIndex && subPhase" class="progress-sub">{{ subPhase }}</span>
          </div>
        </div>
        <div v-if="i < steps.length - 1" class="progress-line" :class="{ filled: i < currentStepIndex }" aria-hidden="true" />
      </template>
    </nav>

    <!-- Context breadcrumb: shows what's been selected so far -->
    <div v-if="currentStepIndex > 0 && (deviceLabel || state.selectedRom)" class="wizard-context" aria-label="Current selections">
      <span v-if="deviceLabel" class="context-chip">{{ deviceLabel }}</span>
      <span v-if="state.selectedRom" class="context-chip">{{ state.selectedRom.name }}</span>
    </div>

    <!-- Wizard step content via router-view -->
    <div class="wizard-step active" :class="'step-' + stepDirection" role="region" aria-live="polite">
      <router-view />
    </div>

    <!-- Keyboard shortcut hint (shown on first visit) -->
    <div v-if="currentStepIndex > 0" class="wizard-kbd-hint" aria-hidden="true">
      <kbd>Alt</kbd>+<kbd>&larr;</kbd> to go back
    </div>

    <!-- Start over -->
    <div v-if="currentStepIndex > 0" class="wizard-start-over">
      <div v-if="confirmingReset" class="start-over-confirm">
        <span>This will clear all your selections. Are you sure?</span>
        <button class="btn btn-danger btn-sm" @click="confirmStartOver">Yes, start over</button>
        <button class="btn btn-secondary btn-sm" @click="cancelStartOver">Cancel</button>
      </div>
      <button v-else class="btn btn-link" @click="startOver">Start over from the beginning</button>
    </div>
  </main>
</template>
