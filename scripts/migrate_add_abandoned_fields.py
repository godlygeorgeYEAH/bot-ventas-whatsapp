"""
Migración: Agregar campos abandoned_at y abandonment_reason a la tabla orders
"""
import sys
from pathlib import Path

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from config.database import engine
from sqlalchemy import text
from loguru import logger


def migrate():
    """Agrega columnas para órdenes abandonadas"""
    
    with engine.connect() as conn:
        try:
            # Verificar si las columnas ya existen
            result = conn.execute(text("PRAGMA table_info(orders)"))
            columns = [row[1] for row in result]
            
            migrations_applied = 0
            
            # Agregar abandoned_at si no existe
            if 'abandoned_at' not in columns:
                logger.info("📝 Agregando columna 'abandoned_at' a tabla orders...")
                conn.execute(text("ALTER TABLE orders ADD COLUMN abandoned_at DATETIME"))
                conn.commit()
                logger.info("✅ Columna 'abandoned_at' agregada")
                migrations_applied += 1
            else:
                logger.info("⏭️  Columna 'abandoned_at' ya existe")
            
            # Agregar abandonment_reason si no existe
            if 'abandonment_reason' not in columns:
                logger.info("📝 Agregando columna 'abandonment_reason' a tabla orders...")
                conn.execute(text("ALTER TABLE orders ADD COLUMN abandonment_reason TEXT"))
                conn.commit()
                logger.info("✅ Columna 'abandonment_reason' agregada")
                migrations_applied += 1
            else:
                logger.info("⏭️  Columna 'abandonment_reason' ya existe")
            
            if migrations_applied > 0:
                logger.success(f"🎉 Migración completada: {migrations_applied} columna(s) agregada(s)")
            else:
                logger.info("✅ La base de datos ya está actualizada")
            
        except Exception as e:
            logger.error(f"❌ Error en migración: {e}")
            conn.rollback()
            raise


if __name__ == "__main__":
    logger.info("🔨 Iniciando migración: Agregar campos de abandono...")
    migrate()
    logger.info("✅ Migración finalizada")

