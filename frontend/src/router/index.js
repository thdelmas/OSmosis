import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/wizard/identify',
  },
  // Guided wizard steps
  {
    path: '/wizard',
    component: () => import('@/components/wizard/WizardLayout.vue'),
    children: [
      { path: 'identify', name: 'identify', component: () => import('@/components/wizard/StepIdentify.vue') },
      { path: 'category', name: 'category', component: () => import('@/components/wizard/StepCategory.vue') },
      { path: 'connect', name: 'connect', component: () => import('@/components/wizard/StepConnect.vue') },
      { path: 'goal', name: 'goal', component: () => import('@/components/wizard/StepGoal.vue') },
      { path: 'install', name: 'install', component: () => import('@/components/wizard/StepInstall.vue') },
      { path: 'backup', name: 'backup', component: () => import('@/components/wizard/StepBackup.vue') },
      { path: 'fix', name: 'fix', component: () => import('@/components/wizard/StepFix.vue') },
      { path: 'scooter', name: 'scooter', component: () => import('@/components/wizard/StepScooter.vue') },
      { path: 'ebike', name: 'ebike', component: () => import('@/components/wizard/StepEbike.vue') },
      { path: 'os-builder', name: 'os-builder', component: () => import('@/components/wizard/StepOsBuilder.vue') },
      { path: 'pixel', name: 'pixel', component: () => import('@/components/wizard/StepPixel.vue') },
      { path: 'bootable', name: 'bootable', component: () => import('@/components/wizard/StepBootable.vue') },
      { path: 'microcontroller', name: 'microcontroller', component: () => import('@/components/wizard/StepMicrocontroller.vue') },
      { path: 't2', name: 't2', component: () => import('@/components/wizard/StepT2.vue') },
      { path: 'medicat', name: 'medicat', component: () => import('@/components/wizard/StepMediacat.vue') },
      { path: 'troubleshoot', name: 'troubleshoot', component: () => import('@/components/wizard/StepTroubleshoot.vue') },
    ],
  },
  // Tools
  {
    path: '/flash-stock',
    name: 'flash-stock',
    component: () => import('@/components/pages/PageFlashStock.vue'),
  },
  {
    path: '/flash-recovery',
    name: 'flash-recovery',
    component: () => import('@/components/pages/PageFlashRecovery.vue'),
  },
  {
    path: '/sideload',
    name: 'sideload',
    component: () => import('@/components/pages/PageSideload.vue'),
  },
  {
    path: '/preflight',
    name: 'preflight',
    component: () => import('@/components/pages/PagePreflight.vue'),
  },
  {
    path: '/registry',
    name: 'registry',
    component: () => import('@/components/pages/PageRegistry.vue'),
  },
  // Info pages
  {
    path: '/credits',
    name: 'credits',
    component: () => import('@/components/pages/PageCredits.vue'),
  },
  {
    path: '/wiki',
    name: 'wiki',
    component: () => import('@/components/pages/PageWiki.vue'),
  },
  {
    path: '/about',
    name: 'about',
    component: () => import('@/components/pages/PageAbout.vue'),
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export default router
