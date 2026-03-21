<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
const { t } = useI18n()

const openSection = ref(null)
function toggle(id) {
  openSection.value = openSection.value === id ? null : id
}

const sections = [
  {
    id: 'bootloader',
    title: 'What is a bootloader?',
    content: `The bootloader is the first piece of software that runs when you turn on your device. It decides which operating system to load. Most manufacturers <strong>lock</strong> the bootloader so you can only run their official software. Unlocking it lets you install custom ROMs and recoveries. <em>Warning:</em> unlocking the bootloader usually wipes all data on the device.`
  },
  {
    id: 'rom',
    title: 'What is a ROM?',
    content: `A ROM (Read-Only Memory image) is essentially the operating system installed on your device. A <strong>stock ROM</strong> is the one that came with your device from the manufacturer. A <strong>custom ROM</strong> is an alternative OS built by the community &mdash; like LineageOS, /e/OS, or GrapheneOS. Custom ROMs can extend the life of your device, improve privacy, and remove bloatware.`
  },
  {
    id: 'recovery',
    title: 'What is a custom recovery?',
    content: `Recovery mode is a special boot environment separate from your main OS. The stock recovery is limited, but a <strong>custom recovery</strong> like TWRP gives you powerful features: installing custom ROMs, making full backups (called NANDroid backups), wiping partitions, and more. Think of it as a toolkit that runs before your phone boots up.`
  },
  {
    id: 'root',
    title: 'What is root access?',
    content: `Root access gives you full administrator control over your device &mdash; similar to "admin" on a computer. By default, Android restricts what apps and users can do. With root (via tools like <strong>Magisk</strong>), you can remove system apps, use powerful automation tools, install advanced firewalls, and customize things that are normally locked down. Root can be done "systemless" so it doesn't modify the system partition.`
  },
  {
    id: 'adb',
    title: 'What is ADB?',
    content: `ADB (Android Debug Bridge) is a command-line tool that lets your computer communicate with an Android device over USB. It's used to install apps, copy files, take screenshots, run shell commands, and &mdash; most importantly for OSmosis &mdash; sideload ROMs and firmware. You need to enable <strong>USB Debugging</strong> in your device's Developer Options to use it.`
  },
  {
    id: 'brick',
    title: 'What does "bricked" mean?',
    content: `A "bricked" device is one that won't boot or function properly &mdash; it's about as useful as a brick. A <strong>soft brick</strong> means the device is stuck in a boot loop or won't start the OS, but can usually be fixed by reflashing firmware. A <strong>hard brick</strong> means the device won't turn on at all, which is much harder to recover from. OSmosis includes safety checks and recovery tools to help prevent and fix bricking.`
  },
  {
    id: 'partition',
    title: 'What are partitions?',
    content: `Your device's storage is divided into partitions, each with a specific purpose: <strong>boot</strong> (kernel and startup), <strong>system</strong> (the OS), <strong>data</strong> (your apps and files), <strong>recovery</strong> (recovery environment), and <strong>EFS</strong> (device identity like IMEI). When flashing firmware, you're writing new data to specific partitions. That's why backing up critical partitions like EFS is so important before making changes.`
  },
  {
    id: 'sideload',
    title: 'What is sideloading?',
    content: `Sideloading means installing software on your device from a source other than the official app store &mdash; typically by pushing a file over USB. In the context of OSmosis, <strong>ADB sideload</strong> is used to install custom ROMs: you boot into recovery, enable sideload mode, and then push the ROM ZIP from your computer to the device.`
  },
  {
    id: 'safety',
    title: 'Safety tips',
    content: `<ul>
      <li><strong>Always back up</strong> before flashing anything &mdash; especially EFS/IMEI data.</li>
      <li><strong>Keep your device charged</strong> to at least 50% before starting.</li>
      <li><strong>Use a good USB cable</strong> &mdash; cheap or damaged cables can cause failed flashes.</li>
      <li><strong>Don't unplug</strong> during a flash operation &mdash; this is the #1 cause of soft bricks.</li>
      <li><strong>Download from official sources</strong> &mdash; verify ROM checksums when possible.</li>
      <li><strong>Read the instructions</strong> for your specific device &mdash; not all devices work the same way.</li>
    </ul>`
  }
]
</script>

<template>
  <main class="page-container" role="main">
    <h1>{{ t('nav.wiki', 'Wiki') }}</h1>
    <p class="page-lead">
      Everything you need to know about flashing, rooting, and taking control of your devices.
      Click on a topic to learn more.
    </p>

    <div class="wiki-sections">
      <div
        v-for="section in sections"
        :key="section.id"
        class="wiki-entry"
      >
        <button
          class="wiki-entry-header"
          :aria-expanded="openSection === section.id"
          @click="toggle(section.id)"
        >
          <span>{{ section.title }}</span>
          <span class="wiki-chevron" :class="{ open: openSection === section.id }">&#9660;</span>
        </button>
        <div
          v-if="openSection === section.id"
          class="wiki-entry-body"
          v-html="section.content"
        ></div>
      </div>
    </div>
  </main>
</template>
