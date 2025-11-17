"""
Script de migración: Agregar tablas para monitoreo del bot

Crea las tablas:
- bot_status: Para rastrear el estado de comunicación del bot con WAHA
- communication_failures: Para registrar fallos de comunicación

Uso:
    python scripts/migrate_add_bot_monitoring.py
"""
import sys
from pathlib import Path

# Agregar el directorio raíz al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from sqlalchemy import text
from config.database import get_db
from loguru import logger


def table_exists(db, table_name: str) -> bool:
    """Verifica si una tabla existe en la base de datos"""
    result = db.execute(text(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=:table_name"
    ), {"table_name": table_name})
    return result.first() is not None


def create_bot_status_table(db):
    """Crea la tabla bot_status"""
    logger.info("📊 Creando tabla 'bot_status'...")

    create_table_sql = """
    CREATE TABLE bot_status (
        id TEXT PRIMARY KEY,
        status TEXT NOT NULL DEFAULT 'online',
        reason TEXT,
        last_update DATETIME NOT NULL,
        waha_last_success DATETIME,
        waha_consecutive_failures INTEGER DEFAULT 0,
        extra_data TEXT DEFAULT '{}',
        created_at DATETIME NOT NULL,
        updated_at DATETIME NOT NULL
    )
    """

    db.execute(text(create_table_sql))
    db.commit()
    logger.info("✅ Tabla 'bot_status' creada")


def create_communication_failures_table(db):
    """Crea la tabla communication_failures"""
    logger.info("📊 Creando tabla 'communication_failures'...")

    create_table_sql = """
    CREATE TABLE communication_failures (
        id TEXT PRIMARY KEY,
        failure_type TEXT NOT NULL,
        order_id TEXT,
        customer_phone TEXT,
        diagnostic_user_reached INTEGER DEFAULT 0,
        diagnostic_admin_reached INTEGER DEFAULT 0,
        resolved_at DATETIME,
        resolution_method TEXT,
        created_at DATETIME NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(id)
    )
    """

    db.execute(text(create_table_sql))

    # Crear índice para búsquedas más rápidas
    db.execute(text(
        "CREATE INDEX idx_communication_failures_order_id ON communication_failures(order_id)"
    ))
    db.execute(text(
        "CREATE INDEX idx_communication_failures_created_at ON communication_failures(created_at)"
    ))

    db.commit()
    logger.info("✅ Tabla 'communication_failures' creada con índices")


def initialize_bot_status(db):
    """Inicializa el registro de bot_status con estado online"""
    logger.info("🔧 Inicializando estado del bot...")

    # Importar uuid para generar ID
    import uuid
    from datetime import datetime

    insert_sql = """
    INSERT INTO bot_status (
        id, status, reason, last_update, waha_last_success,
        waha_consecutive_failures, extra_data, created_at, updated_at
    ) VALUES (
        :id, 'online', 'Sistema iniciado', :now, :now,
        0, '{}', :now, :now
    )
    """

    db.execute(text(insert_sql), {
        "id": str(uuid.uuid4()),
        "now": datetime.utcnow()
    })
    db.commit()
    logger.info("✅ Estado inicial del bot configurado como 'online'")


def migrate_add_bot_monitoring():
    """
    Crea las tablas para monitoreo del bot
    """
    logger.info("🔄 Iniciando migración: Agregar sistema de monitoreo del bot")

    try:
        # Obtener conexión a la base de datos
        db = next(get_db())

        # Verificar y crear tabla bot_status
        if table_exists(db, 'bot_status'):
            logger.info("✅ La tabla 'bot_status' ya existe")
        else:
            create_bot_status_table(db)
            initialize_bot_status(db)

        # Verificar y crear tabla communication_failures
        if table_exists(db, 'communication_failures'):
            logger.info("✅ La tabla 'communication_failures' ya existe")
        else:
            create_communication_failures_table(db)

        logger.info("✅ Migración completada exitosamente")
        logger.info("   Tablas creadas:")
        logger.info("   - bot_status: Estado de comunicación del bot")
        logger.info("   - communication_failures: Registro de fallos de comunicación")

        return True

    except Exception as e:
        logger.error(f"❌ Error durante la migración: {e}", exc_info=True)
        return False
    finally:
        db.close()


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("MIGRACIÓN DE BASE DE DATOS")
    logger.info("Sistema de Monitoreo de Comunicación del Bot")
    logger.info("=" * 60)

    success = migrate_add_bot_monitoring()

    if success:
        logger.info("=" * 60)
        logger.info("✅ Migración completada con éxito")
        logger.info("")
        logger.info("📊 Sistema de monitoreo activado:")
        logger.info("   - Detección de pérdida de comunicación")
        logger.info("   - Diagnóstico automático de fallos")
        logger.info("   - Rastreo de estado del bot")
        logger.info("=" * 60)
    else:
        logger.error("=" * 60)
        logger.error("❌ La migración falló")
        logger.error("=" * 60)
        sys.exit(1)
