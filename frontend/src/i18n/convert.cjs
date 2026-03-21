#!/usr/bin/env node
/**
 * Convert the legacy i18n.js (LANGS + T objects) to vue-i18n JSON locale files.
 *
 * Usage: node convert.cjs ../web/static/i18n.js
 * Output: en.json, fr.json, br.json, etc. in the same directory as this script.
 */

const fs = require('fs')
const path = require('path')
const vm = require('vm')

const inputPath = process.argv[2] || path.resolve(__dirname, '..', '..', '..', 'web', 'static', 'i18n.js')
const outputDir = __dirname

const code = fs.readFileSync(inputPath, 'utf-8')

// Extract LANGS and T by evaluating in a sandbox
// Provide stubs for browser globals referenced in the runtime part of i18n.js
const sandbox = {
  localStorage: { getItem: () => null, setItem: () => {} },
  navigator: { language: 'en' },
  document: {
    querySelectorAll: () => [],
    getElementById: () => null,
    documentElement: { lang: 'en' },
  },
}
const wrappedCode = code
  .replace(/\/\/ *----.*$/gm, '')
  + '\n__LANGS = LANGS; __T = T;'

try {
  vm.runInNewContext(wrappedCode, sandbox)
} catch (e) {
  console.error('VM eval failed:', e.message)
  process.exit(1)
}

const LANGS = sandbox.__LANGS
const T = sandbox.__T

if (!LANGS || !T) {
  console.error('Could not extract LANGS or T from i18n.js')
  process.exit(1)
}

// Build per-language message objects
const messages = {}
for (const lang of Object.keys(LANGS)) {
  messages[lang] = {}
}

for (const [key, translations] of Object.entries(T)) {
  for (const [lang, text] of Object.entries(translations)) {
    if (messages[lang] !== undefined) {
      // Convert dotted keys to nested: "step.category.title" -> { step: { category: { title: ... } } }
      const parts = key.split('.')
      let obj = messages[lang]
      for (let i = 0; i < parts.length - 1; i++) {
        if (!(parts[i] in obj)) obj[parts[i]] = {}
        if (typeof obj[parts[i]] === 'string') {
          // Conflict: key is both a leaf and a branch. Use _self for the leaf.
          obj[parts[i]] = { _self: obj[parts[i]] }
        }
        obj = obj[parts[i]]
      }
      obj[parts[parts.length - 1]] = text
    }
  }
}

// Write JSON files
for (const [lang, msgs] of Object.entries(messages)) {
  const outPath = path.join(outputDir, `${lang}.json`)
  fs.writeFileSync(outPath, JSON.stringify(msgs, null, 2) + '\n')
  const keyCount = Object.keys(T).filter(k => T[k][lang]).length
  console.log(`${lang}.json: ${keyCount} keys`)
}

console.log(`\nDone. Output: ${outputDir}`)
