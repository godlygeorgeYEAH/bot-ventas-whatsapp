"""
Script para crear TODAS las tablas de la base de datos
"""
import sys
sys.path.append('.')

from config.database import engine, Base
from app.database.models import Customer, Conversation, Message, Product, ProductCategory
from loguru import logger


def create_all_tables():
    """Crea todas las tablas en la BD"""
    try:
        logger.info("🔨 Creando todas las tablas...")
        
        # Crear todas las tablas definidas en Base
        Base.metadata.create_all(engine)
        
        logger.info("✅ Tablas creadas exitosamente:")
        logger.info(f"   - {Customer.__tablename__}")
        logger.info(f"   - {Conversation.__tablename__}")
        logger.info(f"   - {Message.__tablename__}")
        logger.info(f"   - {Product.__tablename__}")
        logger.info(f"   - {ProductCategory.__tablename__}")
        
    except Exception as e:
        logger.error(f"❌ Error creando tablas: {e}")
        raise


if __name__ == "__main__":
    create_all_tables()