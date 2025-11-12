import asyncio
from typing import Dict, List, Callable, Optional
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger


@dataclass
class BufferedMessage:
    """Representa un mensaje en el buffer"""
    phone: str
    message: str
    message_id: str
    message_type: str
    timestamp: datetime
    media_url: Optional[str] = None


@dataclass
class MessageBuffer:
    """Buffer de mensajes para un usuario específico"""
    phone: str
    messages: List[BufferedMessage] = field(default_factory=list)
    timer_task: Optional[asyncio.Task] = None
    last_message_time: Optional[datetime] = None
    
    def add_message(self, message: BufferedMessage):
        """Agrega un mensaje al buffer"""
        self.messages.append(message)
        self.last_message_time = datetime.utcnow()
    
    def get_combined_text(self) -> str:
        """Combina todos los mensajes de texto en uno solo"""
        text_messages = [
            msg.message 
            for msg in self.messages 
            if msg.message_type == "text"
        ]
        return " ".join(text_messages)
    
    def clear(self):
        """Limpia el buffer"""
        self.messages.clear()
        self.last_message_time = None
        if self.timer_task and not self.timer_task.done():
            self.timer_task.cancel()
        self.timer_task = None
    
    def has_messages(self) -> bool:
        """Verifica si hay mensajes en el buffer"""
        return len(self.messages) > 0


class MessageBufferManager:
    """
    Gestiona buffers de mensajes para múltiples usuarios
    Implementa debouncing para agrupar mensajes rápidos
    """
    
    def __init__(self, debounce_seconds: float = 3.0):
        """
        Args:
            debounce_seconds: Segundos de espera después del último mensaje
        """
        self.debounce_seconds = debounce_seconds
        self.buffers: Dict[str, MessageBuffer] = {}
        self.processing_callback: Optional[Callable] = None
        
        logger.info(f"MessageBufferManager inicializado (debounce: {debounce_seconds}s)")
    
    def set_processing_callback(self, callback: Callable):
        """
        Establece la función que se llamará cuando se procese un buffer
        
        Args:
            callback: Función async que recibe (phone, combined_message, messages_list)
        """
        self.processing_callback = callback
    
    async def add_message(
        self,
        phone: str,
        message: str,
        message_id: str,
        message_type: str = "text",
        media_url: Optional[str] = None
    ):
        """
        Agrega un mensaje al buffer del usuario
        
        Args:
            phone: Número de teléfono
            message: Contenido del mensaje
            message_id: ID del mensaje de WAHA
            message_type: Tipo de mensaje (text, voice, image)
            media_url: URL de media si aplica
        """
        
        # Crear buffer si no existe
        if phone not in self.buffers:
            self.buffers[phone] = MessageBuffer(phone=phone)
            logger.debug(f"Nuevo buffer creado para {phone}")
        
        buffer = self.buffers[phone]
        
        # Agregar mensaje al buffer
        buffered_msg = BufferedMessage(
            phone=phone,
            message=message,
            message_id=message_id,
            message_type=message_type,
            timestamp=datetime.utcnow(),
            media_url=media_url
        )
        
        buffer.add_message(buffered_msg)
        
        logger.info(f"📥 Mensaje agregado al buffer de {phone} (total: {len(buffer.messages)})")
        logger.debug(f"   Contenido: '{message[:50]}...'")
        
        # Cancelar timer anterior si existe
        if buffer.timer_task and not buffer.timer_task.done():
            logger.debug(f"⏱️  Cancelando timer anterior de {phone}")
            buffer.timer_task.cancel()
        
        # Crear nuevo timer
        buffer.timer_task = asyncio.create_task(
            self._debounce_timer(phone)
        )
        
        logger.debug(f"⏱️  Nuevo timer iniciado para {phone} ({self.debounce_seconds}s)")
    
    async def _debounce_timer(self, phone: str):
        """
        Timer de debouncing. Si expira sin ser cancelado, procesa el buffer
        
        Args:
            phone: Número de teléfono del buffer
        """
        try:
            logger.debug(f"⏳ Timer iniciado para {phone}, esperando {self.debounce_seconds}s...")
            await asyncio.sleep(self.debounce_seconds)
            
            # Si llegamos aquí, el timer expiró sin ser cancelado
            logger.info(f"⏰ Timer expirado para {phone}, procesando buffer")
            await self._process_buffer(phone)
            
        except asyncio.CancelledError:
            logger.debug(f"⏱️  Timer cancelado para {phone} (nuevo mensaje recibido)")
        except Exception as e:
            logger.error(f"Error en timer de {phone}: {e}", exc_info=True)
    async def _process_buffer(self, phone: str):
        """
        Procesa el buffer de un usuario, combinando todos sus mensajes
        
        Args:
            phone: Número de teléfono
        """
        if phone not in self.buffers:
            logger.warning(f"No hay buffer para {phone}")
            return
        
        buffer = self.buffers[phone]
        
        if not buffer.has_messages():
            logger.warning(f"Buffer vacío para {phone}")
            return
        
        # Combinar mensajes
        combined_message = buffer.get_combined_text()
        messages_list = buffer.messages.copy()
        
        logger.info("=" * 70)
        logger.info(f"🔄 PROCESANDO BUFFER DE {phone}")
        logger.info(f"   Mensajes en buffer: {len(messages_list)}")
        logger.info(f"   Mensaje combinado: '{combined_message[:100]}...'")
        logger.info("=" * 70)
        
        # Limpiar buffer ANTES de procesar (para evitar duplicados)
        buffer.clear()
        
        # Llamar callback de procesamiento
        if self.processing_callback:
            try:
                await self.processing_callback(phone, combined_message, messages_list)
            except Exception as e:
                logger.error(f"Error en callback de procesamiento: {e}", exc_info=True)
        else:
            logger.warning("No hay callback de procesamiento configurado")
    
    async def force_process(self, phone: str):
        """
        Fuerza el procesamiento inmediato del buffer de un usuario
        
        Args:
            phone: Número de teléfono
        """
        logger.info(f"🔨 Forzando procesamiento de buffer para {phone}")
        
        if phone in self.buffers:
            buffer = self.buffers[phone]
            if buffer.timer_task and not buffer.timer_task.done():
                buffer.timer_task.cancel()
            await self._process_buffer(phone)
    
    def get_buffer_info(self, phone: str) -> Dict:
        """Obtiene información del buffer de un usuario"""
        if phone not in self.buffers:
            return {"exists": False}
        
        buffer = self.buffers[phone]
        return {
            "exists": True,
            "message_count": len(buffer.messages),
            "has_timer": buffer.timer_task is not None and not buffer.timer_task.done(),
            "last_message_time": buffer.last_message_time.isoformat() if buffer.last_message_time else None
        }
    
    def clear_buffer(self, phone: str):
        """Limpia el buffer de un usuario"""
        if phone in self.buffers:
            self.buffers[phone].clear()
            del self.buffers[phone]
            logger.info(f"Buffer de {phone} eliminado")


# Instancia global
message_buffer_manager = MessageBufferManager(debounce_seconds=15.0)
