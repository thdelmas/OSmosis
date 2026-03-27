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
  align-items: flex-start;
  justify-content: flex-start;
  padding: 0.3rem;
  gap: 0.1rem;
}
.screen-rec__title {
  color: #aaa;
  font-family: monospace;
  font-size: 0.42rem;
  font-weight: 700;
  margin-bottom: 0.2rem;
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
  font-size: 0.35rem;
  padding: 0.05rem 0.15rem;
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
