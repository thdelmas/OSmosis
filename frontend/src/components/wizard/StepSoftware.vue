<script setup>
import { ref, computed, onMounted, onUnmounted, watch, inject } from 'vue'
import { useRouter } from 'vue-router'
import { useApi } from '@/composables/useApi'
import { useWizard } from '@/composables/useWizard'
import TerminalOutput from '@/components/shared/TerminalOutput.vue'
import GlossaryTip from '@/components/shared/GlossaryTip.vue'

const router = useRouter()
const { get, post, loading } = useApi()
const { state, deviceLabel, setRom, setApps, setSubPhase } = useWizard()
const registerTask = inject('registerTask', () => {})

const codename = computed(() => state.detectedDevice?.codename || state.detectedDevice?.match?.codename || '')
const model = computed(() => state.detectedDevice?.model || state.detectedDevice?.match?.model || '')
const brand = computed(() => (state.detectedDevice?.brand || state.detectedDevice?.match?.brand || '').toLowerCase())
const deviceId = computed(() => state.detectedDevice?.id || state.detectedDevice?.match?.id || codename.value)

// --- State ---
const phase = ref('pick') // pick | download | recovery-pick | recovery-download | apps | ready
const error = ref(null)

// --- OS selection ---
const presetOs = ref([])
const romfinderResults = ref([])
const selectedRom = ref(state.selectedRom || null)
const showManual = ref(false)
const romPath = ref('')

// Merge preset + romfinder, dedupe
const allOs = computed(() => {
  const map = new Map()
  for (const os of presetOs.value) {
    if (os.type !== 'recovery' && os.type !== 'addon' && os.type !== 'app') map.set(os.id, os)
  }
  for (const r of romfinderResults.value) {
    if (!map.has(r.id)) map.set(r.id, r)
  }
  return [...map.values()]
})

// --- App selection ---
const availableApps = computed(() => {
  const rom = selectedRom.value
  return rom?.recommended_apps || []
})
const checkedApps = ref(state.selectedApps?.length ? [...state.selectedApps] : [])

const hasAppsPhase = computed(() => availableApps.value.length > 0)

// Recovery source: prioritize ROM-required recovery, then TWRP
const recoverySource = computed(() => {
  const rom = selectedRom.value
  if (rom?.required_recovery?.url) return rom.required_recovery
  const preset = presetOs.value.find(os => os.type === 'recovery')
  if (preset?.url) return preset
  const match = state.detectedDevice?.match
  if (match?.twrp_url) return { id: 'twrp', name: 'TWRP', url: match.twrp_url, type: 'recovery' }
  return null
})

const needsRecovery = computed(() => {
  if (!selectedRom.value) return false
  const rom = selectedRom.value
  if (rom.flash_method === 'stock-recovery' || rom.flash_method === 'fastboot') return false
  if (rom.type === 'stock') return false
  return true
})

// --- Download state ---
const downloadTaskId = ref(null)
const downloadDest = ref('')
const downloadTermRef = ref(null)

// --- Recovery state ---
const recoveryChoice = ref(null) // 'have' | 'install' | 'skip'
const recoveryTaskId = ref(null)
const recoveryTermRef = ref(null)
const recoveryDownloading = ref(false)
const recoveryDone = ref(false)
const recoveryError = ref(false)
const recoveryImgPath = ref('')

// --- Load preset OS list ---
onMounted(async () => {
  if (deviceId.value) {
    const resp = await get(`/api/devices/${encodeURIComponent(deviceId.value)}/os`)
    if (resp.ok && resp.data?.os_list) {
      presetOs.value = resp.data.os_list
    }
  }
  // Also try romfinder
  if (codename.value) {
    const rf = await get(`/api/romfinder/${encodeURIComponent(codename.value)}`)
    if (rf.ok && rf.data?.roms) {
      romfinderResults.value = rf.data.roms
    }
  }
})

function waitForTask(taskId, cb, timeoutMs = 300000) {
  const start = Date.now()
  const poll = setInterval(async () => {
    if (Date.now() - start > timeoutMs) {
      clearInterval(poll)
      cb('error')
      return
    }
    const resp = await get('/api/tasks')
    if (!resp.ok) return
    const task = resp.data?.find(t => t.id === taskId)
    if (!task || task.status === 'running') return
    clearInterval(poll)
    cb(task.status)
  }, 2000)
}

// --- Select ROM ---
function selectRom(rom) {
  selectedRom.value = rom
  setRom(rom)
  showManual.value = false
}

const pathValidation = ref(null)
const pathValidating = ref(false)
let pathValidateTimeout = null

function onPathInput() {
  pathValidation.value = null
  if (pathValidateTimeout) clearTimeout(pathValidateTimeout)
  const val = romPath.value.trim()
  if (!val) return
  pathValidateTimeout = setTimeout(async () => {
    pathValidating.value = true
    const { ok, data } = await post('/api/validate-path', { path: val })
    pathValidating.value = false
    if (ok) pathValidation.value = data
  }, 400)
}

function selectManualRom() {
  if (!romPath.value.trim()) return
  const rom = { id: 'manual', name: 'Custom ROM', filename: romPath.value.split('/').pop(), manual_path: romPath.value.trim() }
  selectedRom.value = rom
  setRom(rom)
}

// Phase after recovery (or after download if no recovery needed)
function phaseAfterRecovery() {
  return hasAppsPhase.value ? 'apps' : 'ready'
}

// --- Download ROM ---
async function startDownload() {
  if (!selectedRom.value) return
  error.value = null
  phase.value = 'download'

  const rom = selectedRom.value

  // Manual file — skip download
  if (rom.manual_path) {
    downloadDest.value = rom.manual_path
    phase.value = needsRecovery.value ? 'recovery-pick' : phaseAfterRecovery()
    return
  }

  const { ok, data } = await post('/api/romfinder/download', {
    url: rom.download_url || rom.url || '',
    ipfs_cid: rom.ipfs_cid || '',
    filename: rom.filename || `${rom.id || 'rom'}.zip`,
    codename: codename.value,
    rom_id: rom.id,
    rom_name: rom.name,
  })

  if (ok && data?.task_id) {
    downloadTaskId.value = data.task_id
    downloadDest.value = data.dest || ''
    registerTask(data.task_id, `Download ${rom.name}`)
    waitForTask(data.task_id, (status) => {
      if (status === 'done') {
        downloadDest.value = data.dest || downloadDest.value
        phase.value = needsRecovery.value ? 'recovery-pick' : phaseAfterRecovery()
      } else {
        error.value = 'Download failed. Check terminal output.'
      }
    })
  } else {
    error.value = data?.error || 'Failed to start download.'
  }
}

// --- Recovery download ---
async function installRecovery() {
  if (!recoverySource.value?.url) {
    recoveryError.value = true
    return
  }
  recoveryDownloading.value = true
  recoveryError.value = false
  phase.value = 'recovery-download'

  const src = recoverySource.value
  const filename = src.name ? `${src.name.replace(/\s+/g, '-').toLowerCase()}.img` : 'recovery.img'

  const { ok, data } = await post('/api/romfinder/download', {
    url: src.url,
    filename,
    codename: codename.value,
    rom_id: src.id || 'recovery',
    rom_name: src.name || 'Recovery',
  })

  if (ok && data?.task_id) {
    recoveryTaskId.value = data.task_id
    registerTask(data.task_id, `Download ${src.name || 'Recovery'}`)
    waitForTask(data.task_id, (status) => {
      recoveryDownloading.value = false
      if (status === 'done') {
        recoveryImgPath.value = data.dest || ''
        recoveryDone.value = true
        phase.value = phaseAfterRecovery()
      } else {
        recoveryError.value = true
      }
    })
  } else {
    recoveryDownloading.value = false
    recoveryError.value = true
  }
}

function skipRecovery() {
  recoveryChoice.value = 'skip'
  phase.value = phaseAfterRecovery()
}

function haveRecovery() {
  recoveryChoice.value = 'have'
  phase.value = phaseAfterRecovery()
}

// --- App selection ---
function confirmApps() {
  const selected = availableApps.value.filter(a => checkedApps.value.includes(a.id))
  setApps(selected)
  state.selectedApps = selected
  phase.value = 'ready'
}

function skipApps() {
  setApps([])
  state.selectedApps = []
  phase.value = 'ready'
}

// --- Proceed to Connect step ---
function proceed() {
  // Save everything to wizard state for the next steps
  state.selectedRom = selectedRom.value
  state._downloadDest = downloadDest.value
  state._recoveryImgPath = recoveryImgPath.value
  state._recoveryChoice = recoveryChoice.value
  state._recoverySource = recoverySource.value
  state._selectedApps = state.selectedApps || []
  router.push('/wizard/connect')
}

// Persist phase — scoped to device so switching devices doesn't restore stale state
const STORAGE_KEY = computed(() => `osmosis-software-phase-${deviceId.value || 'unknown'}`)
watch([phase, selectedRom, downloadDest, recoveryChoice, checkedApps], () => {
  try {
    localStorage.setItem(STORAGE_KEY.value, JSON.stringify({
      phase: phase.value,
      selectedRom: selectedRom.value,
      downloadDest: downloadDest.value,
      recoveryChoice: recoveryChoice.value,
      recoveryImgPath: recoveryImgPath.value,
      recoveryDone: recoveryDone.value,
      checkedApps: checkedApps.value,
    }))
  } catch (_) {}
}, { deep: true })

// Restore on mount — only if key matches current device
onMounted(() => {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY.value) || '{}')
    if (saved.selectedRom) selectedRom.value = saved.selectedRom
    if (saved.downloadDest) downloadDest.value = saved.downloadDest
    if (saved.recoveryChoice) recoveryChoice.value = saved.recoveryChoice
    if (saved.recoveryImgPath) recoveryImgPath.value = saved.recoveryImgPath
    if (saved.recoveryDone) recoveryDone.value = saved.recoveryDone
    if (saved.checkedApps) checkedApps.value = saved.checkedApps
    if (saved.phase === 'ready' || saved.phase === 'apps') phase.value = saved.phase
  } catch (_) {}
})

// Update sub-phase label in progress bar
const phaseLabels = { pick: 'Choose OS', download: 'Downloading...', 'recovery-pick': 'Recovery', 'recovery-download': 'Downloading recovery...', apps: 'Apps', ready: 'Ready' }
watch(phase, (p) => setSubPhase(phaseLabels[p] || null), { immediate: true })
onUnmounted(() => setSubPhase(null))
</script>

<template>
  <h2 class="step-title">Software for {{ deviceLabel || 'your device' }}</h2>

  <!-- ===== PHASE 1: Pick OS ===== -->
  <div v-if="phase === 'pick'">
    <div v-if="allOs.length">
      <p class="step-desc">Choose an operating system to install:</p>
      <div class="rom-grid">
        <button
          v-for="os in allOs"
          :key="os.id"
          class="rom-card"
          :class="{ selected: selectedRom?.id === os.id, 'rom-card--featured': os.id === 'lethe' }"
          @click="selectRom(os)"
        >
          <div v-if="os.id === 'lethe'" class="rom-featured-badge">Recommended</div>
          <div class="rom-name">{{ os.name }}</div>
          <div v-if="os.desc" class="rom-desc">{{ os.desc }}</div>
          <div v-if="os.id === 'lethe' && !os.desc" class="rom-desc">Privacy-hardened Android by OSmosis. Dead man's switch, duress PIN, burner mode, tracker blocking, default-deny firewall. Works on 300+ devices.</div>
          <div class="rom-tags">
            <span v-for="tag in (os.tags || [])" :key="tag" class="rom-tag">{{ tag }}</span>
          </div>
        </button>
      </div>
    </div>

    <div v-if="selectedRom" class="install-action">
      <button class="btn btn-large btn-primary" :disabled="loading" @click="startDownload">
        Download {{ selectedRom.name }} &rarr;
      </button>
    </div>

    <div v-if="!allOs.length && codename" class="info-box info-box--warn">
      No pre-built operating systems found for <strong>{{ codename }}</strong>. You can provide a ROM file manually below, or search community forums like <a href="https://xdaforums.com" target="_blank" rel="noopener">XDA</a> for compatible ROMs.
    </div>

    <div class="step-skip">
      <button class="btn btn-link" @click="showManual = !showManual">
        {{ showManual ? 'Hide' : 'I already have a ROM file' }} &rarr;
      </button>
      <div v-if="showManual" class="manual-rom-input">
        <input v-model="romPath" type="text" class="input" placeholder="/path/to/rom.zip" @input="onPathInput" />
        <div v-if="pathValidating" class="path-status path-checking"><span class="spinner-small"></span> Checking file...</div>
        <div v-else-if="pathValidation && !pathValidation.valid" class="path-status path-invalid">{{ pathValidation.reason }}</div>
        <div v-else-if="pathValidation && pathValidation.valid" class="path-status path-valid">
          {{ pathValidation.filename }} ({{ pathValidation.size_human }})
          <span v-if="pathValidation.ext_warning" class="path-ext-warn">{{ pathValidation.ext_warning }}</span>
        </div>
        <button class="btn btn-primary" :disabled="!romPath.trim() || (pathValidation && !pathValidation.valid)" @click="selectManualRom(); phase = needsRecovery ? 'recovery-pick' : 'ready'">
          Use this file &rarr;
        </button>
      </div>
    </div>

    <div v-if="error" class="info-box info-box--error">{{ error }}</div>

    <div class="step-nav">
      <button class="btn btn-secondary" @click="router.push('/wizard/identify')">&larr; Back</button>
    </div>
  </div>

  <!-- ===== PHASE 2: Download ROM ===== -->
  <div v-if="phase === 'download'">
    <div class="install-guide-box">
      <h3>Downloading {{ selectedRom?.name }}...</h3>
      <p>ROM files are typically 500 MB - 2 GB. This may take a few minutes depending on your connection.</p>
      <p class="download-safe-hint">You can safely leave this page open — the download will continue in the background.</p>
    </div>

    <div v-if="downloadTaskId" class="task-section">
      <TerminalOutput ref="downloadTermRef" :task-id="downloadTaskId" />
    </div>

    <div v-if="error" class="info-box info-box--error">{{ error }}</div>

    <div class="step-nav">
      <button class="btn btn-secondary" @click="phase = 'pick'">&larr; Back</button>
    </div>
  </div>

  <!-- ===== PHASE 3: Recovery selection ===== -->
  <div v-if="phase === 'recovery-pick'">
    <div class="install-guide-box">
      <h3><GlossaryTip term="recovery">Custom Recovery</GlossaryTip></h3>
      <p>
        <strong>{{ selectedRom?.name }}</strong> requires a special install tool called a
        <GlossaryTip term="recovery">custom recovery</GlossaryTip>
        {{ recoverySource ? `(${recoverySource.name})` : '' }}
        on your device. Do you already have one?
      </p>
    </div>

    <div v-if="selectedRom?.required_recovery" class="info-box info-box--warn" style="margin-bottom: 1rem;">
      <strong>{{ selectedRom.name }}</strong> requires <strong>{{ selectedRom.required_recovery.name }}</strong> specifically.
      Other recoveries (like TWRP) will not work with this ROM.
    </div>

    <div class="recovery-options">
      <button class="recovery-option" @click="haveRecovery()">
        <strong>I already have {{ selectedRom?.required_recovery ? selectedRom.required_recovery.name : 'a custom recovery' }}</strong>
        <span>{{ recoverySource?.name || 'Custom recovery' }} is installed on my device</span>
      </button>
      <button v-if="recoverySource" class="recovery-option" @click="installRecovery()">
        <strong>Download {{ recoverySource.name }} for me</strong>
        <span>We'll download it now and flash it in the Connect step</span>
      </button>
      <button class="recovery-option" @click="skipRecovery()">
        <strong>Try without custom recovery</strong>
        <span>{{ selectedRom?.required_recovery ? 'Not recommended — this ROM requires ' + selectedRom.required_recovery.name : 'Attempt with stock recovery (may fail)' }}</span>
      </button>
    </div>

    <div class="step-nav">
      <button class="btn btn-secondary" @click="phase = 'pick'">&larr; Back</button>
    </div>
  </div>

  <!-- ===== PHASE 4: Recovery download ===== -->
  <div v-if="phase === 'recovery-download'">
    <div class="install-guide-box">
      <h3>Downloading {{ recoverySource?.name || 'Recovery' }}...</h3>
      <p>This will be flashed to your device in the Connect step.</p>
    </div>

    <div v-if="recoveryTaskId" class="task-section">
      <TerminalOutput ref="recoveryTermRef" :task-id="recoveryTaskId" />
    </div>

    <div v-if="recoveryError" class="info-box info-box--error">
      Recovery download failed. You can try again or skip and install manually.
      <div style="margin-top: 0.5rem;">
        <button class="btn btn-secondary" @click="installRecovery()">Retry</button>
        <button class="btn btn-secondary" @click="skipRecovery()">Skip</button>
      </div>
    </div>

    <div class="step-nav">
      <button class="btn btn-secondary" @click="phase = 'recovery-pick'">&larr; Back</button>
    </div>
  </div>

  <!-- ===== PHASE 5: App selection ===== -->
  <div v-if="phase === 'apps'">
    <div class="install-guide-box">
      <h3>Apps for {{ deviceLabel || 'your device' }}</h3>
      <p>
        <strong>{{ selectedRom?.name }}</strong> does not include an app store.
        Select apps to install from your computer after flashing:
      </p>
    </div>

    <div class="app-grid">
      <label
        v-for="app in availableApps"
        :key="app.id"
        class="app-card"
        :class="{ selected: checkedApps.includes(app.id) }"
      >
        <input
          type="checkbox"
          :value="app.id"
          v-model="checkedApps"
          class="app-checkbox"
        />
        <div class="app-info">
          <div class="app-name">{{ app.name }}</div>
          <div v-if="app.desc" class="app-desc">{{ app.desc }}</div>
          <div class="rom-tags">
            <span v-for="tag in (app.tags || [])" :key="tag" class="rom-tag">{{ tag }}</span>
          </div>
        </div>
      </label>
    </div>

    <div class="install-action">
      <button class="btn btn-large btn-primary" @click="confirmApps">
        {{ checkedApps.length ? 'Continue with selected apps' : 'Continue without apps' }} &rarr;
      </button>
    </div>

    <div class="step-skip">
      <button class="btn btn-link" @click="skipApps">
        Skip &mdash; I don't need any apps right now &rarr;
      </button>
    </div>

    <div class="step-nav">
      <button class="btn btn-secondary" @click="phase = needsRecovery ? 'recovery-pick' : 'pick'">&larr; Back</button>
    </div>
  </div>

  <!-- ===== PHASE 6: Ready to proceed ===== -->
  <div v-if="phase === 'ready'">
    <div class="install-guide-box install-guide-success">
      <h3>Software ready!</h3>
      <p>Everything is downloaded and ready to install on {{ deviceLabel || 'your device' }}.</p>
      <ul class="install-steps">
        <li><strong>{{ selectedRom?.name }}</strong>{{ downloadDest ? ' (downloaded)' : '' }}</li>
        <li v-if="recoveryDone"><strong>{{ recoverySource?.name }}</strong> (downloaded &mdash; will be flashed first)</li>
        <li v-else-if="recoveryChoice === 'have'">Custom recovery already installed on device</li>
        <li v-else-if="recoveryChoice === 'skip'">Skipping custom recovery (will try stock)</li>
        <li v-for="app in (state.selectedApps || [])" :key="app.id">
          <strong>{{ app.name }}</strong> (will be installed via ADB after flashing)
        </li>
      </ul>
    </div>

    <div class="install-action">
      <button class="btn btn-large btn-primary" @click="proceed">
        Connect device &rarr;
      </button>
    </div>

    <div class="step-nav">
      <button class="btn btn-secondary" @click="phase = hasAppsPhase ? 'apps' : (needsRecovery ? 'recovery-pick' : 'pick')">&larr; Back</button>
    </div>
  </div>
</template>
