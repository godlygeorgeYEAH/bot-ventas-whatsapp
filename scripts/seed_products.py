"""
Script para poblar el catálogo de productos
"""
import sys
sys.path.append('.')

from sqlalchemy.orm import Session
from config.database import SessionLocal
from app.database.models import Product
from loguru import logger


# Catálogo inicial de productos
INITIAL_PRODUCTS = [
    {
        "name": "Laptop HP 15",
        "description": "Laptop HP 15.6\", Intel Core i5-1235U, 8GB RAM, 256GB SSD",
        "price": 850.00,
        "stock": 10,
        "category": "laptops",
        "sku": "LAP-HP-001",
        "image_path": "static/products/images/LAP-HP-001.jpg"  # ← PATH LOCAL
    },
    {
        "name": "MacBook Air M2",
        "description": "Apple MacBook Air 13\" con chip M2, 8GB RAM, 256GB SSD",
        "price": 1200.00,
        "stock": 5,
        "category": "laptops",
        "sku": "LAP-MAC-001",
        "image_path": "static/products/images/LAP-MAC-001.jpg"  # ← PATH LOCAL
    },
    {
        "name": "Dell XPS 13",
        "description": "Dell XPS 13.4\" FHD, Intel Core i7, 16GB RAM, 512GB SSD",
        "price": 1500.00,
        "stock": 3,
        "category": "laptops",
        "sku": "LAP-DEL-001",
        "image_path": "static/products/images/LAP-DEL-001.jpg"  # ← PATH LOCAL
    },
    {
        "name": "Mouse Logitech MX Master 3",
        "description": "Mouse inalámbrico ergonómico con 7 botones programables",
        "price": 100.00,
        "stock": 25,
        "category": "accesorios",
        "sku": "ACC-MOU-001",
        "image_path": "static/products/images/ACC-MOU-001.jpg"  # ← PATH LOCAL
    },
    {
        "name": "Mouse Básico USB",
        "description": "Mouse óptico USB con cable, 3 botones",
        "price": 10.00,
        "stock": 50,
        "category": "accesorios",
        "sku": "ACC-MOU-002",
        "image_path": "static/products/images/ACC-MOU-002.jpg"  # ← PATH LOCAL
    },
    {
        "name": "Teclado Mecánico RGB",
        "description": "Teclado mecánico gaming con switches Blue, retroiluminación RGB",
        "price": 120.00,
        "stock": 15,
        "category": "accesorios",
        "sku": "ACC-TEC-001",
        "image_path": "static/products/images/ACC-TEC-001.jpg"  # ← PATH LOCAL
    },
    {
        "name": "Teclado Inalámbrico",
        "description": "Teclado inalámbrico compacto, batería recargable",
        "price": 45.00,
        "stock": 30,
        "category": "accesorios",
        "sku": "ACC-TEC-002",
        "image_path": "static/products/images/ACC-TEC-002.jpg"  # ← PATH LOCAL
    },
    {
        "name": "Monitor LG 24\"",
        "description": "Monitor LG 24\" Full HD IPS, 75Hz, HDMI",
        "price": 200.00,
        "stock": 12,
        "category": "monitores",
        "sku": "MON-LG-001",
        "image_path": "static/products/images/MON-LG-001.jpg"  # ← PATH LOCAL
    },
    {
        "name": "Monitor Samsung 27\" 4K",
        "description": "Monitor Samsung 27\" UHD 4K, HDR10, 60Hz",
        "price": 400.00,
        "stock": 6,
        "category": "monitores",
        "sku": "MON-SAM-001",
        "image_path": "static/products/images/MON-SAM-001.jpg"  # ← PATH LOCAL
    },
    {
        "name": "Audífonos Sony WH-1000XM5",
        "description": "Audífonos inalámbricos con cancelación de ruido activa",
        "price": 350.00,
        "stock": 8,
        "category": "audio",
        "sku": "AUD-SON-001",
        "image_path": "static/products/images/AUD-SON-001.jpg"  # ← PATH LOCAL
    },
    {
        "name": "Audífonos Gamer",
        "description": "Audífonos gaming con micrófono, sonido surround 7.1",
        "price": 80.00,
        "stock": 20,
        "category": "audio",
        "sku": "AUD-GAM-001",
        "image_path": "static/products/images/AUD-GAM-001.jpg"  # ← PATH LOCAL
    },
    {
        "name": "Webcam Logitech C920",
        "description": "Cámara web Full HD 1080p con micrófono estéreo",
        "price": 90.00,
        "stock": 18,
        "category": "accesorios",
        "sku": "ACC-CAM-001",
        "image_path": "static/products/images/ACC-CAM-001.jpg"  # ← PATH LOCAL
    }
]


def seed_products(clear_existing=False):
    """
    Puebla la base de datos con productos iniciales
    
    Args:
        clear_existing: Si True, elimina productos existentes primero
    """
    db = SessionLocal()
    
    try:
        if clear_existing:
            logger.warning("⚠️  Eliminando productos existentes...")
            db.query(Product).delete()
            db.commit()
            logger.info("✅ Productos eliminados")
        
        logger.info("🌱 Sembrando productos en la base de datos...")
        
        created_count = 0
        skipped_count = 0
        missing_images = []
        
        for product_data in INITIAL_PRODUCTS:
            # Verificar si ya existe (por SKU)
            existing = db.query(Product).filter(
                Product.sku == product_data["sku"]
            ).first()
            
            if existing:
                logger.info(f"⏭️  Producto '{product_data['name']}' ya existe, omitiendo...")
                skipped_count += 1
                continue
            
            # Verificar si la imagen existe
            import os
            if product_data.get("image_path"):
                if not os.path.exists(product_data["image_path"]):
                    logger.warning(f"⚠️  Imagen no encontrada: {product_data['image_path']}")
                    missing_images.append(product_data["sku"])
            
            # Crear producto
            product = Product(**product_data)
            db.add(product)
            created_count += 1
            logger.info(f"✅ Creado: {product.name} - ${product.price} ({product.stock} en stock)")
        
        db.commit()
        
        logger.info("=" * 60)
        logger.info(f"🎉 Seed completado:")
        logger.info(f"   - {created_count} productos creados")
        logger.info(f"   - {skipped_count} productos omitidos (ya existían)")
        if missing_images:
            logger.warning(f"   ⚠️ {len(missing_images)} productos sin imagen: {', '.join(missing_images)}")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ Error en seed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import sys
    
    # Opción para limpiar productos existentes
    clear = "--clear" in sys.argv
    
    if clear:
        confirm = input("⚠️  ¿Estás seguro de eliminar todos los productos? (yes/no): ")
        if confirm.lower() != "yes":
            logger.info("Operación cancelada")
            sys.exit(0)
    
    seed_products(clear_existing=clear)