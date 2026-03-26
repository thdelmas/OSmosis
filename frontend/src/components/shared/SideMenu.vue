<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import GlossaryTip from '@/components/shared/GlossaryTip.vue'
const { t } = useI18n()
const router = useRouter()

defineProps({
  open: { type: Boolean, default: false },
})

defineEmits(['close'])

const connectedDevices = ref([])
let pollTimer = null

const modeLabels = {
  device: 'ADB',
  recovery: 'Recovery',
  sideload: 'Sideload',
  fastboot: 'Fastboot',
  download: 'Download',
  unauthorized: 'Locked',
}

const modeColors = {
  device: 'var(--success, #4caf50)',
  recovery: 'var(--warning, #ff9800)',
  sideload: 'var(--info, #2196f3)',
  fastboot: '#9c27b0',
  download: 'var(--warning, #ff9800)',
  unauthorized: 'var(--danger, #f44336)',
}

async function pollDevices() {
  try {
    const res = await fetch('/api/devices/connected')
    if (res.ok) {
      const data = await res.json()
      connectedDevices.value = data.devices || []
    }
  } catch { /* ignore */ }
}

function openDevice(dev) {
  router.push({ name: 'connected-device', params: { serial: dev.serial || dev.mode } })
}

onMounted(() => {
  pollDevices()
  pollTimer = setInterval(pollDevices, 3000)
})
onUnmounted(() => clearInterval(pollTimer))
</script>

<template>
  <aside id="side-menu" class="side-menu" :class="{ open }" role="navigation" aria-label="Main navigation">
    <div class="side-menu-logo">
      <router-link to="/" class="side-menu-brand">
        <img src="/logo.png" alt="OSmosis logo" class="side-menu-logo-img" />
        <span class="side-menu-title"><span class="accent">OS</span>mosis</span>
      </router-link>
    </div>

    <nav class="side-menu-nav">
      <router-link
        to="/wizard/identify"
        class="side-menu-link"
        :class="{ active: $route.path.startsWith('/wizard') }"
      >
        {{ t('nav.wizard', 'Wizard') }}
      </router-link>

      <div class="side-menu-divider"></div>
      <div class="side-menu-section">{{ t('nav.tools', 'Tools') }}</div>

      <router-link to="/flash-stock" class="side-menu-link" active-class="active">
        <GlossaryTip term="Flash Stock">{{ t('nav.flashStock', 'Restore factory software') }}</GlossaryTip>
      </router-link>

      <router-link to="/flash-recovery" class="side-menu-link" active-class="active">
        <GlossaryTip term="Flash Recovery">{{ t('nav.flashRecovery', 'Install recovery tool') }}</GlossaryTip>
      </router-link>

      <router-link to="/sideload" class="side-menu-link" active-class="active">
        <GlossaryTip term="ADB Sideload">{{ t('nav.sideload', 'Send file to device') }}</GlossaryTip>
      </router-link>

      <router-link to="/apps" class="side-menu-link" active-class="active">
        {{ t('nav.apps', 'Install apps') }}
      </router-link>

      <router-link to="/preflight" class="side-menu-link" active-class="active">
        <GlossaryTip term="Pre-Flight">{{ t('nav.preflight', 'Pre-install checklist') }}</GlossaryTip>
      </router-link>

      <router-link to="/registry" class="side-menu-link" active-class="active">
        {{ t('nav.registry', 'Registry') }}
      </router-link>

      <div class="side-menu-divider"></div>

      <router-link to="/wiki" class="side-menu-link" active-class="active">
        {{ t('nav.wiki', 'Wiki') }}
      </router-link>

      <router-link to="/about" class="side-menu-link" active-class="active">
        {{ t('nav.about', 'About') }}
      </router-link>

      <router-link to="/credits" class="side-menu-link" active-class="active">
        {{ t('nav.credits', 'Credits') }}
      </router-link>
    </nav>

    <div class="side-menu-devices" aria-label="Connected devices">
      <div class="side-menu-section">Devices</div>
      <TransitionGroup name="device-list" tag="div">
        <div
          v-for="dev in connectedDevices"
          :key="dev.serial || dev.mode"
          class="device-card clickable"
          @click="openDevice(dev)"
        >
          <div class="device-card-header">
            <span
              class="device-mode-dot"
              :style="{ background: modeColors[dev.mode] || 'var(--text-dim)' }"
              :title="modeLabels[dev.mode] || dev.mode"
            ></span>
            <span class="device-card-name">{{ dev.display_name || dev.serial }}</span>
          </div>
          <div class="device-card-meta">
            <span class="device-mode-badge" :style="{ color: modeColors[dev.mode] || 'var(--text-dim)' }">
              {{ modeLabels[dev.mode] || dev.mode }}
            </span>
            <span v-if="dev.serial" class="device-serial">{{ dev.serial.slice(0, 8) }}</span>
          </div>
        </div>
      </TransitionGroup>
      <div v-if="!connectedDevices.length" class="device-empty">
        No devices connected
      </div>
    </div>

    <div class="side-menu-footer">
      <p>Free & open source</p>
    </div>
  </aside>
</template>
