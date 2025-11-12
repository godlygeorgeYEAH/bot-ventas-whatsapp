<template>
  <el-card class="product-card" :class="{ 'in-cart': inCart }" shadow="hover">
    <div class="product-image-container">
      <img
        :src="productImage"
        :alt="product.name"
        class="product-image"
        @error="handleImageError"
      />
      <el-tag v-if="inCart" class="in-cart-badge" type="success">
        <el-icon><Check /></el-icon>
        En el carrito
      </el-tag>
      <el-tag v-if="product.stock <= 5" class="low-stock-badge" type="warning">
        ¡Solo {{ product.stock }} disponibles!
      </el-tag>
    </div>

    <div class="product-info">
      <h3 class="product-name">{{ product.name }}</h3>
      
      <p v-if="product.description" class="product-description">
        {{ truncatedDescription }}
      </p>

      <div class="product-meta">
        <el-tag v-if="product.category" size="small" type="info">
          {{ product.category }}
        </el-tag>
        <el-tag v-if="product.sku" size="small" type="">
          SKU: {{ product.sku }}
        </el-tag>
      </div>

      <div class="product-footer">
        <div class="price-section">
          <span class="price">${{ product.price.toFixed(2) }}</span>
          <span class="stock-info">Stock: {{ product.stock }}</span>
        </div>

        <el-button
          type="primary"
          :disabled="product.stock === 0 || inCart"
          @click="addToCart"
          class="add-button"
        >
          <el-icon><Plus /></el-icon>
          {{ inCart ? 'En Carrito' : 'Agregar' }}
        </el-button>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Plus, Check } from '@element-plus/icons-vue'
import { cartAPI } from '@/services/api'
import type { Product } from '@/types'

interface Props {
  product: Product
  inCart: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{
  addToCart: [product: Product]
}>()

const imageError = ref(false)

const productImage = computed(() => {
  if (imageError.value) {
    return 'https://via.placeholder.com/300x200?text=Sin+Imagen'
  }
  return cartAPI.getImageUrl(props.product.image_path)
})

const truncatedDescription = computed(() => {
  if (!props.product.description) return ''
  return props.product.description.length > 100
    ? props.product.description.substring(0, 100) + '...'
    : props.product.description
})

function handleImageError() {
  imageError.value = true
}

function addToCart() {
  emit('addToCart', props.product)
}
</script>

<style scoped>
.product-card {
  display: flex;
  flex-direction: column;
  height: 100%;
  transition: transform 0.3s ease;
}

.product-card:hover {
  transform: translateY(-5px);
}

.product-card.in-cart {
  border: 2px solid #67c23a;
}

.product-image-container {
  position: relative;
  width: 100%;
  height: 200px;
  overflow: hidden;
  background-color: #f5f7fa;
  border-radius: 4px;
  margin-bottom: 15px;
}

.product-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.in-cart-badge {
  position: absolute;
  top: 10px;
  right: 10px;
}

.low-stock-badge {
  position: absolute;
  bottom: 10px;
  left: 10px;
}

.product-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.product-name {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  margin: 0;
  line-height: 1.3;
}

.product-description {
  font-size: 14px;
  color: #606266;
  margin: 0;
  line-height: 1.5;
}

.product-meta {
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
}

.product-footer {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-top: auto;
  padding-top: 15px;
  border-top: 1px solid #ebeef5;
}

.price-section {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.price {
  font-size: 24px;
  font-weight: 700;
  color: #667eea;
}

.stock-info {
  font-size: 12px;
  color: #909399;
}

.add-button {
  flex-shrink: 0;
}
</style>

