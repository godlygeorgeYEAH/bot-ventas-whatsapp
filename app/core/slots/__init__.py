"""
Sistema de Slot-Filling
"""
from .slot_definition import SlotDefinition, SlotType
from .slot_extractor import SlotExtractor
from .slot_validator import SlotValidator
from .slot_manager import SlotManager, SlotFillingResult

__all__ = [
    "SlotDefinition",
    "SlotType",
    "SlotExtractor",
    "SlotValidator",
    "SlotManager",
    "SlotFillingResult"
]