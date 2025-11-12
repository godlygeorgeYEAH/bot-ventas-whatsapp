# 🎁 Módulo de Ofrecimientos de Productos

## 📋 Descripción General

El **Módulo de Ofrecimientos** permite al bot sugerir productos adicionales a los clientes en momentos estratégicos de la conversación, aumentando las oportunidades de venta (upselling) y mejorando la experiencia del usuario con recomendaciones personalizadas.

---

## ✨ Características

### **1. Ofrecimientos Inteligentes**
- ✅ Basados en el historial de compras del cliente
- ✅ Priorización por frecuencia de compra
- ✅ Exclusión de productos ya en la orden actual
- ✅ Fallback a productos aleatorios para clientes nuevos

### **2. Momentos de Ofrecimiento**
- ✅ **Después de completar orden**: Antes de confirmarla, se ofrece un producto adicional
- ✅ **Después de greeting** _(configuración lista, implementación futura)_

### **3. Formato Visual**
- ✅ Mensaje de ofrecimiento con imagen del producto
- ✅ Configuración flexible:
  - **Opción A** (`offer_image_as_caption = True`): Texto como caption de la imagen
  - **Opción B** (`offer_image_as_caption = False`): Solo texto SIN imagen

### **4. Respuesta del Usuario**
- ✅ Detección de aceptación: "Sí", "Ok", "Quiero", "Dale", etc.
- ✅ Detección de rechazo: "No", "Paso", "No gracias", etc.
- ✅ Solicitud de clarificación si la respuesta es ambigua

---

## 🔄 Flujo de Funcionamiento

### **Flujo: Ofrecimiento Después de Orden**

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. Usuario completa todos los slots (producto, GPS, referencia) │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. CreateOrderModule crea la orden (estado: PENDING)            │
│    - NO la confirma todavía                                     │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. OfferService selecciona producto para ofrecer                │
│    Prioridad:                                                    │
│    ├─ Producto más ordenado (no en orden actual)                │
│    ├─ Segundo producto más ordenado (no en orden actual)        │
│    └─ Producto aleatorio (si no hay historial)                  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. Bot envía ofrecimiento con imagen                            │
│    📸 [Imagen del producto]                                     │
│    🎁 "¿Te gustaría agregar esto a tu orden?"                   │
│    💰 "Precio: $X.XX"                                           │
│    "Responde Sí para agregarlo o No para continuar"             │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. Contexto actualizado:                                        │
│    - current_module: "OfferProductModule"                       │
│    - waiting_offer_response: true                               │
│    - offered_product: {...}                                     │
│    - pending_order_id: "xxx"                                    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                  ┌─────────┴─────────┐
                  │   Usuario responde   │
                  └─────────┬─────────┘
                            │
            ┌───────────────┼───────────────┐
            │               │               │
            ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │   "Sí"   │    │   "No"   │    │ Ambiguo  │
    └─────┬────┘    └─────┬────┘    └─────┬────┘
          │               │               │
          ▼               ▼               ▼
┌─────────────────┐ ┌─────────────┐ ┌─────────────┐
│ 6a. ACEPTADO    │ │ 6b. RECHAZADO│ │ 6c. CLARIF. │
│ - Agregar prod. │ │ - Confirmar  │ │ Pedir que   │
│   a orden       │ │   orden sin  │ │ responda    │
│ - Confirmar     │ │   producto   │ │ Sí o No     │
│   orden         │ │   adicional  │ │             │
│ - Mostrar       │ │ - Mostrar    │ │ (Vuelve al  │
│   resumen       │ │   resumen    │ │  paso 5)    │
└─────────────────┘ └─────────────┘ └─────────────┘
```

---

## 🗂️ Arquitectura del Sistema

### **Servicios**

#### **1. `OfferService`** (`app/services/offer_service.py`)

**Responsabilidades:**
- Seleccionar producto a ofrecer basado en historial
- Formatear mensaje de ofrecimiento
- Determinar si hacer ofrecimiento

**Métodos principales:**

```python
select_product_to_offer(
    customer_id: str,
    current_order_id: Optional[str] = None,
    exclude_product_ids: Optional[List[str]] = None
) -> Optional[Dict]
```
- **Input**: ID del cliente, orden actual (opcional), productos a excluir
- **Output**: Dict con información del producto seleccionado o None
- **Lógica de prioridad**:
  1. Producto más ordenado (no en orden actual)
  2. Segundo producto más ordenado (no en orden actual)
  3. Producto aleatorio

```python
format_offer_message(
    product: Dict,
    include_price: bool = True
) -> str
```
- **Input**: Producto a ofrecer
- **Output**: Mensaje formateado con emojis

---

#### **2. `OrderService` (Extensión)** (`app/services/order_service.py`)

**Métodos agregados:**

```python
get_customer_product_history(
    customer_id: str,
    limit: int = 10
) -> List[Dict]
```
- **Output**: Lista de productos ordenados por frecuencia
- **Incluye**: `product_id`, `product_name`, `times_ordered`, `total_quantity`

```python
get_products_not_in_order(
    order_id: str
) -> List[str]
```
- **Output**: Lista de IDs de productos NO presentes en la orden

---

### **Módulos**

#### **3. `OfferProductModule`** (`app/modules/offer_product_module.py`)

**Responsabilidades:**
- Detectar respuesta del usuario (Sí/No/Ambiguo)
- Agregar producto a orden si acepta
- Confirmar orden después de respuesta
- Limpiar contexto

**Método principal:**

```python
handle(
    message: str,
    context: Dict[str, Any],
    phone: str
) -> Dict[str, Any]
```

**Estados del módulo:**
- **Entrada**: `waiting_offer_response = True`
- **Salida (Aceptado)**:
  - Producto agregado a orden
  - Orden confirmada
  - Resumen enviado
- **Salida (Rechazado)**:
  - Orden confirmada sin producto adicional
  - Resumen enviado

---

#### **4. `CreateOrderModule` (Modificación)** (`app/modules/create_order_module.py`)

**Cambios realizados:**

**En `_create_order()` (líneas 693-728):**
```python
# Después de crear la orden, verificar si hacer ofrecimiento
if settings.enable_product_offers and settings.offer_after_order:
    # Seleccionar producto
    product_to_offer = offer_service.select_product_to_offer(...)
    
    if product_to_offer:
        # Enviar ofrecimiento
        context_updates = make_offer(phone, product_to_offer, order.id)
        
        # Retornar SIN confirmar orden
        return {
            "success": True,
            "message": None,  # Ya se envió
            "offer_made": True,
            "context_updates": context_updates
        }

# Si no hay ofrecimiento, confirmar normalmente
order = order_service.confirm_order(order.id)
```

**En `handle()` (líneas 509-520):**
```python
if order_result.get("offer_made"):
    # No enviar mensaje (ya enviado por ofrecimiento)
    response_data["response"] = None
    # Aplicar context updates
    response_data["context_updates"].update(...)
else:
    # Flujo normal
    response_data["response"] = order_result["message"]
```

---

### **Helpers**

#### **5. `OfferHelper`** (`app/helpers/offer_helper.py`)

**Responsabilidad:**
- Enviar ofrecimiento con imagen por WhatsApp

**Método principal:**

```python
send_offer_sync(
    phone: str,
    product: Dict,
    offer_message: str
) -> bool
```

**Comportamiento:**
1. Verifica si hay imagen del producto
2. Construye path completo de la imagen
3. Envía según configuración:
   - **Opción A** (`offer_image_as_caption = True`): Imagen con caption
     - Si falla el envío de imagen → Fallback automático a solo texto
   - **Opción B** (`offer_image_as_caption = False`): Solo texto SIN imagen
4. Manejo de errores robusto:
   - Sin imagen → Solo texto
   - Imagen no encontrada → Solo texto
   - Error al enviar imagen (Opción A) → Fallback a solo texto
   - Logs detallados en cada caso

---

#### **6. `make_offer()` (Función helper)** (`app/modules/offer_product_module.py`)

**Responsabilidad:**
- Orquestar el proceso de hacer un ofrecimiento

**Flujo:**
```python
def make_offer(phone, product, pending_order_id):
    1. Formatear mensaje con OfferService
    2. Enviar con OfferHelper
    3. Retornar context_updates para aplicar
```

---

## ⚙️ Configuración

### **Archivo: `config/settings.py`**

```python
# Product Offerings
enable_product_offers: bool = True  # Master switch
offer_after_order: bool = True      # Ofrecer después de orden
offer_after_greeting: bool = True   # Ofrecer después de saludo (futuro)
offer_with_image: bool = True       # Incluir imagen del producto
offer_image_as_caption: bool = True # True: imagen con caption, False: solo texto sin imagen
```

### **Variables de Entorno (`.env`)**

```bash
# Ofrecimientos de productos
ENABLE_PRODUCT_OFFERS=true
OFFER_AFTER_ORDER=true
OFFER_AFTER_GREETING=false  # Para implementación futura
OFFER_WITH_IMAGE=true
OFFER_IMAGE_AS_CAPTION=true
```

---

## 🎨 Opciones de Formato y Manejo de Errores

### **Opción A: Imagen con Caption** (`offer_image_as_caption = True`)

**Comportamiento:**
- Envía imagen del producto con texto en el caption
- **Fallback automático**: Si hay error al enviar imagen → envía solo texto
- Casos de fallback:
  - Archivo de imagen no encontrado
  - Error en transmisión de imagen
  - Formato de imagen no soportado

**Logs:**
```
📸 Enviando ofrecimiento con imagen+caption
✅ Ofrecimiento (imagen+caption) enviado a 1234567890

// O en caso de error:
❌ Error enviando imagen: [error]
⚠️ Fallback: Enviando ofrecimiento solo texto (sin imagen)
✅ Ofrecimiento (solo texto fallback) enviado a 1234567890
```

**Ventajas:**
- ✅ Visual atractivo del producto
- ✅ Mensaje integrado (imagen + texto)
- ✅ Robusto (fallback automático)

---

### **Opción B: Solo Texto** (`offer_image_as_caption = False`)

**Comportamiento:**
- Envía solo mensaje de texto, SIN imagen
- Ignora completamente la imagen del producto
- Útil para:
  - Conexiones lentas
  - Reducir uso de datos
  - Productos sin imágenes
  - Testing rápido

**Logs:**
```
📝 Enviando ofrecimiento solo texto (sin imagen)
✅ Ofrecimiento (solo texto) enviado a 1234567890
```

**Ventajas:**
- ✅ Rápido y ligero
- ✅ No depende de imágenes
- ✅ Bajo uso de datos

---

### **Manejo de Errores Global**

**Casos cubiertos:**

1. **Producto sin `image_path`**
   ```
   ⚠️ Producto sin imagen, enviando solo texto
   ✅ Ofrecimiento (texto) enviado
   ```

2. **Imagen no encontrada en filesystem**
   ```
   ⚠️ Imagen no encontrada: /path/to/image.jpg
   ⚠️ Fallback: enviando solo texto
   ✅ Ofrecimiento (texto) enviado
   ```

3. **Error al enviar imagen (Opción A)**
   ```
   ❌ Error enviando imagen: [detalle del error]
   ⚠️ Fallback: Enviando ofrecimiento solo texto
   ✅ Ofrecimiento (solo texto fallback) enviado
   ```

4. **Error general**
   ```
   ❌ Error enviando ofrecimiento: [error]
   (Retorna False, no envía nada)
   ```

**Garantía:** El sistema SIEMPRE intenta enviar el mensaje, priorizando el texto sobre la imagen.

---

## 📊 Contexto de Conversación

### **Campos agregados:**

```python
{
    # Estado de ofrecimiento
    "waiting_offer_response": bool,     # True si esperando respuesta
    "offered_product": Dict,            # Producto ofrecido
    "pending_order_id": str,            # ID de orden pendiente
    
    # Módulo activo
    "current_module": "OfferProductModule"
}
```

### **Ejemplo de contexto durante ofrecimiento:**

```python
{
    "current_module": "OfferProductModule",
    "waiting_offer_response": True,
    "offered_product": {
        "product_id": "abc-123",
        "product_name": "Mouse Logitech MX Master 3",
        "price": 100.0,
        "image_path": "uploads/products/mouse.jpg",
        "selection_reason": "most_ordered"
    },
    "pending_order_id": "order-xyz-789",
    "conversation_state": "waiting_offer_response"
}
```

---

## 🗄️ Base de Datos

### **Consultas agregadas:**

#### **1. Historial de productos del cliente**
```sql
SELECT 
    product_id, 
    product_name, 
    COUNT(*) as times_ordered,
    SUM(quantity) as total_quantity
FROM order_items
JOIN orders ON order_items.order_id = orders.id
WHERE 
    orders.customer_id = ?
    AND orders.status = 'confirmed'
GROUP BY product_id, product_name
ORDER BY COUNT(*) DESC
LIMIT 10;
```

#### **2. Productos NO en una orden**
```sql
SELECT id
FROM products
WHERE 
    is_active = true
    AND stock > 0
    AND id NOT IN (
        SELECT product_id FROM order_items WHERE order_id = ?
    );
```

---

## 📝 Ejemplos de Uso

### **Caso 1: Usuario con historial - Acepta ofrecimiento**

```
Usuario: "Quiero una laptop"
Bot: "¿Cuántas laptops quieres?"
Usuario: "2"
Bot: "¿Cuál es tu dirección de entrega?"
Usuario: [Envía ubicación GPS]
Bot: "¿Alguna referencia?"
Usuario: "Casa azul"
Bot: "¿Método de pago?"
Usuario: "Efectivo"

[Bot crea orden PENDING]

Bot: 📸 [Imagen de Mouse]
     🎁 ¿Te gustaría agregar esto a tu orden?
     
     Mouse Logitech MX Master 3
     Mouse ergonómico inalámbrico
     
     💰 Precio: $100.00
     
     Responde Sí para agregarlo o No para continuar sin él.

Usuario: "Sí"

Bot: ✅ ¡Genial! He agregado Mouse Logitech MX Master 3 a tu orden.
     
     ✅ Orden #ORD-20251108-004
     
     Estado: CONFIRMED
     
     Productos:
       • Laptop HP 15 x2 - $1700.00
       • Mouse Logitech MX Master 3 x1 - $100.00
     
     Subtotal: $1800.00
     Impuesto (19%): $342.00
     Envío: $0.00
     ────────────────────
     TOTAL: $2142.00
     ...
```

---

### **Caso 2: Usuario sin historial - Rechaza ofrecimiento**

```
Usuario: "Quiero un teclado"
[... flujo normal ...]

[Bot crea orden PENDING]

Bot: 📸 [Imagen de Laptop aleatoria]
     🎁 ¿Te gustaría agregar esto a tu orden?
     
     Laptop Dell Inspiron
     ...
     
Usuario: "No"

Bot: Entendido, continuamos con tu orden actual.
     
     ✅ Orden #ORD-20251108-005
     
     Estado: CONFIRMED
     
     Productos:
       • Teclado Mecánico RGB x1 - $150.00
     ...
```

---

### **Caso 3: Respuesta ambigua**

```
[... después de ofrecimiento ...]

Usuario: "mmm no sé"

Bot: ⚠️ No entendí tu respuesta. Por favor responde *Sí* para 
     agregar el producto o *No* para continuar sin él.

Usuario: "Ok sí"

Bot: ✅ ¡Genial! He agregado [producto] a tu orden.
     ...
```

---

## 🔍 Prioridad de Selección de Productos

### **Algoritmo detallado:**

```python
def select_product_to_offer(customer_id, current_order_id):
    # 1. Obtener historial del cliente
    history = get_customer_product_history(customer_id)
    # Resultado: [
    #   {product_id: "A", times_ordered: 5},
    #   {product_id: "B", times_ordered: 3},
    #   {product_id: "C", times_ordered: 1}
    # ]
    
    # 2. Obtener productos ya en la orden actual
    products_in_order = get_products_in_order(current_order_id)
    # Resultado: ["A"]  # Ya tiene producto A
    
    # 3. Filtrar historial (excluir productos en orden)
    available_history = filter(history, not in products_in_order)
    # Resultado: [
    #   {product_id: "B", times_ordered: 3},  # ← PRIORIDAD 1
    #   {product_id: "C", times_ordered: 1}   # ← PRIORIDAD 2
    # ]
    
    # 4. Seleccionar según disponibilidad
    if len(available_history) >= 1:
        return available_history[0]  # Producto más ordenado
    elif len(available_history) >= 2:
        return available_history[1]  # Segundo más ordenado
    else:
        # Sin historial, seleccionar aleatorio
        all_products = get_all_available_products()
        exclude_in_order = [...]
        available = filter(all_products, not in exclude_in_order)
        return random.choice(available)
```

---

## 🚀 Testing

### **Test 1: Ofrecimiento exitoso con aceptación**

```bash
# 1. Crear orden con producto
curl -X POST http://localhost:8000/webhook/waha \
  -d '{"phone": "1234567890", "message": "Quiero 2 laptops"}'

# 2. Completar flujo hasta GPS y referencia
# (El bot enviará automáticamente el ofrecimiento)

# 3. Aceptar ofrecimiento
curl -X POST http://localhost:8000/webhook/waha \
  -d '{"phone": "1234567890", "message": "Sí"}'

# Verificar:
# - Producto agregado a la orden
# - Orden confirmada
# - Stock actualizado para ambos productos
```

### **Test 2: Ofrecimiento con rechazo**

```bash
# [Mismo flujo hasta ofrecimiento]

# Rechazar
curl -X POST http://localhost:8000/webhook/waha \
  -d '{"phone": "1234567890", "message": "No gracias"}'

# Verificar:
# - Orden confirmada SIN producto adicional
# - Stock actualizado solo para productos originales
```

### **Test 3: Sin ofrecimiento (sin productos disponibles)**

```bash
# Crear orden con TODOS los productos disponibles en catálogo
# El bot NO debería hacer ofrecimiento y confirmar directamente
```

---

## 📂 Archivos Modificados/Creados

### **Nuevos archivos:**

1. ✅ `app/services/offer_service.py` - Lógica de selección de productos
2. ✅ `app/modules/offer_product_module.py` - Módulo de manejo de ofrecimientos
3. ✅ `app/helpers/offer_helper.py` - Helper para envío con imagen

### **Archivos modificados:**

1. ✅ `app/services/order_service.py` - Métodos de historial de productos
2. ✅ `app/modules/create_order_module.py` - Integración de ofrecimientos
3. ✅ `app/services/sync_worker.py` - Manejo de respuesta None
4. ✅ `app/main.py` - Registro del módulo
5. ✅ `config/settings.py` - Configuración de ofrecimientos

### **Documentación:**

1. ✅ `PRODUCT_OFFERS_FEATURE.md` - Este archivo

---

## ⚠️ Consideraciones Importantes

### **1. Estado de la Orden**

- **PENDING**: Orden creada, esperando confirmación
- **CONFIRMED**: Orden confirmada después de aceptar/rechazar ofrecimiento

❗ **La orden NO se confirma hasta que el usuario responda al ofrecimiento**

### **2. Stock Management**

- Stock NO se reduce al crear orden PENDING
- Stock SÍ se reduce al confirmar orden (después de ofrecimiento)
- Si usuario acepta producto adicional, stock de ambos se reduce

### **3. Imágenes de Productos**

- Ruta esperada: `uploads/products/[nombre_imagen]`
- Formato soportado: JPG, PNG, GIF, WEBP
- **Sistema robusto de fallback**:
  - Sin imagen → Envía solo texto
  - Imagen no encontrada → Envía solo texto
  - Error al enviar imagen → Fallback automático a texto
  - Logs detallados en cada caso
- **Opción B**: Ignora imágenes completamente (solo texto)

### **4. Performance**

- Query de historial limitado a 10 productos más frecuentes
- Selección de producto aleatoria usa todos los productos activos disponibles

---

## 🔮 Mejoras Futuras

### **1. Ofrecimientos después de Greeting**
```python
Usuario: "Hola"
Bot: "¡Hola! ¿Cómo estás?"
Bot: 📸 [Imagen]
     "Te recomiendo nuestra nueva Laptop Dell..."
```

### **2. Machine Learning para Recomendaciones**
- Análisis de patrones de compra
- Recomendaciones basadas en categorías
- Productos complementarios (ej: Mouse → Mouse Pad)

### **3. A/B Testing**
- Diferentes formatos de mensaje
- Con/sin imagen
- Caption vs separado

### **4. Analytics**
- Tasa de aceptación de ofrecimientos
- Productos más exitosos en ofrecimientos
- Revenue adicional generado

---

## ✅ Checklist de Implementación

- [x] ✅ Crear `OfferService` con lógica de selección
- [x] ✅ Agregar métodos de historial en `OrderService`
- [x] ✅ Crear `OfferHelper` para envío con imagen
- [x] ✅ Implementar Opción A (imagen con caption) con fallback
- [x] ✅ Implementar Opción B (solo texto sin imagen)
- [x] ✅ Manejo robusto de errores de imágenes
- [x] ✅ Crear `OfferProductModule` para manejo de respuestas
- [x] ✅ Modificar `CreateOrderModule` para integración
- [x] ✅ Modificar `sync_worker` para respuesta None
- [x] ✅ Agregar configuración en `settings.py`
- [x] ✅ Registrar módulo en `main.py`
- [x] ✅ Sin errores de linter
- [x] ✅ Documentación completa
- [ ] ⏳ Testing Opción A con imagen válida
- [ ] ⏳ Testing Opción A con imagen inexistente (fallback)
- [ ] ⏳ Testing Opción B (solo texto)
- [ ] ⏳ Testing de edge cases
- [ ] ⏳ Validar métricas de conversión

---

## 🔄 Cambios Recientes

### **v1.1 - Mejoras de Robustez** (Último cambio)

**1. Opción B redefinida:**
- **Antes**: Texto separado + imagen
- **Ahora**: Solo texto SIN imagen
- **Beneficio**: Más rápido, menor uso de datos, sin dependencia de imágenes

**2. Manejo de errores mejorado (Opción A):**
- Try-catch en envío de imagen
- Fallback automático a solo texto si falla
- Logs detallados de errores
- Sistema robusto que garantiza envío del mensaje

**3. Logs mejorados:**
```
Opción A exitosa:   ✅ Ofrecimiento (imagen+caption) enviado
Opción A fallback:  ❌ Error enviando imagen → ⚠️ Fallback → ✅ (solo texto fallback)
Opción B:           ✅ Ofrecimiento (solo texto) enviado
```

**Archivos modificados:**
- `app/helpers/offer_helper.py` - Try-catch y fallback en Opción A
- `config/settings.py` - Comentario actualizado
- `PRODUCT_OFFERS_FEATURE.md` - Documentación completa

---

**¡El módulo de ofrecimientos está completamente implementado y listo para probar!** 🎉🎁

