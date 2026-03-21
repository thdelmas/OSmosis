import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/wizard/category',
  },
  // Guided wizard steps
  {
    path: '/wizard',
    component: () => import('@/components/wizard/WizardLayout.vue'),
    children: [
      { path: 'category', name: 'category', component: () => import('@/components/wizard/StepCategory.vue') },
      { path: 'connect', name: 'connect', component: () => import('@/components/wizard/StepConnect.vue') },
      { path: 'goal', name: 'goal', component: () => import('@/components/wizard/StepGoal.vue') },
      { path: 'install', name: 'install', component: () => import('@/components/wizard/StepInstall.vue') },
      { path: 'backup', name: 'backup', component: () => import('@/components/wizard/StepBackup.vue') },
      { path: 'fix', name: 'fix', component: () => import('@/components/wizard/StepFix.vue') },
      { path: 'scooter', name: 'scooter', component: () => import('@/components/wizard/StepScooter.vue') },
      { path: 'os-builder', name: 'os-builder', component: () => import('@/components/wizard/StepOsBuilder.vue') },
      { path: 'bootable', name: 'bootable', component: () => import('@/components/wizard/StepBootable.vue') },
    ],
  },
  // Advanced mode
  {
    path: '/advanced',
    name: 'advanced',
    component: () => import('@/components/advanced/AdvancedDashboard.vue'),
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export default router
