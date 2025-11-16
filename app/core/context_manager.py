from typing import Dict, List, Optional, Any
from datetime import datetime
from loguru import logger
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.database.repository import (
    CustomerRepository,
    ConversationRepository,
    MessageRepository
)
from app.core.correlation import set_client_context


class ContextManager:
    """Gestiona el contexto de las conversaciones"""
    
    def __init__(self, db: Session):
        self.db = db
        self.customer_repo = CustomerRepository()
        self.conversation_repo = ConversationRepository()
        self.message_repo = MessageRepository()
    
    def get_or_create_context(self, phone: str) -> Dict[str, Any]:
        """
        Obtiene o crea el contexto completo para un cliente
        
        Returns:
            Dict con toda la información contextual
        """
        # Obtener o crear cliente
        customer = self.customer_repo.get_or_create(phone, self.db)
        
        # Obtener o crear conversación activa
        conversation = self.conversation_repo.get_active_conversation(
            customer.id, self.db
        )
        
        if not conversation:
            conversation = self.conversation_repo.create_conversation(
                customer.id, self.db
            )

        # Establecer contexto de cliente para tracking en logs
        set_client_context(phone, conversation.id)

        # Obtener historial de mensajes
        messages = self.message_repo.get_conversation_history(
            conversation.id, 
            limit=10,
            db=self.db
        )
        
        # Construir contexto
        context = {
            "customer_id": customer.id,
            "customer_phone": customer.phone,
            "customer_name": customer.name,
            "customer_data": customer.customer_data or {},
            "conversation_id": conversation.id,
            "conversation_state": conversation.state,
            "current_intent": conversation.current_intent,
            "current_module": conversation.current_module,
            "slots_data": conversation.slots_data or {},
            "slots_schema": conversation.slots_schema or {},  # <-- IMPORTANTE
            "current_slot": conversation.current_slot,
            "validation_attempts": conversation.validation_attempts or {},
            "message_history": [
                {
                    "content": msg.content,
                    "is_from_bot": msg.is_from_bot,
                    "timestamp": msg.created_at.isoformat()
                }
                for msg in messages
            ],
            "conversation_started_at": conversation.started_at.isoformat(),
            "last_activity": conversation.last_activity_at.isoformat()
        }
        
        # ⚡ NUEVO: Incluir TODOS los campos adicionales de context_data
        # Esto incluye flags personalizados como waiting_location_confirmation, 
        # previous_location_offered, offered_location, etc.
        if conversation.context_data:
            context.update(conversation.context_data)
            logger.debug(f"📦 [ContextManager] Cargando context_data: {list(conversation.context_data.keys())}")
        
        logger.info(f"🔍 [ContextManager] Contexto leído: current_module={context.get('current_module')}, estado={context.get('conversation_state')}")
        
        return context
    
    def save_message(
        self,
        phone: str,
        content: str,
        message_type: str = "text",
        is_from_bot: bool = False,
        waha_message_id: Optional[str] = None
    ) -> None:
        """Guarda un mensaje en el contexto"""
        context = self.get_or_create_context(phone)
        
        self.message_repo.create_message(
            conversation_id=context["conversation_id"],
            customer_id=context["customer_id"],
            content=content,
            message_type=message_type,
            is_from_bot=is_from_bot,
            waha_message_id=waha_message_id,
            db=self.db
        )
        
        logger.debug(f"💾 Mensaje guardado para {phone}")
    
    def update_conversation_state(
        self,
        phone: str,
        state: str,
        intent: Optional[str] = None,
        module: Optional[str] = None
    ) -> None:
        """Actualiza el estado de la conversación"""
        context = self.get_or_create_context(phone)
        
        conversation = self.conversation_repo.update_state(
            context["conversation_id"],
            state,
            self.db
        )
        
        if conversation:
            if intent:
                conversation.current_intent = intent
            if module:
                conversation.current_module = module
            self.db.commit()
    
    def get_conversation_summary(self, phone: str) -> str:
        """
        Genera un resumen de la conversación para usar en prompts
        
        Returns:
            String con el resumen de la conversación
        """
        context = self.get_or_create_context(phone)
        
        messages = context["message_history"]
        if not messages:
            return "Primera interacción con el cliente."
        
        # Crear resumen
        summary_parts = []
        
        # Info del cliente
        if context.get("customer_name"):
            summary_parts.append(f"Cliente: {context['customer_name']}")
        
        # Mensajes recientes (últimos 5)
        recent_messages = messages[-5:]
        conversation_text = "\n".join([
            f"{'Bot' if msg['is_from_bot'] else 'Cliente'}: {msg['content']}"
            for msg in recent_messages
        ])
        summary_parts.append(f"Conversación reciente:\n{conversation_text}")
        
        # Estado actual
        if context.get("current_intent"):
            summary_parts.append(f"Intención actual: {context['current_intent']}")
        
        if context.get("slots_data"):
            summary_parts.append(f"Datos recolectados: {context['slots_data']}")
        
        return "\n\n".join(summary_parts)
    
    # ═══════════════════════════════════════════════════════════
    # MÉTODOS PARA GESTIÓN DE MÓDULOS
    # ═══════════════════════════════════════════════════════════
    
    def update_module_context(
        self,
        phone: str,
        module_name: str,
        context_updates: Dict[str, Any]
    ) -> None:
        """
        Actualiza el contexto relacionado con un módulo

        Args:
            phone: Teléfono del usuario
            module_name: Nombre del módulo
            context_updates: Actualizaciones de contexto
        """
        # Obtener customer y conversation directamente
        customer = self.customer_repo.get_or_create(phone, self.db)
        conversation = self.conversation_repo.get_active_conversation(
            customer.id, self.db
        )

        if not conversation:
            conversation = self.conversation_repo.create_conversation(
                customer.id, self.db
            )

        # Establecer contexto de cliente para tracking en logs
        set_client_context(phone, conversation.id)

        # Actualizar campos específicos del módulo
        if 'current_slot' in context_updates:
            conversation.current_slot = context_updates['current_slot']
        
        if 'slots_data' in context_updates:
            # Asegurar que slots_data siempre sea un diccionario
            slots_data = context_updates['slots_data']
            if isinstance(slots_data, list):
                logger.warning(f"⚠️ slots_data era una lista, convirtiendo a dict: {slots_data}")
                conversation.slots_data = {}
            else:
                conversation.slots_data = slots_data
        
        if 'validation_attempts' in context_updates:
            # Asegurar que validation_attempts siempre sea un diccionario
            validation_attempts = context_updates['validation_attempts']
            if isinstance(validation_attempts, list):
                logger.warning(f"⚠️ validation_attempts era una lista, convirtiendo a dict: {validation_attempts}")
                conversation.validation_attempts = {}
            else:
                conversation.validation_attempts = validation_attempts
        
        if 'conversation_state' in context_updates:
            conversation.state = context_updates['conversation_state']
        
        # Guardar módulo actual (usar el de context_updates si existe, si no usar module_name)
        if 'current_module' in context_updates:
            conversation.current_module = context_updates['current_module']
            logger.info(f"   🔑 [ContextManager] Guardando current_module desde updates: {context_updates['current_module']}")
        else:
            conversation.current_module = module_name
            logger.info(f"   🔑 [ContextManager] Guardando current_module desde parámetro: {module_name}")
        
        # ⚡ NUEVO: Guardar TODOS los campos adicionales en context_data
        # Esto incluye flags personalizados como waiting_location_confirmation, 
        # previous_location_offered, offered_location, etc.
        context_data = conversation.context_data or {}
        
        logger.debug(f"📥 [ContextManager] context_data ANTES: {context_data}")
        logger.debug(f"📥 [ContextManager] context_updates: {list(context_updates.keys())}")
        
        # Campos conocidos que ya se guardan en columnas específicas
        known_fields = {'current_slot', 'slots_data', 'validation_attempts', 'conversation_state', 'current_module'}
        
        # Guardar cualquier otro campo en context_data
        additional_fields = []
        for key, value in context_updates.items():
            if key not in known_fields:
                context_data[key] = value
                additional_fields.append(f"{key}={value}")
        
        if additional_fields:
            logger.debug(f"  📝 [ContextManager] Campos adicionales: {', '.join(additional_fields)}")
        
        conversation.context_data = context_data
        
        # ⚡ CRÍTICO: Marcar el campo JSON como modificado para que SQLAlchemy lo guarde
        flag_modified(conversation, 'context_data')
        
        self.db.commit()
        
        # Verificar que se guardó correctamente
        self.db.refresh(conversation)
        logger.info(f"✅ [ContextManager] Contexto COMMITEADO. current_module en BD: {conversation.current_module}")
        logger.debug(f"✅ [ContextManager] Contexto actualizado: {module_name}")
    
    def get_module_context(self, phone: str) -> Dict[str, Any]:
        """
        Obtiene el contexto relacionado con módulos

        Args:
            phone: Teléfono del usuario

        Returns:
            Dict con contexto de módulos
        """
        # Obtener customer y conversation directamente
        customer = self.customer_repo.get_or_create(phone, self.db)
        conversation = self.conversation_repo.get_active_conversation(
            customer.id, self.db
        )

        if not conversation:
            conversation = self.conversation_repo.create_conversation(
                customer.id, self.db
            )

        # Establecer contexto de cliente para tracking en logs
        set_client_context(phone, conversation.id)

        # Construir contexto base
        # Asegurar que slots_data y validation_attempts sean siempre diccionarios
        slots_data = conversation.slots_data or {}
        if isinstance(slots_data, list):
            logger.warning(f"⚠️ [ContextManager] slots_data en BD era lista, corrigiendo a dict")
            slots_data = {}
        
        validation_attempts = conversation.validation_attempts or {}
        if isinstance(validation_attempts, list):
            logger.warning(f"⚠️ [ContextManager] validation_attempts en BD era lista, corrigiendo a dict")
            validation_attempts = {}
        
        module_context = {
            'current_module': conversation.current_module,
            'conversation_state': conversation.state,
            'slots_data': slots_data,
            'current_slot': conversation.current_slot,
            'validation_attempts': validation_attempts
        }
        
        # ⚡ NUEVO: Fusionar campos de context_data al nivel superior
        # Para que sean accesibles directamente como context.get('waiting_location_confirmation')
        if conversation.context_data:
            module_context.update(conversation.context_data)
            logger.debug(f"📦 [ContextManager] Cargando module context_data: {list(conversation.context_data.keys())}")
        
        return module_context
    
    def clear_module_context(self, phone: str) -> None:
        """
        Limpia el contexto de módulos (después de completar un proceso)

        Args:
            phone: Teléfono del usuario
        """
        # Obtener customer y conversation directamente
        customer = self.customer_repo.get_or_create(phone, self.db)
        conversation = self.conversation_repo.get_active_conversation(
            customer.id, self.db
        )

        if not conversation:
            # Si no hay conversación, no hay nada que limpiar
            return

        # Establecer contexto de cliente para tracking en logs
        set_client_context(phone, conversation.id)

        conversation.current_module = None
        conversation.current_slot = None
        conversation.slots_data = {}
        conversation.validation_attempts = {}
        conversation.state = "idle"
        
        self.db.commit()
        
        logger.info(f"🧹 [ContextManager] Contexto de módulo limpiado")