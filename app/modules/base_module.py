from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger


class SlotType(Enum):
    """Tipos de datos que puede contener un slot"""
    TEXT = "text"
    NUMBER = "number"
    PHONE = "phone"
    EMAIL = "email"
    DATE = "date"
    TIME = "time"
    CHOICE = "choice"
    CURRENCY = "currency"
    BOOLEAN = "boolean"


@dataclass
class Slot:
    """Define un dato que el módulo necesita recolectar"""
    name: str
    type: SlotType
    description: str
    required: bool = True
    question_template: str = ""
    
    # Validación
    validation_rules: Optional[Dict[str, Any]] = None
    choices: Optional[List[str]] = None
    
    # Dependencias
    depends_on: Optional[str] = None
    skip_if: Optional[Dict[str, Any]] = None
    
    # Valor actual
    value: Any = None
    filled: bool = False
    attempts: int = 0
    
    def __post_init__(self):
        """Inicialización después de crear el objeto"""
        if not self.question_template:
            self.question_template = f"Por favor, proporciona {self.description}"
        
        if self.validation_rules is None:
            self.validation_rules = {}
        
        if self.type == SlotType.CHOICE and not self.choices:
            logger.warning(f"Slot {self.name} es tipo CHOICE pero no tiene opciones definidas")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte el slot a diccionario"""
        return {
            "name": self.name,
            "type": self.type.value,
            "description": self.description,
            "required": self.required,
            "question_template": self.question_template,
            "validation_rules": self.validation_rules,
            "choices": self.choices,
            "depends_on": self.depends_on,
            "skip_if": self.skip_if,
            "value": self.value,
            "filled": self.filled,
            "attempts": self.attempts
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Slot':
        """Crea un slot desde un diccionario"""
        slot_type = SlotType(data.get("type", "text"))
        
        slot = cls(
            name=data["name"],
            type=slot_type,
            description=data["description"],
            required=data.get("required", True),
            question_template=data.get("question_template", ""),
            validation_rules=data.get("validation_rules"),
            choices=data.get("choices"),
            depends_on=data.get("depends_on"),
            skip_if=data.get("skip_if")
        )
        
        # IMPORTANTE: Restaurar el estado del slot
        slot.value = data.get("value")
        slot.filled = data.get("filled", False)
        slot.attempts = data.get("attempts", 0)
        
        return slot


class BaseModule(ABC):
    """Clase base para todos los módulos de acción"""
    
    def __init__(self):
        self.name = self.__class__.__name__
        self.description = "Módulo base"
    
    @abstractmethod
    def get_required_slots(self) -> List[Slot]:
        """
        Define qué slots (datos) necesita el módulo
        
        Returns:
            Lista de objetos Slot que definen los datos requeridos
        """
        pass
    
    @abstractmethod
    async def execute(self, slots_data: Dict[str, Any], context: Dict) -> Dict:
        """
        Ejecuta la acción del módulo con los datos completos
        
        Args:
            slots_data: Diccionario con todos los slots llenos
            context: Contexto de la conversación
            
        Returns:
            Dict con el resultado de la ejecución:
            {
                "success": bool,
                "message": str,  # Mensaje para el usuario
                "data": dict,    # Datos adicionales
                "next_action": str  # Próxima acción opcional
            }
        """
        pass
    
    def get_slot_schema(self) -> Dict:
        """
        Retorna el schema de slots en formato JSON
        
        Returns:
            Dict con la estructura de slots del módulo
        """
        slots = self.get_required_slots()
        return {
            "module": self.name,
            "description": self.description,
            "slots": [slot.to_dict() for slot in slots]
        }
    
    def get_module_info(self) -> Dict:
        """Información del módulo"""
        return {
            "name": self.name,
            "description": self.description,
            "slots_count": len(self.get_required_slots())
        }