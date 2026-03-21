<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import TerminalOutput from '@/components/shared/TerminalOutput.vue'

const { t } = useI18n()
const router = useRouter()
const { get, post } = useApi()

// Steps: 0=base, 1=system, 2=desktop, 3=network, 4=security, 5=disk, 6=review, 7=building
const step = ref(0)
const steps = [
  { key: 'base',     icon: '\u{1F4E6}', label: 'Base' },
  { key: 'system',   icon: '\u2699',    label: 'System' },
  { key: 'desktop',  icon: '\u{1F5A5}', label: 'Desktop' },
  { key: 'network',  icon: '\u{1F310}', label: 'Network' },
  { key: 'security', icon: '\u{1F512}', label: 'Security' },
  { key: 'disk',     icon: '\u{1F4BE}', label: 'Disk' },
  { key: 'review',   icon: '\u{1F3D7}', label: 'Build' },
]

const options = ref(null)
const selectedBase = ref(null)
const taskId = ref(null)
const previewData = ref(null)
const sizeEstimate = ref(null)
const buildComplete = ref(false)

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
  { id: 'fedora', icon: '\u{1F3A9}', label: 'Fedora', desc: 'Cutting-edge packages, strong SELinux, RPM-based.' },
  { id: 'nixos', icon: '\u2744', label: 'NixOS', desc: 'Declarative, reproducible, rollback-friendly.' },
]

const baseInfo = computed(() => options.value?.bases?.[selectedBase.value] || {})
const suites = computed(() => baseInfo.value.suites || [])
const architectures = computed(() => baseInfo.value.arch || ['amd64'])
const selectedBaseInfo = computed(() => bases.find(b => b.id === selectedBase.value))
const canContinue = computed(() => step.value === 0 ? !!selectedBase.value : true)

onMounted(async () => {
  const { ok, data } = await get('/api/os-builder/options')
  if (ok) options.value = data
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
}

function goNext() {
  if (step.value < steps.length - 1) {
    step.value++
    scrollTop()
  }
}

function goBack() {
  if (step.value > 0) {
    step.value--
    scrollTop()
  } else {
    router.push('/wizard/category')
  }
}

function goToStep(i) {
  if (i === 0 || selectedBase.value) {
    step.value = i
    scrollTop()
  }
}

function scrollTop() {
  nextTick(() => {
    document.querySelector('.osb-step-content')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  })
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
    step.value = steps.length // building phase
  } else {
    alert(data?.error || 'Failed to start build')
  }
}

async function previewConfig() {
  const { ok, data } = await post('/api/os-builder/preview', collectProfile())
  if (ok) previewData.value = data
  else alert(data?.error || 'Failed to generate preview')
}

async function saveProfile() {
  const { ok, data } = await post('/api/os-builder/profiles', collectProfile())
  if (ok) alert(`Profile saved: ${data.path}`)
  else alert(data?.error || 'Failed to save profile')
}

async function loadProfile() {
  const { ok, data } = await get('/api/os-builder/profiles')
  if (!ok || !data.length) { alert('No saved profiles found.'); return }
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
    name: p.name || 'my-os', suite: p.suite || '', arch: p.arch || 'amd64',
    target_device: p.target_device || 'generic-x86_64', output_format: p.output_format || 'img',
    image_size_mb: p.image_size_mb || 4096, hostname: p.hostname || 'osmosis',
    locale: p.locale || 'en_US.UTF-8', timezone: p.timezone || 'UTC',
    keyboard_layout: p.keyboard_layout || 'us', username: p.username || 'user',
    password: p.password || '', ssh_keys: (p.ssh_keys || []).join('\n'),
    extra_packages: (p.extra_packages || []).join(' '), desktop: p.desktop || 'none',
    network: p.network || 'dhcp', static_ip: p.static_ip || '', gateway: p.gateway || '',
    dns: (p.dns || []).join(', '), firewall: p.firewall || 'none',
    disk_layout: p.disk_layout || 'auto', post_install_script: p.post_install_script || '',
    ipfs_publish: false,
  }
  step.value = 6 // go to review
}

function onBuildDone(status) {
  taskId.value = null
  if (status === 'done') buildComplete.value = true
}

function writeToUsb() { router.push('/wizard/bootable') }

watch(() => [form.value.desktop, form.value.extra_packages], estimateSize, { debounce: 500 })
</script>

<template>
  <h2 class="step-title">Build your own OS</h2>

  <!-- Step indicator -->
  <div v-if="step < steps.length" class="osb-progress">
    <button
      v-for="(s, i) in steps"
      :key="s.key"
      class="osb-progress-step"
      :class="{ active: i === step, done: i < step, disabled: i > 0 && !selectedBase }"
      @click="goToStep(i)"
    >
      <span class="osb-progress-dot">{{ i < step ? '\u2713' : i + 1 }}</span>
      <span class="osb-progress-label">{{ s.label }}</span>
    </button>
  </div>

  <div class="osb-step-content">
    <!-- ===== Step 0: Pick base ===== -->
    <template v-if="step === 0">
      <p class="step-desc">Pick the Linux distribution to build from.</p>
      <div class="goal-grid">
        <div
          v-for="base in bases" :key="base.id"
          class="goal-card" :class="{ active: selectedBase === base.id }"
          role="button" tabindex="0"
          @click="selectBase(base.id)"
          @keydown.enter="selectBase(base.id)"
          @keydown.space.prevent="selectBase(base.id)"
        >
          <div class="goal-icon">{{ base.icon }}</div>
          <h3>{{ base.label }}</h3>
          <p>{{ base.desc }}</p>
        </div>
      </div>
    </template>

    <!-- ===== Step 1: System ===== -->
    <template v-if="step === 1 && options">
      <p class="step-desc">Set up the basics: name, release, architecture, and login credentials.</p>
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
          <label for="os-password">Password (leave empty for key-only)</label>
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
    </template>

    <!-- ===== Step 2: Desktop & packages ===== -->
    <template v-if="step === 2 && options">
      <p class="step-desc">Choose a desktop environment and add any extra packages.</p>
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
    </template>

    <!-- ===== Step 3: Networking ===== -->
    <template v-if="step === 3">
      <p class="step-desc">Configure how your OS connects to the network.</p>
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
    </template>

    <!-- ===== Step 4: Security ===== -->
    <template v-if="step === 4">
      <p class="step-desc">Set up firewall and SSH access.</p>
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
          <label for="os-disk-layout">Disk layout</label>
          <select id="os-disk-layout" v-model="form.disk_layout">
            <option value="auto">Automatic (single partition)</option>
            <option value="lvm">LVM (flexible volumes)</option>
            <option value="luks">LUKS encrypted</option>
          </select>
        </div>
      </div>
      <div class="form-group">
        <label for="os-ssh-keys">SSH public keys (one per line)</label>
        <textarea id="os-ssh-keys" v-model="form.ssh_keys" rows="3" placeholder="ssh-ed25519 AAAA..." />
      </div>
    </template>

    <!-- ===== Step 5: Disk & extras ===== -->
    <template v-if="step === 5">
      <p class="step-desc">Configure disk size and optional post-install script.</p>
      <div class="form-row">
        <div class="form-group">
          <label for="os-image-size">Image size (MB)</label>
          <input id="os-image-size" v-model.number="form.image_size_mb" type="number" min="1024" step="512">
        </div>
        <div class="form-group">
          <label>&nbsp;</label>
          <label class="checklist-item">
            <input v-model="form.ipfs_publish" type="checkbox">
            <span class="check-label">Publish to IPFS</span>
          </label>
        </div>
      </div>
      <div class="form-group">
        <label for="os-post-install">Post-install script (optional)</label>
        <textarea id="os-post-install" v-model="form.post_install_script" rows="5" placeholder="#!/bin/bash&#10;# Commands to run after the base system is configured..." />
      </div>
    </template>

    <!-- ===== Step 6: Review & Build ===== -->
    <template v-if="step === 6">
      <p class="step-desc">Review your configuration and start the build.</p>

      <div class="osb-review">
        <div class="osb-review-row">
          <span class="osb-review-label">Base</span>
          <span>{{ selectedBaseInfo?.icon }} {{ selectedBaseInfo?.label }}</span>
        </div>
        <div class="osb-review-row">
          <span class="osb-review-label">Name</span>
          <span>{{ form.name }}</span>
        </div>
        <div class="osb-review-row">
          <span class="osb-review-label">Arch / Suite</span>
          <span>{{ form.arch }} / {{ form.suite || 'rolling' }}</span>
        </div>
        <div class="osb-review-row">
          <span class="osb-review-label">Target</span>
          <span>{{ form.target_device }}</span>
        </div>
        <div class="osb-review-row">
          <span class="osb-review-label">Desktop</span>
          <span>{{ form.desktop === 'none' ? 'None (headless)' : form.desktop }}</span>
        </div>
        <div class="osb-review-row">
          <span class="osb-review-label">Network</span>
          <span>{{ form.network === 'dhcp' ? 'DHCP' : form.static_ip }}</span>
        </div>
        <div class="osb-review-row">
          <span class="osb-review-label">Firewall</span>
          <span>{{ form.firewall }}</span>
        </div>
        <div class="osb-review-row">
          <span class="osb-review-label">Disk</span>
          <span>{{ form.disk_layout }} &middot; {{ form.image_size_mb }} MB</span>
        </div>
        <div class="osb-review-row">
          <span class="osb-review-label">User</span>
          <span>{{ form.username }}@{{ form.hostname }}</span>
        </div>
        <div v-if="form.extra_packages" class="osb-review-row">
          <span class="osb-review-label">Packages</span>
          <span>{{ form.extra_packages }}</span>
        </div>
      </div>

      <div v-if="sizeEstimate" class="info-box">
        <div class="info-icon">&#x1F4CA;</div>
        <div>
          <strong>Estimated size:</strong> ~{{ sizeEstimate.total_mb }} MB
          (base: {{ sizeEstimate.base_mb }}, desktop: {{ sizeEstimate.desktop_mb }}, packages: {{ sizeEstimate.packages_mb }} MB)
        </div>
      </div>

      <div class="osb-build-actions">
        <button class="btn btn-large btn-primary" :disabled="!!taskId" @click="startBuild">
          <span class="btn-icon">&#x1F3D7;</span>
          Start build
        </button>
        <button class="btn btn-secondary" @click="previewConfig">Preview config</button>
        <button class="btn btn-secondary" @click="saveProfile">Save profile</button>
      </div>

      <div v-if="previewData" class="config-preview">
        <label>Generated {{ previewData.type }}: {{ previewData.filename }}</label>
        <pre class="terminal active">{{ previewData.content }}</pre>
      </div>
    </template>

    <!-- ===== Building phase ===== -->
    <template v-if="step >= steps.length">
      <div class="selected-base-banner">
        <span class="selected-base-icon">{{ selectedBaseInfo?.icon }}</span>
        <div class="selected-base-info">
          <strong>Building {{ form.name }}</strong>
          <span class="text-dim">{{ selectedBaseInfo?.label }} &middot; {{ form.arch }} &middot; {{ form.suite || 'rolling' }}</span>
        </div>
      </div>

      <TerminalOutput :task-id="taskId" @done="onBuildDone" />

      <div v-if="buildComplete" class="build-complete-box">
        <div class="build-complete-icon">&#x2705;</div>
        <h3>Build complete!</h3>
        <p class="text-dim">Your image is ready at <code>~/Osmosis-downloads/os-builds/</code></p>
        <div class="build-complete-actions">
          <button class="btn btn-large btn-primary" @click="writeToUsb">
            <span class="btn-icon">&#x1F4BF;</span>
            Write to USB / SD card
          </button>
          <button class="btn btn-secondary" @click="step = 0; buildComplete = false">
            Build another
          </button>
        </div>
      </div>
    </template>
  </div>

  <!-- Navigation -->
  <div v-if="step < steps.length" class="osb-nav">
    <button class="btn btn-secondary" @click="goBack">
      &larr; {{ step === 0 ? 'Back' : steps[step - 1].label }}
    </button>
    <span class="osb-nav-skip" v-if="step > 0 && step < 6" @click="step = 6; estimateSize()">
      Skip to build &rarr;
    </span>
    <button
      class="btn btn-primary"
      :disabled="!canContinue"
      @click="step === 6 ? startBuild() : goNext(); step === 5 && estimateSize()"
    >
      {{ step === 6 ? 'Start build' : step === 0 ? 'Continue' : 'Next' }} &rarr;
    </button>
  </div>
  <div v-else class="osb-nav">
    <button class="btn btn-secondary" @click="router.push('/wizard/category')">&larr; Back to start</button>
  </div>
</template>

<style scoped>
/* Step progress indicator */
.osb-progress {
  display: flex;
  justify-content: center;
  gap: 0;
  margin-bottom: 1.25rem;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
  padding: 0 0.25rem;
}
.osb-progress::-webkit-scrollbar { display: none; }
.osb-progress-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.3rem;
  padding: 0.5rem 0.4rem;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-dim);
  transition: color var(--transition-fast);
  min-width: 0;
  flex: 1;
  max-width: 80px;
}
.osb-progress-step.disabled { pointer-events: none; opacity: 0.4; }
.osb-progress-step.active { color: var(--accent); }
.osb-progress-step.done { color: var(--green); }
.osb-progress-dot {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 2px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8rem;
  font-weight: 700;
  transition: all var(--transition-fast);
  flex-shrink: 0;
}
.osb-progress-step.active .osb-progress-dot {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
  transform: scale(1.1);
}
.osb-progress-step.done .osb-progress-dot {
  background: var(--green);
  border-color: var(--green);
  color: #fff;
}
.osb-progress-label {
  font-size: calc(0.7rem * var(--font-scale));
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}
@media (min-width: 600px) {
  .osb-progress-step { padding: 0.5rem 0.6rem; max-width: 100px; }
  .osb-progress-dot { width: 36px; height: 36px; font-size: 0.9rem; }
  .osb-progress-label { font-size: calc(0.8rem * var(--font-scale)); }
}

/* Step content */
.osb-step-content {
  animation: fadeIn 0.2s ease;
  min-height: 200px;
}

/* Navigation bar */
.osb-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-top: auto;
  padding-top: 0.75rem;
  border-top: 1px solid var(--border);
  flex-shrink: 0;
}
.osb-nav-skip {
  color: var(--accent);
  font-size: calc(0.85rem * var(--font-scale));
  cursor: pointer;
  white-space: nowrap;
  padding: 0.5rem;
  min-height: 44px;
  display: flex;
  align-items: center;
}
.osb-nav-skip:hover { text-decoration: underline; }

/* Review table */
.osb-review {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
  overflow: hidden;
  margin-bottom: 1rem;
}
.osb-review-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.7rem 1rem;
  border-bottom: 1px solid var(--border);
  gap: 1rem;
  font-size: calc(0.95rem * var(--font-scale));
}
.osb-review-row:last-child { border-bottom: none; }
.osb-review-label {
  color: var(--text-dim);
  font-weight: 500;
  white-space: nowrap;
  flex-shrink: 0;
}
@media (min-width: 600px) {
  .osb-review-row { padding: 0.85rem 1.25rem; }
}
@media (pointer: coarse) {
  .osb-review-row { padding: 1rem 1.25rem; min-height: 52px; }
}

/* Build actions */
.osb-build-actions {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin: 1rem 0;
  align-items: stretch;
}
@media (min-width: 600px) {
  .osb-build-actions {
    flex-direction: row;
    align-items: center;
    flex-wrap: wrap;
  }
}

/* Selected base banner (building phase) */
.selected-base-banner {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem 1.25rem;
  background: var(--bg-card);
  border: 1px solid var(--accent);
  border-radius: var(--radius-card);
  margin-bottom: 1rem;
  min-height: 56px;
}
.selected-base-icon { font-size: 2rem; flex-shrink: 0; }
.selected-base-info {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  flex: 1;
  min-width: 0;
}
.selected-base-info strong { font-size: calc(1.1rem * var(--font-scale)); }

/* Config preview */
.config-preview { margin-top: 0.75rem; }
.config-preview .terminal {
  white-space: pre-wrap;
  max-height: 300px;
  overflow-y: auto;
  display: block;
}

/* Build complete */
.build-complete-box {
  text-align: center;
  padding: 2rem 1rem;
  margin-top: 1rem;
  background: var(--bg-card);
  border: 1px solid var(--green);
  border-radius: var(--radius-card);
  animation: fadeIn 0.3s ease;
}
.build-complete-icon { font-size: 3rem; margin-bottom: 0.5rem; }
.build-complete-box h3 { font-size: calc(1.3rem * var(--font-scale)); margin-bottom: 0.25rem; }
.build-complete-box p { margin-bottom: 1rem; }
.build-complete-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: center;
  flex-wrap: wrap;
}
</style>
