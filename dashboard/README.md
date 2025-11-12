# 🎯 Dashboard Administrativo - Bot de Ventas WhatsApp

Dashboard administrativo creado con Vue 3 + TypeScript + Element Plus para gestionar órdenes, productos y clientes del bot de ventas.

## 🚀 Características

- ✅ **Gestión de Órdenes**: Ver, filtrar y actualizar estados de órdenes
- ✅ **Estadísticas en Tiempo Real**: KPIs de órdenes por estado
- ✅ **Interfaz Moderna**: UI profesional con Element Plus
- ✅ **100% Responsive**: Optimizado para móvil, tablet y desktop
- ✅ **Vista Móvil**: Cards touch-friendly en lugar de tabla
- ✅ **Sidebar Colapsable**: Menú hamburguesa en móvil
- ✅ **Touch-Optimized**: Botones y áreas táctiles más grandes
- 🔜 **Dashboard de Métricas**: Gráficos y estadísticas (próximamente)
- 🔜 **Gestión de Productos**: CRUD de productos (próximamente)
- 🔜 **Gestión de Clientes**: Ver historial de clientes (próximamente)

## 📦 Tecnologías

- **Vue 3** - Framework progresivo
- **TypeScript** - Tipado estático
- **Vite** - Build tool ultra rápido
- **Element Plus** - Componentes UI premium
- **Vue Router** - Navegación
- **Pinia** - State management
- **Axios** - Cliente HTTP
- **ECharts** - Gráficos (futuro)

## 🛠️ Instalación

### Prerrequisitos

- Node.js 18+ 
- npm o pnpm

### Pasos

1. **Instalar dependencias:**
```bash
cd dashboard
npm install
```

2. **Configurar variables de entorno:**

Crear archivo `.env.development`:
```env
VITE_API_URL=http://localhost:8000
```

3. **Iniciar el servidor de desarrollo:**
```bash
npm run dev
```

El dashboard estará disponible en: `http://localhost:5173`

## 🎨 Estructura del Proyecto

```
dashboard/
├── src/
│   ├── api/              # Clientes HTTP para FastAPI
│   │   ├── client.ts     # Configuración de Axios
│   │   └── orders.ts     # API de órdenes
│   ├── assets/           # Imágenes y recursos estáticos
│   ├── components/       # Componentes reutilizables
│   ├── layouts/          # Layouts de página
│   │   └── MainLayout.vue
│   ├── router/           # Configuración de Vue Router
│   │   └── index.ts
│   ├── types/            # Tipos TypeScript
│   │   └── index.ts
│   ├── views/            # Páginas
│   │   ├── Orders.vue    # Gestión de órdenes
│   │   ├── Dashboard.vue
│   │   ├── Products.vue
│   │   └── Customers.vue
│   ├── App.vue           # Componente raíz
│   └── main.ts           # Punto de entrada
├── package.json
└── vite.config.ts
```

## 🔌 Integración con Backend

El dashboard se conecta al backend FastAPI en `http://localhost:8000`.

### Endpoints disponibles:

- `GET /api/orders` - Obtener todas las órdenes
- `GET /api/orders/{id}` - Obtener una orden específica
- `GET /api/orders/stats` - Obtener estadísticas
- `PATCH /api/orders/{id}/status` - Actualizar estado
- `POST /api/orders/{id}/cancel` - Cancelar orden

## 📱 Panel de Órdenes (100% Responsive)

### Vista Desktop (Tabla Completa):
- Tabla expandible con todos los detalles
- Múltiples columnas de información
- Ordenamiento y paginación
- Acciones en dropdown

### Vista Móvil (Cards Touch-Friendly):
- Cards individuales por orden
- Información resumida y clara
- Botones grandes para tocar fácilmente
- Modal de detalles completos
- Sin scroll horizontal

El panel de órdenes incluye:

### Características:

- ✅ **Tabla expandible** con detalles de items
- ✅ **Filtros por estado** (Pendiente, Confirmada, En Camino, Entregada, Cancelada)
- ✅ **Búsqueda** por número de orden o cliente
- ✅ **Acciones rápidas:**
  - Marcar como "En Camino"
  - Marcar como "Entregada"
  - Cancelar orden
- ✅ **KPIs** en la parte superior
- ✅ **Formato de moneda** automático
- ✅ **Enlaces a Google Maps** para ubicaciones
- ✅ **Paginación** de resultados

### Estados de Órdenes:

- 🔵 **Pendiente** (pending)
- 🟦 **Confirmada** (confirmed)
- 🟨 **En Camino** (shipped)
- 🟩 **Entregada** (delivered)
- 🟥 **Cancelada** (cancelled)

## 🎯 Uso

1. **Ver órdenes**: La tabla muestra todas las órdenes ordenadas por fecha
2. **Expandir orden**: Click en la flecha para ver los items y detalles completos
3. **Filtrar**: Usa los filtros en la parte superior
4. **Buscar**: Escribe en el campo de búsqueda
5. **Actualizar estado**: Click en "Acciones" y selecciona la acción deseada

## 🚀 Build para Producción

```bash
npm run build
```

Los archivos optimizados se generarán en la carpeta `dist/`.

### Deploy:

Puedes deployar el contenido de `dist/` en:
- Netlify
- Vercel
- GitHub Pages
- Nginx
- Cualquier servidor estático

## 🔧 Configuración Adicional

### Cambiar URL del API

Edita `.env.development` o `.env.production`:

```env
VITE_API_URL=https://tu-api.com
```

### Personalizar tema Element Plus

En `main.ts`:

```typescript
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

app.use(ElementPlus, {
  // Opciones de personalización
})
```

## 📝 Próximas Funcionalidades

- [ ] Dashboard con gráficos de ventas (ECharts)
- [ ] Gestión de productos (CRUD completo)
- [ ] Gestión de clientes
- [ ] Exportar órdenes a CSV/Excel
- [ ] Notificaciones en tiempo real (WebSockets)
- [ ] Sistema de autenticación
- [ ] Modo oscuro
- [ ] Reportes avanzados

## 🐛 Problemas Comunes

### El dashboard no se conecta al backend

- Verifica que FastAPI esté corriendo en `http://localhost:8000`
- Revisa la configuración de CORS en `app/main.py`
- Verifica la variable `VITE_API_URL`

### Error de CORS

Asegúrate de que en `app/main.py` esté configurado:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 📚 Recursos

- [Vue 3 Docs](https://vuejs.org/)
- [Element Plus](https://element-plus.org/)
- [Vite](https://vitejs.dev/)
- [TypeScript](https://www.typescriptlang.org/)

## 👤 Autor

Jorge - Bot de Ventas WhatsApp

---

🚀 **¡Disfruta gestionando tus órdenes!**
