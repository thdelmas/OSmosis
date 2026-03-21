<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'

const { t } = useI18n()
const { get } = useApi()

const registryEntries = ref([])
const registryLoading = ref(true)

onMounted(async () => {
  const { ok, data } = await get('/api/registry')
  registryLoading.value = false
  if (ok) registryEntries.value = data
})
</script>

<template>
  <main class="page-content">
    <h2 class="step-title">{{ t('adv.registry.title', 'Firmware Registry') }}</h2>
    <p class="step-desc">{{ t('adv.registry.desc', 'Every firmware file Osmosis has flashed, with SHA256 hashes for verification.') }}</p>

    <div v-if="registryLoading" class="text-dim">Loading...</div>
    <div v-else-if="registryEntries.length === 0" class="text-dim">
      No firmware has been registered yet. Flash a device to start building the registry.
    </div>
    <div v-else>
      <div v-for="(entry, i) in registryEntries" :key="i" class="registry-entry">
        <div class="registry-header">
          <strong>{{ entry.device_label || entry.filename }}</strong>
          <span v-if="entry.version" class="text-dim">v{{ entry.version }}</span>
        </div>
        <div class="registry-details text-dim">
          <div>{{ entry.filename }} ({{ Math.round(entry.size / 1024) }}K)</div>
          <div class="registry-hash">SHA256: {{ entry.sha256 }}</div>
          <div v-if="entry.flash_method">Method: {{ entry.flash_method }}</div>
          <div v-if="entry.flashed_at">{{ new Date(entry.flashed_at).toLocaleString() }}</div>
        </div>
      </div>
    </div>
  </main>
</template>
