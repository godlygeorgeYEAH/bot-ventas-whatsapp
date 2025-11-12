# CheckOrderModule - Documentación

## 🔍 ¿Cómo se Activa?

El `CheckOrderModule` se activa **automáticamente** cuando el LLM detecta que el usuario quiere consultar su orden.

### ⚡ Comportamiento Simplificado

**NO hay palabras clave específicas.** El LLM entiende la intención independientemente de cómo el usuario pregunte.

### Mensajes que Activan el Módulo (Ejemplos)

El `IntentDetector` (usando **LLM Ollama**) entiende variaciones como:

```
✅ "dónde está mi pedido"
✅ "cómo va mi orden"
✅ "ya enviaron"
✅ "cuándo llega"
✅ "información de mi compra"
✅ "estado de mi pedido"
✅ "rastrear mi orden"
✅ "seguimiento"
✅ "ya llegó"
```

**Intent detectado:** `check_order`

**Respuesta:** Muestra automáticamente la última orden relevante (confirmed/shipped/delivered)

---

## ⚙️ Funcionamiento Actual

### Flujo Principal (100% Automático)

```
Usuario envía mensaje (cualquier variación)
    ↓
IntentDetector analiza con LLM Ollama
    ↓
Identifica intent: "check_order"
    ↓
ModuleRegistry activa CheckOrderModule
    ↓
CheckOrderModule.handle() ejecuta
    ↓
┌──────────────────────────────────────────┐
│ ✅ RESPUESTA INMEDIATA:                 │
│                                          │
│ Busca y muestra la última orden         │
│ relevante del cliente automáticamente    │
│                                          │
│ Estados relevantes:                      │
│ • confirmed (✅ Confirmada)             │
│ • shipped (🚚 En camino)                │
│ • delivered (🎉 Entregada)              │
│                                          │
│ NO pide información adicional            │
│ NO usa palabras clave específicas        │
│ NO requiere número de orden              │
└──────────────────────────────────────────┘
```

---

## 📋 Funcionalidades

### 1. Consulta Automática de Última Orden ✅ ACTIVO

**Lenguaje Natural - Ejemplos de Uso:**
```
✅ "dónde está mi pedido"
✅ "cómo va mi orden"
✅ "ya enviaron"
✅ "cuándo llega"
✅ "información de mi compra"
✅ "seguimiento"
✅ "ya llegó mi pedido"
✅ "estado"
```

**El LLM entiende la intención sin importar cómo pregunte el usuario.**

**Comportamiento:**
- ⚡ **Respuesta inmediata** - No pide información adicional
- 🎯 Busca la última orden con estado relevante:
  - ✅ **confirmed** (Confirmada)
  - 🚚 **shipped** (En camino)
  - 🎉 **delivered** (Entregada)
- ❌ **NO muestra** órdenes: `pending` o `cancelled`
- 📊 Muestra detalles completos automáticamente

**Ventajas:**
- ⚡ Respuesta instantánea
- 🧠 Entiende lenguaje natural (gracias al LLM)
- 🎯 Solo muestra información relevante
- 🚫 No confunde con órdenes pendientes o canceladas
- 💬 Conversación fluida

**Ejemplo de Conversación:**
```
Usuario: "cómo va mi pedido"

Bot: ✅ Orden ORD-20241107-001

     📊 Estado: Confirmada
     📅 Fecha: 07/11/2024 10:30

     Productos:
     • Laptop HP 15 x1
       $850.00 c/u = $850.00

     💰 Subtotal: $850.00
     💵 Total: $850.00

     📍 GPS: 10.9685, -74.7813
     🗺️ Ver en mapa: https://www.google.com/maps?q=10.9685,-74.7813
     🏠 Referencia: Casa amarilla

     ✅ Tu orden ha sido confirmada y está siendo preparada.
     
     💡 Tienes 2 órdenes activas en total.
```


---

## 🔐 Validaciones

### Seguridad y Privacidad

- ✅ **Automático:** El módulo solo muestra órdenes del cliente autenticado por su número de teléfono
- ✅ **Filtrado inteligente:** Solo muestra órdenes en estados relevantes
- ✅ **Sin exposición de datos:** No pide ni muestra números de orden innecesariamente

### Casos Edge

1. **Cliente sin órdenes registradas:**
```
Usuario: "mi pedido"

Bot: No tienes órdenes registradas aún. ¿Te gustaría hacer un pedido?
```

2. **Cliente sin órdenes activas (solo pending/cancelled):**
```
Usuario: "dónde está mi orden"

Bot: No tienes órdenes activas en este momento.
     
     ¿Te gustaría hacer un pedido?
```

3. **Cliente nuevo sin historial:**
```
Usuario: "seguimiento de mi compra"

Bot: No tienes órdenes registradas aún. ¿Te gustaría hacer un pedido?
```

---

## 📊 Estados de Orden

| Estado | Emoji | Descripción | Visible en "última orden"? |
|--------|-------|-------------|----------------------------|
| pending | ⏳ | Pendiente de confirmación | ❌ NO |
| confirmed | ✅ | Confirmada, siendo preparada | ✅ SÍ |
| shipped | 🚚 | En camino | ✅ SÍ |
| delivered | 🎉 | Entregada | ✅ SÍ |
| cancelled | ❌ | Cancelada | ❌ NO |

---

## 🧪 Cómo Probar

### Opción 1: Script de Testing
```bash
python scripts/test_check_order.py
```

### Opción 2: WhatsApp Real

1. Iniciar bot:
```bash
python -m app.main
```

2. Enviar mensajes de prueba (usa lenguaje natural):
```
"cómo va mi pedido"
"dónde está mi orden"
"ya enviaron"
"cuándo llega"
"seguimiento"
"información de mi compra"
```

**Nota:** El LLM entenderá la intención sin importar cómo preguntes.

---

## 🎯 Próximas Mejoras

- [ ] Tracking en tiempo real (integración con courier)
- [ ] Notificaciones automáticas de cambio de estado
- [ ] Historial con filtros (por fecha, estado, etc.)
- [ ] Exportar órdenes a PDF
- [ ] Rating/feedback post-entrega

---

## 🔧 Configuración Técnica

### Archivos Involucrados

```
app/modules/check_order_module.py    → Lógica principal (simplificada)
app/services/order_service.py        → Consultas a BD
app/core/intent_detector.py          → Detección LLM (⭐ clave)
app/main.py                          → Registro del módulo
```

### Sistema Sin Slots

```python
# CheckOrderModule NO usa slots
self.slot_definitions = []
self.slot_manager = None

# Respuesta inmediata basada solo en:
# 1. Intent detectado por LLM (check_order)
# 2. Teléfono del cliente
```

### Dependencias

- `OrderService`: Consultas a base de datos, filtrado de estados
- `CustomerService`: Validación de cliente por teléfono
- `IntentDetector` (LLM): **Componente clave** - detecta intención sin palabras clave

---

## 💡 Tips para Uso

### Para el Usuario Final

1. **Lenguaje natural:** Pregunta como hablarías normalmente
   - "cómo va mi pedido", "ya enviaron", "cuándo llega"
2. **Sin códigos:** No necesitas el número de orden
3. **Respuesta instantánea:** El bot responde de inmediato
4. **Rastreo GPS:** Recibirás enlace a Google Maps automáticamente

### Para el Desarrollador

1. **Cambiar estados mostrados:** 
   ```python
   # En _show_last_relevant_order()
   relevant_statuses = ['confirmed', 'shipped', 'delivered']
   
   # Para incluir pending:
   relevant_statuses = ['pending', 'confirmed', 'shipped', 'delivered']
   ```

2. **Ajustar detección LLM:**
   ```python
   # En app/core/intent_detector.py
   "check_order": {
       "description": "...",  # Modifica la descripción
       "examples": [...]      # Agrega más ejemplos
   }
   ```

3. **Personalizar formato:** Edita `_format_order_details()`

---

## ❓ FAQ

### ¿Cómo sabe el bot qué quiero consultar mi orden?

**R:** Usa el LLM (Ollama) que entiende la intención detrás de tu mensaje, no palabras clave específicas. Puede decir "dónde está", "cómo va", "ya llegó" - el LLM entiende que quieres consultar tu orden.

### ¿Por qué no muestra órdenes pending?

**R:** Las órdenes `pending` aún no están confirmadas ni procesadas. Mostrar solo órdenes activas (confirmadas/enviadas/entregadas) enfoca al usuario en información relevante y evita confusión.

### ¿Por qué no muestra órdenes cancelled?

**R:** Las órdenes canceladas ya no son relevantes para tracking. El bot muestra solo órdenes que el usuario puede rastrear activamente.

### ¿Puedo cambiar qué estados son "relevantes"?

**R:** Sí, edita `relevant_statuses` en `_show_last_relevant_order()`:

```python
# Por defecto
relevant_statuses = ['confirmed', 'shipped', 'delivered']

# Para incluir pending:
relevant_statuses = ['pending', 'confirmed', 'shipped', 'delivered']
```

### ¿El usuario puede especificar un número de orden?

**R:** No, el módulo actual está diseñado para ser completamente automático. El LLM detecta la intención y muestra la última orden relevante. Esto simplifica la experiencia del usuario.

### ¿Qué pasa si tengo múltiples órdenes activas?

**R:** El bot muestra la más reciente y te informa cuántas órdenes activas tienes en total ("💡 Tienes 3 órdenes activas en total").

---

**Última actualización:** 07/11/2024
**Versión:** 2.0 (Simplificado - LLM Only, Sin Slots)

