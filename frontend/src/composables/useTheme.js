/**
 * Composable for theme (dark/light/high-contrast) and font size management.
 */
import { ref, watchEffect } from 'vue'

const theme = ref(localStorage.getItem('osmosis-theme') || 'dark')
const fontSize = ref(localStorage.getItem('osmosis-font-size') || 'normal')

const FONT_SIZES = ['normal', 'large', 'xl', 'xxl']
const THEMES = ['dark', 'light', 'high-contrast', 'high-contrast-light']

export function useTheme() {
  function applyTheme() {
    document.documentElement.setAttribute('data-theme', theme.value)
    // Legacy class for light theme compat
    document.body.classList.toggle('theme-light', theme.value === 'light')
    localStorage.setItem('osmosis-theme', theme.value)
  }

  function applyFontSize() {
    document.body.classList.remove('font-large', 'font-xl', 'font-xxl')
    if (fontSize.value === 'large') document.body.classList.add('font-large')
    if (fontSize.value === 'xl') document.body.classList.add('font-xl')
    if (fontSize.value === 'xxl') document.body.classList.add('font-xxl')
    localStorage.setItem('osmosis-font-size', fontSize.value)
  }

  function toggleTheme() {
    const idx = THEMES.indexOf(theme.value)
    theme.value = THEMES[(idx + 1) % THEMES.length]
  }

  function cycleFontSize() {
    const idx = FONT_SIZES.indexOf(fontSize.value)
    fontSize.value = FONT_SIZES[(idx + 1) % FONT_SIZES.length]
  }

  /** Human-readable label for current font size */
  function fontSizeLabel() {
    return { normal: 'A', large: 'A+', xl: 'A++', xxl: 'A+++' }[fontSize.value] || 'A'
  }

  /** Human-readable label for current theme */
  function themeLabel() {
    return {
      dark: 'Dark',
      light: 'Light',
      'high-contrast': 'High Contrast',
      'high-contrast-light': 'High Contrast Light',
    }[theme.value] || 'Dark'
  }

  /** Icon for current theme */
  function themeIcon() {
    return {
      dark: '\u263E',
      light: '\u2600',
      'high-contrast': '\u25D0',
      'high-contrast-light': '\u25D1',
    }[theme.value] || '\u263E'
  }

  watchEffect(applyTheme)
  watchEffect(applyFontSize)

  return { theme, fontSize, toggleTheme, cycleFontSize, fontSizeLabel, themeLabel, themeIcon, FONT_SIZES, THEMES }
}
