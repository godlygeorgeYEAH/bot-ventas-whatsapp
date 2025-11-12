<template>
  <div class="products-container">
    <el-page-header @back="$router.push('/dashboard')" content="Gestión de Productos" />

    <!-- KPIs -->
    <div class="kpis-container">
      <el-card class="kpi-card">
        <div class="kpi-content">
          <el-icon class="kpi-icon" color="#409EFF"><Box /></el-icon>
          <div>
            <div class="kpi-value">{{ stats.total }}</div>
            <div class="kpi-label">Total Productos</div>
          </div>
        </div>
      </el-card>

      <el-card class="kpi-card">
        <div class="kpi-content">
          <el-icon class="kpi-icon" color="#67C23A"><CircleCheck /></el-icon>
          <div>
            <div class="kpi-value">{{ stats.active }}</div>
            <div class="kpi-label">Activos</div>
          </div>
        </div>
      </el-card>

      <el-card class="kpi-card">
        <div class="kpi-content">
          <el-icon class="kpi-icon" color="#F56C6C"><CircleClose /></el-icon>
          <div>
            <div class="kpi-value">{{ stats.out_of_stock }}</div>
            <div class="kpi-label">Sin Stock</div>
          </div>
        </div>
      </el-card>

      <el-card class="kpi-card">
        <div class="kpi-content">
          <el-icon class="kpi-icon" color="#E6A23C"><Warning /></el-icon>
          <div>
            <div class="kpi-value">{{ stats.low_stock }}</div>
            <div class="kpi-label">Stock Bajo</div>
          </div>
        </div>
      </el-card>
    </div>

    <!-- Filtros y Búsqueda -->
    <el-card class="filters-card">
      <div class="filters-container">
        <div class="filters-row">
          <el-input
            v-model="searchQuery"
            placeholder="Buscar por nombre, descripción o SKU..."
            :prefix-icon="Search"
            clearable
            @input="handleSearch"
            style="flex: 1; min-width: 200px;"
          />

          <el-select
            v-model="selectedCategory"
            placeholder="Categoría"
            clearable
            @change="loadProducts"
            style="width: 180px;"
          >
            <el-option label="Todas las categorías" value="" />
            <el-option
              v-for="cat in categories"
              :key="cat"
              :label="cat"
              :value="cat"
            />
          </el-select>

          <el-select
            v-model="selectedStatus"
            placeholder="Estado"
            @change="loadProducts"
            style="width: 150px;"
          >
            <el-option label="Todos" value="all" />
            <el-option label="Activos" value="active" />
            <el-option label="Inactivos" value="inactive" />
            <el-option label="Con Stock" value="in_stock" />
            <el-option label="Sin Stock" value="out_of_stock" />
          </el-select>

          <el-button type="primary" :icon="Plus" @click="openCreateDialog">
            Nuevo Producto
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- Tabla de Productos (Desktop) -->
    <el-card v-if="!isMobile" class="table-card">
      <el-table
        v-loading="loading"
        :data="products"
        style="width: 100%"
        :default-sort="{ prop: 'name', order: 'ascending' }"
      >
        <el-table-column label="Imagen" width="80" align="center">
          <template #default="{ row }">
            <div class="product-image-cell">
              <img
                v-if="row.image_path"
                :src="getImageUrl(row.image_path)"
                :alt="row.name"
                class="table-product-image"
              />
              <el-icon v-else class="no-image-icon" :size="32" color="#C0C4CC">
                <Picture />
              </el-icon>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="name" label="Producto" min-width="200" sortable>
          <template #default="{ row }">
            <div style="display: flex; align-items: center; gap: 8px;">
              <el-tag v-if="!row.is_active" type="info" size="small">Inactivo</el-tag>
              <span :style="{ fontWeight: 500, color: row.is_active ? '#303133' : '#909399' }">
                {{ row.name }}
              </span>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="category" label="Categoría" width="150" sortable>
          <template #default="{ row }">
            <el-tag v-if="row.category" size="small">{{ row.category }}</el-tag>
            <span v-else style="color: #C0C4CC;">Sin categoría</span>
          </template>
        </el-table-column>

        <el-table-column prop="sku" label="SKU" width="120">
          <template #default="{ row }">
            <span style="font-family: monospace; font-size: 12px;">{{ row.sku || '-' }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="price" label="Precio" width="120" sortable align="right">
          <template #default="{ row }">
            <span style="font-weight: 600; color: #67C23A;">${{ row.price.toFixed(2) }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="stock" label="Stock" width="100" sortable align="center">
          <template #default="{ row }">
            <el-tag
              :type="row.stock === 0 ? 'danger' : row.stock < 10 ? 'warning' : 'success'"
              size="small"
            >
              {{ row.stock }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="Estado" width="100" align="center">
          <template #default="{ row }">
            <el-switch
              v-model="row.is_active"
              @change="toggleProductActive(row)"
              active-color="#67C23A"
              inactive-color="#C0C4CC"
            />
          </template>
        </el-table-column>

        <el-table-column label="Acciones" width="180" fixed="right">
          <template #default="{ row }">
            <div style="display: flex; gap: 4px;">
              <el-button
                type="primary"
                size="small"
                :icon="Edit"
                @click="openEditDialog(row)"
                circle
              />
              <el-button
                type="warning"
                size="small"
                :icon="Box"
                @click="openStockDialog(row)"
                circle
              />
              <el-button
                type="danger"
                size="small"
                :icon="Delete"
                @click="confirmDelete(row)"
                circle
              />
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Vista Móvil (Cards) -->
    <div v-else class="mobile-products">
      <el-card
        v-for="product in products"
        :key="product.id"
        class="product-card-mobile"
        shadow="hover"
      >
        <div class="product-header">
          <div class="product-image-mobile">
            <img
              v-if="product.image_path"
              :src="getImageUrl(product.image_path)"
              :alt="product.name"
            />
            <el-icon v-else :size="48" color="#C0C4CC">
              <Picture />
            </el-icon>
          </div>

          <div class="product-title">
            <el-tag v-if="!product.is_active" type="info" size="small">Inactivo</el-tag>
            <h3>{{ product.name }}</h3>
          </div>
          <el-switch
            v-model="product.is_active"
            @change="toggleProductActive(product)"
            size="small"
          />
        </div>

        <div class="product-info">
          <div class="info-row">
            <span class="label">Categoría:</span>
            <el-tag v-if="product.category" size="small">{{ product.category }}</el-tag>
            <span v-else style="color: #C0C4CC;">Sin categoría</span>
          </div>

          <div class="info-row">
            <span class="label">SKU:</span>
            <span style="font-family: monospace;">{{ product.sku || '-' }}</span>
          </div>

          <div class="info-row">
            <span class="label">Precio:</span>
            <span class="price">${{ product.price.toFixed(2) }}</span>
          </div>

          <div class="info-row">
            <span class="label">Stock:</span>
            <el-tag
              :type="product.stock === 0 ? 'danger' : product.stock < 10 ? 'warning' : 'success'"
              size="small"
            >
              {{ product.stock }} unidades
            </el-tag>
          </div>
        </div>

        <div class="product-actions">
          <el-button type="primary" size="small" :icon="Edit" @click="openEditDialog(product)">
            Editar
          </el-button>
          <el-button type="warning" size="small" :icon="Box" @click="openStockDialog(product)">
            Stock
          </el-button>
          <el-button type="danger" size="small" :icon="Delete" @click="confirmDelete(product)">
            Eliminar
          </el-button>
        </div>
      </el-card>
    </div>

    <!-- Dialog: Crear/Editar Producto -->
    <el-dialog
      v-model="dialogVisible"
      :title="editMode ? 'Editar Producto' : 'Nuevo Producto'"
      width="90%"
      :style="{ maxWidth: '600px' }"
    >
      <el-form
        ref="productFormRef"
        :model="productForm"
        :rules="formRules"
        label-position="top"
      >
        <el-form-item label="Nombre del Producto" prop="name">
          <el-input v-model="productForm.name" placeholder="Ej: Laptop Dell XPS 13" />
        </el-form-item>

        <el-form-item label="Descripción" prop="description">
          <el-input
            v-model="productForm.description"
            type="textarea"
            :rows="3"
            placeholder="Descripción detallada del producto..."
          />
        </el-form-item>

        <el-row :gutter="16">
          <el-col :xs="24" :sm="12">
            <el-form-item label="Precio (USD)" prop="price">
              <el-input-number
                v-model="productForm.price"
                :min="0.01"
                :step="0.01"
                :precision="2"
                style="width: 100%;"
              />
            </el-form-item>
          </el-col>

          <el-col :xs="24" :sm="12">
            <el-form-item label="Stock" prop="stock">
              <el-input-number
                v-model="productForm.stock"
                :min="0"
                :step="1"
                style="width: 100%;"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :xs="24" :sm="12">
            <el-form-item label="Categoría" prop="category">
              <el-select
                v-model="productForm.category"
                filterable
                allow-create
                placeholder="Seleccionar o crear categoría"
                style="width: 100%;"
              >
                <el-option
                  v-for="cat in categories"
                  :key="cat"
                  :label="cat"
                  :value="cat"
                />
              </el-select>
            </el-form-item>
          </el-col>

          <el-col :xs="24" :sm="12">
            <el-form-item label="SKU (Opcional)" prop="sku">
              <el-input v-model="productForm.sku" placeholder="Ej: LAP-DELL-001" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="Estado">
          <el-switch
            v-model="productForm.is_active"
            active-text="Activo"
            inactive-text="Inactivo"
          />
        </el-form-item>

        <!-- Upload de Imagen -->
        <el-form-item label="Imagen del Producto">
          <div class="image-upload-section">
            <!-- Preview de imagen actual -->
            <div v-if="currentImageUrl" class="image-preview">
              <img :src="apiBaseUrl + currentImageUrl" alt="Producto" />
              <el-button
                type="danger"
                size="small"
                :icon="Delete"
                circle
                @click="removeImage"
                class="delete-image-btn"
              />
            </div>

            <!-- Botón de subir imagen -->
            <el-upload
              v-if="!currentImageUrl"
              class="image-uploader"
              :auto-upload="false"
              :show-file-list="false"
              :on-change="handleImageChange"
              accept="image/jpeg,image/jpg,image/png,image/gif,image/webp"
              drag
            >
              <el-icon class="el-icon--upload"><Plus /></el-icon>
              <div class="el-upload__text">
                Arrastra una imagen aquí o <em>click para subir</em>
              </div>
              <template #tip>
                <div class="el-upload__tip">
                  JPG, PNG, GIF o WEBP. Máximo 5MB.
                </div>
              </template>
            </el-upload>

            <!-- Preview de nueva imagen seleccionada -->
            <div v-if="imagePreview && !currentImageUrl" class="image-preview">
              <img :src="imagePreview" alt="Preview" />
              <el-button
                type="danger"
                size="small"
                :icon="Delete"
                circle
                @click="clearImagePreview"
                class="delete-image-btn"
              />
            </div>
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">Cancelar</el-button>
        <el-button type="primary" :loading="saving" @click="saveProduct">
          {{ editMode ? 'Actualizar' : 'Crear' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- Dialog: Ajustar Stock -->
    <el-dialog
      v-model="stockDialogVisible"
      title="Ajustar Stock"
      width="90%"
      :style="{ maxWidth: '400px' }"
    >
      <div style="margin-bottom: 16px;">
        <strong>Producto:</strong> {{ selectedProduct?.name }}
      </div>
      <div style="margin-bottom: 16px;">
        <strong>Stock Actual:</strong>
        <el-tag :type="selectedProduct?.stock === 0 ? 'danger' : selectedProduct?.stock < 10 ? 'warning' : 'success'">
          {{ selectedProduct?.stock }}
        </el-tag>
      </div>

      <el-form-item label="Nuevo Stock">
        <el-input-number
          v-model="newStock"
          :min="0"
          :step="1"
          style="width: 100%;"
        />
      </el-form-item>

      <template #footer>
        <el-button @click="stockDialogVisible = false">Cancelar</el-button>
        <el-button type="primary" :loading="saving" @click="saveStock">
          Actualizar Stock
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import {
  Box,
  CircleCheck,
  CircleClose,
  Warning,
  Search,
  Plus,
  Edit,
  Delete,
  Picture
} from '@element-plus/icons-vue'
import type { UploadProps, UploadFile } from 'element-plus'
import {
  getProducts,
  getProductStats,
  getCategories,
  createProduct,
  updateProduct,
  deleteProduct,
  updateStock as updateStockApi,
  toggleActive,
  uploadProductImage,
  deleteProductImage,
  type Product,
  type ProductCreate,
  type ProductUpdate,
  type ProductStats
} from '../api/products'

const router = useRouter()

// Estado
const loading = ref(false)
const saving = ref(false)
const products = ref<Product[]>([])
const stats = ref<ProductStats>({
  total: 0,
  active: 0,
  inactive: 0,
  out_of_stock: 0,
  low_stock: 0,
  categories: 0
})
const categories = ref<string[]>([])

// Filtros
const searchQuery = ref('')
const selectedCategory = ref('')
const selectedStatus = ref('all')
let searchTimeout: any = null

// Diálogo de producto
const dialogVisible = ref(false)
const editMode = ref(false)
const productFormRef = ref<FormInstance>()
const selectedProduct = ref<Product | null>(null)

const productForm = reactive<ProductCreate>({
  name: '',
  description: '',
  price: 0,
  stock: 0,
  category: '',
  sku: '',
  is_active: true
})

const formRules: FormRules = {
  name: [
    { required: true, message: 'El nombre es requerido', trigger: 'blur' },
    { min: 1, max: 200, message: 'El nombre debe tener entre 1 y 200 caracteres', trigger: 'blur' }
  ],
  price: [
    { required: true, message: 'El precio es requerido', trigger: 'blur' },
    { type: 'number', min: 0.01, message: 'El precio debe ser mayor a 0', trigger: 'blur' }
  ],
  stock: [
    { required: true, message: 'El stock es requerido', trigger: 'blur' },
    { type: 'number', min: 0, message: 'El stock debe ser mayor o igual a 0', trigger: 'blur' }
  ]
}

// Diálogo de stock
const stockDialogVisible = ref(false)
const newStock = ref(0)

// Manejo de imágenes
const selectedImageFile = ref<File | null>(null)
const imagePreview = ref<string | null>(null)
const currentImageUrl = ref<string | null>(null)
const apiBaseUrl = import.meta.env.VITE_API_URL || 'http://192.168.68.101:8000'

// Responsive
const windowWidth = ref(window.innerWidth)
const isMobile = computed(() => windowWidth.value <= 768)

// Lifecycle
onMounted(() => {
  loadProducts()
  loadStats()
  loadCategories()

  window.addEventListener('resize', () => {
    windowWidth.value = window.innerWidth
  })
})

// Métodos
const loadProducts = async () => {
  try {
    loading.value = true

    const params: any = {
      search: searchQuery.value || undefined,
      category: selectedCategory.value || undefined
    }

    // Filtro de estado
    if (selectedStatus.value === 'active') {
      params.is_active = true
    } else if (selectedStatus.value === 'inactive') {
      params.is_active = false
    } else if (selectedStatus.value === 'in_stock') {
      params.in_stock = true
    } else if (selectedStatus.value === 'out_of_stock') {
      params.in_stock = false
    }

    products.value = await getProducts(params)
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || 'Error al cargar productos')
    console.error('Error cargando productos:', error)
  } finally {
    loading.value = false
  }
}

const loadStats = async () => {
  try {
    stats.value = await getProductStats()
  } catch (error) {
    console.error('Error cargando estadísticas:', error)
  }
}

const loadCategories = async () => {
  try {
    const response = await getCategories()
    categories.value = response.categories
  } catch (error) {
    console.error('Error cargando categorías:', error)
  }
}

const handleSearch = () => {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    loadProducts()
  }, 500)
}

const openCreateDialog = () => {
  editMode.value = false
  selectedProduct.value = null
  Object.assign(productForm, {
    name: '',
    description: '',
    price: 0,
    stock: 0,
    category: '',
    sku: '',
    is_active: true
  })
  // Limpiar imagen
  currentImageUrl.value = null
  clearImagePreview()
  dialogVisible.value = true
}

const openEditDialog = (product: Product) => {
  editMode.value = true
  selectedProduct.value = product
  Object.assign(productForm, {
    name: product.name,
    description: product.description || '',
    price: product.price,
    stock: product.stock,
    category: product.category || '',
    sku: product.sku || '',
    is_active: product.is_active
  })
  // Cargar imagen actual
  if (product.image_path) {
    currentImageUrl.value = getImageUrl(product.image_path)
  } else {
    currentImageUrl.value = null
  }
  clearImagePreview()
  dialogVisible.value = true
}

const saveProduct = async () => {
  if (!productFormRef.value) return

  await productFormRef.value.validate(async (valid) => {
    if (!valid) return

    try {
      saving.value = true

      let productId: string

      if (editMode.value && selectedProduct.value) {
        // Actualizar
        await updateProduct(selectedProduct.value.id, productForm as ProductUpdate)
        productId = selectedProduct.value.id
        ElMessage.success('Producto actualizado exitosamente')
      } else {
        // Crear
        const newProduct = await createProduct(productForm)
        productId = newProduct.id
        ElMessage.success('Producto creado exitosamente')
      }

      // Subir imagen si hay una seleccionada
      if (selectedImageFile.value) {
        try {
          await uploadImage(productId)
        } catch (imgError) {
          // Si falla la imagen, el producto ya se guardó
          console.error('Error subiendo imagen:', imgError)
        }
      }

      dialogVisible.value = false
      loadProducts()
      loadStats()
      loadCategories()
    } catch (error: any) {
      ElMessage.error(error.response?.data?.detail || 'Error al guardar producto')
      console.error('Error guardando producto:', error)
    } finally {
      saving.value = false
    }
  })
}

const toggleProductActive = async (product: Product) => {
  try {
    await toggleActive(product.id)
    ElMessage.success(`Producto ${product.is_active ? 'activado' : 'desactivado'} exitosamente`)
    loadStats()
  } catch (error: any) {
    // Revertir cambio en UI si falla
    product.is_active = !product.is_active
    ElMessage.error(error.response?.data?.detail || 'Error al cambiar estado del producto')
    console.error('Error cambiando estado:', error)
  }
}

const openStockDialog = (product: Product) => {
  selectedProduct.value = product
  newStock.value = product.stock
  stockDialogVisible.value = true
}

const saveStock = async () => {
  if (!selectedProduct.value) return

  try {
    saving.value = true
    await updateStockApi(selectedProduct.value.id, newStock.value)
    ElMessage.success('Stock actualizado exitosamente')
    stockDialogVisible.value = false
    loadProducts()
    loadStats()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || 'Error al actualizar stock')
    console.error('Error actualizando stock:', error)
  } finally {
    saving.value = false
  }
}

const confirmDelete = async (product: Product) => {
  try {
    await ElMessageBox.confirm(
      `¿Estás seguro de eliminar el producto "${product.name}"? Esta acción no se puede deshacer.`,
      'Confirmar Eliminación',
      {
        confirmButtonText: 'Eliminar',
        cancelButtonText: 'Cancelar',
        type: 'warning'
      }
    )

    await deleteProduct(product.id)
    ElMessage.success('Producto eliminado exitosamente')
    loadProducts()
    loadStats()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || 'Error al eliminar producto')
      console.error('Error eliminando producto:', error)
    }
  }
}

// Métodos de manejo de imágenes
const getImageUrl = (imagePath: string) => {
  if (!imagePath) return ''
  // Extraer solo el nombre del archivo
  const filename = imagePath.split(/[\\\/]/).pop()
  return `${apiBaseUrl}/static/products/${filename}`
}

const handleImageChange = (uploadFile: UploadFile) => {
  const file = uploadFile.raw
  if (!file) return

  // Validar tamaño (5MB)
  if (file.size > 5 * 1024 * 1024) {
    ElMessage.error('El archivo es demasiado grande. Máximo 5MB.')
    return
  }

  // Validar tipo
  if (!file.type.startsWith('image/')) {
    ElMessage.error('Solo se permiten imágenes')
    return
  }

  selectedImageFile.value = file

  // Crear preview
  const reader = new FileReader()
  reader.onload = (e) => {
    imagePreview.value = e.target?.result as string
  }
  reader.readAsDataURL(file)
}

const clearImagePreview = () => {
  selectedImageFile.value = null
  imagePreview.value = null
}

const removeImage = async () => {
  if (!selectedProduct.value) return

  try {
    await ElMessageBox.confirm(
      '¿Estás seguro de eliminar la imagen de este producto?',
      'Confirmar',
      {
        confirmButtonText: 'Eliminar',
        cancelButtonText: 'Cancelar',
        type: 'warning'
      }
    )

    await deleteProductImage(selectedProduct.value.id)
    currentImageUrl.value = null
    ElMessage.success('Imagen eliminada exitosamente')
    loadProducts()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || 'Error al eliminar imagen')
    }
  }
}

const uploadImage = async (productId: string) => {
  if (!selectedImageFile.value) return

  try {
    await uploadProductImage(productId, selectedImageFile.value)
    ElMessage.success('Imagen subida exitosamente')
    clearImagePreview()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || 'Error al subir imagen')
    throw error
  }
}
</script>

<style scoped>
.products-container {
  padding: 20px;
}

.kpis-container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin: 20px 0;
}

.kpi-card {
  cursor: default;
}

.kpi-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.kpi-icon {
  font-size: 36px;
}

.kpi-value {
  font-size: 28px;
  font-weight: 700;
  color: #303133;
}

.kpi-label {
  font-size: 14px;
  color: #909399;
}

.filters-card {
  margin: 20px 0;
}

.filters-container {
  width: 100%;
}

.filters-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: center;
}

.table-card {
  margin-top: 20px;
}

/* Mobile Cards */
.mobile-products {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 16px;
}

.product-card-mobile {
  padding: 16px;
}

.product-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
  gap: 12px;
}

.product-title {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.product-title h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.product-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
}

.info-row .label {
  color: #909399;
  font-weight: 500;
}

.info-row .price {
  font-size: 18px;
  font-weight: 700;
  color: #67C23A;
}

.product-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.product-actions .el-button {
  flex: 1;
  min-width: 80px;
}

/* Responsive */
@media (max-width: 768px) {
  .products-container {
    padding: 12px;
  }

  .kpis-container {
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }

  .kpi-value {
    font-size: 24px;
  }

  .kpi-label {
    font-size: 12px;
  }

  .filters-row {
    flex-direction: column;
  }

  .filters-row > * {
    width: 100%;
  }
}

/* Estilos de imagen */
.product-image-cell {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 60px;
  height: 60px;
}

.table-product-image {
  width: 60px;
  height: 60px;
  object-fit: cover;
  border-radius: 8px;
  border: 1px solid #EBEEF5;
}

.no-image-icon {
  opacity: 0.3;
}

.product-image-mobile {
  width: 80px;
  height: 80px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #F5F7FA;
  border-radius: 8px;
  overflow: hidden;
}

.product-image-mobile img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* Upload de imagen */
.image-upload-section {
  width: 100%;
}

.image-uploader {
  width: 100%;
}

.image-preview {
  position: relative;
  width: 200px;
  height: 200px;
  border: 1px dashed #DCDFE6;
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 12px;
}

.image-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.delete-image-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 10;
}
</style>
