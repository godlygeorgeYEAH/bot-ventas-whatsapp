"""
Registro de Módulos - Gestiona todos los módulos disponibles
"""
from typing import Dict, Optional, Any
from loguru import logger


class ModuleRegistry:
    """Registro centralizado de módulos del bot"""
    
    def __init__(self):
        self.modules = {}
        logger.info("📋 [ModuleRegistry] Inicializado")
    
    def register(self, module):
        """
        Registra un módulo
        
        Args:
            module: Instancia del módulo a registrar
        """
        if not hasattr(module, 'name') or not hasattr(module, 'intent'):
            raise ValueError("Módulo debe tener atributos 'name' e 'intent'")
        
        self.modules[module.intent] = module
        logger.info(f"✅ [ModuleRegistry] Módulo registrado: {module.name} (intent: {module.intent})")
    
    def get_module(self, intent: str):
        """
        Obtiene un módulo por su intención
        
        Args:
            intent: Intención a buscar
            
        Returns:
            Módulo correspondiente o None
        """
        module = self.modules.get(intent)
        
        if module:
            logger.info(f"✅ [ModuleRegistry] Módulo encontrado para intent '{intent}': {module.name}")
        else:
            logger.warning(f"⚠️ [ModuleRegistry] No hay módulo para intent '{intent}'")
        
        return module
    
    def get_module_by_context(self, context: Dict[str, Any]):
        """
        Obtiene un módulo basado en el contexto actual
        
        Args:
            context: Contexto de la conversación
            
        Returns:
            Módulo correspondiente o None
        """
        # Si hay un módulo activo en el contexto
        current_module_name = context.get('current_module')
        if current_module_name:
            # Buscar por nombre exacto
            for module in self.modules.values():
                if module.name == current_module_name:
                    logger.info(f"✅ [ModuleRegistry] Módulo activo (por name): {module.name}")
                    return module
            
            # Fallback: buscar por intent (backwards compatibility)
            # Esto permite que "create_order" encuentre CreateOrderModule
            for module in self.modules.values():
                if module.intent == current_module_name:
                    logger.info(f"✅ [ModuleRegistry] Módulo activo (por intent): {module.name} (intent={module.intent})")
                    return module
        
        return None
    
    def find_module_for_intent(self, intent: str, context: Dict[str, Any]):
        """
        Encuentra el módulo apropiado para una intención y contexto
        
        Args:
            intent: Intención detectada
            context: Contexto actual
            
        Returns:
            Módulo correspondiente o None
        """
        # Primero verificar si hay un módulo activo que pueda manejar
        active_module = self.get_module_by_context(context)
        if active_module and hasattr(active_module, 'can_handle'):
            if active_module.can_handle(intent, context):
                return active_module
        
        # Si no, buscar módulo por intención
        return self.get_module(intent)
    
    def list_modules(self):
        """Lista todos los módulos registrados"""
        logger.info(f"📋 [ModuleRegistry] Módulos registrados: {len(self.modules)}")
        for intent, module in self.modules.items():
            logger.info(f"   - {module.name} → {intent}")
        
        return list(self.modules.values())


# Instancia global del registro
_registry = None

def get_module_registry() -> ModuleRegistry:
    """Obtiene la instancia global del registro de módulos"""
    global _registry
    if _registry is None:
        _registry = ModuleRegistry()
    return _registry