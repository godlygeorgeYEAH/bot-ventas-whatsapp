"""
Definición de Slots
"""
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum


class SlotType(str, Enum):
    """Tipos de slots soportados"""
    TEXT = "text"           # Texto libre
    NUMBER = "number"       # Número entero o decimal
    CHOICE = "choice"       # Opción de una lista
    BOOLEAN = "boolean"     # Sí/No
    EMAIL = "email"         # Email
    PHONE = "phone"         # Teléfono
    DATE = "date"           # Fecha
    ADDRESS = "address"     # Dirección
    LOCATION = "location"   # Ubicación GPS (latitud, longitud)
    CONFIRMATION = "confirmation" 
    
@dataclass
class SlotDefinition:
    """
    Define un slot y sus reglas de validación
    """
    name: str                                    # Nombre del slot
    type: SlotType                               # Tipo de slot
    required: bool = True                        # ¿Es obligatorio?
    prompt: str = ""                             # Pregunta para solicitar el slot
    validation_rules: Dict[str, Any] = field(default_factory=dict)  # Reglas de validación
    examples: List[str] = field(default_factory=list)  # Ejemplos de valores válidos
    error_message: str = ""                      # Mensaje de error personalizado
    depends_on: Optional[str] = None             # Slot del que depende (condicional)
    max_attempts: int = 3                        # Máximo de intentos de validación
    auto_extract: bool = True                    # ¿Se puede extraer del mensaje inicial automáticamente?
    
    def __post_init__(self):
        """Validación post-inicialización"""
        if not self.prompt:
            self.prompt = f"Por favor proporciona {self.name}"
        
        if not self.error_message:
            self.error_message = f"El valor para {self.name} no es válido"