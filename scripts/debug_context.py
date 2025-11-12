#!/usr/bin/env python3
"""
Script para debuggear el contexto de una conversación
"""
import sys
from pathlib import Path

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from config.database import get_db_context
from app.core.context_manager import ContextManager
from config.logging_config import setup_logging
from loguru import logger


def debug_context():
    """Muestra el contexto completo de una conversación"""
    setup_logging()
    
    phone = input("Ingresa el telefono a debuggear: ")
    
    with get_db_context() as db:
        context_manager = ContextManager(db)
        context = context_manager.get_or_create_context(phone)
        
        logger.info("=" * 60)
        logger.info("CONTEXTO COMPLETO")
        logger.info("=" * 60)
        
        for key, value in context.items():
            if key == "message_history":
                logger.info(f"{key}: {len(value)} mensajes")
            else:
                logger.info(f"{key}: {value}")
        
        logger.info("=" * 60)
        
        if context.get("slots_schema"):
            logger.info("\nSLOTS SCHEMA:")
            logger.info(context["slots_schema"])
        
        if context.get("slots_data"):
            logger.info("\nSLOTS DATA:")
            logger.info(context["slots_data"])


if __name__ == "__main__":
    debug_context()