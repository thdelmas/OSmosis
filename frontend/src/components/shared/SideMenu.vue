<script setup>
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
</script>

<template>
  <aside class="side-menu" role="navigation" aria-label="Main navigation">
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
        {{ t('nav.flashStock', 'Flash Stock') }}
      </router-link>

      <router-link to="/flash-recovery" class="side-menu-link" active-class="active">
        {{ t('nav.flashRecovery', 'Flash Recovery') }}
      </router-link>

      <router-link to="/sideload" class="side-menu-link" active-class="active">
        {{ t('nav.sideload', 'ADB Sideload') }}
      </router-link>

      <router-link to="/preflight" class="side-menu-link" active-class="active">
        {{ t('nav.preflight', 'Pre-Flight') }}
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
