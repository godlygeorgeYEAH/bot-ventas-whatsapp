"""
Migración: Agregar campo notification_sent_at a tabla orders

Este campo permite rastrear cuándo se notificó al usuario sobre
la confirmación de su orden, evitando notificaciones duplicadas.
"""
import sys
from pathlib import Path

# Agregar directorio raíz al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from loguru import logger
from sqlalchemy import text
from config.database import engine, SessionLocal


def migrate_add_notification_sent_at():
    """Agrega columna notification_sent_at a tabla orders"""

    logger.info("🔄 Iniciando migración: agregar notification_sent_at a orders")

    db = SessionLocal()

    try:
        # Verificar si la columna ya existe
        result = db.execute(text("PRAGMA table_info(orders)"))
        columns = [row[1] for row in result.fetchall()]

        if "notification_sent_at" in columns:
            logger.info("✅ La columna notification_sent_at ya existe")
            return

        # Agregar columna
        logger.info("➕ Agregando columna notification_sent_at...")
        db.execute(text("ALTER TABLE orders ADD COLUMN notification_sent_at DATETIME"))
        db.commit()

        logger.info("✅ Columna notification_sent_at agregada exitosamente")

        # Verificar que se agregó
        result = db.execute(text("PRAGMA table_info(orders)"))
        columns = [row[1] for row in result.fetchall()]

        if "notification_sent_at" in columns:
            logger.info("✅ Verificación exitosa: columna existe en la tabla")
        else:
            logger.error("❌ Error: columna no aparece después de agregarla")

    except Exception as e:
        logger.error(f"❌ Error en migración: {e}")
        db.rollback()
        raise
    finally:
        db.close()

    logger.info("🎉 Migración completada")


if __name__ == "__main__":
    migrate_add_notification_sent_at()
