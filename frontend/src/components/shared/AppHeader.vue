<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useTheme } from '@/composables/useTheme'
import { useApi } from '@/composables/useApi'
import { LANGS } from '@/i18n'

const { t, locale } = useI18n()
const { theme, fontSize, toggleTheme, cycleFontSize, fontSizeLabel, themeLabel, themeIcon } = useTheme()
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
  <header role="banner">
    <nav class="header-controls" aria-label="Settings">
      <!-- Language switcher -->
      <div class="lang-switcher">
        <button
          class="header-btn"
          @click="langOpen = !langOpen"
          :aria-expanded="langOpen"
          aria-haspopup="listbox"
          :aria-label="'Language: ' + (LANGS[locale] || 'English')"
        >
          {{ LANGS[locale] || 'English' }} &#x25BE;
        </button>
        <div v-if="langOpen" class="lang-dropdown open" role="listbox" :aria-label="t('nav.language', 'Language')">
          <button
            v-for="(label, code) in LANGS"
            :key="code"
            class="lang-option"
            role="option"
            :aria-selected="code === locale"
            :class="{ active: code === locale }"
            @click="setLang(code)"
          >
            {{ label }}
          </button>
        </div>
      </div>

      <!-- Font size -->
      <button
        class="header-btn"
        @click="cycleFontSize()"
        :title="'Text size: ' + fontSizeLabel()"
        :aria-label="'Text size: ' + fontSizeLabel() + '. Click to enlarge.'"
      >
        <span aria-hidden="true" style="font-size:1.1em">A</span><span aria-hidden="true" style="font-size:0.8em">A</span>
        <span class="header-btn-label">{{ fontSizeLabel() }}</span>
      </button>

      <!-- Theme toggle -->
      <button
        class="header-btn"
        @click="toggleTheme()"
        :title="themeLabel()"
        :aria-label="'Theme: ' + themeLabel() + '. Click to switch.'"
      >
        <span aria-hidden="true">{{ themeIcon() }}</span>
        <span class="header-btn-label">{{ themeLabel() }}</span>
      </button>

      <!-- Tool status -->
      <div class="status-bar" role="status" aria-live="polite" :aria-label="t('nav.toolStatus', 'Tool availability')">
        <span
          v-for="(ok, tool) in toolStatus"
          :key="tool"
          class="status-pill"
          :class="ok ? 'ok' : 'missing'"
          :title="tool + (ok ? ' (installed)' : ' (not found)')"
          :aria-label="tool + (ok ? ' is available' : ' is not installed')"
        >
          {{ tool }}
        </span>
      </div>
    </nav>
  </header>
</template>
