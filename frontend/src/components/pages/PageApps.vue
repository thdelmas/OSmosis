<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import TerminalOutput from '@/components/shared/TerminalOutput.vue'

const { t } = useI18n()
const { get, post, loading } = useApi()

// --- Device detection ---
const deviceStatus = ref(null) // null | 'checking' | 'found' | 'not-found'
const deviceSerial = ref('')

async function checkDevice() {
  deviceStatus.value = 'checking'
  const resp = await get('/api/device')
  if (resp.ok && resp.data?.mode === 'device') {
    deviceStatus.value = 'found'
    deviceSerial.value = resp.data.serial || ''
  } else {
    deviceStatus.value = 'not-found'
  }
}

// --- App sources ---
const mode = ref('url') // 'url' | 'file' | 'catalog'
const apkUrl = ref('')
const apkPath = ref('')
const appName = ref('')

// Catalog of common free/open-source apps
const catalog = [
  { id: 'fdroid', name: 'F-Droid', desc: 'Free and open-source app store', url: 'https://f-droid.org/F-Droid.apk', tags: ['app-store', 'freedom'] },
  { id: 'termux', name: 'Termux', desc: 'Terminal emulator and Linux environment', url: 'https://f-droid.org/repo/com.termux_118.apk', tags: ['terminal', 'dev-tools'] },
  { id: 'k9mail', name: 'K-9 Mail', desc: 'Open-source email client (Thunderbird mobile)', url: 'https://f-droid.org/repo/com.fsck.k9_42084.apk', tags: ['email', 'privacy'] },
  { id: 'signal', name: 'Signal', desc: 'Encrypted messaging', url: 'https://updates.signal.org/android/Signal-Android-website-prod-universal-release.apk', tags: ['messaging', 'privacy'] },
]
const selectedCatalogApps = ref([])

// --- Install state ---
const taskId = ref(null)
const installDone = ref(false)
const installError = ref(false)

const canInstall = computed(() => {
  if (deviceStatus.value !== 'found') return false
  if (mode.value === 'url') return apkUrl.value.trim().length > 0
  if (mode.value === 'file') return apkPath.value.trim().length > 0
  if (mode.value === 'catalog') return selectedCatalogApps.value.length > 0
  return false
})

async function installApps() {
  taskId.value = null
  installDone.value = false
  installError.value = false

  let apps = []

  if (mode.value === 'url') {
    const name = appName.value.trim() || apkUrl.value.split('/').pop().replace('.apk', '')
    apps = [{ id: 'custom', name, url: apkUrl.value.trim(), install_method: 'adb' }]
  } else if (mode.value === 'file') {
    // For local files, use adb install directly
    const name = appName.value.trim() || apkPath.value.split('/').pop().replace('.apk', '')
    apps = [{ id: 'local', name, local_path: apkPath.value.trim(), install_method: 'adb' }]
  } else if (mode.value === 'catalog') {
    apps = catalog.filter(a => selectedCatalogApps.value.includes(a.id))
      .map(a => ({ ...a, install_method: 'adb' }))
  }

  if (!apps.length) return

  const { ok, data } = await post('/api/apps/install', { apps })
  if (ok && data?.task_id) {
    taskId.value = data.task_id
  } else {
    installError.value = true
  }
}
</script>

<template>
  <main class="page-content">
    <h2 class="step-title">{{ t('apps.title', 'Install Apps') }}</h2>
    <p class="step-desc">{{ t('apps.desc', 'Install apps from your computer to any Android device connected via USB.') }}</p>

    <!-- Step 1: Check device -->
    <div class="form-group">
      <h3>1. Connect your device</h3>
      <p class="step-desc">
        Boot your phone into the OS (normal mode) with USB debugging enabled,
        then plug it in via USB.
      </p>
      <button class="btn btn-secondary" :disabled="deviceStatus === 'checking'" @click="checkDevice">
        {{ deviceStatus === 'checking' ? 'Checking...' : 'Detect device' }}
      </button>
      <div v-if="deviceStatus === 'found'" class="info-box info-box--success" style="margin-top: 0.75rem;">
        Device connected{{ deviceSerial ? ` (${deviceSerial})` : '' }}. Ready to install apps.
      </div>
      <div v-if="deviceStatus === 'not-found'" class="info-box info-box--warn" style="margin-top: 0.75rem;">
        No device found in normal mode. Make sure USB debugging is enabled
        (Settings &rarr; Developer options &rarr; USB debugging) and the device is unlocked.
      </div>
    </div>

    <!-- Step 2: Choose apps -->
    <div v-if="deviceStatus === 'found'" class="form-group">
      <h3>2. Choose apps to install</h3>

      <div class="mode-tabs">
        <button class="mode-tab" :class="{ active: mode === 'catalog' }" @click="mode = 'catalog'">
          App catalog
        </button>
        <button class="mode-tab" :class="{ active: mode === 'url' }" @click="mode = 'url'">
          From URL
        </button>
        <button class="mode-tab" :class="{ active: mode === 'file' }" @click="mode = 'file'">
          Local APK file
        </button>
      </div>

      <!-- Catalog mode -->
      <div v-if="mode === 'catalog'" class="app-catalog">
        <label
          v-for="app in catalog"
          :key="app.id"
          class="app-card"
          :class="{ selected: selectedCatalogApps.includes(app.id) }"
        >
          <input type="checkbox" :value="app.id" v-model="selectedCatalogApps" class="app-checkbox" />
          <div class="app-info">
            <div class="app-name">{{ app.name }}</div>
            <div class="app-desc">{{ app.desc }}</div>
            <div class="app-tags">
              <span v-for="tag in app.tags" :key="tag" class="rom-tag">{{ tag }}</span>
            </div>
          </div>
        </label>
      </div>

      <!-- URL mode -->
      <div v-if="mode === 'url'">
        <div class="form-group">
          <label class="form-label">APK download URL</label>
          <input v-model="apkUrl" type="text" class="form-input" placeholder="https://f-droid.org/F-Droid.apk" />
        </div>
        <div class="form-group">
          <label class="form-label">App name (optional)</label>
          <input v-model="appName" type="text" class="form-input" placeholder="F-Droid" />
        </div>
      </div>

      <!-- File mode -->
      <div v-if="mode === 'file'">
        <div class="form-group">
          <label class="form-label">Path to APK file</label>
          <input v-model="apkPath" type="text" class="form-input" placeholder="/home/user/app.apk" />
        </div>
        <div class="form-group">
          <label class="form-label">App name (optional)</label>
          <input v-model="appName" type="text" class="form-input" placeholder="My App" />
        </div>
      </div>
    </div>

    <!-- Step 3: Install -->
    <div v-if="deviceStatus === 'found'" class="step-actions">
      <button
        class="btn btn-large btn-primary"
        :class="{ 'btn-loading': loading }"
        :disabled="loading || !canInstall"
        @click="installApps"
      >
        {{ loading ? 'Installing...' : 'Install on device' }}
      </button>
    </div>

    <TerminalOutput v-if="taskId" :task-id="taskId" />

    <div v-if="installError" class="info-box info-box--error" style="margin-top: 1rem;">
      Failed to start app installation. Check that ADB is available and the device is connected.
    </div>
  </main>
</template>

<style scoped>
.mode-tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.25rem;
}
.mode-tab {
  padding: 0.5rem 1rem;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: transparent;
  color: var(--text);
  cursor: pointer;
  font-size: calc(0.9rem * var(--font-scale, 1));
}
.mode-tab.active {
  background: var(--accent);
  color: var(--bg);
  border-color: var(--accent);
}

.app-catalog {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 0.75rem;
  margin-bottom: 1rem;
}
.app-card {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 0.875rem;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}
.app-card:hover {
  border-color: var(--accent);
}
.app-card.selected {
  border-color: var(--accent);
  background: rgba(54, 216, 183, 0.06);
}
.app-checkbox {
  margin-top: 0.2rem;
  accent-color: var(--accent);
}
.app-name {
  font-weight: 600;
  font-size: calc(0.95rem * var(--font-scale, 1));
}
.app-desc {
  font-size: calc(0.85rem * var(--font-scale, 1));
  color: var(--text-dim);
  margin-top: 0.2rem;
}
.app-tags {
  display: flex;
  gap: 0.35rem;
  margin-top: 0.4rem;
  flex-wrap: wrap;
}
</style>
