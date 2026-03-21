import { createI18n } from 'vue-i18n'

import en from './en.json'
import fr from './fr.json'
import br from './br.json'
import ca from './ca.json'
import eu from './eu.json'
import pt from './pt.json'
import es from './es.json'

export const LANGS = {
  en: 'English',
  fr: 'Français',
  br: 'Brezhoneg',
  ca: 'Català',
  eu: 'Euskara',
  pt: 'Português',
  es: 'Español',
}

function detectLocale() {
  const saved = localStorage.getItem('osmosis-lang')
  if (saved && LANGS[saved]) return saved
  const browser = navigator.language?.split('-')[0]
  if (browser && LANGS[browser]) return browser
  return 'en'
}

const i18n = createI18n({
  legacy: false,
  locale: detectLocale(),
  fallbackLocale: 'en',
  messages: { en, fr, br, ca, eu, pt, es },
  missingWarn: false,
  fallbackWarn: false,
})

export default i18n
