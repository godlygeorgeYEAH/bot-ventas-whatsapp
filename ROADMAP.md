# Roadmap

---

## 🔄 **CAMBIO DE ARQUITECTURA - NOVIEMBRE 2025**

### **Nuevo Enfoque: Bot como "Checkout Assistant"**

**Problema identificado:** El sistema de creación de órdenes en el bot es demasiado complejo:
- Múltiples estados de órdenes
- Validaciones cruzadas complicadas
- Agregar/eliminar productos en conversación
- Manejo de multi-producto
- Lógica de negocio distribuida entre muchos módulos

**Solución:** Separar responsabilidades entre **WebApp de Carrito** y **Bot de WhatsApp**

```
┌─────────────────────────────────────────────────────────────┐
│                   ARQUITECTURA NUEVA                        │
└─────────────────────────────────────────────────────────────┘

Usuario WhatsApp: "Quiero hacer un pedido"
        │
        ▼
┌──────────────────┐
│   Bot WhatsApp   │ ──▶ Genera link único de carrito
│   (Python)       │     https://tutienda.com/cart/abc123
└──────────────────┘
        │
        │ [Envía link]
        ▼
┌──────────────────┐
│   Usuario        │ ──▶ Abre link, ve productos con imágenes
└──────────────────┘     Agrega productos, ajusta cantidades
        │                 Click "Orden Lista"
        ▼
┌──────────────────┐
│   WebApp Cart    │ ──▶ Webhook al bot con orden completa
│   (Vue 3)        │     { products: [...], total: X }
└──────────────────┘
        │
        ▼
┌──────────────────┐
│   Bot WhatsApp   │ ──▶ "✅ Recibí tu orden de X productos"
│   (Python)       │     Pide GPS
└──────────────────┘     Pide método de pago
        │                 Confirma orden
        ▼
    ✅ Orden confirmada
```

### **Ventajas del Nuevo Enfoque**

#### Para el Bot (Mucho más simple):
- ❌ No más slot filling de productos
- ❌ No más CreateOrderModule complejo
- ❌ No más agregar/eliminar productos en conversación
- ❌ No más multi-producto handler
- ❌ No más validaciones de stock en chat
- ✅ **Solo maneja: Link → Recibir orden → GPS → Pago → Confirmar**

#### Para el Usuario (Mejor UX):
- ✅ Ve **imágenes** de todos los productos
- ✅ Interfaz **visual** para agregar/quitar
- ✅ Ve el **total** actualizado en tiempo real
- ✅ Puede **comparar** productos fácilmente
- ✅ Experiencia de **e-commerce moderna**

#### Para el Admin:
- ✅ Gestión centralizada de productos en dashboard
- ✅ Puede agregar campos complejos (tallas, colores, variantes)
- ✅ Analytics más precisos

---

## 🎯 Leyenda de Prioridades

- **!!!** = Extremadamente prioritario (bloqueante)
- **!!** = Muy prioritario (necesario para MVP)
- **!** = Prioritario (importante pero no bloqueante)
- **(sin !)** = Normal (mejoras futuras)

## ✅ = Completado | ⏳ = En Progreso | 🔄 = Refactorizar | ⬜ = Pendiente | ❌ = Deprecado

---

## **FASE 0: Refactorización de Arquitectura** ⏳ (85% COMPLETADO - Bug fixing pendiente)

### Nuevo Sistema de Carrito WebApp

- [✅] **!!!** **Diseño de base de datos para cart_sessions**
  - ✅ Tabla `cart_sessions` (token, customer_id, expires_at, used, order_id)
  - ✅ Índice único en `token`
  - ✅ Relaciones con Customer y Order
  - ✅ Migraciones aplicadas
  
- [✅] **!!!** **Backend: Sistema de links únicos**
  - ✅ Servicio `CartService` para generar tokens UUID
  - ✅ Endpoint `POST /api/cart/create` → genera link
  - ✅ Endpoint `GET /api/cart/{token}` → valida token
  - ✅ Endpoint `GET /api/cart/{token}/products` → devuelve productos
  - ✅ Endpoint `POST /api/cart/{token}/complete` → webhook desde webapp
  - ✅ Endpoint `GET /api/cart/{token}/status` → check estado
  - ✅ Expiración automática de tokens (configurable)
  - ✅ CORS configurado para webapp

- [✅] **!!!** **WebApp del Carrito (Frontend)**
  - ✅ Stack: Vue 3 + TypeScript + Vite + Element Plus + Pinia
  - ✅ Página de carrito con listado de productos
  - ✅ Agregar/quitar productos con clicks
  - ✅ Ajustar cantidades con +/-
  - ✅ Ver imágenes de productos
  - ✅ Total calculado en tiempo real
  - ✅ Botón "Confirmar Orden"
  - ✅ Validación de token en URL
  - ✅ Página de error si token inválido
  - ✅ **Carrito flotante con drawer** (botón FAB en top-right)
  - ✅ Responsive (mobile/desktop)
  - ✅ Loading states y feedback visual

- [✅] **!!!** **CartLinkModule (Bot)**
  - ✅ Reemplaza `CreateOrderModule` para inicio de orden
  - ✅ Genera link único cuando usuario quiere ordenar
  - ✅ Envía link por WhatsApp con instrucciones
  - ✅ Maneja sesiones activas (reenvía link si existe)
  - ✅ Guarda contexto esperando webhook
  - ⬜ Maneja timeout si usuario no completa carrito

- [⏳] **!!!** **CartWebhookHandler (Bot)** (85% completado)
  - ✅ Recibe orden completa desde webapp (en endpoint `/api/cart/{token}/complete`)
  - ✅ Valida estructura de datos
  - ✅ Crea orden en estado `pending` con productos
  - ✅ Actualiza contexto para activar `CheckoutModule`
  - ✅ Envía mensaje de confirmación por WhatsApp
  - ✅ Envía prompt de GPS automáticamente
  - ⚠️ **BUG PENDIENTE**: `slots_data` guardándose como lista en vez de dict
  - ⬜ Retry logic si webhook falla

- [⏳] **!!** **CheckoutModule (Bot) - Simplificado** (90% completado)
  - ✅ Estructura base del módulo
  - ✅ Integración con Slot-Filling (GPS, referencia, pago)
  - ✅ Definición de slots correcta (SlotType.LOCATION, TEXT, CHOICE)
  - ✅ Recibe orden desde webhook
  - ✅ Parsea GPS y guarda en delivery_latitude/longitude
  - ✅ Confirma orden cuando checkout completo (pending → confirmed)
  - ✅ Resumen final con ubicación y método de pago
  - ⚠️ **BUG PENDIENTE**: Error al procesar slots debido a `slots_data` como lista
  - ⚠️ **CORRECCIÓN APLICADA**: Validación en ContextManager para convertir lista a dict
  - ⬜ Testing completo del flujo GPS → Referencia → Pago

### Deprecación y Limpieza

- [🔄] **!!!** **Deprecar CreateOrderModule actual**
  - Marcar como `@deprecated`
  - Mantener temporalmente para referencia
  - Documentar qué partes se reutilizan en CheckoutModule
  - Eliminar después de validar nuevo flujo

- [🔄] **!!** **Deprecar MultiProductHandler**
  - Ya no es necesario en el bot
  - La webapp maneja múltiples productos
  - Eliminar después de refactorización completa

- [🔄] **!** **Simplificar OfferProductModule**
  - Cambiar para que envíe link de carrito pre-llenado
  - Ej: `https://tutienda.com/cart/abc123?suggested=laptop-hp-15`
  - Webapp pre-agrega productos sugeridos

### Testing de la Nueva Arquitectura

- [✅] **!!** Test de generación de links únicos (manual con script Python)
- [✅] **!!** Test de validación de tokens
- [✅] **!!** Test de obtener productos
- [⏳] **!!** Test E2E: Link → Webapp → Checkout → Confirmación (parcial - bug en slots_data)
- [✅] **!!** Test de webhook desde webapp (funcional con bug)
- [⬜] **!** Test de expiración de tokens
- [⬜] **!** Test de links usados (no reutilizables)
- [⬜] **!** Test automatizado con pytest

### Documentación

- [⬜] **!!** `ARCHITECTURE_CHANGE.md` - Explicar el cambio
- [⬜] **!!** `WEBAPP_CART_SETUP.md` - Guía de setup de webapp
- [⬜] **!** Diagrama de secuencia del nuevo flujo
- [⬜] **!** Guía de migración para órdenes existentes

---

## **FASE 1: Fundamentos del Sistema** ✅ (COMPLETADA)

### Base de Datos y Modelos

- [x] ✅ Diseño del esquema de base de datos
- [x] ✅ Modelo `Customer` (clientes)
- [x] ✅ Modelo `Conversation` (conversaciones)
- [x] ✅ Modelo `Message` (mensajes)
- [x] ✅ Modelo `Product` (productos)
- [x] ✅ Modelo `ProductCategory` (categorías)
  - 📝 **Uso**: Filtrar productos por categoría en webapp
- [x] ✅ Modelo `Order` (órdenes)
- [x] ✅ Modelo `OrderItem` (items de órdenes)
- [x] ✅ Migraciones y seeds de datos de prueba

### Repositorios y Servicios Base

- [x] ✅ `CustomerRepository` (CRUD clientes)
- [x] ✅ `ConversationRepository` (CRUD conversaciones)
- [x] ✅ `MessageRepository` (CRUD mensajes)
- [x] ✅ `ProductRepository` (CRUD productos)
- [x] ✅ `OrderRepository` (CRUD órdenes)
- [x] ✅ `ProductService` (búsqueda fuzzy, gestión stock, validaciones)
- [x] ✅ `OrderService` (crear, confirmar, cancelar órdenes, cálculos de totales)

### Infraestructura Core

- [x] ✅ Configuración de base de datos SQLAlchemy
- [x] ✅ Sistema de logging con Loguru
- [x] ✅ Configuración de settings con Pydantic
- [x] ✅ Cliente WAHA para WhatsApp
- [x] ✅ Integración con Ollama (proxy HTTP + worker síncrono)
- [x] ✅ Context Manager para gestión de contexto
- [x] ✅ Message Buffer Manager (debouncing de mensajes - 40 segundos)

---

## **FASE 2: Sistema de Slot-Filling** ✅ (COMPLETADA - Reutilizable)

**Nota**: Este sistema se reutilizará en `CheckoutModule` para pedir GPS, referencia y método de pago.

- [x] ✅ `SlotDefinition` (definición de slots)
- [x] ✅ `SlotType` (tipos de datos)
- [x] ✅ `SlotExtractor` (extracción de valores)
- [x] ✅ `SlotValidator` (validación de datos)
- [x] ✅ `SlotManager` (orquestación)
- [x] ✅ Sistema de ejemplos y prompts dinámicos
- [x] ✅ Extracción inteligente con LLM
- [x] ✅ Validación de stock en tiempo real *(Ya no necesario en bot)*
- [x] ✅ Sistema de sugerencias de productos *(Mover a webapp)*
- [x] ✅ Selección ordinal de productos *(Ya no necesario en bot)*

---

## **FASE 3: Módulos de Conversación** 🔄 (REFACTORIZACIÓN MAYOR)

### CartLinkModule ⬜ (NUEVO - Prioridad Máxima)

**Reemplaza el inicio de CreateOrderModule**

- [⬜] **!!!** Estructura base del módulo
- [⬜] **!!!** Generar link único de carrito
- [⬜] **!!!** Enviar link por WhatsApp con instrucciones claras
- [⬜] **!!** Guardar contexto esperando webhook
- [⬜] **!!** Manejo de timeout (si usuario no completa en X tiempo)
- [⬜] **!** Permitir regenerar link si expiró
- [⬜] **!** Analytics: cuántos links generados vs completados

### CheckoutModule ⬜ (NUEVO - Simplificado)

**Reemplaza la parte de checkout de CreateOrderModule**

- [⬜] **!!!** Estructura base del módulo
- [⬜] **!!!** Integración con Slot-Filling (solo 3 slots)
  - `delivery_location` (GPS)
  - `delivery_reference` (texto)
  - `payment_method` (choice)
- [⬜] **!!!** Recibir orden desde webhook (productos ya confirmados)
- [⬜] **!!!** Crear orden en estado `pending`
- [⬜] **!!!** Confirmar orden cuando checkout completo
- [⬜] **!!** Ofrecimiento de última ubicación conocida (reutilizar código)
- [⬜] **!!** Validación de ubicación GPS
- [⬜] **!** Resumen final con productos y total

### CreateOrderModule ❌ (DEPRECADO)

**Será reemplazado por CartLinkModule + CheckoutModule**

- [x] ✅ ~~Estructura base del módulo~~ (Deprecar)
- [x] ✅ ~~Integración con Slot-Filling~~ (Mover a CheckoutModule)
- [x] ✅ ~~Búsqueda de productos~~ (Mover a webapp)
- [x] ✅ ~~Validación de stock~~ (Mover a webapp)
- [x] ✅ ~~Sistema de multi-producto~~ (Mover a webapp)
- [x] ✅ ~~Detección de cantidades~~ (Mover a webapp)
- [x] ✅ ~~Ofrecimiento de ubicación~~ (Reutilizar en CheckoutModule)
- [🔄] **Mantener temporalmente para referencia**
- [🔄] **Extraer código reutilizable a CheckoutModule**
- [❌] **Eliminar después de validar nuevo flujo**

### CheckOrderModule ✅ (MANTENER - No cambia)

- [x] ✅ Estructura base del módulo
- [x] ✅ Búsqueda automática de última orden
- [x] ✅ Detección de intención con LLM
- [x] ✅ Mostrar detalles completos
- [x] ✅ Formato visual con emojis
- [x] ✅ Enlaces a Google Maps
- [x] ✅ Documentación completa
- [⏳] **!!** Testing con WhatsApp real
- [⬜] **!** Tracking de envío avanzado

### RemoveFromOrderModule 🔄 (SIMPLIFICAR)

**Cambiar enfoque: Enviar link de carrito para modificar**

- [🔄] **!!** Cambiar a enviar link de carrito con orden actual
- [🔄] **!!** Usuario modifica productos en webapp
- [🔄] **!!** Webhook actualiza orden
- [❌] Eliminar lógica compleja de remover productos en chat
- [❌] Eliminar slot-filling para eliminar productos

### CancelOrderModule ⬜ (Mantener - Más simple ahora)

- [⬜] **!** Estructura base del módulo
- [⬜] **!** Validación de cancelación (solo pending/confirmed)
- [⬜] **!** Restaurar stock automáticamente
- [⬜] **!** Notificación de cancelación
- [⬜] Política de cancelación (tiempo límite)

### OfferProductModule 🔄 (SIMPLIFICAR)

**Cambiar a enviar link de carrito pre-llenado**

- [🔄] **!!** Enviar link con productos sugeridos
- [🔄] **!!** URL: `/cart/abc123?suggested=product-id`
- [🔄] **!!** Webapp pre-agrega productos sugeridos
- [x] ✅ ~~Lógica de detección de productos ofrecidos~~ (Mantener)
- [❌] Eliminar lógica de agregar productos en chat

### FAQModule ⬜ (Mantener)

- [⬜] **!** Estructura base del módulo
- [⬜] **!** Base de conocimiento
- [⬜] **!** Búsqueda semántica con LLM
- [⬜] Respuestas contextuales
- [⬜] Escalamiento a agente humano

### GreetingModule ⬜ (Mantener - Actualizar mensaje)

- [⬜] **!** Manejo de saludos
- [⬜] **!** Presentación del bot
- [⬜] **!!** Mencionar nuevo sistema de carrito en menú
- [⬜] **!** Menú de opciones actualizado
- [⬜] Personalización por horario

### FallbackModule ⬜ (Prioridad Alta)

- [⬜] **!!** Manejo de mensajes no entendidos
- [⬜] **!!** Sugerencias inteligentes
- [⬜] **!** Opciones de ayuda

---

## **FASE 4: Integración y Worker** ✅ (COMPLETADA - Actualizar)

### SyncWorker

- [x] ✅ Estructura básica del worker
- [x] ✅ Cola de mensajes (queue)
- [x] ✅ Procesamiento síncrono
- [x] ✅ Detección de intenciones con LLM
- [x] ✅ Generación de respuestas con LLM
- [x] ✅ Integración con módulos
- [⏳] **!!** Actualizar para nuevos módulos (CartLink, Checkout)
- [⏳] **!!** Testing continuo con WhatsApp real
- [⬜] **!** Manejo de reintentos
- [⬜] **!** Dead letter queue para errores
- [⬜] Rate limiting

### ModuleRegistry

- [x] ✅ Registro de módulos
- [x] ✅ Búsqueda de módulos por intención
- [x] ✅ Gestión de módulos activos
- [x] ✅ Inicialización en ciclo de vida
- [⏳] **!!** Registrar CartLinkModule
- [⏳] **!!** Registrar CheckoutModule
- [⏳] **!!** Deprecar CreateOrderModule
- [⬜] **!** Priorización de módulos
- [⬜] Registro dinámico de módulos

### ContextManager

- [x] ✅ Guardar/recuperar contexto
- [x] ✅ Gestión de slots
- [x] ✅ Gestión de módulos activos
- [x] ✅ Métodos para actualizar contexto
- [x] ✅ Persistencia robusta con `flag_modified`
- [x] ✅ Manejo de campos JSON y diccionarios
- [⏳] **!!** Agregar contexto para cart tokens
- [⏳] **!!** Agregar contexto para órdenes desde webhook
- [⬜] **!** Limpieza automática de contextos antiguos
- [⬜] Timeout de conversaciones inactivas

---

## **FASE 4.5: WebApp del Carrito** ⬜ (NUEVA FASE - Prioridad Máxima)

### Backend API

- [⬜] **!!!** `POST /api/cart/create` - Crear sesión de carrito
- [⬜] **!!!** `GET /api/cart/{token}` - Obtener productos y validar token
- [⬜] **!!!** `POST /api/cart/{token}/complete` - Webhook de orden completa
- [⬜] **!!** `GET /api/cart/{token}/status` - Check si completado
- [⬜] **!!** Validación de expiración de tokens
- [⬜] **!** `DELETE /api/cart/{token}` - Cancelar sesión
- [⬜] **!** Analytics de conversión (cuántos completan)

### Frontend WebApp

- [⬜] **!!!** Setup inicial (Vue 3 + TypeScript + Vite)
- [⬜] **!!!** Layout del carrito responsive
- [⬜] **!!!** Listado de productos con imágenes
- [⬜] **!!!** Agregar/quitar productos (botones)
- [⬜] **!!!** Ajustar cantidades (+/-)
- [⬜] **!!!** Total calculado en tiempo real
- [⬜] **!!!** Botón "Marcar como Lista" / "Confirmar Orden"
- [⬜] **!!** Validación de token en URL
- [⬜] **!!** Mensaje si token expiró o inválido
- [⬜] **!!** Validación de stock en tiempo real
- [⬜] **!** Búsqueda/filtro de productos
- [⬜] **!** Categorías de productos
- [⬜] **!** Detalles de producto (modal)
- [⬜] **!** Productos sugeridos (si viene en URL)
- [⬜] Loading states y UX feedback
- [⬜] Error handling

### Integración

- [⬜] **!!!** Webhook de webapp → bot cuando orden completa
- [⬜] **!!!** Formato de datos: `{ cart_token, products: [{id, qty}], total }`
- [⬜] **!!** Validación de firma/autenticación de webhook
- [⬜] **!!** Retry logic si webhook falla
- [⬜] **!** Notificación al usuario si hay error

### Deployment

- [⬜] **!!** Build de producción (Vite)
- [⬜] **!!** Hosting del frontend (Netlify/Vercel/VPS)
- [⬜] **!** CDN para imágenes de productos
- [⬜] **!** SSL/HTTPS configurado
- [⬜] Environment variables para API URLs

---

## **FASE 5: Manejo de Errores y Robustez** ⏳ (EN PROGRESO)

- [x] ✅ Manejo de errores de LLM (timeout, conexión)
- [x] ✅ Logging estructurado con Loguru
- [⬜] **!!!** Manejo de errores de red (WhatsApp)
- [⬜] **!!!** Manejo de errores de BD con reintentos
- [⬜] **!!** Reintentos automáticos configurables
- [⬜] **!!** Alertas para errores críticos
- [⬜] **!!** Manejo de webhook failures (retry logic)
- [⬜] **!** Circuit breaker para servicios externos
- [⬜] **!** Fallback cuando LLM no responde
- [⬜] Métricas de errores

---

## **FASE 6: Testing y Calidad** ⏳ (EN PROGRESO)

### Tests Unitarios

- [x] ✅ Test de CreateOrderModule básico *(Deprecar)*
- [x] ✅ Scripts de testing de integración
- [⬜] **!!!** Tests de CartService (generar tokens)
- [⬜] **!!!** Tests de webhook handler
- [⬜] **!!** Tests de CheckoutModule
- [⬜] **!!** Tests de CartLinkModule
- [⬜] **!!** Tests de expiración de tokens
- [⬜] **!** Tests de SlotValidator
- [⬜] **!** Tests de ProductService
- [⬜] **!** Tests de OrderService

### Tests de Integración

- [x] ✅ Flujo completo de crear orden (manual) *(Deprecar)*
- [x] ✅ Flujo completo de consultar orden (manual)
- [⬜] **!!!** Suite E2E: Link → Webapp → Webhook → Checkout → Confirmación
- [⬜] **!!** Test de webapp con Cypress/Playwright
- [⬜] **!!** Test de webhook con mocks
- [⬜] **!** Conversaciones multi-turno
- [⬜] **!** Manejo de interrupciones

### Tests de Carga

- [⬜] **!** Múltiples usuarios simultáneos
- [⬜] **!** Rate limiting
- [⬜] **!** Carga de webapp (muchos productos)
- [⬜] Stress testing del worker

---

## **FASE 7: Mejoras de UX** ⏳ (EN PROGRESO)

### Bot WhatsApp

- [x] ✅ Mensajes de confirmación claros
- [x] ✅ Indicadores de progreso (typing...)
- [x] ✅ Validación de entrada amigable
- [x] ✅ Mensajes de error amigables
- [⬜] **!!** Instrucciones claras para usar webapp
- [⬜] **!!** Notificaciones de progreso ("Recibí tu orden...")
- [⬜] **!** Botones de respuesta rápida (WhatsApp buttons)
- [⬜] **!** Reenviar link si usuario lo pierde
- [⬜] Emojis contextuales avanzados

### WebApp Carrito

- [⬜] **!!** Onboarding/tutorial primera vez
- [⬜] **!!** Animaciones suaves (agregar/quitar)
- [⬜] **!!** Preview de imágenes grandes
- [⬜] **!** Búsqueda con sugerencias
- [⬜] **!** Filtros por categoría
- [⬜] **!** "Productos que te pueden gustar"
- [⬜] Toast notifications para acciones
- [⬜] Loading skeletons
- [⬜] Empty states informativos

---

## **FASE 8: Funcionalidades Avanzadas** ⬜ (FUTURO)

### Pagos

- [⬜] **!** Integración con pasarela de pagos
- [⬜] **!** Pago directo en webapp
- [⬜] **!** Confirmación de pago
- [⬜] **!** Manejo de reembolsos
- [⬜] Facturación electrónica

### Notificaciones

- [⬜] **!** Notificación de orden creada
- [⬜] **!** Notificación de orden enviada
- [⬜] **!** Notificación de orden entregada
- [⬜] **!** Notificación si carrito abandonado (24h)
- [⬜] Recordatorios personalizados
- [⬜] Promociones por WhatsApp

### Carritos Avanzados

- [⬜] **!** Guardar carrito para después
- [⬜] **!** Compartir carrito con otra persona
- [⬜] **!** Cupones de descuento
- [⬜] Wishlists
- [⬜] Carritos recurrentes

### Gestión de Clientes

- [x] ✅ Perfil básico de cliente
- [x] ✅ Historial de órdenes básico
- [⬜] **!** Direcciones guardadas múltiples
- [⬜] **!** Métodos de pago guardados
- [⬜] Preferencias de comunicación
- [⬜] Programa de lealtad

### Catálogo Avanzado

- [x] ✅ Búsqueda fuzzy de productos
- [⬜] **!!** Imágenes de productos en webapp
- [⬜] **!!** Gestión de imágenes en dashboard
- [⬜] **!** Categorías visuales
- [⬜] **!** Filtros (precio, marca, etc.)
- [⬜] **!** Productos relacionados
- [⬜] Reviews y ratings
- [⬜] Productos en oferta

---

## **FASE 9: Dashboard Administrativo** ⏳ (EN PROGRESO - 60%)

### Frontend Admin ✅

- [x] ✅ Diseño moderno con Vue 3 + TypeScript + Vite
- [x] ✅ Element Plus
- [x] ✅ Layout responsive
- [x] ✅ Router configurado
- [x] ✅ 100% Responsive
- [x] ✅ Acceso desde red local
- [⬜] **!** Autenticación y autorización
- [x] ✅ Dashboard con KPIs

### Gestión de Órdenes ✅ (COMPLETADO)

- [x] ✅ **!!** Lista de órdenes
- [x] ✅ **!!** Detalles expandibles
- [x] ✅ **!!** KPIs en tiempo real
- [x] ✅ **!!** Cambiar estado
- [x] ✅ **!!** Cancelar orden
- [x] ✅ **!!** Eliminar orden
- [x] ✅ **!** Filtros por estado
- [x] ✅ **!** Búsqueda
- [x] ✅ **!** Enlaces a Google Maps
- [x] ✅ **!** Vista mobile
- [x] ✅ **!** Sidebar colapsable
- [⬜] **!** Ver orden completa desde webapp (link)
- [⬜] **!** Exportar órdenes (CSV)
- [⬜] Notas internas
- [⬜] Historial de cambios

### Backend API ✅ (COMPLETADO)

- [x] ✅ GET /api/orders
- [x] ✅ GET /api/orders/stats
- [x] ✅ GET /api/orders/{id}
- [x] ✅ PUT /api/orders/{id}/status
- [x] ✅ POST /api/orders/{id}/cancel
- [x] ✅ DELETE /api/orders/{id}
- [x] ✅ CORS configurado

### Gestión de Productos ⬜ (PRIORIDAD ALTA)

- [⬜] **!!!** CRUD de productos
- [⬜] **!!!** Subir imágenes de productos
- [⬜] **!!!** Gestión de stock en tiempo real
- [⬜] **!!** Gestión de categorías
- [⬜] **!** Carga masiva (CSV/Excel)
- [⬜] **!** Preview de cómo se ve en webapp
- [⬜] Variantes de productos
- [⬜] Productos destacados/ofertas

### Gestión de Clientes ⬜ (PENDIENTE)

- [⬜] **!** Lista de clientes
- [⬜] **!** Perfil detallado
- [⬜] **!** Historial de conversaciones
- [⬜] **!** Historial de compras
- [⬜] Segmentación
- [⬜] Exportar lista

### Analytics del Carrito ⬜ (NUEVO)

- [⬜] **!!** Tasa de conversión (links → órdenes)
- [⬜] **!!** Tiempo promedio en webapp
- [⬜] **!** Productos más agregados/removidos
- [⬜] **!** Tasa de abandono de carrito
- [⬜] **!** Heatmap de interacciones
- [⬜] Analytics de productos más vistos

### Analytics General ⬜

- [⬜] **!** Gráfico de ventas por período
- [⬜] **!** Productos más vendidos
- [⬜] **!** Top clientes
- [⬜] **!** Tiempo promedio de respuesta
- [⬜] Alertas de bajo stock
- [⬜] Reportes exportables

---

## **FASE 10: Optimización y Escalabilidad** ⬜ (FUTURO)

### Performance

- [⬜] **!** Cache de productos en memoria (Redis)
- [⬜] **!** Cache de imágenes (CDN)
- [⬜] **!** Optimización de queries BD
- [⬜] **!** Lazy loading de imágenes en webapp
- [⬜] Índices compuestos en BD
- [⬜] Connection pooling
- [⬜] Image optimization (WebP, thumbnails)

### Escalabilidad

- [⬜] **!** Múltiples workers
- [⬜] **!** Load balancing para FastAPI
- [⬜] **!** Queue distribuida (Redis)
- [⬜] **!** Replicación de BD
- [⬜] Microservicios
- [⬜] Containerización (Docker)
- [⬜] Orquestación (Kubernetes)

### Monitoreo

- [⬜] **!!** Health checks
- [⬜] **!!** Métricas de sistema
- [⬜] **!** APM
- [⬜] **!** Logs centralizados
- [⬜] **!** Alertas automáticas
- [⬜] Dashboards de monitoreo
- [⬜] Trazabilidad de requests

---

## **FASE 11: Seguridad** ⬜ (FUTURO - Crítico para producción)

- [⬜] **!!!** Encriptación de datos sensibles
- [⬜] **!!!** Autenticación de webhooks (firma HMAC)
- [⬜] **!!** Rate limiting por usuario
- [⬜] **!!** Validación de números WhatsApp
- [⬜] **!!** Protección contra spam
- [⬜] **!!** CORS restrictivo en producción
- [⬜] **!** HTTPS obligatorio
- [⬜] **!** Backup automático de BD
- [⬜] **!** Protección CSRF en webapp
- [⬜] **!** XSS protection
- [⬜] Auditoría de accesos
- [⬜] GDPR compliance
- [⬜] PCI DSS (pagos)

---

## **FASE 12: Internacionalización** ⬜ (FUTURO)

- [⬜] Multi-idioma (Español, Inglés, Portugués)
- [⬜] Múltiples monedas
- [⬜] Formatos locales
- [⬜] Detección automática de idioma
- [⬜] Traducción de productos

---

## **FASE 13: Documentación** ⬜ (IMPORTANTE)

- [⬜] **!!!** `ARCHITECTURE_CHANGE.md` - Explicar nuevo enfoque
- [⬜] **!!** `WEBAPP_SETUP.md` - Setup de webapp
- [⬜] **!!** README actualizado con nueva arquitectura
- [⬜] **!!** Guía de instalación completa
- [⬜] **!!** Diagramas de arquitectura actualizados
- [⬜] **!** Documentación de API (OpenAPI)
- [⬜] **!** Guía de contribución
- [x] ✅ Documentación de CheckOrderModule
- [x] ✅ Documentación de acceso móvil
- [⬜] **!** Diagramas de flujo nuevos
- [⬜] Video tutorials

---

## 📊 **RESUMEN DEL ESTADO ACTUAL**

### ✅ **Completado (70+ tareas)**

- ✅ Infraestructura Core completa
- ✅ Base de datos y modelos
- ✅ Sistema de Slot-Filling (reutilizable)
- ✅ CheckOrderModule completo
- ✅ Dashboard de órdenes completo
- ✅ Sistema de logging robusto
- ✅ Worker síncrono funcionando
- ✅ Context Manager robusto

### 🔄 **En Refactorización**

- 🔄 CreateOrderModule → CartLinkModule + CheckoutModule
- 🔄 RemoveFromOrderModule → Enviar link de carrito
- 🔄 OfferProductModule → Link con productos sugeridos
- 🔄 MultiProductHandler → Mover a webapp

### ⏳ **En Progreso (Últimos Detalles)**

1. ⚠️ **!!!** **Bug Fix: slots_data como lista** (Corrección aplicada, requiere testing)
2. ⬜ **!!** Testing completo del flujo CheckoutModule
3. ⬜ **!!** Timeout de cart sessions si usuario no completa
4. ⬜ **!** Retry logic para webhook failures
5. ⬜ **!** Documentación del cambio arquitectónico

### ✅ **Recientemente Completado (Noviembre 2025)**

1. ✅ Diseño y creación de tabla `cart_sessions`
2. ✅ Backend completo de cart links (`CartService`)
3. ✅ API endpoints para cart (create, validate, products, complete, status)
4. ✅ WebApp del carrito (Vue 3 + TypeScript + Vite + Element Plus)
5. ✅ UI de carrito flotante con drawer
6. ✅ CartLinkModule funcionando
7. ✅ CheckoutModule implementado (con bug pendiente)
8. ✅ Webhook handler integrado
9. ✅ CORS configurado para múltiples orígenes

### 🎯 **Próximos Pasos Inmediatos (Completar implementación)**

**Prioridad Crítica (1-2 días):**
1. ⚠️ **Resolver bug de `slots_data` como lista**
   - Ya aplicada corrección en ContextManager
   - Requiere testing con orden nueva (no reusar contexto corrupto)
   - Verificar que slots_data se inicializa como `{}` en API
2. 🧪 **Testing E2E completo**
   - Flujo: "Quiero ordenar" → Link → WebApp → Productos → Confirmar → GPS → Referencia → Pago → Confirmación
   - Verificar todos los mensajes del bot
   - Confirmar que la orden se marca como `confirmed`

**Prioridad Alta (3-5 días):**
3. ⏰ **Timeout de cart sessions**
   - Notificar al usuario si no completa en X horas
   - Limpiar sesiones expiradas
4. 🔄 **Retry logic para webhooks**
   - Si falla el webhook, reintentar N veces
   - Notificar al admin si falla permanentemente
5. 📖 **Documentación**
   - `ARCHITECTURE_CHANGE.md`
   - `WEBAPP_CART_SETUP.md`
   - Actualizar README principal

---

## 📈 **Progreso General del Proyecto**

```
FASE 0 (Refactorización):  █████████████████░░░  85% ⏳ (Bug fixing pendiente)
Fase 1 (Fundamentos):      ████████████████████ 100% ✅
Fase 2 (Slot-Filling):     ████████████████████ 100% ✅
Fase 3 (Módulos):          ████████░░░░░░░░░░░░  40% 🔄 (CartLink ✅, Checkout ⏳, CheckOrder ✅)
Fase 4 (Integración):      ███████████████████░  95% ⏳ (Actualizado para nuevos módulos)
Fase 4.5 (WebApp Cart):    ████████████████████ 100% ✅ (Completado!)
Fase 5 (Errores):          ████████░░░░░░░░░░░░  40% ⏳
Fase 6 (Testing):          ██████░░░░░░░░░░░░░░  30% ⏳
Fase 7 (UX):               ███████████████░░░░░  75% ⏳
Fase 9 (Dashboard):        ████████████░░░░░░░░  60% ⏳

PROGRESO TOTAL ACTUAL:     ███████████████░░░░░  75% ⏳
MVP POST-REFACTOR:         █████████████████░░░  85% 🎯 (Falta: bug fix + testing)
PRODUCCIÓN LISTA:          ████████████████░░░░  80% 🚀 (Falta: docs + deployment)
```

### 🎯 **Hitos Alcanzados Esta Semana**

- ✅ **Arquitectura Bot + WebApp implementada** (85%)
- ✅ **Frontend Vue 3 del carrito completo y funcional**
- ✅ **Backend de cart sessions y API completo**
- ✅ **Integración webhook webapp → bot funcionando**
- ✅ **CartLinkModule reemplazando CreateOrderModule**
- ⏳ **CheckoutModule casi completo** (bug en proceso de resolución)

---

## 🎯 **Roadmap para MVP con Nueva Arquitectura**

### Core Bot (3-4 semanas)

- [⬜] **!!!** CartLinkModule
- [⬜] **!!!** CheckoutModule
- [⬜] **!!!** Webhook handler
- [x] ✅ CheckOrderModule
- [⬜] **!!** FallbackModule
- [⬜] **!** CancelOrderModule
- [⬜] **!** GreetingModule actualizado

### WebApp Carrito (2-3 semanas)

- [⬜] **!!!** Setup y estructura
- [⬜] **!!!** UI del carrito funcional
- [⬜] **!!!** Integración con API
- [⬜] **!!!** Webhook a bot
- [⬜] **!!** Validación de tokens
- [⬜] **!** Responsive design

### Dashboard Admin (1-2 semanas adicionales)

- [x] ✅ Panel de órdenes
- [⬜] **!!!** Gestión de productos + imágenes
- [⬜] **!** Gestión de clientes
- [⬜] **!** Analytics de carrito

### Testing y Deployment (1 semana)

- [⬜] **!!** Tests E2E completos
- [⬜] **!!** Deployment de webapp
- [⬜] **!** Documentación actualizada
- [⬜] **!** Scripts de backup

**Estimación Total MVP**: **4-6 semanas** (más largo inicialmente, pero mucho más mantenible)

---

## 🎉 **Ventajas del Nuevo Enfoque**

### ✨ Para el Usuario
1. **Experiencia visual moderna** - Ve fotos, compara fácilmente
2. **Control total** - Agrega/quita sin límites de conversación
3. **Velocidad** - No espera respuestas del bot para cada producto
4. **Familiaridad** - UX de e-commerce conocida

### 🚀 Para el Desarrollo
1. **Bot 70% más simple** - Solo checkout, no gestión de productos
2. **Separación de responsabilidades** - Cada componente tiene un rol claro
3. **Más fácil de mantener** - Menos lógica compleja en el bot
4. **Más escalable** - Webapp puede crecer independientemente

### 💼 Para el Negocio
1. **Mejor conversión** - UX visual aumenta ventas
2. **Menos abandonos** - Proceso más fluido
3. **Analytics más ricos** - Ver qué productos se agregan/quitan
4. **Fácil agregar features** - Wishlist, cupones, etc.

---

## 📝 **Notas Importantes**

### ⚠️ Cambios Importantes

1. **CreateOrderModule será deprecado** - Código complejo que se reemplaza
2. **Slot-filling de productos eliminado** - Se hace en webapp
3. **Nueva tabla en BD** - `cart_sessions` para tokens
4. **Nuevo módulo prioritario** - CartLinkModule
5. **WebApp nuevo componente** - Requiere desarrollo frontend

### 🎯 Foco Inmediato

**Las próximas 2 semanas deben enfocarse en:**
1. Backend de cart links (CartService + API)
2. CartLinkModule y CheckoutModule
3. Setup básico de webapp
4. Webhook funcional

### 💡 Decisiones Pendientes

1. **¿Dónde hostear la webapp?** (Netlify/Vercel/VPS)
2. **¿CDN para imágenes?** (Cloudinary/S3/local)
3. **¿Framework CSS para webapp?** (TailwindCSS/Element Plus reutilizado)
4. **¿Pagos en webapp o bot?** (Decidir más adelante)

---

---

## 🐛 **Bugs Conocidos y Trabajo Pendiente**

### ⚠️ **Bug Crítico - En Resolución**

**`slots_data` guardándose como lista en lugar de dict**
- **Síntoma**: Al enviar GPS en CheckoutModule, falla con `'list' object has no attribute 'items'`
- **Causa**: Algún punto en el código está guardando `slots_data` como `[]` en lugar de `{}`
- **Corrección Aplicada**: 
  - ✅ API inicializa `slots_data={}` explícitamente
  - ✅ ContextManager valida y convierte lista a dict al leer/escribir
  - ✅ CheckoutModule pasa parámetros correctos a SlotManager
- **Requiere**: Testing con orden nueva (no reusar contexto corrupto de pruebas anteriores)
- **Archivos Modificados**:
  - `app/api/cart.py` (líneas 346-349)
  - `app/core/context_manager.py` (líneas 203-210, 282-290)
  - `app/modules/checkout_module.py` (líneas 90-96)

### 📋 **Trabajo Pendiente (Prioridad)**

1. **Testing E2E Completo** 🧪
   - Crear orden nueva y probar flujo completo
   - Verificar que slots_data se maneja correctamente
   - Confirmar que checkout completa exitosamente

2. **Timeout de Cart Sessions** ⏰
   - Implementar notificación si usuario no completa carrito en X horas
   - Job cron o background task para limpiar sesiones expiradas

3. **Retry Logic para Webhooks** 🔄
   - Si falla mensaje inicial de WhatsApp, reintentar
   - Queue de retry con backoff exponencial

4. **Documentación** 📖
   - `ARCHITECTURE_CHANGE.md` explicando el cambio
   - `WEBAPP_CART_SETUP.md` para setup del frontend
   - Actualizar README principal con nuevo flujo

---

**🎯 Estado: Refactorización 85% completada - Bug fixing en progreso**

**🚀 Objetivo: MVP completamente funcional en 2-3 días**

**📅 Actualizado: Noviembre 11, 2025**
