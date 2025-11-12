#!/usr/bin/env python3
"""
Script para probar conversaciones completas
"""
import sys
import asyncio
from pathlib import Path

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from app.services.message_processor import MessageProcessor
from config.logging_config import setup_logging
from loguru import logger


async def test_conversation():
    """Prueba una conversación completa"""
    setup_logging()
    
    processor = MessageProcessor()
    test_phone = "1234567890"
    
    logger.info("🧪 Iniciando prueba de conversación")
    logger.info("=" * 50)
    
    # Secuencia de mensajes de prueba
    test_messages = [
        "Hola",
        "Quiero hacer un pedido",
        "Una laptop",
        "Necesito 2",
        "¿Cuánto cuesta?",
        "Gracias, adiós"
    ]
    
    for i, message in enumerate(test_messages, 1):
        logger.info(f"\n--- Mensaje {i} ---")
        logger.info(f"Usuario: {message}")
        
        # Procesar mensaje
        await processor.process_text_message(
            phone=test_phone,
            message=message
        )
        
        # Pequeña pausa entre mensajes
        await asyncio.sleep(1)
    
    logger.info("\n" + "=" * 50)
    logger.info("✓ Prueba de conversación completada")


if __name__ == "__main__":
    asyncio.run(test_conversation())