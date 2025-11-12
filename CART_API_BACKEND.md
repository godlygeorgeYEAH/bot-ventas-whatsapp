# 🛒 Backend: Sistema de Carrito con Links Únicos

## 📋 Resumen

Este documento describe la implementación del backend para el sistema de carrito con links únicos. El objetivo es permitir que el bot de WhatsApp genere links únicos que los usuarios pueden abrir en una webapp para construir sus órdenes de forma visual e intuitiva.

## 🏗️ Arquitectura

### **Flujo Completo**

```
1. Usuario: "Quiero hacer un pedido"
   ↓
2. Bot genera link único → http://webapp.com/cart/abc-123-xyz
   ↓
3. Bot envía link por WhatsApp
   ↓
4. Usuario abre link en navegador
   ↓
5. WebApp muestra catálogo de productos
   ↓
6. Usuario selecciona productos y confirma
   ↓
7. WebApp envía webhook al bot con orden
   ↓
8. Bot solicita GPS y método de pago
   ↓
9. Bot confirma orden final
```

### **Componentes Implementados**

- ✅ **`CartSession` Model**: Tabla de BD para gestionar sesiones de carrito
- ✅ **`CartService`**: Lógica de negocio para tokens y sesiones
- ✅ **API Endpoints**: Interfaz REST para webapp y bot
- ✅ **Configuración**: Settings para URLs y expiración

---

## 📦 Base de Datos

### **Tabla: `cart_sessions`**

```sql
CREATE TABLE cart_sessions (
    id VARCHAR PRIMARY KEY,
    token VARCHAR(36) UNIQUE NOT NULL,           -- Token UUID único
    customer_id VARCHAR NOT NULL,                -- FK a customers
    expires_at DATETIME NOT NULL,                -- Expiración (default: 24h)
    used BOOLEAN DEFAULT FALSE,                  -- ¿Ya se completó?
    order_id VARCHAR NULL,                       -- FK a orders (cuando se completa)
    cart_data JSON DEFAULT '{}',                 -- Metadata (productos sugeridos, etc)
    created_at DATETIME,
    updated_at DATETIME,
    
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (order_id) REFERENCES orders(id)
)

CREATE UNIQUE INDEX ix_cart_sessions_token ON cart_sessions(token);
CREATE INDEX ix_cart_sessions_customer_id ON cart_sessions(customer_id);
```

### **Propiedades Helper**

```python
@property
def is_expired(self) -> bool:
    """Verifica si el token expiró"""
    return datetime.utcnow() > self.expires_at

@property
def is_valid(self) -> bool:
    """Verifica si el token es válido (no usado y no expirado)"""
    return not self.used and not self.is_expired
```

---

## 🔧 CartService

**Ubicación**: `app/services/cart_service.py`

### **Métodos Principales**

#### 1. **`create_cart_session()`**

Crea una nueva sesión de carrito con token único.

```python
cart_service = CartService(db)
result = cart_service.create_cart_session(
    customer_id="customer-id-123",
    hours_valid=24,
    suggested_products=["product-id-1", "product-id-2"]  # Opcional
)

# Resultado:
{
    "success": True,
    "session_id": "session-id-abc",
    "token": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "cart_link": "http://localhost:5173/cart/f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "expires_at": "2025-11-12T10:00:00",
    "suggested_products": ["product-id-1", "product-id-2"]
}
```

#### 2. **`validate_cart_session()`**

Valida un token y devuelve información de la sesión.

```python
validation = cart_service.validate_cart_session(token="abc-123-xyz")

# Si es válido:
{
    "valid": True,
    "session_id": "session-id",
    "customer_id": "customer-id",
    "cart_data": {"suggested_products": [...]},
    "expires_at": "2025-11-12T10:00:00"
}

# Si está expirado:
{
    "valid": False,
    "error": "token_expired",
    "message": "Este link expiró. Solicita uno nuevo.",
    "expired_at": "2025-11-11T10:00:00"
}

# Si ya fue usado:
{
    "valid": False,
    "error": "token_already_used",
    "message": "Este link ya fue usado...",
    "order_id": "order-123"
}
```

#### 3. **`get_available_products()`**

Obtiene todos los productos disponibles (activos con stock).

```python
products = cart_service.get_available_products()

# Resultado:
[
    {
        "id": "product-1",
        "name": "Laptop HP 15",
        "description": "...",
        "price": 599.99,
        "stock": 10,
        "category": "Computadoras",
        "sku": "LAP-HP-15",
        "image_path": "/static/products/laptop.png"
    },
    ...
]
```

#### 4. **`mark_session_as_used()`**

Marca una sesión como usada después de completar la orden.

```python
success = cart_service.mark_session_as_used(
    token="abc-123-xyz",
    order_id="order-456"
)
# True si se marcó exitosamente
```

#### 5. **`get_customer_active_sessions()`**

Obtiene sesiones activas de un cliente (útil para evitar duplicados).

```python
active_sessions = cart_service.get_customer_active_sessions(customer_id="customer-123")
# Lista de CartSession (no usadas, no expiradas)
```

#### 6. **`cleanup_expired_sessions()`**

Limpia sesiones expiradas antiguas (para mantenimiento periódico).

```python
deleted_count = cart_service.cleanup_expired_sessions(days_old=7)
# Número de sesiones eliminadas
```

---

## 🌐 API Endpoints

**Ubicación**: `app/api/cart.py`

Todos los endpoints están bajo el prefijo `/api/cart`.

### **1. POST `/api/cart/create`**

Crea una nueva sesión de carrito.

**Request:**
```json
{
    "customer_phone": "18095551234",
    "suggested_products": ["product-id-1"],  // Opcional
    "hours_valid": 24  // Opcional (default: 24)
}
```

**Response (200):**
```json
{
    "success": true,
    "session_id": "session-id",
    "token": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "cart_link": "http://localhost:5173/cart/f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "expires_at": "2025-11-12T10:00:00",
    "suggested_products": ["product-id-1"]
}
```

**Errores:**
- **404**: Cliente no encontrado
- **500**: Error creando sesión

---

### **2. GET `/api/cart/{token}`**

Obtiene información de una sesión de carrito (validación).

**URL:** `/api/cart/f47ac10b-58cc-4372-a567-0e02b2c3d479`

**Response (200) - Válido:**
```json
{
    "valid": true,
    "session_id": "session-id",
    "customer_id": "customer-id",
    "cart_data": {
        "suggested_products": ["product-id-1"]
    },
    "expires_at": "2025-11-12T10:00:00"
}
```

**Response (200) - Expirado:**
```json
{
    "valid": false,
    "error": "token_expired",
    "message": "Este link expiró. Solicita uno nuevo.",
    "expired_at": "2025-11-11T10:00:00"
}
```

**Response (200) - Ya usado:**
```json
{
    "valid": false,
    "error": "token_already_used",
    "message": "Este link ya fue usado. Si necesitas hacer otra orden, solicita un nuevo link.",
    "order_id": "order-123"
}
```

---

### **3. GET `/api/cart/{token}/products`**

Obtiene la lista de productos disponibles para el carrito.

**URL:** `/api/cart/f47ac10b-58cc-4372-a567-0e02b2c3d479/products`

**Response (200):**
```json
[
    {
        "id": "product-1",
        "name": "Laptop HP 15",
        "description": "Laptop con procesador Intel Core i5",
        "price": 599.99,
        "stock": 10,
        "category": "Computadoras",
        "sku": "LAP-HP-15",
        "image_path": "/static/products/laptop.png"
    },
    {
        "id": "product-2",
        "name": "Mouse Logitech",
        "description": "Mouse inalámbrico ergonómico",
        "price": 29.99,
        "stock": 50,
        "category": "Periféricos",
        "sku": "MOU-LOG-01",
        "image_path": "/static/products/mouse.png"
    }
]
```

**Errores:**
- **400**: Token inválido (expirado, usado, o no existe)

---

### **4. POST `/api/cart/{token}/complete`**

Completa el carrito y crea la orden (webhook desde webapp).

**URL:** `/api/cart/f47ac10b-58cc-4372-a567-0e02b2c3d479/complete`

**Request:**
```json
{
    "products": [
        {"product_id": "product-1", "quantity": 2},
        {"product_id": "product-2", "quantity": 1}
    ],
    "total": 1229.97
}
```

**Response (200):**
```json
{
    "success": true,
    "message": "Orden recibida. Pronto recibirás un mensaje para completar tu pedido.",
    "order_id": "order-789"
}
```

**Errores:**
- **400**: Token inválido
- **500**: Error creando orden

**⚠️ TODO:** Actualmente solo marca la sesión como usada. Falta implementar:
- Creación de orden PENDING con productos
- Notificación al bot para continuar con CheckoutModule (GPS + pago)

---

### **5. GET `/api/cart/{token}/status`**

Verifica el estado actual de una sesión de carrito.

**URL:** `/api/cart/f47ac10b-58cc-4372-a567-0e02b2c3d479/status`

**Response (200):**
```json
{
    "exists": true,
    "used": false,
    "expired": false,
    "valid": true,
    "order_id": null,
    "expires_at": "2025-11-12T10:00:00"
}
```

---

## ⚙️ Configuración

**Archivo**: `config/settings.py`

### **Nuevas Variables**

```python
# WebApp Carrito
webapp_base_url: str = "http://localhost:5173"  # URL base de la webapp del carrito
cart_session_hours: int = 24                    # Horas de validez de una sesión de carrito
```

### **Variables de Entorno (.env)**

```bash
# WebApp Carrito
WEBAPP_BASE_URL=http://localhost:5173
CART_SESSION_HOURS=24
```

**Producción:**
```bash
WEBAPP_BASE_URL=https://shop.tudominio.com
CART_SESSION_HOURS=24
```

---

## 🧪 Testing

### **1. Crear Sesión de Carrito**

```bash
curl -X POST http://localhost:8000/api/cart/create \
  -H "Content-Type: application/json" \
  -d '{
    "customer_phone": "18095551234",
    "hours_valid": 24
  }'
```

### **2. Validar Token**

```bash
curl http://localhost:8000/api/cart/f47ac10b-58cc-4372-a567-0e02b2c3d479
```

### **3. Obtener Productos**

```bash
curl http://localhost:8000/api/cart/f47ac10b-58cc-4372-a567-0e02b2c3d479/products
```

### **4. Completar Carrito**

```bash
curl -X POST http://localhost:8000/api/cart/f47ac10b-58cc-4372-a567-0e02b2c3d479/complete \
  -H "Content-Type: application/json" \
  -d '{
    "products": [
      {"product_id": "product-1", "quantity": 2},
      {"product_id": "product-2", "quantity": 1}
    ],
    "total": 1229.97
  }'
```

---

## 📊 Diagrama de Flujo

```
┌──────────────┐
│   Usuario    │
│  "Quiero un  │
│   pedido"    │
└──────┬───────┘
       │
       v
┌──────────────────────────┐
│   Bot WhatsApp           │
│ - Llama POST /cart/create│
│ - Recibe cart_link       │
└──────┬───────────────────┘
       │
       │ 🔗 Envía link por WhatsApp
       v
┌──────────────────────────┐
│   Usuario abre link      │
│   en navegador           │
└──────┬───────────────────┘
       │
       v
┌──────────────────────────┐
│   WebApp (Vue 3)         │
│ 1. GET /cart/{token}     │ ← Valida token
│ 2. GET /cart/{token}/    │ ← Obtiene productos
│    products              │
│ 3. Usuario selecciona    │
│ 4. POST /cart/{token}/   │ ← Completa carrito
│    complete              │
└──────┬───────────────────┘
       │
       v
┌──────────────────────────┐
│   Bot WhatsApp           │
│ - Recibe webhook         │
│ - Activa CheckoutModule  │
│ - Solicita GPS           │
│ - Solicita método pago   │
│ - Confirma orden         │
└──────────────────────────┘
```

---

## 🚀 Próximos Pasos

### **Backend (Pendiente)**

1. ✅ ~~Tabla `cart_sessions` en BD~~
2. ✅ ~~`CartService` con gestión de tokens~~
3. ✅ ~~Endpoints API REST~~
4. ⬜ **`CartLinkModule`**: Módulo del bot para generar y enviar links
5. ⬜ **`CheckoutModule`**: Módulo del bot para GPS + pago después de webapp
6. ⬜ **Webhook Handler**: Implementar creación de orden desde `/cart/{token}/complete`

### **Frontend (WebApp)**

1. ⬜ Configurar Vue 3 + Vite
2. ⬜ Pantalla de validación de token
3. ⬜ Catálogo de productos
4. ⬜ Carrito de compras (agregar/remover)
5. ⬜ Pantalla de confirmación
6. ⬜ Integración con API backend

### **Testing**

1. ⬜ Pruebas unitarias de `CartService`
2. ⬜ Pruebas de integración de API endpoints
3. ⬜ Pruebas E2E del flujo completo

---

## 📝 Notas Técnicas

### **Seguridad**

- **Tokens UUID**: Generados con `uuid.uuid4()` (128 bits de aleatoriedad)
- **Expiración**: Tokens expiran en 24 horas por defecto
- **Uso único**: Cada token solo puede usarse una vez
- **Validación estricta**: Se valida token antes de cada operación

### **Performance**

- **Índices en BD**: Token y customer_id están indexados
- **Cleanup periódico**: Método para limpiar sesiones expiradas antiguas
- **Sesiones activas**: Query optimizado para obtener solo sesiones válidas

### **Extensibilidad**

- **`cart_data` JSON**: Permite almacenar metadata adicional (productos sugeridos, descuentos, etc.)
- **Configuración flexible**: Tiempo de expiración y URL base configurables
- **Webhook extensible**: Endpoint `/complete` preparado para lógica adicional

---

## ✅ Checklist de Implementación

- [x] Modelo `CartSession` en `models.py`
- [x] Migración de BD ejecutada (tabla creada)
- [x] `CartService` implementado
- [x] Endpoints API creados
- [x] Router registrado en `main.py`
- [x] Configuración agregada a `settings.py`
- [x] Sin errores de linting
- [x] Documentación completa

---

**Estado**: ✅ Backend del sistema de carrito implementado y listo para integración con webapp y bot.

**Siguiente**: Implementar `CartLinkModule` en el bot para generar y enviar links a usuarios.

