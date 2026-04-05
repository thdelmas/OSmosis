<script setup>
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useWizard } from '@/composables/useWizard'

const { t } = useI18n()
const router = useRouter()
const { setCategory } = useWizard()

const groups = [
  {
    label: 'Mobile & personal',
    items: [
      { id: 'phone', icon: '\u{1F4F1}' },
      { id: 'console', icon: '\u{1F3AE}' },
      { id: 'ereader', icon: '\u{1F4D6}', tag: 'New' },
      { id: 'gps', icon: '\u{1F4CD}' },
      { id: 'iot', icon: '\u{1F4E1}' },
    ],
  },
  {
    label: 'Computers & networking',
    items: [
      { id: 'computer', icon: '\u{1F4BB}' },
      { id: 'network', icon: '\u{1F5A7}' },
      { id: 'microcontroller', icon: '\u{1F9F0}' },
      { id: 'keyboard', icon: '\u2328\uFE0F', tag: 'New' },
    ],
  },
  {
    label: 'Vehicles & mobility',
    items: [
      { id: 'scooter', icon: '\u{1F6F4}' },
      { id: 'ebike', icon: '\u{1F6B2}' },
      { id: 'car', icon: '\u{1F697}' },
      { id: 'marine', icon: '\u26F5' },
    ],
  },
  {
    label: 'Home & appliances',
    items: [
      { id: 'tv', icon: '\u{1F4FA}', tag: 'New' },
      { id: 'vacuum', icon: '\u{1F9F9}', tag: 'New' },
      { id: 'camera', icon: '\u{1F4F7}', tag: 'New' },
      { id: 'solar', icon: '\u2600\uFE0F', tag: 'New' },
    ],
  },
  {
    label: 'Maker & lab',
    items: [
      { id: 'printer', icon: '\u{1F5A8}\uFE0F', tag: 'New' },
      { id: 'sdr', icon: '\u{1F4FB}', tag: 'New' },
      { id: 'lab', icon: '\u{1F52C}', tag: 'New' },
    ],
  },
  {
    label: 'Tools',
    items: [
      { id: 'build-os', icon: '\u{1F3D7}' },
    ],
  },
]

function pick(cat) {
  // Direct-flow categories — skip the generic connect step
  if (cat === 'build-os') {
    setCategory(cat)
    router.push('/wizard/os-builder')
    return
  }
  if (cat === 'ereader') {
    setCategory(cat)
    router.push('/wizard/ereader')
    return
  }
  setCategory(cat)
  router.push('/wizard/connect')
}
</script>

<template>
  <h2 class="step-title">{{ t('step.category.title', 'What kind of device?') }}</h2>
  <p class="step-desc">{{ t('step.category.desc', 'Different devices need different tools. Pick the category that matches your device.') }}</p>

  <div v-for="group in groups" :key="group.label" class="category-group">
    <h3 class="category-group-label">{{ group.label }}</h3>
    <div class="goal-grid category-grid" role="list" :aria-label="group.label">
      <div
        v-for="cat in group.items"
        :key="cat.id"
        class="goal-card"
        role="listitem"
        tabindex="0"
        :aria-label="t(`cat.${cat.id}.title`) + '. ' + t(`cat.${cat.id}.desc`)"
        @click="pick(cat.id)"
        @keydown.enter="pick(cat.id)"
        @keydown.space.prevent="pick(cat.id)"
      >
        <div class="goal-icon" aria-hidden="true">{{ cat.icon }}</div>
        <h3>{{ t(`cat.${cat.id}.title`) }}</h3>
        <p>{{ t(`cat.${cat.id}.desc`) }}</p>
        <div v-if="cat.tag" class="goal-tag" aria-label="Tag: new">{{ cat.tag }}</div>
      </div>
    </div>
  </div>

  <div class="step-skip">
    <router-link to="/wizard/identify" class="btn btn-link">&larr; Back to hardware identification</router-link>
  </div>
</template>
