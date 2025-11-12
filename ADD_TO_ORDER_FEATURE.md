# 🛒 Funcionalidad: Agregar Productos a Orden Existente

## 📋 Resumen

Esta funcionalidad permite a los clientes agregar productos adicionales a una orden **confirmada** sin necesidad de crear una nueva orden. El sistema detecta automáticamente si el cliente tiene una orden reciente y **agrega los productos automáticamente** a ella.

---

## ✨ Características

### 1. **Detección y Agregado Automático** ⚡
- Al iniciar el flujo de crear orden (intent: `create_order`)
- El sistema busca órdenes confirmadas del cliente en las **últimas 24 horas**
- Si encuentra una, **automáticamente** configura el flujo para agregar a esa orden
- El cliente **NO necesita elegir** - todo es transparente y automático

### 2. **Solo Órdenes Confirmadas**
- ⚠️ **Restricción**: Solo se puede agregar a órdenes en estado `"confirmed"`
- Otros estados (pending, shipped, delivered, cancelled) crean una orden nueva

### 3. **Flujo Totalmente Transparente y Optimizado** ⚡
El bot NO pide ubicación ni método de pago (usa los de la orden existente):
```
Cliente: "Quiero un mouse"
Bot: ¿Cuántas unidades de *mouse* quieres?
Cliente: "2"
Bot: ➕ ¡Productos agregados automáticamente a tu orden existente ORD-20251108-001!
     [Muestra resumen completo actualizado]
```

**¿Por qué no pide ubicación/pago?**
- La orden existente YA tiene esta información
- Los nuevos productos se envían a la misma dirección
- Usa el mismo método de pago

**Comparación de Flujos:**

| Acción | Orden Nueva | Agregar a Existente |
|--------|-------------|---------------------|
| Producto | ✅ Pide | ✅ Pide |
| Cantidad | ✅ Pide | ✅ Pide |
| Ubicación GPS | ✅ Pide | ❌ **Omite** (usa existente) |
| Referencia | ✅ Pide | ❌ **Omite** (usa existente) |
| Método de pago | ✅ Pide | ❌ **Omite** (usa existente) |
| **Total mensajes** | **4-5** | **2 solamente** ⚡ |

### 4. **Actualización Automática de Totales**
- Agrega los nuevos items a la orden
- Recalcula subtotal, impuestos y total
- Reduce el stock de productos
- Muestra resumen actualizado completo

---

## 🔧 Implementación Técnica

### **Archivos Modificados**

#### 1. `app/services/order_service.py`
**Métodos nuevos:**

**`get_recent_confirmed_order(customer_id, max_hours=24)`**
```python
# Busca la orden confirmada más reciente del cliente
# Parámetros:
#   - customer_id: ID del cliente
#   - max_hours: Ventana de tiempo (default: 24 horas)
# Retorna: Order o None
```

**`add_items_to_order(order_id, items)`**
```python
# Agrega items a una orden existente
# Parámetros:
#   - order_id: ID de la orden
#   - items: Lista de {"product_id": "...", "quantity": 2}
# Retorna: Order actualizada
# Excepciones: ValueError si orden no existe o no está confirmed
```

#### 2. `app/modules/create_order_module.py`
**Lógica agregada:**

**Al inicio del método `handle()`:**
- Detecta si es inicio del flujo (sin slots llenados)
- Busca orden confirmada reciente
- **Automáticamente** configura el contexto para agregar a esa orden
- Pre-llena slots de ubicación y pago (de la orden existente)
- Continúa flujo optimizado: **solo pide producto y cantidad**

**Modificación en `_create_order()`:**
- Detecta si `context.get('adding_to_existing_order')` es True
- Llama a `add_items_to_order()` en lugar de `create_order()`
- Muestra resumen actualizado con mensaje de "agregado automáticamente"

---

## 🎯 Flujo de Usuario

### **Escenario 1: Cliente tiene orden confirmada reciente (Agregado Automático)**

```
Cliente: "Quiero un mouse"

Bot: ¿Cuántas unidades de *mouse* quieres?

Cliente: "2"

Bot: ➕ ¡Productos agregados automáticamente a tu orden existente ORD-20251108-001!
     
     *✅ Orden #ORD-20251108-001*
     
     *Estado:* CONFIRMED
     
     *Productos:*
       • Laptop HP x1 - $800.00
       • Mouse Logitech x2 - $40.00
     
     *Subtotal:* $840.00
     *Envío:* $0.00
     *Impuestos:* $159.60
     *TOTAL:* $999.60
     
     📍 Ubicación de entrega:
     GPS: 10.2117903, -67.9884199
     📝 Referencia: casa azul
     
     *Método de pago:* efectivo
     *Estado de pago:* pending
     
     *Fecha:* 08/11/2025 20:33
```

### **Escenario 2: Cliente NO tiene orden confirmada reciente (Orden Nueva)**

```
Cliente: "Quiero un teclado"

Bot: ¿Cuántas unidades de *teclado mecánico* quieres?

Cliente: "1"

Bot: 📍 Por favor comparte tu ubicación GPS desde WhatsApp...

[Flujo normal de orden nueva]
```

---

## 🛡️ Validaciones

### **1. Estado de Orden**
```python
if order.status != OrderStatus.CONFIRMED.value:
    raise ValueError("Solo se pueden agregar items a órdenes confirmadas")
```

### **2. Stock Disponible**
```python
if not self.product_service.check_stock(product.id, quantity):
    raise ValueError(f"Stock insuficiente para {product.name}")
```

### **3. Ventana de Tiempo**
- Solo busca órdenes en las **últimas 24 horas**
- Configurable mediante el parámetro `max_hours`

### **4. Existencia de Orden**
```python
if not order:
    raise ValueError(f"Orden {order_id} no encontrada")
```

---

## 📊 Actualización de Totales

El método `add_items_to_order` recalcula automáticamente:

```python
# 1. Agregar subtotal de nuevos items
order.subtotal += subtotal_added

# 2. Recalcular impuesto (19%)
order.tax = order.subtotal * 0.19

# 3. Recalcular total
order.total = order.subtotal + order.tax + order.shipping_cost

# 4. Actualizar timestamp
order.updated_at = datetime.now()
```

---

## 🎨 Variables de Contexto

| Variable | Tipo | Descripción |
|----------|------|-------------|
| `adding_to_existing_order` | bool | True si estamos agregando a orden existente (automático) |
| `existing_order_id` | str | ID de la orden a la que se agrega |
| `existing_order_number` | str | Número de la orden (para mostrar al usuario) |

---

## 🔒 Restricciones y Consideraciones

### ✅ **Permitido:**
- Agregar múltiples productos en una sola interacción
- Agregar un solo producto
- Productos con cantidad especificada

### ❌ **NO Permitido:**
- Agregar a órdenes en estado `pending`, `shipped`, `delivered` o `cancelled`
- Agregar a órdenes de más de 24 horas (configurable)
- Agregar productos sin stock suficiente

### ⚠️ **Importante:**
- El stock se reduce inmediatamente al agregar
- Los totales se recalculan automáticamente
- La ubicación y método de pago **NO** cambian
- La orden mantiene su número original

---

## 🧪 Testing

### **Caso 1: Agregar producto único automáticamente**
```python
# Cliente con orden confirmada reciente
# 1. Cliente dice "quiero un mouse"
# 2. Bot detecta orden confirmada automáticamente
# 3. Bot pide cantidad (flujo normal)
# 4. Cliente especifica "2"
# 5. Bot agrega y muestra resumen actualizado con mensaje de agregado automático
```

### **Caso 2: Agregar múltiples productos automáticamente**
```python
# Cliente dice "quiero un mouse y un teclado"
# Sistema detecta orden confirmada automáticamente
# Sistema detecta múltiples productos
# Sistema pre-llena ubicación y pago
# Sigue flujo optimizado: solo pide cantidades de cada producto
# Al final agrega todos a la orden existente automáticamente
# NO pide ubicación ni método de pago
```

### **Caso 3: Orden nueva (sin orden confirmada reciente)**
```python
# Cliente sin orden confirmada en últimas 24h
# Sistema crea orden completamente nueva
# Flujo normal: producto → cantidad → ubicación → pago
```

---

## 🚀 Beneficios

1. ✅ **Súper Rápido**: Solo 2 preguntas (producto + cantidad) en lugar de 4
2. ✅ **Totalmente Transparente**: Cliente ni siquiera sabe que está agregando - flujo natural
3. ✅ **Cero Fricción**: No repite ubicación ni método de pago
4. ✅ **UX Mejorada**: Cliente no necesita recordar su número de orden
5. ✅ **Eficiencia**: Menos órdenes fragmentadas automáticamente
6. ✅ **Consistencia**: Todo en una sola orden con la misma ubicación y pago
7. ✅ **Inteligente**: Detección y pre-llenado automático en background
8. ✅ **Seguro**: Validaciones de stock y estado

---

## 🎯 Próximas Mejoras Sugeridas

- [ ] Permitir agregar a órdenes en estado `pending` también
- [ ] Permitir modificar ubicación al agregar productos
- [ ] Mostrar resumen breve antes de agregar (confirmación)
- [ ] Permitir remover productos de orden (antes de shipped)
- [ ] Soporte para cupones/descuentos al agregar productos

---

## 📝 Notas de Desarrollo

- **Fecha de implementación**: 2025-11-08
- **Archivos modificados**: 2 (`order_service.py`, `create_order_module.py`)
- **Líneas agregadas**: ~200
- **Testing**: Manual con WhatsApp real requerido


