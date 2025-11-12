#!/usr/bin/env python3
"""
Script para probar detección de intenciones
"""
import sys
import asyncio
from pathlib import Path

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from app.clients.ollama_client import OllamaClient
from app.core.intent_detector import IntentDetector
from config.logging_config import setup_logging
from loguru import logger


async def test_intent_detection():
    """Prueba la detección de intenciones"""
    setup_logging()
    
    ollama = OllamaClient()
    detector = IntentDetector(ollama)
    
    # Mensajes de prueba
    test_messages = [
        "Hola, buenos días",
        "Quiero comprar una laptop",
        "Cuánto cuesta el iPhone?",
        "Dónde está mi pedido #123",
        "Ayuda por favor",
        "Gracias, hasta luego",
        "Me gustaría información sobre sus productos",
    ]
    
    logger.info("🧪 Probando detección de intenciones")
    logger.info("=" * 60)
    
    context = {"message_history": []}
    
    for message in test_messages:
        logger.info(f"\n📨 Mensaje: '{message}'")
        
        result = await detector.detect_intent(message, context)
        
        logger.info(f"🎯 Intención: {result['intent']}")
        logger.info(f"📊 Confianza: {result['confidence']:.2f}")
        if result['entities']:
            logger.info(f"📦 Entidades: {result['entities']}")
        
        logger.info("-" * 60)
    
    logger.info("\n✓ Prueba completada")


if __name__ == "__main__":
    asyncio.run(test_intent_detection())