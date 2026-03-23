<script setup>
/**
 * GlossaryTip — wraps a technical term with an inline tooltip explanation.
 * Usage: <GlossaryTip term="ADB" /> or <GlossaryTip term="ROM">custom label</GlossaryTip>
 */
import { ref } from 'vue'

const props = defineProps({
  term: { type: String, required: true },
})

const open = ref(false)
const tipRef = ref(null)

const glossary = {
  ADB: 'Android Debug Bridge — a tool that lets your computer talk to an Android device over USB.',
  sideload: 'A way to send a software file from your computer directly to a device, without using the app store.',
  ROM: 'The operating system software that runs on your device (like Android or a custom version of it).',
  TWRP: 'Team Win Recovery Project — a special tool installed on your device that helps install new software.',
  recovery: 'A special startup mode on your device used to install updates or fix problems.',
  'Recovery Mode': 'A special startup mode on your device used to install updates or fix problems.',
  'Download Mode': 'A special mode (mostly Samsung) where the device waits for your computer to send it new software.',
  fastboot: 'A protocol that lets your computer install low-level software on a device while it is in bootloader mode.',
  bootloader: 'The very first program that runs when your device powers on — it decides what software to start.',
  flash: 'To write new software onto a device, replacing what was there before.',
  'Flash Stock': 'Install the original factory software back onto your device.',
  'Flash Recovery': 'Install a special recovery tool onto your device so you can load new software.',
  'ADB Sideload': 'Send a software file from your computer to your device over USB using a built-in Android tool.',
  'Pre-Flight': 'A checklist of things to verify before you start — like charging your battery and backing up data.',
  codename: 'A short internal nickname manufacturers give each device model (e.g. "hammerhead" for Nexus 5).',
  UF2: 'A simple file format used to install firmware on small boards like Raspberry Pi Pico — just drag and drop.',
  BOOTSEL: 'A physical button on some boards (like Pi Pico) you hold while plugging in to enter programming mode.',
  GApps: 'Google Apps — the package that adds the Play Store, Gmail, Maps, etc. to a custom Android install.',
  OEM: 'Original Equipment Manufacturer — the company that made your device.',
  'OEM unlock': 'A setting that allows your device\'s bootloader to be unlocked, so you can install custom software.',
  partition: 'A section of your device\'s storage reserved for a specific purpose (system, data, recovery, etc.).',
  kernel: 'The core part of the operating system that controls hardware and manages resources.',
  brick: 'When a device stops working and won\'t turn on — usually caused by a failed software update.',
  Heimdall: 'A free tool that sends firmware to Samsung devices while they\'re in Download Mode.',
  IPFS: 'InterPlanetary File System — a way to share files across many computers so downloads are more reliable.',
  'stock firmware': 'The original software that came pre-installed on your device from the manufacturer.',
  'custom ROM': 'A community-built version of Android (or another OS) that replaces the stock software.',
  'wipe': 'Erasing all user data on the device — like doing a factory reset. Usually required when installing a new ROM.',
  'root': 'Full administrator access to your device, letting you modify system files and run privileged apps.',
  'Magisk': 'A popular tool for rooting Android devices while keeping safety checks (SafetyNet) working.',
  'LineageOS': 'A free, community-built Android distribution — the most popular custom ROM, supporting hundreds of devices.',
  '/e/OS': 'A privacy-focused Android distribution that replaces Google services with open-source alternatives.',
  'Replicant': 'A fully free/libre Android distribution that avoids all proprietary software.',
  'postmarketOS': 'A Linux distribution for phones and tablets, aiming for long-term device support.',
  'CalyxOS': 'A privacy and security-focused Android OS, available for Google Pixel devices.',
  'GrapheneOS': 'A hardened, security-focused Android OS for Pixel devices with strong privacy protections.',
  'data cable': 'A USB cable that can transfer data, not just charge — some cheap cables are charge-only and won\'t work.',
  'USB hub': 'A device that splits one USB port into several. Hubs can cause connection issues during flashing.',
  'SELinux': 'Security-Enhanced Linux — a security system built into Android that controls what apps and processes can do.',
  'OTA': 'Over-The-Air update — a software update delivered wirelessly, rather than through a cable.',
}

const explanation = glossary[props.term] || null

function toggle() {
  open.value = !open.value
}

function close() {
  open.value = false
}
</script>

<template>
  <span class="glossary-tip" ref="tipRef" @mouseleave="close">
    <button
      class="glossary-term"
      @click.stop="toggle"
      @focus="open = true"
      @blur="close"
      :aria-expanded="open"
      :aria-label="term + (explanation ? ': ' + explanation : '')"
    >
      <slot>{{ term }}</slot><span class="glossary-icon" aria-hidden="true">?</span>
    </button>
    <span
      v-if="open && explanation"
      class="glossary-popup"
      role="tooltip"
    >
      {{ explanation }}
    </span>
  </span>
</template>
