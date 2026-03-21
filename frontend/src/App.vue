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
  <footer class="app-credits">
    <p>
      Built on open-source tools:
      <a href="https://github.com/Benjamin-Dobell/Heimdall" target="_blank" rel="noopener">Heimdall</a>,
      <a href="https://developer.android.com/tools" target="_blank" rel="noopener">Android Platform Tools</a>,
      <a href="https://github.com/topjohnwu/Magisk" target="_blank" rel="noopener">Magisk</a>.
      Scooter support powered by the <a href="https://scooterhacking.org/" target="_blank" rel="noopener">ScooterHacking</a> community.
      ROMs by <a href="https://lineageos.org/" target="_blank" rel="noopener">LineageOS</a>,
      <a href="https://grapheneos.org/" target="_blank" rel="noopener">GrapheneOS</a>,
      <a href="https://calyxos.org/" target="_blank" rel="noopener">CalyxOS</a>,
      <a href="https://e.foundation/" target="_blank" rel="noopener">/e/OS</a>.
    </p>
  </footer>
</template>
