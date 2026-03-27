<script setup>
import { computed } from 'vue'

const props = defineProps({
  /** Which physical buttons to highlight: 'power' | 'volume-up' | 'volume-down' */
  highlightButtons: { type: Array, default: () => [] },
  /** Optional label shown next to the highlighted button(s) */
  buttonLabel: { type: String, default: '' },
  /** Pulse animation on highlighted buttons */
  pulse: { type: Boolean, default: false },
  /** Device orientation: 'portrait' | 'landscape' */
  orientation: { type: String, default: 'portrait' },
})

const isLandscape = computed(() => props.orientation === 'landscape')

function isHighlighted(btn) {
  return props.highlightButtons.includes(btn)
}
</script>

<template>
  <div class="device-frame" :class="{ 'device-frame--landscape': isLandscape }">
    <svg
      :viewBox="isLandscape ? '0 0 340 200' : '0 0 200 380'"
      class="device-svg"
      xmlns="http://www.w3.org/2000/svg"
    >
      <!-- Phone body -->
      <rect
        :x="isLandscape ? 30 : 20"
        :y="isLandscape ? 10 : 20"
        :width="isLandscape ? 280 : 160"
        :height="isLandscape ? 180 : 340"
        rx="18" ry="18"
        class="device-body"
      />

      <!-- Screen area -->
      <rect
        :x="isLandscape ? 50 : 32"
        :y="isLandscape ? 24 : 52"
        :width="isLandscape ? 240 : 136"
        :height="isLandscape ? 152 : 276"
        rx="6" ry="6"
        class="device-screen-bg"
      />

      <!-- Front camera dot -->
      <circle
        :cx="isLandscape ? 170 : 100"
        :cy="isLandscape ? 17 : 38"
        r="3"
        class="device-camera"
      />

      <!-- BUTTONS (right side in portrait) -->

      <!-- Power button -->
      <rect
        v-if="!isLandscape"
        x="180" y="110" width="5" height="32" rx="2"
        class="device-btn"
        :class="{
          'device-btn--active': isHighlighted('power'),
          'device-btn--pulse': isHighlighted('power') && pulse,
        }"
      />
      <rect
        v-else
        x="250" y="190" width="32" height="5" rx="2"
        class="device-btn"
        :class="{
          'device-btn--active': isHighlighted('power'),
          'device-btn--pulse': isHighlighted('power') && pulse,
        }"
      />

      <!-- Volume Up button -->
      <rect
        v-if="!isLandscape"
        x="180" y="160" width="5" height="26" rx="2"
        class="device-btn"
        :class="{
          'device-btn--active': isHighlighted('volume-up'),
          'device-btn--pulse': isHighlighted('volume-up') && pulse,
        }"
      />
      <rect
        v-else
        x="190" y="190" width="26" height="5" rx="2"
        class="device-btn"
        :class="{
          'device-btn--active': isHighlighted('volume-up'),
          'device-btn--pulse': isHighlighted('volume-up') && pulse,
        }"
      />

      <!-- Volume Down button -->
      <rect
        v-if="!isLandscape"
        x="180" y="192" width="5" height="26" rx="2"
        class="device-btn"
        :class="{
          'device-btn--active': isHighlighted('volume-down'),
          'device-btn--pulse': isHighlighted('volume-down') && pulse,
        }"
      />
      <rect
        v-else
        x="148" y="190" width="26" height="5" rx="2"
        class="device-btn"
        :class="{
          'device-btn--active': isHighlighted('volume-down'),
          'device-btn--pulse': isHighlighted('volume-down') && pulse,
        }"
      />

      <!-- Button label annotation -->
      <template v-if="buttonLabel && highlightButtons.length">
        <!-- Arrow + label next to the first highlighted button -->
        <g v-if="!isLandscape" class="device-btn-label-group">
          <line
            x1="192" :y1="isHighlighted('power') ? 126 : isHighlighted('volume-up') ? 173 : 205"
            x2="210" :y2="isHighlighted('power') ? 126 : isHighlighted('volume-up') ? 173 : 205"
            class="device-label-arrow"
          />
          <text
            x="214" :y="isHighlighted('power') ? 130 : isHighlighted('volume-up') ? 177 : 209"
            class="device-label-text"
          >{{ buttonLabel }}</text>
        </g>
      </template>

      <!-- USB port at bottom -->
      <rect
        v-if="!isLandscape"
        x="90" y="358" width="20" height="4" rx="2"
        class="device-usb"
      />
      <rect
        v-else
        x="308" y="90" width="4" height="20" rx="2"
        class="device-usb"
      />
    </svg>

    <!-- Screen content overlay — positioned over the SVG screen area -->
    <div class="device-screen-content" :class="{ 'device-screen-content--landscape': isLandscape }">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.device-frame {
  position: relative;
  display: inline-block;
  width: 160px;
  flex-shrink: 0;
}
.device-frame--landscape {
  width: 240px;
}

.device-svg {
  width: 100%;
  height: auto;
  display: block;
}

/* Body */
.device-body {
  fill: var(--bg-card, #141c24);
  stroke: var(--border, #2a3a4a);
  stroke-width: 2;
}

/* Screen background */
.device-screen-bg {
  fill: #000;
}

/* Camera */
.device-camera {
  fill: var(--text-dim, #8a9bb0);
  opacity: 0.4;
}

/* Physical buttons */
.device-btn {
  fill: var(--border, #2a3a4a);
  transition: fill var(--transition-fast, 0.15s ease);
}
.device-btn--active {
  fill: var(--accent, #36d8b7);
}
.device-btn--pulse {
  animation: btn-pulse 1.2s ease-in-out infinite;
}

@keyframes btn-pulse {
  0%, 100% { fill: var(--accent, #36d8b7); opacity: 1; }
  50% { fill: var(--accent-hover, #5ee8cc); opacity: 0.6; }
}

/* Label annotation */
.device-label-arrow {
  stroke: var(--accent, #36d8b7);
  stroke-width: 1.5;
  marker-end: none;
}
.device-label-text {
  fill: var(--accent, #36d8b7);
  font-size: 9px;
  font-family: system-ui, sans-serif;
  font-weight: 600;
}

/* USB port */
.device-usb {
  fill: var(--text-dim, #8a9bb0);
  opacity: 0.3;
}

/* Screen content overlay */
.device-screen-content {
  position: absolute;
  /* Aligned to the screen rect in the SVG */
  top: 13.7%;
  left: 16%;
  width: 68%;
  height: 72.6%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: 4px;
  color: #ccc;
  font-size: calc(0.65rem * var(--font-scale, 1));
  text-align: center;
}
.device-screen-content--landscape {
  top: 12%;
  left: 14.7%;
  width: 70.6%;
  height: 76%;
}
</style>
