import axios from 'axios'
import type { Product, CartSession, CompleteCartRequest, CompleteCartResponse } from '@/types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

export const cartAPI = {
  /**
   * Valida un token de sesión de carrito
   */
  async validateSession(token: string): Promise<CartSession> {
    const response = await api.get<CartSession>(`/api/cart/${token}`)
    return response.data
  },

  /**
   * Obtiene la lista de productos disponibles
   */
  async getProducts(token: string): Promise<Product[]> {
    const response = await api.get<Product[]>(`/api/cart/${token}/products`)
    return response.data
  },

  /**
   * Obtiene la orden PENDING asociada al token si existe
   */
  async getPendingOrder(token: string): Promise<any> {
    const response = await api.get(`/api/cart/${token}/pending-order`)
    return response.data
  },

  /**
   * Completa el carrito y crea la orden
   */
  async completeCart(token: string, data: CompleteCartRequest): Promise<CompleteCartResponse> {
    const response = await api.post<CompleteCartResponse>(`/api/cart/${token}/complete`, data)
    return response.data
  },

  /**
   * Obtiene la URL completa de una imagen de producto
   */
  getImageUrl(imagePath: string | null): string {
    if (!imagePath) {
      return '/placeholder-product.png'
    }
    
    // Si la ruta ya es absoluta, devolverla tal cual
    if (imagePath.startsWith('http')) {
      return imagePath
    }
    
    // Construir URL completa
    return `${API_BASE_URL}${imagePath}`
  }
}

export default api

