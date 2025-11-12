from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from loguru import logger

from app.database.models import Customer, Conversation, Message
from config.database import get_db_context


class CustomerRepository:
    """Repositorio para operaciones con Customer"""
    
    @staticmethod
    def get_or_create(phone: str, db: Session) -> Customer:
        """Obtiene o crea un cliente por teléfono"""
        customer = db.query(Customer).filter(Customer.phone == phone).first()
        
        if not customer:
            customer = Customer(phone=phone)
            db.add(customer)
            db.commit()
            db.refresh(customer)
            logger.info(f"✓ Nuevo cliente creado: {phone}")
        else:
            # Actualizar último contacto
            customer.last_contact_at = datetime.utcnow()
            customer.total_messages += 1
            db.commit()
        
        return customer
    
    @staticmethod
    def update_customer_data(
        customer_id: str,
        data: Dict[str, Any],
        db: Session
    ) -> Optional[Customer]:
        """Actualiza datos del cliente"""
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        
        if customer:
            # Merge con datos existentes
            current_data = customer.customer_data or {}
            current_data.update(data)
            customer.customer_data = current_data
            db.commit()
            db.refresh(customer)
        
        return customer


class ConversationRepository:
    """Repositorio para operaciones con Conversation"""
    
    @staticmethod
    def get_active_conversation(
        customer_id: str,
        db: Session
    ) -> Optional[Conversation]:
        """Obtiene la conversación activa de un cliente"""
        conversation = db.query(Conversation).filter(
            Conversation.customer_id == customer_id,
            Conversation.is_active == True
        ).first()
        
        return conversation
    
    @staticmethod
    def create_conversation(
        customer_id: str,
        db: Session
    ) -> Conversation:
        """Crea una nueva conversación"""
        conversation = Conversation(
            customer_id=customer_id,
            state="idle",
            # ✅ Inicializar explícitamente los campos JSON como diccionarios
            slots_data={},
            slots_schema={},
            validation_attempts={},
            context_data={}
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        
        logger.info(f"✓ Nueva conversación creada: {conversation.id}")
        return conversation
    
    @staticmethod
    def update_state(
        conversation_id: str,
        state: str,
        db: Session
    ) -> Optional[Conversation]:
        """Actualiza el estado de una conversación"""
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        
        if conversation:
            conversation.state = state
            conversation.last_activity_at = datetime.utcnow()
            db.commit()
            db.refresh(conversation)
        
        return conversation
    
    @staticmethod
    def update_slots(
        conversation_id: str,
        slot_name: str,
        slot_value: Any,
        db: Session
    ) -> Optional[Conversation]:
        """Actualiza un slot en la conversación"""
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        
        if conversation:
            slots_data = conversation.slots_data or {}
            slots_data[slot_name] = slot_value
            conversation.slots_data = slots_data
            conversation.last_activity_at = datetime.utcnow()
            db.commit()
            db.refresh(conversation)
        
        return conversation
    
    @staticmethod
    def complete_conversation(
        conversation_id: str,
        db: Session
    ) -> Optional[Conversation]:
        """Marca una conversación como completada"""
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        
        if conversation:
            conversation.is_active = False
            conversation.state = "completed"
            conversation.completed_at = datetime.utcnow()
            db.commit()
            db.refresh(conversation)
        
        return conversation


class MessageRepository:
    """Repositorio para operaciones con Message"""
    
    @staticmethod
    def create_message(
        conversation_id: str,
        customer_id: str,
        content: str,
        message_type: str = "text",
        is_from_bot: bool = False,
        waha_message_id: Optional[str] = None,
        db: Session = None
    ) -> Message:
        """Crea un nuevo mensaje"""
        message = Message(
            conversation_id=conversation_id,
            customer_id=customer_id,
            content=content,
            message_type=message_type,
            is_from_bot=is_from_bot,
            waha_message_id=waha_message_id
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        
        return message
    
    @staticmethod
    def get_conversation_history(
        conversation_id: str,
        limit: int = 10,
        db: Session = None
    ) -> List[Message]:
        """Obtiene el historial de mensajes de una conversación"""
        messages = db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(desc(Message.created_at)).limit(limit).all()
        
        return list(reversed(messages))  # Orden cronológico
    
    @staticmethod
    def get_recent_messages(
        customer_id: str,
        limit: int = 10,
        db: Session = None
    ) -> List[Message]:
        """Obtiene los mensajes recientes de un cliente"""
        messages = db.query(Message).filter(
            Message.customer_id == customer_id
        ).order_by(desc(Message.created_at)).limit(limit).all()
        
        return list(reversed(messages))