"""
API endpoints para gestión de productos
"""
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import os
import uuid
import shutil
from pathlib import Path

from config.database import get_db
from app.database.models import Product
from loguru import logger

router = APIRouter(prefix="/api/products", tags=["products"])


# ============================================
# MODELOS PYDANTIC
# ============================================

class ProductBase(BaseModel):
    """Modelo base para productos"""
    name: str = Field(..., min_length=1, max_length=200, description="Nombre del producto")
    description: Optional[str] = Field(None, description="Descripción del producto")
    price: float = Field(..., gt=0, description="Precio unitario (debe ser mayor a 0)")
    stock: int = Field(..., ge=0, description="Stock disponible (debe ser >= 0)")
    category: Optional[str] = Field(None, max_length=100, description="Categoría del producto")
    sku: Optional[str] = Field(None, max_length=100, description="SKU único del producto")
    is_active: bool = Field(True, description="Si el producto está activo")


class ProductCreate(ProductBase):
    """Modelo para crear un producto"""
    pass


class ProductUpdate(BaseModel):
    """Modelo para actualizar un producto (todos los campos opcionales)"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    stock: Optional[int] = Field(None, ge=0)
    category: Optional[str] = Field(None, max_length=100)
    sku: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None


class ProductResponse(ProductBase):
    """Modelo de respuesta de producto"""
    id: str
    image_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    in_stock: bool = Field(..., description="Si el producto tiene stock y está activo")
    has_image: bool = Field(..., description="Si el producto tiene imagen")

    class Config:
        from_attributes = True


class ProductStats(BaseModel):
    """Estadísticas de productos"""
    total: int
    active: int
    inactive: int
    out_of_stock: int
    low_stock: int
    categories: int


# ============================================
# ENDPOINTS
# ============================================

@router.get("/", response_model=List[ProductResponse])
async def list_products(
    skip: int = Query(0, ge=0, description="Número de productos a saltar"),
    limit: int = Query(100, ge=1, le=1000, description="Límite de productos a retornar"),
    search: Optional[str] = Query(None, description="Buscar por nombre o descripción"),
    category: Optional[str] = Query(None, description="Filtrar por categoría"),
    is_active: Optional[bool] = Query(None, description="Filtrar por estado activo/inactivo"),
    in_stock: Optional[bool] = Query(None, description="Filtrar productos con/sin stock"),
    db: Session = Depends(get_db)
):
    """
    Listar productos con filtros opcionales
    
    - **skip**: Paginación - productos a saltar
    - **limit**: Máximo de productos a retornar
    - **search**: Buscar en nombre o descripción
    - **category**: Filtrar por categoría específica
    - **is_active**: true para activos, false para inactivos
    - **in_stock**: true para productos con stock, false para sin stock
    """
    try:
        query = db.query(Product)
        
        # Filtro de búsqueda
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Product.name.ilike(search_term),
                    Product.description.ilike(search_term),
                    Product.sku.ilike(search_term)
                )
            )
        
        # Filtro por categoría
        if category:
            query = query.filter(Product.category == category)
        
        # Filtro por estado activo
        if is_active is not None:
            query = query.filter(Product.is_active == is_active)
        
        # Filtro por stock
        if in_stock is not None:
            if in_stock:
                query = query.filter(Product.stock > 0)
            else:
                query = query.filter(Product.stock == 0)
        
        # Ordenar por nombre
        query = query.order_by(Product.name.asc())
        
        # Aplicar paginación
        products = query.offset(skip).limit(limit).all()
        
        logger.info(f"📦 Listando {len(products)} productos (filtros: search={search}, category={category}, is_active={is_active}, in_stock={in_stock})")
        
        return products
        
    except Exception as e:
        logger.error(f"❌ Error listando productos: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listando productos: {str(e)}")


@router.get("/stats", response_model=ProductStats)
async def get_products_stats(db: Session = Depends(get_db)):
    """
    Obtener estadísticas generales de productos
    """
    try:
        total = db.query(Product).count()
        active = db.query(Product).filter(Product.is_active == True).count()
        inactive = db.query(Product).filter(Product.is_active == False).count()
        out_of_stock = db.query(Product).filter(Product.stock == 0).count()
        low_stock = db.query(Product).filter(Product.stock > 0, Product.stock < 10).count()
        
        # Contar categorías únicas
        categories = db.query(func.count(func.distinct(Product.category))).scalar() or 0
        
        stats = ProductStats(
            total=total,
            active=active,
            inactive=inactive,
            out_of_stock=out_of_stock,
            low_stock=low_stock,
            categories=categories
        )
        
        logger.info(f"📊 Estadísticas de productos: {stats.dict()}")
        return stats
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo estadísticas: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo estadísticas: {str(e)}")


@router.get("/categories")
async def list_categories(db: Session = Depends(get_db)):
    """
    Listar todas las categorías de productos disponibles
    """
    try:
        categories = db.query(Product.category)\
            .filter(Product.category.isnot(None))\
            .distinct()\
            .order_by(Product.category.asc())\
            .all()
        
        categories_list = [cat[0] for cat in categories if cat[0]]
        
        logger.info(f"📂 Listando {len(categories_list)} categorías")
        return {"categories": categories_list}
        
    except Exception as e:
        logger.error(f"❌ Error listando categorías: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listando categorías: {str(e)}")


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: str, db: Session = Depends(get_db)):
    """
    Obtener un producto específico por ID
    """
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        
        if not product:
            logger.warning(f"⚠️ Producto no encontrado: {product_id}")
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        
        logger.info(f"📦 Producto encontrado: {product.name}")
        return product
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error obteniendo producto: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo producto: {str(e)}")


@router.post("/", response_model=ProductResponse, status_code=201)
async def create_product(product_data: ProductCreate, db: Session = Depends(get_db)):
    """
    Crear un nuevo producto
    
    Validaciones:
    - Nombre es requerido
    - Precio debe ser mayor a 0
    - Stock debe ser >= 0
    - SKU debe ser único (si se proporciona)
    """
    try:
        # Validar SKU único
        if product_data.sku:
            existing = db.query(Product).filter(Product.sku == product_data.sku).first()
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Ya existe un producto con el SKU '{product_data.sku}'"
                )
        
        # Crear nuevo producto
        new_product = Product(
            name=product_data.name,
            description=product_data.description,
            price=product_data.price,
            stock=product_data.stock,
            category=product_data.category,
            sku=product_data.sku,
            is_active=product_data.is_active
        )
        
        db.add(new_product)
        db.commit()
        db.refresh(new_product)
        
        logger.info(f"✅ Producto creado: {new_product.name} (ID: {new_product.id})")
        return new_product
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error creando producto: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creando producto: {str(e)}")


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    product_data: ProductUpdate,
    db: Session = Depends(get_db)
):
    """
    Actualizar un producto existente
    
    Solo se actualizan los campos proporcionados (PATCH-like behavior)
    """
    try:
        # Buscar producto
        product = db.query(Product).filter(Product.id == product_id).first()
        
        if not product:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        
        # Validar SKU único si se está actualizando
        if product_data.sku and product_data.sku != product.sku:
            existing = db.query(Product).filter(
                Product.sku == product_data.sku,
                Product.id != product_id
            ).first()
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Ya existe otro producto con el SKU '{product_data.sku}'"
                )
        
        # Actualizar solo los campos proporcionados
        update_data = product_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(product, field, value)
        
        db.commit()
        db.refresh(product)
        
        logger.info(f"✅ Producto actualizado: {product.name} (ID: {product_id})")
        return product
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error actualizando producto: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error actualizando producto: {str(e)}")


@router.delete("/{product_id}")
async def delete_product(product_id: str, db: Session = Depends(get_db)):
    """
    Eliminar un producto permanentemente
    
    ⚠️ ADVERTENCIA: Esta acción no se puede deshacer
    
    Nota: Si hay órdenes asociadas, se recomienda desactivar el producto
    en lugar de eliminarlo (PUT con is_active=false)
    """
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        
        if not product:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        
        product_name = product.name
        
        # Eliminar producto
        db.delete(product)
        db.commit()
        
        logger.info(f"🗑️ Producto eliminado: {product_name} (ID: {product_id})")
        return {
            "success": True,
            "message": f"Producto '{product_name}' eliminado exitosamente"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error eliminando producto: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error eliminando producto: {str(e)}")


@router.patch("/{product_id}/stock")
async def update_stock(
    product_id: str,
    new_stock: int = Query(..., ge=0, description="Nuevo valor de stock"),
    db: Session = Depends(get_db)
):
    """
    Actualizar solo el stock de un producto
    
    Endpoint rápido para ajustes de inventario
    """
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        
        if not product:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        
        old_stock = product.stock
        product.stock = new_stock
        
        db.commit()
        db.refresh(product)
        
        logger.info(f"📦 Stock actualizado: {product.name} - {old_stock} → {new_stock}")
        return {
            "success": True,
            "product_name": product.name,
            "old_stock": old_stock,
            "new_stock": new_stock
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error actualizando stock: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error actualizando stock: {str(e)}")


@router.patch("/{product_id}/toggle-active")
async def toggle_active(product_id: str, db: Session = Depends(get_db)):
    """
    Activar/desactivar un producto
    
    Endpoint rápido para cambiar el estado activo
    """
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        
        if not product:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        
        product.is_active = not product.is_active
        
        db.commit()
        db.refresh(product)
        
        status = "activado" if product.is_active else "desactivado"
        logger.info(f"🔄 Producto {status}: {product.name}")
        
        return {
            "success": True,
            "product_name": product.name,
            "is_active": product.is_active,
            "message": f"Producto '{product.name}' {status} exitosamente"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error cambiando estado: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error cambiando estado: {str(e)}")


# ============================================
# ENDPOINTS DE MANEJO DE IMÁGENES
# ============================================

# Configuración de almacenamiento
UPLOAD_DIR = Path("static/products")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Tipos de archivo permitidos
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


def validate_image_file(file: UploadFile) -> None:
    """
    Validar que el archivo sea una imagen válida
    
    Raises:
        HTTPException: Si el archivo no es válido
    """
    # Validar extensión
    file_ext = Path(file.filename or "").suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de archivo no permitido. Solo se aceptan: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Validar tipo MIME
    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="El archivo debe ser una imagen"
        )


def generate_unique_filename(original_filename: str) -> str:
    """
    Generar un nombre de archivo único manteniendo la extensión original
    
    Args:
        original_filename: Nombre original del archivo
        
    Returns:
        Nombre único para el archivo
    """
    file_ext = Path(original_filename).suffix.lower()
    unique_id = str(uuid.uuid4())
    return f"{unique_id}{file_ext}"


@router.post("/{product_id}/upload-image")
async def upload_product_image(
    product_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Subir una imagen para un producto
    
    - **product_id**: ID del producto
    - **file**: Archivo de imagen (JPG, PNG, GIF, WEBP)
    
    Limitaciones:
    - Tamaño máximo: 5 MB
    - Formatos permitidos: JPG, JPEG, PNG, GIF, WEBP
    """
    try:
        # Buscar producto
        product = db.query(Product).filter(Product.id == product_id).first()
        
        if not product:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        
        # Validar archivo
        validate_image_file(file)
        
        # Validar tamaño (leer contenido)
        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"El archivo es demasiado grande. Tamaño máximo: {MAX_FILE_SIZE / 1024 / 1024:.1f} MB"
            )
        
        # Eliminar imagen anterior si existe
        if product.image_path and os.path.exists(product.image_path):
            try:
                os.remove(product.image_path)
                logger.info(f"🗑️ Imagen anterior eliminada: {product.image_path}")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo eliminar imagen anterior: {str(e)}")
        
        # Generar nombre único para el archivo
        filename = generate_unique_filename(file.filename or "image.jpg")
        file_path = UPLOAD_DIR / filename
        
        # Guardar archivo
        with open(file_path, "wb") as f:
            f.write(contents)
        
        # Actualizar path en BD (guardar path relativo)
        product.image_path = str(file_path)
        db.commit()
        db.refresh(product)
        
        logger.info(f"📷 Imagen subida para producto '{product.name}': {filename}")
        
        return {
            "success": True,
            "message": "Imagen subida exitosamente",
            "filename": filename,
            "image_url": f"/static/products/{filename}",
            "product_name": product.name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error subiendo imagen: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error subiendo imagen: {str(e)}")


@router.delete("/{product_id}/delete-image")
async def delete_product_image(product_id: str, db: Session = Depends(get_db)):
    """
    Eliminar la imagen de un producto
    
    - **product_id**: ID del producto
    """
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        
        if not product:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        
        if not product.image_path:
            raise HTTPException(status_code=404, detail="El producto no tiene imagen")
        
        # Eliminar archivo físico
        if os.path.exists(product.image_path):
            try:
                os.remove(product.image_path)
                logger.info(f"🗑️ Imagen eliminada: {product.image_path}")
            except Exception as e:
                logger.error(f"❌ Error eliminando archivo: {str(e)}")
        
        # Actualizar BD
        product.image_path = None
        db.commit()
        db.refresh(product)
        
        return {
            "success": True,
            "message": "Imagen eliminada exitosamente",
            "product_name": product.name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error eliminando imagen: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error eliminando imagen: {str(e)}")


@router.get("/{product_id}/image")
async def get_product_image(product_id: str, db: Session = Depends(get_db)):
    """
    Obtener la URL de la imagen de un producto
    
    - **product_id**: ID del producto
    """
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        
        if not product:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        
        if not product.image_path:
            return {
                "has_image": False,
                "image_url": None
            }
        
        # Extraer solo el nombre del archivo
        filename = Path(product.image_path).name
        
        return {
            "has_image": True,
            "image_url": f"/static/products/{filename}",
            "product_name": product.name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error obteniendo imagen: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo imagen: {str(e)}")

