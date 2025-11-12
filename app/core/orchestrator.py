from typing import Dict, Optional, Any
from sqlalchemy.orm import Session
from loguru import logger

from app.core.slot_manager import SlotManager
from app.core.slot_validator import SlotValidator
from app.modules.base_module import BaseModule, Slot
from app.modules.registry import module_registry
from app.clients.ollama_client import OllamaClient
from app.database.repository import ConversationRepository
from app.core.confirmation_manager import ConfirmationManager

class ConversationState:
    """Estados posibles de una conversación"""
    IDLE = "idle"
    COLLECTING_SLOTS = "collecting_slots"
    CONFIRMING = "confirming"
    EXECUTING_ACTION = "executing_action"
    COMPLETED = "completed"


class Orchestrator:
    """Orquesta el flujo completo de conversación con slot filling"""
    
    def __init__(self, ollama_client: OllamaClient, db: Session):
        self.ollama = ollama_client
        self.db = db
        self.validator = SlotValidator(ollama_client)
        self.conversation_repo = ConversationRepository()
    
    async def process_message(
        self,
        message: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Procesa un mensaje dentro del flujo de conversación
        """
        conversation_id = context.get("conversation_id")
        state = context.get("conversation_state", ConversationState.IDLE)
        
        logger.info(f"Orchestrator procesando en estado: {state}")
        
        # Si está inactivo, es un nuevo intent
        if state == ConversationState.IDLE:
            return await self._handle_new_intent(message, context)
        
        # Si está recolectando slots
        elif state == ConversationState.COLLECTING_SLOTS:
            return await self._handle_slot_filling(message, context)
        
        # Si está esperando confirmación
        elif state == ConversationState.CONFIRMING:
            return await self._handle_confirmation(message, context)
        
        # Si está ejecutando acción
        elif state == ConversationState.EXECUTING_ACTION:
            return "Dame un momento, estoy procesando tu solicitud..."
        
        # Por defecto, reiniciar
        return await self._handle_new_intent(message, context)
    
    async def _handle_new_intent(
        self,
        message: str,
        context: Dict[str, Any]
    ) -> str:
        """Maneja una nueva intención detectada"""
        
        intent = context.get("current_intent")
        
        if not intent:
            return "No entendi tu solicitud. Podrias reformularla?"
        
        logger.info(f"Manejando nueva intencion: {intent}")
        
        # Obtener módulo para esta intención
        module = module_registry.get_module(intent)
        
        if not module:
            logger.warning(f"No hay modulo registrado para: {intent}")
            return "Entiendo tu solicitud, pero aun no puedo ayudarte con eso. Pronto estare listo!"
        
        # Obtener slots requeridos
        required_slots = module.get_required_slots()
        
        # Si no requiere slots, ejecutar directamente
        if not required_slots:
            result = await module.execute({}, context)
            return result.get("message", "Accion completada")
        
        # Iniciar recolección de slots
        logger.info(f"Iniciando recoleccion de {len(required_slots)} slots")
        slot_manager = SlotManager(required_slots)
        
        conversation_id = context["conversation_id"]
        
        # IMPORTANTE: Guardar estado del slot manager ANTES de cambiar el estado
        self._save_slot_manager_state(conversation_id, slot_manager)
        
        # Cambiar estado de la conversación
        from app.database.models import Conversation
        conversation = self.db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        
        if conversation:
            conversation.state = ConversationState.COLLECTING_SLOTS
            conversation.current_intent = intent
            conversation.current_module = module.name
            self.db.commit()
            logger.info(f"Estado actualizado a COLLECTING_SLOTS")
        
        # Solicitar primer slot
        next_slot = slot_manager.get_next_slot()
        if next_slot:
            logger.info(f"Solicitando primer slot: {next_slot.name}")
            return next_slot.question_template
        
        return "Hay un problema con el proceso. Intenta de nuevo."
    
    async def _handle_slot_filling(
        self,
        message: str,
        context: Dict[str, Any]
    ) -> str:
        """Maneja el proceso de recolección de slots"""
        
        conversation_id = context["conversation_id"]
        
        logger.debug(f"=== HANDLE SLOT FILLING ===")
        logger.debug(f"Conversation ID: {conversation_id}")
        logger.debug(f"Mensaje: {message}")
        
        # Recuperar SlotManager del contexto
        slot_manager = self._load_slot_manager(context)
        
        if not slot_manager:
            logger.error("No se pudo cargar SlotManager")
            logger.error(f"Contexto disponible: {list(context.keys())}")
            logger.error(f"slots_schema en contexto: {context.get('slots_schema')}")
            
            # Intentar recuperarse reiniciando la conversación
            from app.database.models import Conversation
            conversation = self.db.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()
            
            if conversation:
                conversation.state = ConversationState.IDLE
                conversation.current_intent = None
                conversation.current_module = None
                conversation.slots_data = {}
                conversation.slots_schema = {}
                self.db.commit()
            
            return "Hubo un error en el proceso. Empecemos de nuevo. Que necesitas?"
        
        # CRÍTICO: Obtener slot actual
        current_slot = slot_manager.get_current_slot()
        
        # Si el slot actual está vacío, obtener el siguiente
        if not current_slot:
            logger.warning("No hay current_slot, obteniendo siguiente")
            current_slot = slot_manager.get_next_slot()
            
            if not current_slot:
                logger.error("No hay slot actual ni siguiente")
                # Verificar si ya están todos llenos
                if slot_manager.is_complete():
                    logger.info("Todos los slots completados (detección tardía)")
                    return await self._request_confirmation(context, slot_manager)
                
                return "Hubo un error. Que necesitas?"
        
        # ⭐ NUEVO: Si el slot actual YA ESTÁ LLENO, pasar al siguiente
        if current_slot.filled:
            logger.warning(f"⚠️ Slot '{current_slot.name}' ya está lleno con valor: {current_slot.value}")
            logger.warning("Saltando al siguiente slot...")
            
            # Obtener el siguiente slot vacío
            next_slot = slot_manager.get_next_slot()
            
            if not next_slot:
                # No hay más slots, ir a confirmación
                logger.info("No hay más slots vacíos, solicitando confirmación")
                return await self._request_confirmation(context, slot_manager)
            
            # Actualizar current_slot
            current_slot = next_slot
            logger.info(f"✓ Nuevo slot actual: {current_slot.name}")
        
        logger.info(f"Procesando slot: {current_slot.name}")
        logger.debug(f"Tipo: {current_slot.type.value}")
        logger.debug(f"Filled: {current_slot.filled}")
        logger.debug(f"Value: {current_slot.value}")
        
        # Validar respuesta del usuario
        is_valid, value, feedback = await self.validator.validate_and_extract(
            user_message=message,
            slot=current_slot,
            context=context
        )
        
        logger.debug(f"Validacion: valido={is_valid}, valor={value}")
        
        # Si no es válido
        if not is_valid:
            attempts = slot_manager.increment_attempts(current_slot.name)
            logger.info(f"Intento fallido #{attempts} para slot {current_slot.name}")
            
            # Guardar intentos actualizados
            self._save_slot_manager_state(conversation_id, slot_manager)
            
            if attempts >= 3:
                help_msg = f"{feedback}\n\n"
                help_msg += "Parece que hay confusion. Te explico mejor:\n"
                help_msg += f"{current_slot.description}\n\n"
                
                if current_slot.choices:
                    help_msg += f"Opciones: {', '.join(current_slot.choices)}"
                
                return help_msg
            
            return feedback
        
        # Slot válido, guardarlo
        logger.info(f"✓ Slot {current_slot.name} llenado con: {value}")
        slot_manager.fill_slot(current_slot.name, value)
        
        # Actualizar en BD
        self.conversation_repo.update_slots(
            conversation_id,
            current_slot.name,
            value,
            self.db
        )
        
        # Guardar estado del slot manager
        self._save_slot_manager_state(conversation_id, slot_manager)
        
        # Verificar si todos los slots están completos
        if slot_manager.is_complete():
            logger.info("✓ Todos los slots completados, solicitando confirmación")
            return await self._request_confirmation(context, slot_manager)
        
        # Solicitar siguiente slot
        next_slot = slot_manager.get_next_slot()
        if next_slot:
            logger.info(f"➡️ Solicitando siguiente slot: {next_slot.name}")
            confirmation = f"Perfecto, {current_slot.description}: {value}\n\n"
            return confirmation + next_slot.question_template
        
        logger.warning("No hay siguiente slot pero no está complete()")
        return "Hay un problema. Empecemos de nuevo."
      
    async def _request_confirmation(
        self,
        context: Dict[str, Any],
        slot_manager: SlotManager
    ) -> str:
        """
        Solicita confirmación antes de ejecutar el módulo
        """
        conversation_id = context["conversation_id"]
        module_name = context.get("current_module")
        
        # Cambiar estado a CONFIRMING
        from app.database.models import Conversation
        conversation = self.db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        
        if conversation:
            conversation.state = ConversationState.CONFIRMING
            self.db.commit()
        
        # Generar mensaje de confirmación
        slots_data = slot_manager.get_filled_slots()
        confirmation_msg = ConfirmationManager.generate_confirmation_message(
            module_name,
            slots_data
        )
        
        return confirmation_msg
    
    async def _handle_confirmation(
        self,
        message: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Maneja la respuesta del usuario a la confirmación
        """
        conversation_id = context["conversation_id"]
        
        # Parsear respuesta
        response_type = ConfirmationManager.parse_confirmation_response(message)
        
        logger.info(f"Respuesta a confirmacion: {response_type}")
        
        if response_type == "yes":
            # Confirmar y ejecutar
            slot_manager = self._load_slot_manager(context)
            if slot_manager:
                return await self._execute_module(context, slot_manager)
            else:
                return "Hubo un error. Empecemos de nuevo."
        
        elif response_type == "no":
            # Cancelar operación
            self.conversation_repo.complete_conversation(conversation_id, self.db)
            return "Operacion cancelada. Si necesitas algo mas, solo escribeme!"
        
        elif response_type and response_type.startswith("edit:"):
            # Editar un campo específico
            field_to_edit = response_type.split(":")[1]
            return await self._handle_field_correction(field_to_edit, context)
        
        else:
            # No entendió la respuesta
            return "No entendi tu respuesta. Por favor responde 'SI' para confirmar, 'NO' para cancelar, o dime que campo quieres corregir."
    
    async def _handle_field_correction(
        self,
        field_name: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Maneja la corrección de un campo específico
        """
        conversation_id = context["conversation_id"]
        
        # Cargar slot manager
        slot_manager = self._load_slot_manager(context)
        
        if not slot_manager:
            return "Hubo un error. Empecemos de nuevo."
        
        # Buscar el slot
        if field_name not in slot_manager.slots:
            return f"No encontre el campo '{field_name}'. Cual campo quieres corregir?"
        
        slot = slot_manager.slots[field_name]
        
        # Marcar el slot como no lleno
        slot.filled = False
        slot.value = None
        slot.attempts = 0
        
        # Resetear slot manager al campo a corregir
        slot_manager.current_slot_name = field_name
        slot_manager.completed = False
        
        # Guardar estado
        self._save_slot_manager_state(conversation_id, slot_manager)
        
        # Cambiar estado a collecting
        from app.database.models import Conversation
        conversation = self.db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        
        if conversation:
            conversation.state = ConversationState.COLLECTING_SLOTS
            conversation.current_slot = field_name
            self.db.commit()
        
        return f"Perfecto, vamos a corregir {slot.description}.\n\n{slot.question_template}"
    
    async def _execute_module(
        self,
        context: Dict[str, Any],
        slot_manager: SlotManager
    ) -> str:
        """Ejecuta el módulo con todos los slots completos"""
        
        conversation_id = context["conversation_id"]
        intent = context.get("current_intent")
        
        # Cambiar estado a ejecutando
        self.conversation_repo.update_state(
            conversation_id,
            ConversationState.EXECUTING_ACTION,
            self.db
        )
        
        logger.info(f"Ejecutando modulo para: {intent}")
        
        # Obtener módulo
        module = module_registry.get_module(intent)
        
        if not module:
            logger.error(f"Modulo no encontrado para: {intent}")
            return "Hubo un error ejecutando la accion."
        
        # Ejecutar con todos los datos
        slots_data = slot_manager.get_filled_slots()
        result = await module.execute(slots_data, context)
        
        # Completar conversación
        self.conversation_repo.complete_conversation(conversation_id, self.db)
        
        # Retornar mensaje del resultado
        return result.get("message", "Accion completada exitosamente")
    
    def _save_slot_manager_state(
        self,
        conversation_id: str,
        slot_manager: SlotManager
    ):
        """Guarda el estado del SlotManager en la BD"""
        try:
            from app.database.models import Conversation
            
            conversation = self.db.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()
            
            if not conversation:
                logger.error(f"Conversacion {conversation_id} no encontrada")
                return
            
            # Guardar estado completo
            state_dict = slot_manager.to_dict()
            filled_slots = slot_manager.get_filled_slots()
            
            conversation.slots_schema = state_dict
            conversation.slots_data = filled_slots
            conversation.current_slot = slot_manager.current_slot_name
            
            self.db.commit()
            
            logger.debug("=" * 60)
            logger.debug(f"💾 GUARDANDO Estado de SlotManager:")
            logger.debug(f"  Conversacion: {conversation_id}")
            logger.debug(f"  Current slot: {slot_manager.current_slot_name}")
            logger.debug(f"  Completed: {slot_manager.completed}")
            logger.debug(f"  Slots llenos: {list(filled_slots.keys())}")
            
            # Verificar cada slot
            for name, slot in slot_manager.slots.items():
                status = "✓ LLENO" if slot.filled else "⭕ VACÍO"
                logger.debug(f"    {status} {name}: {slot.value}")
            
            logger.debug("=" * 60)
            
        except Exception as e:
            logger.error(f"Error guardando estado de SlotManager: {e}", exc_info=True)
            self.db.rollback()
            
    def _load_slot_manager(self, context: Dict[str, Any]) -> Optional[SlotManager]:
        """Carga el SlotManager desde el contexto"""
        try:
            slots_schema = context.get("slots_schema")
            
            logger.debug(f"Cargando SlotManager desde contexto")
            logger.debug(f"slots_schema disponible: {slots_schema is not None}")
            
            if not slots_schema:
                logger.warning("No hay slots_schema en el contexto")
                return None
            
            if not isinstance(slots_schema, dict):
                logger.warning(f"slots_schema no es dict: {type(slots_schema)}")
                return None
            
            if "slots" not in slots_schema:
                logger.warning("slots_schema no contiene 'slots'")
                return None
            
            # Cargar desde el schema guardado
            slot_manager = SlotManager.from_dict(slots_schema)
            
            logger.debug(f"SlotManager cargado exitosamente")
            logger.debug(f"Slots totales: {len(slot_manager.slots)}")
            logger.debug(f"Slot actual: {slot_manager.current_slot_name}")
            
            return slot_manager
            
        except Exception as e:
            logger.error(f"Error cargando SlotManager: {e}", exc_info=True)
            return None