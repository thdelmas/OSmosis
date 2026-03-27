<template>
  <div class="screen-warn">
    <div class="screen-warn__icon">&#x26A0;</div>
    <div class="screen-warn__title">Warning</div>
    <div class="screen-warn__text">
      A custom OS can cause problems.<br />
      Press Volume Up to continue.
    </div>
    <div class="screen-warn__keys">
      <span class="key-hint">Vol Up = Continue</span>
      <span class="key-hint">Vol Down = Cancel</span>
    </div>
  </div>
</template>

<style scoped>
.screen-warn {
  width: 100%;
  height: 100%;
  background: #000;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.15rem;
  padding: 0.3rem;
}
.screen-warn__icon {
  font-size: 1rem;
  color: #ffc107;
}
.screen-warn__title {
  color: #ffc107;
  font-size: 0.5rem;
  font-weight: 700;
}
.screen-warn__text {
  color: #aaa;
  font-size: 0.35rem;
  text-align: center;
  line-height: 1.4;
}
.key-hint {
  color: #666;
  font-size: 0.3rem;
  font-family: monospace;
}
.screen-warn__keys {
  display: flex;
  flex-direction: column;
  gap: 0.05rem;
  margin-top: 0.1rem;
}
</style>
