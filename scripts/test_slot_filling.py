"""
Script para probar el sistema de slot-filling
"""
import sys
sys.path.append('.')

from app.core.slots import (
    SlotDefinition,
    SlotType,
    SlotManager
)
from loguru import logger


def test_slot_filling():
    """Prueba el sistema de slot filling"""
    
    logger.info("=" * 60)
    logger.info("🧪 Probando Sistema de Slot-Filling")
    logger.info("=" * 60)
    
    # Definir schema de slots
    slots_schema = {
        "product_name": SlotDefinition(
            name="product_name",
            type=SlotType.TEXT,
            required=True,
            prompt="¿Qué producto te interesa?",
            validation_rules={
                "min_length": 3
            },
            examples=["laptop", "mouse", "teclado"]
        ),
        "quantity": SlotDefinition(
            name="quantity",
            type=SlotType.NUMBER,
            required=True,
            prompt="¿Cuántas unidades quieres?",
            validation_rules={
                "min": 1,
                "max": 100,
                "only_integers": True
            },
            examples=["1", "2", "5"]
        ),
        "delivery_address": SlotDefinition(
            name="delivery_address",
            type=SlotType.ADDRESS,
            required=True,
            prompt="¿Cuál es tu dirección de entrega?",
            validation_rules={
                "min_length": 10
            },
            examples=["Calle 123 #45-67"]
        ),
        "payment_method": SlotDefinition(
            name="payment_method",
            type=SlotType.CHOICE,
            required=True,
            prompt="¿Cómo prefieres pagar?",
            validation_rules={
                "choices": ["efectivo", "tarjeta", "transferencia"]
            }
        )
    }
    
    # Crear manager
    manager = SlotManager(slots_schema)
    
    # Simular conversación CORRECTA
    messages = [
        "Quiero una laptop HP",      # ← Debería extraer product_name
        "2",                          # ← Cantidad
        "Calle 45 #12-34, Bogotá",  # ← Dirección
        "tarjeta"                     # ← Método de pago
    ]
    
    filled_slots = {}
    current_slot = None
    attempts = {}
    
    logger.info("\n🎬 Iniciando simulación de conversación:\n")
    
    for i, message in enumerate(messages, 1):
        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info(f"👤 Usuario [{i}]: {message}")
        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        result = manager.process_message(
            message=message,
            current_slots=filled_slots,
            current_slot_name=current_slot,
            attempts=attempts
        )
        
        # Actualizar estado
        filled_slots = result.filled_slots
        current_slot = result.current_slot
        attempts = result.attempts
        
        # Mostrar progreso
        percentage = manager.get_filled_percentage(filled_slots)
        logger.info(f"\n📊 Progreso: {percentage:.0f}%")
        logger.info(f"   Slots llenados: {list(filled_slots.keys())}")
        
        if result.next_prompt:
            logger.info(f"\n🤖 Bot: {result.next_prompt}\n")
        
        if result.completed:
            logger.info("\n" + "=" * 60)
            logger.info("✅ ¡Todos los slots completados!")
            logger.info("=" * 60)
            logger.info(f"\n📦 Datos recolectados:")
            for slot_name, value in filled_slots.items():
                logger.info(f"   - {slot_name}: {value}")
            break


if __name__ == "__main__":
    test_slot_filling()