<template>
  <div class="cart-item">
    <div class="item-image">
      <img
        :src="productImage"
        :alt="item.product.name"
        @error="handleImageError"
      />
    </div>

    <div class="item-details">
      <div class="item-header">
        <h4 class="item-name">{{ item.product.name }}</h4>
        <el-button
          type="danger"
          :icon="Delete"
          circle
          size="small"
          @click="handleRemove"
          class="remove-button"
        />
      </div>

      <p class="item-price">${{ item.product.price.toFixed(2) }} c/u</p>

      <div class="item-footer">
        <div class="quantity-controls">
          <el-button
            :icon="Minus"
            circle
            size="small"
            @click="handleDecrement"
            :disabled="item.quantity === 1"
          />
          
          <span class="quantity-display">{{ item.quantity }}</span>
          
          <el-button
            :icon="Plus"
            circle
            size="small"
            @click="handleIncrement"
            :disabled="item.quantity >= item.product.stock"
          />
        </div>

        <div class="item-subtotal">
          <span class="subtotal-label">Subtotal:</span>
          <span class="subtotal-value">${{ itemSubtotal.toFixed(2) }}</span>
        </div>
      </div>

      <p v-if="item.quantity >= item.product.stock" class="stock-warning">
        <el-icon><Warning /></el-icon>
        Stock máximo alcanzado
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Plus, Minus, Delete, Warning } from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'
import { cartAPI } from '@/services/api'
import type { CartItem as CartItemType } from '@/types'

interface Props {
  item: CartItemType
}

const props = defineProps<Props>()
const emit = defineEmits<{
  increment: []
  decrement: []
  remove: []
}>()

const imageError = ref(false)

const productImage = computed(() => {
  if (imageError.value) {
    return 'https://via.placeholder.com/80x80?text=N/A'
  }
  return cartAPI.getImageUrl(props.item.product.image_path)
})

const itemSubtotal = computed(() => {
  return props.item.product.price * props.item.quantity
})

function handleImageError() {
  imageError.value = true
}

function handleIncrement() {
  emit('increment')
}

function handleDecrement() {
  emit('decrement')
}

async function handleRemove() {
  try {
    await ElMessageBox.confirm(
      `¿Estás seguro de que quieres eliminar "${props.item.product.name}" del carrito?`,
      'Confirmar eliminación',
      {
        confirmButtonText: 'Sí, eliminar',
        cancelButtonText: 'Cancelar',
        type: 'warning'
      }
    )
    emit('remove')
  } catch {
    // Usuario canceló
  }
}
</script>

<style scoped>
.cart-item {
  display: flex;
  gap: 15px;
  padding: 15px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  background-color: #fafafa;
  transition: all 0.3s ease;
}

.cart-item:hover {
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.item-image {
  flex-shrink: 0;
  width: 80px;
  height: 80px;
  border-radius: 8px;
  overflow: hidden;
  background-color: #f5f7fa;
}

.item-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.item-details {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 10px;
}

.item-name {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin: 0;
  line-height: 1.3;
}

.remove-button {
  flex-shrink: 0;
}

.item-price {
  font-size: 14px;
  color: #909399;
  margin: 0;
}

.item-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: auto;
}

.quantity-controls {
  display: flex;
  align-items: center;
  gap: 10px;
}

.quantity-display {
  font-size: 16px;
  font-weight: 600;
  min-width: 30px;
  text-align: center;
}

.item-subtotal {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}

.subtotal-label {
  font-size: 12px;
  color: #909399;
}

.subtotal-value {
  font-size: 18px;
  font-weight: 700;
  color: #667eea;
}

.stock-warning {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: #e6a23c;
  margin: 0;
}

@media (max-width: 480px) {
  .cart-item {
    flex-direction: column;
  }

  .item-image {
    width: 100%;
    height: 150px;
  }

  .item-footer {
    flex-direction: column;
    align-items: stretch;
    gap: 15px;
  }

  .quantity-controls {
    justify-content: center;
  }

  .item-subtotal {
    align-items: center;
  }
}
</style>

