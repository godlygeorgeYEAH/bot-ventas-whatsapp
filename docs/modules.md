# 📦 Sistema de Módulos - Documentación Completa

> Guía completa sobre el sistema de módulos del Bot de Ventas WhatsApp

## 📋 Tabla de Contenidos

- [¿Qué es un Módulo?](#-qué-es-un-módulo)
- [Arquitectura del Sistema](#️-arquitectura-del-sistema)
- [Anatomía de un Módulo](#-anatomía-de-un-módulo)
- [Ciclo de Vida](#-ciclo-de-vida-de-un-módulo)
- [Tipos de Módulos](#-tipos-de-módulos)
- [Sistema de Slots](#-sistema-de-slots)
- [ModuleRegistry](#-moduleregistry-el-cerebro-del-sistema)
- [Comunicación Entre Módulos](#-comunicación-entre-módulos)
- [Ejemplos Completos](#-ejemplos-completos)
- [Buenas Prácticas](#-buenas-prácticas)
- [Troubleshooting](#-troubleshooting)

---

## 🎯 ¿Qué es un Módulo?

Un **módulo** es una pieza independiente de funcionalidad que maneja una **intención específica** del usuario. Cada módulo sabe cómo:

1. **Detectar** cuándo debe activarse (mediante su `intent`)
2. **Recopilar** información necesaria (mediante `slots`)
3. **Ejecutar** la acción correspondiente
4. **Responder** al usuario
5. **Comunicarse** con otros módulos (mediante contexto)

### Características Principales

- **Independientes**: Cada módulo funciona por sí solo
- **Reutilizables**: Se pueden usar en múltiples contextos
- **Persistentes**: Mantienen estado entre mensajes
- **Comunicables**: Comparten información mediante contexto

---

## 🏗️ Arquitectura del Sistema

### Componentes Principales

```
┌─────────────────────────────────────────────────┐
│                                                 │
│  BaseModule (Clase abstracta)                   │
│  ↓                                              │
│  Todos los módulos heredan de aquí             │
│                                                 │
└─────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────┐
│                                                 │
│  ModuleRegistry (Singleton)                     │
│  ↓                                              │
│  Registro central de todos los módulos          │
│  - Almacena módulos por intent                  │
│  - Encuentra módulo apropiado                   │
│                                                 │
└─────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────┐
│                                                 │
│  Módulos Concretos                             │
│  ↓                                              │
│  - CartLinkModule                              │
│  - CheckOrderModule                            │
│  - CheckoutModule                              │
│  - CancelOrderModule                           │
│  - RemoveFromOrderModule                       │
│  - OfferProductModule                          │
│                                                 │
└─────────────────────────────────────────────────┘
```

### Flujo General

```
Usuario envía mensaje
   ↓
SyncWorker procesa
   ↓
¿Hay módulo activo? ──→ SÍ ──→ Usar ese módulo
   ↓
  NO
   ↓
Detectar intención con LLM
   ↓
Buscar módulo en Registry
   ↓
Ejecutar módulo.handle()
   ↓
Guardar context_updates en BD
   ↓
Enviar respuesta al usuario
```

---

## 📦 Anatomía de un Módulo

### Estructura Básica

Todo módulo debe tener esta estructura mínima:

```python
class MiModulo:
    """Descripción del módulo"""

    def __init__(self):
        self.name = "MiModulo"           # Nombre del módulo
        self.intent = "mi_intent"        # Intención que maneja

    def get_intent(self) -> str:
        """Retorna la intención que maneja"""
        return self.intent

    def handle(
        self,
        message: str,
        context: Dict[str, Any],
        phone: str
    ) -> Dict[str, Any]:
        """
        Maneja la ejecución del módulo

        Args:
            message: Mensaje del usuario
            context: Contexto de la conversación
            phone: Teléfono del usuario

        Returns:
            Dict con:
            - response: Texto a enviar al usuario
            - context_updates: Cambios en el contexto
        """
        # LÓGICA AQUÍ

        return {
            "response": "Respuesta al usuario",
            "context_updates": {
                "current_module": None,  # Limpia módulo si termina
                # Otros campos...
            }
        }

    def get_required_slots(self) -> list:
        """Retorna los slots requeridos (si los necesita)"""
        return []  # O lista de SlotDefinition
```

### Campos Importantes

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `name` | `str` | Nombre único del módulo |
| `intent` | `str` | Intención que activa el módulo |
| `slot_definitions` | `List[SlotDefinition]` | Slots que necesita recopilar |
| `slot_manager` | `SlotManager` | Gestor de slots (si usa slots) |

### Métodos Obligatorios

| Método | Retorno | Descripción |
|--------|---------|-------------|
| `__init__()` | - | Inicializa el módulo |
| `get_intent()` | `str` | Retorna la intención |
| `handle()` | `Dict` | Procesa el mensaje |
| `get_required_slots()` | `List` | Retorna slots necesarios |

---

## 🔄 Ciclo de Vida de un Módulo

### Fase 1: Registro (Startup)

Cuando el bot inicia en `app/main.py`:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Iniciando BotVentasWhatsApp")

    # Obtener registro global
    registry = get_module_registry()

    # Registrar módulos
    cart_link_module = CartLinkModule()
    registry.register(cart_link_module)

    checkout_module = CheckoutModule()
    registry.register(checkout_module)

    check_order_module = CheckOrderModule()
    registry.register(check_order_module)

    # ... más módulos

    yield
```

**¿Qué hace `registry.register()`?**

```python
# En module_registry.py
def register(self, module):
    """Registra un módulo con su intent como clave"""
    self.modules[module.intent] = module
    logger.info(f"✅ Módulo {module.name} registrado (intent: {module.intent})")

# Resultado:
# self.modules = {
#   "create_order": CartLinkModule(),
#   "check_order": CheckOrderModule(),
#   "cancel_order": CancelOrderModule(),
#   ...
# }
```

### Fase 2: Detección de Intención

Cuando llega un mensaje del usuario:

```python
# En sync_worker.py
def _process_message_sync(phone, message):
    # 1. Obtener contexto
    context = context_manager.get_or_create_context(phone)
    module_context = context_manager.get_module_context(phone)

    # 2. ¿Hay módulo activo?
    active_module = registry.get_module_by_context(module_context)

    if active_module:
        # SÍ - usar ese módulo
        module = active_module
    else:
        # NO - detectar intención con LLM
        intent_result = self._detect_intent_with_ollama(message)
        intent = intent_result.get("intent")

        # Buscar módulo para esa intención
        module = registry.get_module(intent)
```

### Fase 3: Ejecución del Módulo

El módulo ejecuta su método `handle()`:

```python
# Ejecutar módulo
result = module.handle(
    message=message,
    context=module_context,
    phone=phone
)

# result = {
#   "response": "¡Aquí está tu carrito: http://...",
#   "context_updates": {
#       "current_module": None,
#       "cart_session_token": "abc-123",
#       "awaiting_cart_completion": True
#   }
# }
```

### Fase 4: Actualización de Contexto

```python
# Actualizar contexto con los cambios del módulo
with get_db_context() as db:
    context_manager = ContextManager(db)
    context_manager.update_module_context(
        phone=phone,
        module_name=module.name,
        context_updates=result["context_updates"]
    )

# Enviar respuesta al usuario
waha.send_text_message(phone, result["response"])
```

---

## 🎯 Tipos de Módulos

### 1. Módulos SIN Slots (Respuesta Inmediata)

**Características:**
- No necesitan recopilar información adicional
- Responden inmediatamente
- `get_required_slots()` retorna `[]`

**Ejemplo: CheckOrderModule**

```python
class CheckOrderModule:
    """Consulta última orden del cliente"""

    def __init__(self):
        self.name = "CheckOrderModule"
        self.intent = "check_order"

    def get_required_slots(self) -> list:
        return []  # ← NO necesita slots

    def handle(self, message, context, phone):
        # 1. Buscar última orden del cliente
        order = self._get_last_order(phone)

        # 2. Formatear respuesta
        if order:
            response = self._format_order_details(order)
        else:
            response = "No tienes órdenes activas"

        # 3. Retornar (sin mantener módulo activo)
        return {
            "response": response,
            "context_updates": {
                "current_module": None  # Limpia módulo
            }
        }
```

**Flujo:**
```
Usuario: "¿Dónde está mi pedido?"
   ↓
Intent detectado: check_order
   ↓
CheckOrderModule.handle() ejecuta INMEDIATAMENTE
   ↓
Consulta BD, formatea respuesta
   ↓
Respuesta: "📦 Tu orden ORD-20231115-001 está en camino..."
   ↓
current_module = None (limpia estado)
```

### 2. Módulos CON Slots (Recopilación Progresiva)

**Características:**
- Necesitan recopilar información paso a paso
- Mantienen estado entre mensajes
- Usan `SlotManager` para gestionar slots
- `get_required_slots()` retorna lista de `SlotDefinition`

**Ejemplo: CheckoutModule**

```python
class CheckoutModule:
    """Módulo para checkout después de webapp"""

    SLOTS = [
        SlotDefinition(
            name="gps_location",
            type=SlotType.LOCATION,
            prompt="📍 Por favor, envíame tu ubicación GPS",
            required=True,
            auto_extract=False
        ),
        SlotDefinition(
            name="delivery_reference",
            type=SlotType.TEXT,
            prompt="🏠 ¿Alguna referencia para tu dirección?",
            required=True,
            auto_extract=True
        ),
        SlotDefinition(
            name="payment_method",
            type=SlotType.CHOICE,
            prompt="💳 ¿Cómo pagarás? (efectivo/tarjeta/transferencia)",
            required=True,
            auto_extract=True,
            validation_rules={
                "choices": ["efectivo", "tarjeta", "transferencia"]
            }
        )
    ]

    def __init__(self):
        self.name = "CheckoutModule"
        self.intent = None  # Se activa por webhook, no por intent

        # Crear slot manager
        slots_dict = {slot.name: slot for slot in self.SLOTS}
        self.slot_manager = SlotManager(slots_dict)

    def handle(self, message, context, phone):
        # Usar slot manager para procesar
        result = self.slot_manager.process_message(
            message=message,
            current_slots=context.get("slots_data", {}),
            current_slot_name=context.get("current_slot"),
            attempts=context.get("validation_attempts", {}),
            context=context
        )

        # Si no está completo, pedir siguiente slot
        if not result.completed:
            return {
                "response": result.next_prompt,
                "context_updates": {
                    "current_module": self.name,
                    "slots_data": result.filled_slots,
                    "current_slot": result.current_slot,
                    "validation_attempts": result.attempts
                }
            }

        # Slots completos - ejecutar acción
        return self._complete_checkout(result.filled_slots, context, phone)
```

**Flujo con Slots:**

```
MENSAJE 1:
Usuario: "Quiero confirmar mi orden"
   ↓
CheckoutModule detecta que necesita 3 slots
   ↓
Estado → "collecting_slots"
current_slot → "gps_location"
   ↓
Bot: "📍 Por favor, comparte tu ubicación GPS"

─────────────────────────────────────────

MENSAJE 2:
Usuario: [Envía GPS] "21.1234,-101.5678"
   ↓
CheckoutModule.handle() recibe mensaje
   ↓
SlotManager valida GPS ✓
Guarda en slots_data["gps_location"]
   ↓
Pasa al siguiente slot: "delivery_reference"
   ↓
Bot: "🏠 ¿Alguna referencia? (ej: casa azul)"

─────────────────────────────────────────

MENSAJE 3:
Usuario: "Casa azul con portón negro"
   ↓
Valida referencia ✓
Guarda en slots_data["delivery_reference"]
   ↓
Pasa al siguiente slot: "payment_method"
   ↓
Bot: "💳 ¿Cómo pagarás?"

─────────────────────────────────────────

MENSAJE 4:
Usuario: "Efectivo"
   ↓
Valida método ✓
Guarda en slots_data["payment_method"]
   ↓
TODOS LOS SLOTS COMPLETOS ✅
   ↓
CheckoutModule._complete_checkout() ejecuta
   ↓
Crea/actualiza orden en BD
   ↓
Bot: "✅ Orden ORD-20231115-001 confirmada!"
   ↓
Limpia contexto (current_module = None)
```

---

## 🎰 Sistema de Slots

### ¿Qué es un Slot?

Un **Slot** es una pieza de información que el módulo necesita recopilar del usuario.

### SlotDefinition

```python
from app.core.slots.slot_definition import SlotDefinition, SlotType

slot = SlotDefinition(
    name="product_name",                    # Nombre único
    type=SlotType.TEXT,                     # Tipo de dato
    prompt="¿Qué producto deseas?",         # Pregunta al usuario
    required=True,                          # ¿Es obligatorio?
    auto_extract=True,                      # ¿Extraer del mensaje inicial?
    validation_rules={                      # Reglas de validación
        "min_length": 3,
        "max_length": 100
    },
    examples=["laptop", "mouse", "teclado"] # Ejemplos
)
```

### Tipos de Slot

```python
class SlotType(Enum):
    TEXT = "text"           # Texto libre
    NUMBER = "number"       # Números
    PHONE = "phone"         # Teléfonos
    EMAIL = "email"         # Emails
    DATE = "date"           # Fechas
    TIME = "time"           # Horas
    LOCATION = "location"   # GPS (lat,lon)
    CHOICE = "choice"       # Opciones predefinidas
    CURRENCY = "currency"   # Moneda
    BOOLEAN = "boolean"     # Sí/No
```

### Campos de SlotDefinition

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `name` | `str` | Nombre único del slot |
| `type` | `SlotType` | Tipo de dato esperado |
| `prompt` | `str` | Pregunta al usuario |
| `required` | `bool` | ¿Es obligatorio? |
| `auto_extract` | `bool` | ¿Intentar extraer del mensaje inicial? |
| `validation_rules` | `Dict` | Reglas de validación |
| `choices` | `List[str]` | Opciones válidas (para CHOICE) |
| `examples` | `List[str]` | Ejemplos de valores válidos |

### Validación de Slots

El `SlotManager` valida automáticamente según el tipo:

```python
# Ejemplo de validación para NUMBER
if slot.type == SlotType.NUMBER:
    try:
        value = float(user_input)
        # Verificar reglas
        if "min" in validation_rules:
            if value < validation_rules["min"]:
                return False
        if "max" in validation_rules:
            if value > validation_rules["max"]:
                return False
        return True
    except ValueError:
        return False

# Ejemplo de validación para CHOICE
elif slot.type == SlotType.CHOICE:
    return user_input.lower() in [c.lower() for c in slot.choices]
```

### Manejo de Errores de Validación

```python
# Si falla la validación
slot_result.attempts += 1

if slot_result.attempts >= 3:
    # Demasiados intentos fallidos
    return {
        "response": "❌ No pude validar tu respuesta. Cancelando...",
        "context_updates": {
            "current_module": None,
            "conversation_state": "failed"
        }
    }
else:
    # Reintentar
    return {
        "response": f"⚠️ Respuesta inválida. {slot.prompt}",
        "context_updates": {
            # Mantener módulo activo y slot actual
        }
    }
```

### SlotManager

El `SlotManager` gestiona todo el proceso de slot filling:

```python
from app.core.slots.slot_manager import SlotManager

# Crear manager con slots
slots_dict = {slot.name: slot for slot in SLOTS}
slot_manager = SlotManager(slots_dict)

# Procesar mensaje del usuario
result = slot_manager.process_message(
    message=user_message,
    current_slots=context.get("slots_data", {}),
    current_slot_name=context.get("current_slot"),
    attempts=context.get("validation_attempts", {}),
    context=context
)

# Resultado
# result.completed: bool - ¿Todos los slots llenos?
# result.filled_slots: Dict - Slots llenados
# result.current_slot: str - Slot actual
# result.next_prompt: str - Siguiente pregunta
# result.attempts: Dict - Intentos de validación
```

---

## 🔌 ModuleRegistry: El Cerebro del Sistema

El `ModuleRegistry` es un **singleton** que gestiona todos los módulos registrados.

### Ubicación

```
app/core/module_registry.py
```

### Métodos Principales

```python
class ModuleRegistry:
    """Registro centralizado de módulos del bot"""

    def __init__(self):
        self.modules = {}  # {intent: module_instance}

    def register(self, module):
        """
        Registra un módulo

        Args:
            module: Instancia del módulo a registrar
        """
        self.modules[module.intent] = module
        logger.info(f"✅ Módulo {module.name} registrado")

    def get_module(self, intent: str):
        """
        Obtiene un módulo por su intención

        Args:
            intent: Intención a buscar

        Returns:
            Módulo correspondiente o None
        """
        return self.modules.get(intent)

    def get_module_by_context(self, context: Dict):
        """
        Obtiene un módulo basado en el contexto actual

        Args:
            context: Contexto de la conversación

        Returns:
            Módulo activo o None
        """
        current_module_name = context.get('current_module')

        if current_module_name:
            # Buscar por nombre exacto
            for module in self.modules.values():
                if module.name == current_module_name:
                    return module

        return None

    def find_module_for_intent(self, intent: str, context: Dict):
        """
        Encuentra el módulo apropiado para una intención

        Args:
            intent: Intención detectada
            context: Contexto actual

        Returns:
            Módulo correspondiente o None
        """
        # Primero verificar si hay módulo activo
        active_module = self.get_module_by_context(context)
        if active_module:
            return active_module

        # Si no, buscar por intención
        return self.get_module(intent)
```

### Uso en el Código

```python
# Obtener instancia global
from app.core.module_registry import get_module_registry

registry = get_module_registry()

# Registrar módulo
my_module = MyModule()
registry.register(my_module)

# Buscar módulo por intención
module = registry.get_module("create_order")
# → Retorna CartLinkModule()

# Buscar módulo activo en contexto
module = registry.get_module_by_context(context)
# → Retorna módulo que está en context["current_module"]
```

---

## 🔄 Comunicación Entre Módulos

Los módulos **NO se hablan directamente**. En lugar de eso, usan un **contexto compartido** que persiste en la base de datos.

### El Canal: ContextManager

El `ContextManager` es el intermediario que gestiona toda la comunicación:

```python
# Ubicación: app/core/context_manager.py

class ContextManager:
    """Gestiona el contexto de las conversaciones"""

    # 📖 LEER contexto
    def get_or_create_context(self, phone: str) -> Dict:
        """Obtiene TODO el contexto del usuario"""
        # Retorna diccionario con:
        # - Datos del cliente
        # - Estado de conversación
        # - Módulo activo
        # - Slots recopilados
        # - FLAGS personalizados (context_data)

    # ✍️ ESCRIBIR contexto
    def update_module_context(
        self,
        phone: str,
        module_name: str,
        context_updates: Dict
    ):
        """Guarda cambios de un módulo en BD"""
        # Actualiza campos específicos
        # Guarda flags adicionales en context_data

    # 🧹 LIMPIAR contexto
    def clear_module_context(self, phone: str):
        """Limpia el contexto del módulo (al terminar)"""
```

### Estructura del Contexto

Cada usuario tiene un contexto con esta estructura:

```python
context = {
    # ═════════════════════════════════════════════
    # DATOS DEL CLIENTE
    # ═════════════════════════════════════════════
    "customer_id": "uuid-123",
    "customer_phone": "584121234567",
    "customer_name": "Juan Pérez",
    "customer_data": {},

    # ═════════════════════════════════════════════
    # ESTADO DE LA CONVERSACIÓN
    # ═════════════════════════════════════════════
    "conversation_id": "uuid-456",
    "conversation_state": "collecting_slots",  # idle, collecting_slots, completed, failed
    "current_intent": "create_order",
    "current_module": "CheckoutModule",        # ← Módulo ACTIVO

    # ═════════════════════════════════════════════
    # SLOT FILLING
    # ═════════════════════════════════════════════
    "slots_data": {                            # ← Datos recopilados
        "product_name": "Laptop",
        "quantity": 2,
        "gps_location": "21.123,-101.456"
    },
    "current_slot": "payment_method",          # ← Slot actual
    "validation_attempts": {                   # ← Intentos de validación
        "payment_method": 1
    },

    # ═════════════════════════════════════════════
    # FLAGS DE COMUNICACIÓN (context_data)
    # ═════════════════════════════════════════════
    "awaiting_cart_completion": True,          # Flag de CartLinkModule
    "cart_session_token": "abc-123",           # Token del carrito
    "checkout_order_id": "uuid-789",           # ID de orden para CheckoutModule
    "start_checkout": True,                    # Flag que activa CheckoutModule
    "waiting_offer_response": False,           # Flag de OfferProductModule
    "awaiting_delivery_reuse_confirmation": False,  # Flag de CheckoutModule

    # Historial de mensajes
    "message_history": [
        {
            "content": "Hola",
            "is_from_bot": False,
            "timestamp": "2023-11-15T10:00:00"
        },
        # ...
    ]
}
```

### Mecanismos de Comunicación

#### 1. Flags Booleanos

Activan o desactivan comportamientos:

```python
# Módulo A deja un flag
context_updates = {
    "awaiting_confirmation": True  # ← Flag
}

# Módulo B lee el flag
if context.get("awaiting_confirmation"):
    # Hacer algo específico
```

**Ejemplos reales:**
- `start_checkout` - Activa CheckoutModule
- `awaiting_cart_completion` - Indica que espera webapp
- `waiting_offer_response` - Espera respuesta a oferta
- `awaiting_delivery_reuse_confirmation` - Espera confirmación SI/NO

#### 2. Datos de Transferencia

Pasan información específica entre módulos:

```python
# Módulo A guarda datos
context_updates = {
    "checkout_order_id": "uuid-789",     # ← Dato
    "cart_session_token": "abc-123"      # ← Dato
}

# Módulo B usa los datos
order_id = context.get("checkout_order_id")
order = db.query(Order).filter(Order.id == order_id).first()
```

**Ejemplos reales:**
- `checkout_order_id` - ID de orden para checkout
- `cart_session_token` - Token de sesión de carrito
- `last_delivery_info` - Última dirección de entrega
- `offered_location` - Ubicación ofrecida para reutilizar

#### 3. Estado del Módulo

Indica qué módulo está activo:

```python
# Activar módulo
context_updates = {
    "current_module": "CheckoutModule"  # ← Módulo activo
}

# SyncWorker lee esto
active_module = registry.get_module_by_context(context)
# Retorna CheckoutModule()
```

#### 4. Slots Compartidos

Los slots persisten entre módulos:

```python
# Módulo A recopila slots
context_updates = {
    "slots_data": {
        "product_name": "Laptop",
        "quantity": 2
    }
}

# Módulo B puede acceder a esos slots
product = context.get("slots_data", {}).get("product_name")
# → "Laptop"
```

### context_data: El Campo Mágico

El campo `context_data` en la tabla `conversations` es un **JSON flexible** que permite guardar CUALQUIER información:

```python
# En la BD (PostgreSQL/SQLite)
CREATE TABLE conversations (
    ...
    context_data JSONB,  -- ← Campo JSON flexible
    ...
);

# Puedes guardar LO QUE SEA
conversation.context_data = {
    "custom_flag": True,
    "custom_data": {"foo": "bar"},
    "custom_list": [1, 2, 3],
    # ... lo que necesites
}
```

**Actualización automática:**

```python
# En context_manager.py
def update_module_context(self, phone, module_name, context_updates):
    # Campos conocidos van a columnas específicas
    conversation.current_module = context_updates.get("current_module")
    conversation.slots_data = context_updates.get("slots_data")
    conversation.current_slot = context_updates.get("current_slot")
    conversation.validation_attempts = context_updates.get("validation_attempts")
    conversation.state = context_updates.get("conversation_state")

    # ✨ TODO LO DEMÁS va a context_data
    context_data = conversation.context_data or {}

    known_fields = {
        'current_slot',
        'slots_data',
        'validation_attempts',
        'conversation_state',
        'current_module'
    }

    for key, value in context_updates.items():
        if key not in known_fields:
            context_data[key] = value  # ← Guarda en context_data

    conversation.context_data = context_data

    # ⚡ CRÍTICO: Marcar como modificado para que SQLAlchemy lo guarde
    flag_modified(conversation, 'context_data')
    db.commit()
```

---

## 💡 Ejemplos Completos

### Ejemplo 1: Módulo Simple Sin Slots

```python
# app/modules/greeting_module.py

class GreetingModule:
    """Módulo simple que saluda al usuario"""

    def __init__(self):
        self.name = "GreetingModule"
        self.intent = "greeting"

    def get_intent(self) -> str:
        return self.intent

    def handle(self, message, context, phone):
        """Responde con saludo personalizado"""

        # Obtener nombre del usuario
        customer_name = context.get("customer_name", "")

        # Generar saludo
        if customer_name:
            response = f"¡Hola {customer_name}! 👋 ¿En qué puedo ayudarte hoy?"
        else:
            response = "¡Hola! 👋 ¿En qué puedo ayudarte hoy?"

        # Retornar sin mantener módulo activo
        return {
            "response": response,
            "context_updates": {
                "current_module": None,
                "current_intent": None,
                "conversation_state": "active"
            }
        }

    def get_required_slots(self) -> list:
        return []  # No necesita slots
```

### Ejemplo 2: Módulo con Slots

```python
# app/modules/contact_module.py

from app.core.slots.slot_definition import SlotDefinition, SlotType
from app.core.slots.slot_manager import SlotManager

class ContactModule:
    """Módulo que recopila información de contacto"""

    SLOTS = [
        SlotDefinition(
            name="name",
            type=SlotType.TEXT,
            prompt="¿Cuál es tu nombre completo?",
            required=True,
            auto_extract=True,
            validation_rules={"min_length": 3}
        ),
        SlotDefinition(
            name="email",
            type=SlotType.EMAIL,
            prompt="¿Cuál es tu email?",
            required=True,
            auto_extract=True
        ),
        SlotDefinition(
            name="phone",
            type=SlotType.PHONE,
            prompt="¿Cuál es tu teléfono?",
            required=False,
            auto_extract=True
        )
    ]

    def __init__(self):
        self.name = "ContactModule"
        self.intent = "provide_contact"

        # Crear slot manager
        slots_dict = {slot.name: slot for slot in self.SLOTS}
        self.slot_manager = SlotManager(slots_dict)

    def get_intent(self) -> str:
        return self.intent

    def handle(self, message, context, phone):
        """Recopila información de contacto"""

        # Procesar con slot manager
        result = self.slot_manager.process_message(
            message=message,
            current_slots=context.get("slots_data", {}),
            current_slot_name=context.get("current_slot"),
            attempts=context.get("validation_attempts", {}),
            context=context
        )

        # Si no está completo, pedir siguiente slot
        if not result.completed:
            return {
                "response": result.next_prompt,
                "context_updates": {
                    "current_module": self.name,
                    "conversation_state": "collecting_slots",
                    "slots_data": result.filled_slots,
                    "current_slot": result.current_slot,
                    "validation_attempts": result.attempts
                }
            }

        # Slots completos - guardar contacto
        return self._save_contact(result.filled_slots, context, phone)

    def _save_contact(self, slots_data, context, phone):
        """Guarda la información de contacto"""
        with get_db_context() as db:
            customer = db.query(Customer).filter(
                Customer.phone == phone
            ).first()

            if customer:
                customer.name = slots_data.get("name")
                customer.email = slots_data.get("email")
                db.commit()

        response = (
            f"✅ Información guardada:\n\n"
            f"Nombre: {slots_data.get('name')}\n"
            f"Email: {slots_data.get('email')}\n"
        )

        if slots_data.get("phone"):
            response += f"Teléfono: {slots_data.get('phone')}\n"

        response += "\n¿En qué más puedo ayudarte?"

        return {
            "response": response,
            "context_updates": {
                "current_module": None,
                "conversation_state": "completed",
                "slots_data": {},
                "current_slot": None,
                "validation_attempts": {}
            }
        }

    def get_required_slots(self) -> list:
        return self.SLOTS
```

### Ejemplo 3: Comunicación Entre Módulos

**Flujo: CartLinkModule → WebApp → CheckoutModule**

```python
# ═══════════════════════════════════════════════════
# MÓDULO 1: CartLinkModule
# ═══════════════════════════════════════════════════
class CartLinkModule:
    """Genera link de carrito"""

    def handle(self, message, context, phone):
        # 1. Crear sesión de carrito
        cart_session = cart_service.create_cart_session(
            customer_id=customer.id,
            hours_valid=24
        )

        # 2. Generar link
        cart_link = f"{settings.webapp_base_url}/cart/{cart_session.token}"

        # 3. ✨ COMUNICACIÓN: Guardar flags para otros módulos
        return {
            "response": f"🛒 Aquí está tu carrito: {cart_link}",
            "context_updates": {
                "current_module": None,
                "cart_session_token": cart_session.token,  # ← FLAG 1
                "awaiting_cart_completion": True           # ← FLAG 2
            }
        }

# BD después de CartLinkModule:
# context_data = {
#   "cart_session_token": "abc-123",
#   "awaiting_cart_completion": True
# }

# ═══════════════════════════════════════════════════
# WEBAPP API: Usuario completa carrito
# ═══════════════════════════════════════════════════
@router.post("/complete_cart")
async def complete_cart_webhook(data: Dict):
    """Webhook de webapp al completar carrito"""

    # 1. Crear orden en BD
    order = Order(
        customer_id=customer.id,
        status="pending",
        # ... más campos
    )
    db.add(order)
    db.commit()

    # 2. ✨ COMUNICACIÓN: Actualizar contexto para CheckoutModule
    conversation.context_data = {
        "cart_session_token": "abc-123",
        "awaiting_cart_completion": False,      # ← Limpia
        "start_checkout": True,                 # ← FLAG: Activa CheckoutModule
        "checkout_order_id": str(order.id)      # ← DATO: ID de orden
    }
    db.commit()

    # 3. Enviar confirmación
    waha.send_text_message(
        phone,
        "✅ Carrito completado! Ahora necesito tu ubicación GPS..."
    )

# BD después de WebApp:
# context_data = {
#   "cart_session_token": "abc-123",
#   "awaiting_cart_completion": False,
#   "start_checkout": True,           ← NUEVO
#   "checkout_order_id": "uuid-789"   ← NUEVO
# }

# ═══════════════════════════════════════════════════
# MÓDULO 3: CheckoutModule
# ═══════════════════════════════════════════════════
class CheckoutModule:
    """Completa el checkout"""

    def handle(self, message, context, phone):
        # ✨ COMUNICACIÓN: Leer datos que WebApp dejó
        order_id = context.get("checkout_order_id")  # "uuid-789"

        logger.info(f"Procesando checkout para orden: {order_id}")

        # Procesar slot filling (GPS, referencia, pago)
        # ...

        # Cuando termina
        return {
            "response": "✅ Orden confirmada!",
            "context_updates": {
                "start_checkout": False,      # ← Limpia flag
                "checkout_order_id": None,    # ← Limpia dato
                "current_module": None
            }
        }

# BD después de CheckoutModule:
# context_data = {
#   "cart_session_token": "abc-123",
#   "awaiting_cart_completion": False,
#   "start_checkout": False,
#   "checkout_order_id": None
# }
```

---

## ✅ Buenas Prácticas

### 1. Limpieza de Contexto

**Siempre limpia los flags cuando terminas:**

```python
# ✅ BIEN
context_updates = {
    "my_flag": False,           # Limpia flag
    "my_data": None,            # Limpia dato
    "current_module": None      # Limpia módulo
}

# ❌ MAL
context_updates = {
    # No limpia nada, contamina el contexto
}
```

### 2. Nombres Descriptivos

**Usa nombres claros y específicos:**

```python
# ✅ BIEN
"awaiting_delivery_reuse_confirmation"  # Claro y específico

# ❌ MAL
"flag1"  # Confuso
"waiting"  # Ambiguo
```

### 3. Documentación de Flags

**Documenta qué flags usa tu módulo:**

```python
class MyModule:
    """
    Módulo que hace X cosa.

    FLAGS que usa:
    - my_custom_flag (bool): Indica si está esperando Y
    - my_custom_data (str): Contiene el ID de Z
    - my_custom_list (list): Lista de elementos W

    FLAGS que lee:
    - other_module_flag (bool): Flag del OtherModule
    """
```

### 4. Validación de Datos

**Siempre valida que los datos existen:**

```python
# ✅ BIEN
order_id = context.get("checkout_order_id")
if not order_id:
    logger.error("No hay checkout_order_id en contexto")
    return error_response

# ❌ MAL
order_id = context["checkout_order_id"]  # KeyError si no existe
```

### 5. Tipos de Datos Serializables

**Solo usa tipos que se puedan serializar a JSON:**

```python
# ✅ BIEN - Tipos primitivos
context_updates = {
    "order_id": str(order.id),      # String
    "quantity": 5,                  # Number
    "is_active": True,              # Boolean
    "items": ["a", "b", "c"],       # List
    "metadata": {"key": "value"}    # Dict
}

# ❌ MAL - Objetos no serializables
context_updates = {
    "order_object": order,          # SQLAlchemy object
    "datetime_obj": datetime.now(), # datetime object
    "set_data": {1, 2, 3}          # Set (no JSON)
}
```

### 6. Manejo de Errores

**Siempre maneja errores en handle():**

```python
def handle(self, message, context, phone):
    try:
        # Lógica del módulo
        # ...

        return {
            "response": response,
            "context_updates": {...}
        }

    except Exception as e:
        logger.error(f"❌ Error en {self.name}: {e}", exc_info=True)

        return {
            "response": "❌ Hubo un error. Por favor intenta de nuevo.",
            "context_updates": {
                "current_module": None,
                "conversation_state": "failed"
            }
        }
```

### 7. Logging Detallado

**Usa logs para debugging:**

```python
def handle(self, message, context, phone):
    logger.info(f"🔄 [{self.name}] Procesando mensaje de {phone}")
    logger.debug(f"   Mensaje: {message[:50]}...")
    logger.debug(f"   Contexto: {list(context.keys())}")

    # Lógica...

    logger.info(f"✅ [{self.name}] Completado con éxito")
```

---

## ❌ Anti-Patrones

### 1. No Compartir Objetos Python

```python
# ❌ MAL - No se puede serializar a JSON
context_updates = {
    "order_object": order,          # SQLAlchemy object
    "customer_obj": customer        # SQLAlchemy object
}

# ✅ BIEN - Solo IDs o datos primitivos
context_updates = {
    "order_id": str(order.id),      # String UUID
    "customer_id": str(customer.id) # String UUID
}
```

### 2. No Asumir que Existe

```python
# ❌ MAL - KeyError si no existe
if context["my_flag"]:
    do_something()

# ✅ BIEN - Retorna None si no existe
if context.get("my_flag"):
    do_something()
```

### 3. No Modificar Contexto Directamente

```python
# ❌ MAL - Modifica pero no guarda
context["my_flag"] = True  # No persiste en BD

# ✅ BIEN - Retorna en context_updates
return {
    "response": "...",
    "context_updates": {
        "my_flag": True  # Se guarda en BD
    }
}
```

### 4. No Olvidar Limpiar

```python
# ❌ MAL - No limpia al terminar
return {
    "response": "✅ Completado",
    "context_updates": {}  # current_module sigue activo
}

# ✅ BIEN - Limpia módulo y flags
return {
    "response": "✅ Completado",
    "context_updates": {
        "current_module": None,
        "my_flag": False,
        "my_data": None
    }
}
```

### 5. No Usar Slots cuando Deberías

```python
# ❌ MAL - Pedir todo en un solo mensaje
def handle(self, message, context, phone):
    response = "Dame nombre, email y teléfono (separados por comas)"
    # Usuario debe formatear específicamente

# ✅ BIEN - Usar slot filling
SLOTS = [
    SlotDefinition(name="name", ...),
    SlotDefinition(name="email", ...),
    SlotDefinition(name="phone", ...)
]
# Pide uno a la vez, valida cada uno
```

---

## 🐛 Troubleshooting

### Problema: Módulo no se activa

**Síntomas:**
- El módulo existe pero no se ejecuta
- `get_module()` retorna `None`

**Causas:**
1. Módulo no registrado en `lifespan()`
2. Intent no coincide
3. Typo en el nombre del intent

**Solución:**
```python
# 1. Verificar registro en main.py
registry = get_module_registry()
my_module = MyModule()
registry.register(my_module)  # ← Asegurar que esté aquí

# 2. Verificar intent
logger.info(f"Intent: {my_module.intent}")  # Debe coincidir

# 3. Listar módulos registrados
registry.list_modules()
```

### Problema: Contexto no se guarda

**Síntomas:**
- `context_updates` no persisten
- Valores se pierden entre mensajes

**Causas:**
1. No usar `flag_modified()` para campos JSON
2. No hacer `db.commit()`
3. Modificar contexto directamente

**Solución:**
```python
# En update_module_context()
conversation.context_data = new_data

# ⚡ CRÍTICO: Marcar como modificado
flag_modified(conversation, 'context_data')

# Guardar cambios
db.commit()
```

### Problema: Slots no validan correctamente

**Síntomas:**
- Acepta valores inválidos
- Rechaza valores válidos

**Causas:**
1. `validation_rules` incorrectas
2. Tipo de slot incorrecto
3. No usar `SlotManager`

**Solución:**
```python
# Revisar validation_rules
SlotDefinition(
    name="quantity",
    type=SlotType.NUMBER,  # ← Tipo correcto
    validation_rules={
        "min": 1,           # ← Reglas claras
        "max": 100
    }
)

# Usar SlotManager
result = self.slot_manager.process_message(...)
```

### Problema: Módulo se queda activo

**Síntomas:**
- `current_module` no se limpia
- Módulo procesa mensajes que no debería

**Causas:**
1. No retornar `current_module: None` al terminar
2. Error en la lógica que no limpia

**Solución:**
```python
# Siempre limpiar al terminar
return {
    "response": "✅ Completado",
    "context_updates": {
        "current_module": None,  # ← IMPORTANTE
        "conversation_state": "completed"
    }
}
```

### Problema: Comunicación entre módulos falla

**Síntomas:**
- Módulo B no lee datos de Módulo A
- Flags no se detectan

**Causas:**
1. Flag no guardado en `context_updates`
2. Nombre de flag diferente entre módulos
3. No leer de `context.get()`

**Solución:**
```python
# Módulo A: ESCRIBE
return {
    "response": "...",
    "context_updates": {
        "my_flag": True,      # ← Escribir con nombre claro
        "my_data": "value"
    }
}

# Módulo B: LEE
flag_value = context.get("my_flag")  # ← Leer con mismo nombre
data_value = context.get("my_data")
```

---

## 📚 Referencias

### Archivos Clave

- **BaseModule**: `app/modules/base_module.py`
- **ModuleRegistry**: `app/core/module_registry.py`
- **ContextManager**: `app/core/context_manager.py`
- **SlotDefinition**: `app/core/slots/slot_definition.py`
- **SlotManager**: `app/core/slots/slot_manager.py`
- **SyncWorker**: `app/services/sync_worker.py`

### Módulos Existentes

- **CartLinkModule**: `app/modules/cart_link_module.py`
- **CheckoutModule**: `app/modules/checkout_module.py`
- **CheckOrderModule**: `app/modules/check_order_module.py`
- **CancelOrderModule**: `app/modules/cancel_order_module.py`
- **RemoveFromOrderModule**: `app/modules/remove_from_order_module.py`
- **OfferProductModule**: `app/modules/offer_product_module.py`

### Documentación Relacionada

- **README.md**: Visión general del proyecto
- **API.md**: Documentación de endpoints REST
- **DATABASE.md**: Estructura de base de datos

---

## 🎓 Resumen

### Conceptos Clave

1. **Módulo** = Funcionalidad independiente para una intención
2. **Intent** = Qué quiere hacer el usuario
3. **Slot** = Información que necesita recopilar
4. **Contexto** = Buzón compartido entre módulos
5. **Registry** = Gestor central de módulos

### Flujo Típico

```
Mensaje → SyncWorker → ¿Módulo activo?
                            ↓
                          NO
                            ↓
                    Detectar Intent → Registry
                            ↓
                    Encontrar Módulo
                            ↓
                    module.handle()
                            ↓
                    context_updates → BD
                            ↓
                    Respuesta → Usuario
```

### Comunicación

```
Módulo A → context_updates → ContextManager → BD
                                              ↓
BD → ContextManager → context → Módulo B
```

### Puntos Importantes

✅ Los módulos NO se llaman directamente
✅ Usan contexto como buzón compartido
✅ Siempre limpiar flags al terminar
✅ Solo datos serializables a JSON
✅ Validar que los datos existan
✅ Usar nombres descriptivos
✅ Documentar flags que usa cada módulo

---

**¡Fin de la documentación! 🎉**

Para crear tu propio módulo, usa las plantillas y ejemplos en este documento.
