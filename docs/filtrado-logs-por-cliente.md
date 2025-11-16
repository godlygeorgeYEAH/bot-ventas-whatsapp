# Filtrado de Logs por Cliente

## Descripción

El sistema de logging del bot incluye **correlation IDs** que permiten filtrar todos los logs relacionados a un cliente específico o a una conversación particular.

Cada log incluye dos campos de identificación:
- **`client`**: Número de teléfono del cliente (ej: `+584244107121`) o `SYSTEM` para operaciones del sistema
- **`conv_id`**: Primeros 8 caracteres del UUID de conversación (ej: `a1b2c3d4`)

## Formato de Logs

### Console
```
13:06:01 | INFO     | +584244107121    | a1b2c3d4 | 📱 Mensaje recibido
```

### Archivo (`logs/app_YYYY-MM-DD.log`)
```
2025-11-16 13:06:01 | INFO     | +584244107121    | a1b2c3d4 | app.main:process_incoming_message - 📱 Mensaje recibido
```

**Estructura:**
```
[timestamp] | [nivel] | [teléfono cliente] | [conv_id] | [módulo:función] - [mensaje]
```

---

## Comandos de Filtrado

### 1. Filtrar por Número de Teléfono

Obtener **todos** los logs de un cliente específico:

```bash
grep '+584244107121' logs/app_2025-11-16.log
```

**Múltiples días:**
```bash
grep '+584244107121' logs/app_*.log
```

**Resultado:**
```
2025-11-16 13:06:01 | INFO     | +584244107121    | a1b2c3d4 | 📱 Mensaje recibido
2025-11-16 13:06:02 | INFO     | +584244107121    | a1b2c3d4 | 🔍 Detectando intent...
2025-11-16 13:06:03 | INFO     | +584244107121    | a1b2c3d4 | ✅ Orden creada
```

---

### 2. Filtrar por Conversation ID

Obtener logs de una **conversación específica**:

```bash
grep 'a1b2c3d4' logs/app_2025-11-16.log
```

**Útil cuando:**
- Un cliente tiene múltiples conversaciones
- Quieres rastrear una sesión específica
- Debugging de un flujo particular

---

### 3. Filtrado Combinado

**Cliente + Conversation ID:**
```bash
grep '+584244107121' logs/app_*.log | grep 'a1b2c3d4'
```

**Cliente + Nivel de log:**
```bash
grep '+584244107121' logs/app_*.log | grep 'ERROR'
```

**Cliente + Módulo específico:**
```bash
grep '+584244107121' logs/app_*.log | grep 'CreateOrderModule'
```

---

### 4. Seguimiento en Tiempo Real

**Monitorear cliente en vivo:**
```bash
tail -f logs/app_*.log | grep '+584244107121'
```

**Monitorear conversación:**
```bash
tail -f logs/app_*.log | grep 'a1b2c3d4'
```

**Con resaltado de color:**
```bash
tail -f logs/app_*.log | grep --color=always '+584244107121'
```

---

## Casos de Uso Comunes

### Debugging de un Error Reportado

Cliente reporta: "Mi orden no se procesó"

```bash
# 1. Ver toda la actividad del cliente hoy
grep '+584244107121' logs/app_$(date +%Y-%m-%d).log

# 2. Buscar errores específicos
grep '+584244107121' logs/app_*.log | grep -E 'ERROR|WARN'

# 3. Ver flujo de creación de orden
grep '+584244107121' logs/app_*.log | grep 'CreateOrderModule'
```

---

### Rastrear una Conversación Completa

```bash
# Obtener el conversation_id del cliente
grep '+584244107121' logs/app_*.log | head -1

# Ver toda la conversación
grep 'a1b2c3d4' logs/app_2025-11-16.log
```

---

### Encontrar Conversaciones de un Cliente

Ver **todos** los conversation IDs de un cliente:

```bash
grep '+584244107121' logs/app_*.log | cut -d'|' -f4 | sort -u
```

**Resultado:**
```
 a1b2c3d4
 b2c3d4e5
 c3d4e5f6
```

---

### Estadísticas de Cliente

**Contar mensajes procesados:**
```bash
grep '+584244107121' logs/app_*.log | wc -l
```

**Ver últimos 20 logs:**
```bash
grep '+584244107121' logs/app_*.log | tail -20
```

**Ver primeros logs (inicio de interacción):**
```bash
grep '+584244107121' logs/app_*.log | head -20
```

---

## Herramientas Avanzadas

### Con `less` para navegación

```bash
grep '+584244107121' logs/app_*.log | less
```

**Controles:**
- `/texto` - Buscar hacia adelante
- `?texto` - Buscar hacia atrás
- `n` - Siguiente resultado
- `q` - Salir

---

### Guardar logs filtrados

```bash
# Guardar en archivo
grep '+584244107121' logs/app_*.log > debug_cliente.txt

# Con timestamp en nombre
grep '+584244107121' logs/app_*.log > "debug_$(date +%Y%m%d_%H%M%S).txt"
```

---

### Análisis de Flujo Completo

Ver el flujo completo desde webhook hasta respuesta:

```bash
grep '+584244107121' logs/app_2025-11-16.log | grep -E 'Webhook|Procesando|Contexto|Intent|Orden|Notificación'
```

---

## Ejemplos por Módulo

### Flujo de Creación de Orden
```bash
grep '+584244107121' logs/app_*.log | grep -E 'CreateOrderModule|slots_data|delivery_location'
```

### Notificaciones
```bash
grep '+584244107121' logs/app_*.log | grep -E 'Notificación|enviada|admin'
```

### Errores de Validación
```bash
grep '+584244107121' logs/app_*.log | grep -E 'validación|inválido|ERROR'
```

### Webhooks Recibidos
```bash
grep '+584244107121' logs/app_*.log | grep 'Webhook'
```

---

## Tips y Mejores Prácticas

### 1. Usar variables para facilitar búsquedas

```bash
# Definir variable con número
CLIENTE="+584244107121"

# Usar en comandos
grep "$CLIENTE" logs/app_*.log
tail -f logs/app_*.log | grep "$CLIENTE"
```

### 2. Alias útiles (agregar a `.bashrc` o `.zshrc`)

```bash
# Ver logs de cliente
alias logcliente='function _logc(){ grep "$1" logs/app_*.log; }; _logc'

# Monitorear cliente en vivo
alias watchcliente='function _wc(){ tail -f logs/app_*.log | grep "$1"; }; _wc'

# Errores de cliente
alias errcliente='function _ec(){ grep "$1" logs/app_*.log | grep ERROR; }; _ec'
```

**Uso:**
```bash
logcliente "+584244107121"
watchcliente "+584244107121"
errcliente "+584244107121"
```

### 3. Combinación con `jq` (si tienes logs JSON)

Si en el futuro exportas a JSON:
```bash
cat logs/app.json | jq 'select(.client == "+584244107121")'
```

---

## Identificación de Conversation IDs

### Obtener conversation_id actual de un cliente

```bash
# Última conversación
grep '+584244107121' logs/app_$(date +%Y-%m-%d).log | tail -1 | cut -d'|' -f4 | tr -d ' '
```

### Ver cuándo inició cada conversación

```bash
grep '+584244107121' logs/app_*.log | grep 'Contexto leído' | grep 'estado=idle'
```

---

## Rotación de Logs

Los logs se rotan automáticamente:
- **Rotación**: Diaria a las 00:00
- **Retención**: 30 días
- **Compresión**: ZIP después de rotar

**Buscar en logs comprimidos:**
```bash
zgrep '+584244107121' logs/app_2025-10-15.log.zip
```

---

## Solución de Problemas

### No aparece el cliente en logs

**Verificar formato del número:**
```bash
# Con +
grep '+584244107121' logs/app_*.log

# Sin +
grep '584244107121' logs/app_*.log
```

### Logs muestran "SYSTEM"

Significa que el contexto no se estableció. Posibles causas:
1. Log generado antes de establecer contexto
2. Operación del sistema (no relacionada a cliente)
3. Error en la propagación del contexto

**Buscar logs SYSTEM para debug:**
```bash
grep 'SYSTEM' logs/app_*.log | tail -20
```

---

## Resumen de Comandos Esenciales

| Acción | Comando |
|--------|---------|
| Ver todos los logs de un cliente | `grep '+584XXX' logs/app_*.log` |
| Ver conversación específica | `grep 'a1b2c3d4' logs/app_*.log` |
| Monitorear en tiempo real | `tail -f logs/app_*.log \| grep '+584XXX'` |
| Buscar errores de cliente | `grep '+584XXX' logs/app_*.log \| grep ERROR` |
| Ver últimos 20 logs | `grep '+584XXX' logs/app_*.log \| tail -20` |
| Contar logs de cliente | `grep '+584XXX' logs/app_*.log \| wc -l` |
| Guardar logs filtrados | `grep '+584XXX' logs/app_*.log > debug.txt` |
| Listar conversation IDs | `grep '+584XXX' logs/app_*.log \| cut -d'\|' -f4 \| sort -u` |

---

## Soporte

Para más información sobre el sistema de logging, consulta:
- `config/logging_config.py` - Configuración de logging
- `app/core/correlation.py` - Sistema de correlation IDs
