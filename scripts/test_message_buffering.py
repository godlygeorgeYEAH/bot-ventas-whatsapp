#!/usr/bin/env python3
"""
Test para probar agrupación de mensajes
"""
import sys
import asyncio
from pathlib import Path

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from app.services.message_buffer import message_buffer_manager
from config.logging_config import setup_logging
from loguru import logger


async def mock_processing_callback(phone, combined, messages):
    """Callback simulado para testing"""
    logger.success(f"✓ CALLBACK EJECUTADO")
    logger.info(f"   Phone: {phone}")
    logger.info(f"   Combined: '{combined}'")
    logger.info(f"   Messages count: {len(messages)}")


async def test_message_buffering():
    """Prueba el sistema de buffering"""
    setup_logging()
    
    # Configurar callback
    message_buffer_manager.set_processing_callback(mock_processing_callback)
    
    test_phone = "1234567890"
    
    logger.info("=" * 70)
    logger.info("TEST: MESSAGE BUFFERING")
    logger.info("=" * 70)
    
    # Simular ráfaga de mensajes
    messages = [
        "Hola",
        "quiero",
        "hacer un pedido",
        "de una laptop"
    ]
    
    logger.info("\n📨 Enviando ráfaga de mensajes...")
    for i, msg in enumerate(messages, 1):
        logger.info(f"   Mensaje {i}: '{msg}'")
        await message_buffer_manager.add_message(
            phone=test_phone,
            message=msg,
            message_id=f"msg_{i}",
            message_type="text"
        )
        await asyncio.sleep(0.5)  # 500ms entre mensajes
    
    logger.info("\n⏳ Esperando debounce...")
    
    # Esperar a que se procese (debounce + margen)
    await asyncio.sleep(4)
    
    logger.info("\n" + "=" * 70)
    logger.info("✓ TEST COMPLETADO")
    logger.info("=" * 70)


async def test_multiple_bursts():
    """Prueba múltiples ráfagas con pausas"""
    setup_logging()
    
    message_buffer_manager.set_processing_callback(mock_processing_callback)
    
    test_phone = "9876543210"
    
    logger.info("=" * 70)
    logger.info("TEST: MÚLTIPLES RÁFAGAS")
    logger.info("=" * 70)
    
    # Primera ráfaga
    logger.info("\n📨 Primera ráfaga...")
    await message_buffer_manager.add_message(test_phone, "Hola", "m1", "text")
    await asyncio.sleep(0.3)
    await message_buffer_manager.add_message(test_phone, "quiero consultar", "m2", "text")
    
    logger.info("⏳ Esperando procesamiento de primera ráfaga...")
    await asyncio.sleep(4)
    
    # Segunda ráfaga (después de que se procesó la primera)
    logger.info("\n📨 Segunda ráfaga...")
    await message_buffer_manager.add_message(test_phone, "productos", "m3", "text")
    await asyncio.sleep(0.3)
    await message_buffer_manager.add_message(test_phone, "laptops", "m4", "text")
    
    logger.info("⏳ Esperando procesamiento de segunda ráfaga...")
    await asyncio.sleep(4)
    
    logger.info("\n" + "=" * 70)
    logger.info("✓ TEST COMPLETADO")
    logger.info("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_message_buffering())
    asyncio.run(test_multiple_bursts())
