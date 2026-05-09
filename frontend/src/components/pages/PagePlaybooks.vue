<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import TerminalOutput from '@/components/shared/TerminalOutput.vue'

const { t } = useI18n()
const { get, post, api } = useApi()

const builtin = ref([])
const userPlaybooks = ref([])
const loading = ref(true)

const selectedId = ref('')
const host = ref('')
const username = ref('root')
const connection = ref('ssh')
const become = ref(true)
const extraVarsText = ref('')

const activeTaskId = ref(null)
const taskRunning = ref(false)

const uploadId = ref('')
const uploadContent = ref('')
const uploadError = ref('')

const allPlaybooks = computed(() => [...builtin.value, ...userPlaybooks.value])

async function refresh() {
  loading.value = true
  const { ok, data } = await get('/api/playbooks')
  loading.value = false
  if (ok) {
    builtin.value = data.builtin || []
    userPlaybooks.value = data.user || []
  }
}

async function runPlaybook() {
  const body = {
    playbook: selectedId.value,
    host: host.value,
    user: username.value,
    connection: connection.value,
    become: become.value,
  }
  if (extraVarsText.value.trim()) {
    try {
      body.extra_vars = JSON.parse(extraVarsText.value)
    } catch (e) {
      alert('extra_vars must be valid JSON: ' + e.message)
      return
    }
  }
  const { ok, data } = await post('/api/playbooks/run', body)
  if (ok && data.task_id) {
    activeTaskId.value = data.task_id
    taskRunning.value = true
  }
}

function onTaskDone() {
  taskRunning.value = false
}

async function upload() {
  uploadError.value = ''
  const { ok, data, status } = await post('/api/playbooks/upload', {
    id: uploadId.value,
    content: uploadContent.value,
  })
  if (!ok) {
    uploadError.value = data?.error || `HTTP ${status}`
    return
  }
  uploadId.value = ''
  uploadContent.value = ''
  await refresh()
}

async function remove(pid) {
  if (!confirm(t('playbooks.confirmDelete', `Delete playbook "${pid}"?`))) return
  await api(`/api/playbooks/${pid}`, { method: 'DELETE' })
  await refresh()
}

onMounted(refresh)
</script>

<template>
  <main class="page-content">
    <h2 class="step-title">{{ t('playbooks.title', 'Post-Flash Playbooks') }}</h2>
    <p class="step-desc">
      {{ t('playbooks.desc', 'Configure a freshly-flashed device with Ansible — Wi-Fi, locale, packages, SSH keys, hardening.') }}
    </p>

    <section class="pb-section">
      <h3>{{ t('playbooks.available', 'Available') }}</h3>
      <div v-if="loading" class="text-dim">Loading…</div>
      <div v-else class="pb-list">
        <article
          v-for="pb in allPlaybooks"
          :key="pb.id"
          class="pb-card"
          :class="{ active: selectedId === pb.id }"
          @click="selectedId = pb.id"
        >
          <header>
            <strong>{{ pb.name }}</strong>
            <span :class="['badge', pb.source === 'builtin' ? 'badge-cyan' : 'badge-green']">
              {{ pb.source }}
            </span>
          </header>
          <p v-if="pb.description" class="text-dim">{{ pb.description }}</p>
          <button v-if="pb.source === 'user'" class="btn-link danger" @click.stop="remove(pb.id)">
            {{ t('playbooks.delete', 'Delete') }}
          </button>
        </article>
      </div>
    </section>

    <section class="pb-section">
      <h3>{{ t('playbooks.run', 'Run') }}</h3>
      <div class="pb-form">
        <label>
          {{ t('playbooks.host', 'Host (IP or DNS)') }}
          <input v-model="host" placeholder="192.168.1.50" />
        </label>
        <label>
          {{ t('playbooks.user', 'User') }}
          <input v-model="username" />
        </label>
        <label>
          {{ t('playbooks.connection', 'Connection') }}
          <select v-model="connection">
            <option value="ssh">SSH</option>
            <option value="local">Local (this machine)</option>
          </select>
        </label>
        <label class="pb-checkbox">
          <input v-model="become" type="checkbox" />
          {{ t('playbooks.become', 'Use sudo on target') }}
        </label>
        <label class="pb-extra">
          {{ t('playbooks.extraVars', 'extra_vars (JSON)') }}
          <textarea v-model="extraVarsText" rows="3" placeholder='{"wifi_ssid": "home", "wifi_password": "..."}' />
        </label>
        <button class="btn-primary" :disabled="!selectedId || taskRunning" @click="runPlaybook">
          {{ taskRunning ? t('playbooks.running', 'Running…') : t('playbooks.runNow', 'Run playbook') }}
        </button>
      </div>
    </section>

    <section v-if="activeTaskId" class="pb-section">
      <h3>{{ t('playbooks.output', 'Output') }}</h3>
      <TerminalOutput :task-id="activeTaskId" @done="onTaskDone" />
    </section>

    <section class="pb-section">
      <h3>{{ t('playbooks.upload', 'Upload custom playbook') }}</h3>
      <div class="pb-form">
        <label>
          {{ t('playbooks.uploadId', 'Identifier (lowercase, dashes ok)') }}
          <input v-model="uploadId" placeholder="my-playbook" />
        </label>
        <label class="pb-extra">
          {{ t('playbooks.yaml', 'Playbook YAML') }}
          <textarea v-model="uploadContent" rows="10" spellcheck="false" />
        </label>
        <p v-if="uploadError" class="text-error">{{ uploadError }}</p>
        <button class="btn-primary" :disabled="!uploadId || !uploadContent" @click="upload">
          {{ t('playbooks.save', 'Save playbook') }}
        </button>
      </div>
    </section>
  </main>
</template>

<style scoped>
.pb-section { margin-bottom: 2rem; }
.pb-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 0.75rem;
}
.pb-card {
  border: 1px solid var(--border, #333);
  border-radius: 6px;
  padding: 0.75rem;
  cursor: pointer;
  background: var(--surface, transparent);
}
.pb-card.active {
  border-color: var(--accent, #5cf);
  background: rgba(90, 200, 255, 0.08);
}
.pb-card header {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
  align-items: center;
  margin-bottom: 0.25rem;
}
.pb-form {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 0.75rem;
  align-items: end;
}
.pb-form label {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.9rem;
}
.pb-form input,
.pb-form select,
.pb-form textarea {
  padding: 0.4rem 0.5rem;
  border-radius: 4px;
  border: 1px solid var(--border, #333);
  background: var(--surface, #1a1a1a);
  color: var(--text, inherit);
  font-family: inherit;
}
.pb-form textarea { font-family: monospace; }
.pb-extra { grid-column: 1 / -1; }
.pb-checkbox {
  flex-direction: row;
  align-items: center;
  gap: 0.5rem;
}
.btn-link.danger { color: var(--danger, #f44336); }
.text-error { color: var(--danger, #f44336); margin: 0.25rem 0; }
</style>
