<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useTheme } from '@/composables/useTheme'
import { useApi } from '@/composables/useApi'
import { usePubsub } from '@/composables/usePubsub'
import { LANGS } from '@/i18n'

const { t, locale } = useI18n()
const { theme, fontSize, toggleTheme, setFontSize, fontSizeLabel, themeLabel, themeIcon, FONT_SIZES } = useTheme()
const { get } = useApi()
const { hasUnread, unreadCount } = usePubsub()

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

      <!-- Discord -->
      <a
        href="https://discord.gg/vWqxwvRpJe"
        target="_blank"
        rel="noopener noreferrer"
        class="header-btn discord-link"
        aria-label="Join our Discord server"
        title="Join our Discord"
      >
        <svg width="20" height="15" viewBox="0 0 71 55" fill="currentColor" aria-hidden="true">
          <path d="M60.1 4.9A58.5 58.5 0 0 0 45.4.2a.2.2 0 0 0-.2.1 40.6 40.6 0 0 0-1.8 3.7 54 54 0 0 0-16.2 0A37.4 37.4 0 0 0 25.4.3a.2.2 0 0 0-.2-.1A58.4 58.4 0 0 0 10.6 4.9a.2.2 0 0 0-.1.1C1.5 18.7-.9 32.2.3 45.5v.2a58.9 58.9 0 0 0 17.7 9 .2.2 0 0 0 .3-.1 42.1 42.1 0 0 0 3.6-5.9.2.2 0 0 0-.1-.3 38.8 38.8 0 0 1-5.5-2.6.2.2 0 0 1 0-.4l1.1-.9a.2.2 0 0 1 .2 0 42 42 0 0 0 35.8 0 .2.2 0 0 1 .2 0l1.1.9a.2.2 0 0 1 0 .4 36.4 36.4 0 0 1-5.5 2.6.2.2 0 0 0-.1.3 47.2 47.2 0 0 0 3.6 5.9.2.2 0 0 0 .3.1 58.7 58.7 0 0 0 17.7-9 .2.2 0 0 0 .1-.2c1.4-15-2.3-28.3-9.8-40a.2.2 0 0 0 0-.2ZM23.7 37.3c-3.5 0-6.3-3.2-6.3-7s2.8-7 6.3-7 6.4 3.2 6.3 7-2.8 7-6.3 7Zm23.3 0c-3.5 0-6.3-3.2-6.3-7s2.8-7 6.3-7 6.4 3.2 6.3 7-2.8 7-6.3 7Z"/>
        </svg>
        <span class="header-btn-label">Discord</span>
      </a>

      <!-- IPFS updates -->
      <router-link
        to="/ipfs"
        class="header-btn ipfs-notif"
        :aria-label="hasUnread ? `${unreadCount} new IPFS update(s)` : 'IPFS Network'"
        title="IPFS Network"
      >
        IPFS
        <span v-if="hasUnread" class="ipfs-notif-dot" aria-hidden="true"></span>
      </router-link>

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
