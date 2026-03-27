<script setup>
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { usePubsub } from '@/composables/usePubsub'
import TerminalOutput from '@/components/shared/TerminalOutput.vue'

const { t } = useI18n()
const { get, post } = useApi()
const pubsub = usePubsub()

// ---------------------------------------------------------------------------
// IPFS status
// ---------------------------------------------------------------------------
const ipfsStatus = ref(null)
const statusLoading = ref(true)

async function refreshStatus() {
  statusLoading.value = true
  const { ok, data } = await get('/api/ipfs/status')
  ipfsStatus.value = ok ? data : null
  statusLoading.value = false
}

// ---------------------------------------------------------------------------
// Bitswap stats
// ---------------------------------------------------------------------------
const bitswap = ref(null)
const bitswapLoading = ref(false)

async function refreshBitswap() {
  bitswapLoading.value = true
  const { ok, data } = await get('/api/ipfs/bitswap')
  bitswap.value = ok ? data : null
  bitswapLoading.value = false
}

function formatBytes(bytes) {
  if (bytes == null) return '--'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
}

// ---------------------------------------------------------------------------
// IPFS index (pinned items)
// ---------------------------------------------------------------------------
const index = ref([])
const indexLoading = ref(false)

async function refreshIndex() {
  indexLoading.value = true
  const { ok, data } = await get('/api/ipfs/index')
  index.value = ok ? data : []
  indexLoading.value = false
}

// ---------------------------------------------------------------------------
// CAR export
// ---------------------------------------------------------------------------
const exportTaskId = ref(null)
const selectedKeys = ref([])
const selectAll = ref(false)

function toggleSelectAll() {
  if (selectAll.value) {
    selectedKeys.value = index.value.map(e => e.key)
  } else {
    selectedKeys.value = []
  }
}

async function exportCar() {
  const keys = selectedKeys.value.length ? selectedKeys.value : []
  const { ok, data } = await post('/api/ipfs/car/export', { keys })
  if (ok && data.task_id) exportTaskId.value = data.task_id
}

// ---------------------------------------------------------------------------
// CAR import
// ---------------------------------------------------------------------------
const importPath = ref('')
const importTaskId = ref(null)

async function importCar() {
  if (!importPath.value.trim()) return
  const { ok, data } = await post('/api/ipfs/car/import', { path: importPath.value.trim() })
  if (ok && data.task_id) {
    importTaskId.value = data.task_id
    importPath.value = ''
  }
}

// ---------------------------------------------------------------------------
// PubSub notifications (uses global composable)
// ---------------------------------------------------------------------------
const pubsubMessages = pubsub.messages
const pubsubActive = pubsub.connected

// ---------------------------------------------------------------------------
// Config channel
// ---------------------------------------------------------------------------
const channel = ref(null)
const channelLoading = ref(false)
const channelUpdates = ref(null)
const subscribeInput = ref('')

async function refreshChannel() {
  channelLoading.value = true
  const { ok, data } = await get('/api/ipfs/config-channel')
  channel.value = ok ? data : null
  channelLoading.value = false
}

async function checkChannelUpdates() {
  const { ok, data } = await get('/api/ipfs/config-channel/check')
  channelUpdates.value = ok ? data : null
}

async function subscribeChannel() {
  const val = subscribeInput.value.trim()
  if (!val) return
  const body = val.startsWith('/ipns/') || val.startsWith('k5') || val.startsWith('12D')
    ? { ipns_name: val }
    : { channel_cid: val }
  const { ok, data } = await post('/api/ipfs/config-channel', body)
  if (ok) {
    channel.value = data
    subscribeInput.value = ''
  }
}

async function applyAllUpdates() {
  await post('/api/ipfs/config-channel/apply', { all: true })
  await checkChannelUpdates()
}

// ---------------------------------------------------------------------------
// Lifecycle
// ---------------------------------------------------------------------------
onMounted(async () => {
  // Mark PubSub notifications as read when visiting this page
  pubsub.clearUnread()

  await refreshStatus()
  if (ipfsStatus.value?.available) {
    refreshBitswap()
    refreshIndex()
    refreshChannel()
  }
})
</script>

<template>
  <main class="page-content">
    <h2 class="step-title">IPFS Network</h2>
    <p class="step-desc">Peer-to-peer firmware sharing, offline transfer, and community seeding.</p>

    <!-- Status -->
    <section class="ipfs-section">
      <h3 class="ipfs-section-title">Node Status</h3>
      <div v-if="statusLoading" class="text-dim">Checking IPFS daemon...</div>
      <div v-else-if="!ipfsStatus?.available" class="ipfs-offline">
        IPFS daemon is not running. Start it with <code>ipfs daemon</code> or run <code>make ipfs</code>.
      </div>
      <div v-else class="ipfs-status-grid">
        <div class="ipfs-stat">
          <span class="ipfs-stat-label">Status</span>
          <span class="ipfs-stat-value ipfs-online">Online</span>
        </div>
        <div class="ipfs-stat">
          <span class="ipfs-stat-label">Peer ID</span>
          <span class="ipfs-stat-value ipfs-mono">{{ ipfsStatus.peer_id?.slice(0, 16) }}...</span>
        </div>
        <div class="ipfs-stat">
          <span class="ipfs-stat-label">Agent</span>
          <span class="ipfs-stat-value">{{ ipfsStatus.agent }}</span>
        </div>
      </div>
    </section>

    <!-- Bitswap / Community seeding -->
    <section v-if="ipfsStatus?.available" class="ipfs-section">
      <h3 class="ipfs-section-title">
        Community Seeding
        <button class="btn-sm" @click="refreshBitswap" :disabled="bitswapLoading">Refresh</button>
      </h3>
      <div v-if="bitswapLoading" class="text-dim">Loading stats...</div>
      <div v-else-if="!bitswap" class="text-dim">Bitswap stats unavailable.</div>
      <div v-else class="ipfs-status-grid">
        <div class="ipfs-stat">
          <span class="ipfs-stat-label">Blocks sent</span>
          <span class="ipfs-stat-value">{{ bitswap.blocks_sent ?? '--' }}</span>
        </div>
        <div class="ipfs-stat">
          <span class="ipfs-stat-label">Blocks received</span>
          <span class="ipfs-stat-value">{{ bitswap.blocks_received ?? '--' }}</span>
        </div>
        <div class="ipfs-stat">
          <span class="ipfs-stat-label">Data sent</span>
          <span class="ipfs-stat-value">{{ formatBytes(bitswap.data_sent) }}</span>
        </div>
        <div class="ipfs-stat">
          <span class="ipfs-stat-label">Data received</span>
          <span class="ipfs-stat-value">{{ formatBytes(bitswap.data_received) }}</span>
        </div>
        <div class="ipfs-stat">
          <span class="ipfs-stat-label">Seeding ratio</span>
          <span class="ipfs-stat-value" :class="{ 'ipfs-online': (bitswap.seeding_ratio ?? 0) >= 1 }">
            {{ bitswap.seeding_ratio === Infinity ? 'Seeder' : (bitswap.seeding_ratio ?? 0).toFixed(2) }}
          </span>
        </div>
        <div class="ipfs-stat">
          <span class="ipfs-stat-label">Connected peers</span>
          <span class="ipfs-stat-value">{{ bitswap.peers ?? '--' }}</span>
        </div>
      </div>
    </section>

    <!-- Pinned items -->
    <section v-if="ipfsStatus?.available" class="ipfs-section">
      <h3 class="ipfs-section-title">
        Pinned Content ({{ index.length }})
        <button class="btn-sm" @click="refreshIndex" :disabled="indexLoading">Refresh</button>
      </h3>
      <div v-if="indexLoading" class="text-dim">Loading index...</div>
      <div v-else-if="index.length === 0" class="text-dim">No content pinned yet.</div>
      <div v-else>
        <label class="checklist-item ipfs-select-all">
          <input type="checkbox" v-model="selectAll" @change="toggleSelectAll" />
          <span class="check-label">Select all for export</span>
        </label>
        <div v-for="entry in index" :key="entry.key" class="ipfs-entry">
          <label class="ipfs-entry-check">
            <input type="checkbox" :value="entry.key" v-model="selectedKeys" />
          </label>
          <div class="ipfs-entry-info">
            <strong>{{ entry.filename || entry.key }}</strong>
            <span class="text-dim">{{ entry.codename }}</span>
          </div>
          <div class="ipfs-entry-cid ipfs-mono text-dim">{{ entry.cid?.slice(0, 20) }}...</div>
          <div class="ipfs-entry-size text-dim">{{ formatBytes(entry.size) }}</div>
        </div>
      </div>
    </section>

    <!-- CAR export/import -->
    <section v-if="ipfsStatus?.available" class="ipfs-section">
      <h3 class="ipfs-section-title">Offline Transfer (CAR)</h3>
      <p class="text-dim">Export pinned content as .car files for USB/sneakernet transfer. Import .car files from other OSmosis nodes.</p>

      <div class="ipfs-actions">
        <button class="btn-primary" @click="exportCar" :disabled="index.length === 0">
          Export {{ selectedKeys.length || 'all' }} as .car
        </button>
      </div>
      <TerminalOutput v-if="exportTaskId" :taskId="exportTaskId" @done="exportTaskId = null" />

      <div class="ipfs-import-row">
        <input
          v-model="importPath"
          type="text"
          class="input-field"
          placeholder="/path/to/firmware.car"
          @keyup.enter="importCar"
        />
        <button class="btn-primary" @click="importCar" :disabled="!importPath.trim()">Import .car</button>
      </div>
      <TerminalOutput v-if="importTaskId" :taskId="importTaskId" @done="importTaskId = null; refreshIndex()" />
    </section>

    <!-- Config channel -->
    <section v-if="ipfsStatus?.available" class="ipfs-section">
      <h3 class="ipfs-section-title">Config Channel</h3>
      <div v-if="channelLoading" class="text-dim">Loading...</div>
      <div v-else-if="channel?.subscribed">
        <div class="ipfs-status-grid">
          <div class="ipfs-stat">
            <span class="ipfs-stat-label">Subscribed</span>
            <span class="ipfs-stat-value ipfs-online">Yes</span>
          </div>
          <div v-if="channel.ipns_name" class="ipfs-stat">
            <span class="ipfs-stat-label">IPNS name</span>
            <span class="ipfs-stat-value ipfs-mono">{{ channel.ipns_name?.slice(0, 20) }}...</span>
          </div>
          <div class="ipfs-stat">
            <span class="ipfs-stat-label">Manifest CID</span>
            <span class="ipfs-stat-value ipfs-mono">{{ channel.channel_cid?.slice(0, 20) }}...</span>
          </div>
        </div>
        <div class="ipfs-actions">
          <button class="btn-sm" @click="checkChannelUpdates">Check for updates</button>
        </div>
        <div v-if="channelUpdates">
          <div v-if="channelUpdates.updates_available === 0" class="text-dim">All configs are up to date.</div>
          <div v-else>
            <p>{{ channelUpdates.updates_available }} update(s) available:</p>
            <ul class="ipfs-update-list">
              <li v-for="u in channelUpdates.updates" :key="u.name">
                <strong>{{ u.name }}</strong>
                <span class="text-dim">{{ u.local_cid?.slice(0, 12) || 'none' }} &rarr; {{ u.remote_cid?.slice(0, 12) }}</span>
              </li>
            </ul>
            <button class="btn-primary" @click="applyAllUpdates">Apply all updates</button>
          </div>
          <div v-if="channelUpdates.ipns_resolved" class="text-dim">
            IPNS resolved to a newer manifest automatically.
          </div>
        </div>
      </div>
      <div v-else>
        <p class="text-dim">Not subscribed to any config channel. Enter a CID or IPNS name to subscribe:</p>
        <div class="ipfs-import-row">
          <input
            v-model="subscribeInput"
            type="text"
            class="input-field"
            placeholder="Qm... or /ipns/k51..."
            @keyup.enter="subscribeChannel"
          />
          <button class="btn-primary" @click="subscribeChannel" :disabled="!subscribeInput.trim()">Subscribe</button>
        </div>
      </div>
    </section>

    <!-- PubSub feed -->
    <section v-if="ipfsStatus?.available" class="ipfs-section">
      <h3 class="ipfs-section-title">
        Live Updates (PubSub)
        <button class="btn-sm" @click="pubsubActive ? pubsub.disconnect() : pubsub.connect()">
          {{ pubsubActive ? 'Disconnect' : 'Connect' }}
        </button>
      </h3>
      <div v-if="!pubsubActive && pubsubMessages.length === 0" class="text-dim">
        Connect to hear real-time firmware and config announcements from peers.
      </div>
      <div v-else-if="pubsubMessages.length === 0" class="text-dim">Listening... no messages yet.</div>
      <div v-else class="ipfs-pubsub-feed">
        <div v-for="(msg, i) in pubsubMessages" :key="i" class="ipfs-pubsub-msg">
          <span class="ipfs-pubsub-type">{{ msg.type }}</span>
          <span class="ipfs-pubsub-text">{{ msg.message || msg.cid }}</span>
          <span class="text-dim">{{ msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString() : '' }}</span>
        </div>
      </div>
    </section>
  </main>
</template>

<style scoped>
.ipfs-section {
  margin-bottom: 2rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid var(--c-border, rgba(255,255,255,0.08));
}
.ipfs-section:last-child { border-bottom: none; }
.ipfs-section-title {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 1.1rem;
  margin-bottom: 0.75rem;
}
.ipfs-status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}
.ipfs-stat {
  background: var(--c-surface, rgba(255,255,255,0.03));
  border-radius: 8px;
  padding: 0.75rem 1rem;
}
.ipfs-stat-label {
  display: block;
  font-size: 0.8rem;
  color: var(--c-dim, rgba(255,255,255,0.5));
  margin-bottom: 0.25rem;
}
.ipfs-stat-value {
  font-size: 1.1rem;
  font-weight: 600;
}
.ipfs-online { color: rgba(100, 200, 100, 0.9); }
.ipfs-mono { font-family: monospace; font-size: 0.9rem; word-break: break-all; }
.ipfs-offline {
  background: rgba(200, 80, 80, 0.1);
  border: 1px solid rgba(200, 80, 80, 0.25);
  border-radius: 8px;
  padding: 1rem;
  color: rgba(200, 80, 80, 0.9);
}
.ipfs-offline code {
  background: rgba(255,255,255,0.06);
  padding: 0.15em 0.4em;
  border-radius: 3px;
  font-size: 0.9em;
}
.ipfs-entry {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--c-border, rgba(255,255,255,0.05));
}
.ipfs-entry-check { flex-shrink: 0; }
.ipfs-entry-info { flex: 1; min-width: 0; }
.ipfs-entry-info strong { display: block; }
.ipfs-entry-cid { flex-shrink: 0; }
.ipfs-entry-size { flex-shrink: 0; min-width: 5rem; text-align: right; }
.ipfs-select-all { margin-bottom: 0.5rem; }
.ipfs-actions { display: flex; gap: 0.5rem; margin: 0.75rem 0; }
.ipfs-import-row { display: flex; gap: 0.5rem; margin: 0.75rem 0; }
.ipfs-import-row .input-field { flex: 1; }
.ipfs-update-list {
  list-style: none;
  padding: 0;
  margin: 0.5rem 0;
}
.ipfs-update-list li {
  padding: 0.25rem 0;
  display: flex;
  gap: 0.75rem;
  align-items: baseline;
}
.ipfs-pubsub-feed {
  max-height: 300px;
  overflow-y: auto;
}
.ipfs-pubsub-msg {
  display: flex;
  gap: 0.75rem;
  padding: 0.35rem 0;
  border-bottom: 1px solid var(--c-border, rgba(255,255,255,0.05));
  font-size: 0.9rem;
}
.ipfs-pubsub-type {
  flex-shrink: 0;
  background: rgba(100, 200, 100, 0.15);
  color: rgba(100, 200, 100, 0.9);
  padding: 0.1em 0.5em;
  border-radius: 4px;
  font-size: 0.8rem;
  text-transform: uppercase;
}
.ipfs-pubsub-text { flex: 1; min-width: 0; word-break: break-all; }
.btn-sm {
  font-size: 0.8rem;
  padding: 0.25rem 0.6rem;
  border-radius: 4px;
  background: var(--c-surface, rgba(255,255,255,0.06));
  border: 1px solid var(--c-border, rgba(255,255,255,0.1));
  color: inherit;
  cursor: pointer;
}
.btn-sm:hover { background: rgba(255,255,255,0.1); }
.btn-primary {
  padding: 0.4rem 1rem;
  border-radius: 6px;
  background: rgba(100, 200, 100, 0.15);
  border: 1px solid rgba(100, 200, 100, 0.3);
  color: rgba(100, 200, 100, 0.9);
  cursor: pointer;
  font-weight: 500;
}
.btn-primary:hover { background: rgba(100, 200, 100, 0.25); }
.btn-primary:disabled { opacity: 0.4; cursor: not-allowed; }
.input-field {
  padding: 0.4rem 0.75rem;
  border-radius: 6px;
  background: var(--c-surface, rgba(255,255,255,0.03));
  border: 1px solid var(--c-border, rgba(255,255,255,0.1));
  color: inherit;
  font-family: monospace;
  font-size: 0.9rem;
}
</style>
