<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'

const { t } = useI18n()
const { post } = useApi()

const preflightType = ref('phone')
const preflightResult = ref(null)
const preflightLoading = ref(false)

async function runPreflight() {
  preflightLoading.value = true
  preflightResult.value = null
  const { ok, data } = await post(`/api/preflight/${preflightType.value}`, {})
  preflightLoading.value = false
  if (ok) preflightResult.value = data
}
</script>

<template>
  <main class="page-content">
    <h2 class="step-title">{{ t('adv.preflight.title', 'Pre-Flight Check') }}</h2>
    <p class="step-desc">{{ t('adv.preflight.desc', 'Run a safety checklist before flashing. Select your device type:') }}</p>

    <div class="form-group">
      <label class="form-label">Device type</label>
      <select v-model="preflightType" class="form-input">
        <option value="phone">Phone / Tablet (ADB)</option>
        <option value="scooter">Scooter (BLE)</option>
        <option value="pixel">Google Pixel (Fastboot)</option>
      </select>
    </div>

    <div class="step-actions">
      <button
        class="btn btn-large btn-primary"
        :class="{ 'btn-loading': preflightLoading }"
        :disabled="preflightLoading"
        @click="runPreflight"
      >
        {{ t('btn.check', 'Check Now') }}
      </button>
    </div>

    <div v-if="preflightResult" style="margin-top: 1.5rem;">
      <div :class="['info-box', preflightResult.passed ? 'info-box--success' : 'info-box--warn']">
        <strong>{{ preflightResult.passed ? 'All required checks passed' : 'Some checks failed' }}</strong>
        &mdash; {{ preflightResult.passed_count }}/{{ preflightResult.total }} passed
      </div>
      <div v-for="check in preflightResult.checks" :key="check.id" class="preflight-check">
        <span class="preflight-icon">{{ check.passed ? '\u2705' : (check.required ? '\u274C' : '\u26A0\uFE0F') }}</span>
        <div>
          <strong>{{ check.label }}</strong>
          <span v-if="!check.required" class="text-dim"> (optional)</span>
          <div class="text-dim" style="font-size: 0.85em;">{{ check.detail }}</div>
        </div>
      </div>
    </div>
  </main>
</template>
