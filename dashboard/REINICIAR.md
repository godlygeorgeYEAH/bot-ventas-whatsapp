# 🔄 REINICIAR CORRECTAMENTE

## ⚠️ IMPORTANTE: El problema es que Vite NO releyó el archivo .env.local

Vite solo lee los archivos `.env*` cuando se inicia, no en hot reload.

---

## 🚀 PASOS PARA ARREGLAR:

### **1️⃣ Detén COMPLETAMENTE el servidor Vite**

Ve a la terminal donde está corriendo `npm run dev`:

```bash
# Presiona Ctrl+C
# Espera a que el proceso termine completamente
```

---

### **2️⃣ Reinicia Vite desde cero**

```bash
cd "C:\work\work\Context Bot V2\bot-ventas-whatsapp\dashboard"
npm run dev
```

**Deberías ver en la terminal algo como:**
```
VITE v5.x.x  ready in xxx ms

➜  Local:   http://localhost:5173/
➜  Network: http://192.168.68.101:5173/
```

---

### **3️⃣ Verifica que la configuración se cargó**

Abre la consola del navegador (F12) en tu PC y escribe:

```javascript
console.log(import.meta.env.VITE_API_URL)
```

Debería mostrar: `http://192.168.68.101:8000`

Si muestra `undefined` o `http://localhost:8000`, el archivo `.env.local` NO se está leyendo.

---

### **4️⃣ En tu MÓVIL:**

1. **Cierra completamente** la pestaña del navegador (no solo refrescar)
2. **Abre una nueva pestaña**
3. Ve a: `http://192.168.68.101:5173`
4. **Espera a que cargue**
5. Abre la consola del navegador móvil (si puedes) y verifica errores

---

## 🔍 Si AÚN no funciona:

### **Opción A: Verificar en la PC primero**

Antes de probar en el móvil, **verifica en tu PC**:

1. Abre `http://192.168.68.101:5173` en tu navegador de PC (no localhost)
2. Abre DevTools (F12) → pestaña "Network"
3. Refresca la página
4. Busca las peticiones a `/api/orders`
5. **Verifica la URL**: Debería ser `http://192.168.68.101:8000/api/orders`

Si aparece `http://localhost:8000/api/orders`, el `.env.local` NO se está leyendo.

---

### **Opción B: Verificar en tiempo real**

En la consola del navegador de tu móvil, busca errores tipo:

```
Failed to fetch
net::ERR_CONNECTION_REFUSED
CORS error
```

---

## 🆘 Si el .env.local NO se está leyendo:

### **Alternativa 1: Modificar directamente el código**

Edita: `dashboard/src/api/client.ts`

```typescript
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://192.168.68.101:8000'
```

Cambiar por:

```typescript
const API_BASE_URL = 'http://192.168.68.101:8000' // Hardcoded para testing
```

---

### **Alternativa 2: Usar variable de entorno en línea de comandos**

```bash
$env:VITE_API_URL="http://192.168.68.101:8000"; npm run dev
```

---

## 📝 Checklist Final:

- [ ] Puerto 8000 abierto en firewall (✅ ya está)
- [ ] CORS configurado en backend (✅ ya está)
- [ ] Archivo `.env.local` creado con IP correcta (✅ ya está)
- [ ] **Frontend reiniciado DESPUÉS de crear .env.local** ← **ESTE ES EL PASO CRÍTICO**
- [ ] Caché del navegador limpiado
- [ ] Probado desde la PC primero con la IP (no localhost)
- [ ] Probado desde el móvil

---

## 🎯 La causa más común:

**Vite NO recarga automáticamente los archivos `.env`**. Debes reiniciar el servidor completamente.

---

✅ **Después de reiniciar Vite, DEBERÍA funcionar.**

