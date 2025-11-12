"""
Script para probar CreateOrderModule completo
"""
import sys
sys.path.append('.')

from app.modules.create_order_module import CreateOrderModule
from loguru import logger


def test_create_order_module():
    """Prueba el módulo completo de creación de órdenes"""
    
    logger.info("=" * 60)
    logger.info("🧪 Probando CreateOrderModule")
    logger.info("=" * 60)
    
    module = CreateOrderModule()
    
    # Simular conversación completa
    messages = [
        "Quiero comprar una laptop",
        "2",
        "Calle 123 #45-67, Bogotá",
        "tarjeta"
    ]
    
    context = {}
    phone = "573001234567"
    
    logger.info("\n🎬 Simulando conversación completa:\n")
    
    for i, message in enumerate(messages, 1):
        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info(f"👤 Usuario [{i}]: {message}")
        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        result = module.handle(
            message=message,
            context=context,
            phone=phone
        )
        
        # Actualizar contexto
        context.update(result["context_updates"])
        
        # Mostrar respuesta
        logger.info(f"\n🤖 Bot:\n{result['response']}\n")
        
        # Si completó, terminar
        if context.get("conversation_state") in ["completed", "failed"]:
            break
    
    logger.info("=" * 60)
    logger.info("✅ Test completado")
    logger.info("=" * 60)


if __name__ == "__main__":
    test_create_order_module()