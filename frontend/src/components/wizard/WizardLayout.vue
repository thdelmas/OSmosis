<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

// Standard device-flashing flow
const deviceSteps = [
  { name: 'identify', num: 1, label: 'Identify' },
  { name: 'connect', num: 2, label: 'Connect' },
  { name: 'goal', num: 3, label: 'Choose' },
  { name: 'action', num: 4, label: 'Go!' },
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

const actionSteps = ['install', 'backup', 'fix', 'scooter', 'bootable']

const currentStepIndex = computed(() => {
  const name = route.name

  if (isBuilderFlow.value) {
    if (name === 'category') return 0
    return 1
  }

  if (name === 'identify') return 0
  if (name === 'connect') return 1
  if (name === 'goal') return 2
  if (actionSteps.includes(name)) return 3
  return 0
})
</script>

<template>
  <main id="guided-mode">
    <!-- Progress bar -->
    <div class="progress-bar">
      <template v-for="(step, i) in steps" :key="step.name">
        <div class="progress-step-wrap">
          <div class="progress-dot" :class="{ active: i <= currentStepIndex }">{{ step.num }}</div>
          <div class="progress-label" :class="{ active: i <= currentStepIndex }">{{ step.label }}</div>
        </div>
        <div v-if="i < steps.length - 1" class="progress-line" :class="{ filled: i < currentStepIndex }" />
      </template>
    </div>

    <!-- Wizard step content via router-view -->
    <div class="wizard-step active">
      <router-view />
    </div>
  </main>
</template>
