import { createRouter, createWebHistory } from 'vue-router'
import CartView from '@/views/CartView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/cart/:token',
      name: 'cart',
      component: CartView,
      props: true
    },
    {
      path: '/',
      redirect: to => {
        // Si acceden a la raíz, redirigir a una página de error o info
        return '/invalid'
      }
    },
    {
      path: '/invalid',
      name: 'invalid',
      component: () => import('@/views/InvalidView.vue')
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/invalid'
    }
  ]
})

export default router

