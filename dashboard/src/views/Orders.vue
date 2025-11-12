<template>
  <MainLayout>
    <div class="orders-container">
      <!-- Header con estadísticas -->
      <el-row :gutter="isMobile ? 12 : 20" style="margin-bottom: 20px">
        <el-col :xs="12" :sm="12" :md="6">
          <el-card shadow="hover" class="stat-card">
            <el-statistic title="Total" :value="stats.total">
              <template #suffix>
                <el-icon><Document /></el-icon>
              </template>
            </el-statistic>
          </el-card>
        </el-col>
        <el-col :xs="12" :sm="12" :md="6">
          <el-card shadow="hover" class="stat-card">
            <el-statistic 
              title="Confirmadas" 
              :value="stats.confirmed"
              :value-style="{ color: '#409EFF' }"
            >
              <template #suffix>
                <el-icon><Check /></el-icon>
              </template>
            </el-statistic>
          </el-card>
        </el-col>
        <el-col :xs="12" :sm="12" :md="6">
          <el-card shadow="hover" class="stat-card">
            <el-statistic 
              title="En Camino" 
              :value="stats.shipped"
              :value-style="{ color: '#E6A23C' }"
            >
              <template #suffix>
                <el-icon><Van /></el-icon>
              </template>
            </el-statistic>
          </el-card>
        </el-col>
        <el-col :xs="12" :sm="12" :md="6">
          <el-card shadow="hover" class="stat-card">
            <el-statistic 
              title="Entregadas" 
              :value="stats.delivered"
              :value-style="{ color: '#67C23A' }"
            >
              <template #suffix>
                <el-icon><CircleCheck /></el-icon>
              </template>
            </el-statistic>
          </el-card>
        </el-col>
      </el-row>

      <!-- Filtros -->
      <el-card style="margin-bottom: 20px">
        <el-row :gutter="isMobile ? 12 : 20" align="middle">
          <el-col :xs="24" :sm="24" :md="10">
            <el-input
              v-model="searchQuery"
              :placeholder="isMobile ? 'Buscar...' : 'Buscar por número de orden o cliente'"
              :prefix-icon="Search"
              clearable
              size="default"
            />
          </el-col>
          <el-col :xs="16" :sm="16" :md="8">
            <el-select
              v-model="statusFilter"
              placeholder="Filtrar por estado"
              clearable
              style="width: 100%"
              size="default"
            >
              <el-option label="Todos" value="" />
              <el-option label="Pendiente" value="pending" />
              <el-option label="Confirmada" value="confirmed" />
              <el-option label="En Camino" value="shipped" />
              <el-option label="Entregada" value="delivered" />
              <el-option label="Cancelada" value="cancelled" />
            </el-select>
          </el-col>
          <el-col :xs="8" :sm="8" :md="6">
            <el-button 
              type="primary" 
              :icon="Refresh" 
              @click="loadOrders"
              :style="{ width: isMobile ? '100%' : 'auto' }"
            >
              {{ isMobile ? '' : 'Actualizar' }}
            </el-button>
          </el-col>
        </el-row>
      </el-card>

      <!-- Vista Móvil: Cards -->
      <div v-if="isMobile" class="mobile-view">
        <OrderCard
          v-for="order in paginatedOrders"
          :key="order.id"
          :order="order"
          @expand="showOrderDetails"
          @action="handleAction"
        />
        
        <el-empty v-if="filteredOrders.length === 0" description="No hay órdenes" />
      </div>

      <!-- Vista Desktop: Tabla -->
      <el-card v-else>
        <el-table
          v-loading="loading"
          :data="paginatedOrders"
          stripe
          style="width: 100%"
          :default-sort="{ prop: 'created_at', order: 'descending' }"
        >
          <!-- Expansión para ver items -->
          <el-table-column type="expand">
            <template #default="{ row }">
              <div style="padding: 20px">
                <h4 style="margin-bottom: 10px">Items de la Orden:</h4>
                <el-table :data="row.items" border>
                  <el-table-column prop="product_name" label="Producto" />
                  <el-table-column prop="quantity" label="Cantidad" width="100" align="center" />
                  <el-table-column label="Precio Unitario" width="130" align="right">
                    <template #default="{ row: item }">
                      ${{ item.unit_price.toFixed(2) }}
                    </template>
                  </el-table-column>
                  <el-table-column label="Total" width="130" align="right">
                    <template #default="{ row: item }">
                      <strong style="color: #67C23A">
                        ${{ (item.unit_price * item.quantity).toFixed(2) }}
                      </strong>
                    </template>
                  </el-table-column>
                </el-table>

                <div style="margin-top: 20px">
                  <el-descriptions :column="2" border>
                    <el-descriptions-item label="Subtotal">
                      ${{ row.subtotal.toFixed(2) }}
                    </el-descriptions-item>
                    <el-descriptions-item label="Impuesto">
                      ${{ row.tax.toFixed(2) }}
                    </el-descriptions-item>
                    <el-descriptions-item label="Envío">
                      ${{ row.shipping_cost.toFixed(2) }}
                    </el-descriptions-item>
                    <el-descriptions-item label="Total">
                      <strong>${{ row.total.toFixed(2) }}</strong>
                    </el-descriptions-item>
                    <el-descriptions-item label="Método de Pago" :span="2">
                      {{ getPaymentMethodLabel(row.payment_method) }}
                    </el-descriptions-item>
                    <el-descriptions-item v-if="row.delivery_reference" label="Referencia" :span="2">
                      {{ row.delivery_reference }}
                    </el-descriptions-item>
                    <el-descriptions-item v-if="row.delivery_latitude && row.delivery_longitude" label="Ubicación" :span="2">
                      <el-link 
                        :href="`https://www.google.com/maps?q=${row.delivery_latitude},${row.delivery_longitude}`"
                        target="_blank"
                        type="primary"
                      >
                        <el-icon><Location /></el-icon>
                        Ver en Google Maps
                      </el-link>
                    </el-descriptions-item>
                  </el-descriptions>
                </div>
              </div>
            </template>
          </el-table-column>

          <!-- Número de orden -->
          <el-table-column prop="order_number" label="Número de Orden" width="180" sortable>
            <template #default="{ row }">
              <strong>{{ row.order_number }}</strong>
            </template>
          </el-table-column>

          <!-- Cliente -->
          <el-table-column label="Cliente" width="200">
            <template #default="{ row }">
              <div>
                <div>{{ row.customer_name || 'Cliente' }}</div>
                <div style="font-size: 12px; color: #909399">
                  {{ formatPhone(row.customer_phone) }}
                </div>
              </div>
            </template>
          </el-table-column>

          <!-- Items (resumen) -->
          <el-table-column label="Productos" width="150">
            <template #default="{ row }">
              <div style="font-size: 12px">
                {{ row.items.length }} producto{{ row.items.length > 1 ? 's' : '' }}
              </div>
              <div style="font-size: 11px; color: #909399; margin-top: 2px">
                {{ getItemsSummary(row.items) }}
              </div>
            </template>
          </el-table-column>

          <!-- Total Items -->
          <el-table-column label="Total Items" width="120" align="right">
            <template #default="{ row }">
              <strong style="font-size: 14px; color: #606266">
                ${{ calculateItemsTotal(row.items).toFixed(2) }}
              </strong>
            </template>
          </el-table-column>

          <!-- Total -->
          <el-table-column label="Total" width="120" align="right" sortable prop="total">
            <template #default="{ row }">
              <strong style="font-size: 16px; font-weight: 600; color: #67C23A">
                ${{ row.total.toFixed(2) }}
              </strong>
            </template>
          </el-table-column>

          <!-- Estado -->
          <el-table-column label="Estado" width="130" sortable prop="status">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)">
                {{ getStatusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>

          <!-- Fecha -->
          <el-table-column label="Fecha" width="180" sortable prop="created_at">
            <template #default="{ row }">
              <div>
                <div style="font-size: 16px; font-weight: 600; color: #303133">
                  {{ formatDate(row.created_at) }}
                </div>
                <div style="font-size: 14px; color: #606266; margin-top: 2px">
                  {{ formatTime(row.created_at) }}
                </div>
              </div>
            </template>
          </el-table-column>

          <!-- Acciones -->
          <el-table-column label="Acciones" width="180" fixed="right">
            <template #default="{ row }">
              <el-dropdown @command="(cmd) => handleAction(cmd, row)">
                <el-button size="small" type="primary">
                  Acciones
                  <el-icon class="el-icon--right"><ArrowDown /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <!-- Cambiar Estados -->
                    <el-dropdown-item 
                      v-if="row.status === 'confirmed'" 
                      command="ship"
                      :icon="Van"
                    >
                      Marcar En Camino
                    </el-dropdown-item>
                    <el-dropdown-item 
                      v-if="row.status === 'shipped'" 
                      command="deliver"
                      :icon="CircleCheck"
                    >
                      Marcar Entregada
                    </el-dropdown-item>
                    
                    <!-- Asignar Conductor (solo confirmadas) -->
                    <el-dropdown-item 
                      v-if="row.status === 'confirmed'" 
                      command="assign-driver"
                      divided
                    >
                      👤 Asignar Conductor
                    </el-dropdown-item>
                    
                    <!-- Cancelar (solo si NO está cancelada o entregada) -->
                    <el-dropdown-item 
                      v-if="!['cancelled', 'delivered'].includes(row.status)" 
                      command="cancel"
                      :icon="CircleClose"
                      divided
                    >
                      Cancelar Orden
                    </el-dropdown-item>
                    
                    <!-- Eliminar (siempre disponible) -->
                    <el-dropdown-item 
                      command="delete"
                      divided
                    >
                      🗑️ Eliminar Orden
                    </el-dropdown-item>
                    
                    <el-dropdown-item divided command="details" :icon="View">
                      Ver Detalles
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </template>
          </el-table-column>
        </el-table>

        <!-- Paginación -->
        <div style="margin-top: 20px; text-align: right">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[10, 20, 50, 100]"
            :total="filteredOrders.length"
            layout="total, sizes, prev, pager, next"
          />
        </div>
      </el-card>

      <!-- Modal para Detalles (Móvil) -->
      <el-dialog
        v-model="detailsDialogVisible"
        :title="`Orden ${selectedOrder?.order_number}`"
        :width="isMobile ? '95%' : '600px'"
      >
        <div v-if="selectedOrder">
          <!-- Items -->
          <div class="dialog-section">
            <h4>Productos:</h4>
            <div v-for="item in selectedOrder.items" :key="item.id" class="item-detail">
              <div>
                <div>{{ item.product_name }}</div>
                <div style="font-size: 12px; color: #909399">
                  {{ item.quantity }} x ${{ item.unit_price.toFixed(2) }}
                </div>
              </div>
              <div style="font-weight: 600; color: #67C23A">
                ${{ (item.unit_price * item.quantity).toFixed(2) }}
              </div>
            </div>
          </div>

          <!-- Totales -->
          <div class="dialog-section">
            <el-descriptions :column="1" border>
              <el-descriptions-item label="Subtotal">
                ${{ selectedOrder.subtotal.toFixed(2) }}
              </el-descriptions-item>
              <el-descriptions-item label="Impuesto">
                ${{ selectedOrder.tax.toFixed(2) }}
              </el-descriptions-item>
              <el-descriptions-item label="Envío">
                ${{ selectedOrder.shipping_cost.toFixed(2) }}
              </el-descriptions-item>
              <el-descriptions-item label="Total">
                <strong>${{ selectedOrder.total.toFixed(2) }}</strong>
              </el-descriptions-item>
            </el-descriptions>
          </div>

          <!-- Entrega -->
          <div class="dialog-section">
            <h4>Información de Entrega:</h4>
            <el-descriptions :column="1" border>
              <el-descriptions-item label="Cliente">
                {{ selectedOrder.customer_name || 'Cliente' }}
              </el-descriptions-item>
              <el-descriptions-item label="Teléfono">
                {{ formatPhone(selectedOrder.customer_phone) }}
              </el-descriptions-item>
              <el-descriptions-item label="Método de Pago">
                {{ getPaymentMethodLabel(selectedOrder.payment_method) }}
              </el-descriptions-item>
              <el-descriptions-item v-if="selectedOrder.delivery_reference" label="Referencia">
                {{ selectedOrder.delivery_reference }}
              </el-descriptions-item>
              <el-descriptions-item v-if="selectedOrder.delivery_latitude" label="Ubicación">
                <el-link 
                  :href="`https://www.google.com/maps?q=${selectedOrder.delivery_latitude},${selectedOrder.delivery_longitude}`"
                  target="_blank"
                  type="primary"
                >
                  Ver en Google Maps
                </el-link>
              </el-descriptions-item>
            </el-descriptions>
          </div>
        </div>
      </el-dialog>
    </div>
  </MainLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Van, CircleCheck, CircleClose, View, ArrowDown, Location, Document, Check } from '@element-plus/icons-vue'
import MainLayout from '../layouts/MainLayout.vue'
import OrderCard from '../components/OrderCard.vue'
import { ordersApi } from '../api/orders'
import type { Order } from '../types'
import dayjs from 'dayjs'
import 'dayjs/locale/es'

dayjs.locale('es')

// Estado
const orders = ref<Order[]>([])
const loading = ref(false)
const searchQuery = ref('')
const statusFilter = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const windowWidth = ref(window.innerWidth)
const detailsDialogVisible = ref(false)
const selectedOrder = ref<Order | null>(null)

// Estadísticas
const stats = ref({
  total: 0,
  pending: 0,
  confirmed: 0,
  shipped: 0,
  delivered: 0,
  cancelled: 0
})

// Computed
const isMobile = computed(() => windowWidth.value < 768)

const filteredOrders = computed(() => {
  let filtered = orders.value

  // Filtrar por búsqueda
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(order =>
      order.order_number.toLowerCase().includes(query) ||
      order.customer_name?.toLowerCase().includes(query) ||
      order.customer_phone?.includes(query)
    )
  }

  // Filtrar por estado
  if (statusFilter.value) {
    filtered = filtered.filter(order => order.status === statusFilter.value)
  }

  return filtered
})

const paginatedOrders = computed(() => {
  if (isMobile.value) {
    // En móvil, mostrar todos (o limitar a 50)
    return filteredOrders.value.slice(0, 50)
  }
  
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredOrders.value.slice(start, end)
})

// Métodos
const loadOrders = async () => {
  loading.value = true
  try {
    orders.value = await ordersApi.getOrders()
    await loadStats()
    ElMessage.success('Órdenes cargadas correctamente')
  } catch (error) {
    console.error('Error cargando órdenes:', error)
    ElMessage.error('Error al cargar las órdenes')
  } finally {
    loading.value = false
  }
}

const loadStats = async () => {
  try {
    stats.value = await ordersApi.getStats()
  } catch (error) {
    console.error('Error cargando estadísticas:', error)
  }
}

const showOrderDetails = (order: Order) => {
  selectedOrder.value = order
  detailsDialogVisible.value = true
}

const handleAction = async (command: string, order: Order) => {
  switch (command) {
    case 'ship':
      await updateStatus(order.id, 'shipped', 'Orden marcada como en camino')
      break
    case 'deliver':
      await updateStatus(order.id, 'delivered', 'Orden marcada como entregada')
      break
    case 'cancel':
      await cancelOrder(order)
      break
    case 'assign-driver':
      await assignDriver(order)
      break
    case 'delete':
      await deleteOrder(order)
      break
    case 'details':
      showOrderDetails(order)
      break
  }
}

const updateStatus = async (orderId: string, newStatus: string, successMessage: string) => {
  try {
    await ordersApi.updateOrderStatus(orderId, newStatus)
    ElMessage.success(successMessage)
    await loadOrders()
  } catch (error) {
    console.error('Error actualizando estado:', error)
    ElMessage.error('Error al actualizar el estado de la orden')
  }
}

const cancelOrder = async (order: Order) => {
  try {
    await ElMessageBox.confirm(
      `¿Estás seguro de cancelar la orden ${order.order_number}?\n\nEl stock de los productos será restaurado.`,
      'Confirmar Cancelación',
      {
        confirmButtonText: 'Sí, cancelar',
        cancelButtonText: 'No',
        type: 'warning'
      }
    )
    
    await ordersApi.cancelOrder(order.id)
    ElMessage.success('Orden cancelada correctamente. Stock restaurado.')
    await loadOrders()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Error cancelando orden:', error)
      const errorMessage = (error as any)?.response?.data?.detail || 'Error al cancelar la orden'
      ElMessage.error(errorMessage)
    }
  }
}

const assignDriver = async (order: Order) => {
  try {
    await ElMessageBox.confirm(
      `¿Asignar conductor a la orden ${order.order_number}?\n\nEsta funcionalidad estará disponible próximamente.`,
      'Asignar Conductor',
      {
        confirmButtonText: 'Continuar',
        cancelButtonText: 'Cancelar',
        type: 'info'
      }
    )
    
    const response = await ordersApi.assignDriver(order.id)
    ElMessage.info(response.message)
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Error asignando conductor:', error)
      const errorMessage = (error as any)?.response?.data?.detail || 'Error al asignar conductor'
      ElMessage.error(errorMessage)
    }
  }
}

const deleteOrder = async (order: Order) => {
  try {
    await ElMessageBox.confirm(
      `⚠️ ¿Estás seguro de ELIMINAR PERMANENTEMENTE la orden ${order.order_number}?\n\n` +
      `Esta acción NO se puede deshacer.\n\n` +
      `${order.status === 'confirmed' || order.status === 'shipped' ? '✅ El stock será restaurado automáticamente.' : ''}`,
      '🗑️ Eliminar Orden',
      {
        confirmButtonText: 'Sí, eliminar',
        cancelButtonText: 'Cancelar',
        type: 'error',
        confirmButtonClass: 'el-button--danger'
      }
    )
    
    const response = await ordersApi.deleteOrder(order.id)
    ElMessage.success(response.message)
    await loadOrders()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Error eliminando orden:', error)
      const errorMessage = (error as any)?.response?.data?.detail || 'Error al eliminar la orden'
      ElMessage.error(errorMessage)
    }
  }
}

// Utilidades
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

const getPaymentMethodLabel = (method: string) => {
  const labels: Record<string, string> = {
    efectivo: 'Efectivo',
    tarjeta: 'Tarjeta',
    transferencia: 'Transferencia'
  }
  return labels[method] || method
}

const formatDate = (date: string) => {
  return dayjs(date).format('DD/MM/YYYY')
}

const formatTime = (date: string) => {
  return dayjs(date).format('HH:mm:ss')
}

const formatPhone = (phone?: string) => {
  if (!phone) return '-'
  return phone.replace(/(\d{3})(\d{3})(\d{4})/, '($1) $2-$3')
}

const getItemsSummary = (items: any[]) => {
  if (items.length === 0) return ''
  if (items.length === 1) return items[0].product_name
  const first = items[0].product_name
  return `${first}, +${items.length - 1} más`
}

const calculateItemsTotal = (items: any[]) => {
  return items.reduce((sum, item) => sum + (item.unit_price * item.quantity), 0)
}

const handleResize = () => {
  windowWidth.value = window.innerWidth
}

// Lifecycle
onMounted(() => {
  loadOrders()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.orders-container {
  width: 100%;
}

.stat-card {
  height: 100%;
}

.mobile-view {
  display: flex;
  flex-direction: column;
}

.dialog-section {
  margin-bottom: 20px;
}

.dialog-section h4 {
  margin-bottom: 10px;
  color: #303133;
}

.item-detail {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #ebeef5;
}

.item-detail:last-child {
  border-bottom: none;
}

:deep(.el-table__expanded-cell) {
  background-color: #f5f7fa;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .orders-container {
    padding: 0;
  }
  
  :deep(.el-card) {
    margin-bottom: 12px;
  }
  
  :deep(.el-statistic__head) {
    font-size: 12px;
  }
  
  :deep(.el-statistic__number) {
    font-size: 20px;
  }
}

@media (max-width: 480px) {
  :deep(.el-statistic__number) {
    font-size: 18px;
  }
}
</style>
