"""
Script de migración: Agregar columna delivery_reference a la tabla orders

Uso:
    python scripts/migrate_add_delivery_reference.py
"""
import sys
from pathlib import Path

# Agregar el directorio raíz al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from sqlalchemy import text
from config.database import get_db
from loguru import logger


def migrate_add_delivery_reference():
    """
    Agrega la columna delivery_reference a la tabla orders
    """
    logger.info("🔄 Iniciando migración: Agregar delivery_reference a orders")
    
    try:
        # Obtener conexión a la base de datos
        db = next(get_db())
        
        # Verificar si la columna ya existe
        result = db.execute(text("PRAGMA table_info(orders)"))
        columns = [row[1] for row in result]
        
        if 'delivery_reference' in columns:
            logger.info("✅ La columna 'delivery_reference' ya existe")
            return True
        
        # Agregar la columna
        logger.info("➕ Agregando columna 'delivery_reference'...")
        db.execute(text(
            "ALTER TABLE orders ADD COLUMN delivery_reference VARCHAR(200)"
        ))
        db.commit()
        
        logger.info("✅ Migración completada exitosamente")
        logger.info("   Columna 'delivery_reference' agregada a tabla 'orders'")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error durante la migración: {e}")
        return False
    finally:
        db.close()


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("MIGRACIÓN DE BASE DE DATOS")
    logger.info("=" * 60)
    
    success = migrate_add_delivery_reference()
    
    if success:
        logger.info("=" * 60)
        logger.info("✅ Migración completada con éxito")
        logger.info("=" * 60)
    else:
        logger.error("=" * 60)
        logger.error("❌ La migración falló")
        logger.error("=" * 60)
        sys.exit(1)

