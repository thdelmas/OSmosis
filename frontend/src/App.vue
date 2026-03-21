<script setup>
import { onMounted } from 'vue'
import AppHeader from '@/components/shared/AppHeader.vue'
import DisclaimerBanner from '@/components/shared/DisclaimerBanner.vue'
import { useTheme } from '@/composables/useTheme'

// Initialize theme on mount
const { theme } = useTheme()

onMounted(() => {
  document.documentElement.lang = 'en'
})
</script>

<template>
  <AppHeader />
  <DisclaimerBanner />
  <router-view />
</template>
