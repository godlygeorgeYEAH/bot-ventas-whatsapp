# 🛒 WebApp Cart - Guía de Setup Completa

## 📋 Tabla de Contenidos
1. [Prerequisitos](#prerequisitos)
2. [Backend Setup](#backend-setup)
3. [Frontend Setup](#frontend-setup)
4. [Configuración de Red Local](#configuración-de-red-local)
5. [Testing](#testing)
6. [Despliegue a Producción](#despliegue-a-producción)
7. [Troubleshooting](#troubleshooting)

---

## 🔧 Prerequisitos

### Software Requerido:
- Python 3.11+
- Node.js 18+ y npm/pnpm
- SQLite3
- Git

### Servicios Externos:
- WAHA (WhatsApp API) corriendo
- Ollama con modelo llama3.2 (para LLM)

---

## 🔨 Backend Setup

### 1. Crear Base de Datos

Si es una **instalación nueva**:
```bash
cd bot-ventas-whatsapp
python scripts/setup_db.py
python scripts/seed_products.py
```

Si tienes una **BD existente**, ejecutar migraciones:
```bash
python scripts/migrate_add_abandoned_fields.py
```

### 2. Configurar Variables de Entorno

Crear/editar `bot-ventas-whatsapp/.env`:
```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# WebApp Configuration
WEBAPP_BASE_URL=http://localhost:5174
CART_SESSION_HOURS=24

# WAHA Configuration  
WAHA_BASE_URL=http://localhost:3000
WAHA_SESSION_NAME=default

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# Database
DATABASE_URL=sqlite:///./bot_ventas.db

# Logging
LOG_LEVEL=INFO
DEBUG=False
```

### 3. Instalar Dependencias

```bash
cd bot-ventas-whatsapp
pip install -r requirements.txt
```

### 4. Verificar main.py

Asegurar que los módulos estén registrados correctamente:

```python
# ✅ CartLinkModule (ACTIVO)
from app.modules.cart_link_module import CartLinkModule
cart_link_module = CartLinkModule()
registry.register(cart_link_module)

# ✅ CheckoutModule (ACTIVO)
from app.modules.checkout_module import CheckoutModule
checkout_module = CheckoutModule()
registry.register(checkout_module)

# ❌ CreateOrderModule (DESACTIVADO)
# create_order_module = CreateOrderModule()
# registry.register(create_order_module)
```

### 5. Iniciar Backend

```bash
cd bot-ventas-whatsapp
python run.py
```

Deberías ver:
```
✅ OrderMonitorWorker iniciado (intervalo: 60s)
✅ [Registry] CartLinkModule registrado
✅ [Registry] CheckoutModule registrado
INFO: Uvicorn running on http://0.0.0.0:8000
```

---

## 🎨 Frontend Setup

### 1. Navegar al Directorio

```bash
cd bot-ventas-whatsapp/webapp-cart
```

### 2. Instalar Dependencias

```bash
npm install
# o
pnpm install
```

### 3. Configurar Variables de Entorno

Crear `webapp-cart/.env`:
```bash
# API Backend URL
VITE_API_BASE_URL=http://localhost:8000

# Para desarrollo en red local, usar tu IP:
# VITE_API_BASE_URL=http://192.168.x.x:8000
```

### 4. Verificar vite.config.ts

Debe tener:
```typescript
export default defineConfig({
  server: {
    port: 5174,
    host: '0.0.0.0',  // Permite acceso desde red local
  }
})
```

### 5. Iniciar Frontend

```bash
npm run dev
```

Deberías ver:
```
VITE v5.0.0  ready in 234 ms

➜  Local:   http://localhost:5174/
➜  Network: http://192.168.x.x:5174/
```

---

## 🌐 Configuración de Red Local

Para acceder desde móvil en tu red local:

### 1. Obtener tu IP Local

**Windows:**
```bash
ipconfig
# Busca "IPv4 Address": 192.168.x.x
```

**Mac/Linux:**
```bash
ifconfig | grep "inet "
```

### 2. Actualizar CORS en Backend

Editar `bot-ventas-whatsapp/app/main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5174",
        "http://192.168.x.x:5174",  # ← Tu IP local
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 3. Configurar Firewall (Windows)

**Permitir puerto 8000 (Backend):**
```powershell
netsh advfirewall firewall add rule name="FastAPI Bot" dir=in action=allow protocol=TCP localport=8000
```

**Permitir puerto 5174 (Frontend):**
```powershell
netsh advfirewall firewall add rule name="Vite Dev Server" dir=in action=allow protocol=TCP localport=5174
```

### 4. Actualizar .env del Frontend

```bash
VITE_API_BASE_URL=http://192.168.x.x:8000
```

### 5. Reiniciar Ambos Servicios

```bash
# Backend
Ctrl+C
python run.py

# Frontend (en otra terminal)
Ctrl+C
npm run dev
```

### 6. Probar desde Móvil

Abrir en el navegador del móvil:
```
http://192.168.x.x:5174/cart/{token}
```

---

## 🧪 Testing

### Test E2E Completo:

#### 1. Iniciar Orden desde WhatsApp
```
Usuario: "Quiero ordenar"
Bot: [Envía link único]
```

#### 2. Abrir WebApp
- Click en el link del bot
- Debe cargar el catálogo de productos

#### 3. Agregar Productos
- Click en "+" para agregar productos
- Ajustar cantidades
- Ver total actualizado en tiempo real

#### 4. Confirmar Orden
- Click en "Confirmar Orden"
- Esperar confirmación

#### 5. Completar Checkout en WhatsApp
```
Bot: "📍 Necesito tu ubicación GPS..."
Usuario: [Envía ubicación]
Bot: "🏠 ¿Alguna referencia?"
Usuario: "Casa azul"
Bot: "💳 ¿Método de pago?"
Usuario: "Efectivo"
Bot: "✅ Orden recibida, pendiente de confirmación"
```

#### 6. Confirmar Pago (Dashboard Admin)
- Ir a `http://localhost:5173`
- Encontrar orden PENDING
- Cambiar estado a CONFIRMED
- Esperar máximo 60 segundos

#### 7. Verificar Notificación
```
Bot: "🎉 ¡Pago Confirmado! Tu orden está siendo preparada..."
```

---

### Test de Timeout (30 minutos):

#### Opción A: Esperar 30 minutos
1. Completar orden en webapp
2. NO dar GPS/pago en WhatsApp
3. Esperar 30 minutos
4. Ver logs: `⏰ Orden XXX marcada como ABANDONED`

#### Opción B: Modificar timeout para testing
Editar temporalmente `app/services/order_monitor_worker.py`:
```python
# Cambiar de 30 minutos a 2 minutos
timeout_threshold = datetime.utcnow() - timedelta(minutes=2)
```

---

### Test de Retry Logic:

#### 1. Detener WAHA
```bash
# Detener el servicio WAHA temporalmente
```

#### 2. Completar Orden en WebApp
- El bot intentará enviar mensajes
- Fallará en intento 1

#### 3. Observar Logs
```
🔄 [Enviar mensaje inicial] Intento 1/4
⚠️ [Enviar mensaje inicial] Fallo en intento 1
⏳ [Enviar mensaje inicial] Esperando 30.0s...
🔄 [Enviar mensaje inicial] Intento 2/4
```

#### 4. Iniciar WAHA
- Durante los reintentos, iniciar WAHA
- Un reintento tendrá éxito

---

## 🚀 Despliegue a Producción

### Backend (FastAPI):

#### 1. Usar Gunicorn
```bash
pip install gunicorn
```

#### 2. Crear start script
```bash
#!/bin/bash
gunicorn app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 300
```

#### 3. Configurar Variables
```bash
# Producción .env
WEBAPP_BASE_URL=https://cart.tudominio.com
DATABASE_URL=postgresql://user:pass@host/db  # Usar PostgreSQL en prod
DEBUG=False
```

### Frontend (Vue):

#### 1. Build para Producción
```bash
cd webapp-cart
npm run build
```

#### 2. Servir con Nginx
```nginx
server {
    listen 80;
    server_name cart.tudominio.com;
    
    root /var/www/cart/dist;
    index index.html;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

#### 3. SSL con Certbot
```bash
certbot --nginx -d cart.tudominio.com
```

### Worker (OrderMonitorWorker):

El worker se inicia automáticamente con el bot. Para supervisión:

```bash
# Usar supervisor o systemd
[program:context-bot]
command=/path/to/venv/bin/python run.py
directory=/path/to/bot-ventas-whatsapp
autostart=true
autorestart=true
```

---

## 🐛 Troubleshooting

### Problema: "No such column: orders.abandoned_at"

**Solución:**
```bash
python scripts/migrate_add_abandoned_fields.py
```

---

### Problema: CORS Error en WebApp

**Síntoma:**
```
Access to fetch at 'http://localhost:8000/api/cart/xxx' 
has been blocked by CORS policy
```

**Solución:**
1. Verificar que la IP esté en `allow_origins` en `main.py`
2. Reiniciar backend después de cambios
3. Verificar que `VITE_API_BASE_URL` use la misma IP

---

### Problema: Token Inválido/Expirado

**Síntoma:**
WebApp muestra "Token inválido o expirado"

**Posibles causas:**
1. Token ya fue usado (`used=True`)
2. Token expiró (>24 horas)
3. Token no existe en BD

**Solución:**
- Generar nuevo link desde WhatsApp: "Quiero ordenar"
- Verificar en BD: `SELECT * FROM cart_sessions WHERE token='xxx'`

---

### Problema: Notificaciones No Llegan

**Síntoma:**
Cambio estado a CONFIRMED pero usuario no recibe mensaje

**Verificar:**
1. Worker corriendo: Buscar en logs `OrderMonitorWorker iniciado`
2. Orden tiene `confirmed_at`: 
   ```bash
   python scripts/debug_confirmed_orders.py
   ```
3. Logs del worker cada 60s:
   ```
   🔍 [OrderMonitorWorker] Iniciando chequeo...
   ```

**Solución:**
Si `confirmed_at` es NULL:
```bash
python scripts/fix_confirmed_at.py
```

---

### Problema: Stock No Se Restaura al Abandonar

**Verificar:**
- Worker detectando órdenes: Ver logs `⏰ Orden XXX marcada como ABANDONED`
- Columnas existen: `abandoned_at`, `abandonment_reason`

---

### Problema: Reintentos Muy Rápidos

**Síntoma:**
Los 4 intentos fallan en <10 segundos

**Verificar configuración:**
```python
# app/services/webhook_retry_service.py
webhook_retry_service = WebhookRetryService(
    max_retries=3,
    initial_delay=30.0,  # 30 segundos
    max_delay=90.0,      # 90 segundos
)
```

---

### Problema: WebApp No Carga Productos

**Síntoma:**
Carrito vacío, loading infinito

**Verificar:**
1. Backend corriendo: `curl http://localhost:8000/api/cart/{token}/products`
2. Productos en BD: `SELECT * FROM products WHERE is_active=1`
3. Console del navegador: Ver errores

**Solución:**
```bash
python scripts/seed_products.py
```

---

## 📞 Soporte

Para más información:
- [ARCHITECTURE_CHANGE.md](ARCHITECTURE_CHANGE.md) - Cambios arquitectónicos
- [CART_API_BACKEND.md](CART_API_BACKEND.md) - Documentación de API
- [ROADMAP.md](ROADMAP.md) - Estado del proyecto

---

**Última actualización**: Noviembre 2025  
**Versión**: 2.0

