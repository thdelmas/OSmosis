<script setup>
import { onMounted } from 'vue'
import AppHeader from '@/components/shared/AppHeader.vue'
import SideMenu from '@/components/shared/SideMenu.vue'
import DisclaimerBanner from '@/components/shared/DisclaimerBanner.vue'
import { useTheme } from '@/composables/useTheme'

// Initialize theme on mount
const { theme } = useTheme()

onMounted(() => {
  document.documentElement.lang = 'en'
})
</script>

<template>
  <div class="app-layout">
    <SideMenu />
    <div class="app-main">
      <a href="#guided-mode" class="skip-link">Skip to main content</a>
      <AppHeader />
      <DisclaimerBanner />
      <router-view />
    </div>
  </div>
</template>
