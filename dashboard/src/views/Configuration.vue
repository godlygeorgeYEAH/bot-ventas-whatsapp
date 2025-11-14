<template>
  <MainLayout>
    <div class="configuration-container">
      <!-- Header -->
      <el-card style="margin-bottom: 20px">
        <h2 style="margin: 0">
          <el-icon style="vertical-align: middle; margin-right: 8px"><Setting /></el-icon>
          Configuración del Sistema
        </h2>
      </el-card>

      <!-- Números de Administrador -->
      <el-card>
        <template #header>
          <div class="card-header">
            <h3 style="margin: 0">
              <el-icon style="vertical-align: middle; margin-right: 8px"><Phone /></el-icon>
              Números de Administrador
            </h3>
          </div>
        </template>

        <p style="color: #909399; margin-bottom: 20px">
          Los números de administrador tienen permisos especiales en el sistema.
          El número del bot es el administrador predeterminado.
        </p>

        <!-- Formulario para agregar número -->
        <el-form @submit.prevent="addAdminNumber" style="margin-bottom: 20px">
          <el-row :gutter="20" align="bottom">
            <el-col :xs="24" :sm="18" :md="20">
              <el-form-item label="Nuevo número de administrador">
                <el-input
                  v-model="newPhoneNumber"
                  placeholder="Ej: 15737457069"
                  :prefix-icon="Phone"
                  clearable
                  size="default"
                >
                  <template #prepend>+</template>
                </el-input>
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="6" :md="4">
              <el-button
                type="primary"
                :icon="Plus"
                @click="addAdminNumber"
                :loading="addingNumber"
                :disabled="!newPhoneNumber.trim()"
                style="width: 100%"
              >
                Agregar
              </el-button>
            </el-col>
          </el-row>
        </el-form>

        <!-- Lista de números -->
        <el-divider />

        <div v-if="loading" style="text-align: center; padding: 40px 0">
          <el-icon class="is-loading" :size="40"><Loading /></el-icon>
          <p style="margin-top: 10px; color: #909399">Cargando números...</p>
        </div>

        <div v-else-if="adminNumbers.length === 0" style="text-align: center; padding: 40px 0; color: #909399">
          <el-icon :size="60" style="margin-bottom: 10px"><User /></el-icon>
          <p>No hay números de administrador configurados</p>
        </div>

        <el-table v-else :data="adminNumbers" style="width: 100%" stripe>
          <el-table-column prop="index" label="#" width="60" align="center">
            <template #default="{ $index }">
              {{ $index + 1 }}
            </template>
          </el-table-column>

          <el-table-column label="Número de Teléfono">
            <template #default="{ row }">
              <el-icon style="margin-right: 8px; vertical-align: middle"><Phone /></el-icon>
              <span style="font-family: monospace; font-size: 15px">+{{ row }}</span>
            </template>
          </el-table-column>

          <el-table-column label="Acciones" width="120" align="center">
            <template #default="{ row }">
              <el-popconfirm
                title="¿Estás seguro de eliminar este número?"
                confirm-button-text="Sí"
                cancel-button-text="No"
                @confirm="removeAdminNumber(row)"
              >
                <template #reference>
                  <el-button
                    type="danger"
                    :icon="Delete"
                    size="small"
                    circle
                  />
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>

        <el-alert
          v-if="adminNumbers.length > 0"
          type="info"
          :closable="false"
          style="margin-top: 20px"
        >
          <template #title>
            <el-icon style="vertical-align: middle; margin-right: 4px"><InfoFilled /></el-icon>
            Total de administradores: {{ adminNumbers.length }}
          </template>
        </el-alert>
      </el-card>

      <!-- Timeout de Órdenes -->
      <el-card style="margin-top: 20px">
        <template #header>
          <div class="card-header">
            <h3 style="margin: 0">
              <el-icon style="vertical-align: middle; margin-right: 8px"><Clock /></el-icon>
              Timeout de Órdenes
            </h3>
          </div>
        </template>

        <p style="color: #909399; margin-bottom: 20px">
          Tiempo en minutos después del cual una orden pendiente se marca automáticamente como abandonada.
        </p>

        <el-form @submit.prevent="updateOrderTimeout">
          <el-row :gutter="20" align="bottom">
            <el-col :xs="24" :sm="12" :md="8">
              <el-form-item label="Timeout (minutos)">
                <el-input-number
                  v-model="orderTimeout"
                  :min="5"
                  :max="1440"
                  :step="5"
                  size="default"
                  style="width: 100%"
                  :disabled="loadingTimeout"
                />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12" :md="4">
              <el-button
                type="primary"
                @click="updateOrderTimeout"
                :loading="savingTimeout"
                :disabled="!orderTimeout || orderTimeout < 5 || orderTimeout > 1440"
                style="width: 100%"
              >
                Guardar
              </el-button>
            </el-col>
          </el-row>
        </el-form>

        <el-alert
          type="info"
          :closable="false"
          style="margin-top: 15px"
        >
          <template #title>
            <el-icon style="vertical-align: middle; margin-right: 4px"><InfoFilled /></el-icon>
            Rango permitido: 5 minutos (mínimo) - 1440 minutos / 24 horas (máximo)
          </template>
        </el-alert>

        <el-alert
          v-if="orderTimeout"
          type="success"
          :closable="false"
          style="margin-top: 15px"
        >
          <template #title>
            ⏰ Configuración actual: {{ orderTimeout }} minutos ({{ formatMinutes(orderTimeout) }})
          </template>
        </el-alert>
      </el-card>
    </div>
  </MainLayout>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Setting,
  Phone,
  Plus,
  Delete,
  Loading,
  User,
  InfoFilled,
  Clock
} from '@element-plus/icons-vue'
import MainLayout from '../layouts/MainLayout.vue'
import apiClient from '../api/client'

// Estado - Admin Numbers
const adminNumbers = ref<string[]>([])
const newPhoneNumber = ref('')
const loading = ref(false)
const addingNumber = ref(false)

// Estado - Order Timeout
const orderTimeout = ref<number>(30)
const loadingTimeout = ref(false)
const savingTimeout = ref(false)

// Cargar números de administrador
const loadAdminNumbers = async () => {
  try {
    loading.value = true
    const response = await apiClient.get('/api/settings/admin-numbers/list')
    adminNumbers.value = response.data
  } catch (error: any) {
    console.error('Error cargando números de admin:', error)
    ElMessage.error('Error al cargar los números de administrador')
  } finally {
    loading.value = false
  }
}

// Agregar número de administrador
const addAdminNumber = async () => {
  const phoneNumber = newPhoneNumber.value.trim()

  if (!phoneNumber) {
    ElMessage.warning('Por favor ingresa un número de teléfono')
    return
  }

  try {
    addingNumber.value = true

    const response = await apiClient.post('/api/settings/admin-numbers/add', {
      phone_number: phoneNumber
    })

    ElMessage.success(`Número ${phoneNumber} agregado exitosamente`)

    // Actualizar lista
    adminNumbers.value = response.data.admin_numbers

    // Limpiar input
    newPhoneNumber.value = ''
  } catch (error: any) {
    console.error('Error agregando número:', error)

    if (error.response?.status === 400) {
      ElMessage.error(error.response.data.detail || 'Este número ya existe')
    } else {
      ElMessage.error('Error al agregar el número de administrador')
    }
  } finally {
    addingNumber.value = false
  }
}

// Eliminar número de administrador
const removeAdminNumber = async (phoneNumber: string) => {
  try {
    const response = await apiClient.post('/api/settings/admin-numbers/remove', {
      phone_number: phoneNumber
    })

    ElMessage.success(`Número ${phoneNumber} eliminado exitosamente`)

    // Actualizar lista
    adminNumbers.value = response.data.admin_numbers
  } catch (error: any) {
    console.error('Error eliminando número:', error)

    if (error.response?.status === 404) {
      ElMessage.error('Este número no está en la lista')
    } else {
      ElMessage.error('Error al eliminar el número de administrador')
    }
  }
}

// ============================================
// Funciones de Order Timeout
// ============================================

// Cargar timeout de órdenes
const loadOrderTimeout = async () => {
  try {
    loadingTimeout.value = true
    const response = await apiClient.get('/api/settings/order-timeout/minutes')
    orderTimeout.value = response.data
  } catch (error: any) {
    console.error('Error cargando timeout:', error)
    ElMessage.error('Error al cargar el timeout de órdenes')
    // Usar default de 30 minutos
    orderTimeout.value = 30
  } finally {
    loadingTimeout.value = false
  }
}

// Actualizar timeout de órdenes
const updateOrderTimeout = async () => {
  if (!orderTimeout.value || orderTimeout.value < 5 || orderTimeout.value > 1440) {
    ElMessage.warning('El timeout debe estar entre 5 y 1440 minutos')
    return
  }

  try {
    savingTimeout.value = true

    await apiClient.put('/api/settings/order-timeout/minutes', {
      timeout_minutes: orderTimeout.value
    })

    ElMessage.success(`Timeout actualizado a ${orderTimeout.value} minutos`)
  } catch (error: any) {
    console.error('Error actualizando timeout:', error)

    if (error.response?.status === 400) {
      ElMessage.error(error.response.data.detail || 'Valor de timeout inválido')
    } else {
      ElMessage.error('Error al actualizar el timeout de órdenes')
    }
  } finally {
    savingTimeout.value = false
  }
}

// Formatear minutos a texto legible
const formatMinutes = (minutes: number): string => {
  if (minutes < 60) {
    return `${minutes} min`
  }

  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60

  if (mins === 0) {
    return `${hours} ${hours === 1 ? 'hora' : 'horas'}`
  }

  return `${hours}h ${mins}min`
}

// Cargar datos al montar el componente
onMounted(() => {
  loadAdminNumbers()
  loadOrderTimeout()
})
</script>

<style scoped>
.configuration-container {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.is-loading {
  animation: rotating 2s linear infinite;
}

@keyframes rotating {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 768px) {
  .configuration-container {
    padding: 10px;
  }
}
</style>
