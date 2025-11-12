# 📸 Funcionalidad de Imágenes de Productos

## 🎯 Descripción General

Se ha implementado un sistema completo de gestión de imágenes para productos en el dashboard administrativo. Los usuarios pueden subir, visualizar y eliminar imágenes de productos con validaciones robustas y una interfaz intuitiva.

---

## ✨ Características Implementadas

### Backend (FastAPI)

#### **1. Servidor de Archivos Estáticos**
- 📁 Directorio de almacenamiento: `static/products/`
- 🌐 Montado en `/static` para servir imágenes públicamente
- ✅ Configurado en `app/main.py`

#### **2. Endpoints de API**

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/products/{id}/upload-image` | POST | Subir imagen de producto |
| `/api/products/{id}/delete-image` | DELETE | Eliminar imagen de producto |
| `/api/products/{id}/image` | GET | Obtener URL de imagen |

#### **3. Validaciones de Seguridad**

- **Extensiones permitidas**: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`
- **Tamaño máximo**: 5 MB
- **Validación de MIME type**: Verifica el tipo de contenido real
- **Nombres únicos**: Genera nombres con UUID para evitar colisiones

#### **4. Funcionalidad de Upload**

```python
# Características clave:
- Valida formato y tamaño de archivo
- Genera nombre único con UUID
- Elimina imagen anterior automáticamente (si existe)
- Guarda el archivo en static/products/
- Actualiza image_path en la base de datos
- Maneja errores de forma robusta
```

#### **5. Funcionalidad de Delete**

```python
# Características clave:
- Elimina archivo físico del servidor
- Limpia el campo image_path en la DB
- Valida que el producto exista
- Retorna confirmación de éxito
```

---

### Frontend (Vue 3 + Element Plus)

#### **1. Componente de Upload en Formulario**

**Ubicación**: `dashboard/src/views/Products.vue`

**Características**:
- 🖼️ **Preview de imagen actual**: Muestra la imagen existente del producto
- 📤 **Drag & Drop**: Arrastra y suelta para subir
- 🔍 **Preview de nueva imagen**: Vista previa antes de guardar
- ❌ **Botón de eliminar**: Elimina la imagen actual
- 🔄 **Botón de limpiar**: Limpia la selección sin guardar

```vue
<el-form-item label="Imagen">
  <!-- Preview de imagen actual -->
  <div v-if="currentImageUrl && !imagePreview" class="image-preview">
    <img :src="currentImageUrl" alt="Imagen actual" />
    <el-button @click="removeImage">Eliminar</el-button>
  </div>
  
  <!-- Preview de nueva imagen -->
  <div v-if="imagePreview" class="image-preview">
    <img :src="imagePreview" alt="Preview" />
    <el-button @click="clearImagePreview">Limpiar</el-button>
  </div>
  
  <!-- Upload component -->
  <el-upload
    :auto-upload="false"
    :show-file-list="false"
    :on-change="handleImageChange"
    accept="image/*"
    drag
  >
    <el-icon><Picture /></el-icon>
    <div>Arrastra una imagen o haz clic para seleccionar</div>
  </el-upload>
</el-form-item>
```

#### **2. Visualización en Tabla (Desktop)**

- 🖼️ **Columna de Imagen**: Muestra miniatura de 60x60px
- 🔲 **Placeholder**: Ícono de imagen cuando no hay foto
- 📐 **object-fit: cover**: Mantiene proporción sin distorsión

```vue
<el-table-column label="Imagen" width="80" align="center">
  <template #default="{ row }">
    <div class="product-image-cell">
      <img v-if="row.image_path" 
           :src="getImageUrl(row.image_path)" 
           class="table-product-image" />
      <el-icon v-else size="40" class="no-image-icon">
        <Picture />
      </el-icon>
    </div>
  </template>
</el-table-column>
```

#### **3. Visualización en Cards (Mobile)**

- 📱 **Card responsive**: Imagen de 80x80px en móvil
- 🎨 **Fondo gris suave**: Para productos sin imagen
- 🔳 **Diseño flex**: Imagen al lado del contenido

```vue
<div class="product-card-mobile">
  <div class="product-image-mobile">
    <img v-if="product.image_path" 
         :src="getImageUrl(product.image_path)" />
    <el-icon v-else size="40"><Picture /></el-icon>
  </div>
  <div class="product-info">
    <!-- Información del producto -->
  </div>
</div>
```

#### **4. Funciones JavaScript Clave**

##### `handleImageChange(uploadFile)`
- Valida tamaño (máx 5MB)
- Valida tipo (solo imágenes)
- Genera preview con FileReader
- Almacena archivo en `selectedImageFile`

##### `clearImagePreview()`
- Limpia el archivo seleccionado
- Elimina el preview visual

##### `removeImage()`
- Confirma con el usuario
- Llama a API DELETE
- Recarga la lista de productos

##### `uploadImage(productId)`
- Sube el archivo al servidor
- Actualiza la base de datos
- Muestra mensaje de éxito/error

##### `getImageUrl(imagePath)`
- Extrae el nombre del archivo
- Construye URL completa: `http://IP:8000/static/products/filename.jpg`

---

## 🔄 Flujo de Trabajo

### **Crear Producto con Imagen**

1. Usuario abre el diálogo de "Crear Producto"
2. Llena los campos requeridos (nombre, precio, etc.)
3. **Opcional**: Arrastra o selecciona una imagen
4. Ve el preview de la imagen
5. Hace clic en "Guardar"
6. Sistema:
   - Crea el producto en la BD
   - Sube la imagen al servidor
   - Vincula la imagen al producto
   - Muestra mensaje de éxito

### **Editar Imagen de Producto Existente**

1. Usuario hace clic en "Editar" en un producto
2. Si el producto tiene imagen, se muestra el preview
3. Usuario puede:
   - **Opción A**: Seleccionar nueva imagen (reemplaza la anterior)
   - **Opción B**: Eliminar imagen actual
4. Hace clic en "Guardar"
5. Sistema actualiza la imagen automáticamente

### **Eliminar Imagen**

1. Usuario abre el editor de producto
2. Hace clic en "Eliminar Imagen"
3. Confirma la acción
4. Sistema:
   - Elimina archivo del servidor
   - Limpia `image_path` en BD
   - Muestra confirmación

---

## 🛠️ Configuración Técnica

### **Backend (app/main.py)**

```python
from fastapi.staticfiles import StaticFiles

# Montar directorio estático
app.mount("/static", StaticFiles(directory="static"), name="static")
```

### **Backend (app/api/products.py)**

```python
import os, uuid, shutil
from pathlib import Path
from fastapi import UploadFile, File

# Configuración
UPLOAD_DIR = Path("static/products")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

# Funciones helper
def validate_image_file(file: UploadFile) -> None:
    # Validaciones de extensión, MIME type y tamaño
    ...

def generate_unique_filename(original_filename: str) -> str:
    # Genera nombre único con UUID
    ...
```

### **Frontend (dashboard/src/api/products.ts)**

```typescript
export const uploadProductImage = async (
  productId: string,
  file: File
): Promise<Product> => {
  const formData = new FormData()
  formData.append('file', file)
  const response = await apiClient.post(
    `/products/${productId}/upload-image`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } }
  )
  return response.data
}

export const deleteProductImage = async (
  productId: string
): Promise<void> => {
  await apiClient.delete(`/products/${productId}/delete-image`)
}
```

---

## ✅ Validaciones Implementadas

### **Frontend**
- ✅ Tamaño máximo: 5MB (muestra error si excede)
- ✅ Solo imágenes (valida `file.type.startsWith('image/')`)
- ✅ Preview instantáneo antes de subir

### **Backend**
- ✅ Extensión de archivo permitida
- ✅ MIME type validado (`image/jpeg`, `image/png`, etc.)
- ✅ Tamaño máximo de archivo
- ✅ Validación de producto existente
- ✅ Manejo de errores con mensajes claros

---

## 🎨 Estilos CSS Implementados

```css
/* Imagen en tabla (desktop) */
.table-product-image {
  width: 60px;
  height: 60px;
  object-fit: cover;
  border-radius: 8px;
  border: 1px solid #EBEEF5;
}

/* Imagen en card (mobile) */
.product-image-mobile {
  width: 80px;
  height: 80px;
  background: #F5F7FA;
  border-radius: 8px;
  overflow: hidden;
}

/* Preview en formulario */
.image-preview {
  position: relative;
  width: 200px;
  height: 200px;
  border: 1px dashed #DCDFE6;
  border-radius: 8px;
}
```

---

## 🚀 Funcionalidades Avanzadas

1. **Eliminación Automática de Imagen Anterior**
   - Al subir una nueva imagen, la anterior se elimina automáticamente
   - Evita acumulación de archivos huérfanos

2. **Generación de Nombres Únicos**
   - Usa UUID para evitar colisiones
   - Mantiene la extensión original del archivo

3. **Preview Instantáneo**
   - Muestra la imagen antes de subirla
   - Permite al usuario verificar antes de guardar

4. **Manejo Robusto de Errores**
   - Mensajes claros en español
   - No interrumpe la creación/edición del producto si falla la imagen

5. **100% Responsive**
   - Adapta el tamaño de las imágenes según el dispositivo
   - Drag & Drop funciona en desktop y tablet

---

## 📊 Mejoras Futuras (Opcionales)

- [ ] Compresión automática de imágenes grandes
- [ ] Soporte para múltiples imágenes por producto
- [ ] Galería de imágenes en el modal de detalles
- [ ] Crop/resize de imágenes en el frontend
- [ ] CDN para servir imágenes en producción
- [ ] WebP automático para mejor performance
- [ ] Lazy loading de imágenes en tabla/cards

---

## 🎉 Resultado Final

El dashboard ahora tiene un sistema completo de gestión de imágenes que:

✅ **Es fácil de usar**: Drag & drop intuitivo  
✅ **Es seguro**: Validaciones robustas  
✅ **Es eficiente**: Almacenamiento optimizado  
✅ **Es responsive**: Funciona en móvil y desktop  
✅ **Es visual**: Preview en tabla y cards  

**¡La gestión de productos ahora es visualmente completa! 🎨📸**

