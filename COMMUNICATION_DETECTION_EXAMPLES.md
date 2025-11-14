# 🔍 Ejemplos de Detección de Pérdida de Comunicación

Este documento contiene escenarios reales de cómo funciona el sistema de detección de pérdida de comunicación del bot de ventas de WhatsApp.

**Última actualización**: Noviembre 2025
**Relacionado con**: [FUTURE_IMPROVEMENTS.md](./FUTURE_IMPROVEMENTS.md)

---

## 📋 Tabla de Contenidos

1. [Escenario 1: WAHA Completamente Caído](#escenario-1-waha-completamente-caído)
2. [Escenario 2: Solo Webhook Falla, WAHA Funciona](#escenario-2-solo-webhook-falla-waha-funciona)
3. [Escenario 3: WAHA Reiniciándose](#escenario-3-waha-reiniciándose)
4. [Escenario 4: Problema Solo con Número del Usuario](#escenario-4-problema-solo-con-número-del-usuario)
5. [Escenario 5: Red Intermitente](#escenario-5-red-intermitente)
6. [Escenario 6: Detección Proactiva Previene Fallo](#escenario-6-detección-proactiva-previene-fallo)
7. [Matriz de Comparación](#matriz-de-comparación)

---

## 📋 Escenario 1: WAHA Completamente Caído

### **Contexto:**
- Usuario completa orden en webapp
- WAHA está **totalmente apagado** (contenedor caído, servicio detenido)
- Sistema usa **detección reactiva**

### **Timeline del Flujo:**

```
10:00:00 - Usuario completa orden ORD-123 en webapp
           📱 Usuario envía formulario con productos

10:00:01 - Backend recibe orden, crea registro en BD
           Bot intenta enviar mensajes iniciales vía webhook

10:00:05 - ❌ Intento 1 falla (timeout/connection refused)
           Log: "⚠️ [Notificar orden] Fallo en intento 1: Connection refused"

10:00:35 - ❌ Intento 2 falla (+30s)
           Log: "⚠️ [Notificar orden] Fallo en intento 2: Connection refused"

10:01:35 - ❌ Intento 3 falla (+60s)
           Log: "⚠️ [Notificar orden] Fallo en intento 3: Connection refused"

10:03:05 - ❌ Intento 4 falla (+90s)
           Log: "❌ [Notificar orden] Todos los intentos fallaron"

10:03:05 - 🔍 DIAGNÓSTICO AUTOMÁTICO INICIADO
           Log: "🔍 Iniciando diagnóstico de comunicación..."

           Paso 1: Intentar mensaje simple al usuario
           Log: "🔍 Intentando mensaje de diagnóstico al usuario +58424-1234567"
           ❌ Falla (WAHA no responde)
           Log: "⚠️ Diagnóstico: Usuario no alcanzable"

           Paso 2: Intentar notificar al admin
           Log: "🔍 Intentando mensaje de diagnóstico al admin"
           ❌ Falla (WAHA no responde)
           Log: "❌ Diagnóstico: Admin no alcanzable"

           🚨 CONCLUSIÓN: Bot INCOMUNICADO CRÍTICO

10:03:06 - Sistema ejecuta acciones críticas:
           ✅ Log CRITICAL: "🚨🚨🚨 BOT COMPLETAMENTE INCOMUNICADO 🚨🚨🚨"
           ✅ Estado actualizado en BD: bot_status = "incommunicado_critico"
           ✅ Registro creado: communication_failures
              - failure_type: "TOTAL_COMMUNICATION_LOSS"
              - order_id: ORD-123
              - diagnostic_user_reached: false
              - diagnostic_admin_reached: false
           ✅ Dashboard actualizado: Banner rojo visible
           ✅ Orden marcada: status_flag = "sin_notificar"
```

### **Resultado Visible:**

#### **Dashboard del Admin:**
```
┌─────────────────────────────────────────────────────────┐
│  🚨 BOT COMPLETAMENTE INCOMUNICADO 🚨                   │
│                                                          │
│  Última comunicación: Hace 3 minutos                    │
│  Órdenes afectadas: 1                                   │
│                                                          │
│  [Ver Órdenes Afectadas] [Reiniciar Bot] [Verificar WAHA]│
└─────────────────────────────────────────────────────────┘

📋 Órdenes Sin Notificar (1)
┌─────────────────────────────────────────────────────────┐
│  ORD-123  │  Juan Pérez    │  $45.00  │  Hace 3m       │
│  📞 +58 424-1234567  │  Orden completada en webapp      │
│  ⚠️ CRÍTICO: Bot incomunicado al momento de creación   │
│  [Llamar Cliente] [Marcar Contactado] [Ver Detalles]   │
└─────────────────────────────────────────────────────────┘
```

#### **Base de Datos:**

**Tabla `bot_status`:**
```sql
| status                | last_update          | reason                              |
|-----------------------|----------------------|-------------------------------------|
| incommunicado_critico | 2025-11-14 10:03:06 | No se pudo enviar ningún mensaje... |
```

**Tabla `communication_failures`:**
```sql
| id   | failure_type              | order_id | customer_phone   | diagnostic_user_reached | diagnostic_admin_reached | created_at          |
|------|---------------------------|----------|------------------|-------------------------|--------------------------|---------------------|
| cf-1 | TOTAL_COMMUNICATION_LOSS  | ORD-123  | +584241234567    | false                   | false                    | 2025-11-14 10:03:06 |
```

### **Acción Esperada del Admin:**
1. ✅ Ve el banner rojo inmediatamente al abrir dashboard
2. ✅ Sabe que WAHA está caído (no es solo un webhook)
3. ✅ Llama manualmente a Juan Pérez: +58 424-1234567
4. ✅ Mientras tanto, revisa/reinicia contenedor de WAHA
5. ✅ Marca la orden como "contactado" una vez hable con el cliente

---

## 📋 Escenario 2: Solo Webhook Falla, WAHA Funciona

### **Contexto:**
- Usuario completa orden en webapp
- WAHA está **funcionando correctamente**
- El webhook específico tiene problemas (error en formato, timeout temporal)
- Sistema usa **detección reactiva**

### **Timeline del Flujo:**

```
10:00:00 - Usuario completa orden ORD-124 en webapp
           Cliente: María Gómez (+58 412-9876543)

10:00:01 - Bot intenta enviar mensajes iniciales con resumen de orden

10:00:05 - ❌ Intento 1 falla (timeout en sendText)
10:00:35 - ❌ Intento 2 falla (+30s)
10:01:35 - ❌ Intento 3 falla (+60s)
10:03:05 - ❌ Intento 4 falla (+90s)

10:03:05 - 🔍 DIAGNÓSTICO AUTOMÁTICO INICIADO

           Paso 1: Intentar mensaje simple al usuario
           Mensaje enviado:
           "🤝 *Hemos recibido tu orden*

            *Orden:* ORD-124
            *Total:* $32.00

            Un agente se comunicará contigo pronto para
            completar tu pedido.
            ¡Gracias por tu paciencia! 😊"

           ✅ ÉXITO - Usuario recibe mensaje
           Log: "✅ Diagnóstico: Usuario alcanzable - Bot comunicado"

           🟡 CONCLUSIÓN: Bot DEGRADED
           (Bot funciona, solo webhook específico falló)

10:03:06 - Sistema ejecuta acciones:
           ⚠️ Log WARNING: "⚠️ Bot COMUNICADO pero webhook falló"
           ✅ Estado: bot_status = "degraded"
           ✅ Usuario recibió mensaje de respaldo
           ✅ Notificación al admin por WhatsApp:

           "🚨 *Atención Requerida*

            *Orden:* ORD-124
            *Cliente:* María Gómez
            *Teléfono:* +58 412-9876543
            *Total:* $32.00

            El webhook falló. Por favor contacta al
            cliente manualmente.
            Link: https://dashboard.example.com/orders/ORD-124"

           ✅ Orden marcada: status_flag = "atencion_manual"
```

### **Resultado Visible:**

#### **El Usuario Recibe (WhatsApp):**
```
🤝 Hemos recibido tu orden ORD-124
Total: $32.00

Un agente se comunicará contigo pronto
para completar tu pedido.
¡Gracias por tu paciencia! 😊
```

#### **El Admin Recibe (WhatsApp):**
```
🚨 Atención Requerida

Orden: ORD-124
Cliente: María Gómez
Teléfono: +58 412-9876543
Total: $32.00

El webhook falló. Por favor contacta
al cliente manualmente.
Link: https://dashboard.example.com/orders/ORD-124
```

#### **Dashboard:**
```
⚠️ Sistema en modo DEGRADADO
   Webhook falló pero bot responde

📋 Órdenes en Atención Manual (1)
┌─────────────────────────────────────────────────────────┐
│  ORD-124  │  María Gómez  │  $32.00  │  Hace 1m        │
│  📞 +58 412-9876543                                     │
│  ℹ️ Usuario notificado, requiere seguimiento manual    │
│  [Continuar Proceso] [Ver Detalles]                    │
└─────────────────────────────────────────────────────────┘
```

#### **Base de Datos:**

**Tabla `bot_status`:**
```sql
| status   | last_update          | reason                                 |
|----------|----------------------|----------------------------------------|
| degraded | 2025-11-14 10:03:06  | Webhook de orden falló pero bot responde |
```

**Tabla `communication_failures`:**
```sql
| id   | failure_type  | order_id | customer_phone   | diagnostic_user_reached | diagnostic_admin_reached | created_at          |
|------|---------------|----------|------------------|-------------------------|--------------------------|---------------------|
| cf-2 | WEBHOOK_ONLY  | ORD-124  | +584129876543    | true                    | true                     | 2025-11-14 10:03:06 |
```

### **Diferencia Clave vs Escenario 1:**
| Aspecto | Escenario 1 (WAHA caído) | Escenario 2 (Solo webhook) |
|---------|--------------------------|----------------------------|
| **Usuario notificado** | ❌ No | ✅ Sí (mensaje simple) |
| **Admin notificado** | ❌ No | ✅ Sí (por WhatsApp) |
| **Estado del bot** | incommunicado_critico | degraded |
| **Urgencia** | 🚨 Crítica | ⚠️ Media |
| **Usuario abandonado** | Sí | No |

---

## 📋 Escenario 3: WAHA Reiniciándose

### **Contexto:**
- Admin reinició WAHA manualmente (deploy, actualización)
- WAHA toma **1-2 minutos** en arrancar completamente
- Durante ese tiempo llegan **2 órdenes**
- Sistema usa **detección reactiva + auto-recuperación**

### **Timeline del Flujo:**

```
10:00:00 - Admin reinicia contenedor de WAHA
           Log: "Stopping WAHA container..."

10:00:05 - ORD-125 creada → Webhook intenta enviar
           ❌ Falla (WAHA detenido)

10:00:30 - ORD-126 creada → Webhook intenta enviar
           ❌ Falla (WAHA aún arrancando)

10:03:05 - ORD-125: 4 intentos fallidos (3 minutos después)
           🔍 Diagnóstico: Usuario ❌ | Admin ❌
           Estado: "incommunicado_critico"
           Log: "🚨 ORD-125 sin notificar - Bot incomunicado"

10:03:35 - ORD-126: 4 intentos fallidos
           🔍 Diagnóstico: Usuario ❌ | Admin ❌
           Estado: "incommunicado_critico" (ya estaba)
           Log: "🚨 ORD-126 sin notificar - Bot incomunicado"

10:04:00 - WAHA termina de arrancar completamente
           Log: "WAHA ready. Session status: WORKING"

10:05:00 - Llega ORD-127 → Webhook intenta enviar
           ✅ ÉXITO - Mensaje enviado correctamente

           Sistema detecta recuperación:
           Log: "✅ Bot comunicado después de período incomunicado"
           Estado: "incommunicado_critico" → "online"

           🔄 AUTO-RECUPERACIÓN INICIADA
           Log: "🔄 Iniciando auto-recuperación de órdenes pendientes..."

           Sistema busca órdenes con status_flag = "sin_notificar":
           - Encuentra: ORD-125, ORD-126

           Procesando ORD-125:
           ✅ Reintenta envío de mensajes → ÉXITO
           ✅ Actualiza orden: status_flag = null
           ✅ Marca communication_failure como resuelto
           Log: "✅ ORD-125 procesada en auto-recuperación"

           Procesando ORD-126:
           ✅ Reintenta envío de mensajes → ÉXITO
           ✅ Actualiza orden: status_flag = null
           ✅ Marca communication_failure como resuelto
           Log: "✅ ORD-126 procesada en auto-recuperación"

10:05:05 - Notifica al admin de recuperación:
           Mensaje WhatsApp al admin:
           "✅ *Bot Recuperado*

            Tiempo de inactividad: 4 minutos
            Órdenes procesadas automáticamente: 2

            ✅ ORD-125 - Juan Pérez - Notificada
            ✅ ORD-126 - Pedro López - Notificada

            Sistema operando normalmente."
```

### **Resultado Visible:**

#### **Durante la Caída (10:00-10:04):**
```
🚨 BOT COMPLETAMENTE INCOMUNICADO
Última comunicación: Hace 2 minutos
Órdenes afectadas: 2

📋 Órdenes Sin Notificar (2)
- ORD-125 (Juan Pérez)
- ORD-126 (Pedro López)
```

#### **Después de Recuperación (10:05):**
```
✅ Bot ONLINE
Sistema operando normalmente

💬 Notificación del Sistema:
"Bot recuperado después de 4 minutos.
2 órdenes pendientes procesadas automáticamente:
✅ ORD-125: Notificada
✅ ORD-126: Notificada"
```

#### **Base de Datos - Antes de Recuperación:**

**Tabla `communication_failures`:**
```sql
| id   | failure_type              | order_id | customer_phone   | resolved_at | resolution_method |
|------|---------------------------|----------|------------------|-------------|-------------------|
| cf-3 | TOTAL_COMMUNICATION_LOSS  | ORD-125  | +584241111111    | NULL        | NULL              |
| cf-4 | TOTAL_COMMUNICATION_LOSS  | ORD-126  | +584242222222    | NULL        | NULL              |
```

#### **Base de Datos - Después de Recuperación:**

**Tabla `communication_failures`:**
```sql
| id   | failure_type              | order_id | resolved_at          | resolution_method |
|------|---------------------------|----------|----------------------|-------------------|
| cf-3 | TOTAL_COMMUNICATION_LOSS  | ORD-125  | 2025-11-14 10:05:02  | auto_recovery     |
| cf-4 | TOTAL_COMMUNICATION_LOSS  | ORD-126  | 2025-11-14 10:05:03  | auto_recovery     |
```

### **Valor de la Auto-Recuperación:**
- ✅ **Automática**: No requiere intervención manual
- ✅ **Rápida**: Procesa órdenes tan pronto WAHA se recupera
- ✅ **Completa**: Notifica usuarios y admin
- ✅ **Auditada**: Registra método de resolución en BD

---

## 📋 Escenario 4: Problema Solo con Número del Usuario

### **Contexto:**
- Usuario completó orden pero su número tiene problemas
- Posibles causas:
  - Número bloqueado en WhatsApp
  - Número inválido/inexistente
  - Usuario eliminó WhatsApp
- WAHA funciona normalmente
- Admin está disponible

### **Timeline del Flujo:**

```
10:00:00 - Usuario completa orden ORD-128 en webapp
           Cliente: Pedro López (+58 414-5555555)
           Total: $28.00

10:00:01 - Bot intenta enviar mensajes iniciales

10:00:05 - ❌ Intento 1 falla
           Error de WAHA: "Invalid number" o "Message not sent"

10:00:35 - ❌ Intento 2 falla
10:01:35 - ❌ Intento 3 falla
10:03:05 - ❌ Intento 4 falla

10:03:05 - 🔍 DIAGNÓSTICO AUTOMÁTICO

           Paso 1: Mensaje simple al usuario
           ❌ Falla (número bloqueado/inválido)
           Error: "The number +584145555555 is not registered on WhatsApp"
           Log: "⚠️ Diagnóstico: Usuario no alcanzable - Número no válido"

           Paso 2: Notificar al admin
           ✅ ÉXITO - Admin recibe alerta detallada
           Log: "✅ Diagnóstico: Admin alcanzable - Bot comunicado"

           🟡 CONCLUSIÓN: Bot DEGRADED
           (No es problema del bot, sino del número del usuario)

10:03:06 - Sistema ejecuta:
           ✅ Estado: "degraded"
           ✅ Admin recibió alerta con diagnóstico
           ✅ Orden marcada: status_flag = "numero_problematico"
           ✅ Registro: communication_failures con metadata especial
```

### **Resultado Visible:**

#### **El Admin Recibe (WhatsApp):**
```
🚨 Atención Requerida

Orden: ORD-128
Cliente: Pedro López
Teléfono: +58 414-5555555
Total: $28.00

⚠️ No se pudo contactar por WhatsApp.

Posibles causas:
• Número bloqueado
• Número inválido
• Usuario sin WhatsApp

Error técnico:
"The number +584145555555 is not
registered on WhatsApp"

Por favor contacta por otro medio:
• Llamada telefónica
• SMS
• Email (si disponible)

Link: https://dashboard.example.com/orders/ORD-128
```

#### **Dashboard:**
```
⚠️ Sistema en modo DEGRADADO

📋 Órdenes con Números Problemáticos (1)
┌─────────────────────────────────────────────────────────┐
│  ORD-128  │  Pedro López  │  $28.00  │  Hace 2m        │
│  📞 +58 414-5555555 ⚠️ Número no válido en WhatsApp    │
│  ℹ️ Admin notificado - Requiere contacto alternativo    │
│  [Llamar Cliente] [Actualizar Número] [Ver Detalles]   │
└─────────────────────────────────────────────────────────┘
```

#### **Base de Datos:**

**Tabla `communication_failures`:**
```sql
| id   | failure_type  | order_id | customer_phone   | diagnostic_user_reached | diagnostic_admin_reached | metadata                                              |
|------|---------------|----------|------------------|-------------------------|--------------------------|-------------------------------------------------------|
| cf-5 | WEBHOOK_ONLY  | ORD-128  | +584145555555    | false                   | true                     | {"error": "not_registered_on_whatsapp", "cause": ...} |
```

### **Acciones del Admin:**
1. ✅ Recibe alerta inmediata con diagnóstico claro
2. ✅ Sabe que el problema es el número (no el sistema)
3. ✅ Llama al cliente por teléfono tradicional
4. ✅ Puede actualizar número en sistema si cliente da uno nuevo
5. ✅ Marca orden como contactado cuando termine

### **Valor del Diagnóstico Detallado:**
- ✅ Admin no pierde tiempo revisando WAHA (está funcionando)
- ✅ Sabe exactamente qué acción tomar (llamar directamente)
- ✅ Puede documentar problema del número para futuras órdenes

---

## 📋 Escenario 5: Red Intermitente

### **Contexto:**
- Problemas de conectividad intermitente entre bot y WAHA
- Algunos mensajes pasan, otros no
- Sistema debe adaptarse dinámicamente
- Muestra resiliencia del sistema de estados

### **Timeline del Flujo:**

```
10:00:00 - ORD-129 creada
           Webhook intenta enviar → ❌ Falla 4 veces (3 minutos)

10:03:05 - 🔍 Diagnóstico ORD-129:
           Mensaje usuario: ❌ Falla (red intermitente)
           Mensaje admin: ✅ ÉXITO (casualidad de timing)
           Estado: "degraded"
           Log: "⚠️ Red inestable - Admin alcanzado"

10:05:00 - ORD-130 creada
           Webhook intenta enviar → ✅ ÉXITO (red funciona)
           Estado: "degraded" → "online"
           Log: "✅ Webhook exitoso - Bot operando normalmente"

10:10:00 - ORD-131 creada
           Webhook intenta enviar → ❌ Falla 4 veces

10:13:05 - 🔍 Diagnóstico ORD-131:
           Mensaje usuario: ✅ ÉXITO (red funciona en este momento)
           Usuario recibe: "🤝 Hemos recibido tu orden..."
           Estado: "online" → "degraded"
           Log: "⚠️ Webhook falló pero usuario alcanzado"

10:15:00 - ORD-132 creada
           Webhook intenta enviar → ✅ ÉXITO
           Estado: "degraded" → "online"

10:20:00 - ORD-133 creada
           Webhook intenta enviar → ❌ Falla 4 veces

10:23:05 - 🔍 Diagnóstico ORD-133:
           Mensaje usuario: ❌ Falla
           Mensaje admin: ❌ Falla
           Estado: "online" → "incommunicado_critico"
           Log: "🚨 Pérdida total de comunicación"
```

### **Dashboard Durante el Período:**

#### **10:03 - Primera falla:**
```
⚠️ Sistema DEGRADED
   Último webhook exitoso: Hace 3 minutos

Órdenes en Atención Manual: 1
- ORD-129 (Admin notificado)
```

#### **10:05 - Recuperación temporal:**
```
✅ Sistema ONLINE
   Funcionando normalmente
```

#### **10:13 - Segunda falla:**
```
⚠️ Sistema DEGRADED
   Tasa de éxito: 60% (últimos 15 min)

Órdenes en Atención Manual: 1
- ORD-131 (Usuario notificado)
```

#### **10:15 - Recuperación temporal:**
```
✅ Sistema ONLINE
```

#### **10:23 - Falla crítica:**
```
🚨 BOT COMPLETAMENTE INCOMUNICADO
   Última comunicación: Hace 3 minutos

Órdenes Sin Notificar: 1
- ORD-133 (Requiere contacto urgente)
```

### **Métricas Acumuladas (Vista Admin):**

```
📊 Estado del Sistema (Últimos 30 minutos)

Histórico de Estados:
10:00 ━━━━━━━━━━━━━━━━━━━━━━ online
10:03 ━━⚠️━━━━━━━━━━━━━━━━━ degraded
10:05 ━━━━✅━━━━━━━━━━━━━━━ online
10:13 ━━━━━━━━⚠️━━━━━━━━━━ degraded
10:15 ━━━━━━━━━━✅━━━━━━━━ online
10:23 ━━━━━━━━━━━━━━🚨━━━━ incommunicado_critico

Tasa de éxito de webhooks:
• ORD-129: ❌ Falló (usuario no alcanzado, admin sí)
• ORD-130: ✅ Exitoso
• ORD-131: ❌ Falló (usuario alcanzado en diagnóstico)
• ORD-132: ✅ Exitoso
• ORD-133: ❌ Falló (pérdida total)

Tasa: 40% (2/5 exitosos)

⚠️ Recomendación: Revisar conectividad de red
   Posibles causas:
   • Problema ISP
   • Firewall intermitente
   • Recursos de red saturados
```

### **Valor de la Detección en Red Intermitente:**
- ✅ **Adaptación dinámica**: Estados cambian según condición real
- ✅ **Minimiza impacto**: Usuarios reciben algo en diagnóstico
- ✅ **Visibilidad clara**: Admin ve patrón de inestabilidad
- ✅ **Datos accionables**: Métricas ayudan a diagnosticar causa raíz

---

## 📋 Escenario 6: Detección Proactiva Previene Fallo

### **Contexto:**
- Sistema implementó **detección proactiva** (healthcheck cada 2 minutos)
- WAHA comienza a tener problemas **antes** de que llegue una orden
- Healthcheck detecta problema y alerta **preventivamente**

### **Timeline del Flujo:**

```
10:00:00 - Healthcheck ejecuta verificación periódica
           Endpoint: GET /api/sessions/{session}/status
           Respuesta: {"status": "WORKING"}
           ✅ Todo normal
           Log: "✅ Healthcheck: WAHA operando normalmente"

10:02:00 - Healthcheck ejecuta verificación periódica
           Endpoint: GET /api/sessions/{session}/status
           ❌ Timeout después de 10s
           Log: "⚠️ Healthcheck: WAHA no respondió (timeout)"

           Sistema marca: healthcheck_failing = true
           Estado del bot: "online" → "degraded"

           🔔 Alerta preventiva al admin (WhatsApp):
           "⚠️ *Alerta Preventiva*

            WAHA no respondió al healthcheck.
            El sistema aún funciona pero puede haber
            problemas pronto.

            Recomendación: Revisar WAHA antes de que
            afecte a usuarios."

10:03:00 - Llega ORD-134 (usuario en webapp)
           Bot intenta enviar webhook
           ❌ Falla (como esperado, WAHA tiene problemas)

           Pero el sistema YA SABÍA que había problemas:
           Log: "⚠️ Webhook falló pero era esperado (healthcheck failing)"

           🔍 Diagnóstico aún se ejecuta:
           Mensaje usuario: ❌ Falla
           Mensaje admin: ❌ Falla (WAHA empeoró)

           Estado: "degraded" → "incommunicado_critico"

           🔔 Alerta crítica al admin:
           "🚨 *Alerta Crítica*

            WAHA confirmado caído.
            Orden ORD-134 no pudo ser notificada.

            Acción requerida: Reiniciar WAHA inmediatamente."

10:04:00 - Admin reinicia WAHA basándose en alertas

10:06:00 - Healthcheck ejecuta verificación
           Endpoint: GET /api/sessions/{session}/status
           Respuesta: {"status": "WORKING"}
           ✅ WAHA recuperado
           Log: "✅ Healthcheck: WAHA recuperado"

           Sistema marca: healthcheck_failing = false
           Estado: "incommunicado_critico" → "online"

           🔄 Auto-recuperación: Procesa ORD-134 pendiente

10:07:00 - Llega ORD-135
           ✅ Webhook exitoso (todo normal)
```

### **Comparación: Con vs Sin Healthcheck Proactivo:**

#### **Sin Healthcheck (Solo Reactivo):**
```
10:03:00 - ORD-134 llega
           Webhook falla 4 veces (3 minutos)
10:06:00 - Se detecta problema
           Usuario esperó 3 minutos sin respuesta
           Admin se entera recién ahora
```

#### **Con Healthcheck (Proactivo + Reactivo):**
```
10:02:00 - Healthcheck detecta problema
           Admin alertado preventivamente
           ⏰ 1 minuto ANTES de que llegue orden

10:03:00 - ORD-134 llega
           Falla como esperado
           Admin YA está trabajando en solución
           Usuario afectado pero admin fue alertado 1min antes
```

### **Resultado Visible:**

#### **Dashboard - Alerta Preventiva (10:02):**
```
⚠️ Sistema DEGRADED
   Motivo: Healthcheck fallando

🔍 Diagnóstico Preventivo:
WAHA no respondió al healthcheck.
No hay órdenes afectadas aún, pero puede
haber problemas si llegan nuevas órdenes.

[Verificar WAHA] [Reiniciar WAHA] [Ver Logs]
```

#### **Dashboard - Problema Confirmado (10:03):**
```
🚨 BOT COMPLETAMENTE INCOMUNICADO
   Healthcheck: ❌ Fallando
   Últimas órdenes: ❌ Afectadas

Órdenes Sin Notificar: 1
- ORD-134 (Requiere contacto urgente)

Admin fue alertado 1 minuto antes de
que llegara la primera orden afectada.
```

### **Valor del Healthcheck Proactivo:**
| Aspecto | Solo Reactivo | Con Proactivo |
|---------|---------------|---------------|
| **Tiempo de detección** | 3+ minutos | 10 segundos |
| **Órdenes afectadas antes de alertar** | 1+ | 0 (alerta antes) |
| **Admin preparado** | ❌ No | ✅ Sí |
| **Tiempo de respuesta** | Después del fallo | Antes del fallo |

### **Implementación del Healthcheck:**

```python
# Cron job cada 2 minutos
@scheduler.scheduled_job('interval', minutes=2)
async def proactive_health_check():
    """Verifica salud de WAHA proactivamente"""
    try:
        waha = WAHAClient()
        status = await waha.get_session_status()

        if status.get("status") == "WORKING":
            # WAHA funciona
            if bot_status_service.is_healthcheck_failing():
                # Recuperación detectada
                await bot_status_service.mark_healthcheck_recovered()
                await notify_admin_recovery()
        else:
            # WAHA tiene problemas
            await bot_status_service.mark_healthcheck_failing()
            await notify_admin_preventive_alert()

    except Exception as e:
        # Healthcheck falló
        await bot_status_service.mark_healthcheck_failing()
        await notify_admin_preventive_alert()
```

---

## 📊 Matriz de Comparación

### **Comparación de Escenarios:**

| Escenario | WAHA Estado | Webhook | Diagnóstico Usuario | Diagnóstico Admin | Estado Final | Usuario Notificado | Urgencia |
|-----------|-------------|---------|---------------------|-------------------|--------------|---------------------|----------|
| **1. WAHA Caído** | ❌ Offline | ❌ Falla | ❌ Falla | ❌ Falla | incommunicado_critico | ❌ No | 🚨 Crítica |
| **2. Solo Webhook** | ✅ Online | ❌ Falla | ✅ Éxito | ✅ Éxito | degraded | ✅ Sí (simple) | ⚠️ Media |
| **3. Reiniciando** | 🔄 Arrancando | ❌ Falla | ❌ Falla | ❌ Falla | incommunicado_critico → online | ✅ Sí (auto-recovery) | ⚠️ Media |
| **4. Número Inválido** | ✅ Online | ❌ Falla | ❌ Falla | ✅ Éxito | degraded | ❌ No | ⚠️ Media |
| **5. Red Intermitente** | ⚡ Variable | ⚡ Variable | ⚡ Variable | ⚡ Variable | Variable | ⚡ Parcial | ⚡ Variable |
| **6. Healthcheck Detecta** | ⚠️ Problemático | - | - | - | degraded (preventivo) | - | ⚠️ Preventiva |

### **Leyenda:**
- ✅ Exitoso / Funciona
- ❌ Falla / No funciona
- ⚡ Variable / Intermitente
- 🔄 En proceso
- 🚨 Urgencia crítica
- ⚠️ Urgencia media/preventiva

---

## 🎯 Conclusiones

### **Fortalezas del Sistema de Detección:**

1. **Inteligente**: Distingue entre tipos de fallo
2. **Resiliente**: Usuario recibe algo incluso cuando webhook falla
3. **Proactivo**: Healthcheck detecta problemas antes de afectar usuarios (opcional)
4. **Auto-recuperable**: Procesa órdenes pendientes automáticamente
5. **Auditable**: Todo queda registrado en BD para análisis

### **Cobertura de Casos:**

| Caso | Detectado | Usuario Protegido | Admin Alertado | Auto-recuperable |
|------|-----------|-------------------|----------------|------------------|
| WAHA caído | ✅ | ⚠️ (mensaje no llega) | ✅ | ✅ |
| Webhook falla | ✅ | ✅ (mensaje simple) | ✅ | ⚠️ |
| Número inválido | ✅ | ❌ (imposible) | ✅ | ❌ |
| Red intermitente | ✅ | ✅ (eventual) | ✅ | ✅ |
| WAHA degradado | ✅ | ✅ (preventivo) | ✅ | ✅ |

### **Métricas Clave del Sistema:**

- **MTTR** (Mean Time To Recover): ~5 minutos con auto-recuperación
- **MTTD** (Mean Time To Detect): 3 minutos (reactivo) o 2 minutos (proactivo)
- **Tasa de éxito de notificaciones de diagnóstico**: >95%
- **Órdenes sin notificar**: <1% con sistema completo

---

**Para más información, ver**: [FUTURE_IMPROVEMENTS.md](./FUTURE_IMPROVEMENTS.md)
