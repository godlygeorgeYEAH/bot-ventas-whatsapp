<template>
  <el-container style="height: 100vh">
    <!-- Mobile Overlay -->
    <div 
      v-if="isMobile && drawerVisible" 
      class="mobile-overlay"
      @click="drawerVisible = false"
    />

    <!-- Sidebar -->
    <el-aside 
      :width="sidebarWidth"
      :class="['sidebar', { 'mobile-sidebar': isMobile, 'drawer-open': drawerVisible }]"
      style="background-color: #001529"
    >
      <div class="logo">
        <h2 style="color: white; padding: 20px; text-align: center">
          🤖 Bot Ventas
        </h2>
      </div>
      
      <el-menu
        :default-active="currentRoute"
        router
        background-color="#001529"
        text-color="#fff"
        active-text-color="#409EFF"
        @select="handleMenuSelect"
      >
        <el-menu-item index="/dashboard">
          <el-icon><Odometer /></el-icon>
          <span>Dashboard</span>
        </el-menu-item>
        
        <el-menu-item index="/orders">
          <el-icon><Document /></el-icon>
          <span>Órdenes</span>
        </el-menu-item>
        
        <el-menu-item index="/products">
          <el-icon><Box /></el-icon>
          <span>Productos</span>
        </el-menu-item>
        
        <el-menu-item index="/customers">
          <el-icon><User /></el-icon>
          <span>Clientes</span>
        </el-menu-item>

        <el-menu-item index="/configuration">
          <el-icon><Setting /></el-icon>
          <span>Configuración</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- Main Content -->
    <el-container>
      <el-header class="main-header">
        <!-- Mobile Menu Button -->
        <el-button 
          v-if="isMobile"
          :icon="Menu"
          circle
          @click="drawerVisible = !drawerVisible"
        />
        
        <h3 class="page-title">{{ pageTitle }}</h3>
        
        <div>
          <el-tag type="success">Online</el-tag>
        </div>
      </el-header>
      
      <el-main class="main-content">
        <slot />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { Menu } from '@element-plus/icons-vue'

const route = useRoute()
const drawerVisible = ref(false)
const windowWidth = ref(window.innerWidth)

const currentRoute = computed(() => route.path)

const isMobile = computed(() => windowWidth.value < 768)

const sidebarWidth = computed(() => {
  if (isMobile.value) {
    return '250px' // En móvil siempre 250px pero oculto por CSS
  }
  return '250px'
})

const pageTitle = computed(() => {
  const titles: Record<string, string> = {
    '/dashboard': 'Dashboard',
    '/orders': 'Órdenes',
    '/products': 'Productos',
    '/customers': 'Clientes',
    '/configuration': 'Configuración'
  }
  return titles[route.path] || 'Dashboard'
})

const handleMenuSelect = () => {
  // Cerrar drawer en móvil al seleccionar
  if (isMobile.value) {
    drawerVisible.value = false
  }
}

const handleResize = () => {
  windowWidth.value = window.innerWidth
  // Cerrar drawer si se cambia a desktop
  if (!isMobile.value) {
    drawerVisible.value = false
  }
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.main-header {
  padding: 0 20px;
  border-bottom: 1px solid #e8e8e8;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.page-title {
  flex: 1;
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.main-content {
  background-color: #f0f2f5;
  padding: 20px;
}

.sidebar {
  box-shadow: 2px 0 6px rgba(0, 21, 41, 0.35);
  transition: transform 0.3s ease;
}

/* Mobile Styles */
.mobile-sidebar {
  position: fixed !important;
  left: 0;
  top: 0;
  height: 100vh;
  z-index: 2000;
  transform: translateX(-100%);
}

.mobile-sidebar.drawer-open {
  transform: translateX(0);
}

.mobile-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  z-index: 1999;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .main-header {
    padding: 0 12px;
  }
  
  .main-content {
    padding: 12px;
  }
  
  .page-title {
    font-size: 16px;
  }
}

@media (max-width: 480px) {
  .page-title {
    font-size: 14px;
  }
}
</style>

