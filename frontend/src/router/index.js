import { createRouter, createWebHistory } from 'vue-router';
import { useAuthStore } from '../stores/auth';

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('../components/LoginView.vue')
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('../components/RegisterView.vue')
  },
  {
    path: '/',
    name: 'dashboard',
    component: () => import('../components/DashboardView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/templates',
    name: 'templates',
    component: () => import('../components/TemplateManagementView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/docs',
    name: 'docs',
    component: () => import('../components/DocumentationView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/tasks/:id',
    name: 'task-detail',
    component: () => import('../components/TaskDetailView.vue'),
    meta: { requiresAuth: true }
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

router.beforeEach((to) => {
  const auth = useAuthStore();
  auth.initialise();
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } };
  }
  if ((to.name === 'login' || to.name === 'register') && auth.isAuthenticated) {
    return { name: 'dashboard' };
  }
  return true;
});

export default router;
