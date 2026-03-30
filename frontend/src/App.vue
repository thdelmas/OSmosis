<script setup>
import { onMounted, provide, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import AppHeader from '@/components/shared/AppHeader.vue'
import SideMenu from '@/components/shared/SideMenu.vue'
import DisclaimerBanner from '@/components/shared/DisclaimerBanner.vue'
import TaskBar from '@/components/shared/TaskBar.vue'
import { useTheme } from '@/composables/useTheme'
import { useWizard } from '@/composables/useWizard'
import { useApi } from '@/composables/useApi'
import { usePubsub } from '@/composables/usePubsub'

// Initialize theme on mount
const { theme } = useTheme()
const { backendOnline, retryConnection } = useApi()
const pubsub = usePubsub()
const router = useRouter()
const { peek, restore, discard, setRoute } = useWizard()

const taskBarRef = ref(null)
const menuOpen = ref(false)

// Restore confirmation state
const restoreBanner = ref(null) // { route, deviceLabel } or null

// Close menu on route change
watch(() => router.currentRoute.value.path, () => {
  menuOpen.value = false
})

// Provide a global registerTask function
provide('registerTask', (id, label) => {
  taskBarRef.value?.registerTask(id, label)
})

function acceptRestore() {
  const savedRoute = restore()
  restoreBanner.value = null
  if (savedRoute && savedRoute.startsWith('/wizard/')) {
    router.replace(savedRoute)
  }
}

function declineRestore() {
  discard()
  restoreBanner.value = null
}

onMounted(() => {
  document.documentElement.lang = 'en'

  // Start IPFS PubSub listener (best-effort, no-ops if daemon offline)
  pubsub.connect()

  // Check for saved wizard state and prompt before restoring
  const saved = peek()
  if (saved && saved.route && router.currentRoute.value.path !== saved.route) {
    restoreBanner.value = saved
  } else if (saved) {
    // Already on the saved route — restore silently
    restore()
  }
})

// Track the current wizard route so it persists across refreshes
router.afterEach((to) => {
  if (to.path.startsWith('/wizard/')) {
    setRoute(to.path)
  }
})
</script>

<template>
  <div class="app-layout">
    <div v-if="menuOpen" class="menu-backdrop" @click="menuOpen = false"></div>
    <SideMenu :open="menuOpen" @close="menuOpen = false" />
    <div class="app-main">
      <a href="#guided-mode" class="skip-link">Skip to main content</a>
      <AppHeader @toggle-menu="menuOpen = !menuOpen" :menu-open="menuOpen" />
      <DisclaimerBanner />
      <div v-if="!backendOnline" class="offline-banner" role="alert">
        <span>Cannot reach the OSmosis backend. Make sure the server is running.</span>
        <button class="btn btn-secondary btn-small" @click="retryConnection">Retry</button>
      </div>
      <div v-if="restoreBanner" class="restore-banner">
        <div class="restore-banner-content">
          <strong>Continue where you left off?</strong>
          <span v-if="restoreBanner.deviceLabel"> &mdash; {{ restoreBanner.deviceLabel }}</span>
        </div>
        <div class="restore-banner-actions">
          <button class="btn btn-primary btn-small" @click="acceptRestore">Resume session</button>
          <button class="btn btn-secondary btn-small" @click="declineRestore">Start fresh</button>
        </div>
      </div>
      <router-view />
    </div>
    <TaskBar ref="taskBarRef" />
  </div>
</template>

<style scoped>
.restore-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.75rem 1.25rem;
  margin: 0 1rem 0.75rem;
  border-radius: var(--radius-card, 4px);
  border: 1px solid var(--accent, #22e8a0);
  background: rgba(34, 232, 160, 0.08);
  flex-wrap: wrap;
}

.restore-banner-content {
  font-size: calc(0.95rem * var(--font-scale, 1));
  color: var(--text, #eee);
}

.restore-banner-actions {
  display: flex;
  gap: 0.5rem;
}

.offline-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.75rem 1.25rem;
  margin: 0 1rem 0.75rem;
  border-radius: var(--radius-card, 4px);
  border: 1px solid var(--red, #ff4444);
  background: rgba(255, 68, 68, 0.08);
  color: var(--text, #d8d4c8);
  font-size: calc(0.95rem * var(--font-scale, 1));
  flex-wrap: wrap;
  animation: fadeIn 0.3s ease;
}
</style>
