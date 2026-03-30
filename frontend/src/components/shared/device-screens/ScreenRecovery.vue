<template>
  <div class="screen-rec">
    <div class="screen-rec__title">Android Recovery</div>
    <div class="screen-rec__menu">
      <div
        v-for="(item, i) in items"
        :key="i"
        class="screen-rec__item"
        :class="{ 'screen-rec__item--selected': i === selected }"
      >{{ item }}</div>
    </div>

    <div class="screen-rec__mascot">
      <svg viewBox="0 0 120 100" class="screen-rec__svg" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <!-- Subtle highlight gradient for the body -->
          <linearGradient id="bodyGrad" x1="0" y1="0" x2="0.3" y2="1">
            <stop offset="0%" stop-color="#b8d948" />
            <stop offset="100%" stop-color="#8cb021" />
          </linearGradient>
          <!-- Darker shade for depth -->
          <linearGradient id="bodyShade" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#a4c639" />
            <stop offset="100%" stop-color="#7a9a1e" />
          </linearGradient>
          <!-- Cavity depth gradient -->
          <linearGradient id="cavityGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#0d1a06" />
            <stop offset="100%" stop-color="#1a2e10" />
          </linearGradient>
          <!-- Lid gradient -->
          <linearGradient id="lidGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#9abf30" />
            <stop offset="100%" stop-color="#6d8f1a" />
          </linearGradient>
          <!-- Warning triangle gradient -->
          <linearGradient id="warnGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#ef5350" />
            <stop offset="100%" stop-color="#c62828" />
          </linearGradient>
        </defs>

        <!-- Tilt the bugdroid 40° to lie on its back -->
        <g transform="translate(16, 42) rotate(40, 28, 22)">

          <!-- ====== Shadow on ground ====== -->
          <ellipse cx="28" cy="62" rx="26" ry="4" fill="#0a0a0a" opacity="0.35" />

          <!-- ====== Legs (capsule, slight gap from body) ====== -->
          <rect x="14" y="43" width="11" height="18" rx="5.5" fill="url(#bodyShade)" />
          <rect x="31" y="43" width="11" height="18" rx="5.5" fill="url(#bodyShade)" />
          <!-- Leg highlights -->
          <rect x="16" y="44" width="3" height="14" rx="1.5" fill="#b8d948" opacity="0.2" />
          <rect x="33" y="44" width="3" height="14" rx="1.5" fill="#b8d948" opacity="0.2" />

          <!-- ====== Arms (capsule, on sides of body) ====== -->
          <rect x="-5" y="17" width="10" height="22" rx="5" fill="url(#bodyShade)" />
          <rect x="51" y="17" width="10" height="22" rx="5" fill="url(#bodyShade)" />
          <!-- Arm highlights -->
          <rect x="-3" y="19" width="3" height="16" rx="1.5" fill="#b8d948" opacity="0.2" />
          <rect x="53" y="19" width="3" height="16" rx="1.5" fill="#b8d948" opacity="0.2" />

          <!-- ====== Torso ====== -->
          <rect x="7" y="14" width="42" height="30" rx="6" fill="url(#bodyGrad)" />
          <!-- Body edge highlight (left) -->
          <rect x="9" y="16" width="2.5" height="24" rx="1.25" fill="#c8e650" opacity="0.18" />

          <!-- ====== Open chest cavity ====== -->
          <rect x="12" y="19" width="32" height="18" rx="3.5" fill="url(#cavityGrad)" />
          <!-- Cavity inner rim/bevel -->
          <rect x="12" y="19" width="32" height="18" rx="3.5" fill="none" stroke="#2a4818" stroke-width="0.6" />

          <!-- Internal circuitry -->
          <!-- PCB traces -->
          <line x1="16" y1="23" x2="24" y2="23" stroke="#345a1c" stroke-width="0.9" stroke-linecap="round" />
          <line x1="16" y1="26" x2="30" y2="26" stroke="#345a1c" stroke-width="0.9" stroke-linecap="round" />
          <line x1="16" y1="29" x2="21" y2="29" stroke="#345a1c" stroke-width="0.9" stroke-linecap="round" />
          <line x1="24" y1="23" x2="24" y2="29" stroke="#345a1c" stroke-width="0.7" stroke-linecap="round" />
          <line x1="30" y1="26" x2="30" y2="32" stroke="#345a1c" stroke-width="0.7" stroke-linecap="round" />
          <!-- Chip -->
          <rect x="33" y="22" width="7" height="5" rx="1" fill="#1f3a0e" stroke="#345a1c" stroke-width="0.5" />
          <line x1="34" y1="22" x2="34" y2="20.5" stroke="#345a1c" stroke-width="0.5" />
          <line x1="36.5" y1="22" x2="36.5" y2="20.5" stroke="#345a1c" stroke-width="0.5" />
          <line x1="39" y1="22" x2="39" y2="20.5" stroke="#345a1c" stroke-width="0.5" />
          <line x1="34" y1="27" x2="34" y2="28.5" stroke="#345a1c" stroke-width="0.5" />
          <line x1="36.5" y1="27" x2="36.5" y2="28.5" stroke="#345a1c" stroke-width="0.5" />
          <line x1="39" y1="27" x2="39" y2="28.5" stroke="#345a1c" stroke-width="0.5" />
          <!-- Capacitor -->
          <circle cx="18" cy="33" r="2" fill="none" stroke="#345a1c" stroke-width="0.7" />
          <circle cx="18" cy="33" r="0.7" fill="#345a1c" />
          <!-- LED dots -->
          <circle cx="26" cy="31" r="0.9" fill="#4a2" opacity="0.6" />
          <circle cx="29" cy="31" r="0.9" fill="#a42" opacity="0.5" />
          <!-- Solder pads -->
          <circle cx="22" cy="33.5" r="0.6" fill="#345a1c" />
          <circle cx="25" cy="33.5" r="0.6" fill="#345a1c" />

          <!-- ====== Chest panel lid (hinged open) ====== -->
          <g transform="translate(12, 5) rotate(-15, 16, 12)">
            <rect x="0" y="0" width="32" height="7" rx="3" fill="url(#lidGrad)" />
            <!-- Top highlight -->
            <rect x="2" y="1" width="28" height="2" rx="1" fill="#b8d948" opacity="0.25" />
            <!-- Hinge shadow -->
            <ellipse cx="16" cy="8.5" rx="12" ry="1.5" fill="#0a0a0a" opacity="0.15" />
          </g>

          <!-- ====== Head (semicircle dome + flat bottom) ====== -->
          <path d="M7,14 L7,7 Q7,-4 28,-4 Q49,-4 49,7 L49,14 Z" fill="url(#bodyGrad)" />
          <!-- Head highlight -->
          <path d="M11,12 L11,8 Q11,0 22,0 Q26,0 26,4 L26,12 Z" fill="#c8e650" opacity="0.1" />

          <!-- X eyes (knocked out / dizzy) -->
          <g stroke="#fff" stroke-width="1.6" stroke-linecap="round">
            <line x1="17" y1="4" x2="22" y2="9" />
            <line x1="22" y1="4" x2="17" y2="9" />
            <line x1="34" y1="4" x2="39" y2="9" />
            <line x1="39" y1="4" x2="34" y2="9" />
          </g>

          <!-- ====== Antennae ====== -->
          <line x1="17" y1="-2" x2="11" y2="-10" stroke="#a4c639" stroke-width="2.2" stroke-linecap="round" />
          <line x1="39" y1="-2" x2="45" y2="-10" stroke="#a4c639" stroke-width="2.2" stroke-linecap="round" />
          <!-- Antenna tips -->
          <circle cx="11" cy="-10" r="1.3" fill="#a4c639" />
          <circle cx="45" cy="-10" r="1.3" fill="#a4c639" />
        </g>

        <!-- ====== Red warning triangle ====== -->
        <g transform="translate(73, 6)">
          <!-- Triangle shadow -->
          <polygon points="14,3 28,26 0,26" fill="#1a0000" opacity="0.2" transform="translate(1,1)" />
          <!-- Triangle outline -->
          <polygon points="14,1 28,25 0,25" fill="none" stroke="url(#warnGrad)" stroke-width="2.5" stroke-linejoin="round" />
          <!-- Exclamation mark -->
          <line x1="14" y1="8" x2="14" y2="17" stroke="#d32f2f" stroke-width="3" stroke-linecap="round" />
          <circle cx="14" cy="21.5" r="1.8" fill="#d32f2f" />
        </g>
      </svg>
    </div>
  </div>
</template>

<script setup>
defineProps({
  selected: { type: Number, default: 3 },
})

const items = [
  'Reboot system now',
  'Reboot to bootloader',
  'Enter fastboot',
  'Apply update from ADB',
  'Wipe data/factory reset',
  'Mount /system',
]
</script>

<style scoped>
.screen-rec {
  width: 100%;
  height: 100%;
  background: #000;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  padding: 0.15rem 0.25rem;
  gap: 0.05rem;
}
.screen-rec__mascot {
  width: 85%;
  max-width: 78px;
  flex-shrink: 0;
  margin-top: 0.05rem;
}
.screen-rec__svg {
  width: 100%;
  height: auto;
  display: block;
}
.screen-rec__title {
  color: #aaa;
  font-family: monospace;
  font-size: 0.42rem;
  font-weight: 700;
  margin-bottom: 0.1rem;
  align-self: flex-start;
}
.screen-rec__menu {
  display: flex;
  flex-direction: column;
  gap: 0.05rem;
  width: 100%;
}
.screen-rec__item {
  color: #888;
  font-family: monospace;
  font-size: 0.33rem;
  padding: 0.04rem 0.12rem;
  border-radius: 1px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.screen-rec__item--selected {
  background: #1565c0;
  color: #fff;
}
</style>
