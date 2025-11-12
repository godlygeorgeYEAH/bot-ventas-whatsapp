<template>
  <div class="cart-container">
    <!-- Loading State -->
    <div v-if="loading" class="loading-container">
      <el-icon class="is-loading" :size="50">
        <Loading />
      </el-icon>
      <p class="loading-text">Cargando tu carrito...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-container">
      <el-result icon="error" :title="errorTitle" :sub-title="errorMessage">
        <template #extra>
          <el-button type="primary" @click="retryLoad">Reintentar</el-button>
        </template>
      </el-result>
    </div>

    <!-- Success State (solo si ya NO es PENDING - no mostrar nada especial) -->
    <div v-else-if="orderCompleted && !hasPendingOrder" class="success-container">
      <el-result
        icon="success"
        title="¡Orden Recibida!"
        sub-title="Pronto recibirás un mensaje por WhatsApp para completar tu pedido con la ubicación GPS y método de pago."
      >
        <template #extra>
          <div class="success-info">
            <p><strong>Número de Orden:</strong> {{ completedOrderId }}</p>
            <p class="success-message">Gracias por tu compra!</p>
          </div>
        </template>
      </el-result>
    </div>

    <!-- Main Content -->
    <div v-else class="content">
      <!-- Header -->
      <div class="header">
        <div class="header-content">
          <div class="header-text">
            <h1 class="title">
              <el-icon><ShoppingCart /></el-icon>
              Carrito de Compras
            </h1>
            <p class="subtitle" v-if="hasPendingOrder">
              Modificando orden {{ completedOrderId }} • Puedes modificarla hasta que se procese tu pago
            </p>
            <p class="subtitle" v-else>Selecciona los productos que deseas ordenar</p>
          </div>
          <el-button v-if="hasPendingOrder" circle size="large" @click="closeCart">
            <el-icon><Close /></el-icon>
          </el-button>
        </div>
      </div>

      <!-- Products List (Full Width) -->
      <div class="products-section">
        <el-card class="section-card">
          <template #header>
            <div class="card-header">
              <span>Productos Disponibles</span>
              <el-tag>{{ products.length }} productos</el-tag>
            </div>
          </template>

          <div v-if="products.length === 0" class="empty-products">
            <el-empty description="No hay productos disponibles" />
          </div>

          <div v-else class="products-grid">
            <ProductCard
              v-for="product in products"
              :key="product.id"
              :product="product"
              :in-cart="isInCart(product.id)"
              @add-to-cart="handleAddToCart"
            />
          </div>
        </el-card>
      </div>

      <!-- Floating Cart Button -->
      <el-badge :value="cartStore.itemCount" :max="99" :hidden="cartStore.isEmpty" class="floating-cart-badge">
        <el-button
          type="primary"
          :icon="ShoppingBag"
          circle
          size="large"
          class="floating-cart-button"
          @click="drawerVisible = true"
        />
      </el-badge>

      <!-- Cart Drawer -->
      <el-drawer
        v-model="drawerVisible"
        title="Tu Carrito"
        :size="drawerSize"
        direction="rtl"
      >
        <template #header>
          <div class="drawer-header">
            <span class="drawer-title">Tu Carrito</span>
            <el-badge :value="cartStore.itemCount" :hidden="cartStore.isEmpty">
              <el-icon><ShoppingBag /></el-icon>
            </el-badge>
          </div>
        </template>

        <!-- Empty Cart -->
        <div v-if="cartStore.isEmpty" class="empty-cart">
          <el-empty description="Tu carrito está vacío">
            <el-button type="primary" @click="closeDrawerAndScroll">
              Ver Productos
            </el-button>
          </el-empty>
        </div>

        <!-- Cart Items -->
        <div v-else class="cart-content">
          <div class="cart-items">
            <CartItem
              v-for="item in cartStore.items"
              :key="item.product.id"
              :item="item"
              @increment="cartStore.incrementQuantity(item.product.id)"
              @decrement="cartStore.decrementQuantity(item.product.id)"
              @remove="cartStore.removeFromCart(item.product.id)"
            />
          </div>

          <!-- Cart Summary -->
          <el-divider />

          <div class="cart-summary">
            <div class="summary-row">
              <span>Subtotal:</span>
              <span class="summary-value">${{ cartStore.subtotal.toFixed(2) }}</span>
            </div>
            <div class="summary-row total">
              <span>Total:</span>
              <span class="summary-value">${{ cartStore.subtotal.toFixed(2) }}</span>
            </div>
          </div>

          <!-- Complete Order Button -->
          <el-button
            type="primary"
            size="large"
            :loading="completing"
            :disabled="cartStore.isEmpty"
            @click="completeOrder"
            class="complete-button"
          >
            <el-icon><Check /></el-icon>
            Marcar como Lista
          </el-button>
        </div>
      </el-drawer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Loading, ShoppingCart, ShoppingBag, Check, Close } from '@element-plus/icons-vue'
import { useCartStore } from '@/stores/cart'
import { cartAPI } from '@/services/api'
import type { Product } from '@/types'
import ProductCard from '@/components/ProductCard.vue'
import CartItem from '@/components/CartItem.vue'

const route = useRoute()
const cartStore = useCartStore()

const loading = ref(true)
const error = ref(false)
const errorTitle = ref('')
const errorMessage = ref('')
const products = ref<Product[]>([])
const completing = ref(false)
const orderCompleted = ref(false)
const completedOrderId = ref('')
const drawerVisible = ref(false)
const hasPendingOrder = ref(false)
const lastConfirmTime = ref<number>(0)
const confirmCooldown = ref(false)

const token = route.params.token as string

// Tamaño responsivo del drawer
const drawerSize = computed(() => {
  if (typeof window !== 'undefined') {
    return window.innerWidth < 768 ? '100%' : '450px'
  }
  return '450px'
})

onMounted(async () => {
  await loadCart()
})

async function loadCart() {
  loading.value = true
  error.value = false

  try {
    // Validar token
    const session = await cartAPI.validateSession(token)

    if (!session.valid) {
      error.value = true
      errorTitle.value = 'Link Inválido'
      
      if (session.error === 'token_expired') {
        errorMessage.value = 'Este link ha expirado. Por favor solicita uno nuevo.'
      } else if (session.error === 'token_already_used') {
        errorMessage.value = 'Este link ya fue usado. Si necesitas hacer otra orden, solicita un nuevo link.'
      } else {
        errorMessage.value = session.message || 'Este link no es válido.'
      }
      
      loading.value = false
      return
    }

    // Cargar productos
    const productsData = await cartAPI.getProducts(token)
    products.value = productsData

    cartStore.setToken(token)
    cartStore.setSessionValid(true)
    
    // Cargar orden PENDING si existe
    try {
      const pendingOrderData = await cartAPI.getPendingOrder(token)
      
      if (pendingOrderData.has_pending_order) {
        hasPendingOrder.value = true
        completedOrderId.value = pendingOrderData.order.order_number
        
        // Cargar items al carrito
        for (const item of pendingOrderData.order.items) {
          const product = products.value.find(p => p.id === item.product_id)
          if (product) {
            cartStore.addToCart(product, item.quantity)
          }
        }
        
        ElMessage.info('Continúa modificando tu orden pendiente')
      }
    } catch (pendingErr) {
      console.log('No hay orden pendiente, iniciando nueva orden')
    }

  } catch (err: any) {
    error.value = true
    errorTitle.value = 'Error de Conexión'
    errorMessage.value = err.response?.data?.detail || 'No se pudo conectar con el servidor. Por favor intenta de nuevo.'
  } finally {
    loading.value = false
  }
}

function retryLoad() {
  loadCart()
}

function isInCart(productId: string): boolean {
  return cartStore.items.some(item => item.product.id === productId)
}

function handleAddToCart(product: Product) {
  cartStore.addToCart(product)
  ElMessage.success(`${product.name} agregado al carrito`)
}

function scrollToProducts() {
  const productsSection = document.querySelector('.products-section')
  productsSection?.scrollIntoView({ behavior: 'smooth' })
}

function closeDrawerAndScroll() {
  drawerVisible.value = false
  setTimeout(() => {
    scrollToProducts()
  }, 300)
}

function closeCart() {
  ElMessage.info('Tu orden sigue pendiente. Puedes volver a modificarla cuando quieras.')
  window.close()
}

async function completeOrder() {
  if (cartStore.isEmpty) {
    ElMessage.warning('Tu carrito está vacío')
    return
  }

  // Rate limiting: solo permitir confirmar cada 30 segundos
  const now = Date.now()
  const timeSinceLastConfirm = now - lastConfirmTime.value
  
  if (timeSinceLastConfirm < 30000 && lastConfirmTime.value > 0) {
    const remainingSeconds = Math.ceil((30000 - timeSinceLastConfirm) / 1000)
    ElMessage.warning(`Espera ${remainingSeconds} segundos antes de confirmar nuevamente`)
    return
  }

  try {
    const confirmMessage = hasPendingOrder.value
      ? '¿Confirmar los cambios de tu orden?'
      : '¿Estás seguro de que quieres confirmar tu orden? Recibirás un mensaje por WhatsApp para completar los datos de entrega.'

    await ElMessageBox.confirm(
      confirmMessage,
      'Confirmar Orden',
      {
        confirmButtonText: 'Sí, Confirmar',
        cancelButtonText: 'Cancelar',
        type: 'warning'
      }
    )

    completing.value = true
    confirmCooldown.value = true

    const cartData = cartStore.getCartData()
    const total = cartStore.subtotal

    const response = await cartAPI.completeCart(token, {
      products: cartData,
      total
    })

    if (response.success) {
      completedOrderId.value = response.order_id || 'N/A'
      lastConfirmTime.value = now
      
      if (!hasPendingOrder.value) {
        // Primera confirmación
        hasPendingOrder.value = true
        orderCompleted.value = true
        ElMessage.success('¡Orden confirmada! Puedes seguir editándola mientras esté pendiente.')
      } else {
        // Modificación
        ElMessage.success('Cambios guardados exitosamente')
      }
    } else {
      throw new Error(response.error || 'Error al completar la orden')
    }

  } catch (err: any) {
    if (err !== 'cancel') {
      ElMessage.error(err.message || 'Error al completar la orden')
    }
  } finally {
    completing.value = false
  }
}
</script>

<style scoped>
.cart-container {
  min-height: 100vh;
  padding: 20px;
  padding-bottom: 80px; /* Espacio para el botón flotante */
}

.loading-container,
.error-container,
.success-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 80vh;
}

.loading-text {
  margin-top: 20px;
  font-size: 18px;
  color: white;
}

.content {
  max-width: 1400px;
  margin: 0 auto;
}

.header {
  text-align: center;
  margin-bottom: 30px;
  color: white;
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  max-width: 800px;
  margin: 0 auto;
}

.header-text {
  flex: 1;
  text-align: center;
}

.title {
  font-size: 36px;
  font-weight: 700;
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
}

.subtitle {
  font-size: 18px;
  opacity: 0.9;
}

.products-section {
  width: 100%;
}

.section-card {
  height: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.products-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

@media (max-width: 768px) {
  .products-grid {
    grid-template-columns: 1fr;
  }
  
  .title {
    font-size: 28px;
  }
  
  .subtitle {
    font-size: 16px;
  }
}

.empty-products,
.empty-cart {
  padding: 40px 20px;
  text-align: center;
}

/* Floating Cart Button */
.floating-cart-badge {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 1000;
  animation: fadeIn 0.3s ease-in-out;
}

.floating-cart-button {
  width: 60px;
  height: 60px;
  font-size: 24px;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
  transition: all 0.3s ease;
}

.floating-cart-button:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
}

.floating-cart-button:active {
  transform: translateY(-1px);
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: scale(0.8);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

/* Mobile adjustments */
@media (max-width: 768px) {
  .floating-cart-badge {
    top: 10px;
    right: 10px;
  }
  
  .floating-cart-button {
    width: 55px;
    height: 55px;
    font-size: 20px;
  }
}

/* Drawer Header */
.drawer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.drawer-title {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

/* Cart Content */
.cart-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 0 5px;
}

.cart-items {
  display: flex;
  flex-direction: column;
  gap: 15px;
  max-height: calc(100vh - 400px);
  overflow-y: auto;
  padding-right: 5px;
}

/* Custom scrollbar for cart items */
.cart-items::-webkit-scrollbar {
  width: 6px;
}

.cart-items::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 10px;
}

.cart-items::-webkit-scrollbar-thumb {
  background: #667eea;
  border-radius: 10px;
}

.cart-items::-webkit-scrollbar-thumb:hover {
  background: #5568d3;
}

.cart-summary {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 15px;
  background-color: #f5f7fa;
  border-radius: 8px;
}

.summary-row {
  display: flex;
  justify-content: space-between;
  font-size: 16px;
}

.summary-row.total {
  font-size: 20px;
  font-weight: 700;
  color: #667eea;
  padding-top: 10px;
  border-top: 2px solid #dcdfe6;
}

.summary-value {
  font-weight: 600;
}

.complete-button {
  width: 100%;
  height: 50px;
  font-size: 18px;
  font-weight: 600;
}

.success-info {
  text-align: center;
  font-size: 16px;
}

.success-info p {
  margin: 10px 0;
}

.success-message {
  font-size: 18px;
  color: #67c23a;
  font-weight: 600;
  margin-top: 20px !important;
}

/* Badge personalizado */
:deep(.el-badge__content) {
  font-weight: 700;
  font-size: 12px;
}

/* Drawer responsive */
@media (max-width: 768px) {
  .cart-items {
    max-height: calc(100vh - 350px);
  }
}
</style>

