<template>
  <el-card class="order-card" shadow="hover">
    <!-- Header -->
    <div class="order-header">
      <div class="order-number">
        <strong>{{ order.order_number }}</strong>
      </div>
      <el-tag :type="getStatusType(order.status)" size="small">
        {{ getStatusLabel(order.status) }}
      </el-tag>
    </div>

    <!-- Customer Info -->
    <div class="order-section">
      <div class="section-label">Cliente</div>
      <div>{{ order.customer_name || 'Cliente' }}</div>
      <div class="section-sublabel">{{ formatPhone(order.customer_phone) }}</div>
    </div>

    <!-- Items Summary -->
    <div class="order-section">
      <div class="section-label">Productos</div>
      <div class="items-list">
        <div v-for="item in order.items" :key="item.id" class="item-row">
          <span 
            class="item-name"
            @touchstart="(e) => startLongPress(e, item)"
            @touchend="endLongPress"
            @touchcancel="endLongPress"
            @mousedown="(e) => startLongPress(e, item)"
            @mouseup="endLongPress"
            @mouseleave="endLongPress"
          >
            {{ item.product_name }}
            <div v-if="showingPriceFor === item.id" class="price-tooltip">
              💰 ${{ item.unit_price.toFixed(2) }} c/u
            </div>
          </span>
          <span class="item-qty">x{{ item.quantity }}</span>
          <span class="item-total">${{ (item.unit_price * item.quantity).toFixed(2) }}</span>
        </div>
      </div>
    </div>

    <!-- Date and Total -->
    <div class="order-footer">
      <div class="date-section">
        <el-icon><Clock /></el-icon>
        <span class="date-text">{{ formatDate(order.created_at) }}</span>
      </div>
      <div class="total-section">
        <span class="total-amount">${{ order.total.toFixed(2) }}</span>
      </div>
    </div>

    <!-- Actions -->
    <div class="order-actions">
      <el-button 
        size="small" 
        @click="$emit('expand', order)"
        style="flex: 1"
      >
        Ver Detalles
      </el-button>
      <el-dropdown @command="(cmd) => $emit('action', cmd, order)">
        <el-button size="small" type="primary">
          Acciones
          <el-icon class="el-icon--right"><ArrowDown /></el-icon>
        </el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <!-- Cambiar Estados -->
            <el-dropdown-item 
              v-if="order.status === 'confirmed'" 
              command="ship"
            >
              🚚 Marcar En Camino
            </el-dropdown-item>
            <el-dropdown-item 
              v-if="order.status === 'shipped'" 
              command="deliver"
            >
              ✅ Marcar Entregada
            </el-dropdown-item>
            
            <!-- Asignar Conductor (solo confirmadas) -->
            <el-dropdown-item 
              v-if="order.status === 'confirmed'" 
              command="assign-driver"
              divided
            >
              👤 Asignar Conductor
            </el-dropdown-item>
            
            <!-- Cancelar (solo si NO está cancelada o entregada) -->
            <el-dropdown-item 
              v-if="!['cancelled', 'delivered'].includes(order.status)" 
              command="cancel"
              divided
            >
              ❌ Cancelar Orden
            </el-dropdown-item>
            
            <!-- Eliminar (siempre disponible) -->
            <el-dropdown-item 
              command="delete"
              divided
            >
              🗑️ Eliminar Orden
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Clock, ArrowDown } from '@element-plus/icons-vue'
import type { Order } from '../types'
import dayjs from 'dayjs'

defineProps<{
  order: Order
}>()

defineEmits<{
  expand: [order: Order]
  action: [command: string, order: Order]
}>()

// Long press state
const showingPriceFor = ref<string | null>(null)
let longPressTimer: number | null = null

const startLongPress = (event: Event, item: any) => {
  event.preventDefault()
  
  longPressTimer = window.setTimeout(() => {
    showingPriceFor.value = item.id
    
    // Vibrar en dispositivos móviles si está disponible
    if (navigator.vibrate) {
      navigator.vibrate(50)
    }
  }, 500) // 500ms para activar el long press
}

const endLongPress = () => {
  if (longPressTimer) {
    clearTimeout(longPressTimer)
    longPressTimer = null
  }
  
  // Ocultar el tooltip después de 2 segundos
  if (showingPriceFor.value) {
    setTimeout(() => {
      showingPriceFor.value = null
    }, 2000)
  }
}

const getStatusType = (status: string) => {
  const types: Record<string, any> = {
    pending: 'info',
    confirmed: 'primary',
    shipped: 'warning',
    delivered: 'success',
    cancelled: 'danger'
  }
  return types[status] || 'info'
}

const getStatusLabel = (status: string) => {
  const labels: Record<string, string> = {
    pending: 'Pendiente',
    confirmed: 'Confirmada',
    shipped: 'En Camino',
    delivered: 'Entregada',
    cancelled: 'Cancelada'
  }
  return labels[status] || status
}

const formatDate = (date: string) => {
  return dayjs(date).format('DD/MM/YYYY HH:mm')
}

const formatPhone = (phone?: string) => {
  if (!phone) return '-'
  return phone.replace(/(\d{3})(\d{3})(\d{4})/, '($1) $2-$3')
}
</script>

<style scoped>
.order-card {
  margin-bottom: 12px;
}

.order-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #ebeef5;
}

.order-number {
  font-size: 16px;
  color: #303133;
}

.order-section {
  margin-bottom: 12px;
}

.section-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}

.section-sublabel {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}

.items-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.item-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
  padding: 6px 0;
  gap: 12px;
}

.item-name {
  flex: 1;
  color: #303133;
  position: relative;
  cursor: pointer;
  user-select: none;
  -webkit-user-select: none;
  -webkit-touch-callout: none;
}

.price-tooltip {
  position: absolute;
  top: -35px;
  left: 50%;
  transform: translateX(-50%);
  background: #409EFF;
  color: white;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
  z-index: 1000;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.3);
  animation: tooltipFadeIn 0.2s ease-out;
}

.price-tooltip::after {
  content: '';
  position: absolute;
  bottom: -6px;
  left: 50%;
  transform: translateX(-50%);
  width: 0;
  height: 0;
  border-left: 6px solid transparent;
  border-right: 6px solid transparent;
  border-top: 6px solid #409EFF;
}

@keyframes tooltipFadeIn {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(-5px);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
}

.item-qty {
  color: #909399;
  font-size: 13px;
  min-width: 30px;
  text-align: center;
}

.item-total {
  color: #909399;
  font-size: 13px;
  min-width: 60px;
  text-align: right;
}

.order-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 16px 0;
  padding: 12px 0;
  border-top: 1px solid #ebeef5;
  border-bottom: 1px solid #ebeef5;
}

.total-section {
  display: flex;
  align-items: center;
}

.total-amount {
  font-size: 20px;
  font-weight: 700;
  color: #67C23A;
}

.date-section {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 16px;
  color: #303133;
}

.date-text {
  font-weight: 600;
}

.order-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}
</style>

