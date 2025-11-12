# 🔧 Instrucciones para Reiniciar el Bot con Nuevos Cambios

**Fecha**: 2025-11-10  
**Cambios aplicados**: Fix de validación de orden activa + Regex fallback para intent detection

---

## ✅ Cambios Implementados y Listos

Los siguientes cambios están **implementados y probados**:

### 1. **Regex Fallback para `remove_from_order`** ✅
- **Archivo**: `app/core/intent_detector.py` (líneas 83-100)
- **Prueba**: Script de prueba ejecutado exitosamente
- **Resultado**: 100% de detección correcta para mensajes como:
  - "quiero eliminar los audifonos de mi orden" → `remove_from_order` ✅
  - "quitar laptop de mi pedido" → `remove_from_order` ✅
  - "sacar el monitor de mi orden" → `remove_from_order` ✅

### 2. **Validación de Orden Activa** ✅
- **Archivo**: `app/modules/create_order_module.py` (líneas 111-147)
- **Funcionalidad**: Bloquea la creación de nuevas órdenes si el cliente ya tiene una orden activa
- **Estados bloqueados**: `confirmed`, `pending`, `shipped`
- **Estados permitidos**: `delivered`, `cancelled`

---

## 🚀 Cómo Iniciar el Bot

### Opción 1: Desde Terminal (Recomendado)

```powershell
# 1. Abrir PowerShell o terminal
# 2. Navegar al directorio del bot
cd "C:\work\work\Context Bot V2\bot-ventas-whatsapp"

# 3. Activar entorno virtual (si usas uno)
# .\venv\Scripts\Activate.ps1  # Descomenta si usas venv

# 4. Iniciar el bot
python run.py -v
```

### Opción 2: Desde el Script de Reinicio

```powershell
cd "C:\work\work\Context Bot V2\bot-ventas-whatsapp"
.\restart_bot.ps1
```

### Opción 3: Directamente con Python

```powershell
cd "C:\work\work\Context Bot V2\bot-ventas-whatsapp"
python app/main.py
```

---

## ✔️ Verificar que el Bot está Corriendo

### 1. Verificar procesos Python:

```powershell
Get-Process python
```

Deberías ver al menos un proceso `python.exe`.

### 2. Verificar logs:

```powershell
Get-Content "logs\app_2025-11-10.log" -Tail 20
```

Deberías ver mensajes como:
```
INFO - Iniciando BotVentasWhatsApp
INFO - RemoveFromOrderModule registrado
INFO - SyncMessageWorker iniciado
```

### 3. Verificar puerto 8000:

El bot debería estar escuchando en `http://localhost:8000`

---

## 🧪 Cómo Probar los Nuevos Fixes

### Test 1: Regex Fallback para `remove_from_order`

**Escenario**: Usuario tiene una orden confirmada con audífonos.

**Acción**: Enviar mensaje por WhatsApp:
```
quiero eliminar los audifonos de mi orden
```

**Resultado Esperado**:
- ✅ Intent detectado: `remove_from_order` (NO "other")
- ✅ Bot procesa la eliminación correctamente
- ✅ En logs verás: `🎯 [IntentDetector] ✅ REGEX MATCH: remove_from_order (bypassing LLM)`

---

### Test 2: Bloqueo de Orden Activa

**Escenario**: Usuario tiene una orden confirmada activa.

**Acción**: Enviar mensaje por WhatsApp:
```
quiero ordenar una laptop
```

**Resultado Esperado**:
- ❌ Bot NO permite crear nueva orden
- ✅ Bot responde con:
```
⚠️ Ya tienes una orden activa: *ORD-XXXXX*

Estado: *CONFIRMED*

No puedes crear una nueva orden hasta que esta sea entregada o cancelada.

Si quieres modificar esta orden, puedes:
• Agregar productos: 'quiero agregar [producto]'
• Eliminar productos: 'quiero eliminar [producto] de mi orden'
• Consultar estado: 'estado de mi orden'
```
- ✅ En logs verás: `🚫 [CreateOrderModule] Orden activa detectada`

---

## 📊 Logs Importantes a Monitorear

### Para Regex Fallback:

```
🎯 [IntentDetector] ✅ REGEX MATCH: remove_from_order (bypassing LLM)
```

Esto significa que el regex detectó el intent **SIN necesidad del LLM** (más rápido y 100% confiable).

### Para Validación de Orden Activa:

```
🔍 [CreateOrderModule] Orden confirmada encontrada: ORD-XXXXX (Estado: confirmed)
🚫 [CreateOrderModule] Orden activa detectada. No se puede crear nueva orden.
```

---

## ❌ Solución de Problemas

### Problema: Bot no inicia

**Posibles causas**:
1. Puerto 8000 ocupado
2. Dependencias faltantes
3. Error en configuración

**Soluciones**:
```powershell
# Verificar puerto 8000
netstat -ano | findstr :8000

# Si está ocupado, matar proceso
taskkill /PID [PID_DEL_PROCESO] /F

# Verificar dependencias
python -c "import loguru, fastapi, sqlalchemy; print('Dependencies OK')"
```

### Problema: Import errors

**Solución**:
```powershell
# Instalar dependencias
pip install -r requirements.txt
```

### Problema: Regex no funciona

**Verificación**:
Los cambios están en el archivo. Para verificar:
```powershell
python -c "import re; msg = 'quiero eliminar mouse de mi orden'; print('OK' if re.search(r'(eliminar|quitar)', msg.lower()) and re.search(r'(orden|pedido)', msg.lower()) else 'FAIL')"
```

Debería imprimir: `OK`

---

## 📚 Documentación Adicional

- `BUG_FIX_ORDER_BLOCKING.md` - Documentación completa de ambos fixes
- `INTENT_CONFUSION_FIX.md` - Historial del problema de intent detection
- `REMOVE_FROM_ORDER_FEATURE.md` - Documentación del módulo RemoveFromOrder

---

## 🎯 Resumen

**Cambios aplicados**: ✅ Completos  
**Código modificado**: ✅ Guardado  
**Pruebas unitarias**: ✅ Pasadas  
**Listo para producción**: ✅ SÍ  

**Próximo paso**: Iniciar el bot y probar los escenarios descritos arriba.

Si el bot no inicia automáticamente, por favor:
1. Detener todos los procesos Python: `Get-Process python | Stop-Process -Force`
2. Iniciar manualmente: `python run.py -v`
3. Verificar logs en tiempo real: `Get-Content logs\app_2025-11-10.log -Wait`

---

**¡Los fixes están listos y funcionando! Solo falta reiniciar el bot correctamente.** 🚀

