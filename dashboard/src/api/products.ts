import apiClient from './client'

export interface Product {
  id: string
  name: string
  description: string | null
  price: number
  stock: number
  category: string | null
  image_path: string | null
  sku: string | null
  is_active: boolean
  created_at: string
  updated_at: string
  in_stock: boolean
  has_image: boolean
}

export interface ProductCreate {
  name: string
  description?: string | null
  price: number
  stock: number
  category?: string | null
  sku?: string | null
  is_active?: boolean
}

export interface ProductUpdate {
  name?: string
  description?: string | null
  price?: number
  stock?: number
  category?: string | null
  sku?: string | null
  is_active?: boolean
}

export interface ProductStats {
  total: number
  active: number
  inactive: number
  out_of_stock: number
  low_stock: number
  categories: number
}

// Obtener lista de productos
export const getProducts = async (params?: {
  skip?: number
  limit?: number
  search?: string
  category?: string
  is_active?: boolean
  in_stock?: boolean
}) => {
  const response = await apiClient.get<Product[]>('/api/products', { params })
  return response.data
}

// Obtener estadísticas de productos
export const getProductStats = async () => {
  const response = await apiClient.get<ProductStats>('/api/products/stats')
  return response.data
}

// Obtener categorías disponibles
export const getCategories = async () => {
  const response = await apiClient.get<{ categories: string[] }>('/api/products/categories')
  return response.data
}

// Obtener un producto por ID
export const getProduct = async (id: string) => {
  const response = await apiClient.get<Product>(`/api/products/${id}`)
  return response.data
}

// Crear un nuevo producto
export const createProduct = async (data: ProductCreate) => {
  const response = await apiClient.post<Product>('/api/products', data)
  return response.data
}

// Actualizar un producto
export const updateProduct = async (id: string, data: ProductUpdate) => {
  const response = await apiClient.put<Product>(`/api/products/${id}`, data)
  return response.data
}

// Eliminar un producto
export const deleteProduct = async (id: string) => {
  const response = await apiClient.delete<{ success: boolean; message: string }>(`/api/products/${id}`)
  return response.data
}

// Actualizar solo el stock
export const updateStock = async (id: string, newStock: number) => {
  const response = await apiClient.patch<{ success: boolean; old_stock: number; new_stock: number }>(
    `/api/products/${id}/stock`,
    null,
    { params: { new_stock: newStock } }
  )
  return response.data
}

// Activar/desactivar producto
export const toggleActive = async (id: string) => {
  const response = await apiClient.patch<{ success: boolean; is_active: boolean; message: string }>(
    `/api/products/${id}/toggle-active`
  )
  return response.data
}

// Subir imagen de producto
export const uploadProductImage = async (id: string, file: File) => {
  const formData = new FormData()
  formData.append('file', file)
  
  const response = await apiClient.post<{
    success: boolean
    message: string
    filename: string
    image_url: string
    product_name: string
  }>(`/api/products/${id}/upload-image`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
  
  return response.data
}

// Eliminar imagen de producto
export const deleteProductImage = async (id: string) => {
  const response = await apiClient.delete<{
    success: boolean
    message: string
    product_name: string
  }>(`/api/products/${id}/delete-image`)
  
  return response.data
}

// Obtener URL de imagen de producto
export const getProductImage = async (id: string) => {
  const response = await apiClient.get<{
    has_image: boolean
    image_url: string | null
    product_name?: string
  }>(`/api/products/${id}/image`)
  
  return response.data
}

