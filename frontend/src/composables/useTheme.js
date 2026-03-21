/**
 * Composable for theme (dark/light) and font size management.
 */
import { ref, watchEffect } from 'vue'

const theme = ref(localStorage.getItem('osmosis-theme') || 'dark')
const fontSize = ref(localStorage.getItem('osmosis-font-size') || 'normal')

const FONT_SIZES = ['normal', 'large', 'xl']

export function useTheme() {
  function applyTheme() {
    document.body.classList.toggle('theme-light', theme.value === 'light')
    localStorage.setItem('osmosis-theme', theme.value)
  }

  function applyFontSize() {
    document.body.classList.remove('font-large', 'font-xl')
    if (fontSize.value === 'large') document.body.classList.add('font-large')
    if (fontSize.value === 'xl') document.body.classList.add('font-xl')
    localStorage.setItem('osmosis-font-size', fontSize.value)
  }

  function toggleTheme() {
    theme.value = theme.value === 'dark' ? 'light' : 'dark'
  }

  function cycleFontSize() {
    const idx = FONT_SIZES.indexOf(fontSize.value)
    fontSize.value = FONT_SIZES[(idx + 1) % FONT_SIZES.length]
  }

  watchEffect(applyTheme)
  watchEffect(applyFontSize)

  return { theme, fontSize, toggleTheme, cycleFontSize }
}
