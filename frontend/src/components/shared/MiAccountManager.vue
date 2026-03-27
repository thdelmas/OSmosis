<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps({
  deviceRegion: { type: String, default: '' },
  selectable: { type: Boolean, default: false },
  selectedAccountId: { type: String, default: '' },
})

const emit = defineEmits(['select', 'session-ready'])

// --- Account list ---
const accounts = ref([])
const loadingAccounts = ref(false)
const loadError = ref('')

// --- Add account form ---
const showAddForm = ref(false)
const addEmail = ref('')
const addPassword = ref('')
const addLabel = ref('')
const addLoading = ref(false)
const addError = ref('')

// --- Delete confirmation ---
const confirmDeleteId = ref(null)

// --- Proxy / Tor ---
const proxyUrl = ref('')
const proxySaving = ref(false)
const proxyStatus = ref('')  // '' | 'saved' | 'error'
const torState = ref(null)   // null | { installed, running, proxy }
const torStarting = ref(false)

// --- Login / 2FA flow (per-account, keyed by account id) ---
const loginState = ref({})
// Each entry: { step: 'idle'|'logging-in'|'2fa-method'|'2fa-code'|'verifying'|'done',
//               methods: [], selectedMethod: '', code: '', error: '', attemptsLeft: null }

function getLoginState(id) {
  if (!loginState.value[id]) {
    loginState.value[id] = {
      step: 'idle',
      methods: [],
      selectedMethod: '',
      code: '',
      error: '',
      attemptsLeft: null,
    }
  }
  return loginState.value[id]
}

// --- Helpers ---
function maskEmail(email) {
  if (!email) return ''
  const [local, domain] = email.split('@')
  if (!domain) return email
  const visible = local.slice(0, 3)
  return `${visible}***@${domain}`
}

function regionLabel(code) {
  const map = {
    cn: 'China', global: 'Global', eu: 'Europe', in: 'India',
    ru: 'Russia', id: 'Indonesia', tw: 'Taiwan',
  }
  return map[code?.toLowerCase()] || code || 'Unknown'
}

function isCompatible(account) {
  if (!props.deviceRegion) return null
  if (!account.region) return null
  return account.region.toLowerCase() === props.deviceRegion.toLowerCase()
}

// --- API calls ---
async function fetchAccounts() {
  loadingAccounts.value = true
  loadError.value = ''
  try {
    const res = await fetch('/api/mi-accounts/')
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    accounts.value = data.accounts || data || []
  } catch (e) {
    loadError.value = e.message || 'Failed to load accounts'
  } finally {
    loadingAccounts.value = false
  }
}

async function addAccount() {
  if (!addEmail.value.trim() || !addPassword.value.trim()) return
  addLoading.value = true
  addError.value = ''
  try {
    const res = await fetch('/api/mi-accounts/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: addEmail.value.trim(),
        password: addPassword.value.trim(),
        label: addLabel.value.trim() || undefined,
      }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.error || `HTTP ${res.status}`)
    }
    addEmail.value = ''
    addPassword.value = ''
    addLabel.value = ''
    showAddForm.value = false
    await fetchAccounts()
  } catch (e) {
    addError.value = e.message || 'Failed to add account'
  } finally {
    addLoading.value = false
  }
}

async function deleteAccount(id) {
  try {
    const res = await fetch(`/api/mi-accounts/${id}`, { method: 'DELETE' })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    confirmDeleteId.value = null
    delete loginState.value[id]
    await fetchAccounts()
  } catch {
    // silently retry on next attempt
  }
}

async function startLogin(account) {
  const ls = getLoginState(account.id)
  ls.step = 'logging-in'
  ls.error = ''
  try {
    const res = await fetch(`/api/mi-accounts/${account.id}/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) {
      ls.error = data.error || `Login failed (HTTP ${res.status})`
      ls.step = 'idle'
      return
    }
    if (data.requires_2fa || data['2fa_required']) {
      ls.methods = data.methods || ['email', 'phone']
      ls.attemptsLeft = data.attempts_left ?? null
      ls.step = '2fa-method'
    } else {
      // Login succeeded without 2FA
      ls.step = 'done'
      await fetchAccounts()
      emit('session-ready', account)
    }
  } catch (e) {
    ls.error = e.message || 'Login request failed'
    ls.step = 'idle'
  }
}

async function sendCode(account) {
  const ls = getLoginState(account.id)
  ls.error = ''
  try {
    const res = await fetch(`/api/mi-accounts/${account.id}/send-code`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ method: ls.selectedMethod }),
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) {
      ls.error = data.error || 'Failed to send verification code'
      return
    }
    ls.attemptsLeft = data.attempts_left ?? ls.attemptsLeft
    ls.step = '2fa-code'
  } catch (e) {
    ls.error = e.message || 'Failed to send code'
  }
}

async function verifyCode(account) {
  const ls = getLoginState(account.id)
  ls.step = 'verifying'
  ls.error = ''
  try {
    const res = await fetch(`/api/mi-accounts/${account.id}/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code: ls.code, method: ls.selectedMethod }),
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) {
      ls.error = data.error || 'Verification failed'
      ls.attemptsLeft = data.attempts_left ?? ls.attemptsLeft
      ls.step = '2fa-code'
      return
    }
    ls.step = 'done'
    await fetchAccounts()
    emit('session-ready', account)
  } catch (e) {
    ls.error = e.message || 'Verification request failed'
    ls.step = '2fa-code'
  }
}

function resetLogin(id) {
  loginState.value[id] = {
    step: 'idle',
    methods: [],
    selectedMethod: '',
    code: '',
    error: '',
    attemptsLeft: null,
  }
}

function selectAccount(account) {
  if (!props.selectable) return
  emit('select', account)
}

async function fetchProxy() {
  try {
    const res = await fetch('/api/mi-accounts/proxy')
    if (res.ok) {
      const data = await res.json()
      proxyUrl.value = data.proxy || ''
    }
  } catch { /* ignore */ }
}

async function fetchTorStatus() {
  try {
    const res = await fetch('/api/mi-accounts/tor')
    if (res.ok) torState.value = await res.json()
  } catch { /* ignore */ }
}

async function startTor() {
  torStarting.value = true
  try {
    const res = await fetch('/api/mi-accounts/tor/start', { method: 'POST' })
    const data = await res.json()
    if (data.ok) {
      proxyUrl.value = data.proxy
      proxyStatus.value = 'saved'
      setTimeout(() => { proxyStatus.value = '' }, 3000)
    } else {
      proxyStatus.value = 'error'
      torState.value = { ...torState.value, error: data.error }
    }
    await fetchTorStatus()
  } catch {
    proxyStatus.value = 'error'
  } finally {
    torStarting.value = false
  }
}

async function useTorProxy() {
  proxyUrl.value = 'socks5://127.0.0.1:9050'
  await saveProxy()
}

async function saveProxy() {
  proxySaving.value = true
  proxyStatus.value = ''
  try {
    const res = await fetch('/api/mi-accounts/proxy', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ proxy: proxyUrl.value.trim() }),
    })
    proxyStatus.value = res.ok ? 'saved' : 'error'
  } catch {
    proxyStatus.value = 'error'
  } finally {
    proxySaving.value = false
    if (proxyStatus.value === 'saved') {
      setTimeout(() => { proxyStatus.value = '' }, 3000)
    }
  }
}

onMounted(() => {
  fetchAccounts()
  fetchProxy()
  fetchTorStatus()
})
</script>

<template>
  <div class="mi-account-manager">

    <!-- Loading -->
    <div v-if="loadingAccounts && accounts.length === 0" class="mi-loading">
      <span class="spinner-small"></span> Loading accounts...
    </div>

    <!-- Load error -->
    <div v-if="loadError" class="banner banner-warn mi-error-banner">
      {{ loadError }}
      <button class="btn btn-link" @click="fetchAccounts">Retry</button>
    </div>

    <!-- Account list -->
    <div v-if="accounts.length > 0" class="mi-account-list">
      <div
        v-for="account in accounts"
        :key="account.id"
        class="mi-account-row"
        :class="{
          'mi-account-row--selectable': selectable,
          'mi-account-row--selected': selectable && selectedAccountId === account.id,
          'mi-account-row--compatible': isCompatible(account) === true,
          'mi-account-row--incompatible': isCompatible(account) === false,
        }"
        @click="selectAccount(account)"
      >
        <div class="mi-account-info">
          <div class="mi-account-primary">
            <span class="mi-session-dot" :class="account.session_active ? 'dot-active' : 'dot-expired'"></span>
            <span class="mi-account-email">{{ maskEmail(account.email) }}</span>
            <span v-if="account.label" class="mi-account-label">{{ account.label }}</span>
          </div>
          <div class="mi-account-meta">
            <span class="badge mi-region-badge">{{ regionLabel(account.region) }}</span>
            <span v-if="isCompatible(account) === true" class="badge badge-compatible">Compatible</span>
            <span v-else-if="isCompatible(account) === false" class="badge badge-incompatible">Incompatible</span>
            <span class="mi-session-label">{{ account.session_active ? 'Session active' : 'No session' }}</span>
          </div>
        </div>

        <div class="mi-account-actions">
          <button
            v-if="!account.session_active && getLoginState(account.id).step === 'idle'"
            class="btn btn-primary btn-sm"
            @click.stop="startLogin(account)"
          >Login</button>
          <button
            v-if="confirmDeleteId !== account.id"
            class="btn btn-link btn-sm mi-delete-btn"
            @click.stop="confirmDeleteId = account.id"
          >Delete</button>
          <template v-if="confirmDeleteId === account.id">
            <span class="mi-confirm-text">Delete?</span>
            <button class="btn btn-link btn-sm mi-confirm-yes" @click.stop="deleteAccount(account.id)">Yes</button>
            <button class="btn btn-link btn-sm" @click.stop="confirmDeleteId = null">No</button>
          </template>
        </div>

        <!-- Inline login / 2FA flow -->
        <div
          v-if="getLoginState(account.id).step !== 'idle'"
          class="mi-login-flow"
          @click.stop
        >
          <!-- Logging in -->
          <div v-if="getLoginState(account.id).step === 'logging-in'" class="mi-flow-step">
            <span class="spinner-small"></span> Logging in...
          </div>

          <!-- 2FA method selection -->
          <div v-if="getLoginState(account.id).step === '2fa-method'" class="mi-flow-step">
            <p class="mi-flow-label">Two-factor authentication required. Select a method:</p>
            <div class="mi-2fa-methods">
              <button
                v-for="method in getLoginState(account.id).methods"
                :key="method"
                class="btn btn-sm"
                :class="getLoginState(account.id).selectedMethod === method ? 'btn-primary' : 'btn-secondary'"
                @click="getLoginState(account.id).selectedMethod = method"
              >{{ method === 'email' ? 'Email' : method === 'phone' ? 'Phone' : method }}</button>
            </div>
            <button
              class="btn btn-primary btn-sm"
              :disabled="!getLoginState(account.id).selectedMethod"
              @click="sendCode(account)"
            >Send code</button>
          </div>

          <!-- 2FA code input -->
          <div v-if="getLoginState(account.id).step === '2fa-code'" class="mi-flow-step">
            <p class="mi-flow-label">
              Enter the verification code sent via {{ getLoginState(account.id).selectedMethod }}:
            </p>
            <div class="mi-code-row">
              <input
                v-model="getLoginState(account.id).code"
                class="form-input mi-code-input"
                type="text"
                inputmode="numeric"
                placeholder="000000"
                autocomplete="one-time-code"
                @keydown.enter="verifyCode(account)"
              />
              <button
                class="btn btn-primary btn-sm"
                :disabled="!getLoginState(account.id).code.trim()"
                @click="verifyCode(account)"
              >Verify</button>
            </div>
            <p v-if="getLoginState(account.id).attemptsLeft != null" class="mi-attempts">
              {{ getLoginState(account.id).attemptsLeft }} attempt{{ getLoginState(account.id).attemptsLeft === 1 ? '' : 's' }} remaining
            </p>
          </div>

          <!-- Verifying -->
          <div v-if="getLoginState(account.id).step === 'verifying'" class="mi-flow-step">
            <span class="spinner-small"></span> Verifying code...
          </div>

          <!-- Done -->
          <div v-if="getLoginState(account.id).step === 'done'" class="mi-flow-step mi-flow-done">
            <span class="mi-done-icon">&#x2705;</span> Session established
            <button class="btn btn-link btn-sm" @click="resetLogin(account.id)">Dismiss</button>
          </div>

          <!-- Error -->
          <div v-if="getLoginState(account.id).error" class="mi-flow-error">
            {{ getLoginState(account.id).error }}
            <button class="btn btn-link btn-sm" @click="getLoginState(account.id).step === 'idle' ? null : startLogin(account)">
              Retry
            </button>
            <button class="btn btn-link btn-sm" @click="resetLogin(account.id)">Cancel</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-if="!loadingAccounts && !loadError && accounts.length === 0" class="mi-empty">
      No Mi accounts saved. Add one below.
    </div>

    <!-- Add account toggle -->
    <div class="mi-add-section">
      <button
        v-if="!showAddForm"
        class="btn btn-secondary btn-sm"
        @click="showAddForm = true"
      >+ Add Mi account</button>

      <div v-if="showAddForm" class="mi-add-form">
        <h4 class="mi-add-title">Add Mi account</h4>
        <label class="form-label">
          Email
          <input
            v-model="addEmail"
            class="form-input"
            type="email"
            placeholder="your@email.com"
            autocomplete="email"
          />
        </label>
        <label class="form-label">
          Password
          <input
            v-model="addPassword"
            class="form-input"
            type="password"
            placeholder="Mi account password"
            autocomplete="new-password"
          />
        </label>
        <label class="form-label">
          Label <span class="text-dim">(optional)</span>
          <input
            v-model="addLabel"
            class="form-input"
            type="text"
            placeholder="e.g. Work account"
          />
        </label>

        <div v-if="addError" class="mi-flow-error">{{ addError }}</div>

        <div class="mi-add-actions">
          <button
            class="btn btn-primary btn-sm"
            :class="{ 'btn-loading': addLoading }"
            :disabled="!addEmail.trim() || !addPassword.trim() || addLoading"
            @click="addAccount"
          >Add</button>
          <button class="btn btn-link btn-sm" @click="showAddForm = false; addError = ''">Cancel</button>
        </div>
      </div>
    </div>

    <!-- Proxy configuration -->
    <details class="mi-proxy-section">
      <summary class="mi-proxy-toggle">Proxy / VPN settings</summary>
      <div class="mi-proxy-form">
        <p class="mi-proxy-hint">
          If Xiaomi servers are blocked in your region, route API calls through a proxy.
        </p>

        <!-- Tor quick option -->
        <div v-if="torState" class="mi-tor-box">
          <div class="mi-tor-row">
            <span class="mi-tor-label">
              Tor
              <span v-if="!torState.installed" class="mi-tor-badge mi-tor-missing">not installed</span>
              <span v-else-if="torState.running" class="mi-tor-badge mi-tor-running">running</span>
              <span v-else class="mi-tor-badge mi-tor-stopped">stopped</span>
            </span>
            <button
              v-if="torState.installed && torState.running && proxyUrl !== 'socks5://127.0.0.1:9050'"
              class="btn btn-secondary btn-sm"
              @click="useTorProxy"
            >Use Tor</button>
            <button
              v-else-if="torState.installed && !torState.running"
              class="btn btn-secondary btn-sm"
              :disabled="torStarting"
              @click="startTor"
            >{{ torStarting ? 'Starting...' : 'Start Tor' }}</button>
            <span v-else-if="!torState.installed" class="mi-tor-install">
              <code>sudo apt install tor</code>
            </span>
            <span v-else-if="proxyUrl === 'socks5://127.0.0.1:9050'" class="mi-proxy-ok">Active</span>
          </div>
          <div v-if="torState.error" class="mi-proxy-status mi-proxy-err">{{ torState.error }}</div>
        </div>

        <!-- Manual proxy -->
        <div class="mi-proxy-input-row">
          <input
            v-model="proxyUrl"
            class="form-input"
            type="text"
            placeholder="socks5://127.0.0.1:1080"
            @keyup.enter="saveProxy"
          />
          <button
            class="btn btn-secondary btn-sm"
            :disabled="proxySaving"
            @click="saveProxy"
          >{{ proxyUrl.trim() ? 'Save' : 'Clear' }}</button>
        </div>
        <div v-if="proxyStatus === 'saved'" class="mi-proxy-status mi-proxy-ok">Proxy updated.</div>
        <div v-if="proxyStatus === 'error'" class="mi-proxy-status mi-proxy-err">Failed to save proxy.</div>
        <p class="mi-proxy-examples">
          Supports <code>socks5://</code>, <code>http://</code>, <code>socks4://</code>
        </p>
      </div>
    </details>

  </div>
</template>

<style scoped>
.mi-account-manager {
  width: 100%;
}

.mi-loading {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem 0;
  color: var(--text-dim);
  font-size: calc(0.85rem * var(--font-scale));
}

.mi-error-banner {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.mi-empty {
  padding: 1.25rem;
  text-align: center;
  color: var(--text-dim);
  font-style: italic;
  font-size: calc(0.85rem * var(--font-scale));
}

/* Account list */
.mi-account-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.mi-account-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--bg-card);
  transition: all 0.15s ease;
}

.mi-account-row--selectable {
  cursor: pointer;
}

.mi-account-row--selectable:hover {
  border-color: var(--accent);
  background: color-mix(in srgb, var(--accent) 8%, var(--bg-card));
}

.mi-account-row--selected {
  border-color: var(--accent);
  background: color-mix(in srgb, var(--accent) 12%, var(--bg-card));
}

.mi-account-row--compatible {
  border-left: 3px solid #4caf50;
}

.mi-account-row--incompatible {
  opacity: 0.6;
}

/* Account info */
.mi-account-info {
  flex: 1;
  min-width: 0;
}

.mi-account-primary {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin-bottom: 0.25rem;
}

.mi-session-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-active {
  background: #4caf50;
  box-shadow: 0 0 4px #4caf50;
}

.dot-expired {
  background: #f44336;
  box-shadow: 0 0 4px #f44336;
}

.mi-account-email {
  font-weight: 600;
  font-size: calc(0.9rem * var(--font-scale));
  font-family: monospace;
}

.mi-account-label {
  font-size: calc(0.75rem * var(--font-scale));
  color: var(--text-dim);
  font-style: italic;
}

.mi-account-meta {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex-wrap: wrap;
}

.mi-region-badge {
  background: color-mix(in srgb, var(--accent) 15%, transparent);
  color: var(--accent);
}

.mi-session-label {
  font-size: calc(0.72rem * var(--font-scale));
  color: var(--text-dim);
}

/* Account actions */
.mi-account-actions {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex-shrink: 0;
}

.btn-sm {
  padding: 0.3rem 0.65rem;
  font-size: calc(0.78rem * var(--font-scale));
}

.mi-delete-btn {
  color: var(--text-dim);
}

.mi-delete-btn:hover {
  color: #f44336;
}

.mi-confirm-text {
  font-size: calc(0.78rem * var(--font-scale));
  color: #f44336;
  font-weight: 600;
}

.mi-confirm-yes {
  color: #f44336;
  font-weight: 600;
}

/* Inline login flow */
.mi-login-flow {
  width: 100%;
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--border);
}

.mi-flow-step {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  font-size: calc(0.85rem * var(--font-scale));
}

.mi-flow-label {
  width: 100%;
  margin: 0 0 0.4rem;
  font-size: calc(0.85rem * var(--font-scale));
  color: var(--text-dim);
}

.mi-2fa-methods {
  display: flex;
  gap: 0.4rem;
  margin-bottom: 0.5rem;
  width: 100%;
}

.mi-code-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
}

.mi-code-input {
  max-width: 160px;
  font-family: monospace;
  letter-spacing: 0.15em;
  text-align: center;
}

.mi-attempts {
  width: 100%;
  margin: 0.3rem 0 0;
  font-size: calc(0.75rem * var(--font-scale));
  color: var(--text-dim);
}

.mi-flow-done {
  color: #4caf50;
  font-weight: 600;
}

.mi-done-icon {
  font-size: 1.1rem;
}

.mi-flow-error {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-top: 0.4rem;
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  background: color-mix(in srgb, #f44336 10%, var(--bg-card));
  color: #f44336;
  font-size: calc(0.8rem * var(--font-scale));
}

/* Add account */
.mi-add-section {
  margin-top: 0.5rem;
}

.mi-add-form {
  padding: 1rem;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--bg-card);
}

.mi-add-title {
  font-size: calc(0.95rem * var(--font-scale));
  font-weight: 600;
  margin: 0 0 0.75rem;
}

.mi-add-form .form-label {
  display: block;
  margin-bottom: 0.6rem;
  font-size: calc(0.8rem * var(--font-scale));
  font-weight: 600;
  color: var(--text-dim);
}

.mi-add-form .form-input {
  display: block;
  width: 100%;
  margin-top: 0.25rem;
}

.mi-add-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.75rem;
}

/* Shared utility (matches codebase) */
.spinner-small {
  display: inline-block;
  width: 1rem;
  height: 1rem;
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.badge {
  font-size: calc(0.65rem * var(--font-scale));
  padding: 0.1rem 0.4rem;
  border-radius: 999px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.badge-compatible {
  background: color-mix(in srgb, #4caf50 15%, transparent);
  color: #4caf50;
}

.badge-incompatible {
  background: color-mix(in srgb, #f44336 15%, transparent);
  color: #f44336;
}

.text-dim {
  opacity: 0.6;
  font-size: 0.85em;
}

/* Proxy settings */
.mi-proxy-section {
  margin-top: 1rem;
  font-size: calc(0.85rem * var(--font-scale, 1));
}
.mi-proxy-toggle {
  cursor: pointer;
  color: var(--text-dim);
  font-weight: 500;
}
.mi-proxy-form {
  margin-top: 0.5rem;
  padding: 0.75rem;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--bg-card);
}
.mi-proxy-hint {
  margin: 0 0 0.5rem;
  color: var(--text-dim);
  line-height: 1.5;
}
.mi-proxy-input-row {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}
.mi-proxy-input-row .form-input {
  flex: 1;
  font-family: monospace;
  font-size: 0.85rem;
}
.mi-proxy-status {
  margin-top: 0.35rem;
  font-size: 0.85em;
}
.mi-proxy-ok { color: var(--color-success, #4caf50); }
.mi-proxy-err { color: var(--color-error, #f44336); }
.mi-proxy-examples {
  margin: 0.5rem 0 0;
  color: var(--text-dim);
  font-size: 0.8em;
}
/* Tor */
.mi-tor-box {
  padding: 0.6rem 0.75rem;
  border-radius: 6px;
  background: color-mix(in srgb, var(--border) 25%, transparent);
  margin-bottom: 0.75rem;
}
.mi-tor-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.mi-tor-label {
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.mi-tor-badge {
  font-size: 0.75em;
  font-weight: 600;
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
.mi-tor-running {
  background: color-mix(in srgb, #4caf50 20%, transparent);
  color: #4caf50;
}
.mi-tor-stopped {
  background: color-mix(in srgb, #ff9800 20%, transparent);
  color: #ff9800;
}
.mi-tor-missing {
  background: color-mix(in srgb, var(--text-dim) 15%, transparent);
  color: var(--text-dim);
}
.mi-tor-install code {
  font-size: 0.85em;
  background: color-mix(in srgb, var(--border) 30%, transparent);
  padding: 0.15rem 0.4rem;
  border-radius: 3px;
}
.mi-tor-row .btn { margin-left: auto; }

.mi-proxy-examples code {
  background: color-mix(in srgb, var(--border) 30%, transparent);
  padding: 0.1rem 0.3rem;
  border-radius: 3px;
  font-size: 0.9em;
}
</style>
