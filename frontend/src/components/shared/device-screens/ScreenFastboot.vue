<template>
  <div class="screen-fb">
    <div class="screen-fb__line screen-fb__title">FASTBOOT MODE</div>
    <div class="screen-fb__line">PRODUCT: {{ codename || 'device' }}</div>
    <div class="screen-fb__line" :class="unlocked ? 'screen-fb__unlocked' : 'screen-fb__locked'">
      LOCK STATE: {{ unlocked ? 'unlocked' : 'locked' }}
    </div>
  </div>
</template>

<script setup>
defineProps({
  codename: { type: String, default: '' },
  unlocked: { type: Boolean, default: false },
})
</script>

<style scoped>
.screen-fb {
  width: 100%;
  height: 100%;
  background: #000;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  padding: 0.4rem;
  gap: 0.15rem;
}
.screen-fb__line {
  color: #ccc;
  font-family: monospace;
  font-size: 0.4rem;
  line-height: 1.3;
}
.screen-fb__title {
  color: #ef5350;
  font-weight: 700;
  font-size: 0.5rem;
  margin-bottom: 0.15rem;
}
.screen-fb__unlocked {
  color: #66bb6a;
}
.screen-fb__locked {
  color: #ef5350;
}
</style>
