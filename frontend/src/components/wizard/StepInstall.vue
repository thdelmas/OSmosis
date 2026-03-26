<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick, inject } from 'vue'
import { useRouter, onBeforeRouteLeave } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { useWizard } from '@/composables/useWizard'
import TerminalOutput from '@/components/shared/TerminalOutput.vue'
import GlossaryTip from '@/components/shared/GlossaryTip.vue'
import { parseErrorType, parseTerminalHints } from '@/composables/useErrorGuide'

const INSTALL_STORAGE_KEY = 'osmosis-install-phase'

const { t } = useI18n()
const router = useRouter()
const { get, post, loading } = useApi()
const { state, deviceLabel, setSubPhase, reset: resetWizard } = useWizard()
const registerTask = inject('registerTask', () => {})

const codename = computed(() => state.detectedDevice?.codename || state.detectedDevice?.match?.codename || '')
const model = computed(() => state.detectedDevice?.model || state.detectedDevice?.match?.model || '')
const brand = computed(() => (state.detectedDevice?.brand || state.detectedDevice?.match?.brand || '').toLowerCase())
const deviceMode = computed(() => state.detectedDevice?.mode || '')
const isMiAssistant = computed(() => deviceMode.value === 'miassistant_sideload')
const isFastboot = computed(() => deviceMode.value === 'fastboot')
const isRestoreStock = computed(() => state.selectedGoal === 'restore-stock')

// Device-specific button combos for Download Mode and Recovery Mode
const downloadModeCombo = computed(() => {
  const b = brand.value
  if (b.includes('samsung')) return 'Volume Down + Home + Power'
  if (b.includes('google') || b.includes('pixel')) return 'Power off, then hold Power + Volume Down'
  if (b.includes('oneplus') || b.includes('xiaomi') || b.includes('poco')) return 'Power off, then hold Volume Up + Volume Down + Power'
  if (b.includes('motorola')) return 'Power off, then hold Volume Down + Power'
  if (b.includes('sony')) return 'Power off, connect USB while holding Volume Down'
  if (b.includes('fairphone')) return 'Power off, then hold Volume Down + Power'
  return 'Power off, then hold Volume Down + Power (or check your device\'s manual for the correct combo)'
})

const recoveryModeCombo = computed(() => {
  const b = brand.value
  if (b.includes('samsung')) return 'Volume Up + Home + Power'
  if (b.includes('google') || b.includes('pixel')) return 'Power off, then hold Power + Volume Up'
  if (b.includes('oneplus')) return 'Power off, then hold Volume Down + Power, select Recovery'
  if (b.includes('xiaomi') || b.includes('poco')) return 'Power off, then hold Volume Up + Power'
  if (b.includes('motorola')) return 'Power off, then hold Volume Down + Power, select Recovery'
  if (b.includes('fairphone')) return 'Power off, then hold Volume Up + Power'
  return 'Power off, then hold Volume Up + Power (or check your device\'s manual for the correct combo)'
})

// --- Phase tracking ---
// Phases: pick → download → backup → recovery → boot-recovery → sideload → done
function loadSavedPhase() {
  try {
    const saved = JSON.parse(localStorage.getItem(INSTALL_STORAGE_KEY) || '{}')
    // Only restore if the codename matches (same device/session)
    if (saved.codename && saved.codename === (state.detectedDevice?.codename || state.detectedDevice?.match?.codename || '')) {
      return saved
    }
  } catch {}
  return {}
}

// Map install phases to human-readable sub-phase labels for the wizard progress bar
const phaseLabels = {
  pick: 'Choosing OS',
  download: 'Downloading',
  backup: 'Backup',
  recovery: 'Recovery setup',
  'boot-recovery': 'Booting recovery',
  sideload: 'Flashing',
  'miassistant-pick': 'Select ROM',
  'miassistant-flash': 'Flashing stock ROM',
  'fastboot-pick': 'Select image',
  'fastboot-flash': 'Flashing via fastboot',
  done: 'Complete',
}

const savedInstall = loadSavedPhase()
const defaultPhase = (() => {
  if (savedInstall.phase) return savedInstall.phase
  const mode = state.detectedDevice?.mode || ''
  if (mode === 'miassistant_sideload') return 'miassistant-pick'
  if (mode === 'fastboot') return 'fastboot-pick'
  return 'pick'
})()
const phase = ref(defaultPhase)
watch(phase, (p) => setSubPhase(phaseLabels[p] || null), { immediate: true })
const taskId = ref(null)
const error = ref(null)
const terminalRef = ref(null)

function scrollToTerminal() {
  nextTick(() => {
    terminalRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  })
}

// Warn before leaving during active operations
const activePhases = ['download', 'recovery', 'boot-recovery', 'sideload', 'miassistant-flash', 'fastboot-flash']

function beforeUnloadHandler(e) {
  if (activePhases.includes(phase.value)) {
    e.preventDefault()
    e.returnValue = ''
  }
}

onMounted(() => window.addEventListener('beforeunload', beforeUnloadHandler))
onUnmounted(() => window.removeEventListener('beforeunload', beforeUnloadHandler))

onBeforeRouteLeave(() => {
  if (activePhases.includes(phase.value)) {
    return window.confirm('An operation is in progress. Leaving this page may interrupt it. Are you sure?')
  }
})

// --- Phase 1: Pick ROM ---
const romfinderLoading = ref(false)
const roms = ref([])
const searchLinks = ref([])
const presetOs = ref([])
const selectedRom = ref(savedInstall.selectedRom || null)
const showManual = ref(false)
const romPath = ref('')

onMounted(async () => {
  if (codename.value) {
    romfinderLoading.value = true
    const [romResp, osResp] = await Promise.all([
      get(`/api/romfinder/${encodeURIComponent(codename.value)}${model.value ? '?model=' + encodeURIComponent(model.value) : ''}`),
      get(`/api/devices/${state.detectedDevice?.id || state.detectedDevice?.match?.id || codename.value}/os`),
    ])
    romfinderLoading.value = false
    if (romResp.ok && romResp.data) {
      roms.value = romResp.data.roms || []
      searchLinks.value = romResp.data.search_links || []
    }
    if (osResp.ok && osResp.data?.os_list) {
      presetOs.value = osResp.data.os_list
    }

    // Also fetch device profile for TWRP fallback
    const deviceId = state.detectedDevice?.id || state.detectedDevice?.match?.id || codename.value
    if (deviceId) {
      const profResp = await get(`/api/profiles/${encodeURIComponent(deviceId)}`)
      if (profResp.ok && profResp.data?.firmware) {
        const twrp = profResp.data.firmware.find(f => f.type === 'recovery' || f.id === 'twrp')
        if (twrp?.url) profileTwrp.value = twrp
      }
    }
  }
})

const allOs = computed(() => {
  const seen = new Set()
  const merged = []
  for (const os of presetOs.value) {
    seen.add(os.id)
    merged.push({ ...os, source: 'preset' })
  }
  for (const rom of roms.value) {
    if (!seen.has(rom.id)) {
      seen.add(rom.id)
      merged.push({
        id: rom.id, name: rom.name,
        desc: rom.version ? `Version ${rom.version}` : '',
        url: rom.download_url || rom.page_url || '',
        download_url: rom.download_url || '',
        page_url: rom.page_url || '',
        filename: rom.filename || '',
        version: rom.version || '',
        ipfs_cid: rom.ipfs_cid || '',
        tags: [], source: 'romfinder',
      })
    }
  }
  return merged
})

function selectRom(rom) {
  selectedRom.value = rom
  showManual.value = false
}

// --- Phase 2: Download ---
const downloadDest = ref(savedInstall.downloadDest || '')
const downloadRetries = ref(0)
const MAX_DOWNLOAD_RETRIES = 2
const retrying = ref(false)

async function startDownload() {
  if (!selectedRom.value) return
  error.value = null
  taskId.value = null
  phase.value = 'download'

  const rom = selectedRom.value
  const { ok, data } = await post('/api/romfinder/download', {
    url: rom.download_url || '',
    ipfs_cid: rom.ipfs_cid || '',
    filename: rom.filename || `${rom.id || 'rom'}.zip`,
    codename: codename.value,
    rom_id: rom.id || '',
    rom_name: rom.name || '',
    version: rom.version || '',
  })

  if (ok && data?.task_id) {
    taskId.value = data.task_id
    downloadDest.value = data.dest || ''
    registerTask(data.task_id, `Download ${rom.name}`)
    scrollToTerminal()
    waitForTask(data.task_id, (status) => {
      if (status === 'done') {
        downloadRetries.value = 0
        phase.value = 'backup'
      } else if (downloadRetries.value < MAX_DOWNLOAD_RETRIES) {
        // Auto-retry with backoff
        downloadRetries.value++
        retrying.value = true
        const delay = downloadRetries.value * 3000
        setTimeout(() => {
          retrying.value = false
          startDownload()
        }, delay)
      } else {
        downloadRetries.value = 0
        error.value = 'Download failed after multiple attempts. Check your internet connection and try again.'
        // Parse terminal for more specific hints
        setTimeout(() => {
          const lines = terminalRef.value?.task?.lines?.value || []
          const hints = parseTerminalHints(lines)
          if (hints.length) {
            error.value = 'Download failed after multiple attempts.\n\n' + hints.join('\n')
          }
        }, 1000)
      }
    })
  } else {
    error.value = data?.error || 'Failed to start download.'
    phase.value = 'pick'
  }
}

function waitForTask(id, callback) {
  const poll = setInterval(async () => {
    const { ok, data } = await get('/api/tasks')
    if (!ok) return
    const task = data.find(t => t.id === id)
    if (task && task.status !== 'running') {
      clearInterval(poll)
      callback(task.status)
    }
  }, 2000)
}

// --- Phase 3: Prepare (backup + instructions) ---
const backupTaskId = ref(null)
const backupDone = ref(savedInstall.backupDone || false)
const skipBackup = ref(savedInstall.skipBackup || false)

const backupRunning = ref(false)
const backupError = ref(false)

async function startBackup() {
  backupTaskId.value = null
  backupRunning.value = true
  backupError.value = false

  const label = [
    state.detectedDevice?.display_name || state.detectedDevice?.label || '',
    model.value,
    codename.value,
  ].filter(Boolean).join(' ').trim() || 'device'

  const { ok, data } = await post('/api/backup', {
    partitions: ['boot', 'recovery'],
    label,
  })
  if (ok && data?.task_id) {
    backupTaskId.value = data.task_id
    registerTask(data.task_id, 'Backup partitions')
    waitForTask(data.task_id, (status) => {
      backupRunning.value = false
      if (status === 'done') {
        backupDone.value = true
      } else {
        backupError.value = true
        backupDone.value = true // allow proceeding even if backup failed
      }
    })
  } else {
    backupRunning.value = false
    backupError.value = true
    backupDone.value = true
  }
}

// --- Phase 3b: Boot into recovery ---
const recoveryTaskId = ref(null)
const rebootSent = ref(false)
const rebootFailed = ref(false)
const sideloadReady = ref(false)
const deviceInRecovery = ref(false)
let sideloadPollTimer = null

function proceedToBootRecovery() {
  phase.value = 'boot-recovery'
  rebootSent.value = false
  rebootFailed.value = false
  sideloadReady.value = false
  deviceInRecovery.value = false
  recoveryTaskId.value = null
  startRebootRecovery()
}

async function startRebootRecovery() {
  error.value = null
  const { ok, data } = await post('/api/reboot-recovery')
  if (ok && data?.task_id) {
    recoveryTaskId.value = data.task_id
    registerTask(data.task_id, 'Reboot into recovery')
    waitForTask(data.task_id, (status) => {
      rebootSent.value = true
      rebootFailed.value = status !== 'done'
      startSideloadPoll()
    })
  } else {
    rebootSent.value = true
    rebootFailed.value = true
    startSideloadPoll()
  }
}

const stuckInDownloadMode = ref(false)

function startSideloadPoll() {
  if (sideloadPollTimer) clearInterval(sideloadPollTimer)
  stuckInDownloadMode.value = false
  sideloadPollTimer = setInterval(async () => {
    const { ok, data } = await get('/api/sideload-ready')
    if (!ok) return
    if (data.ready) {
      sideloadReady.value = true
      deviceInRecovery.value = false
      stuckInDownloadMode.value = false
      clearInterval(sideloadPollTimer)
      sideloadPollTimer = null
      // Auto-advance after a brief moment so the user sees the success state
      setTimeout(() => proceedToSideload(), 1200)
    } else if (data.recovery) {
      deviceInRecovery.value = true
      stuckInDownloadMode.value = false
    } else if (data.download_mode) {
      stuckInDownloadMode.value = true
      deviceInRecovery.value = false
    }
  }, 3000)
}

// --- Custom recovery guidance ---
const showRecoveryHelp = ref(false)
const recoveryAnswer = ref(null) // null | 'unsure' | 'no' | 'yes-twrp' | 'yes-stock'

// --- Recovery step ---
const recoveryChoice = ref(null) // null | 'have-twrp' | 'install' | 'skip'
const recoveryInstalling = ref(false)
const recoveryInstallTaskId = ref(null)
const recoveryInstallDone = ref(false)
const recoveryInstallError = ref(false)
const bootRepairOffered = ref(false)
const bootRepairing = ref(false)
const lastRecoveryImgPath = ref(null)

const profileTwrp = ref(null)

// Recovery source: prioritize ROM-required recovery, then fall back to TWRP
const recoverySource = computed(() => {
  // 1. If selected ROM requires a specific recovery, use that
  const rom = selectedRom.value
  if (rom?.required_recovery?.url) return rom.required_recovery
  // 2. Check preset OS list for recoveries
  const preset = presetOs.value.find(os => os.type === 'recovery')
  if (preset?.url) return preset
  // 3. Check device match from auto-detect (devices.cfg)
  const match = state.detectedDevice?.match
  if (match?.twrp_url) return { id: 'twrp', name: 'TWRP Recovery', url: match.twrp_url, type: 'recovery' }
  // 4. Check all merged OS options
  const fromAll = allOs.value.find(os => os.type === 'recovery')
  if (fromAll?.url) return fromAll
  // 5. Check device profile
  if (profileTwrp.value?.url) return profileTwrp.value
  return null
})
// Backwards compat alias
const twrpSource = recoverySource

async function installRecoveryNow() {
  recoveryInstalling.value = true
  recoveryInstallError.value = false
  recoveryInstallDone.value = false
  recoveryInstallTaskId.value = null

  // 1. Use twrpSource if available
  const src = twrpSource.value
  if (src?.url) {
    return doRecoveryFlash(src.url, src.name ? `${src.name.replace(/\s+/g, '-').toLowerCase()}.img` : 'twrp-recovery.img')
  }

  // 2. Try the device match twrp_url directly
  const matchUrl = state.detectedDevice?.match?.twrp_url
  if (matchUrl) {
    return doRecoveryFlash(matchUrl, 'twrp-recovery.img')
  }

  // 3. Try to find TWRP via romfinder
  const { ok, data } = await get(`/api/romfinder/${encodeURIComponent(codename.value)}?type=recovery`)
  if (ok && data?.roms?.length) {
    const twrp = data.roms.find(r => r.name?.toLowerCase().includes('twrp')) || data.roms[0]
    if (twrp?.download_url) {
      return doRecoveryFlash(twrp.download_url, twrp.filename || 'twrp.img')
    }
  }

  // 4. Try fetching TWRP URL from device profile API
  const deviceId = state.detectedDevice?.id || state.detectedDevice?.match?.id || codename.value
  if (deviceId) {
    const profResp = await get(`/api/profiles/${encodeURIComponent(deviceId)}`)
    if (profResp.ok && profResp.data?.firmware) {
      const twrp = profResp.data.firmware.find(f => f.type === 'recovery' || f.id === 'twrp')
      if (twrp?.url) {
        return doRecoveryFlash(twrp.url, 'twrp-recovery.img')
      }
    }
    // Also try the os endpoint directly
    const osResp = await get(`/api/devices/${encodeURIComponent(deviceId)}/os`)
    if (osResp.ok && osResp.data?.os_list) {
      const twrp = osResp.data.os_list.find(o => o.type === 'recovery' || o.id === 'twrp')
      if (twrp?.url) {
        return doRecoveryFlash(twrp.url, 'twrp-recovery.img')
      }
    }
  }

  recoveryInstalling.value = false
  recoveryInstallError.value = true
}

async function doRecoveryFlash(url, filename) {
  const recName = recoverySource.value?.name || 'Recovery'
  const isSamsung = brand.value.includes('samsung')

  // Step 1: Download the recovery image
  const dlResp = await post('/api/romfinder/download', {
    url,
    filename,
    codename: codename.value,
    rom_id: recoverySource.value?.id || 'recovery',
    rom_name: recName,
  })

  if (!dlResp.ok || !dlResp.data?.task_id) {
    // Fallback: try flashing directly if it's already a local .img URL
    recoveryInstalling.value = false
    recoveryInstallError.value = true
    return
  }

  recoveryInstallTaskId.value = dlResp.data.task_id
  registerTask(dlResp.data.task_id, 'Download TWRP')
  scrollToTerminal()

  // Wait for download to complete, then flash
  waitForTask(dlResp.data.task_id, async (dlStatus) => {
    if (dlStatus !== 'done') {
      recoveryInstalling.value = false
      recoveryInstallError.value = true
      return
    }

    // Step 2: Flash the downloaded recovery image
    // Samsung devices need recovery flashed to BOOT too (avoids Download Mode loop)
    const imgPath = dlResp.data.dest
    lastRecoveryImgPath.value = imgPath
    const flashResp = await post('/api/flash/recovery', {
      recovery_img: imgPath,
      fix_boot: isSamsung,
    })

    if (flashResp.ok && flashResp.data?.task_id) {
      recoveryInstallTaskId.value = flashResp.data.task_id
      registerTask(flashResp.data.task_id, 'Flash TWRP Recovery')
      waitForTask(flashResp.data.task_id, (flashStatus) => {
        recoveryInstalling.value = false
        if (flashStatus === 'done') {
          recoveryInstallDone.value = true
          recoveryAnswer.value = 'yes-twrp'
        } else {
          recoveryInstallError.value = true
        }
      })
    } else {
      recoveryInstalling.value = false
      recoveryInstallError.value = true
    }
  })
}

async function repairBoot() {
  if (!lastRecoveryImgPath.value) {
    error.value = 'No recovery tool image available. Go back to the previous step and choose "Install recovery for me" to download one.'
    return
  }
  bootRepairing.value = true
  const resp = await post('/api/flash/recovery', {
    recovery_img: lastRecoveryImgPath.value,
    fix_boot: true,
  })
  if (resp.ok && resp.data?.task_id) {
    recoveryInstallTaskId.value = resp.data.task_id
    registerTask(resp.data.task_id, 'Repair boot partition')
    waitForTask(resp.data.task_id, (status) => {
      bootRepairing.value = false
      if (status === 'done') {
        stuckInDownloadMode.value = false
        recoveryInstallDone.value = true
      } else {
        error.value = 'Boot repair failed. Try these steps:\n1. Unplug the USB cable\n2. Remove and reinsert the battery (if removable)\n3. Re-enter Download Mode using the button combination shown above\n4. Plug USB back in and retry'
      }
    })
  } else {
    bootRepairing.value = false
    error.value = 'Could not start boot repair.'
  }
}


function proceedToSideload() {
  if (sideloadPollTimer) { clearInterval(sideloadPollTimer); sideloadPollTimer = null }
  phase.value = 'sideload'
  taskId.value = null
}

// --- Phase 4: Sideload ---
const sideloadTaskId = ref(null)
const sideloadTermRef = ref(null)
const signatureFailure = ref(false)
const incompleteTransfer = ref(false)
const errorGuide = ref(null) // { type, title, message, steps } from useErrorGuide
const pushTaskId = ref(null)

async function startPushInstall() {
  error.value = null
  incompleteTransfer.value = false
  const zipPath = downloadDest.value || romPath.value.trim()
  if (!zipPath) {
    error.value = 'No ROM file available.'
    return
  }

  const { ok, data } = await post('/api/flash/push-install', {
    zip_path: zipPath,
    label: selectedRom.value?.name || 'ROM',
  })

  if (ok && data?.task_id) {
    pushTaskId.value = data.task_id
    sideloadTaskId.value = data.task_id
    registerTask(data.task_id, `Push install ${selectedRom.value?.name || 'ROM'}`)
    scrollToTerminal()
    waitForTask(data.task_id, (status) => {
      if (status === 'done') {
        phase.value = 'done'
      } else {
        error.value = 'Software transfer failed. Click "Show details" for more information. Make sure your device is still connected and try again.'
      }
    })
  } else {
    error.value = data?.error || 'Failed to start push install.'
  }
}

async function startSideload() {
  error.value = null
  errorGuide.value = null
  signatureFailure.value = false
  incompleteTransfer.value = false
  const zipPath = downloadDest.value || romPath.value.trim()
  if (!zipPath) {
    error.value = 'No ROM file available.'
    return
  }

  const { ok, data } = await post('/api/sideload', {
    zip_path: zipPath,
    label: selectedRom.value?.name || 'ROM',
  })

  if (ok && data?.task_id) {
    sideloadTaskId.value = data.task_id
    registerTask(data.task_id, `Sideload ${selectedRom.value?.name || 'ROM'}`)
    scrollToTerminal()
    waitForTask(data.task_id, (status) => {
      if (status === 'done') {
        phase.value = 'done'
      } else {
        // Wait for the EventSource stream to deliver remaining lines
        // before checking for the signature error marker
        // Default to generic error immediately, then upgrade to signature
        // failure if the terminal lines confirm it once the stream flushes
        // Don't show generic error immediately — wait for stream to flush
        // and check for specific error types first
        const checkForErrorType = () => {
          const lines = sideloadTermRef.value?.task?.lines?.value || []
          const allText = lines.map(l => (l.msg || '').toLowerCase()).join(' ')
          const hasSignatureError =
            allText.includes('__error_type:signature_verification_failed') ||
            allText.includes('rejected this rom') ||
            allText.includes('rom rejected') ||
            allText.includes('rejected by recovery') ||
            allText.includes('require a custom recovery')
          const hasIncompleteTransfer =
            allText.includes('__error_type:incomplete_transfer') ||
            allText.includes('transfer ended at') ||
            allText.includes('total xfer:')
          if (hasSignatureError) {
            signatureFailure.value = true
            incompleteTransfer.value = false
            error.value = null
          } else if (hasIncompleteTransfer) {
            incompleteTransfer.value = true
            signatureFailure.value = false
            error.value = null
          } else {
            // Check for other typed errors via the shared parser
            const guide = parseErrorType(lines)
            if (guide) {
              errorGuide.value = guide
              error.value = null
            } else if (!error.value) {
              // Parse terminal for actionable hints
              const hints = parseTerminalHints(lines)
              error.value = hints.length
                ? 'Software transfer failed.\n\n' + hints.join('\n')
                : 'Software transfer failed. Make sure your device is still in recovery mode with sideload started, then try again. If the device restarted, go back and re-enter recovery mode.'
            }
          }
        }
        // Check repeatedly as stream lines arrive asynchronously
        setTimeout(checkForErrorType, 300)
        setTimeout(checkForErrorType, 1000)
        setTimeout(checkForErrorType, 2000)
        setTimeout(checkForErrorType, 4000)
        // Set fallback error only after final check
        setTimeout(() => {
          if (!signatureFailure.value && !incompleteTransfer.value && !errorGuide.value && !error.value) {
            error.value = 'Software transfer failed. Make sure your device is still in recovery mode with sideload started, then try again. If the device restarted, go back and re-enter recovery mode.'
          }
        }, 5000)
      }
    })
  } else {
    error.value = data?.error || 'Failed to start sideload.'
  }
}

// --- Manual file path ---
const pathValidation = ref(null) // { valid, reason, filename, size_human, ext_warning }
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

function useManualFile() {
  if (!romPath.value.trim()) return
  downloadDest.value = romPath.value.trim()
  selectedRom.value = { id: 'manual', name: 'Custom ROM', filename: romPath.value.split('/').pop() }
  phase.value = 'backup'
}

// --- MIAssistant sideload flow ---
const miStockPath = ref('')
const miStockValidation = ref(null)
const miStockValidating = ref(false)
let miStockValidateTimeout = null
const miSideloadTaskId = ref(null)

function onMiStockPathInput() {
  miStockValidation.value = null
  if (miStockValidateTimeout) clearTimeout(miStockValidateTimeout)
  const val = miStockPath.value.trim()
  if (!val) return
  miStockValidateTimeout = setTimeout(async () => {
    miStockValidating.value = true
    const { ok, data } = await post('/api/validate-path', { path: val })
    miStockValidating.value = false
    if (ok) miStockValidation.value = data
  }, 400)
}

async function startMiSideload() {
  error.value = null
  const zipPath = miStockPath.value.trim()
  if (!zipPath) {
    error.value = 'Please provide the path to the stock ROM ZIP file.'
    return
  }

  phase.value = 'miassistant-flash'
  const { ok, data } = await post('/api/miassistant/sideload', {
    zip_path: zipPath,
    codename: codename.value || 'unknown',
  })

  if (ok && data?.task_id) {
    miSideloadTaskId.value = data.task_id
    registerTask(data.task_id, `MIAssistant sideload ${codename.value || 'stock ROM'}`)
    scrollToTerminal()
    waitForTask(data.task_id, (status) => {
      if (status === 'done') {
        phase.value = 'done'
      } else {
        error.value = 'MIAssistant sideload failed. Check the terminal output for details. Make sure the device is still in MIAssistant sideload mode and try again.'
      }
    })
  } else {
    error.value = data?.error || 'Failed to start MIAssistant sideload.'
    phase.value = 'miassistant-pick'
  }
}

// --- Fastboot flash flow ---
const fbImagePath = ref('')
const fbImageValidation = ref(null)
const fbImageValidating = ref(false)
let fbImageValidateTimeout = null
const fbFlashTaskId = ref(null)

function onFbImagePathInput() {
  fbImageValidation.value = null
  if (fbImageValidateTimeout) clearTimeout(fbImageValidateTimeout)
  const val = fbImagePath.value.trim()
  if (!val) return
  fbImageValidateTimeout = setTimeout(async () => {
    fbImageValidating.value = true
    const { ok, data } = await post('/api/validate-path', { path: val })
    fbImageValidating.value = false
    if (ok) fbImageValidation.value = data
  }, 400)
}

async function startFastbootFlash() {
  error.value = null
  const zipPath = fbImagePath.value.trim()
  if (!zipPath) {
    error.value = 'Please provide the path to the factory image ZIP.'
    return
  }

  phase.value = 'fastboot-flash'
  const flashType = isRestoreStock.value ? 'factory' : 'custom'
  const { ok, data } = await post('/api/fastboot/flash', {
    image_zip: zipPath,
    flash_type: flashType,
  })

  if (ok && data?.task_id) {
    fbFlashTaskId.value = data.task_id
    registerTask(data.task_id, `Fastboot flash ${flashType}`)
    scrollToTerminal()
    waitForTask(data.task_id, (status) => {
      if (status === 'done') {
        phase.value = 'done'
      } else {
        error.value = 'Fastboot flash failed. Check the terminal output for details. Make sure the device is still in fastboot mode and try again.'
      }
    })
  } else {
    error.value = data?.error || 'Failed to start fastboot flash.'
    phase.value = 'fastboot-pick'
  }
}

/// --- App installation (post-flash) ---
const appsInstalling = ref(false)
const appsInstalled = ref(false)
const appsError = ref(false)
const appsTaskId = ref(null)

async function installApps() {
  const apps = state.selectedApps || []
  if (!apps.length) return
  appsInstalling.value = true
  appsError.value = false
  appsTaskId.value = null

  const { ok, data } = await post('/api/apps/install', {
    apps: apps.map(a => ({ id: a.id, name: a.name, url: a.url, install_method: a.install_method || 'adb' })),
  })

  if (ok && data?.task_id) {
    appsTaskId.value = data.task_id
    registerTask(data.task_id, 'Install apps')
    waitForTask(data.task_id, (status) => {
      appsInstalling.value = false
      if (status === 'done') {
        appsInstalled.value = true
      } else {
        appsError.value = true
      }
    })
  } else {
    appsInstalling.value = false
    appsError.value = true
  }
}

// --- Start over: clear all state ---
function startOver() {
  localStorage.removeItem(INSTALL_STORAGE_KEY)
  phase.value = 'pick'
  selectedRom.value = null
  downloadDest.value = ''
  backupDone.value = false
  skipBackup.value = false
  taskId.value = null
  sideloadTaskId.value = null
  miSideloadTaskId.value = null
  fbFlashTaskId.value = null
  miStockPath.value = ''
  fbImagePath.value = ''
  error.value = null
  signatureFailure.value = false
  recoveryInstallDone.value = false
  recoveryInstallError.value = false
  resetWizard()
  router.push('/wizard/identify')
}

// --- Persist install-step progress ---
watch(
  [phase, selectedRom, downloadDest, backupDone, skipBackup],
  () => {
    try {
      localStorage.setItem(INSTALL_STORAGE_KEY, JSON.stringify({
        phase: phase.value,
        selectedRom: selectedRom.value,
        downloadDest: downloadDest.value,
        backupDone: backupDone.value,
        skipBackup: skipBackup.value,
        codename: codename.value,
      }))
    } catch {}
  },
  { deep: true },
)

onUnmounted(() => {
  if (sideloadPollTimer) { clearInterval(sideloadPollTimer); sideloadPollTimer = null }
  setSubPhase(null)
})
</script>

<template>
  <div class="step-install">
  <div v-if="deviceLabel || codename" class="detect-box found">
    <strong>{{ deviceLabel }}</strong>
    <span v-if="model && model !== deviceLabel" class="detect-meta"> &middot; {{ model }}</span>
    <span v-if="codename && codename !== model" class="detect-meta"> &middot; {{ codename }}</span>
  </div>

  <!-- Phase indicator (standard ADB flow) -->
  <div v-if="!isMiAssistant && !isFastboot" class="install-phases">
    <div class="install-phase" :class="{ active: phase === 'pick', done: phase !== 'pick' }">Choose</div>
    <div class="install-phase-line" :class="{ filled: phase !== 'pick' }"></div>
    <div class="install-phase" :class="{ active: phase === 'download', done: ['backup','recovery','boot-recovery','sideload','done'].includes(phase) }">Download</div>
    <div class="install-phase-line" :class="{ filled: ['backup','recovery','boot-recovery','sideload','done'].includes(phase) }"></div>
    <div class="install-phase" :class="{ active: phase === 'backup', done: ['recovery','boot-recovery','sideload','done'].includes(phase) }">Backup</div>
    <div class="install-phase-line" :class="{ filled: ['recovery','boot-recovery','sideload','done'].includes(phase) }"></div>
    <div class="install-phase" :class="{ active: phase === 'recovery', done: ['boot-recovery','sideload','done'].includes(phase) }">Recovery</div>
    <div class="install-phase-line" :class="{ filled: ['boot-recovery','sideload','done'].includes(phase) }"></div>
    <div class="install-phase" :class="{ active: phase === 'boot-recovery', done: ['sideload','done'].includes(phase) }">Prepare</div>
    <div class="install-phase-line" :class="{ filled: ['sideload','done'].includes(phase) }"></div>
    <div class="install-phase" :class="{ active: phase === 'sideload', done: phase === 'done' }">Flash</div>
  </div>
  <!-- Phase indicator (MIAssistant sideload flow) -->
  <div v-else-if="isMiAssistant" class="install-phases">
    <div class="install-phase" :class="{ active: phase === 'miassistant-pick', done: ['miassistant-flash','done'].includes(phase) }">Select ROM</div>
    <div class="install-phase-line" :class="{ filled: ['miassistant-flash','done'].includes(phase) }"></div>
    <div class="install-phase" :class="{ active: phase === 'miassistant-flash', done: phase === 'done' }">Flash</div>
  </div>
  <!-- Phase indicator (fastboot flow) -->
  <div v-else-if="isFastboot" class="install-phases">
    <div class="install-phase" :class="{ active: phase === 'fastboot-pick', done: ['fastboot-flash','done'].includes(phase) }">Select Image</div>
    <div class="install-phase-line" :class="{ filled: ['fastboot-flash','done'].includes(phase) }"></div>
    <div class="install-phase" :class="{ active: phase === 'fastboot-flash', done: phase === 'done' }">Flash</div>
  </div>

  <!-- ==================== PHASE 1: Pick ROM ==================== -->
  <div v-if="phase === 'pick'">
    <div v-if="romfinderLoading" class="install-loading">
      <span class="spinner-small"></span> Searching for available operating systems...
    </div>

    <div v-else-if="allOs.length">
      <p class="step-desc">Choose an operating system to install:</p>
      <div class="rom-grid">
        <button
          v-for="os in allOs"
          :key="os.id"
          class="rom-card"
          :class="{ selected: selectedRom?.id === os.id }"
          @click="selectRom(os)"
        >
          <div class="rom-name">{{ os.name }}</div>
          <div v-if="os.desc" class="rom-desc">{{ os.desc }}</div>
          <div v-if="os.version" class="rom-version">v{{ os.version }}</div>
          <div class="rom-tags">
            <span v-for="tag in (os.tags || [])" :key="tag" class="rom-tag">{{ tag }}</span>
            <span v-if="os.download_url || os.ipfs_cid" class="rom-tag rom-tag-dl">Download</span>
            <span v-if="os.ipfs_cid" class="rom-tag rom-tag-ipfs">IPFS</span>
          </div>
        </button>
      </div>

      <div v-if="selectedRom" class="install-action">
        <button
          v-if="selectedRom.download_url || selectedRom.ipfs_cid"
          class="btn btn-large btn-primary"
          :disabled="loading"
          @click="startDownload"
        >
          Download {{ selectedRom.name }} &rarr;
        </button>
        <a v-if="selectedRom.page_url" :href="selectedRom.page_url" target="_blank" rel="noopener" class="btn btn-secondary">
          Visit download page &nearr;
        </a>
      </div>
    </div>

    <div v-else-if="!romfinderLoading && codename" class="info-box info-box--warn">
      No pre-built ROMs found for <strong>{{ codename }}</strong>. Check the community links below or provide a ROM file manually.
    </div>

    <div v-if="searchLinks.length" class="install-section">
      <label class="section-label">Community resources</label>
      <div class="search-links-row">
        <a v-for="link in searchLinks" :key="link.id" :href="link.url" target="_blank" rel="noopener" class="search-link">{{ link.name }} &nearr;</a>
      </div>
    </div>

    <div class="install-section">
      <button v-if="!showManual" class="btn btn-link" @click="showManual = true">I already have a ROM file &rarr;</button>
      <div v-if="showManual" class="manual-install">
        <div class="form-group">
          <label class="form-label">ROM ZIP file path</label>
          <input v-model="romPath" type="text" class="form-input" placeholder="/path/to/rom.zip" @input="onPathInput" />
        </div>
        <div v-if="pathValidating" class="path-status path-checking"><span class="spinner-small"></span> Checking file...</div>
        <div v-else-if="pathValidation && !pathValidation.valid" class="path-status path-invalid">{{ pathValidation.reason }}</div>
        <div v-else-if="pathValidation && pathValidation.valid" class="path-status path-valid">
          {{ pathValidation.filename }} ({{ pathValidation.size_human }})
          <span v-if="pathValidation.ext_warning" class="path-ext-warn">{{ pathValidation.ext_warning }}</span>
        </div>
        <button class="btn btn-primary" :disabled="!romPath.trim() || (pathValidation && !pathValidation.valid)" @click="useManualFile">Use this file &rarr;</button>
      </div>
    </div>
  </div>

  <!-- ==================== PHASE 2: Download ==================== -->
  <div v-if="phase === 'download'">
    <div class="install-guide-box">
      <h3>Downloading {{ selectedRom?.name }}...</h3>
      <p>This may take a few minutes depending on your connection. The file will be saved locally and shared via <GlossaryTip term="IPFS" /> for future use.</p>
    </div>

    <div v-if="retrying" class="install-guide-note install-guide-note-warn">
      Download failed — retrying automatically (attempt {{ downloadRetries + 1 }} of {{ MAX_DOWNLOAD_RETRIES + 1 }})...
    </div>

    <div v-if="taskId" ref="terminalRef" class="task-section">
      <TerminalOutput :task-id="taskId" />
    </div>

    <div v-if="error" class="info-box info-box--error" style="white-space: pre-line;">{{ error }}</div>
    <div v-if="error" class="install-action">
      <button class="btn btn-primary" @click="downloadRetries = 0; error = null; startDownload()">Try again</button>
      <button class="btn btn-secondary" @click="phase = 'pick'; error = null">&larr; Choose a different OS</button>
    </div>
  </div>

  <!-- ==================== PHASE 3: Backup ==================== -->
  <div v-if="phase === 'backup'">
    <div class="install-guide-box install-guide-success">
      <h3>Download complete!</h3>
      <p>{{ selectedRom?.name }} has been downloaded and verified.</p>
      <p v-if="downloadDest" class="install-file-path">{{ downloadDest }}</p>
    </div>

    <div class="install-guide-box">
      <h3>Back up your device</h3>
      <p>We recommend saving a copy of your device's current software before installing a new one. If anything goes wrong, you'll be able to restore it.</p>

      <!-- Not started yet -->
      <div v-if="!backupTaskId && !backupDone && !skipBackup" class="install-guide-actions">
        <button class="btn btn-primary" @click="startBackup">Back up now</button>
        <button class="btn btn-link" @click="skipBackup = true; backupDone = true">Skip backup &rarr;</button>
      </div>

      <!-- Running -->
      <div v-if="backupRunning" class="install-guide-status">
        <span class="spinner-small"></span> Backing up partitions...
      </div>

      <!-- Terminal output -->
      <TerminalOutput v-if="backupTaskId" :task-id="backupTaskId" />

      <!-- Results -->
      <div v-if="skipBackup" class="install-guide-note">
        Backup skipped. You can still back up later from the main menu.
      </div>
      <div v-else-if="backupDone && !backupError" class="install-guide-note install-guide-note-ok">
        Backup complete.
      </div>
      <div v-else-if="backupDone && backupError" class="install-guide-note install-guide-note-warn">
        Backup failed — your device may not support this feature. This is normal for most devices and won't prevent the install, but you won't have a copy of the original software to go back to.
      </div>
    </div>

    <div v-if="backupDone || skipBackup" class="install-action">
      <button class="btn btn-large btn-primary" @click="phase = 'recovery'">
        Continue &rarr;
      </button>
    </div>
  </div>

  <!-- ==================== PHASE 4: Custom Recovery ==================== -->
  <div v-if="phase === 'recovery'">
    <div class="install-guide-box">
      <h3><GlossaryTip term="recovery">Custom Recovery</GlossaryTip></h3>
      <p>To install <strong>{{ selectedRom?.name }}</strong>, your device needs a special install tool called a <GlossaryTip term="recovery">custom recovery</GlossaryTip>{{ recoverySource ? ` (${recoverySource.name})` : '' }}. The built-in recovery only accepts official updates and will reject third-party software.</p>
    </div>

    <!-- Already done from a previous attempt -->
    <div v-if="recoveryInstallDone" class="install-guide-box install-guide-success">
      <p><strong>{{ recoverySource?.name || 'Custom Recovery' }} is installed!</strong></p>
      <p>Now boot into recovery to flash {{ selectedRom?.name }}.</p>

      <div class="install-guide-box device-mode-card" style="margin: 1rem 0;">
        <div class="device-mode-header">
          <strong>{{ deviceLabel || 'Your device' }}</strong> &mdash; Boot into {{ recoverySource?.name || 'Recovery' }}
        </div>
        <ol class="install-steps">
          <li><strong>Unplug the USB cable</strong></li>
          <li v-if="brand === 'samsung'">Remove and reinsert the battery (if removable)</li>
          <li>Hold <strong>{{ recoveryModeCombo }}</strong></li>
          <li>Keep holding until the <strong>{{ recoverySource?.name || 'recovery' }}</strong> screen appears</li>
          <li>Plug the USB cable back in</li>
          <li v-if="recoverySource?.id === 'replicant-recovery'">In Replicant Recovery: select <strong>Apply update from ADB</strong></li>
          <li v-else>In TWRP: tap <strong>Advanced</strong>, then <strong><GlossaryTip term="ADB Sideload" /></strong>, then swipe to start</li>
        </ol>
        <p class="text-dim" style="margin-top: 0.5rem;">
          If your device boots back into Download Mode, make sure USB is <strong>unplugged</strong> during boot and you're holding the correct buttons.
        </p>
      </div>

      <div class="install-guide-actions">
        <button class="btn btn-large btn-primary" @click="proceedToBootRecovery">My device is in {{ recoverySource?.name || 'recovery' }} &rarr;</button>
      </div>
    </div>

    <div v-else-if="recoveryInstalling">
      <div class="install-guide-box">
        <p>Installing {{ recoverySource?.name || 'custom recovery' }} on your device...</p>
        <p class="text-dim">Make sure your device is in <strong><GlossaryTip term="Download Mode" /></strong> ({{ downloadModeCombo }}).</p>
      </div>
      <div class="task-section">
        <TerminalOutput v-if="recoveryInstallTaskId" :taskId="recoveryInstallTaskId" />
      </div>
    </div>

    <div v-else>
      <div class="recovery-options" style="margin-bottom: 1rem;">
        <button
          class="recovery-option"
          :class="{ selected: recoveryChoice === 'have-twrp' }"
          @click="recoveryChoice = 'have-twrp'"
        >
          <strong>I already have a custom recovery</strong>
          <span>{{ recoverySource?.name || 'Custom recovery' }} is installed on my device</span>
        </button>
        <button
          class="recovery-option"
          :class="{ selected: recoveryChoice === 'install' }"
          @click="recoveryChoice = 'install'"
        >
          <strong>Install {{ recoverySource?.name || 'custom recovery' }} for me</strong>
          <span>Download and flash the required recovery now</span>
        </button>
        <button
          class="recovery-option"
          :class="{ selected: recoveryChoice === 'skip' }"
          @click="recoveryChoice = 'skip'"
        >
          <strong>Try without custom recovery</strong>
          <span>Attempt sideload with stock recovery (may fail)</span>
        </button>
      </div>

      <!-- Install TWRP -->
      <div v-if="recoveryChoice === 'install'">
        <div class="install-guide-box device-mode-card">
          <div class="device-mode-header">
            <strong>{{ deviceLabel || 'Your device' }}</strong> &mdash; Download Mode
          </div>
          <ol class="install-steps">
            <li>Power off the device completely</li>
            <li>Hold <strong>{{ downloadModeCombo }}</strong></li>
            <li>Wait for the Download Mode screen to appear</li>
          </ol>
        </div>

        <div v-if="recoverySource" class="install-guide-box">
          <p>Ready to install <strong>{{ recoverySource.name || 'Custom Recovery' }}</strong> for {{ deviceLabel || 'your device' }}.</p>
          <div class="install-guide-actions">
            <button class="btn btn-primary" @click="installRecoveryNow">
              Install {{ recoverySource.name || 'Recovery' }} &rarr;
            </button>
          </div>
        </div>
        <div v-else class="install-guide-box">
          <p>We'll search for a compatible recovery image for {{ deviceLabel || 'your device' }}.</p>
          <div class="install-guide-actions">
            <button class="btn btn-primary" @click="installRecoveryNow">
              Find and install TWRP &rarr;
            </button>
          </div>
        </div>
        <div v-if="recoveryInstallError" class="install-guide-box install-guide-tip">
          <p>Automatic install failed. You can install TWRP manually:</p>
          <ol class="install-steps">
            <li>Find your device on <a href="https://twrp.me/Devices/" target="_blank" rel="noopener">twrp.me</a></li>
            <li>Download the .img file</li>
            <li>Put your device in Download Mode</li>
            <li>Use the <strong>Flash Recovery</strong> page in OSmosis to flash it</li>
          </ol>
        </div>
      </div>

      <!-- Already have TWRP or skip -->
      <div v-if="recoveryChoice === 'have-twrp' || recoveryChoice === 'skip'" class="install-action">
        <button class="btn btn-large btn-primary" @click="proceedToBootRecovery">
          Continue &rarr;
        </button>
        <p v-if="recoveryChoice === 'skip'" class="text-dim" style="margin-top: 0.5rem; text-align: center;">
          If stock recovery rejects the ROM, you'll need to come back and install the custom recovery.
        </p>
      </div>

      <div class="install-action" style="margin-top: 1rem;">
        <button class="btn btn-secondary" @click="phase = 'pick'">&larr; Choose a different OS</button>
        <button class="btn btn-secondary" @click="startOver">Start over</button>
      </div>
    </div>
  </div>

  <!-- ==================== PHASE 5: Boot into recovery ==================== -->
  <div v-if="phase === 'boot-recovery'">
    <div class="install-guide-box" :class="{ 'install-guide-success': sideloadReady }">
      <h3 v-if="sideloadReady">Device is in sideload mode!</h3>
      <h3 v-else>Booting into recovery mode...</h3>

      <!-- Auto-reboot in progress -->
      <div v-if="!rebootSent" class="install-guide-status">
        <span class="spinner-small"></span> Sending reboot command to device...
      </div>

      <!-- Reboot sent successfully, waiting for sideload -->
      <div v-else-if="rebootSent && !rebootFailed && !sideloadReady">
        <p>Reboot command sent. Your device should restart into recovery mode shortly.</p>

        <div v-if="deviceInRecovery" class="install-guide-note install-guide-note-ok">
          Device is in recovery mode. Now enable ADB sideload:
        </div>

        <ol class="install-steps">
          <li>Wait for the device to boot into recovery</li>
          <li>If you have <strong>TWRP</strong>: go to <strong>Advanced &rarr; ADB Sideload</strong>, then swipe to start</li>
          <li>If you have <strong>stock recovery</strong>: select <strong>Apply update from ADB</strong></li>
        </ol>

        <div class="install-guide-status">
          <span class="spinner-small"></span> Waiting for sideload mode...
        </div>
      </div>

      <!-- Reboot failed — show manual instructions -->
      <div v-else-if="rebootFailed && !sideloadReady">
        <p>Could not reboot automatically. Boot into recovery manually:</p>

        <div class="install-guide-box device-mode-card">
          <div class="device-mode-header">
            <strong>{{ deviceLabel || 'Your device' }}</strong> &mdash; Boot into Recovery
          </div>
          <ol class="install-steps">
            <li><strong>Unplug the USB cable</strong></li>
            <li v-if="brand === 'samsung'">Remove and reinsert the battery (if removable)</li>
            <li v-else>Hold <strong>Power for 10+ seconds</strong> to force restart</li>
            <li>Immediately hold <strong>{{ recoveryModeCombo }}</strong></li>
            <li>Keep holding until the recovery screen appears</li>
            <li>Plug the USB cable back in</li>
            <li v-if="recoveryInstallDone || recoveryChoice === 'have-twrp' || recoveryChoice === 'install'">
              In <strong>TWRP</strong>: go to <strong>Advanced &rarr; ADB Sideload &rarr; swipe to start</strong>
            </li>
            <li v-else-if="recoveryChoice === 'skip'">
              In stock recovery: select <strong>Apply update from ADB</strong>
            </li>
            <template v-else>
              <li>If <strong>TWRP</strong>: go to <strong>Advanced &rarr; ADB Sideload &rarr; swipe to start</strong></li>
              <li>If stock recovery: select <strong>Apply update from ADB</strong></li>
            </template>
          </ol>
        </div>

        <div v-if="stuckInDownloadMode" class="install-guide-box install-guide-tip" style="margin-top: 1rem; border-color: #e67e22;">
          <p><strong>Your device is still in Download Mode</strong> instead of recovery.</p>

          <div v-if="!bootRepairOffered">
            <p>This usually happens when USB is plugged in during boot. Try these steps:</p>
            <ol class="install-steps">
              <li><strong>Unplug the USB cable</strong></li>
              <li v-if="brand === 'samsung'"><strong>Remove the battery</strong>, wait 10 seconds, reinsert it</li>
              <li v-else>Hold <strong>Power 15+ seconds</strong> until completely off</li>
              <li>With USB <strong>unplugged</strong>, hold <strong>{{ recoveryModeCombo }}</strong></li>
              <li>Keep holding until TWRP appears, then plug USB in</li>
            </ol>
            <p class="text-dim" style="margin-top: 0.5rem;">
              If the Home button is physically stuck, press it firmly several times to unstick it.
            </p>
            <div style="margin-top: 0.75rem;">
              <button class="btn btn-secondary btn-small" @click="bootRepairOffered = true">
                Still stuck? Try boot repair
              </button>
            </div>
          </div>

          <div v-else>
            <p>Your device's boot partition may be corrupted, causing it to default to Download Mode.
               OSmosis can fix this by flashing TWRP to both the recovery <strong>and</strong> boot partitions.</p>
            <ol class="install-steps">
              <li>Make sure the device is in <strong>Download Mode</strong> and USB is <strong>plugged in</strong></li>
              <li>Click the button below — OSmosis will flash the boot partition</li>
              <li>After flashing: unplug USB, pull battery, reinsert, press Power</li>
              <li>The device should boot straight into TWRP</li>
            </ol>
            <div style="margin-top: 0.75rem;">
              <button class="btn btn-primary" :disabled="bootRepairing" @click="repairBoot">
                {{ bootRepairing ? 'Repairing...' : 'Repair boot partition' }}
              </button>
            </div>
          </div>
        </div>

        <details v-else class="troubleshoot-section" style="margin-top: 1rem;">
          <summary><strong>Device keeps booting into Download Mode?</strong></summary>
          <div class="install-guide-box" style="margin-top: 0.5rem;">
            <p>Some devices re-enter Download Mode when USB is connected during boot. Try:</p>
            <ol class="install-steps">
              <li><strong>Unplug USB</strong> before doing anything</li>
              <li v-if="brand === 'samsung'"><strong>Remove the battery</strong>, wait 10 seconds, reinsert it</li>
              <li v-else>Hold <strong>Power 15+ seconds</strong> until completely off</li>
              <li>With USB still <strong>unplugged</strong>, hold <strong>{{ recoveryModeCombo }}</strong></li>
              <li>Only plug USB in <strong>after</strong> you see the TWRP/recovery screen</li>
            </ol>
            <p class="text-dim">If the Home button is physically stuck, it can trigger Download Mode on every boot. Try gently pressing around the button to unstick it.</p>
          </div>
        </details>

        <div class="install-guide-status" style="margin-top: 1rem;">
          <span class="spinner-small"></span> Waiting for sideload mode...
        </div>
      </div>

      <!-- Sideload ready -->
      <div v-if="sideloadReady">
        <p>Proceeding to flash automatically...</p>
      </div>
    </div>

    <!-- Terminal output for reboot task -->
    <div v-if="recoveryTaskId" class="task-section">
      <TerminalOutput :task-id="recoveryTaskId" />
    </div>

    <div class="install-action">
      <button v-if="!sideloadReady" class="btn btn-large btn-primary" @click="proceedToSideload">
        My device is in sideload mode &rarr;
      </button>
      <button v-if="rebootFailed" class="btn btn-secondary" @click="startRebootRecovery">Retry automatic reboot</button>
      <button class="btn btn-secondary" @click="phase = 'recovery'">&larr; Back</button>
    </div>

  </div>

  <!-- ==================== PHASE 4: Sideload ==================== -->
  <div v-if="phase === 'sideload'">
    <div class="install-guide-box">
      <h3>Flashing {{ selectedRom?.name }}...</h3>
      <p>Sending the ROM to your device via ADB sideload. <strong>Do not disconnect your device.</strong></p>
    </div>

    <div v-if="!sideloadTaskId" class="install-action">
      <button class="btn btn-large btn-primary" :disabled="loading" @click="startSideload">
        Start sideload now
      </button>
    </div>

    <div v-if="sideloadTaskId" class="task-section">
      <TerminalOutput ref="sideloadTermRef" :task-id="sideloadTaskId" />
    </div>

    <!-- Signature verification failure — redirect to recovery step -->
    <div v-if="signatureFailure" class="install-guide-box install-guide-tip">
      <h3>Your stock recovery rejected the ROM</h3>
      <p>Stock recovery only accepts manufacturer-signed updates. To install <strong>{{ selectedRom?.name }}</strong>, you need a custom recovery{{ recoverySource ? ` (${recoverySource.name})` : '' }}.</p>
      <p>Your device is safe &mdash; nothing was changed.</p>
      <div class="install-guide-actions">
        <button class="btn btn-primary" @click="signatureFailure = false; recoveryChoice = 'install'; phase = 'recovery'">
          Install {{ recoverySource?.name || 'custom recovery' }} &rarr;
        </button>
        <button class="btn btn-secondary" @click="signatureFailure = false; startSideload()">
          Retry sideload
        </button>
      </div>
    </div>

    <!-- Incomplete transfer — offer push method -->
    <div v-if="incompleteTransfer" class="install-guide-box install-guide-tip">
      <h3>Transfer may be incomplete</h3>
      <p>The sideload ended early. Check your device screen:</p>
      <ul class="install-steps">
        <li>If TWRP shows <strong>"Install complete"</strong>: tap <strong>Reboot System</strong> &mdash; you're done!</li>
        <li>If TWRP shows <strong>"Zip corrupt"</strong> or an error: the transfer was cut short.</li>
      </ul>
      <p><strong>USB troubleshooting:</strong></p>
      <ul class="install-steps">
        <li>Use a shorter, higher-quality USB cable</li>
        <li>Connect directly to your computer (not a USB hub)</li>
        <li>Avoid moving the cable during transfer</li>
      </ul>
      <div class="install-guide-actions">
        <button class="btn btn-primary" @click="incompleteTransfer = false; startPushInstall()">
          Try push method (more reliable) &rarr;
        </button>
        <button class="btn btn-secondary" @click="incompleteTransfer = false; startSideload()">
          Retry sideload
        </button>
        <button class="btn btn-secondary" @click="phase = 'done'">
          It worked &mdash; continue
        </button>
      </div>
    </div>

    <!-- Typed error guide from backend -->
    <div v-if="errorGuide" class="install-guide-box install-guide-tip">
      <h3>{{ errorGuide.title }}</h3>
      <p>{{ errorGuide.message }}</p>
      <ol class="install-steps">
        <li v-for="(step, i) in errorGuide.steps" :key="i">{{ step }}</li>
      </ol>
      <div class="install-guide-actions">
        <button class="btn btn-primary" @click="errorGuide = null; startSideload()">Retry sideload</button>
        <button class="btn btn-secondary" @click="errorGuide = null; recoveryChoice = 'install'; phase = 'recovery'">Install custom recovery</button>
      </div>
    </div>

    <div v-if="error" class="info-box info-box--error" style="white-space: pre-line;">{{ error }}</div>

    <div v-if="!sideloadTaskId || error || signatureFailure || incompleteTransfer || errorGuide" class="install-action" style="margin-top: 1rem;">
      <button class="btn btn-secondary" @click="phase = 'pick'; sideloadTaskId = null; error = null">&larr; Choose a different OS</button>
      <button class="btn btn-secondary" @click="phase = 'recovery'; sideloadTaskId = null; error = null">&larr; Back to recovery</button>
    </div>
  </div>

  <!-- ==================== PHASE 5: Done ==================== -->
  <div v-if="phase === 'done'">
    <div class="install-guide-box install-guide-success">
      <h3>{{ isMiAssistant || isFastboot ? t('done.title', 'Installation complete!') : t('done.title', 'Installation complete!') }}</h3>
      <p v-if="selectedRom?.name"><strong>{{ selectedRom.name }}</strong> has been flashed to {{ deviceLabel || 'your device' }}.</p>
      <p v-else-if="isMiAssistant">Stock firmware has been flashed to {{ deviceLabel || 'your device' }} via MIAssistant sideload.</p>
      <p v-else-if="isFastboot">Firmware has been flashed to {{ deviceLabel || 'your device' }} via fastboot.</p>
      <p v-else>Firmware has been flashed to {{ deviceLabel || 'your device' }}.</p>
    </div>

    <div v-if="isMiAssistant" class="install-guide-box">
      <h3>What to do now</h3>
      <ol class="install-steps">
        <li>
          Wait for the device to verify and install the ROM
          <span class="step-hint">This may take several minutes. Do not unplug the device.</span>
        </li>
        <li>
          The device will reboot automatically when finished
          <span class="step-hint">The first boot after a stock restore can take 5-10 minutes.</span>
        </li>
        <li>
          Follow the on-screen setup wizard on your device
          <span class="step-hint">Choose your language, connect to Wi-Fi, and set up your account</span>
        </li>
      </ol>
    </div>
    <div v-else-if="isFastboot" class="install-guide-box">
      <h3>What to do now</h3>
      <ol class="install-steps">
        <li>
          The device should reboot automatically after flashing
          <span class="step-hint">If it stays in fastboot mode, run <strong>fastboot reboot</strong> or hold Power for 10 seconds.</span>
        </li>
        <li>
          Wait for the first boot to finish
          <span class="step-hint">This can take 5-10 minutes. Don't restart or unplug during this time.</span>
        </li>
        <li>
          Follow the on-screen setup wizard on your device
          <span class="step-hint">Choose your language, connect to Wi-Fi, and set up your account</span>
        </li>
      </ol>
    </div>
    <div v-else class="install-guide-box">
      <h3>What to do now</h3>
      <ol class="install-steps">
        <li>
          On your device screen, select <strong>Reboot System Now</strong>
          <span class="step-hint">You should see this option in your recovery menu</span>
        </li>
        <li>
          Wait for the first boot to finish
          <span class="step-hint">This can take 3-10 minutes — the screen may stay on a logo for a while. Don't restart or unplug during this time.</span>
        </li>
        <li>
          Follow the on-screen setup wizard on your device
          <span class="step-hint">Choose your language, connect to Wi-Fi, and set up your account</span>
        </li>
        <li v-if="state.selectedApps?.length">
          Keep the USB cable connected to install your selected apps after setup
        </li>
      </ol>
    </div>

    <details v-if="!isMiAssistant && !isFastboot" class="done-troubleshoot">
      <summary>Device stuck on a logo or not booting?</summary>
      <div class="done-troubleshoot-body">
        <p>If your device doesn't boot within 10 minutes:</p>
        <ol class="install-steps">
          <li>Hold <strong>{{ recoveryModeCombo }}</strong> to get back into recovery</li>
          <li>In recovery, select <strong>Wipe data / Factory reset</strong></li>
          <li>Then select <strong>Reboot System Now</strong> again</li>
        </ol>
        <p class="step-hint">A wipe is sometimes required after installing a new OS. This only erases data on the device, not the new OS you just installed.</p>
      </div>
    </details>

    <div v-if="state.selectedApps?.length && !appsInstalled" class="install-guide-box">
      <h3>Install apps</h3>
      <p>
        Once your device has fully booted and you've completed the initial setup,
        click below to download and install your selected apps via USB:
      </p>
      <ul class="install-steps">
        <li v-for="app in state.selectedApps" :key="app.id">
          <strong>{{ app.name }}</strong> <span v-if="app.desc" class="rom-desc">&mdash; {{ app.desc }}</span>
        </li>
      </ul>
      <div class="install-action">
        <button class="btn btn-primary" :disabled="appsInstalling" @click="installApps">
          {{ appsInstalling ? 'Installing apps...' : 'Install apps now' }}
        </button>
      </div>
      <div v-if="appsTaskId" class="task-section">
        <TerminalOutput :task-id="appsTaskId" />
      </div>
      <div v-if="appsError" class="info-box info-box--error">
        App installation failed. Make sure the device is fully booted and USB debugging is enabled, then try again.
      </div>
    </div>

    <div v-if="appsInstalled" class="info-box info-box--success">
      Apps installed successfully.
    </div>

    <div class="done-actions">
      <button class="btn btn-large btn-primary" @click="startOver">Flash another device</button>
      <router-link to="/apps" class="btn btn-secondary">Install more apps</router-link>
      <router-link to="/wiki" class="btn btn-secondary">Browse the wiki</router-link>
    </div>
  </div>

  <!-- ==================== MIAssistant Sideload: Pick ROM ==================== -->
  <div v-if="phase === 'miassistant-pick'">
    <div class="install-guide-box">
      <h3>{{ t('miassistant.pick.title', 'Restore stock firmware via MIAssistant') }}</h3>
      <p>{{ t('miassistant.pick.desc', 'Your Xiaomi device is in MIAssistant sideload mode. Provide the stock MIUI/HyperOS ROM ZIP to restore factory firmware.') }}</p>
    </div>

    <div v-if="state.detectedDevice?.match?.stock_url" class="install-guide-box install-guide-tip">
      <p><strong>{{ t('miassistant.pick.stock_available', 'Stock ROM available for your device') }}</strong></p>
      <p>{{ t('miassistant.pick.stock_download', 'Download the official ROM from the link below, then provide the file path.') }}</p>
      <a :href="state.detectedDevice.match.stock_url" target="_blank" rel="noopener" class="btn btn-secondary">
        {{ t('miassistant.pick.download_btn', 'Download stock ROM') }} &nearr;
      </a>
    </div>

    <div class="install-section">
      <div class="form-group">
        <label class="form-label">{{ t('miassistant.pick.zip_label', 'Stock ROM ZIP file path') }}</label>
        <input v-model="miStockPath" type="text" class="form-input" placeholder="/path/to/miui_RENOIR_stock.zip" @input="onMiStockPathInput" />
      </div>
      <div v-if="miStockValidating" class="path-status path-checking"><span class="spinner-small"></span> {{ t('progress.preparing', 'Preparing...') }}</div>
      <div v-else-if="miStockValidation && !miStockValidation.valid" class="path-status path-invalid">{{ miStockValidation.reason }}</div>
      <div v-else-if="miStockValidation && miStockValidation.valid" class="path-status path-valid">
        {{ miStockValidation.filename }} ({{ miStockValidation.size_human }})
      </div>
      <button class="btn btn-large btn-primary" :disabled="!miStockPath.trim() || (miStockValidation && !miStockValidation.valid) || loading" @click="startMiSideload">
        {{ t('miassistant.pick.flash_btn', 'Flash stock ROM') }} &rarr;
      </button>
    </div>

    <div class="install-guide-box" style="margin-top: 1.5rem;">
      <details>
        <summary><strong>{{ t('miassistant.pick.how_title', 'How to enter MIAssistant sideload mode') }}</strong></summary>
        <ol class="install-steps">
          <li>{{ t('miassistant.pick.how_step1', 'Power off the device') }}</li>
          <li>{{ t('miassistant.pick.how_step2', 'Hold Volume Down + Power to enter MIUI Recovery') }}</li>
          <li>{{ t('miassistant.pick.how_step3', 'Select "Connect with MIAssistant" from the recovery menu') }}</li>
          <li>{{ t('miassistant.pick.how_step4', 'The device will appear in ADB sideload mode') }}</li>
        </ol>
      </details>
    </div>
  </div>

  <!-- ==================== MIAssistant Sideload: Flashing ==================== -->
  <div v-if="phase === 'miassistant-flash'">
    <div class="install-guide-box">
      <h3>{{ t('miassistant.flash.title', 'Flashing stock ROM via MIAssistant...') }}</h3>
      <p>{{ t('miassistant.flash.desc', 'Sending the ROM to your device. Do not unplug the USB cable or touch the device.') }}</p>
    </div>

    <div v-if="miSideloadTaskId" ref="terminalRef" class="task-section">
      <TerminalOutput :task-id="miSideloadTaskId" />
    </div>

    <div v-if="error" class="info-box info-box--error" style="white-space: pre-line;">{{ error }}</div>
    <div v-if="error" class="install-action">
      <button class="btn btn-primary" @click="error = null; phase = 'miassistant-pick'">{{ t('miassistant.flash.retry', 'Try again') }}</button>
    </div>
  </div>

  <!-- ==================== Fastboot: Pick Image ==================== -->
  <div v-if="phase === 'fastboot-pick'">
    <div class="install-guide-box">
      <h3>{{ t('fastboot.pick.title', 'Flash via fastboot') }}</h3>
      <p>{{ t('fastboot.pick.desc', 'Your device is in fastboot mode. Provide a factory image ZIP to flash.') }}</p>
      <p v-if="state.detectedDevice?.unlocked === false" class="info-box info-box--warn" style="margin-top: 0.5rem;">
        {{ t('fastboot.pick.locked_warning', 'Bootloader is locked. You must unlock it before flashing. This usually requires an OEM unlock command and will erase all data.') }}
      </p>
    </div>

    <div class="install-section">
      <div class="form-group">
        <label class="form-label">{{ t('fastboot.pick.zip_label', 'Factory image ZIP file path') }}</label>
        <input v-model="fbImagePath" type="text" class="form-input" placeholder="/path/to/factory-image.zip" @input="onFbImagePathInput" />
      </div>
      <div v-if="fbImageValidating" class="path-status path-checking"><span class="spinner-small"></span> {{ t('progress.preparing', 'Preparing...') }}</div>
      <div v-else-if="fbImageValidation && !fbImageValidation.valid" class="path-status path-invalid">{{ fbImageValidation.reason }}</div>
      <div v-else-if="fbImageValidation && fbImageValidation.valid" class="path-status path-valid">
        {{ fbImageValidation.filename }} ({{ fbImageValidation.size_human }})
      </div>
      <button class="btn btn-large btn-primary" :disabled="!fbImagePath.trim() || (fbImageValidation && !fbImageValidation.valid) || loading" @click="startFastbootFlash">
        {{ t('fastboot.pick.flash_btn', 'Flash image') }} &rarr;
      </button>
    </div>
  </div>

  <!-- ==================== Fastboot: Flashing ==================== -->
  <div v-if="phase === 'fastboot-flash'">
    <div class="install-guide-box">
      <h3>{{ t('fastboot.flash.title', 'Flashing via fastboot...') }}</h3>
      <p>{{ t('fastboot.flash.desc', 'Sending the image to your device. Do not unplug the USB cable.') }}</p>
    </div>

    <div v-if="fbFlashTaskId" ref="terminalRef" class="task-section">
      <TerminalOutput :task-id="fbFlashTaskId" />
    </div>

    <div v-if="error" class="info-box info-box--error" style="white-space: pre-line;">{{ error }}</div>
    <div v-if="error" class="install-action">
      <button class="btn btn-primary" @click="error = null; phase = 'fastboot-pick'">{{ t('fastboot.flash.retry', 'Try again') }}</button>
    </div>
  </div>

  <!-- Nav -->
  <div class="step-nav">
    <button class="btn btn-secondary" v-if="phase === 'pick'" @click="router.push('/wizard/identify')">&larr; Back</button>
    <button class="btn btn-secondary" v-if="phase === 'backup'" @click="phase = 'pick'">&larr; Choose a different OS</button>
    <button class="btn btn-secondary" v-if="phase === 'miassistant-pick'" @click="router.push('/wizard/goal')">&larr; Back</button>
    <button class="btn btn-secondary" v-if="phase === 'fastboot-pick'" @click="router.push('/wizard/goal')">&larr; Back</button>
  </div>
  </div>
</template>

<style scoped>
/* ==========================================================
   Tablet-first responsive styles (768px base, scales down)
   ========================================================== */

/* Done screen */
.step-hint {
  display: block;
  font-size: calc(0.85rem * var(--font-scale, 1));
  color: var(--text-dim);
  margin-top: 0.15rem;
  font-weight: 400;
}
.done-troubleshoot {
  margin: 1rem 0;
  border: 1px solid var(--border);
  border-radius: var(--radius-card, 12px);
  padding: 0;
}
.done-troubleshoot summary {
  cursor: pointer;
  padding: 0.75rem 1rem;
  font-weight: 500;
  font-size: calc(0.95rem * var(--font-scale, 1));
  color: var(--text);
}
.done-troubleshoot-body {
  padding: 0 1rem 1rem;
}
.done-actions {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-top: 1.5rem;
}

/* Device-specific mode instructions card */
.device-mode-card {
  border-left: 3px solid var(--accent, #60a5fa);
  background: rgba(96, 165, 250, 0.06);
}
.device-mode-header {
  font-size: calc(0.9rem * var(--font-scale, 1));
  margin-bottom: 0.5rem;
  color: var(--accent, #60a5fa);
}

/* Phase indicator */
.install-phases {
  display: flex;
  align-items: center;
  gap: 0;
  margin: 1.25rem 0 2rem;
  padding: 0 0.5rem;
}

.install-phase {
  font-size: calc(0.85rem * var(--font-scale));
  font-weight: 500;
  color: var(--text-dim);
  padding: 0.4rem 0.75rem;
  border-radius: var(--radius-pill);
  white-space: nowrap;
}

.install-phase.active {
  color: var(--accent);
  font-weight: 600;
  background: rgba(54, 216, 183, 0.1);
}

.install-phase.done {
  color: var(--green, #4ade80);
}

.install-phase-line {
  flex: 1;
  height: 2px;
  background: var(--border);
  min-width: 16px;
}

.install-phase-line.filled {
  background: var(--green, #4ade80);
}

/* Loading */
.install-loading {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 2rem 0;
  color: var(--text-dim);
  font-size: calc(1rem * var(--font-scale));
}

.spinner-small {
  display: inline-block;
  width: 1.1rem;
  height: 1.1rem;
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ROM grid — 2 cols on tablet, 3 on wide, 1 on mobile */
.rom-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
  margin-bottom: 1.25rem;
}

.rom-card {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  padding: 1rem 1.15rem;
  border-radius: var(--radius-card);
  border: 2px solid var(--border);
  background: var(--bg-card);
  color: var(--text);
  cursor: pointer;
  text-align: left;
  transition: all var(--transition-fast);
  min-height: 48px;
}

.rom-card:hover { border-color: var(--accent); background: var(--bg-hover); }
.rom-card.selected { border-color: var(--accent); background: var(--bg-hover); box-shadow: inset 3px 0 0 var(--accent); }

.rom-name { font-weight: 600; font-size: calc(1.05rem * var(--font-scale)); }
.rom-desc { font-size: calc(0.85rem * var(--font-scale)); color: var(--text-dim); }
.rom-version { font-size: calc(0.8rem * var(--font-scale)); color: var(--text-dim); }

.rom-tags { display: flex; flex-wrap: wrap; gap: 0.3rem; margin-top: auto; padding-top: 0.35rem; }
.rom-tag {
  font-size: calc(0.7rem * var(--font-scale));
  padding: 0.15rem 0.5rem;
  border-radius: var(--radius-pill);
  background: rgba(54, 216, 183, 0.15);
  color: var(--accent);
  font-weight: 600;
}
.rom-tag-dl { background: rgba(100, 150, 255, 0.15); color: #6496ff; }
.rom-tag-ipfs { background: rgba(100, 200, 100, 0.15); color: #64c864; }

/* Guide boxes — generous padding on tablet */
.install-guide-box {
  padding: 1.5rem 1.75rem;
  border-radius: var(--radius-card);
  border: 1px solid var(--border);
  background: var(--bg-card);
  margin-bottom: 1.25rem;
}

.install-guide-box h3 {
  font-size: calc(1.15rem * var(--font-scale));
  font-weight: 600;
  margin: 0 0 0.6rem;
}

.install-guide-box p {
  color: var(--text-dim);
  font-size: calc(0.95rem * var(--font-scale));
  line-height: 1.6;
  margin: 0 0 0.6rem;
}

.install-guide-box p:last-child {
  margin-bottom: 0;
}

.install-guide-success {
  border-color: var(--accent);
  background: rgba(54, 216, 183, 0.06);
}

.install-guide-success h3 {
  color: var(--accent);
}

.install-guide-tip {
  border-color: var(--yellow, #fbbf24);
  background: rgba(251, 191, 36, 0.05);
}

.install-guide-tip a {
  color: var(--accent);
}

/* Recovery help */
.recovery-help-toggle {
  padding: 0;
  font-size: calc(0.95rem * var(--font-scale));
}

.recovery-options {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.6rem;
  margin: 1rem 0;
}

.recovery-option {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  padding: 0.85rem 1rem;
  border-radius: var(--radius-card);
  border: 2px solid var(--border);
  background: var(--bg-card);
  color: var(--text);
  cursor: pointer;
  text-align: left;
  transition: all var(--transition-fast);
  min-height: 44px;
}

.recovery-option:hover { border-color: var(--accent); }
.recovery-option.selected { border-color: var(--accent); background: var(--bg-hover); box-shadow: inset 3px 0 0 var(--accent); }

.recovery-option strong {
  font-size: calc(0.95rem * var(--font-scale));
}

.recovery-option span {
  font-size: calc(0.8rem * var(--font-scale));
  color: var(--text-dim);
}

.recovery-answer {
  margin-top: 0.75rem;
  padding: 1rem;
  border-radius: var(--radius-card);
  background: var(--bg-hover);
}

.recovery-answer p {
  color: var(--text) !important;
  margin: 0 0 0.5rem;
}

.recovery-answer p:last-child { margin-bottom: 0; }

.recovery-answer .text-dim { color: var(--text-dim) !important; }

.install-guide-actions {
  display: flex;
  gap: 1rem;
  align-items: center;
  margin-top: 0.75rem;
  flex-wrap: wrap;
}

.install-guide-note {
  font-size: calc(0.9rem * var(--font-scale));
  color: var(--text-dim);
  margin-top: 0.75rem;
  padding: 0.6rem 0.85rem;
  border-radius: var(--radius-card);
  background: var(--bg-hover);
  line-height: 1.5;
}

.install-guide-note-ok {
  color: var(--green, #4ade80);
  background: rgba(74, 222, 128, 0.08);
}

.install-guide-note-warn {
  color: var(--yellow, #fbbf24);
  background: rgba(251, 191, 36, 0.08);
}

.install-guide-status {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.6rem 0;
  color: var(--accent);
  font-weight: 500;
  font-size: calc(0.95rem * var(--font-scale));
}

.install-file-path {
  font-family: monospace;
  font-size: calc(0.8rem * var(--font-scale)) !important;
  color: var(--text-dim) !important;
  word-break: break-all;
}

/* Steps list — spacious for touch */
.install-steps {
  margin: 0.75rem 0;
  padding-left: 1.5rem;
  color: var(--text);
  font-size: calc(0.95rem * var(--font-scale));
  line-height: 2;
}

.install-steps li {
  margin-bottom: 0.35rem;
}

/* Action bar — centered on tablet */
.install-action {
  display: flex;
  gap: 1rem;
  align-items: center;
  justify-content: center;
  margin: 1.5rem 0;
  flex-wrap: wrap;
}

.install-section {
  margin-bottom: 1.25rem;
}

.section-label {
  display: block;
  font-weight: 600;
  font-size: calc(0.95rem * var(--font-scale));
  margin-bottom: 0.6rem;
}

.search-links-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
}

.search-link {
  padding: 0.5rem 1rem;
  border-radius: var(--radius-pill);
  border: 1px solid var(--border);
  background: var(--bg-card);
  color: var(--text);
  text-decoration: none;
  font-size: calc(0.9rem * var(--font-scale));
  transition: border-color var(--transition-fast);
  min-height: 44px;
  display: inline-flex;
  align-items: center;
}
.search-link:hover { border-color: var(--accent); color: var(--accent); }

.manual-install {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  max-width: 500px;
}

/* Task terminal */
.task-section {
  margin: 1.25rem 0;
  border: 2px solid var(--accent);
  border-radius: var(--radius-card);
  overflow: hidden;
}

.info-box--error {
  border-color: var(--red, #f87171);
  color: var(--red, #f87171);
}

/* ========================
   Wide screens (1024px+)
   ======================== */
@media (min-width: 1024px) {
  .rom-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

/* ========================
   Mobile (<600px)
   ======================== */
@media (max-width: 599px) {
  .install-phases {
    margin: 0.75rem 0 1rem;
    padding: 0;
  }

  .install-phase {
    font-size: calc(0.7rem * var(--font-scale));
    padding: 0.25rem 0.4rem;
  }

  .rom-grid,
  .recovery-options {
    grid-template-columns: 1fr;
  }

  .install-guide-box {
    padding: 1rem 1.15rem;
  }

  .install-guide-box h3 {
    font-size: calc(1rem * var(--font-scale));
  }

  .install-action {
    flex-direction: column;
    align-items: stretch;
  }

  .install-action .btn {
    text-align: center;
  }
}
</style>
