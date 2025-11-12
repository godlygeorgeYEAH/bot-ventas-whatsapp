#!/usr/bin/env python3
"""
Test para verificar que los slots se persisten correctamente
"""
import sys
from pathlib import Path

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from app.modules.base_module import Slot, SlotType
from app.core.slots.slot_manager import SlotManager
from config.logging_config import setup_logging
from loguru import logger


def test_slot_serialization():
    """Prueba serialización y deserialización de slots"""
    setup_logging()
    
    logger.info("=" * 60)
    logger.info("TEST: SERIALIZACION DE SLOTS")
    logger.info("=" * 60)
    
    # Crear slots originales
    slots = [
        Slot(name="product", type=SlotType.TEXT, description="producto"),
        Slot(name="quantity", type=SlotType.NUMBER, description="cantidad"),
        Slot(name="phone", type=SlotType.PHONE, description="telefono"),
    ]
    
    # Crear manager y llenar algunos slots
    manager1 = SlotManager(slots)
    
    # Llenar primer slot
    first = manager1.get_next_slot()
    logger.info(f"Primer slot: {first.name}")
    manager1.fill_slot(first.name, "Laptop")
    
    # Llenar segundo slot
    second = manager1.get_next_slot()
    logger.info(f"Segundo slot: {second.name}")
    manager1.fill_slot(second.name, 2)
    
    # Obtener siguiente (sin llenar)
    third = manager1.get_next_slot()
    logger.info(f"Tercer slot (no lleno): {third.name}")
    
    logger.info(f"\nEstado del Manager 1:")
    logger.info(f"  Current slot: {manager1.current_slot_name}")
    logger.info(f"  Filled slots: {manager1.get_filled_slots()}")
    
    # Serializar
    state_dict = manager1.to_dict()
    logger.info(f"\nSerializado: {state_dict}")
    
    # Deserializar
    manager2 = SlotManager.from_dict(state_dict)
    
    logger.info(f"\nEstado del Manager 2 (deserializado):")
    logger.info(f"  Current slot: {manager2.current_slot_name}")
    logger.info(f"  Filled slots: {manager2.get_filled_slots()}")
    
    # Verificar que sea el mismo estado
    assert manager1.current_slot_name == manager2.current_slot_name, "Current slot no coincide!"
    assert manager1.get_filled_slots() == manager2.get_filled_slots(), "Filled slots no coinciden!"
    
    # Verificar que el siguiente slot sea el mismo
    next1 = manager1.get_next_slot()
    next2 = manager2.get_next_slot()
    
    logger.info(f"\nSiguiente slot en Manager 1: {next1.name if next1 else None}")
    logger.info(f"Siguiente slot en Manager 2: {next2.name if next2 else None}")
    
    if next1 and next2:
        assert next1.name == next2.name, "Siguiente slot no coincide!"
    
    logger.info("\n" + "=" * 60)
    logger.info("✓ TEST EXITOSO: La serialización funciona correctamente")
    logger.info("=" * 60)


if __name__ == "__main__":
    test_slot_serialization()