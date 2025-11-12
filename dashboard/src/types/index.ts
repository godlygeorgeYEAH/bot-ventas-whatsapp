// Tipos para el dashboard
export interface Order {
  id: string
  order_number: string
  customer_id: string
  customer_name?: string
  customer_phone?: string
  status: OrderStatus
  subtotal: number
  tax: number
  shipping_cost: number
  total: number
  payment_method: string
  delivery_address?: string
  delivery_latitude?: number
  delivery_longitude?: number
  delivery_reference?: string
  items: OrderItem[]
  created_at: string
  updated_at: string
  confirmed_at?: string
  shipped_at?: string
  delivered_at?: string
  cancelled_at?: string
}

export interface OrderItem {
  id: string
  product_id: string
  product_name: string
  quantity: number
  unit_price: number
  subtotal: number
}

export type OrderStatus = 'pending' | 'confirmed' | 'shipped' | 'delivered' | 'cancelled'

export interface Product {
  id: string
  name: string
  description?: string
  price: number
  stock: number
  category?: string
  image_url?: string
  created_at: string
  updated_at: string
}

export interface Customer {
  id: string
  phone: string
  name: string
  email?: string
  total_messages: number
  first_contact_at: string
  last_contact_at: string
  created_at: string
}

