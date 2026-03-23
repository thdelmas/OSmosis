<script setup>
import { useI18n } from 'vue-i18n'
import GlossaryTip from '@/components/shared/GlossaryTip.vue'
const { t } = useI18n()

defineProps({
  open: { type: Boolean, default: false },
})

defineEmits(['close'])
</script>

<template>
  <aside id="side-menu" class="side-menu" :class="{ open }" role="navigation" aria-label="Main navigation">
    <div class="side-menu-logo">
      <router-link to="/" class="side-menu-brand">
        <img src="/logo.png" alt="OSmosis logo" class="side-menu-logo-img" />
        <span class="side-menu-title"><span class="accent">OS</span>mosis</span>
      </router-link>
    </div>

    <nav class="side-menu-nav">
      <router-link
        to="/wizard/identify"
        class="side-menu-link"
        :class="{ active: $route.path.startsWith('/wizard') }"
      >
        {{ t('nav.wizard', 'Wizard') }}
      </router-link>

      <div class="side-menu-divider"></div>
      <div class="side-menu-section">{{ t('nav.tools', 'Tools') }}</div>

      <router-link to="/flash-stock" class="side-menu-link" active-class="active">
        <GlossaryTip term="Flash Stock">{{ t('nav.flashStock', 'Restore factory software') }}</GlossaryTip>
      </router-link>

      <router-link to="/flash-recovery" class="side-menu-link" active-class="active">
        <GlossaryTip term="Flash Recovery">{{ t('nav.flashRecovery', 'Install recovery tool') }}</GlossaryTip>
      </router-link>

      <router-link to="/sideload" class="side-menu-link" active-class="active">
        <GlossaryTip term="ADB Sideload">{{ t('nav.sideload', 'Send file to device') }}</GlossaryTip>
      </router-link>

      <router-link to="/preflight" class="side-menu-link" active-class="active">
        <GlossaryTip term="Pre-Flight">{{ t('nav.preflight', 'Pre-install checklist') }}</GlossaryTip>
      </router-link>

      <router-link to="/registry" class="side-menu-link" active-class="active">
        {{ t('nav.registry', 'Registry') }}
      </router-link>

      <div class="side-menu-divider"></div>

      <router-link to="/wiki" class="side-menu-link" active-class="active">
        {{ t('nav.wiki', 'Wiki') }}
      </router-link>

      <router-link to="/about" class="side-menu-link" active-class="active">
        {{ t('nav.about', 'About') }}
      </router-link>

      <router-link to="/credits" class="side-menu-link" active-class="active">
        {{ t('nav.credits', 'Credits') }}
      </router-link>
    </nav>

    <div class="side-menu-footer">
      <p>Free & open source</p>
    </div>
  </aside>
</template>
