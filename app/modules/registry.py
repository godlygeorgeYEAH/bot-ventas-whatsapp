from typing import Dict, Optional, Type
from app.modules.base_module import BaseModule
from app.modules.order_module import CreateOrderModule
from app.modules.product_inquiry_module import (
    ProductInquiryModule, 
    GreetingModule
)
from app.modules.check_order_module import (
    CheckOrderModule,
    HelpModule,
    CancelModule
)
from loguru import logger


class ModuleRegistry:
    """Registro central de todos los módulos disponibles"""
    
    def __init__(self):
        self._modules: Dict[str, Type[BaseModule]] = {}
        self._register_default_modules()
    
    def _register_default_modules(self):
        """Registra los módulos por defecto del sistema"""
        self.register("create_order", CreateOrderModule)
        self.register("product_inquiry", ProductInquiryModule)
        self.register("greeting", GreetingModule)
        self.register("check_order", CheckOrderModule)
        self.register("help", HelpModule)
        self.register("goodbye", CancelModule)  # Reutilizar para despedidas
        
        logger.info(f"Modulos registrados: {list(self._modules.keys())}")
    
    def register(self, intent: str, module_class: Type[BaseModule]):
        """Registra un módulo para una intención"""
        self._modules[intent] = module_class
        logger.debug(f"Modulo '{module_class.__name__}' registrado para intent '{intent}'")
    
    def get_module(self, intent: str) -> Optional[BaseModule]:
        """Obtiene una instancia del módulo para una intención"""
        module_class = self._modules.get(intent)
        if module_class:
            return module_class()
        return None
    
    def get_all_intents(self) -> list:
        """Retorna lista de todas las intenciones registradas"""
        return list(self._modules.keys())
    
    def module_exists(self, intent: str) -> bool:
        """Verifica si existe un módulo para una intención"""
        return intent in self._modules


# Instancia global del registro
module_registry = ModuleRegistry()