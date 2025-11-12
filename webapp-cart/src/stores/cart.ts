import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Product, CartItem } from '@/types'

export const useCartStore = defineStore('cart', () => {
  // State
  const items = ref<CartItem[]>([])
  const token = ref<string>('')
  const sessionValid = ref<boolean>(false)
  const sessionError = ref<string>('')

  // Getters
  const itemCount = computed(() => {
    return items.value.reduce((total, item) => total + item.quantity, 0)
  })

  const subtotal = computed(() => {
    return items.value.reduce((total, item) => {
      return total + (item.product.price * item.quantity)
    }, 0)
  })

  const isEmpty = computed(() => items.value.length === 0)

  // Actions
  function setToken(newToken: string) {
    token.value = newToken
  }

  function setSessionValid(valid: boolean) {
    sessionValid.value = valid
  }

  function setSessionError(error: string) {
    sessionError.value = error
  }

  function addToCart(product: Product, quantity: number = 1) {
    const existingItem = items.value.find(item => item.product.id === product.id)
    
    if (existingItem) {
      // Actualizar cantidad si ya existe
      const newQuantity = Math.min(existingItem.quantity + quantity, product.stock)
      existingItem.quantity = newQuantity
    } else {
      // Agregar nuevo item con la cantidad especificada
      const validQuantity = Math.min(quantity, product.stock)
      items.value.push({
        product,
        quantity: validQuantity
      })
    }
  }

  function removeFromCart(productId: string) {
    const index = items.value.findIndex(item => item.product.id === productId)
    if (index !== -1) {
      items.value.splice(index, 1)
    }
  }

  function updateQuantity(productId: string, quantity: number) {
    const item = items.value.find(item => item.product.id === productId)
    if (item) {
      // Validar que no exceda el stock
      const newQuantity = Math.min(quantity, item.product.stock)
      // Validar que sea al menos 1
      item.quantity = Math.max(1, newQuantity)
    }
  }

  function incrementQuantity(productId: string) {
    const item = items.value.find(item => item.product.id === productId)
    if (item && item.quantity < item.product.stock) {
      item.quantity++
    }
  }

  function decrementQuantity(productId: string) {
    const item = items.value.find(item => item.product.id === productId)
    if (item) {
      if (item.quantity > 1) {
        item.quantity--
      } else {
        // Si la cantidad es 1, remover del carrito
        removeFromCart(productId)
      }
    }
  }

  function clearCart() {
    items.value = []
  }

  function getCartData() {
    return items.value.map(item => ({
      product_id: item.product.id,
      quantity: item.quantity
    }))
  }

  return {
    // State
    items,
    token,
    sessionValid,
    sessionError,
    // Getters
    itemCount,
    subtotal,
    isEmpty,
    // Actions
    setToken,
    setSessionValid,
    setSessionError,
    addToCart,
    removeFromCart,
    updateQuantity,
    incrementQuantity,
    decrementQuantity,
    clearCart,
    getCartData
  }
})

