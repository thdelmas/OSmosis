<script setup>
import { ref, computed, onMounted, onUnmounted, inject } from 'vue'
import { useRouter } from 'vue-router'
import { useApi } from '@/composables/useApi'
import { useWizard } from '@/composables/useWizard'
import TerminalOutput from '@/components/shared/TerminalOutput.vue'

const router = useRouter()
const { get, post } = useApi()
const { state, setDevice } = useWizard()
const registerTask = inject('registerTask', () => {})

// Phase: detect → pick → install → done
const phase = ref('detect')
const error = ref(null)

// Detection
const detecting = ref(false)
const device = ref(null)
let detectTimer = null

// Software selection
const installKoreader = ref(true)
const installNickelmenu = ref(true)

// Install progress
const taskId = ref(null)
const installDone = ref(false)
const installError = ref(false)

const koboModels = {
  'N306': 'Kobo Libra Colour',
  'N418': 'Kobo Clara Colour',
  'N604': 'Kobo Touch',
  'N905': 'Kobo Mini',
  'N613': 'Kobo Glo',
  'N236': 'Kobo Aura 2',
  'N249': 'Kobo Clara HD',
  'N873': 'Kobo Libra H2O',
  'N778': 'Kobo Forma',
  'N867': 'Kobo Elipsa',
  'N587': 'Kobo Sage',
}

const modelName = computed(() => {
  if (!device.value?.model) return 'Kobo e-reader'
  return koboModels[device.value.model] || `Kobo ${device.value.model}`
})

async function detect() {
  detecting.value = true
  error.value = null

  const { ok, data } = await get('/api/ereader/detect')
  detecting.value = false

  if (ok && data && !data.error) {
    device.value = data
    setDevice({
      display_name: modelName.value,
      model: data.model || '',
      brand: 'Kobo',
      mount: data.mount,
    })
    phase.value = 'pick'
  } else {
    error.value = data?.hint
      || 'No e-reader detected. Connect your Kobo via USB and tap "Connect" on the device screen.'
  }
}

onMounted(() => {
  detect()
  detectTimer = setInterval(() => {
    if (!device.value && !detecting.value) detect()
  }, 4000)
})

onUnmounted(() => {
  if (detectTimer) clearInterval(detectTimer)
})

async function startInstall() {
  error.value = null
  installDone.value = false
  installError.value = false
  phase.value = 'install'

  const body = {
    koreader_url: 'https://github.com/koreader/koreader/releases/latest/download/koreader-kobo-arm-linux-gnueabihf-latest.zip',
  }
  if (installNickelmenu.value) {
    body.nickelmenu_url = 'https://github.com/pgaskin/NickelMenu/releases/latest/download/KoboRoot.tgz'
  }

  const { ok, data } = await post(
    '/api/ereader/install-koreader', body,
  )

  if (ok && data?.task_id) {
    taskId.value = data.task_id
    registerTask(data.task_id, 'Install KOReader')
    waitForTask(data.task_id)
  } else {
    installError.value = true
    error.value = data?.error || 'Failed to start installation.'
  }
}

function waitForTask(id) {
  const start = Date.now()
  const poll = setInterval(async () => {
    if (Date.now() - start > 300000) {
      clearInterval(poll)
      installError.value = true
      error.value = 'Installation timed out.'
      return
    }
    const resp = await get('/api/tasks')
    if (!resp.ok) return
    const task = resp.data?.find(t => t.id === id)
    if (!task || task.status === 'running') return
    clearInterval(poll)
    if (task.status === 'done') {
      installDone.value = true
      phase.value = 'done'
    } else {
      installError.value = true
      error.value = 'Installation failed. Check output above.'
    }
  }, 2000)
}
</script>

<template>
  <h2 class="step-title">E-Reader Setup</h2>

  <!-- DETECT -->
  <div v-if="phase === 'detect'">
    <p class="step-desc">
      Connect your Kobo e-reader via USB. When the Kobo
      screen asks how to connect, choose
      <strong>Connect</strong> (not "Charge only").
    </p>

    <div class="step-illustration" aria-hidden="true">
      <div class="illustration-box">
        <div class="plug-icon">&#x1F50C;</div>
        <div class="arrow-icon">&rarr;</div>
        <div class="device-icon">&#x1F4D6;</div>
      </div>
    </div>

    <div class="step-actions">
      <button
        class="btn btn-large btn-primary"
        :class="{ 'btn-loading': detecting }"
        :disabled="detecting"
        @click="detect"
      >
        <span v-if="detecting">Scanning...</span>
        <span v-else>Find my e-reader</span>
      </button>
    </div>

    <div v-if="error" class="info-box info-box--warn">
      {{ error }}
    </div>
  </div>

  <!-- PICK SOFTWARE -->
  <div v-if="phase === 'pick'">
    <div class="detect-box found">
      <strong>{{ modelName }}</strong>
      <span v-if="device.firmware" class="text-dim">
        &mdash; firmware {{ device.firmware }}
      </span>
      <div class="text-dim" style="margin-top: 0.25rem;">
        Mounted at {{ device.mount }}
      </div>
    </div>

    <h3 class="section-title">What to install</h3>

    <label class="ereader-option">
      <input type="checkbox" v-model="installKoreader" disabled />
      <div class="ereader-option-info">
        <strong>KOReader</strong>
        <span class="ereader-option-desc">
          Open-source reading app. Supports EPUB, PDF, DjVu,
          CBZ, and more. Highly configurable.
        </span>
        <span class="rom-tag">recommended</span>
      </div>
    </label>

    <label class="ereader-option">
      <input type="checkbox" v-model="installNickelmenu" />
      <div class="ereader-option-info">
        <strong>NickelMenu</strong>
        <span class="ereader-option-desc">
          Adds a launcher menu to the Kobo home screen so
          you can switch between Nickel (stock) and KOReader.
        </span>
        <span class="rom-tag">optional</span>
      </div>
    </label>

    <div class="info-box" style="margin-top: 1rem;">
      This is non-destructive. Your books and settings are
      preserved. You can uninstall later by deleting the
      KOReader folder from the device.
    </div>

    <div class="install-action">
      <button class="btn btn-large btn-primary" @click="startInstall">
        Install &rarr;
      </button>
    </div>

    <div class="step-nav">
      <button
        class="btn btn-secondary"
        @click="phase = 'detect'; device = null"
      >&larr; Back</button>
    </div>
  </div>

  <!-- INSTALLING -->
  <div v-if="phase === 'install'">
    <div class="install-guide-box">
      <h3>Installing on {{ modelName }}...</h3>
      <p>
        Do <strong>not</strong> unplug the USB cable until
        the installation is complete.
      </p>
    </div>

    <div v-if="taskId" class="task-section">
      <TerminalOutput :task-id="taskId" />
    </div>

    <div v-if="installError" class="info-box info-box--error">
      {{ error || 'Installation failed.' }}
      <div style="margin-top: 0.5rem;">
        <button class="btn btn-secondary" @click="startInstall">
          Retry
        </button>
        <button
          class="btn btn-secondary"
          @click="phase = 'pick'"
        >&larr; Back</button>
      </div>
    </div>
  </div>

  <!-- DONE -->
  <div v-if="phase === 'done'">
    <div class="install-guide-box install-guide-success">
      <h3>Installation complete!</h3>
      <p>KOReader has been installed on your {{ modelName }}.</p>
    </div>

    <div class="ereader-next-steps">
      <h3 class="section-title">Next steps</h3>
      <ol>
        <li>
          <strong>Safely eject</strong> the Kobo from your
          file manager (or click the eject icon in your
          system tray)
        </li>
        <li>
          <strong>Disconnect</strong> the USB cable
        </li>
        <li>
          The Kobo will process the update and restart
          automatically
        </li>
        <li v-if="installNickelmenu">
          Open the Kobo menu &mdash; you'll see a new
          <strong>KOReader</strong> entry added by NickelMenu
        </li>
        <li v-else>
          Launch KOReader from the Kobo home screen
          (it appears as a new option)
        </li>
      </ol>
    </div>

    <div class="step-actions">
      <button
        class="btn btn-large btn-primary"
        @click="router.push('/wizard/identify')"
      >Done &mdash; back to start</button>
    </div>
  </div>
</template>

<style scoped>
.section-title {
  font-size: calc(1rem * var(--font-scale, 1));
  font-weight: 600;
  margin: 1.25rem 0 0.75rem;
}

.ereader-option {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 0.85rem 1rem;
  border-radius: var(--radius-card, 12px);
  border: 2px solid var(--border, #333);
  background: var(--bg-card, #1a1a2e);
  margin-bottom: 0.5rem;
  cursor: pointer;
  transition: border-color 0.15s;
}

.ereader-option:hover {
  border-color: var(--accent, #36d8b7);
}

.ereader-option input[type="checkbox"] {
  margin-top: 0.2rem;
  accent-color: var(--accent, #36d8b7);
  width: 1.1rem;
  height: 1.1rem;
}

.ereader-option-info {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.ereader-option-desc {
  font-size: calc(0.85rem * var(--font-scale, 1));
  color: var(--text-dim, #888);
  line-height: 1.4;
}

.ereader-next-steps ol {
  padding-left: 1.5rem;
  line-height: 1.8;
}

.ereader-next-steps li {
  margin-bottom: 0.25rem;
}
</style>
