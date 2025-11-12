#!/usr/bin/env python3
"""
Script para probar el flujo completo incluyendo confirmación
"""
import sys
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from app.services.message_processor import MessageProcessor
from config.logging_config import setup_logging
from loguru import logger


async def test_order_with_confirmation():
    """Prueba creación de orden con confirmación"""
    setup_logging()
    
    processor = MessageProcessor()
    
    # Mockear WAHA
    processor.waha.send_text_message = AsyncMock(return_value={"success": True})
    processor.waha.mark_as_read = AsyncMock(return_value=True)
    processor.waha.send_typing = AsyncMock(return_value=True)
    
    test_phone = "1111111111"
    
    logger.info("=" * 70)
    logger.info("TEST: ORDEN CON CONFIRMACION")
    logger.info("=" * 70)
    
    conversation = [
        ("Usuario", "Quiero hacer un pedido"),
        ("Usuario", "Laptop Dell"),
        ("Usuario", "3"),
        ("Usuario", "Domicilio"),
        ("Usuario", "Av Principal 456, Bogota"),
        ("Usuario", "3001234567"),
        ("Usuario", "SI"),  # Confirmación
    ]
    
    for i, (speaker, message) in enumerate(conversation, 1):
        logger.info(f"\n{'='*70}")
        logger.info(f"Turno {i}: {speaker} dice: '{message}'")
        logger.info(f"{'='*70}")
        
        await processor.process_text_message(
            phone=test_phone,
            message=message
        )
        
        await asyncio.sleep(0.5)
    
    logger.info("\n" + "=" * 70)
    logger.info("TEST COMPLETADO")
    logger.info("=" * 70)


async def test_order_with_correction():
    """Prueba corrección de datos"""
    setup_logging()
    
    processor = MessageProcessor()
    
    # Mockear WAHA
    processor.waha.send_text_message = AsyncMock(return_value={"success": True})
    processor.waha.mark_as_read = AsyncMock(return_value=True)
    processor.waha.send_typing = AsyncMock(return_value=True)
    
    test_phone = "2222222222"
    
    logger.info("=" * 70)
    logger.info("TEST: CORRECCION DE DATOS")
    logger.info("=" * 70)
    
    conversation = [
        ("Usuario", "Quiero comprar algo"),
        ("Usuario", "Tablet"),
        ("Usuario", "1"),
        ("Usuario", "Domicilio"),
        ("Usuario", "Calle 123"),
        ("Usuario", "555-9999"),
        ("Usuario", "No, quiero corregir la cantidad"),  # Corrección
        ("Usuario", "2"),  # Nueva cantidad
        ("Usuario", "SI"),  # Confirmar
    ]
    
    for i, (speaker, message) in enumerate(conversation, 1):
        logger.info(f"\n{'='*70}")
        logger.info(f"Turno {i}: {speaker} dice: '{message}'")
        logger.info(f"{'='*70}")
        
        await processor.process_text_message(
            phone=test_phone,
            message=message
        )
        
        await asyncio.sleep(0.5)
    
    logger.info("\n" + "=" * 70)
    logger.info("TEST COMPLETADO")
    logger.info("=" * 70)


async def test_check_order():
    """Prueba consulta de orden"""
    setup_logging()
    
    processor = MessageProcessor()
    
    # Mockear WAHA
    processor.waha.send_text_message = AsyncMock(return_value={"success": True})
    processor.waha.mark_as_read = AsyncMock(return_value=True)
    processor.waha.send_typing = AsyncMock(return_value=True)
    
    test_phone = "3333333333"
    
    logger.info("=" * 70)
    logger.info("TEST: CONSULTA DE ORDEN")
    logger.info("=" * 70)
    
    conversation = [
        ("Usuario", "Donde esta mi pedido"),
        ("Usuario", "#123456"),
    ]
    
    for i, (speaker, message) in enumerate(conversation, 1):
        logger.info(f"\n{'='*70}")
        logger.info(f"Turno {i}: {speaker} dice: '{message}'")
        logger.info(f"{'='*70}")
        
        await processor.process_text_message(
            phone=test_phone,
            message=message
        )
        
        await asyncio.sleep(0.5)
    
    logger.info("\n" + "=" * 70)
    logger.info("TEST COMPLETADO")
    logger.info("=" * 70)


async def main():
    """Ejecuta todos los tests"""
    await test_order_with_confirmation()
    await asyncio.sleep(2)
    
    await test_order_with_correction()
    await asyncio.sleep(2)
    
    await test_check_order()


if __name__ == "__main__":
    asyncio.run(main())