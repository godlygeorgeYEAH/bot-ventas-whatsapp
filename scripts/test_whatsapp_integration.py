"""
Script para probar integración completa con WhatsApp simulado
"""
import sys
sys.path.append('.')

from app.services.sync_worker import SyncMessageWorker, sync_worker  # ← Nombre correcto
from app.core.module_registry import get_module_registry
from app.modules.create_order_module import CreateOrderModule
from loguru import logger
import time


def test_whatsapp_integration():
    """Prueba la integración completa simulando mensajes de WhatsApp"""
    
    logger.info("=" * 60)
    logger.info("🧪 Probando Integración con WhatsApp")
    logger.info("=" * 60)
    
    # 1. Inicializar módulos
    logger.info("\n1️⃣ Inicializando módulos...")
    registry = get_module_registry()
    create_order_module = CreateOrderModule()
    registry.register(create_order_module)
    
    # 2. Iniciar worker (usar instancia global o crear nueva)
    logger.info("\n2️⃣ Iniciando worker...")
    worker = sync_worker  # Usar instancia global
    worker.start()
    
    # 3. Simular conversación de WhatsApp
    phone = "573001234567"
    
    messages = [
        "Hola! Quiero comprar una laptop",
        "2",
        "Calle 123 #45-67, Bogotá",
        "tarjeta"
    ]
    
    logger.info(f"\n3️⃣ Simulando conversación de WhatsApp desde {phone}:\n")
    
    for i, message in enumerate(messages, 1):
        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info(f"👤 Usuario WhatsApp [{i}]: {message}")
        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        # Encolar mensaje (como si viniera de WhatsApp)
        worker.enqueue_message(phone, message, f"msg_{i}")  # ← Método correcto
        
        # Esperar un poco para que se procese
        time.sleep(15)
        
        logger.info("")
    
    # Esperar a que se procesen todos los mensajes
    logger.info("\n⏳ Esperando a que se procesen todos los mensajes...")
    time.sleep(60)
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ Test de integración completado")
    logger.info("=" * 60)
    logger.info("\n💡 Nota: El worker sigue corriendo. Presiona Ctrl+C para terminar.")


if __name__ == "__main__":
    try:
        test_whatsapp_integration()
        
        # Mantener el script corriendo para que el worker termine
        logger.info("\n⏳ Esperando procesos en segundo plano...")
        time.sleep(15)
        
    except KeyboardInterrupt:
        logger.info("\n\n👋 Test interrumpido por usuario")
    except Exception as e:
        logger.error(f"\n\n❌ Error en test: {e}", exc_info=True)