<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'

const { t } = useI18n()
const { get } = useApi()
const router = useRouter()

const devices = ref([])
const loading = ref(true)
const lastScan = ref(null)
const filter = ref('all')
let pollTimer = null

const TYPE_LABELS = {
  usb: 'USB',
  adb: 'ADB',
  serial: 'Serial',
  ble: 'BLE',
  network: 'Network',
}

const TYPE_COLORS = {
  usb: 'var(--info, #2196f3)',
  adb: 'var(--success, #4caf50)',
  serial: '#9c27b0',
  ble: '#00bcd4',
  network: 'var(--warning, #ff9800)',
}

async function refresh() {
  const { ok, data } = await get('/api/inventory')
  loading.value = false
  if (ok && Array.isArray(data)) {
    devices.value = data
    lastScan.value = new Date()
  }
}

const grouped = computed(() => {
  const out = { usb: [], adb: [], serial: [], ble: [], network: [] }
  for (const d of devices.value) {
    if (filter.value !== 'all' && d.type !== filter.value) continue
    if (out[d.type]) out[d.type].push(d)
  }
  return out
})

const counts = computed(() => {
  const c = { all: devices.value.length, usb: 0, adb: 0, serial: 0, ble: 0, network: 0 }
  for (const d of devices.value) {
    if (c[d.type] !== undefined) c[d.type]++
  }
  return c
})

function actionsFor(dev) {
  const out = []
  if (dev.profile_id) {
    const cat = dev.details?.category || 'phone'
    out.push({
      label: t('inventory.openProfile', 'Open device'),
      run: () => router.push({ name: 'device', params: { type: cat, id: dev.profile_id } }),
    })
  }
  if (dev.type === 'adb' && dev.serial) {
    out.push({
      label: t('inventory.openLive', 'Live device'),
      run: () => router.push({ name: 'connected-device', params: { serial: dev.serial } }),
    })
  }
  if (dev.profile_id) {
    out.push({
      label: t('inventory.flash', 'Flash workflow'),
      run: () => router.push({ name: 'flash-stock', query: { device: dev.profile_id } }),
    })
  }
  return out
}

onMounted(() => {
  refresh()
  pollTimer = setInterval(refresh, 8000)
})
onUnmounted(() => clearInterval(pollTimer))
</script>

<template>
  <main class="page-content">
    <div class="inv-header">
      <div>
        <h2 class="step-title">{{ t('inventory.title', 'Device Inventory') }}</h2>
        <p class="step-desc">
          {{ t('inventory.desc', 'Every device OSmosis can see right now — USB, ADB, serial, Bluetooth, and the local network.') }}
        </p>
      </div>
      <button class="btn-secondary" :disabled="loading" @click="refresh">
        {{ loading ? t('inventory.scanning', 'Scanning…') : t('inventory.rescan', 'Rescan') }}
      </button>
    </div>

    <div class="inv-filters" role="tablist">
      <button
        v-for="t in ['all', 'usb', 'adb', 'serial', 'ble', 'network']"
        :key="t"
        role="tab"
        :aria-selected="filter === t"
        :class="['inv-filter', { active: filter === t }]"
        @click="filter = t"
      >
        {{ t === 'all' ? 'All' : (TYPE_LABELS[t] || t) }}
        <span class="inv-filter-count">{{ counts[t] }}</span>
      </button>
    </div>

    <div v-if="loading && !devices.length" class="text-dim">
      {{ t('inventory.scanning', 'Scanning…') }}
    </div>
    <div v-else-if="!devices.length" class="text-dim">
      {{ t('inventory.empty', 'No devices detected. Plug in USB, enable ADB, or check that your network has discoverable services.') }}
    </div>

    <template v-for="(group, type) in grouped" :key="type">
      <section v-if="group.length" class="inv-group">
        <div class="inv-group-header">
          <span class="inv-type-dot" :style="{ background: TYPE_COLORS[type] }"></span>
          <h3 class="inv-group-title">{{ TYPE_LABELS[type] || type }}</h3>
          <span class="text-dim">{{ group.length }}</span>
        </div>
        <div class="inv-cards">
          <article v-for="d in group" :key="d.id" class="inv-card">
            <header class="inv-card-header">
              <strong>{{ d.name || d.id }}</strong>
              <span v-if="d.profile_id" class="badge badge-green" :title="t('inventory.matched', 'Matched device profile')">
                {{ d.profile_id }}
              </span>
              <span v-else class="badge badge-dim" :title="t('inventory.unmatched', 'No matching device profile')">
                {{ t('inventory.unmatched', 'unmatched') }}
              </span>
            </header>
            <dl class="inv-card-meta text-dim">
              <template v-if="d.vendor">
                <dt>{{ t('inventory.vendor', 'Vendor') }}</dt><dd>{{ d.vendor }}</dd>
              </template>
              <template v-if="d.model">
                <dt>{{ t('inventory.model', 'Model') }}</dt><dd>{{ d.model }}</dd>
              </template>
              <template v-if="d.serial">
                <dt>{{ t('inventory.serial', 'Serial') }}</dt><dd>{{ d.serial }}</dd>
              </template>
              <template v-if="d.connection">
                <dt>{{ t('inventory.connection', 'Connection') }}</dt><dd>{{ d.connection }}</dd>
              </template>
              <template v-if="d.status && d.status !== 'detected'">
                <dt>{{ t('inventory.status', 'Status') }}</dt><dd>{{ d.status }}</dd>
              </template>
            </dl>
            <div v-if="actionsFor(d).length" class="inv-card-actions">
              <button
                v-for="(a, i) in actionsFor(d)"
                :key="i"
                class="btn-link"
                @click="a.run"
              >
                {{ a.label }}
              </button>
            </div>
          </article>
        </div>
      </section>
    </template>

    <p v-if="lastScan" class="inv-footer text-dim">
      {{ t('inventory.lastScan', 'Last scan') }}: {{ lastScan.toLocaleTimeString() }}
    </p>
  </main>
</template>

<style scoped>
.inv-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  flex-wrap: wrap;
}
.inv-filters {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin: 1rem 0 1.5rem;
}
.inv-filter {
  background: transparent;
  border: 1px solid var(--border, #444);
  color: var(--text, inherit);
  padding: 0.35rem 0.75rem;
  border-radius: 999px;
  cursor: pointer;
  font-size: 0.9rem;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}
.inv-filter.active {
  background: var(--accent, #5cf);
  color: #000;
  border-color: var(--accent, #5cf);
}
.inv-filter-count {
  opacity: 0.7;
  font-variant-numeric: tabular-nums;
}
.inv-group { margin-bottom: 1.5rem; }
.inv-group-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}
.inv-type-dot {
  width: 0.6rem;
  height: 0.6rem;
  border-radius: 50%;
}
.inv-group-title { margin: 0; font-size: 1rem; }
.inv-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 0.75rem;
}
.inv-card {
  border: 1px solid var(--border, #333);
  border-radius: 6px;
  padding: 0.75rem;
  background: var(--surface, transparent);
}
.inv-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}
.inv-card-meta {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.25rem 0.75rem;
  font-size: 0.85rem;
  margin: 0;
}
.inv-card-meta dt { font-weight: 500; }
.inv-card-meta dd { margin: 0; word-break: break-word; }
.inv-card-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.5rem;
  flex-wrap: wrap;
}
.btn-link {
  background: transparent;
  border: none;
  color: var(--accent, #5cf);
  cursor: pointer;
  padding: 0.25rem 0;
  font-size: 0.9rem;
  text-decoration: underline;
}
.inv-footer { margin-top: 1.5rem; font-size: 0.8rem; }
</style>
