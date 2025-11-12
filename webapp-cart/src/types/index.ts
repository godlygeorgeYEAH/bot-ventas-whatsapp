export interface Product {
  id: string
  name: string
  description: string | null
  price: number
  stock: number
  category: string | null
  sku: string | null
  image_path: string | null
}

export interface CartItem {
  product: Product
  quantity: number
}

export interface CartSession {
  valid: boolean
  session_id?: string
  customer_id?: string
  cart_data?: Record<string, any>
  expires_at?: string
  error?: string
  message?: string
}

export interface CompleteCartRequest {
  products: Array<{
    product_id: string
    quantity: number
  }>
  total: number
}

export interface CompleteCartResponse {
  success: boolean
  message: string
  order_id?: string
  error?: string
}

