<script setup>
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
</script>

<template>
  <div class="disclaimer-banner" role="alert" aria-live="polite">
    <strong>{{ t('disclaimer.warning', 'Warning:') }}</strong> {{ t('disclaimer.text', 'This tool is under active development and may be unreliable. Use at your own risk. Make sure you have a full backup before proceeding.') }}
  </div>
</template>
