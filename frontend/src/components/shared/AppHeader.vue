<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useTheme } from '@/composables/useTheme'
import { useApi } from '@/composables/useApi'
import { LANGS } from '@/i18n'

const { t, locale } = useI18n()
const { theme, fontSize, toggleTheme, setFontSize, fontSizeLabel, themeLabel, themeIcon, FONT_SIZES } = useTheme()
const { get } = useApi()

defineProps({
  menuOpen: { type: Boolean, default: false },
})

const emit = defineEmits(['toggle-menu'])

const langOpen = ref(false)
const fontSizeOpen = ref(false)
const langSwitcherRef = ref(null)
const fontSizeSwitcherRef = ref(null)
const toolStatus = ref({})

function handleClickOutside(e) {
  if (langOpen.value && langSwitcherRef.value && !langSwitcherRef.value.contains(e.target)) {
    langOpen.value = false
  }
  if (fontSizeOpen.value && fontSizeSwitcherRef.value && !fontSizeSwitcherRef.value.contains(e.target)) {
    fontSizeOpen.value = false
  }
}

function handleKeydown(e) {
  if (e.key === 'Escape') {
    langOpen.value = false
    fontSizeOpen.value = false
  }
}

function pickFontSize(size) {
  setFontSize(size)
  fontSizeOpen.value = false
}

function setLang(lang) {
  locale.value = lang
  localStorage.setItem('osmosis-lang', lang)
  langOpen.value = false
}

async function refreshStatus() {
  const { ok, data } = await get('/api/status')
  if (ok) toolStatus.value = data
}

onMounted(() => {
  refreshStatus()
  document.addEventListener('click', handleClickOutside)
  document.addEventListener('keydown', handleKeydown)
})
onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  document.removeEventListener('keydown', handleKeydown)
})
</script>

<template>
  <header role="banner">
    <button
      class="hamburger-btn"
      @click="emit('toggle-menu')"
      :aria-expanded="menuOpen"
      aria-controls="side-menu"
      aria-label="Toggle navigation menu"
    >
      <span class="hamburger-icon" :class="{ open: menuOpen }">
        <span></span><span></span><span></span>
      </span>
    </button>
    <nav class="header-controls" aria-label="Settings">
      <!-- Language switcher -->
      <div class="lang-switcher" ref="langSwitcherRef">
        <button
          class="header-btn"
          @click="langOpen = !langOpen"
          :aria-expanded="langOpen"
          aria-haspopup="menu"
          :aria-label="'Language: ' + (LANGS[locale] || 'English')"
        >
          {{ LANGS[locale] || 'English' }} &#x25BE;
        </button>
        <div v-if="langOpen" class="lang-dropdown open" role="menu" :aria-label="t('nav.language', 'Language')">
          <button
            v-for="(label, code) in LANGS"
            :key="code"
            class="lang-option"
            role="menuitem"
            :aria-current="code === locale ? 'true' : undefined"
            :class="{ active: code === locale }"
            @click="setLang(code)"
          >
            {{ label }}
          </button>
        </div>
      </div>

      <!-- Font size -->
      <div class="font-size-switcher" ref="fontSizeSwitcherRef">
        <button
          class="header-btn"
          @click="fontSizeOpen = !fontSizeOpen"
          :aria-expanded="fontSizeOpen"
          aria-haspopup="menu"
          :aria-label="'Text size: ' + fontSizeLabel()"
        >
          <span aria-hidden="true" style="font-size:1.1em">A</span><span aria-hidden="true" style="font-size:0.8em">A</span>
          <span class="header-btn-label">{{ fontSizeLabel() }}</span>
          &#x25BE;
        </button>
        <div v-if="fontSizeOpen" class="lang-dropdown open" role="menu" aria-label="Text size">
          <button
            v-for="size in FONT_SIZES"
            :key="size"
            class="lang-option"
            role="menuitem"
            :aria-current="size === fontSize ? 'true' : undefined"
            :class="{ active: size === fontSize }"
            @click="pickFontSize(size)"
          >{{ fontSizeLabel(size) }}</button>
        </div>
      </div>

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
