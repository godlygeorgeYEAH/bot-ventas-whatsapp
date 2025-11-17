# 🧪 Guía de Testing - Sistema de Detección de Comunicación

Esta guía explica cómo probar el sistema de detección de pérdida de comunicación que acabamos de implementar.

**Última actualización**: Noviembre 2025
**Relacionado con**: [COMMUNICATION_DETECTION_EXAMPLES.md](./COMMUNICATION_DETECTION_EXAMPLES.md)

---

## 📋 Pre-requisitos

Antes de comenzar con los tests, asegúrate de:

1. ✅ Ejecutar la migración de base de datos
2. ✅ Tener WAHA ejecutándose (para tests de detección)
3. ✅ Tener logs visibles en tiempo real
4. ✅ Configurar `ADMIN_PHONE` en settings

---

## 🔧 Paso 1: Ejecutar Migración

```bash
# Ejecutar el script de migración
python scripts/migrate_add_bot_monitoring.py
```

**Salida esperada:**
```
============================================================
MIGRACIÓN DE BASE DE DATOS
Sistema de Monitoreo de Comunicación del Bot
============================================================
🔄 Iniciando migración: Agregar sistema de monitoreo del bot
📊 Creando tabla 'bot_status'...
✅ Tabla 'bot_status' creada
🔧 Inicializando estado del bot...
✅ Estado inicial del bot configurado como 'online'
📊 Creando tabla 'communication_failures'...
✅ Tabla 'communication_failures' creada con índices
✅ Migración completada exitosamente
```

**Verificar que las tablas fueron creadas:**
```bash
# Conectar a la BD
sqlite3 data/bot.db

# Listar tablas
.tables

# Deberías ver:
# bot_status  communication_failures  orders  ...

# Ver estructura
.schema bot_status
.schema communication_failures
```

---

## 🧪 Paso 2: Test 1 - WAHA Completamente Caído

Este test simula el escenario donde WAHA está completamente apagado.

### 2.1 Preparación

```bash
# Terminal 1: Logs en tiempo real
tail -f logs/app.log | grep -E "CRÍTICO|Diagnóstico|🔍|🚨"

# Terminal 2: Detener WAHA
docker stop waha

# Verificar que WAHA está detenido
docker ps | grep waha
# No debería aparecer nada
```

### 2.2 Ejecutar Test

```bash
# Terminal 3: Crear orden en webapp
# Opción A: Usar el navegador
open http://localhost:5173/cart?token=<tu-token>

# Opción B: Usar curl
curl -X POST http://localhost:8000/api/cart/complete \
  -H "Content-Type: application/json" \
  -d '{
    "token": "test-token",
    "items": [
      {"product_id": "prod-1", "quantity": 2}
    ]
  }'
```

### 2.3 Observar Comportamiento Esperado

**En los logs (Terminal 1) deberías ver:**

```
[Timestamp] 🚨 CRÍTICO: No se pudo comunicar con WAHA después de 4 intentos para orden ORD-XXX
[Timestamp] 🔍 Iniciando diagnóstico de comunicación...
[Timestamp]    Orden: ORD-XXX, Cliente: +58424XXXXXXX
[Timestamp] 🔍 Intentando mensaje de diagnóstico al usuario +58424XXXXXXX
[Timestamp] ⚠️ Diagnóstico: Usuario no alcanzable
[Timestamp] 🔍 Intentando notificación de diagnóstico al admin
[Timestamp] ⚠️ Diagnóstico: Admin no alcanzable
[Timestamp] 🚨🚨🚨 BOT COMPLETAMENTE INCOMUNICADO 🚨🚨🚨
[Timestamp]    Orden: <order-id>
[Timestamp]    Cliente: +58424XXXXXXX
[Timestamp] 🤖 Estado del bot cambiando: online → incommunicado_critico
[Timestamp]    Razón: No se pudo enviar ningún mensaje después de webhook fallido
[Timestamp] 📊 Resultado del diagnóstico:
[Timestamp]    Bot alcanzable: False
[Timestamp]    Usuario alcanzado: False
[Timestamp]    Admin alcanzado: False
[Timestamp]    Tipo de fallo: TOTAL_COMMUNICATION_LOSS
[Timestamp]    Estado del bot: incommunicado_critico
```

### 2.4 Verificar en Base de Datos

```bash
sqlite3 data/bot.db

# Verificar estado del bot
SELECT status, reason, waha_consecutive_failures
FROM bot_status;

# Resultado esperado:
# incommunicado_critico | No se pudo enviar ningún mensaje... | 1

# Verificar registro de fallo
SELECT failure_type, diagnostic_user_reached, diagnostic_admin_reached, resolved_at
FROM communication_failures
ORDER BY created_at DESC
LIMIT 1;

# Resultado esperado:
# TOTAL_COMMUNICATION_LOSS | 0 | 0 | NULL
```

### 2.5 Test de Recuperación

```bash
# Terminal 2: Reiniciar WAHA
docker start waha

# Esperar ~30 segundos a que WAHA arranque completamente
sleep 30

# Terminal 3: Crear nueva orden
# (Usar webapp o curl como antes)
```

**En los logs deberías ver:**
```
[Timestamp] ✅ Bot recuperado: incommunicado_critico → online
[Timestamp] 🤖 Estado del bot cambiando: incommunicado_critico → online
[Timestamp]    Razón: Comunicación con WAHA restablecida
```

---

## 🧪 Paso 3: Test 2 - Solo Webhook Falla

Este test simula que el webhook específico falla pero WAHA funciona.

### 3.1 Inyectar Fallo Temporal

Editar temporalmente `app/api/cart.py`:

```python
# Buscar la línea donde se ejecuta execute_with_retry (aprox línea 539)
# ANTES de la línea:
success1, _ = await webhook_retry_service.execute_with_retry(...)

# AGREGAR (solo para testing):
if order.order_number:  # Siempre True
    import random
    if random.random() < 1.0:  # 100% de probabilidad
        success1 = False
        success2 = False
        logger.warning("🧪 TEST: Forzando fallo de webhook")
    else:
        success1, _ = await webhook_retry_service.execute_with_retry(...)
        # ... resto del código
```

**IMPORTANTE**: Esto es SOLO para testing. Revierte este cambio después.

### 3.2 Ejecutar Test

```bash
# Asegurar que WAHA está corriendo
docker ps | grep waha

# Crear orden en webapp
```

### 3.3 Observar Comportamiento Esperado

**En los logs deberías ver:**

```
[Timestamp] 🧪 TEST: Forzando fallo de webhook
[Timestamp] 🚨 CRÍTICO: No se pudo comunicar con WAHA después de 4 intentos...
[Timestamp] 🔍 Iniciando diagnóstico de comunicación...
[Timestamp] 🔍 Intentando mensaje de diagnóstico al usuario...
[Timestamp] ✅ Usuario +58424XXXXXXX alcanzado en diagnóstico
[Timestamp] ✅ Diagnóstico: Usuario alcanzable - Bot comunicado
[Timestamp] ⚠️ Bot COMUNICADO pero webhook falló
[Timestamp] 🤖 Estado del bot cambiando: online → degraded
[Timestamp]    Razón: Webhook de orden falló pero bot responde
[Timestamp] 📊 Resultado del diagnóstico:
[Timestamp]    Bot alcanzable: True
[Timestamp]    Usuario alcanzado: True
[Timestamp]    Admin alcanzado: None
[Timestamp]    Tipo de fallo: WEBHOOK_ONLY
[Timestamp]    Estado del bot: degraded
```

**El usuario debería recibir (en WhatsApp):**
```
🤝 Hemos recibido tu orden

Orden: ORD-XXX

Un agente se comunicará contigo pronto para
completar tu pedido.

¡Gracias por tu paciencia! 😊
```

### 3.4 Verificar en Base de Datos

```bash
sqlite3 data/bot.db

# Verificar estado del bot
SELECT status, reason FROM bot_status;
# Resultado: degraded | Webhook de orden falló pero bot responde

# Verificar tipo de fallo
SELECT failure_type, diagnostic_user_reached, diagnostic_admin_reached
FROM communication_failures
ORDER BY created_at DESC
LIMIT 1;
# Resultado: WEBHOOK_ONLY | 1 | 0
```

### 3.5 Revertir Cambios

**IMPORTANTE**: Eliminar el código de prueba de `cart.py`:

```bash
# Buscar y eliminar las líneas que agregaste:
# if order.order_number:
#     import random
#     if random.random() < 1.0:
#         ...
```

---

## 🧪 Paso 4: Test 3 - Número de Usuario Inválido

### 4.1 Preparación

Este test requiere usar un número de teléfono que no existe en WhatsApp.

### 4.2 Ejecutar Test

```bash
# Opción A: Modificar temporalmente el número en la orden
# Editar app/api/cart.py línea donde se obtiene phone:
# phone = "+58 000-0000000"  # Número obviamente falso

# Opción B: Crear sesión de carrito con número inválido
curl -X POST http://localhost:8000/api/cart/create \
  -H "Content-Type: application/json" \
  -d '{
    "customer_phone": "+58 000-0000000",
    "hours_valid": 24
  }'

# Luego completar orden con ese token
```

### 4.3 Observar Comportamiento Esperado

**En los logs:**
```
[Timestamp] 🔍 Intentando mensaje de diagnóstico al usuario +58 000-0000000
[Timestamp] ⚠️ Diagnóstico: Usuario no alcanzable - The number is not registered on WhatsApp
[Timestamp] 🔍 Intentando notificación de diagnóstico al admin
[Timestamp] ✅ Admin alcanzado en diagnóstico
[Timestamp] ⚠️ Bot COMUNICADO pero webhook falló
[Timestamp]    Tipo de fallo: WEBHOOK_ONLY
```

**El admin debería recibir:**
```
🚨 Atención Requerida

Orden: ORD-XXX
Cliente: +58 000-0000000

El webhook falló después de 4 reintentos.
Por favor contacta al cliente manualmente.

⚠️ Nota: No se pudo notificar al cliente automáticamente.
```

---

## 📊 Paso 5: Verificar Métricas del Sistema

### 5.1 Consultar Estado del Bot

```bash
sqlite3 data/bot.db

-- Estado actual
SELECT
    status,
    reason,
    datetime(last_update) as last_update,
    datetime(waha_last_success) as last_success,
    waha_consecutive_failures
FROM bot_status;
```

### 5.2 Consultar Historial de Fallos

```bash
-- Todos los fallos
SELECT
    failure_type,
    order_id,
    customer_phone,
    diagnostic_user_reached,
    diagnostic_admin_reached,
    datetime(created_at) as created_at,
    datetime(resolved_at) as resolved_at,
    resolution_method
FROM communication_failures
ORDER BY created_at DESC;

-- Fallos sin resolver
SELECT COUNT(*) as unresolved_failures
FROM communication_failures
WHERE resolved_at IS NULL;

-- Estadísticas por tipo
SELECT
    failure_type,
    COUNT(*) as count,
    SUM(CASE WHEN resolved_at IS NOT NULL THEN 1 ELSE 0 END) as resolved,
    SUM(CASE WHEN resolved_at IS NULL THEN 1 ELSE 0 END) as pending
FROM communication_failures
GROUP BY failure_type;
```

---

## 🔧 Paso 6: Test de API (Opcional)

Si quieres crear un endpoint API para consultar el estado:

```python
# app/api/monitoring.py (crear si no existe)

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from config.database import get_db
from app.services.bot_status_service import BotStatusService

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])

@router.get("/health")
async def get_system_health(db: Session = Depends(get_db)):
    """Obtiene el estado de salud del sistema"""
    bot_status_service = BotStatusService(db)
    health = await bot_status_service.get_health_summary()
    return health

@router.get("/failures")
async def get_communication_failures(
    resolved: bool = False,
    db: Session = Depends(get_db)
):
    """Lista fallos de comunicación"""
    from app.database.models import CommunicationFailure

    query = db.query(CommunicationFailure)

    if not resolved:
        query = query.filter(CommunicationFailure.resolved_at.is_(None))

    failures = query.order_by(CommunicationFailure.created_at.desc()).all()

    return [failure.to_dict() for failure in failures]
```

### Probar el Endpoint

```bash
# Estado de salud
curl http://localhost:8000/api/monitoring/health | jq

# Resultado esperado:
{
  "status": "online",
  "is_healthy": true,
  "reason": "Sistema iniciado",
  "consecutive_failures": 0,
  "unresolved_communication_failures": 0,
  "last_success_timestamp": "2025-11-14T10:30:00",
  "seconds_since_last_success": 120.5,
  "last_update": "2025-11-14T10:30:00",
  "metadata": {}
}

# Fallos sin resolver
curl http://localhost:8000/api/monitoring/failures | jq
```

---

## 📝 Checklist de Testing Completo

Usa este checklist para asegurar que todo funciona:

### Migración de Base de Datos
- [ ] Script de migración ejecutado sin errores
- [ ] Tabla `bot_status` creada
- [ ] Tabla `communication_failures` creada
- [ ] Registro inicial en `bot_status` con estado "online"

### Test 1: WAHA Caído
- [ ] WAHA detenido
- [ ] Orden creada en webapp
- [ ] Logs muestran "BOT COMPLETAMENTE INCOMUNICADO"
- [ ] Estado del bot: `incommunicado_critico`
- [ ] Registro en `communication_failures` con tipo `TOTAL_COMMUNICATION_LOSS`
- [ ] Usuario NO alcanzado
- [ ] Admin NO alcanzado

### Test 2: Solo Webhook Falla
- [ ] Fallo inyectado temporalmente
- [ ] Logs muestran "Bot COMUNICADO pero webhook falló"
- [ ] Estado del bot: `degraded`
- [ ] Registro en `communication_failures` con tipo `WEBHOOK_ONLY`
- [ ] Usuario alcanzado (recibió mensaje simple)
- [ ] Código de prueba revertido

### Test 3: Número Inválido
- [ ] Número inválido usado
- [ ] Usuario no alcanzable
- [ ] Admin alcanzado
- [ ] Estado: `degraded`
- [ ] Tipo: `WEBHOOK_ONLY`

### Recuperación
- [ ] WAHA reiniciado
- [ ] Nueva orden exitosa
- [ ] Estado del bot vuelve a `online`
- [ ] Log muestra "Bot recuperado"

### Verificación de BD
- [ ] `bot_status` tiene datos correctos
- [ ] `communication_failures` registra todos los fallos
- [ ] Timestamps son correctos
- [ ] Foreign keys funcionan

---

## 🐛 Troubleshooting

### Problema: "ModuleNotFoundError: No module named 'app.services.communication_diagnostic_service'"

**Solución:**
```bash
# Verificar que el archivo existe
ls -la app/services/communication_diagnostic_service.py

# Reiniciar el servidor
# Ctrl+C y volver a ejecutar
python main.py
```

### Problema: "Table bot_status doesn't exist"

**Solución:**
```bash
# Ejecutar migración
python scripts/migrate_add_bot_monitoring.py

# Verificar
sqlite3 data/bot.db ".tables"
```

### Problema: Los logs no muestran el diagnóstico

**Solución:**
```bash
# Verificar que el código en cart.py tiene la integración
grep -A 10 "DIAGNÓSTICO" app/api/cart.py

# Debería mostrar el código del diagnóstico
```

### Problema: ADMIN_PHONE no configurado

**Solución:**
```bash
# En .env o config/settings.py
ADMIN_PHONE="+58424XXXXXXX"

# Reiniciar servidor
```

---

## 📚 Próximos Pasos

Una vez que todos los tests pasen:

1. ✅ **Dashboard**: Implementar vista de estado del bot
2. ✅ **Alertas**: Configurar notificaciones por email/SMS
3. ✅ **Auto-recuperación**: Procesar órdenes pendientes automáticamente
4. ✅ **Healthcheck Proactivo**: Implementar verificación periódica (Fase 2)
5. ✅ **Métricas**: Agregar gráficas de disponibilidad

---

**Para más escenarios de testing, ver**: [COMMUNICATION_DETECTION_EXAMPLES.md](./COMMUNICATION_DETECTION_EXAMPLES.md)
