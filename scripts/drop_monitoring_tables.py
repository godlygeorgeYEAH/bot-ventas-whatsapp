"""
Script para eliminar las tablas de monitoreo del bot

Este script elimina las tablas:
- bot_status
- communication_failures

Úsalo cuando necesites recrear las tablas con un esquema actualizado.

Uso:
    python scripts/drop_monitoring_tables.py
"""
import sys
from pathlib import Path

# Agregar el directorio raíz al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from sqlalchemy import text
from config.database import get_db
from loguru import logger


def drop_monitoring_tables():
    """Elimina las tablas de monitoreo del bot"""
    logger.info("🗑️ Eliminando tablas de monitoreo del bot...")

    try:
        # Obtener conexión a la base de datos
        db = next(get_db())

        # Eliminar tabla communication_failures primero (tiene foreign key a bot_status)
        logger.info("🗑️ Eliminando tabla 'communication_failures'...")
        db.execute(text("DROP TABLE IF EXISTS communication_failures"))
        db.commit()
        logger.info("✅ Tabla 'communication_failures' eliminada")

        # Eliminar tabla bot_status
        logger.info("🗑️ Eliminando tabla 'bot_status'...")
        db.execute(text("DROP TABLE IF EXISTS bot_status"))
        db.commit()
        logger.info("✅ Tabla 'bot_status' eliminada")

        logger.success("✅ Tablas eliminadas exitosamente")
        logger.info("")
        logger.info("📝 Próximo paso:")
        logger.info("   Ejecuta: python scripts/migrate_add_bot_monitoring.py")
        logger.info("   Para recrear las tablas con el esquema actualizado")

        return True

    except Exception as e:
        logger.error(f"❌ Error eliminando tablas: {e}")
        return False
    finally:
        db.close()


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("ELIMINAR TABLAS DE MONITOREO")
    logger.info("=" * 60)

    success = drop_monitoring_tables()

    if success:
        logger.info("=" * 60)
        logger.info("✅ Operación completada con éxito")
        logger.info("=" * 60)
    else:
        logger.error("=" * 60)
        logger.error("❌ La operación falló")
        logger.error("=" * 60)
        sys.exit(1)
