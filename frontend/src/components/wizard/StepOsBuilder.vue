<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import TerminalOutput from '@/components/shared/TerminalOutput.vue'

const { t } = useI18n()
const router = useRouter()
const { get, post } = useApi()

// Options loaded from API
const options = ref(null)
const selectedBase = ref('debian')
const taskId = ref(null)
const previewData = ref(null)
const sizeEstimate = ref(null)
const buildComplete = ref(false)

// Form state
const form = ref({
  name: 'my-os',
  suite: '',
  arch: 'amd64',
  target_device: 'generic-x86_64',
  output_format: 'img',
  image_size_mb: 4096,
  hostname: 'osmosis',
  locale: 'en_US.UTF-8',
  timezone: 'UTC',
  keyboard_layout: 'us',
  username: 'user',
  password: '',
  ssh_keys: '',
  extra_packages: '',
  desktop: 'none',
  network: 'dhcp',
  static_ip: '',
  gateway: '',
  dns: '1.1.1.1, 9.9.9.9',
  firewall: 'none',
  disk_layout: 'auto',
  post_install_script: '',
  ipfs_publish: false,
})

const bases = [
  { id: 'debian', icon: '\u{1F4E6}', label: 'Debian', desc: 'Stable, minimal, versatile. The universal base.' },
  { id: 'ubuntu', icon: '\u{1F7E0}', label: 'Ubuntu', desc: 'User-friendly with broad hardware support and PPAs.' },
  { id: 'arch', icon: '\u{1F3AF}', label: 'Arch Linux', desc: 'Rolling release, build exactly what you want.' },
  { id: 'alpine', icon: '\u26F0', label: 'Alpine Linux', desc: 'Tiny (~50 MB), musl-based, great for containers.' },
]

const baseInfo = computed(() => options.value?.bases?.[selectedBase.value] || {})

const suites = computed(() => baseInfo.value.suites || [])
const architectures = computed(() => baseInfo.value.arch || ['amd64'])

onMounted(async () => {
  const { ok, data } = await get('/api/os-builder/options')
  if (ok) {
    options.value = data
    updateDefaults()
  }
})

function updateDefaults() {
  const info = options.value?.bases?.[selectedBase.value]
  if (info) {
    form.value.suite = info.default_suite || ''
    if (info.arch?.length) form.value.arch = info.arch[0]
  }
}

function selectBase(id) {
  selectedBase.value = id
  updateDefaults()
  estimateSize()
}

function collectProfile() {
  return {
    ...form.value,
    base: selectedBase.value,
    ssh_keys: form.value.ssh_keys.split('\n').filter(k => k.trim()),
    extra_packages: form.value.extra_packages.split(/\s+/).filter(Boolean),
    dns: form.value.dns.split(',').map(d => d.trim()).filter(Boolean),
  }
}

async function estimateSize() {
  const { ok, data } = await post('/api/os-builder/estimate', collectProfile())
  if (ok) {
    sizeEstimate.value = data
    if (data.recommended_image_mb > form.value.image_size_mb) {
      form.value.image_size_mb = data.recommended_image_mb
    }
  }
}

async function startBuild() {
  const profile = collectProfile()
  profile.ipfs_publish = form.value.ipfs_publish
  const { ok, data } = await post('/api/os-builder/build', profile)
  if (ok && data.task_id) {
    taskId.value = data.task_id
  } else {
    alert(data?.error || 'Failed to start build')
  }
}

async function previewConfig() {
  const { ok, data } = await post('/api/os-builder/preview', collectProfile())
  if (ok) {
    previewData.value = data
  } else {
    alert(data?.error || 'Failed to generate preview')
  }
}

async function saveProfile() {
  const { ok, data } = await post('/api/os-builder/profiles', collectProfile())
  if (ok) {
    alert(`Profile saved: ${data.path}`)
  } else {
    alert(data?.error || 'Failed to save profile')
  }
}

async function loadProfile() {
  const { ok, data } = await get('/api/os-builder/profiles')
  if (!ok || !data.length) {
    alert('No saved profiles found.')
    return
  }
  const names = data.map(p => p.name)
  const choice = prompt('Available profiles:\n' + names.map((n, i) => `${i + 1}. ${n}`).join('\n') + '\n\nEnter profile name:')
  if (!choice) return

  const { ok: ok2, data: profile } = await get(`/api/os-builder/profiles/${encodeURIComponent(choice)}`)
  if (ok2) applyProfile(profile)
  else alert(profile?.error || 'Failed to load profile')
}

function applyProfile(p) {
  selectedBase.value = p.base || 'debian'
  form.value = {
    name: p.name || 'my-os',
    suite: p.suite || '',
    arch: p.arch || 'amd64',
    target_device: p.target_device || 'generic-x86_64',
    output_format: p.output_format || 'img',
    image_size_mb: p.image_size_mb || 4096,
    hostname: p.hostname || 'osmosis',
    locale: p.locale || 'en_US.UTF-8',
    timezone: p.timezone || 'UTC',
    keyboard_layout: p.keyboard_layout || 'us',
    username: p.username || 'user',
    password: p.password || '',
    ssh_keys: (p.ssh_keys || []).join('\n'),
    extra_packages: (p.extra_packages || []).join(' '),
    desktop: p.desktop || 'none',
    network: p.network || 'dhcp',
    static_ip: p.static_ip || '',
    gateway: p.gateway || '',
    dns: (p.dns || []).join(', '),
    firewall: p.firewall || 'none',
    disk_layout: p.disk_layout || 'auto',
    post_install_script: p.post_install_script || '',
    ipfs_publish: false,
  }
  estimateSize()
}

function onBuildDone(status) {
  taskId.value = null
  if (status === 'done') buildComplete.value = true
}

function writeToUsb() {
  // Navigate to bootable step — the built image path can be entered there
  router.push('/wizard/bootable')
}

// Debounced estimate on desktop/package change
watch(() => [form.value.desktop, form.value.extra_packages], estimateSize, { debounce: 500 })
</script>

<template>
  <h2 class="step-title">Build your own operating system</h2>
  <p class="step-desc">Choose a base distribution, configure it to your needs, and build a ready-to-flash image.</p>

  <!-- Base distro selection -->
  <h3 class="form-section-title">Base distribution</h3>
  <div class="goal-grid">
    <div
      v-for="base in bases"
      :key="base.id"
      class="goal-card"
      :class="{ active: selectedBase === base.id }"
      role="button"
      tabindex="0"
      @click="selectBase(base.id)"
      @keydown.enter="selectBase(base.id)"
      @keydown.space.prevent="selectBase(base.id)"
    >
      <div class="goal-icon">{{ base.icon }}</div>
      <h3>{{ base.label }}</h3>
      <p>{{ base.desc }}</p>
    </div>
  </div>

  <!-- System configuration -->
  <template v-if="options">
    <h3 class="form-section-title">System configuration</h3>

    <div class="form-row">
      <div class="form-group">
        <label for="os-name">Build name</label>
        <input id="os-name" v-model="form.name" type="text" placeholder="my-os">
      </div>
      <div class="form-group">
        <label for="os-suite">Release / Suite</label>
        <select id="os-suite" v-model="form.suite">
          <option v-if="!suites.length" value="">Rolling release</option>
          <option v-for="s in suites" :key="s" :value="s">{{ s }}</option>
        </select>
      </div>
    </div>

    <div class="form-row">
      <div class="form-group">
        <label for="os-arch">Architecture</label>
        <select id="os-arch" v-model="form.arch">
          <option v-for="a in architectures" :key="a" :value="a">{{ a }}</option>
        </select>
      </div>
      <div class="form-group">
        <label for="os-target">Target device</label>
        <select id="os-target" v-model="form.target_device">
          <option v-for="d in options.target_devices" :key="d.id" :value="d.id">{{ d.label }}</option>
        </select>
      </div>
    </div>

    <div class="form-row">
      <div class="form-group">
        <label for="os-hostname">Hostname</label>
        <input id="os-hostname" v-model="form.hostname" type="text">
      </div>
      <div class="form-group">
        <label for="os-username">Username</label>
        <input id="os-username" v-model="form.username" type="text">
      </div>
    </div>

    <div class="form-row">
      <div class="form-group">
        <label for="os-password">Password (leave empty for key-only auth)</label>
        <input id="os-password" v-model="form.password" type="password">
      </div>
      <div class="form-group">
        <label for="os-locale">Locale</label>
        <input id="os-locale" v-model="form.locale" type="text">
      </div>
    </div>

    <div class="form-row">
      <div class="form-group">
        <label for="os-timezone">Timezone</label>
        <input id="os-timezone" v-model="form.timezone" type="text" placeholder="Europe/Paris">
      </div>
      <div class="form-group">
        <label for="os-keyboard">Keyboard layout</label>
        <input id="os-keyboard" v-model="form.keyboard_layout" type="text">
      </div>
    </div>

    <!-- Desktop & packages -->
    <h3 class="form-section-title">Desktop &amp; packages</h3>

    <div class="form-row">
      <div class="form-group">
        <label for="os-desktop">Desktop environment</label>
        <select id="os-desktop" v-model="form.desktop" @change="estimateSize">
          <option v-for="d in options.desktops" :key="d.id" :value="d.id">{{ d.label }}</option>
        </select>
      </div>
      <div class="form-group">
        <label for="os-output">Output format</label>
        <select id="os-output" v-model="form.output_format">
          <option v-for="f in options.output_formats" :key="f.id" :value="f.id">
            {{ f.label }} &mdash; {{ f.desc }}
          </option>
        </select>
      </div>
    </div>

    <div class="form-group">
      <label for="os-packages">Extra packages (space-separated)</label>
      <input id="os-packages" v-model="form.extra_packages" type="text" placeholder="vim curl git htop">
    </div>

    <!-- Networking -->
    <h3 class="form-section-title">Networking</h3>

    <div class="form-row">
      <div class="form-group">
        <label for="os-network">Network mode</label>
        <select id="os-network" v-model="form.network">
          <option value="dhcp">DHCP (automatic)</option>
          <option value="static">Static IP</option>
        </select>
      </div>
      <div v-if="form.network === 'static'" class="form-group">
        <label for="os-static-ip">Static IP (CIDR)</label>
        <input id="os-static-ip" v-model="form.static_ip" type="text" placeholder="192.168.1.100/24">
      </div>
    </div>

    <div v-if="form.network === 'static'" class="form-row">
      <div class="form-group">
        <label for="os-gateway">Gateway</label>
        <input id="os-gateway" v-model="form.gateway" type="text" placeholder="192.168.1.1">
      </div>
      <div class="form-group">
        <label for="os-dns">DNS servers (comma-separated)</label>
        <input id="os-dns" v-model="form.dns" type="text">
      </div>
    </div>

    <!-- Security -->
    <h3 class="form-section-title">Security</h3>

    <div class="form-row">
      <div class="form-group">
        <label for="os-firewall">Firewall</label>
        <select id="os-firewall" v-model="form.firewall">
          <option value="none">None</option>
          <option value="ufw">UFW (simple)</option>
          <option value="nftables">nftables (advanced)</option>
        </select>
      </div>
      <div class="form-group">
        <label for="os-ssh-keys">SSH public keys (one per line)</label>
        <textarea id="os-ssh-keys" v-model="form.ssh_keys" rows="2" placeholder="ssh-ed25519 AAAA..." />
      </div>
    </div>

    <!-- Disk & output -->
    <h3 class="form-section-title">Disk &amp; output</h3>

    <div class="form-row">
      <div class="form-group">
        <label for="os-disk-layout">Disk layout</label>
        <select id="os-disk-layout" v-model="form.disk_layout">
          <option value="auto">Automatic (single partition)</option>
          <option value="lvm">LVM (flexible volumes)</option>
          <option value="luks">LUKS encrypted</option>
        </select>
      </div>
      <div class="form-group">
        <label for="os-image-size">Image size (MB)</label>
        <input id="os-image-size" v-model.number="form.image_size_mb" type="number" min="1024" step="512">
      </div>
    </div>

    <!-- Post-install script -->
    <h3 class="form-section-title">Post-install script (optional)</h3>
    <div class="form-group">
      <textarea id="os-post-install" v-model="form.post_install_script" rows="4" placeholder="#!/bin/bash&#10;# Commands to run after the base system is configured..." />
    </div>

    <!-- Size estimate -->
    <div v-if="sizeEstimate" class="info-box">
      <div class="info-icon">&#x1F4CA;</div>
      <div>
        <strong>Estimated size:</strong> ~{{ sizeEstimate.total_mb }} MB
        (base: {{ sizeEstimate.base_mb }} MB, desktop: {{ sizeEstimate.desktop_mb }} MB, packages: {{ sizeEstimate.packages_mb }} MB)<br>
        <strong>Recommended image size:</strong> {{ sizeEstimate.recommended_image_mb }} MB
      </div>
    </div>

    <!-- IPFS toggle -->
    <div class="form-group" style="margin-top: 0.75rem;">
      <label class="checklist-item">
        <input v-model="form.ipfs_publish" type="checkbox">
        <span class="check-label">Publish to IPFS after build</span>
        <span class="check-detail">Pin the output image for decentralized sharing</span>
      </label>
    </div>
  </template>

  <!-- Actions -->
  <div class="step-actions" style="margin-top: 0.75rem; display: flex; gap: 0.5rem; flex-wrap: wrap;">
    <button class="btn btn-large btn-primary" :disabled="!!taskId" @click="startBuild">
      <span class="btn-icon">&#x1F3D7;</span>
      <span>Start build</span>
    </button>
    <button class="btn btn-secondary" @click="previewConfig">
      <span class="btn-icon">&#x1F4C4;</span>
      <span>Preview config</span>
    </button>
    <button class="btn btn-secondary" @click="saveProfile">
      <span class="btn-icon">&#x1F4BE;</span>
      <span>Save profile</span>
    </button>
    <button class="btn btn-secondary" @click="loadProfile">
      <span class="btn-icon">&#x1F4C2;</span>
      <span>Load profile</span>
    </button>
  </div>

  <!-- Config preview -->
  <div v-if="previewData" style="margin-top: 0.75rem;">
    <div class="form-group">
      <label>Generated {{ previewData.type }}: {{ previewData.filename }}</label>
      <pre class="terminal" style="white-space: pre-wrap; max-height: 300px; overflow-y: auto;">{{ previewData.content }}</pre>
    </div>
  </div>

  <!-- Build terminal -->
  <TerminalOutput :task-id="taskId" @done="onBuildDone" />

  <!-- Post-build actions -->
  <div v-if="buildComplete" class="info-box" style="margin-top: 0.75rem;">
    <div class="info-icon">&#x2705;</div>
    <div>
      <strong>Build complete!</strong><br>
      Your image is ready at <code>~/Osmosis-downloads/os-builds/</code>
      <div style="margin-top: 0.5rem; display: flex; gap: 0.5rem; flex-wrap: wrap;">
        <button class="btn btn-primary" @click="writeToUsb">
          <span class="btn-icon">&#x1F4BF;</span>
          Write to USB / SD card
        </button>
        <button class="btn btn-secondary" @click="buildComplete = false">
          Dismiss
        </button>
      </div>
    </div>
  </div>

  <div class="step-nav">
    <button class="btn btn-secondary" @click="router.push('/wizard/category')">&larr; Back</button>
  </div>
</template>
