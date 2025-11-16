# 🤖 Bot de Ventas WhatsApp

> Sistema completo de e-commerce conversacional basado en WhatsApp con inteligencia artificial integrada.

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Ollama](https://img.shields.io/badge/Ollama-LLM-orange.svg)](https://ollama.ai/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 📋 Tabla de Contenidos

- [Descripción General](#-descripción-general)
- [Características Principales](#-características-principales)
- [Arquitectura](#️-arquitectura)
- [Tecnologías](#-tecnologías)
- [Requisitos](#-requisitos)
- [Instalación](#-instalación)
- [Configuración](#️-configuración)
- [Uso](#-uso)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Base de Datos](#️-base-de-datos)
- [API REST](#-api-rest)
- [Módulos](#-módulos)
- [Sistema de Intenciones](#-sistema-de-intenciones)
- [Flujo de Mensajes](#-flujo-de-mensajes)
- [Contribución](#-contribución)

---

## 🎯 Descripción General

**Bot de Ventas WhatsApp** es un sistema completo de comercio electrónico que permite a los clientes realizar pedidos, consultar estados, gestionar órdenes y navegar catálogos de productos mediante conversaciones naturales por WhatsApp.

### ¿Qué lo hace especial?

- 🧠 **Inteligencia Artificial integrada**: Usa Ollama (LLM local) para detectar automáticamente las intenciones del usuario
- 💬 **Conversaciones naturales**: Los clientes hablan como lo harían normalmente, sin comandos especiales
- 🛒 **WebApp moderna**: Carrito de compras con interface Vue.js para mejor experiencia
- 📍 **Geolocalización**: Soporte completo para ubicaciones GPS para delivery
- 🎙️ **Notas de voz**: Transcripción automática de mensajes de audio con Whisper
- 🔔 **Notificaciones automáticas**: Alertas a administradores sobre nuevas órdenes y eventos importantes

---

## ✨ Características Principales

### Para Clientes

- ✅ **Crear órdenes** usando WebApp de carrito moderno
- ✅ **Consultar estado** de pedidos activos en tiempo real
- ✅ **Cancelar órdenes** pendientes o confirmadas
- ✅ **Eliminar productos** de órdenes existentes
- ✅ **Ver catálogo** completo con imágenes y precios
- ✅ **Enviar notas de voz** (transcripción automática)
- ✅ **Compartir ubicación GPS** para delivery preciso
- ✅ **Métodos de pago flexibles** (efectivo, tarjeta, transferencia)

### Para Administradores

- 📊 **Dashboard administrativo** para gestionar órdenes y productos
- 🔔 **Notificaciones automáticas** de nuevas órdenes por WhatsApp
- 📦 **Monitor de órdenes abandonadas** (timeout configurable)
- 🛠️ **API REST completa** para integraciones
- 📈 **Reportes y estadísticas** de ventas
- ⚙️ **Sistema de configuración** dinámico

---

## 🏗️ Arquitectura

### Flujo Principal

```
┌─────────────┐
│   Cliente   │
│  WhatsApp   │
└──────┬──────┘
       │
       ↓
┌─────────────────────────────────────────┐
│          WAHA (WhatsApp API)            │
│    Recibe/Envía mensajes WhatsApp       │
└──────────────┬──────────────────────────┘
               │ webhook
               ↓
┌─────────────────────────────────────────┐
│         FastAPI Application             │
│      /webhook/waha endpoint             │
└──────────────┬──────────────────────────┘
               │
               ↓
┌─────────────────────────────────────────┐
│      Message Buffer Manager             │
│   Debouncing (15 segundos)              │
│   Agrupa mensajes rápidos               │
└──────────────┬──────────────────────────┘
               │
               ↓
┌─────────────────────────────────────────┐
│      Sync Message Worker                │
│   Procesamiento sincrónico en thread    │
└──────────────┬──────────────────────────┘
               │
       ┌───────┴───────┐
       │               │
       ↓               ↓
┌─────────────┐ ┌─────────────┐
│  Contexto   │ │   Módulo    │
│   Manager   │ │   Activo?   │
└──────┬──────┘ └──────┬──────┘
       │               │
       └───────┬───────┘
               │
               ↓
       ┌───────────────┐
       │ ¿Hay módulo?  │
       └───┬───────┬───┘
           │       │
          SÍ      NO
           │       │
           ↓       ↓
    ┌──────────┐ ┌──────────────┐
    │  Módulo  │ │    Intent    │
    │ .handle()│ │   Detector   │
    │          │ │ (Ollama LLM) │
    └────┬─────┘ └──────┬───────┘
         │              │
         └──────┬───────┘
                │
                ↓
       ┌─────────────────┐
       │  Orchestrator   │
       │  (Slot Filling) │
       └────────┬────────┘
                │
                ↓
       ┌─────────────────┐
       │    Respuesta    │
       │  Generada       │
       └────────┬────────┘
                │
        ┌───────┴────────┐
        ↓                ↓
   ┌─────────┐    ┌──────────┐
   │ Guardar │    │   WAHA   │
   │   BD    │    │  Client  │
   └─────────┘    └────┬─────┘
                       │
                       ↓
                ┌─────────────┐
                │   Cliente   │
                │  WhatsApp   │
                └─────────────┘
```

### Componentes Clave

1. **WAHA Client**: Integración con WhatsApp HTTP API
2. **Message Buffer**: Sistema de debouncing para agrupar mensajes
3. **Intent Detector**: IA (Ollama) para detectar intenciones
4. **Orchestrator**: Coordina módulos y slot filling
5. **Module System**: 7 módulos especializados
6. **Database Layer**: SQLAlchemy con soporte PostgreSQL/SQLite

---

## 🛠️ Tecnologías

### Backend
- **Python 3.9+**
- **FastAPI** - Framework web moderno y rápido
- **SQLAlchemy** - ORM para base de datos
- **Uvicorn** - Servidor ASGI
- **Loguru** - Sistema avanzado de logging

### Inteligencia Artificial
- **Ollama** - LLM local (llama3.2) para detección de intenciones
- **Whisper** - Transcripción de notas de voz

### Integraciones
- **WAHA** - WhatsApp HTTP API
- **PostgreSQL/SQLite** - Base de datos relacional

### Frontend
- **Vue.js 3** - WebApp del carrito
- **Vite** - Build tool
- **Tailwind CSS** - Estilos

---

## 📦 Requisitos

### Sistema
- Python 3.9 o superior
- PostgreSQL 12+ o SQLite 3.35+
- Ollama instalado y corriendo
- Node.js 16+ (para WebApp)

### Servicios Externos
- **WAHA** - Instancia corriendo (local o remota)
- **Ollama** - Modelo llama3.2 descargado

---

## 🚀 Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/bot-ventas-whatsapp.git
cd bot-ventas-whatsapp
```

### 2. Crear entorno virtual

```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Instalar Ollama y modelo

```bash
# Instalar Ollama (ver https://ollama.ai)
curl -fsSL https://ollama.ai/install.sh | sh

# Descargar modelo
ollama pull llama3.2:latest
```

### 5. Configurar base de datos

```bash
python scripts/setup_db.py
python scripts/seed_database.py  # Opcional: datos de prueba
```

### 6. Configurar WebApp (opcional)

```bash
cd webapp-cart
npm install
npm run dev
```

---

## ⚙️ Configuración

### Archivo `.env`

Crear archivo `.env` en la raíz del proyecto:

```env
# Application
APP_NAME=BotVentasWhatsApp
APP_ENV=development
DEBUG=false
LOG_LEVEL=INFO

# Server
HOST=0.0.0.0
PORT=8000
WEBHOOK_SECRET=tu_secreto_seguro_aqui

# WAHA Configuration
WAHA_BASE_URL=http://localhost:3000
WAHA_API_KEY=tu_api_key_de_waha
WAHA_SESSION_NAME=default

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:latest
OLLAMA_TIMEOUT=120

# Whisper Configuration
WHISPER_MODEL=base
WHISPER_LANGUAGE=es

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/bot_ventas
# O para SQLite:
# DATABASE_URL=sqlite:///./bot_ventas.db

# Redis (opcional)
REDIS_URL=redis://localhost:6379/0

# Business Rules
MAX_VALIDATION_ATTEMPTS=3
SESSION_TIMEOUT_MINUTES=30
MAX_CONTEXT_MESSAGES=10

# Message Buffering
MESSAGE_DEBOUNCE_SECONDS=15.0
ENABLE_MESSAGE_BUFFERING=true
MAX_BUFFERED_MESSAGES=4

# Feature Flags
ENABLE_VOICE_MESSAGES=true
ENABLE_IMAGE_MESSAGES=true
ENABLE_RATE_LIMITING=true
ENABLE_PRODUCT_OFFERS=true
OFFER_AFTER_ORDER=true
OFFER_AFTER_GREETING=true
OFFER_WITH_IMAGE=true
OFFER_IMAGE_AS_CAPTION=true

# WebApp Cart
WEBAPP_BASE_URL=http://localhost:5174
CART_SESSION_HOURS=24
```

### Configurar WAHA

1. Instalar WAHA según [documentación oficial](https://waha.devlike.pro/)
2. Escanear código QR para vincular WhatsApp
3. Configurar webhook apuntando a: `http://tu-servidor:8000/webhook/waha`

---

## 💻 Uso

### Iniciar el servidor

#### Modo normal
```bash
python run.py
```

#### Modo verbose (con logs detallados)
```bash
python run.py -v    # INFO level
python run.py -vv   # DEBUG level
python run.py -vvv  # TRACE level (máximo detalle)
```

### Scripts útiles

```bash
# Crear tablas de base de datos
python scripts/create_tables.py

# Sembrar productos de prueba
python scripts/seed_products.py

# Limpiar conversación de un usuario
python scripts/clear_conversation.py

# Ver órdenes confirmadas
python scripts/debug_confirmed_orders.py

# Gestionar órdenes (CLI)
python scripts/manage_orders.py
```

### Probar el bot

1. Enviar mensaje por WhatsApp al número vinculado
2. Ejemplos de mensajes:
   - "Hola" - Saludo inicial
   - "Quiero hacer un pedido" - Inicia proceso de orden
   - "¿Dónde está mi pedido?" - Consulta estado
   - "Quiero eliminar el mouse de mi orden" - Elimina producto
   - "Cancelar mi pedido" - Cancela orden

---

## 📁 Estructura del Proyecto

```
bot-ventas-whatsapp/
├── app/
│   ├── api/                    # Endpoints REST
│   │   ├── cart.py            # Gestión de carrito
│   │   ├── orders.py          # Gestión de órdenes
│   │   ├── products.py        # Catálogo de productos
│   │   └── settings.py        # Configuración
│   │
│   ├── clients/               # Integraciones externas
│   │   ├── waha_client.py    # Cliente WhatsApp
│   │   ├── ollama_client.py  # Cliente LLM
│   │   └── whisper_client.py # Transcripción de audio
│   │
│   ├── core/                  # Núcleo inteligente
│   │   ├── intent_detector.py      # Detección de intenciones
│   │   ├── orchestrator.py         # Orquestación
│   │   ├── context_manager.py      # Gestión de contexto
│   │   ├── confirmation_manager.py # Confirmaciones
│   │   └── slots/                  # Sistema de slots
│   │       ├── slot_definition.py
│   │       ├── slot_manager.py
│   │       ├── slot_validator.py
│   │       └── slot_extractor.py
│   │
│   ├── modules/               # Módulos de funcionalidad
│   │   ├── base_module.py
│   │   ├── cart_link_module.py
│   │   ├── checkout_module.py
│   │   ├── check_order_module.py
│   │   ├── create_order_module.py
│   │   ├── cancel_order_module.py
│   │   ├── remove_from_order_module.py
│   │   └── offer_product_module.py
│   │
│   ├── services/              # Servicios de negocio
│   │   ├── message_processor.py
│   │   ├── message_buffer.py
│   │   ├── sync_worker.py
│   │   ├── order_service.py
│   │   ├── cart_service.py
│   │   ├── product_service.py
│   │   ├── order_notification_service.py
│   │   ├── admin_notification_service.py
│   │   └── order_monitor_worker.py
│   │
│   ├── database/              # Capa de datos
│   │   ├── models.py         # Modelos SQLAlchemy
│   │   └── repository.py     # Repositorios
│   │
│   └── main.py               # Punto de entrada
│
├── config/                    # Configuración
│   ├── settings.py
│   ├── logging_config.py
│   ├── prompts.py
│   └── database.py
│
├── webapp-cart/              # Frontend Vue.js
│   ├── src/
│   ├── public/
│   └── package.json
│
├── dashboard/                # Dashboard admin
│
├── scripts/                  # Scripts de utilidad
│   ├── setup_db.py
│   ├── seed_database.py
│   ├── seed_products.py
│   └── manage_orders.py
│
├── static/                   # Archivos estáticos
│   └── products/            # Imágenes de productos
│
├── requirements.txt
├── run.py
├── .env.example
└── README.md
```

---

## 🗄️ Base de Datos

### Modelos Principales

#### **Customers** (Clientes)
- `id` (UUID) - ID único
- `phone` (String, único) - Teléfono WhatsApp
- `name` - Nombre del cliente
- `email` - Email
- `preferences` (JSON) - Preferencias
- `first_contact_at` / `last_contact_at` - Timestamps

#### **Conversations** (Conversaciones)
- `id` (UUID) - ID único
- `customer_id` (FK) - Cliente asociado
- `state` - Estado actual (idle, collecting_slots, confirming, etc.)
- `current_intent` - Intención detectada
- `current_module` - Módulo en ejecución
- `slots_data` (JSON) - Datos de slots recolectados
- `context_data` (JSON) - Contexto adicional

#### **Orders** (Órdenes)
- `id` (UUID) - ID único
- `order_number` (String, único) - Ej: ORD-20231115-001
- `customer_id` (FK) - Cliente
- `status` - pending, confirmed, shipped, delivered, cancelled, etc.
- `subtotal`, `tax`, `shipping_cost`, `discount`, `total`
- `delivery_latitude`, `delivery_longitude` - Coordenadas GPS
- `delivery_reference` - Referencia de ubicación
- `payment_method` - efectivo, tarjeta, transferencia

#### **Products** (Productos)
- `id` (UUID) - ID único
- `name` - Nombre del producto
- `description` - Descripción
- `price` - Precio unitario
- `stock` - Stock disponible
- `category` - Categoría
- `image_path` - Ruta de imagen
- `sku` (String, único) - SKU

#### **OrderItems** (Items de Orden)
- `id` (UUID) - ID único
- `order_id` (FK) - Orden asociada
- `product_id` (FK) - Producto
- `quantity` - Cantidad
- `unit_price` - Precio unitario (snapshot)
- `subtotal` - Total del item

#### **CartSessions** (Sesiones de Carrito)
- `id` (UUID) - ID único
- `token` (UUID, único) - Token para link público
- `customer_id` (FK) - Cliente
- `expires_at` - Fecha de expiración
- `used` - ¿Ya fue usado?
- `order_id` (FK) - Orden generada

### Estados de Orden

```
PENDING      → Creada, aguardando confirmación
CONFIRMED    → Cliente confirmó, lista para preparar
PROCESSING   → En preparación
SHIPPED      → Enviada con delivery
DELIVERED    → Entregada
CANCELLED    → Cancelada por cliente
REFUNDED     → Reembolsada
ABANDONED    → Timeout sin actividad
```

---

## 🔌 API REST

### Endpoints de Carrito

```http
POST /api/cart/create
GET /api/cart/session/{token}
POST /api/cart/complete_cart
POST /api/cart/validate_product
```

### Endpoints de Órdenes

```http
GET /api/orders
GET /api/orders/{order_id}
GET /api/orders/{order_number}/by-number
PUT /api/orders/{order_id}
DELETE /api/orders/{order_id}
```

### Endpoints de Productos

```http
GET /api/products
GET /api/products/{product_id}
POST /api/products
PUT /api/products/{product_id}
DELETE /api/products/{product_id}
```

### Endpoints de Configuración

```http
GET /api/settings
GET /api/settings/{key}
PUT /api/settings/{key}
POST /api/settings/{key}
```

### Webhook

```http
POST /webhook/waha
```

---

## 🎯 Módulos

### 1. **CartLinkModule**
- **Intent**: `create_order`
- **Función**: Genera link único para WebApp de carrito
- **Flujo**: Usuario solicita → Bot genera link → Usuario completa en webapp

### 2. **CheckoutModule**
- **Activación**: Webhook de webapp al completar carrito
- **Función**: Solicita GPS, dirección y método de pago
- **Slots**: `gps_location`, `delivery_reference`, `payment_method`

### 3. **CheckOrderModule**
- **Intent**: `check_order`
- **Función**: Muestra estado de última orden activa
- **Sin slots**: Respuesta inmediata

### 4. **RemoveFromOrderModule**
- **Intent**: `remove_from_order`
- **Función**: Elimina productos de orden existente
- **Prioridad**: Detección por regex ANTES de LLM
- **Palabras clave**: "eliminar", "quitar", "remover" + "orden"/"pedido"

### 5. **CancelOrderModule**
- **Intent**: `cancel_order`
- **Función**: Cancela órdenes pendientes o confirmadas
- **Requiere confirmación**: Sí

### 6. **OfferProductModule**
- **Intent**: Detectado automáticamente
- **Función**: Sugiere productos en oferta
- **Configurable**: Via settings (enable_product_offers)

---

## 🧠 Sistema de Intenciones

### Intenciones Soportadas

1. **greeting** - Saludos ("hola", "buenos días")
2. **create_order** - Hacer pedido ("quiero comprar", "necesito")
3. **check_order** - Consultar estado ("dónde está mi pedido")
4. **remove_from_order** - Eliminar producto ("quitar de mi orden")
5. **cancel_order** - Cancelar orden ("cancelar pedido")
6. **product_inquiry** - Consulta de productos ("qué productos tienen")
7. **help** - Ayuda ("qué puedes hacer")
8. **goodbye** - Despedida ("adiós", "gracias")
9. **other** - Conversación general

### Detección con IA

El sistema usa **Ollama (LLM local)** para detectar automáticamente la intención del usuario:

```python
# Ejemplo de respuesta del detector
{
  "intent": "create_order",
  "confidence": 0.95,
  "entities": {
    "product": "laptop",
    "quantity": 2
  },
  "requires_action": true
}
```

### Fallback con Regex

Para intenciones críticas como `remove_from_order`, el sistema usa **regex como fallback** antes de llamar al LLM, garantizando detección precisa.

---

## 🔄 Flujo de Mensajes

### 1. Recepción
```
Usuario envía mensaje → WAHA webhook → FastAPI
```

### 2. Buffering (Debouncing)
```
MessageBuffer agrega mensaje
Timer 15 segundos
Si llega otro mensaje → reinicia timer
Timer expira → procesa buffer combinado
```

### 3. Procesamiento
```
SyncWorker (thread sincrónico)
├─ Guardar mensaje en BD
├─ Obtener contexto de usuario
└─ ¿Hay módulo activo?
   ├─ SÍ → Enrutar a módulo
   └─ NO → Detectar intención
```

### 4. Detección de Intención
```
IntentDetector
├─ Regex fallback (remove_from_order)
├─ LLM Ollama (otras intenciones)
└─ Retorna: {intent, confidence, entities}
```

### 5. Orquestación
```
Orchestrator
├─ Obtener módulo para intent
├─ Verificar slots requeridos
├─ Slot filling si es necesario
└─ Ejecutar módulo
```

### 6. Respuesta
```
Módulo genera respuesta
├─ Guardar en BD
├─ Enviar por WAHA
├─ Actualizar contexto
└─ Marcar como leído
```

---

## ⚡ Características Avanzadas

### Message Buffering
- **Debouncing de 15 segundos** para agrupar mensajes rápidos
- Evita procesamiento múltiple innecesario
- Configurable via `MESSAGE_DEBOUNCE_SECONDS`

### Slot Filling System
- Recopilación progresiva de información
- Validación automática con LLM
- Reintentos configurables (max 3)
- Tipos: TEXT, NUMBER, LOCATION, CHOICE, DATE

### Context Management
- Estado persistente de conversación
- Soporte para datos personalizados (JSON)
- Timeout automático de sesiones
- Historial de mensajes limitado (configurable)

### Order Monitoring
- Worker que ejecuta cada 30 segundos
- Detecta órdenes abandonadas (>30 min sin actividad)
- Notifica automáticamente a admin
- Marca órdenes como "abandoned"

### Admin Notifications
- Notificaciones por WhatsApp a números configurados
- Ejecución en thread separado (no bloquea)
- Eventos: nueva orden, orden confirmada, errores, abandonos

---

## 🧪 Testing

### Scripts de prueba disponibles

```bash
# Probar conexión con WAHA
python scripts/test_waha_connection.py

# Probar Ollama
python scripts/test_ollama_connection.py

# Probar detección de intención
python scripts/test_intent_detection.py

# Probar flujo completo
python scripts/test_full_flow.py

# Probar slot filling
python scripts/test_slot_filling.py

# Probar productos
python scripts/test_products.py
```

---

## 🐛 Troubleshooting

### El bot no responde

1. Verificar que WAHA esté corriendo: `curl http://localhost:3000/health`
2. Verificar webhook configurado correctamente en WAHA
3. Revisar logs: `python run.py -vv`

### Ollama timeout

1. Verificar que Ollama esté corriendo: `ollama list`
2. Aumentar `OLLAMA_TIMEOUT` en `.env`
3. Usar modelo más pequeño: `ollama pull llama3.2:1b`

### Base de datos errores

1. Recrear tablas: `python scripts/create_tables.py`
2. Verificar `DATABASE_URL` en `.env`
3. Permisos de usuario de BD

---

## 📊 Configuración Avanzada

### Ajustar debouncing

```env
MESSAGE_DEBOUNCE_SECONDS=20.0  # Aumentar a 20 segundos
MAX_BUFFERED_MESSAGES=6        # Máximo 6 mensajes agrupados
```

### Timeout de órdenes abandonadas

```python
# En order_monitor_worker.py
ABANDONED_ORDER_TIMEOUT_MINUTES = 45  # Cambiar de 30 a 45 min
```

### Personalizar prompts

Editar `config/prompts.py` para ajustar prompts del LLM.

---

## 🤝 Contribución

Las contribuciones son bienvenidas. Por favor:

1. Fork el repositorio
2. Crear branch de feature (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push al branch (`git push origin feature/AmazingFeature`)
5. Abrir Pull Request

---

## 📝 Licencia

Este proyecto está bajo la Licencia MIT. Ver archivo `LICENSE` para más detalles.

---

## 👨‍💻 Autor

**Tu Nombre**
- GitHub: [@tu-usuario](https://github.com/tu-usuario)
- Email: tu-email@ejemplo.com

---

## 🙏 Agradecimientos

- [FastAPI](https://fastapi.tiangolo.com/) - Framework web
- [Ollama](https://ollama.ai/) - LLM local
- [WAHA](https://waha.devlike.pro/) - WhatsApp HTTP API
- [SQLAlchemy](https://www.sqlalchemy.org/) - ORM
- Comunidad open source

---

## 📞 Soporte

Si tienes preguntas o necesitas ayuda:

1. Abrir un [Issue](https://github.com/tu-usuario/bot-ventas-whatsapp/issues)
2. Revisar la [documentación](https://github.com/tu-usuario/bot-ventas-whatsapp/wiki)
3. Contactar al autor

---

**¡Gracias por usar Bot de Ventas WhatsApp!** 🚀
