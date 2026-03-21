<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useTheme } from '@/composables/useTheme'
import { useApi } from '@/composables/useApi'
import { LANGS } from '@/i18n'

const { t, locale } = useI18n()
const router = useRouter()

function goHome() {
  if (confirm(t('nav.confirmHome', 'Are you sure you want to go back to the home page? Any unsaved progress will be lost.'))) {
    router.push('/')
  }
}
const { theme, toggleTheme, cycleFontSize } = useTheme()
const { get } = useApi()

const langOpen = ref(false)
const toolStatus = ref({})

function setLang(lang) {
  locale.value = lang
  localStorage.setItem('osmosis-lang', lang)
  langOpen.value = false
}

async function refreshStatus() {
  const { ok, data } = await get('/api/status')
  if (ok) toolStatus.value = data
}

onMounted(refreshStatus)
</script>

<template>
  <header>
    <h1 style="cursor: pointer" @click="goHome"><span>OS</span>mosis</h1>
    <div class="header-controls">
      <!-- Language switcher -->
      <div class="lang-switcher">
        <button class="header-btn" @click="langOpen = !langOpen">
          {{ LANGS[locale] || 'English' }} &#x25BE;
        </button>
        <div v-if="langOpen" class="lang-dropdown open">
          <button
            v-for="(label, code) in LANGS"
            :key="code"
            class="lang-option"
            :class="{ active: code === locale }"
            @click="setLang(code)"
          >
            {{ label }}
          </button>
        </div>
      </div>

      <!-- Font size -->
      <button class="header-btn" @click="cycleFontSize()" title="Increase text size">
        <span style="font-size:1.1em">A</span><span style="font-size:0.8em">A</span>
      </button>

      <!-- Theme toggle -->
      <button class="header-btn" @click="toggleTheme()" title="Switch light/dark mode">
        <span>{{ theme === 'dark' ? '\u2600' : '\u263E' }}</span>
      </button>

      <!-- Tool status -->
      <div class="status-bar">
        <span
          v-for="(ok, tool) in toolStatus"
          :key="tool"
          class="status-pill"
          :class="ok ? 'ok' : 'missing'"
          :title="tool"
        >
          {{ tool }}
        </span>
      </div>
    </div>
  </header>
</template>
