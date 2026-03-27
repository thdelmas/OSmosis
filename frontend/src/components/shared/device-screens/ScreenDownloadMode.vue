<template>
  <div class="screen-dl">
    <div class="screen-dl__icon">&#x2B07;</div>
    <div class="screen-dl__title">Downloading...</div>
    <div class="screen-dl__warning">Do not turn off target!</div>
    <div class="screen-dl__bar">
      <div class="screen-dl__bar-fill" />
    </div>
  </div>
</template>

<style scoped>
.screen-dl {
  width: 100%;
  height: 100%;
  background: #0a1628;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.2rem;
  padding: 0.3rem;
}
.screen-dl__icon {
  font-size: 1.2rem;
  color: #00bcd4;
}
.screen-dl__title {
  color: #00bcd4;
  font-size: 0.55rem;
  font-weight: 700;
}
.screen-dl__warning {
  color: #ef5350;
  font-size: 0.4rem;
  margin-top: 0.1rem;
}
.screen-dl__bar {
  width: 60%;
  height: 3px;
  background: #1a3050;
  border-radius: 2px;
  margin-top: 0.3rem;
  overflow: hidden;
}
.screen-dl__bar-fill {
  width: 30%;
  height: 100%;
  background: #00bcd4;
  border-radius: 2px;
  animation: dl-progress 2s ease-in-out infinite;
}
@keyframes dl-progress {
  0% { width: 10%; }
  50% { width: 70%; }
  100% { width: 10%; }
}
</style>
