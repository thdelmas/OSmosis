<script setup>
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
</script>

<template>
  <main class="page-container" role="main">
    <h1>{{ t('nav.about', 'About OSmosis') }}</h1>
    <p class="page-lead">
      OSmosis is a free, open-source platform that helps you take back control of your devices.
      Flash custom firmware, install privacy-respecting operating systems, and rescue bricked hardware &mdash;
      all through a guided, beginner-friendly interface.
    </p>

    <section class="about-manifesto">
      <h2>Our Manifesto</h2>

      <div class="manifesto-point">
        <h3>1. You bought it, you own it</h3>
        <p>If you paid for a device, you should be able to run whatever software you want on it. Locked bootloaders, vendor restrictions, and forced obsolescence are problems, not features. Ownership means control &mdash; not a permanent rental agreement disguised as a purchase.</p>
      </div>

      <div class="manifesto-point">
        <h3>2. No device left behind</h3>
        <p>A perfectly good device doesn't become e-waste just because the manufacturer stopped sending updates. Hardware outlives software cycles by years. OSmosis exists to keep devices alive, useful, and secure long after their makers have moved on.</p>
      </div>

      <div class="manifesto-point">
        <h3>3. Privacy is non-negotiable</h3>
        <p>You shouldn't have to trade your data for a working phone. We prioritize ROMs and firmware that respect your privacy and give you control over what phones home. Telemetry should be opt-in, not baked into the OS you never chose.</p>
      </div>

      <div class="manifesto-point">
        <h3>4. Complexity is our problem, not yours</h3>
        <p>Flashing firmware can brick devices. Partition tables, boot images, recovery modes, download protocols &mdash; none of this should require a weekend of forum research. Our job is to make the process as safe, guided, and reversible as possible.</p>
      </div>

      <div class="manifesto-point">
        <h3>5. Built for everyone &mdash; literally everyone</h3>
        <p>If a twelve-year-old can't figure it out, we failed. If a grandparent is scared to click the next button, we failed. OSmosis must be so intuitive that technical background is irrelevant. Plain language over jargon. Clear steps over clever interfaces.</p>
      </div>

      <div class="manifesto-point">
        <h3>6. Every platform, every form factor</h3>
        <p>Phones today, routers and cars tomorrow. If it has a chip and a flash method, it belongs on our roadmap. A Raspberry Pi, a Samsung tablet, a boat chartplotter, and a smart light bulb all deserve the same respect.</p>
      </div>

      <div class="manifesto-point">
        <h3>7. Open source or go home</h3>
        <p>OSmosis is free software. The tools we wrap &mdash; Heimdall, fastboot, adb, esptool &mdash; are open source. We will never depend on proprietary blobs we can't audit. If we can't read the code, we can't trust the code, and neither should you.</p>
      </div>

      <div class="manifesto-point">
        <h3>8. Teach, don't hide</h3>
        <p>Every command we run is shown to you. Dry-run mode exists so you can learn before you commit. We'd rather you understand what's happening than blindly trust us. OSmosis is a tool, not a black box &mdash; and the best outcome is a user who no longer needs us.</p>
      </div>
    </section>

    <section class="about-links">
      <h2>Get Involved</h2>
      <ul class="credits-list">
        <li><strong>Source Code</strong> &mdash; OSmosis is free software. Inspect, modify, and contribute.</li>
        <li><strong>Report Issues</strong> &mdash; Found a bug or have a suggestion? Let us know.</li>
        <li><strong>Translate</strong> &mdash; Help make OSmosis accessible in more languages.</li>
      </ul>
    </section>
  </main>
</template>
