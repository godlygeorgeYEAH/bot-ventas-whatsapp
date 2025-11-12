#!/usr/bin/env python3
"""
Script para inicializar la base de datos desde cero

Este script:
1. Crea todas las tablas basándose en los modelos de SQLAlchemy
2. Incluye automáticamente todas las columnas definidas en los modelos
3. NO ejecuta migraciones - solo crea tablas nuevas

Para bases de datos existentes, usa los scripts de migración en su lugar:
- scripts/migrate_add_delivery_reference.py
- scripts/migrate_add_abandoned_fields.py
"""
import sys
from pathlib import Path

# Agregar el directorio raíz al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from config.database import init_db, engine
from config.logging_config import setup_logging
from loguru import logger

def main():
    """Inicializa la base de datos"""
    setup_logging()
    
    logger.info("🔨 Inicializando base de datos...")
    
    try:
        init_db()
        logger.success("✓ Base de datos creada exitosamente")
        logger.info(f"📍 Ubicación: {engine.url}")
        
        # Verificar tablas creadas
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        logger.info(f"📊 Tablas creadas: {', '.join(tables)}")
        
        # Verificar columnas importantes de la tabla orders
        if 'orders' in tables:
            columns = [col['name'] for col in inspector.get_columns('orders')]
            logger.info(f"📋 Tabla 'orders' tiene {len(columns)} columnas")
            
            # Verificar columnas clave agregadas en migraciones
            key_columns = ['abandoned_at', 'abandonment_reason', 'delivery_reference', 'confirmed_at']
            for col in key_columns:
                if col in columns:
                    logger.info(f"   ✅ Columna '{col}' presente")
                else:
                    logger.warning(f"   ⚠️ Columna '{col}' faltante (puede necesitar migración)")
        
    except Exception as e:
        logger.error(f"❌ Error inicializando base de datos: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()