# 📱 Arreglar Acceso desde Móvil

## 🔍 Problema
El dashboard carga desde móvil, pero las órdenes no cargan porque:
1. ❌ El puerto 8000 (FastAPI) no está abierto en el firewall
2. ❌ El frontend apunta a `localhost` en lugar de la IP local
3. ❌ CORS no permite acceso desde la IP local

## ✅ Solución (3 pasos)

### **PASO 1: Abrir puerto 8000 en el Firewall**

Ejecuta este comando **como Administrador** en PowerShell:

```powershell
# Click derecho en PowerShell → "Ejecutar como Administrador"
netsh advfirewall firewall add rule name="FastAPI Dev Server" dir=in action=allow protocol=TCP localport=8000
```

**Verificar:**
```powershell
netsh advfirewall firewall show rule name="FastAPI Dev Server"
```

---

### **PASO 2: Crear archivo `.env` en el dashboard**

Crea el archivo: `C:\work\work\Context Bot V2\bot-ventas-whatsapp\dashboard\.env`

Con este contenido:
```env
# API Configuration
# Usar la IP local de tu PC para acceder desde otros dispositivos
VITE_API_URL=http://192.168.68.101:8000
```

**⚠️ IMPORTANTE:** Tu IP local es **`192.168.68.101`**. Si cambia, actualiza este archivo.

---

### **PASO 3: Reiniciar ambos servidores**

#### **A. Reiniciar Frontend (Vite)**

En la terminal donde está corriendo `npm run dev`:
```bash
# Presiona Ctrl+C para detener
# Luego ejecuta de nuevo:
cd "C:\work\work\Context Bot V2\bot-ventas-whatsapp\dashboard"
npm run dev
```

#### **B. Reiniciar Backend (FastAPI)**

En la terminal donde está corriendo `python app/main.py`:
```bash
# Presiona Ctrl+C para detener
# Luego ejecuta de nuevo:
cd "C:\work\work\Context Bot V2\bot-ventas-whatsapp"
python app/main.py
```

---

## 📱 Acceder desde tu Móvil

Asegúrate de que tu móvil esté en la **misma red WiFi** que tu PC.

**Dashboard:**
```
http://192.168.68.101:5173
```

**API (para probar):**
```
http://192.168.68.101:8000/health
```

---

## ✅ Verificación

### **En tu móvil:**
1. Abre el navegador
2. Ve a `http://192.168.68.101:5173`
3. Deberías ver el dashboard
4. Las órdenes deberían cargar correctamente

### **Si aún no funciona:**

Verifica que el firewall aceptó la regla:
```powershell
netsh advfirewall firewall show rule name="FastAPI Dev Server"
```

Verifica que el backend esté escuchando en todas las interfaces:
```bash
netstat -ano | findstr :8000
```
Debería mostrar: `0.0.0.0:8000`

---

## 🔄 Cambios Realizados

### **Backend (`app/main.py`):**
✅ CORS actualizado para permitir IP local:
```python
allow_origins=[
    "http://localhost:5173",
    "http://192.168.68.101:5173",  # Acceso desde red local
    ...
]
```

### **Firewall Script (`enable-firewall.ps1`):**
✅ Agregado puerto 8000 (FastAPI)

---

## 🆘 Troubleshooting

### Error: "Connection refused" desde móvil
- Verifica que el firewall esté abierto (PASO 1)
- Verifica que el backend esté corriendo (`python app/main.py`)
- Verifica que la IP sea correcta: `ipconfig`

### Error: "CORS policy"
- Verifica que reiniciaste el backend (PASO 3B)
- Verifica que el archivo `.env` tenga la IP correcta

### Las órdenes no cargan
- Verifica que el archivo `.env` exista y tenga `VITE_API_URL` correcta
- Verifica que reiniciaste el frontend (PASO 3A)
- Abre la consola del navegador (F12) para ver errores

---

✅ **¡Listo! Después de estos 3 pasos deberías poder usar el dashboard desde tu móvil.**

