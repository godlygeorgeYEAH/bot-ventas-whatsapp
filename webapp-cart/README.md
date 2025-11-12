# 🛒 WebApp Carrito de Compras

Aplicación web Vue 3 + TypeScript para el sistema de carrito de compras del bot de WhatsApp.

## 🚀 Características

- ✅ Vue 3 + TypeScript + Vite
- ✅ Element Plus (UI Framework)
- ✅ Pinia (State Management)
- ✅ Vue Router
- ✅ Diseño Responsive (Mobile/Desktop)
- ✅ Validación de tokens
- ✅ Manejo de estados (loading, error, success)
- ✅ Cálculo de totales en tiempo real
- ✅ Controles de cantidad (+/-)
- ✅ Imágenes de productos
- ✅ Confirmación de orden

## 📦 Instalación

```bash
# Instalar dependencias
npm install

# Iniciar servidor de desarrollo
npm run dev

# Compilar para producción
npm run build

# Vista previa de producción
npm run preview
```

## ⚙️ Configuración

Crea un archivo `.env` en la raíz del proyecto:

```env
VITE_API_BASE_URL=http://localhost:8000
```

## 🏗️ Estructura del Proyecto

```
webapp-cart/
├── src/
│   ├── components/          # Componentes Vue
│   │   ├── ProductCard.vue  # Tarjeta de producto
│   │   └── CartItem.vue     # Item del carrito
│   ├── views/               # Vistas/Páginas
│   │   ├── CartView.vue     # Vista principal del carrito
│   │   └── InvalidView.vue  # Vista de token inválido
│   ├── stores/              # Pinia stores
│   │   └── cart.ts          # Store del carrito
│   ├── services/            # Servicios API
│   │   └── api.ts           # Cliente HTTP
│   ├── types/               # TypeScript types
│   │   └── index.ts         # Definiciones de tipos
│   ├── router/              # Vue Router
│   │   └── index.ts         # Configuración de rutas
│   ├── App.vue              # Componente raíz
│   ├── main.ts              # Punto de entrada
│   └── style.css            # Estilos globales
├── package.json             # Dependencias
├── vite.config.ts           # Configuración de Vite
├── tsconfig.json            # Configuración de TypeScript
└── index.html               # HTML principal
```

## 🌐 Rutas

- `/cart/:token` - Vista principal del carrito (requiere token válido)
- `/invalid` - Vista de link inválido/expirado
- `/` - Redirige a `/invalid`

## 🔄 Flujo de Uso

1. **Usuario recibe link**: El bot de WhatsApp genera un link único: `http://webapp.com/cart/{token}`

2. **Validación**: La webapp valida el token al cargar:
   - ✅ Token válido → Muestra el catálogo
   - ❌ Token expirado → Muestra mensaje de error
   - ❌ Token usado → Muestra mensaje informativo

3. **Selección de productos**: El usuario:
   - Ve todos los productos disponibles con stock
   - Agrega productos al carrito con un click
   - Ajusta cantidades con +/-
   - Remueve productos si lo desea

4. **Confirmación**: Al presionar "Marcar como Lista":
   - Se crea una orden PENDING en el backend
   - Se marca la sesión como usada
   - El backend notifica al bot
   - Se muestra mensaje de éxito

5. **Siguiente paso**: El bot continúa por WhatsApp solicitando:
   - Ubicación GPS
   - Método de pago
   - Confirma la orden final

## 🎨 Diseño

- **Color Principal**: #667eea (Púrpura)
- **Gradiente**: De #667eea a #764ba2
- **Framework UI**: Element Plus
- **Icons**: Element Plus Icons
- **Responsive**: Mobile-first design

## 🔌 Integración con Backend

La webapp se comunica con el backend a través de endpoints REST:

```typescript
// Validar token
GET /api/cart/{token}

// Obtener productos
GET /api/cart/{token}/products

// Completar carrito
POST /api/cart/{token}/complete
```

## 🚨 Manejo de Errores

La aplicación maneja múltiples escenarios de error:

- **Token inválido**: Muestra mensaje claro con instrucciones
- **Token expirado**: Indica que debe solicitar uno nuevo
- **Token ya usado**: Informa que el link fue utilizado
- **Error de conexión**: Botón de reintentar
- **Stock agotado**: Deshabilita botón de agregar
- **Sin productos**: Muestra mensaje de catálogo vacío

## 📱 Características Responsive

- **Desktop (>1024px)**: Grid de 2 columnas (productos + carrito)
- **Tablet (768px-1024px)**: Carrito arriba, productos abajo
- **Mobile (<768px)**: Layout vertical con carrito fijo

## ✅ Validaciones

- ✅ Stock disponible antes de agregar
- ✅ Cantidad máxima = stock del producto
- ✅ Cantidad mínima = 1 (o remover del carrito)
- ✅ Carrito no vacío para confirmar orden
- ✅ Confirmación antes de eliminar productos
- ✅ Confirmación antes de completar orden

## 🔧 Scripts Disponibles

```bash
# Desarrollo
npm run dev          # Inicia servidor en http://localhost:5173

# Producción
npm run build        # Compila para producción
npm run preview      # Vista previa de build de producción
```

## 📊 Estado del Proyecto

**Status**: ✅ Completado y funcional

**Tecnologías**:
- Vue 3.4.0
- TypeScript 5.3.0
- Vite 5.0.0
- Element Plus 2.5.0
- Pinia 2.1.7
- Vue Router 4.2.5

**Características Implementadas**: 100%
- [x] Validación de tokens
- [x] Lista de productos
- [x] Carrito de compras
- [x] Ajuste de cantidades
- [x] Cálculo de totales
- [x] Confirmación de orden
- [x] Diseño responsive
- [x] Manejo de errores
- [x] Imágenes de productos
- [x] Estados de carga

## 🤝 Integración con Bot

Esta webapp es parte del sistema completo de ventas por WhatsApp:

1. **Bot**: Genera link único → Envía por WhatsApp
2. **Webapp**: Usuario construye orden → Confirma
3. **Backend**: Crea orden PENDING → Notifica bot
4. **Bot**: Solicita GPS + Pago → Confirma orden

---

**Desarrollado para**: Bot de Ventas WhatsApp V2
**Última actualización**: Noviembre 2025

