"""
Gestor de Slots - Coordina el proceso de llenado
"""
from typing import Dict, Optional, Any, List
from loguru import logger
from .slot_definition import SlotDefinition
from .slot_extractor import SlotExtractor
from .slot_validator import SlotValidator


class SlotFillingResult:
    """Resultado del proceso de slot filling"""
    
    def __init__(self):
        self.completed = False           # ¿Todos los slots llenados?
        self.current_slot = None         # Slot actual que se está pidiendo
        self.next_prompt = None          # Siguiente pregunta
        self.filled_slots = {}           # Slots llenados con éxito
        self.validation_errors = {}      # Errores de validación
        self.attempts = {}               # Intentos por slot
        self.context = {}                # Contexto adicional (ej: sugerencias)


class SlotManager:
    """Gestiona el proceso de llenado de slots"""
    
    def __init__(self, slots_schema: Dict[str, SlotDefinition]):
        """
        Args:
            slots_schema: Diccionario de slots a llenar {nombre: SlotDefinition}
        """
        self.slots_schema = slots_schema
        self.extractor = SlotExtractor()
        self.validator = SlotValidator()
    
    def process_message(
        self,
        message: str,
        current_slots: Dict[str, Any],
        current_slot_name: Optional[str],
        attempts: Dict[str, int],
        context: Dict[str, Any] = None
    ) -> SlotFillingResult:
        """
        Procesa un mensaje del usuario en el contexto del slot filling
        
        Args:
            message: Mensaje del usuario
            current_slots: Slots ya llenados {nombre: valor}
            current_slot_name: Nombre del slot que se está pidiendo actualmente
            attempts: Intentos de validación por slot {nombre: count}
            context: Contexto adicional (ej: sugerencias de productos)
            
        Returns:
            SlotFillingResult con el resultado del procesamiento
        """
        # ⚠️ Validación robusta: Forzar que current_slots y attempts sean diccionarios
        logger.debug(f"🐛 [SlotManager] Recibido: current_slots type={type(current_slots).__name__}, attempts type={type(attempts).__name__}")
        
        if not isinstance(current_slots, dict):
            logger.warning(f"⚠️ [SlotManager] current_slots no era dict (era {type(current_slots)}), corrigiendo")
            current_slots = {}
        
        if not isinstance(attempts, dict):
            logger.warning(f"⚠️ [SlotManager] attempts no era dict (era {type(attempts)}), corrigiendo")
            attempts = {}
        
        logger.debug(f"🐛 [SlotManager] DESPUÉS de validar: current_slots type={type(current_slots).__name__}, attempts type={type(attempts).__name__}")
        
        result = SlotFillingResult()
        logger.debug(f"🐛 [SlotManager] Haciendo .copy() de current_slots...")
        result.filled_slots = current_slots.copy()
        logger.debug(f"🐛 [SlotManager] result.filled_slots type={type(result.filled_slots).__name__}")
        result.attempts = attempts.copy()
        result.context = (context or {}).copy()  # Inicializar contexto
        
        logger.info(f"🔄 [SlotManager] Procesando mensaje para slot: {current_slot_name}")
        logger.info(f"   Slots llenados: {list(current_slots.keys())}")
        
        # ═══════════════════════════════════════════════════════════
        # CASO 1: Si NO hay slot actual (mensaje inicial)
        # Intentar extraer TODOS los slots posibles del mensaje
        # ═══════════════════════════════════════════════════════════
        if current_slot_name is None:
            logger.info("🔍 [SlotManager] Analizando mensaje inicial, buscando todos los slots...")
            
            # Intentar extraer cada slot del mensaje
            for slot_name, slot_def in self.slots_schema.items():
                if slot_name in result.filled_slots:
                    continue  # Ya está llenado
                
                # Verificar si es requerido
                if not slot_def.required:
                    continue
                
                # ⚡ NUEVO: Si el slot no permite auto-extracción, saltarlo
                if not slot_def.auto_extract:
                    logger.debug(f"⏭️ [SlotManager] Saltando '{slot_name}' (auto_extract=False)")
                    continue
                
                # Verificar dependencias
                if slot_def.depends_on:
                    if slot_def.depends_on not in result.filled_slots:
                        # Depende de un slot que aún no está llenado
                        continue
                
                # Preparar contexto con flags especiales
                extraction_context = {
                    'choices': slot_def.validation_rules.get('choices', []),
                    'current_slots': result.filled_slots,
                    'is_product_name': slot_name == 'product_name'  # Flag para limpieza
                }
                
                # Intentar extraer (pasar contexto si es producto)
                extracted_value = self.extractor.extract(
                    slot_def.type, 
                    message,
                    context=extraction_context if slot_name == 'product_name' else None
                )
                
                if extracted_value is not None:
                    # Preparar contexto de validación (incluir sugerencias previas si existen)
                    validation_context = {
                        'current_slots': result.filled_slots,
                        'slot_name': slot_name,
                        '_suggested_products': result.context.get('_suggested_products', [])
                    }
                    
                    # Validar (incluir nombre del slot para validación de productos)
                    is_valid, error = self.validator.validate(
                        extracted_value,
                        slot_def.type,
                        slot_def.validation_rules,
                        context=validation_context
                    )
                    
                    # Verificar si el validador resolvió el valor (ej: selección ordinal)
                    resolved_value = validation_context.get('_resolved_value', extracted_value)
                    
                    # Guardar sugerencias para la próxima iteración
                    if '_suggested_products' in validation_context:
                        result.context['_suggested_products'] = validation_context['_suggested_products']
                    
                    if is_valid:
                        result.filled_slots[slot_name] = resolved_value
                        logger.info(f"✅ [SlotManager] Extraído del mensaje inicial: {slot_name} = {resolved_value}")
                    else:
                        # Guardar error de validación para mostrarlo en el prompt
                        result.validation_errors[slot_name] = error
                        logger.warning(f"❌ [SlotManager] Validación fallida en mensaje inicial para '{slot_name}': {error}")
        
        # ═══════════════════════════════════════════════════════════
        # CASO 2: Si HAY un slot actual (respuesta a pregunta específica)
        # Intentar extraer ese slot específico
        # ═══════════════════════════════════════════════════════════
        elif current_slot_name and current_slot_name in self.slots_schema:
            slot_def = self.slots_schema[current_slot_name]
            
            # Preparar contexto con flags especiales
            extraction_context = {
                'choices': slot_def.validation_rules.get('choices', []),
                'current_slots': result.filled_slots,
                'is_product_name': current_slot_name == 'product_name'  # Flag para limpieza
            }
            
            # Extraer valor (pasar contexto si es producto)
            extracted_value = self.extractor.extract(
                slot_def.type,
                message,
                context=extraction_context if current_slot_name == 'product_name' else None
            )
            
            if extracted_value is not None:
                # Preparar contexto de validación (incluir sugerencias previas si existen)
                validation_context = {
                    'current_slots': result.filled_slots,
                    'slot_name': current_slot_name,
                    '_suggested_products': result.context.get('_suggested_products', [])
                }
                
                # Validar valor (incluir nombre del slot para validación de productos)
                is_valid, error = self.validator.validate(
                    extracted_value,
                    slot_def.type,
                    slot_def.validation_rules,
                    context=validation_context
                )
                
                # Verificar si el validador resolvió el valor (ej: selección ordinal)
                resolved_value = validation_context.get('_resolved_value', extracted_value)
                
                # Guardar sugerencias para la próxima iteración
                if '_suggested_products' in validation_context:
                    result.context['_suggested_products'] = validation_context['_suggested_products']
                
                if is_valid:
                    # ✅ Slot llenado exitosamente
                    result.filled_slots[current_slot_name] = resolved_value
                    logger.info(f"✅ [SlotManager] Slot '{current_slot_name}' llenado: {resolved_value}")
                    
                    # Resetear intentos
                    result.attempts[current_slot_name] = 0
                else:
                    # ❌ Validación fallida
                    result.attempts[current_slot_name] = result.attempts.get(current_slot_name, 0) + 1
                    result.validation_errors[current_slot_name] = error
                    
                    logger.warning(f"❌ [SlotManager] Validación fallida para '{current_slot_name}': {error}")
                    
                    # Verificar si excede máximo de intentos
                    if result.attempts[current_slot_name] >= slot_def.max_attempts:
                        logger.error(f"❌ [SlotManager] Máximo de intentos alcanzado para '{current_slot_name}'")
            else:
                # No se pudo extraer valor
                result.attempts[current_slot_name] = result.attempts.get(current_slot_name, 0) + 1
                result.validation_errors[current_slot_name] = "No se pudo entender el valor"
                logger.warning(f"⚠️ [SlotManager] No se pudo extraer valor para '{current_slot_name}'")
        
        # Determinar siguiente slot a pedir
        next_slot = self._get_next_slot(result.filled_slots)
        
        if next_slot:
            result.completed = False
            result.current_slot = next_slot
            result.next_prompt = self._build_prompt(next_slot, result)
            logger.info(f"➡️ [SlotManager] Siguiente slot: {next_slot}")
        else:
            result.completed = True
            result.current_slot = None
            result.next_prompt = None
            logger.info(f"✅ [SlotManager] Todos los slots completados!")
        
        return result
    
    def _get_next_slot(self, filled_slots: Dict[str, Any]) -> Optional[str]:
        """
        Determina el siguiente slot a pedir
        
        Args:
            filled_slots: Slots ya llenados
            
        Returns:
            Nombre del siguiente slot o None si todos están llenados
        """
        for slot_name, slot_def in self.slots_schema.items():
            # Si ya está llenado, continuar
            if slot_name in filled_slots:
                continue
            
            # Verificar si es requerido
            if not slot_def.required:
                continue
            
            # Verificar dependencias
            if slot_def.depends_on:
                if slot_def.depends_on not in filled_slots:
                    # Depende de un slot que aún no está llenado
                    continue
            
            # Este es el siguiente slot
            return slot_name
        
        return None
    
    def _build_prompt(self, slot_name: str, result: SlotFillingResult) -> str:
        """
        Construye el prompt para solicitar un slot
        
        Args:
            slot_name: Nombre del slot
            result: Resultado actual del filling
            
        Returns:
            Prompt formateado
        """
        slot_def = self.slots_schema[slot_name]
        
        prompt = slot_def.prompt
        
        # 🎯 Personalizar prompt de cantidad con el nombre del producto
        if slot_name == "quantity" and "product_name" in result.filled_slots:
            product_name = result.filled_slots["product_name"]
            
            # Detectar el verbo del prompt original para mantener contexto
            # Si el prompt original dice "eliminar", "quitar", etc., mantenerlo
            if "eliminar" in prompt.lower():
                prompt = f"¿Cuántas unidades de *{product_name}* quieres eliminar?"
            elif "quitar" in prompt.lower() or "remover" in prompt.lower():
                prompt = f"¿Cuántas unidades de *{product_name}* quieres quitar?"
            else:
                # Por defecto (para agregar/crear órdenes)
                prompt = f"¿Cuántas unidades de *{product_name}* quieres?"
        
        # Si hubo error en intento anterior, agregar mensaje de error
        if slot_name in result.validation_errors:
            error = result.validation_errors[slot_name]
            prompt = f"❌ {error}\n\n{prompt}"
        
        # Agregar ejemplos si existen
        if slot_def.examples:
            examples_text = ", ".join(slot_def.examples[:3])
            prompt += f"\n\nEjemplos: {examples_text}"
        
        # Agregar opciones si es tipo choice
        if slot_def.type == "choice":
            choices = slot_def.validation_rules.get('choices', [])
            if choices:
                choices_text = "\n".join([f"{i+1}. {c}" for i, c in enumerate(choices)])
                prompt += f"\n\nOpciones:\n{choices_text}"
        
        return prompt
    
    def get_filled_percentage(self, filled_slots: Dict[str, Any]) -> float:
        """
        Calcula el porcentaje de slots llenados
        
        Args:
            filled_slots: Slots ya llenados
            
        Returns:
            Porcentaje (0-100)
        """
        required_slots = [
            name for name, slot_def in self.slots_schema.items()
            if slot_def.required
        ]
        
        if not required_slots:
            return 100.0
        
        filled_count = len([s for s in filled_slots.keys() if s in required_slots])
        return (filled_count / len(required_slots)) * 100