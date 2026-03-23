<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { useWizard } from '@/composables/useWizard'

const { t } = useI18n()
const router = useRouter()
const { get, post } = useApi()
const { state } = useWizard()

// Steps: select-board → detect → select-firmware → flash
const step = ref('select-board')

// Board selection
const boards = ref([])
const brandFilter = ref('')
const searchQuery = ref('')
const selectedBoard = ref(null)
const loading = ref(false)

// Detection
const detecting = ref(false)
const detectedDevices = ref([])
const selectedPort = ref('')
const uf2Mount = ref('')

// Tools
const tools = ref({})

// Firmware
const fwPath = ref('')

// Flash
const flashing = ref(false)
const flashTaskId = ref(null)
const flashLog = ref([])
const flashDone = ref(false)
const flashSuccess = ref(false)

const brands = ['Arduino', 'Espressif', 'Raspberry Pi', 'STMicro', 'PJRC', 'Adafruit', 'Seeed', 'SparkFun', 'BBC']

const filteredBoards = computed(() => {
  let list = boards.value
  if (brandFilter.value) {
    list = list.filter(b => b.brand === brandFilter.value)
  }
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter(b =>
      b.label.toLowerCase().includes(q) ||
      b.id.toLowerCase().includes(q) ||
      b.arch.toLowerCase().includes(q) ||
      b.notes.toLowerCase().includes(q)
    )
  }
  return list
})

const boardsByBrand = computed(() => {
  const groups = {}
  for (const b of filteredBoards.value) {
    if (!groups[b.brand]) groups[b.brand] = []
    groups[b.brand].push(b)
  }
  return groups
})

const requiredTool = computed(() => {
  if (!selectedBoard.value) return null
  const tool = selectedBoard.value.flash_tool
  const toolMap = {
    'arduino-cli': 'arduino_cli',
    'esptool': 'esptool',
    'picotool': 'picotool',
    'stflash': 'stflash',
    'openocd': 'openocd',
    'avrdude': 'avrdude',
    'dfu-util': 'dfu_util',
    'teensy_loader_cli': 'teensy_loader',
  }
  const key = toolMap[tool]
  return key ? { name: tool, installed: !!tools.value[key] } : null
})

onMounted(async () => {
  const [boardRes, toolRes] = await Promise.all([
    get('/api/microcontrollers'),
    get('/api/microcontrollers/tools'),
  ])
  if (boardRes.ok) boards.value = boardRes.data
  if (toolRes.ok) tools.value = toolRes.data
})

function selectBoard(board) {
  selectedBoard.value = board
}

function proceedToDetect() {
  step.value = 'detect'
  detect()
}

async function detect() {
  detecting.value = true
  detectedDevices.value = []
  const { ok, data } = await get('/api/microcontrollers/detect')
  detecting.value = false

  if (ok && data.devices) {
    detectedDevices.value = data.devices
    // Auto-select the port if there's exactly one serial device
    const serialDevs = data.devices.filter(d => d.type === 'serial')
    if (serialDevs.length === 1) {
      selectedPort.value = serialDevs[0].port
    }
    // Auto-select UF2 mount if applicable
    const uf2Devs = data.devices.filter(d => d.type === 'uf2')
    if (uf2Devs.length === 1) {
      uf2Mount.value = uf2Devs[0].mount
    }
  }
}

function proceedToFirmware() {
  step.value = 'firmware'
}

async function flash() {
  if (!fwPath.value || !selectedBoard.value) return

  flashing.value = true
  flashLog.value = []
  flashDone.value = false
  flashSuccess.value = false
  step.value = 'flash'

  const { ok, data } = await post('/api/microcontrollers/flash', {
    board_id: selectedBoard.value.id,
    fw_path: fwPath.value,
    port: selectedPort.value,
    uf2_mount: uf2Mount.value,
  })

  if (!ok || !data.task_id) {
    flashLog.value.push({ level: 'error', msg: data?.error || 'Failed to start flash task' })
    flashing.value = false
    flashDone.value = true
    return
  }

  flashTaskId.value = data.task_id

  // Stream task output via SSE
  const es = new EventSource(`/api/task/${data.task_id}/stream`)
  es.onmessage = (e) => {
    try {
      const msg = JSON.parse(e.data)
      flashLog.value.push(msg)
      if (msg.level === 'done') {
        flashDone.value = true
        flashSuccess.value = msg.msg === 'done'
        flashing.value = false
        es.close()
      }
    } catch {
      flashLog.value.push({ level: 'info', msg: e.data })
    }
  }
  es.onerror = () => {
    flashing.value = false
    flashDone.value = true
    es.close()
  }
}
</script>

<template>
  <h2 class="step-title">{{ t('step.mcu.title', 'Flash a microcontroller') }}</h2>

  <!-- Step 1: Select board -->
  <div v-if="step === 'select-board'">
    <p class="step-desc">Select your board from the list, or search by name.</p>

    <!-- Brand filter -->
    <div class="mcu-brand-filter">
      <button
        class="identify-brand-chip"
        :class="{ selected: brandFilter === '' }"
        @click="brandFilter = ''"
      >All</button>
      <button
        v-for="b in brands"
        :key="b"
        class="identify-brand-chip"
        :class="{ selected: brandFilter === b }"
        @click="brandFilter = brandFilter === b ? '' : b"
      >{{ b }}</button>
    </div>

    <!-- Search -->
    <div class="form-group" style="margin-top: 0.75rem;">
      <input
        v-model="searchQuery"
        type="text"
        placeholder="Search boards (e.g. Pico, ESP32-S3, Uno)..."
      >
    </div>

    <!-- Board list grouped by brand -->
    <div class="mcu-board-list">
      <div v-for="(groupBoards, brandName) in boardsByBrand" :key="brandName" class="mcu-brand-group">
        <h4 class="mcu-brand-heading">{{ brandName }}</h4>
        <div class="mcu-board-grid">
          <button
            v-for="board in groupBoards"
            :key="board.id"
            class="identify-device-card"
            :class="{ selected: selectedBoard && selectedBoard.id === board.id }"
            @click="selectBoard(board)"
          >
            <div class="identify-device-name">{{ board.label }}</div>
            <div class="identify-device-meta">
              {{ board.arch }}
              <span v-if="board.notes"> &middot; {{ board.notes }}</span>
            </div>
            <div class="identify-device-tags">
              <span class="identify-tag">{{ board.flash_tool }}</span>
              <span v-if="board.bootloader !== 'native'" class="identify-tag">{{ board.bootloader }}</span>
            </div>
          </button>
        </div>
      </div>
    </div>

    <!-- Tool check warning -->
    <div v-if="requiredTool && !requiredTool.installed" class="detect-box not-found" style="margin-top: 1rem;">
      <strong>{{ requiredTool.name }}</strong> is not installed.
      You'll need it to flash this board. Install it before continuing.
    </div>

    <div class="step-actions">
      <button
        class="btn btn-large btn-primary"
        :disabled="!selectedBoard"
        @click="proceedToDetect"
      >Continue &rarr;</button>
    </div>
  </div>

  <!-- Step 2: Detect device -->
  <div v-if="step === 'detect'">
    <p class="step-desc">
      Connect your <strong>{{ selectedBoard?.label }}</strong> via USB.
    </p>

    <div class="step-illustration">
      <div class="illustration-box">
        <div class="plug-icon">&#x1F50C;</div>
        <div class="arrow-icon">&rarr;</div>
        <div class="device-icon">&#x2699;&#xFE0F;</div>
      </div>
    </div>

    <div v-if="selectedBoard?.bootloader === 'uf2'" class="mcu-hint">
      <strong>UF2 boards:</strong> Hold the BOOTSEL button while plugging in to enter bootloader mode.
    </div>
    <div v-if="selectedBoard?.bootloader === 'stlink'" class="mcu-hint">
      <strong>ST-Link:</strong> Connect your ST-Link programmer to the board's SWD header.
    </div>

    <div class="step-actions">
      <button
        class="btn btn-large btn-primary"
        :class="{ 'btn-loading': detecting }"
        :disabled="detecting"
        @click="detect"
      >
        <span class="btn-icon">&#x1F50D;</span>
        <span>Scan for devices</span>
      </button>
    </div>

    <!-- Detection results -->
    <div v-if="detectedDevices.length" class="mcu-detected">
      <label class="identify-section-label">Detected devices</label>
      <div v-for="dev in detectedDevices" :key="dev.port || dev.mount" class="detect-box found">
        <div v-if="dev.type === 'serial'">
          <strong>{{ dev.product || dev.brand }}</strong>
          <span class="text-dim"> &mdash; {{ dev.port }}</span>
          <div v-if="dev.match" class="identify-device-meta" style="margin-top: 0.25rem;">
            Matched: {{ dev.match.label }}
          </div>
          <div style="margin-top: 0.4rem;">
            <button
              class="btn btn-sm"
              :class="{ 'btn-primary': selectedPort === dev.port }"
              @click="selectedPort = dev.port"
            >{{ selectedPort === dev.port ? 'Selected' : 'Use this port' }}</button>
          </div>
        </div>
        <div v-else-if="dev.type === 'uf2'">
          <strong>UF2 Drive</strong>
          <span class="text-dim"> &mdash; {{ dev.mount }}</span>
          <div v-if="dev.model" class="identify-device-meta" style="margin-top: 0.25rem;">
            {{ dev.model }} ({{ dev.board_id }})
          </div>
          <div style="margin-top: 0.4rem;">
            <button
              class="btn btn-sm"
              :class="{ 'btn-primary': uf2Mount === dev.mount }"
              @click="uf2Mount = dev.mount"
            >{{ uf2Mount === dev.mount ? 'Selected' : 'Use this drive' }}</button>
          </div>
        </div>
      </div>
    </div>

    <div v-else-if="!detecting && detectedDevices.length === 0" class="detect-box not-found" style="margin-top: 1rem;">
      No microcontroller detected. Make sure the board is connected and in the right mode.
    </div>

    <!-- Manual port input -->
    <div class="form-group" style="margin-top: 1rem;">
      <label>Serial port <span class="text-dim">(auto-filled or enter manually)</span></label>
      <input
        v-model="selectedPort"
        type="text"
        placeholder="/dev/ttyUSB0 or /dev/ttyACM0"
      >
    </div>

    <div class="step-actions">
      <button class="btn btn-large btn-primary" @click="proceedToFirmware">
        Continue &rarr;
      </button>
    </div>

    <div class="step-nav">
      <button class="btn btn-secondary" @click="step = 'select-board'">&larr; Back</button>
    </div>
  </div>

  <!-- Step 3: Select firmware -->
  <div v-if="step === 'firmware'">
    <p class="step-desc">
      Provide the firmware file to flash to your <strong>{{ selectedBoard?.label }}</strong>.
    </p>

    <div class="form-group">
      <label>Firmware file path</label>
      <input
        v-model="fwPath"
        type="text"
        :placeholder="selectedBoard?.bootloader === 'uf2'
          ? 'e.g. /home/user/firmware.uf2'
          : selectedBoard?.flash_tool === 'esptool'
            ? 'e.g. /home/user/firmware.bin'
            : selectedBoard?.flash_tool === 'arduino-cli'
              ? 'e.g. /home/user/sketch.ino.hex'
              : 'e.g. /home/user/firmware.bin'"
      >
    </div>

    <div v-if="selectedBoard" class="mcu-flash-summary">
      <h4>Flash summary</h4>
      <table class="mcu-summary-table">
        <tr><td>Board</td><td>{{ selectedBoard.label }}</td></tr>
        <tr><td>Architecture</td><td>{{ selectedBoard.arch }}</td></tr>
        <tr><td>Flash tool</td><td>{{ selectedBoard.flash_tool }}</td></tr>
        <tr v-if="selectedPort"><td>Port</td><td>{{ selectedPort }}</td></tr>
        <tr v-if="uf2Mount"><td>UF2 drive</td><td>{{ uf2Mount }}</td></tr>
        <tr v-if="fwPath"><td>Firmware</td><td>{{ fwPath }}</td></tr>
      </table>
    </div>

    <div class="step-actions">
      <button
        class="btn btn-large btn-primary"
        :disabled="!fwPath"
        @click="flash"
      >Flash firmware</button>
    </div>

    <div class="step-nav">
      <button class="btn btn-secondary" @click="step = 'detect'">&larr; Back</button>
    </div>
  </div>

  <!-- Step 4: Flash progress -->
  <div v-if="step === 'flash'">
    <p class="step-desc">
      Flashing <strong>{{ selectedBoard?.label }}</strong>...
    </p>

    <div class="mcu-flash-log">
      <div
        v-for="(entry, i) in flashLog"
        :key="i"
        class="log-line"
        :class="`log-${entry.level}`"
      >{{ entry.msg }}</div>
    </div>

    <div v-if="flashDone" class="step-actions">
      <div v-if="flashSuccess" class="detect-box found">
        Firmware flashed successfully!
      </div>
      <div v-else class="detect-box not-found">
        Flash failed. Check the log above for errors.
      </div>
      <button class="btn btn-primary" @click="step = 'select-board'" style="margin-top: 1rem;">
        Flash another board
      </button>
    </div>
  </div>

  <div class="step-nav" v-if="step === 'select-board'">
    <button class="btn btn-secondary" @click="router.push('/wizard/identify')">&larr; Back</button>
  </div>
</template>

<style scoped>
.mcu-brand-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-bottom: 0.5rem;
}

.mcu-board-list {
  margin-top: 1rem;
  max-height: 50vh;
  overflow-y: auto;
  padding-right: 0.5rem;
}

.mcu-brand-group {
  margin-bottom: 1.5rem;
}

.mcu-brand-heading {
  font-weight: 600;
  font-size: calc(1rem * var(--font-scale));
  margin-bottom: 0.5rem;
  color: var(--accent);
}

.mcu-board-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 0.5rem;
}

.mcu-hint {
  background: rgba(54, 216, 183, 0.1);
  border: 1px solid var(--accent);
  border-radius: var(--radius-card);
  padding: 0.75rem 1rem;
  margin: 1rem 0;
  font-size: calc(0.9rem * var(--font-scale));
}

.mcu-detected {
  margin-top: 1rem;
}

.mcu-flash-summary {
  margin-top: 1.5rem;
  padding: 1rem;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
}

.mcu-flash-summary h4 {
  margin: 0 0 0.75rem 0;
  font-weight: 600;
}

.mcu-summary-table {
  width: 100%;
  border-collapse: collapse;
}

.mcu-summary-table td {
  padding: 0.3rem 0.5rem;
  border-bottom: 1px solid var(--border);
  font-size: calc(0.9rem * var(--font-scale));
}

.mcu-summary-table td:first-child {
  font-weight: 600;
  color: var(--text-dim);
  width: 120px;
}

.mcu-flash-log {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
  padding: 1rem;
  max-height: 400px;
  overflow-y: auto;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: calc(0.8rem * var(--font-scale));
  line-height: 1.6;
}

.log-line { color: var(--text-dim); }
.log-cmd { color: var(--accent); opacity: 0.8; }
.log-success { color: #36d8b7; font-weight: 600; }
.log-error { color: #ff6b6b; font-weight: 600; }
.log-warn { color: #ffd93d; }
.log-info { color: var(--text); }

.btn-sm {
  padding: 0.25rem 0.75rem;
  font-size: calc(0.8rem * var(--font-scale));
  border-radius: var(--radius-pill);
  border: 1px solid var(--border);
  background: var(--bg);
  color: var(--text);
  cursor: pointer;
}
</style>
