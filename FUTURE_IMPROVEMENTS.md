# 🚀 Mejoras Futuras - TODOs Pendientes

## 📋 Tabla de Contenidos
1. [⚠️ CRÍTICO: Detección de Pérdida de Comunicación](#️-crítico-detección-de-pérdida-de-comunicación)
   - [Detección Reactiva (Principal)](#detección-reactiva-principal)
   - [Detección Proactiva (Complementaria)](#detección-proactiva-complementaria)
2. [Sistema de Notificaciones al Admin](#sistema-de-notificaciones-al-admin)
3. [Estado del Bot](#estado-del-bot)
4. [Panel de Administrador](#panel-de-administrador)
5. [Implementación Sugerida](#implementación-sugerida)
6. [Ejemplos y Escenarios de Testing](#ejemplos-y-escenarios-de-testing)

---

## ⚠️ CRÍTICO: Detección de Pérdida de Comunicación

Este sistema combina dos enfoques complementarios para detectar y manejar problemas de comunicación con WAHA.

### Detección Reactiva (Principal)

#### 🎯 Objetivo
Cuando el webhook de carrito falla, determinar si el problema es:
1. **Fallo del webhook solamente** (bot sigue comunicado con WAHA)
2. **Pérdida total de comunicación** con WAHA (estado crítico)

#### 🧠 Lógica de Detección

#### Escenario: Webhook de Carrito Falla (4 reintentos)

```
Usuario completa orden en webapp
    ↓
Bot intenta enviar mensajes iniciales
    ↓
❌ Fallan los 4 reintentos del webhook
    ↓
🔍 DIAGNÓSTICO DE COMUNICACIÓN
    ↓
    ├─ Intento 1: Mensaje simple al usuario
    │  "🤝 Hemos recibido tu orden. Un agente te atenderá pronto."
    │  
    │  ✅ Éxito → Bot comunicado, solo webhook falló
    │  ❌ Falla → Continuar diagnóstico
    │
    ├─ Intento 2: Notificación al administrador
    │  "🚨 Orden ORD-XXX requiere atención manual. 
    │   Usuario: +58 XXX. Webhook falló."
    │  
    │  ✅ Éxito → Bot comunicado, solo webhook falló
    │  ❌ Falla → Continuar diagnóstico
    │
    └─ AMBOS FALLARON
       ↓
       🚨 ESTADO CRÍTICO: BOT COMPLETAMENTE INCOMUNICADO
       ↓
       1. Log CRITICAL con toda la info
       2. Actualizar bot_status → "incommunicado_critico"
       3. Alerta visual en panel de admin
       4. (Futuro) Email/SMS urgente al admin
       5. (Futuro) Webhook a sistema de monitoreo externo
```

#### 📊 Estados Resultantes

##### ✅ **Bot Comunicado (Webhook Falló)**
```python
Estado: "degraded"
Razón: "Webhook de orden falló pero bot responde"
Acción: 
  - Usuario recibió mensaje de espera
  - Admin recibió alerta
  - Orden en "atención manual" en dashboard
```

##### 🚨 **Bot Incomunicado (Pérdida Total)**
```python
Estado: "incommunicado_critico"
Razón: "No se pudo enviar ningún mensaje después de webhook fallido"
Acción:
  - Panel admin muestra alerta roja prominente
  - Contador de órdenes "sin notificar" visible
  - (Futuro) Notificación por canal alternativo
```

#### 💻 Implementación en Código

##### Ubicación: `app/api/cart.py` (después del webhook fallido)

```python
# ⚠️ FALLBACK: Si ambos mensajes fallaron después de todos los reintentos
if not success1 and not success2:
    logger.critical(f"🚨 CRÍTICO: No se pudo comunicar con WAHA...")
    
    # 🔍 DIAGNÓSTICO: ¿Bot comunicado o pérdida total?
    logger.info("🔍 Iniciando diagnóstico de comunicación...")
    
    # Intento 1: Mensaje simple al usuario
    simple_message = (
        "🤝 *Hemos recibido tu orden*\n\n"
        f"*Orden:* {order.order_number}\n"
        f"*Total:* ${order.total:.2f}\n\n"
        "Un agente se comunicará contigo pronto para completar tu pedido.\n"
        "¡Gracias por tu paciencia! 😊"
    )
    
    try:
        diagnostic_success_user = False
        diagnostic_success_admin = False
        
        # Intento rápido al usuario (solo 1 reintento, 10s)
        user_result = await waha.send_text_message(
            phone=phone,
            message=simple_message
        )
        diagnostic_success_user = True
        logger.info(f"✅ Diagnóstico: Usuario alcanzable - Bot comunicado")
        
    except Exception as e:
        logger.warning(f"⚠️ Diagnóstico: Usuario no alcanzable - {e}")
        
        # Intento 2: Notificar al admin
        try:
            admin_phone = settings.ADMIN_PHONE  # Número del admin
            admin_message = (
                f"🚨 *Atención Requerida*\n\n"
                f"*Orden:* {order.order_number}\n"
                f"*Cliente:* {customer.name or 'Sin nombre'}\n"
                f"*Teléfono:* {phone}\n"
                f"*Total:* ${order.total:.2f}\n\n"
                f"El webhook falló. Por favor contacta al cliente manualmente.\n"
                f"Link: {settings.DASHBOARD_URL}/orders/{order.id}"
            )
            
            await waha.send_text_message(
                phone=admin_phone,
                message=admin_message
            )
            diagnostic_success_admin = True
            logger.info(f"✅ Diagnóstico: Admin alcanzable - Bot comunicado")
            
        except Exception as e2:
            logger.error(f"❌ Diagnóstico: Admin no alcanzable - {e2}")
        
        # Evaluar resultado del diagnóstico
        if diagnostic_success_user or diagnostic_success_admin:
            # Bot comunicado, solo webhook falló
            logger.warning("⚠️ Bot COMUNICADO pero webhook falló")
            await bot_status_service.update_status(
                status="degraded",
                reason="Webhook de orden falló pero bot responde"
            )
            
            # Marcar orden para atención manual
            await order_service.mark_for_manual_attention(
                order_id=order.id,
                reason="Webhook falló, usuario/admin notificado"
            )
            
        else:
            # 🚨 PÉRDIDA TOTAL DE COMUNICACIÓN
            logger.critical("🚨🚨🚨 BOT COMPLETAMENTE INCOMUNICADO 🚨🚨🚨")
            await bot_status_service.update_status(
                status="incommunicado_critico",
                reason="No se pudo enviar ningún mensaje después de webhook fallido",
                metadata={
                    "order_id": order.id,
                    "customer_phone": phone,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            # TODO: Notificar por canal alternativo
            # - Email urgente al admin
            # - SMS al admin
            # - Webhook a sistema de monitoreo externo (PagerDuty, etc)
            # - Escribir a archivo de log especial para scripts externos
            
            # Crear registro de comunicación perdida
            await communication_failure_service.record_critical_failure(
                order_id=order.id,
                customer_phone=phone,
                failure_type="TOTAL_COMMUNICATION_LOSS"
            )
            
    except Exception as diag_error:
        logger.critical(f"🚨 Error en diagnóstico: {diag_error}")
```

#### 🎨 Panel de Administrador - Indicador Crítico

##### Vista cuando Bot está Incomunicado:

```
┌─────────────────────────────────────────────────────────┐
│  🚨 BOT COMPLETAMENTE INCOMUNICADO 🚨                   │
│                                                          │
│  Última comunicación: Hace 3 minutos                    │
│  Órdenes afectadas: 2                                   │
│                                                          │
│  [Ver Órdenes Afectadas] [Reiniciar Bot] [Verificar WAHA]│
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  📋 Órdenes Sin Notificar (2)                           │
├─────────────────────────────────────────────────────────┤
│  ORD-123  │  Juan Pérez    │  $45.00  │  Hace 3m      │
│  📞 +58 424...  │  Orden completada en webapp           │
│  ⚠️ CRÍTICO: Bot incomunicado al momento de creación   │
│  [Llamar Cliente] [Marcar Contactado] [Ver Detalles]   │
├─────────────────────────────────────────────────────────┤
│  ORD-124  │  María Gómez   │  $32.00  │  Hace 2m      │
│  📞 +58 412...  │  Orden completada en webapp           │
│  ⚠️ CRÍTICO: Bot incomunicado al momento de creación   │
│  [Llamar Cliente] [Marcar Contactado] [Ver Detalles]   │
└─────────────────────────────────────────────────────────┘
```

#### 📊 Nuevo Modelo de BD: `communication_failures`

```sql
CREATE TABLE communication_failures (
    id TEXT PRIMARY KEY,
    failure_type TEXT NOT NULL,  -- WEBHOOK_ONLY / TOTAL_COMMUNICATION_LOSS
    order_id TEXT,
    customer_phone TEXT,
    diagnostic_user_reached BOOLEAN,  -- ¿Se alcanzó al usuario?
    diagnostic_admin_reached BOOLEAN, -- ¿Se alcanzó al admin?
    created_at DATETIME NOT NULL,
    resolved_at DATETIME,
    resolution_method TEXT,  -- manual_contact / bot_recovered / etc
    FOREIGN KEY (order_id) REFERENCES orders(id)
);
```

#### 🔧 Servicio: `CommunicationDiagnosticService`

```python
# app/services/communication_diagnostic_service.py

class CommunicationDiagnosticService:
    """Servicio para diagnosticar pérdida de comunicación"""
    
    async def diagnose_after_webhook_failure(
        self,
        order_id: str,
        customer_phone: str
    ) -> dict:
        """
        Diagnóstica si el bot está comunicado después de fallo de webhook
        
        Returns:
            {
                "bot_reachable": bool,
                "user_reached": bool,
                "admin_reached": bool,
                "status": "degraded" | "incommunicado_critico"
            }
        """
        
        user_reached = await self._try_simple_user_message(customer_phone, order_id)
        
        if user_reached:
            return {
                "bot_reachable": True,
                "user_reached": True,
                "admin_reached": None,
                "status": "degraded"
            }
        
        admin_reached = await self._try_admin_notification(customer_phone, order_id)
        
        if admin_reached:
            return {
                "bot_reachable": True,
                "user_reached": False,
                "admin_reached": True,
                "status": "degraded"
            }
        
        # 🚨 CRÍTICO: Ninguno alcanzable
        return {
            "bot_reachable": False,
            "user_reached": False,
            "admin_reached": False,
            "status": "incommunicado_critico"
        }
    
    async def _try_simple_user_message(
        self, 
        phone: str, 
        order_id: str
    ) -> bool:
        """Intenta enviar mensaje simple al usuario"""
        try:
            # Solo 1 intento rápido (10s timeout)
            await self.waha.send_text_message(
                phone=phone,
                message=self._format_simple_user_message(order_id),
                timeout=10
            )
            return True
        except:
            return False
    
    async def _try_admin_notification(
        self,
        customer_phone: str,
        order_id: str
    ) -> bool:
        """Intenta notificar al admin"""
        try:
            admin_phone = self.settings.ADMIN_PHONE
            await self.waha.send_text_message(
                phone=admin_phone,
                message=self._format_admin_alert(customer_phone, order_id),
                timeout=10
            )
            return True
        except:
            return False
```

#### 🚨 Notificaciones Alternativas (Futuro)

Cuando el bot está completamente incomunicado:

##### 1. **Email Urgente**
```python
await email_service.send_urgent_alert(
    to=settings.ADMIN_EMAIL,
    subject="🚨 CRÍTICO: Bot Incomunicado",
    body=f"Órdenes afectadas: {affected_orders}"
)
```

##### 2. **SMS al Admin**
```python
await sms_service.send_admin_alert(
    phone=settings.ADMIN_SMS,
    message=f"Bot incomunicado. {len(affected_orders)} órdenes sin procesar."
)
```

##### 3. **Webhook a Sistema Externo**
```python
# PagerDuty, Opsgenie, etc
await monitoring_service.trigger_incident(
    severity="critical",
    service="whatsapp-bot",
    details={
        "affected_orders": affected_orders,
        "timestamp": datetime.utcnow()
    }
)
```

##### 4. **Archivo de Log Especial**
```python
# Para scripts externos que monitorean archivos
with open("/var/log/bot-critical-failures.log", "a") as f:
    f.write(f"{datetime.utcnow()} | INCOMMUNICADO | {order_id}\n")
```

#### 📈 Métricas Importantes

##### Dashboard debe mostrar:
- ⏰ **Tiempo desde última comunicación exitosa**
- 📊 **Tasa de éxito de webhooks** (últimas 24h)
- 🚨 **Órdenes sin notificar** (contador prominente)
- 📉 **Historial de incidentes** de comunicación
- 🔄 **Estado actual del bot** (grande, visible, color-coded)

#### ⚙️ Auto-Recuperación

Cuando el bot se recupera:

```python
# Detectar recuperación
if bot_was_incommunicado and message_sent_successfully:
    await bot_status_service.update_status(status="online")
    
    # Procesar órdenes pendientes automáticamente
    pending_orders = await get_orders_pending_notification()
    
    for order in pending_orders:
        await retry_send_notification(order)
    
    # Notificar al admin de recuperación
    await notify_admin_recovery(
        downtime_duration=calculate_downtime(),
        orders_processed=len(pending_orders)
    )
```

#### 🎯 Prioridad de Detección Reactiva: **CRÍTICA** 🚨

Este sistema es fundamental porque:
1. ✅ **Distingue** entre fallos parciales y totales
2. ✅ **Minimiza** órdenes perdidas
3. ✅ **Alerta** inmediatamente cuando hay problema real
4. ✅ **Permite** respuesta manual rápida
5. ✅ **Evita** falsos positivos (webhook falla pero bot funciona)

---

### Detección Proactiva (Complementaria)

#### 🎯 Objetivo
Detectar problemas con WAHA **antes** de que afecten a usuarios reales mediante verificaciones periódicas de salud del sistema.

#### 🔍 Cómo Funciona

```
Cada 2-5 minutos (configurable):
    ↓
Ejecutar healthcheck ligero
    ├─ GET /api/sessions/{session}/status
    ├─ Timeout: 10 segundos
    └─ Verificar respuesta: status == "WORKING"

✅ WAHA responde correctamente
    ↓
    - healthcheck_failing = false
    - Si antes estaba en "degraded" por healthcheck → "online"

❌ WAHA no responde o timeout
    ↓
    - healthcheck_failing = true
    - Estado: "online" → "degraded" (preventivo)
    - Alerta preventiva al admin (WhatsApp/Email)
    - Log: "⚠️ Healthcheck fallando - Posibles problemas pronto"
```

#### 💡 Valor Agregado

**Ventajas:**
- ✅ Detecta problemas **antes** de que lleguen órdenes
- ✅ Admin alertado **preventivamente** (1-5 min antes)
- ✅ Tiempo de respuesta más rápido
- ✅ Puede prevenir órdenes perdidas
- ✅ Visibilidad continua del estado del sistema

**Desventajas:**
- ⚠️ Genera tráfico adicional (bajo: 1 request cada 2-5 min)
- ⚠️ Posibles falsos positivos (healthcheck falla pero envío funciona)
- ⚠️ Complejidad adicional en el sistema

#### 🔄 Integración con Detección Reactiva

El sistema **combina ambos enfoques**:

```python
# Estado del bot considera AMBAS fuentes:

if healthcheck_failing and webhook_failing:
    # 🚨 Ambos fallan → Altamente probable que WAHA esté caído
    estado = "incommunicado_critico"
    confianza = "alta"

elif healthcheck_failing and not webhook_failing:
    # ⚠️ Solo healthcheck falla → Posible problema intermitente
    estado = "degraded"
    confianza = "media"
    nota = "Healthcheck fallando pero webhooks funcionan"

elif not healthcheck_failing and webhook_failing:
    # ⚠️ Solo webhook falla → Problema específico de webhook
    estado = "degraded"
    confianza = "media"
    nota = "Webhook fallando pero WAHA responde a healthcheck"

else:
    # ✅ Ambos funcionan → Todo normal
    estado = "online"
```

#### 💻 Implementación Sugerida

##### 1. Servicio de Healthcheck

```python
# app/services/waha_healthcheck_service.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger
from datetime import datetime

class WAHAHealthcheckService:
    """Servicio para verificar salud de WAHA proactivamente"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.check_interval_minutes = 2  # Configurable
        self.consecutive_failures = 0
        self.failure_threshold = 2  # Alertar después de 2 fallos consecutivos

    async def start(self):
        """Inicia el healthcheck periódico"""
        self.scheduler.add_job(
            self.check_waha_health,
            'interval',
            minutes=self.check_interval_minutes,
            id='waha_healthcheck'
        )
        self.scheduler.start()
        logger.info(f"✅ Healthcheck iniciado (cada {self.check_interval_minutes} min)")

    async def check_waha_health(self):
        """Verifica si WAHA está respondiendo"""
        try:
            waha = WAHAClient()

            # Intento de healthcheck con timeout corto
            status = await asyncio.wait_for(
                waha.get_session_status(),
                timeout=10.0
            )

            if status.get("status") == "WORKING":
                await self._handle_healthcheck_success()
            else:
                await self._handle_healthcheck_failure(
                    f"WAHA status: {status.get('status')}"
                )

        except asyncio.TimeoutError:
            await self._handle_healthcheck_failure("Timeout después de 10s")
        except Exception as e:
            await self._handle_healthcheck_failure(str(e))

    async def _handle_healthcheck_success(self):
        """Maneja healthcheck exitoso"""
        was_failing = self.consecutive_failures > 0
        self.consecutive_failures = 0

        if was_failing:
            logger.info("✅ Healthcheck recuperado - WAHA respondiendo")

            # Verificar si debemos cambiar estado del bot
            bot_status = await bot_status_service.get_current_status()

            if bot_status.get("healthcheck_failing"):
                await bot_status_service.mark_healthcheck_recovered()

                # Si el estado solo estaba en "degraded" por healthcheck,
                # y no hay problemas de webhook, volver a "online"
                if not bot_status.get("webhook_failing"):
                    await bot_status_service.update_status("online")
                    await self._notify_admin_recovery()

    async def _handle_healthcheck_failure(self, reason: str):
        """Maneja healthcheck fallido"""
        self.consecutive_failures += 1

        logger.warning(
            f"⚠️ Healthcheck falló ({self.consecutive_failures}/"
            f"{self.failure_threshold}): {reason}"
        )

        # Solo alertar después del threshold
        if self.consecutive_failures >= self.failure_threshold:
            was_healthy = not await bot_status_service.is_healthcheck_failing()

            if was_healthy:
                logger.warning("🚨 Healthcheck fallando consistentemente")
                await bot_status_service.mark_healthcheck_failing()

                # Cambiar a degraded preventivamente
                current_status = await bot_status_service.get_current_status()
                if current_status.get("status") == "online":
                    await bot_status_service.update_status(
                        "degraded",
                        reason="Healthcheck fallando - Posibles problemas"
                    )

                # Alerta preventiva al admin
                await self._notify_admin_preventive_alert(reason)

    async def _notify_admin_preventive_alert(self, reason: str):
        """Notifica al admin preventivamente"""
        try:
            admin_phone = settings.ADMIN_PHONE
            waha = WAHAClient()

            message = (
                f"⚠️ *Alerta Preventiva*\n\n"
                f"WAHA no respondió al healthcheck.\n"
                f"Razón: {reason}\n\n"
                f"El sistema aún funciona pero puede haber "
                f"problemas pronto.\n\n"
                f"Recomendación: Revisar WAHA antes de que "
                f"afecte a usuarios.\n\n"
                f"Timestamp: {datetime.now().strftime('%H:%M:%S')}"
            )

            # Intentar notificar (puede fallar si WAHA está caído)
            await waha.send_text_message(admin_phone, message)

        except Exception as e:
            logger.error(f"No se pudo enviar alerta preventiva: {e}")
            # Esto es esperado si WAHA está completamente caído

    async def _notify_admin_recovery(self):
        """Notifica recuperación del healthcheck"""
        try:
            admin_phone = settings.ADMIN_PHONE
            waha = WAHAClient()

            message = (
                f"✅ *Sistema Recuperado*\n\n"
                f"WAHA está respondiendo normalmente.\n"
                f"Healthcheck exitoso.\n\n"
                f"Timestamp: {datetime.now().strftime('%H:%M:%S')}"
            )

            await waha.send_text_message(admin_phone, message)

        except Exception as e:
            logger.warning(f"No se pudo notificar recuperación: {e}")

# Instancia global
waha_healthcheck_service = WAHAHealthcheckService()
```

##### 2. Integración en BotStatusService

```python
# app/services/bot_status_service.py

class BotStatusService:
    # ... código existente ...

    async def mark_healthcheck_failing(self):
        """Marca que el healthcheck está fallando"""
        bot_status = self.db.query(BotStatus).first()
        if bot_status:
            bot_status.healthcheck_failing = True
            bot_status.healthcheck_last_failure = datetime.utcnow()
            self.db.commit()

    async def mark_healthcheck_recovered(self):
        """Marca que el healthcheck se recuperó"""
        bot_status = self.db.query(BotStatus).first()
        if bot_status:
            bot_status.healthcheck_failing = False
            bot_status.healthcheck_last_success = datetime.utcnow()
            self.db.commit()

    async def is_healthcheck_failing(self) -> bool:
        """Verifica si el healthcheck está fallando"""
        bot_status = self.db.query(BotStatus).first()
        return bot_status.healthcheck_failing if bot_status else False

    async def get_combined_status(self) -> dict:
        """Obtiene estado combinado (healthcheck + webhooks)"""
        bot_status = self.db.query(BotStatus).first()

        if not bot_status:
            return {"status": "unknown"}

        healthcheck_failing = bot_status.healthcheck_failing
        webhook_failing = bot_status.waha_consecutive_failures > 0

        # Lógica combinada
        if healthcheck_failing and webhook_failing:
            status = "incommunicado_critico"
            confidence = "high"
        elif healthcheck_failing:
            status = "degraded"
            confidence = "medium"
            note = "Healthcheck failing but webhooks may work"
        elif webhook_failing:
            status = "degraded"
            confidence = "medium"
            note = "Webhook failing but WAHA responds to healthcheck"
        else:
            status = "online"
            confidence = "high"

        return {
            "status": status,
            "healthcheck_failing": healthcheck_failing,
            "webhook_failing": webhook_failing,
            "confidence": confidence,
            "last_healthcheck": bot_status.healthcheck_last_success,
            "last_webhook_success": bot_status.waha_last_success
        }
```

##### 3. Actualizar Modelo de BD

```sql
-- Agregar campos a bot_status
ALTER TABLE bot_status ADD COLUMN healthcheck_failing BOOLEAN DEFAULT FALSE;
ALTER TABLE bot_status ADD COLUMN healthcheck_last_success DATETIME;
ALTER TABLE bot_status ADD COLUMN healthcheck_last_failure DATETIME;
ALTER TABLE bot_status ADD COLUMN healthcheck_consecutive_failures INTEGER DEFAULT 0;
```

##### 4. Iniciar Healthcheck al Arrancar la App

```python
# app/main.py

@app.on_event("startup")
async def startup_event():
    """Ejecuta al iniciar la aplicación"""
    logger.info("🚀 Iniciando aplicación...")

    # Iniciar healthcheck proactivo
    await waha_healthcheck_service.start()

    logger.info("✅ Aplicación iniciada")
```

#### 📊 Dashboard - Vista con Healthcheck

```
┌─────────────────────────────────────────────────────────┐
│  🤖 Estado del Bot                                      │
├─────────────────────────────────────────────────────────┤
│  Estado: ⚠️ DEGRADED                                   │
│                                                          │
│  📊 Indicadores:                                        │
│    Healthcheck: ❌ Fallando (hace 2 min)              │
│    Webhooks:    ✅ Funcionando                         │
│                                                          │
│  💡 Interpretación:                                     │
│  WAHA no responde a healthcheck pero los webhooks      │
│  aún funcionan. Puede ser problema temporal.           │
│                                                          │
│  [Forzar Healthcheck] [Reiniciar WAHA] [Ver Logs]     │
└─────────────────────────────────────────────────────────┘
```

#### ⚖️ Comparación: Reactivo vs Proactivo

| Aspecto | Solo Reactivo | Con Proactivo |
|---------|---------------|---------------|
| **Tiempo de detección** | 3+ minutos (después de fallo real) | 10 segundos - 5 min |
| **Órdenes afectadas antes de alertar** | 1+ | 0 (alerta antes) |
| **Admin preparado** | ❌ Después del problema | ✅ Antes del problema |
| **Falsos positivos** | Muy bajos | Posibles (healthcheck intermitente) |
| **Costo operacional** | Solo cuando falla | Constante (bajo) |
| **Complejidad** | Media | Alta |

#### 🎯 Recomendación de Implementación

**Fase 1 (Esencial)**: Detección Reactiva
- ✅ Implementar diagnóstico después de webhook fallido
- ✅ Distinción entre fallo parcial y total
- ✅ Auto-recuperación

**Fase 2 (Mejora)**: Detección Proactiva
- ⏳ Agregar healthcheck cada 2-5 minutos
- ⏳ Alertas preventivas
- ⏳ Dashboard con indicadores combinados

**Configuración recomendada** (si se implementa proactivo):
```python
HEALTHCHECK_ENABLED = True
HEALTHCHECK_INTERVAL_MINUTES = 3  # Balance entre detección rápida y tráfico
HEALTHCHECK_FAILURE_THRESHOLD = 2  # Alertar después de 2 fallos consecutivos
HEALTHCHECK_TIMEOUT_SECONDS = 10
```

---

## 🔔 Sistema de Notificaciones al Admin

### Ubicación de TODOs:
- `app/api/cart.py` (líneas 406-432)
- `app/services/order_notification_service.py` (líneas 117-140, 231-243)

### Objetivo:
Notificar al administrador cuando el bot no puede comunicarse con WAHA después de 4 reintentos.

### Casos de Uso:

#### 1. **Webhook de Carrito Falla**
```
Situación: Usuario completa orden en webapp, pero bot no puede enviar mensajes iniciales
Impacto: Usuario no sabe que debe dar GPS/pago
Necesidad: Admin debe contactar manualmente al usuario
```

#### 2. **Notificación de Confirmación Falla**
```
Situación: Admin confirma pago, pero bot no puede notificar al usuario
Impacto: Usuario no sabe que su pago fue confirmado
Necesidad: Admin debe notificar por otro medio (llamada, SMS)
```

#### 3. **Notificación de Envío Falla**
```
Situación: Orden enviada, pero bot no puede notificar
Impacto: Usuario no espera la entrega
Necesidad: Admin debe avisar por otro medio
```

---

## 📊 Panel de Administrador - Notificaciones Pendientes

### Sección Nueva: "Notificaciones Fallidas"

#### Vista Sugerida:
```
┌─────────────────────────────────────────────────────────┐
│  🚨 Notificaciones Pendientes (3)                       │
├─────────────────────────────────────────────────────────┤
│  ORD-001  │  Juan Pérez  │  ORDEN_RECIBIDA  │  10:30   │
│  ✉️ +58 424...            │  4 intentos      │  Hace 5m │
│  [Re-intentar] [Marcar como Notificado] [Ver Orden]    │
├─────────────────────────────────────────────────────────┤
│  ORD-002  │  María Gómez │  PAGO_CONFIRMADO │  10:35   │
│  ✉️ +58 412...            │  4 intentos      │  Hace 2m │
│  [Re-intentar] [Marcar como Notificado] [Ver Orden]    │
└─────────────────────────────────────────────────────────┘
```

#### Características:
- ✅ **Lista de notificaciones fallidas** por tipo
- ✅ **Re-intentar manualmente** (botón)
- ✅ **Marcar como notificado** (si se contactó por otro medio)
- ✅ **Ver detalles de orden** (link directo)
- ✅ **Indicador de tiempo** (cuánto hace que falló)
- ✅ **Información de contacto** del cliente

---

## 🤖 Estado del Bot

### Ubicación de TODOs:
- `app/api/cart.py` (líneas 417-429)
- `app/services/order_notification_service.py` (líneas 130-140)

### Objetivo:
Rastrear y mostrar el estado de comunicación del bot en tiempo real.

### Estados Propuestos:

#### 1. **Online** ✅
```
- Bot funcionando correctamente
- WAHA responde
- Notificaciones enviadas exitosamente
```

#### 2. **Degraded** ⚠️
```
- Algunos reintentos fallan pero eventualmente funcionan
- Latencia alta en respuestas de WAHA
- Tasa de éxito < 90%
```

#### 3. **Incomunicado** 🚨
```
- Múltiples fallos consecutivos (>3 en 5 minutos)
- WAHA no responde después de reintentos
- Notificaciones críticas fallando
```

#### 4. **Offline** ❌
```
- Bot detenido completamente
- No hay actividad por >10 minutos
```

---

## 🗄️ Modelo de Base de Datos Sugerido

### Tabla: `bot_status`
```sql
CREATE TABLE bot_status (
    id INTEGER PRIMARY KEY,
    status TEXT NOT NULL,  -- online/degraded/incommunicado/offline
    last_update DATETIME NOT NULL,
    reason TEXT,  -- Descripción del problema
    waha_last_success DATETIME,  -- Última vez que WAHA respondió
    waha_consecutive_failures INTEGER DEFAULT 0,
    metadata JSON  -- Información adicional
);
```

### Tabla: `failed_notifications`
```sql
CREATE TABLE failed_notifications (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    customer_phone TEXT NOT NULL,
    notification_type TEXT NOT NULL,  -- ORDER_RECEIVED/CONFIRMED/SHIPPED
    attempts INTEGER DEFAULT 0,
    last_attempt DATETIME,
    manually_resolved BOOLEAN DEFAULT FALSE,
    resolved_by TEXT,  -- Admin que lo resolvió
    resolution_method TEXT,  -- retry/phone_call/sms/email
    created_at DATETIME NOT NULL,
    resolved_at DATETIME,
    FOREIGN KEY (order_id) REFERENCES orders(id)
);
```

---

## 💻 Implementación Sugerida

### 1. **Servicio de Estado del Bot**

```python
# app/services/bot_status_service.py

from datetime import datetime, timedelta
from typing import List
from sqlalchemy.orm import Session

class BotStatusService:
    """Servicio para rastrear el estado del bot"""
    
    def __init__(self, db: Session):
        self.db = db
        self.failure_threshold = 3  # Fallos antes de marcar incomunicado
        self.failure_window_minutes = 5
    
    async def record_notification_failure(
        self, 
        order_id: str,
        customer_phone: str,
        notification_type: str,
        attempts: int
    ):
        """Registra un fallo de notificación"""
        failed_notification = FailedNotification(
            order_id=order_id,
            customer_phone=customer_phone,
            notification_type=notification_type,
            attempts=attempts,
            last_attempt=datetime.utcnow()
        )
        self.db.add(failed_notification)
        self.db.commit()
        
        # Verificar si debemos cambiar estado del bot
        recent_failures = await self.get_recent_failures_count(
            minutes=self.failure_window_minutes
        )
        
        if recent_failures >= self.failure_threshold:
            await self.update_status(
                status="incommunicado",
                reason=f"{recent_failures} notificaciones fallidas en {self.failure_window_minutes} minutos"
            )
    
    async def get_recent_failures_count(self, minutes: int) -> int:
        """Obtiene el conteo de fallos recientes"""
        threshold = datetime.utcnow() - timedelta(minutes=minutes)
        
        count = self.db.query(FailedNotification).filter(
            FailedNotification.created_at >= threshold,
            FailedNotification.manually_resolved == False
        ).count()
        
        return count
    
    async def update_status(
        self, 
        status: str, 
        reason: str = None
    ):
        """Actualiza el estado del bot"""
        bot_status = self.db.query(BotStatus).first()
        
        if not bot_status:
            bot_status = BotStatus(status=status)
            self.db.add(bot_status)
        
        bot_status.status = status
        bot_status.last_update = datetime.utcnow()
        bot_status.reason = reason
        
        if status == "incommunicado":
            bot_status.waha_consecutive_failures += 1
        elif status == "online":
            bot_status.waha_consecutive_failures = 0
            bot_status.waha_last_success = datetime.utcnow()
        
        self.db.commit()
        
        logger.warning(f"🤖 Estado del bot actualizado: {status} - {reason}")
    
    async def get_current_status(self) -> dict:
        """Obtiene el estado actual del bot"""
        bot_status = self.db.query(BotStatus).first()
        
        if not bot_status:
            return {
                "status": "unknown",
                "last_update": None,
                "reason": "No status recorded"
            }
        
        return {
            "status": bot_status.status,
            "last_update": bot_status.last_update,
            "reason": bot_status.reason,
            "waha_last_success": bot_status.waha_last_success,
            "consecutive_failures": bot_status.waha_consecutive_failures
        }
```

---

### 2. **Servicio de Notificaciones al Admin**

```python
# app/services/admin_notification_service.py

class AdminNotificationService:
    """Servicio para notificar al administrador"""
    
    async def notify_communication_failure(
        self,
        order_id: str,
        customer_phone: str,
        error_type: str
    ):
        """
        Notifica al admin sobre fallo de comunicación
        
        Métodos de notificación:
        1. Email urgente al admin
        2. Push notification en dashboard
        3. SMS si es crítico
        4. Webhook a sistema externo (opcional)
        """
        
        # 1. Email
        await self._send_admin_email(
            subject=f"🚨 Fallo Crítico: {error_type}",
            body=f"No se pudo notificar orden {order_id} al cliente {customer_phone}"
        )
        
        # 2. Push notification (WebSocket al dashboard)
        await self._send_dashboard_notification({
            "type": "COMMUNICATION_FAILURE",
            "order_id": order_id,
            "customer_phone": customer_phone,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # 3. SMS si configurado
        if self.settings.admin_sms_enabled:
            await self._send_admin_sms(
                f"Bot incomunicado. Orden {order_id} requiere atención."
            )
    
    async def notify_failed_customer_notification(
        self,
        order_id: str,
        customer_phone: str,
        notification_type: str,
        attempts: int
    ):
        """Notifica sobre notificación fallida al cliente"""
        
        # Registrar en failed_notifications
        await bot_status_service.record_notification_failure(
            order_id, customer_phone, notification_type, attempts
        )
        
        # Alerta en dashboard
        await self._send_dashboard_notification({
            "type": "FAILED_CUSTOMER_NOTIFICATION",
            "order_id": order_id,
            "customer_phone": customer_phone,
            "notification_type": notification_type,
            "attempts": attempts
        })
```

---

### 3. **API Endpoints para Dashboard**

```python
# app/api/bot_status.py

@router.get("/bot/status")
async def get_bot_status(db: Session = Depends(get_db)):
    """Obtiene el estado actual del bot"""
    service = BotStatusService(db)
    status = await service.get_current_status()
    return status

@router.get("/notifications/failed")
async def get_failed_notifications(
    resolved: bool = False,
    db: Session = Depends(get_db)
):
    """Lista notificaciones fallidas"""
    query = db.query(FailedNotification).filter(
        FailedNotification.manually_resolved == resolved
    ).order_by(FailedNotification.created_at.desc())
    
    return [
        {
            "id": n.id,
            "order_id": n.order_id,
            "customer_phone": n.customer_phone,
            "type": n.notification_type,
            "attempts": n.attempts,
            "created_at": n.created_at
        }
        for n in query.all()
    ]

@router.post("/notifications/failed/{notification_id}/retry")
async def retry_failed_notification(
    notification_id: str,
    db: Session = Depends(get_db)
):
    """Re-intenta enviar una notificación fallida"""
    notification = db.query(FailedNotification).filter(
        FailedNotification.id == notification_id
    ).first()
    
    if not notification:
        raise HTTPException(404, "Notificación no encontrada")
    
    # Re-intentar envío
    notification_service = OrderNotificationService(db)
    
    if notification.notification_type == "ORDER_CONFIRMED":
        success = await notification_service._send_confirmation_notification(...)
    # ... otros tipos
    
    if success:
        notification.manually_resolved = True
        notification.resolution_method = "retry"
        notification.resolved_at = datetime.utcnow()
        db.commit()
    
    return {"success": success}

@router.post("/notifications/failed/{notification_id}/mark_resolved")
async def mark_notification_resolved(
    notification_id: str,
    resolution_method: str,  # phone_call, sms, email
    db: Session = Depends(get_db)
):
    """Marca una notificación como resuelta manualmente"""
    notification = db.query(FailedNotification).get(notification_id)
    
    notification.manually_resolved = True
    notification.resolution_method = resolution_method
    notification.resolved_at = datetime.utcnow()
    # notification.resolved_by = current_admin_user
    
    db.commit()
    
    return {"message": "Notificación marcada como resuelta"}
```

---

### 4. **Dashboard Frontend (Vue)**

```vue
<!-- AdminDashboard.vue -->
<template>
  <div class="admin-dashboard">
    <!-- Estado del Bot -->
    <el-card class="bot-status-card">
      <div class="status-header">
        <h3>🤖 Estado del Bot</h3>
        <el-tag :type="statusType">{{ botStatus.status }}</el-tag>
      </div>
      
      <div v-if="botStatus.status === 'incommunicado'" class="alert">
        <el-alert type="error" :closable="false">
          ⚠️ Bot incomunicado. {{ botStatus.reason }}
        </el-alert>
      </div>
    </el-card>
    
    <!-- Notificaciones Fallidas -->
    <el-card class="failed-notifications">
      <h3>🚨 Notificaciones Pendientes ({{ failedNotifications.length }})</h3>
      
      <el-table :data="failedNotifications">
        <el-table-column prop="order_id" label="Orden" />
        <el-table-column prop="customer_phone" label="Cliente" />
        <el-table-column prop="type" label="Tipo" />
        <el-table-column prop="attempts" label="Intentos" />
        <el-table-column label="Acciones">
          <template #default="{ row }">
            <el-button @click="retry(row.id)">Re-intentar</el-button>
            <el-button @click="markResolved(row.id)">Marcar Notificado</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>
```

---

## 📅 Priorización

### 🚨 Prioridad CRÍTICA (Implementar PRIMERO):

#### Sistema de Diagnóstico de Comunicación:
1. ⏳ **CommunicationDiagnosticService**
   - Implementar mensajes de diagnóstico (usuario + admin)
   - Lógica de detección: webhook vs pérdida total
   - Integrar en `app/api/cart.py` después del fallback actual
   
2. ⏳ **Tabla `communication_failures`**
   - Registrar tipo de fallo (WEBHOOK_ONLY / TOTAL_COMMUNICATION_LOSS)
   - Diagnóstico (user_reached, admin_reached)
   - Timestamps y resolución
   
3. ⏳ **Estado del Bot - Nivel Crítico**
   - Actualizar `bot_status` con estado "incommunicado_critico"
   - Distinguir entre "degraded" (webhook falló) vs "incommunicado_critico" (pérdida total)
   
4. ⏳ **Dashboard - Alerta de Incomunicación**
   - Banner rojo prominente cuando bot incomunicado
   - Contador de "Órdenes Sin Notificar"
   - Lista de órdenes afectadas con botones de acción

**Impacto**: Sistema puede distinguir entre fallo parcial (recuperable) y fallo total (crítico).  
**Estimación**: 1-2 días de desarrollo

---

### Alta Prioridad (Crítico):
5. ✅ **Sistema de logging crítico** (COMPLETADO)
6. ⏳ **Tabla failed_notifications**
7. ⏳ **API endpoint para listar notificaciones fallidas**
8. ⏳ **Vista básica en dashboard - notificaciones pendientes**

### Media Prioridad:
9. ⏳ **Tabla bot_status** (mejorada con nuevos estados)
10. ⏳ **BotStatusService** (completo con métricas)
11. ⏳ **Indicador de estado en dashboard** (color-coded)
12. ⏳ **Re-intentar notificaciones manualmente**
13. ⏳ **Auto-recuperación del bot** (procesar órdenes pendientes)

### Baja Prioridad:
14. ⏳ **Notificaciones por email al admin**
15. ⏳ **SMS al admin**
16. ⏳ **WebSocket para notificaciones en tiempo real**
17. ⏳ **Integración con sistemas de monitoreo externos** (PagerDuty, etc)
18. ⏳ **Métricas avanzadas** (tasa de éxito, historial de incidentes)

---

## 🎯 Beneficios Esperados

### Con el Sistema de Diagnóstico de Comunicación:
- ✅ **Detección Inteligente**: Distingue entre fallo parcial (webhook) vs pérdida total (WAHA)
- ✅ **Respuesta Inmediata**: Usuario/admin reciben notificación si bot está comunicado
- ✅ **Alertas Precisas**: Solo marca "incomunicado_crítico" cuando realmente hay pérdida total
- ✅ **Cero Falsos Positivos**: Webhook falla pero bot funciona → Estado "degraded", no crítico
- ✅ **Visibilidad Granular**: Admin sabe exactamente qué tipo de problema hay

### Con el Sistema Completo Implementado:
- ✅ **Cero órdenes perdidas**: Admin siempre sabe si hay problemas
- ✅ **Respuesta rápida**: Notificación inmediata de fallos
- ✅ **Visibilidad completa**: Estado del bot en tiempo real (online/degraded/incommunicado_critico)
- ✅ **Recuperación manual**: Admin puede re-intentar o notificar por otro medio
- ✅ **Auditoría**: Registro de todos los fallos y resoluciones
- ✅ **Auto-recuperación**: Bot procesa órdenes pendientes cuando se recupera

### Escenarios de Uso:

#### 📊 Escenario 1: Webhook Falla pero Bot Funciona
```
Resultado: Estado "degraded"
Usuario: Recibe "Orden recibida, agente te contactará"
Admin: Recibe alerta "Orden XXX requiere atención manual"
Dashboard: Muestra orden en "Atención Manual" (no crítico)
```

#### 🚨 Escenario 2: Pérdida Total de Comunicación
```
Resultado: Estado "incommunicado_critico"
Usuario: No recibe mensaje (WAHA caído)
Admin: No recibe alerta por WhatsApp
Dashboard: Banner rojo prominente "Bot Incomunicado"
Orden: Marcada como "Sin Notificar" (requiere llamada urgente)
(Futuro): Email/SMS urgente al admin
```

---

## 📚 Ejemplos y Escenarios de Testing

Para entender mejor cómo funciona el sistema de detección de pérdida de comunicación en escenarios reales, consulta el documento complementario:

**📖 [COMMUNICATION_DETECTION_EXAMPLES.md](./COMMUNICATION_DETECTION_EXAMPLES.md)**

Este documento contiene:
- ✅ **6 escenarios detallados** con timelines paso a paso
- ✅ **Ejemplos de logs** y mensajes del sistema
- ✅ **Estados de base de datos** en cada momento
- ✅ **Vistas del dashboard** para cada situación
- ✅ **Comparaciones** entre detección reactiva y proactiva
- ✅ **Matriz de comparación** de todos los escenarios

**Escenarios incluidos:**
1. 🚨 WAHA completamente caído (pérdida total)
2. ⚠️ Solo webhook falla, WAHA funciona (fallo parcial)
3. 🔄 WAHA reiniciándose (auto-recuperación)
4. 📞 Problema con número del usuario (diagnóstico específico)
5. ⚡ Red intermitente (resiliencia del sistema)
6. 🔍 Detección proactiva previene fallo (healthcheck)

**Uso recomendado:**
- Para **testing**: Usar como casos de prueba durante implementación
- Para **referencia**: Entender comportamiento esperado en producción
- Para **debugging**: Comparar comportamiento real vs esperado
- Para **documentación**: Mostrar a stakeholders cómo funciona el sistema

---

**Última actualización**: Noviembre 2025
**Estado**: TODOs documentados, pendiente de implementación

