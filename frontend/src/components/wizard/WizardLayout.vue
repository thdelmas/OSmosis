<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const steps = [
  { name: 'category', num: 1, label: 'Device' },
  { name: 'connect', num: 2, label: 'Connect' },
  { name: 'goal', num: 3, label: 'Choose' },
  { name: 'action', num: 4, label: 'Go!' },
]

// Map current route to the progress step
const actionSteps = ['install', 'backup', 'fix', 'scooter', 'os-builder', 'bootable']
const currentStepIndex = computed(() => {
  const name = route.name
  if (name === 'category') return 0
  if (name === 'connect') return 1
  if (name === 'goal') return 2
  if (actionSteps.includes(name)) return 3
  return 0
})

function goToAdvanced() {
  router.push('/advanced')
}
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
