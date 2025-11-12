import apiClient from './client'
import type { Order } from '../types'

export const ordersApi = {
  // Obtener todas las órdenes
  async getOrders(params?: {
    status?: string
    limit?: number
    offset?: number
  }): Promise<Order[]> {
    const { data } = await apiClient.get('/api/orders', { params })
    return data
  },

  // Obtener una orden específica
  async getOrder(orderId: string): Promise<Order> {
    const { data } = await apiClient.get(`/api/orders/${orderId}`)
    return data
  },

  // Actualizar estado de una orden
  async updateOrderStatus(orderId: string, status: string): Promise<Order> {
    const { data } = await apiClient.patch(`/api/orders/${orderId}/status`, { status })
    return data
  },

  // Cancelar orden (devuelve stock)
  async cancelOrder(orderId: string): Promise<Order> {
    const { data } = await apiClient.post(`/api/orders/${orderId}/cancel`)
    return data
  },

  // Eliminar orden permanentemente
  async deleteOrder(orderId: string): Promise<{ success: boolean; message: string }> {
    const { data } = await apiClient.delete(`/api/orders/${orderId}`)
    return data
  },

  // Asignar conductor (funcionalidad futura)
  async assignDriver(orderId: string): Promise<{ success: boolean; message: string }> {
    const { data } = await apiClient.post(`/api/orders/${orderId}/assign-driver`)
    return data
  },

  // Obtener estadísticas
  async getStats(): Promise<{
    total: number
    pending: number
    confirmed: number
    shipped: number
    delivered: number
    cancelled: number
  }> {
    const { data } = await apiClient.get('/api/orders/stats')
    return data
  }
}

