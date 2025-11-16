from typing import Dict, Optional, Any
from loguru import logger
from sqlalchemy.orm import Session

from app.clients.waha_client import WAHAClient
from app.clients.ollama_client import OllamaClient
from app.clients.whisper_client import WhisperClient
from app.core.context_manager import ContextManager
from app.core.correlation import set_client_context

from app.core.intent_detector import IntentDetector
from config.database import get_db_context
from config.settings import settings


class MessageProcessor:
    """Procesador central de mensajes"""
    
    def __init__(self):
        """Inicializa el procesador de mensajes"""
        # Inicializar solo los clientes que no necesitan DB
        self.waha = WAHAClient()
        self.ollama = OllamaClient()
        self.whisper = WhisperClient()
        self.intent_detector = IntentDetector(self.ollama)
        
        # NO crear context_manager aquí
        # Se creará dentro de cada método con la sesión DB
        
        logger.info("MessageProcessor inicializado correctamente")


    async def process_text_message(
        self,
        phone: str,
        message: str,
        message_id: Optional[str] = None
    ):
        """Procesa un mensaje de texto"""
        try:
            logger.info(f"🔵 [1/6] Iniciando process_text_message para {phone}")
            logger.info(f"🔵 [1/6] Mensaje: '{message}'")
            
            # ⭐ PASO 1: Obtener contexto y guardar mensaje (con DB)
            with get_db_context() as db:
                logger.info(f"🔵 [2/6] Creando context manager con sesión DB...")
                context_manager = ContextManager(db)
                
                logger.info(f"🔵 [2/6] Obteniendo/creando contexto...")
                context = context_manager.get_or_create_context(phone)

                # Establecer contexto de cliente para tracking en logs
                set_client_context(phone, context.get('conversation_id'))

                logger.info(f"🔵 [2/6] Contexto obtenido. Estado: {context.get('conversation_state', 'IDLE')}")
                
                logger.info(f"🔵 [3/6] Guardando mensaje...")
                context_manager.save_message(
                    phone=phone,
                    content=message,
                    message_type="text",
                    is_from_bot=False,
                    waha_message_id=message_id
                )
                logger.info(f"🔵 [3/6] Mensaje guardado")
            
            # ⭐ DB CERRADA - Ahora podemos hacer llamadas async sin bloquear
            
            logger.info(f"🔵 [4/6] Detectando intención...")
            try:
                import asyncio
                
                intent_result = await asyncio.wait_for(
                    self.intent_detector.detect_intent(
                        message=message,
                        context=context
                    ),
                    timeout=30.0
                )
                
                intent = intent_result.get("intent", "unknown")
                confidence = intent_result.get("confidence", 0.0)
                
                logger.info(f"🔵 [4/6] Intención detectada: {intent} (confianza: {confidence})")
                
            except asyncio.TimeoutError:
                logger.error(f"⏰ Timeout detectando intención (30s)")
                logger.warning("⚠️  Usando intención por defecto: greeting")
                intent = "greeting"
                confidence = 0.5
                
            except Exception as e:
                logger.error(f"❌ Error detectando intención: {e}", exc_info=True)
                logger.warning("⚠️  Usando intención por defecto: greeting")
                intent = "greeting"
                confidence = 0.5
            
            logger.info(f"🔵 [5/6] Generando respuesta...")
            if intent == "greeting":
                response = "¡Hola! Bienvenido. ¿En qué puedo ayudarte hoy?"
            elif intent == "create_order":
                response = "Entiendo que quieres hacer un pedido. ¿Qué producto te interesa?"
            elif intent == "check_order":
                response = "Puedo ayudarte a consultar tu pedido. ¿Tienes el número de orden?"
            elif intent == "goodbye":
                response = "¡Hasta luego! Que tengas un excelente día."
            else:
                response = "Gracias por tu mensaje. ¿Puedes darme más detalles sobre lo que necesitas?"
            
            logger.info(f"🔵 [5/6] Respuesta generada: '{response[:50]}...'")
            
            # ⭐ PASO 2: Guardar respuesta del bot (nueva transacción DB)
            with get_db_context() as db:
                context_manager = ContextManager(db)
                context_manager.save_message(
                    phone=phone,
                    content=response,
                    message_type="text",
                    is_from_bot=True
                )
            
            logger.info(f"🔵 [6/6] Enviando respuesta a WhatsApp...")
            try:
                result = await self.waha.send_text_message(phone, response)
                logger.info(f"🔵 [6/6] ✅ Respuesta enviada exitosamente")
                logger.debug(f"🔵 Resultado WAHA: {result}")
            except Exception as e:
                logger.error(f"❌ Error enviando a WhatsApp: {e}", exc_info=True)
                raise
            
            if message_id:
                await self.waha.mark_as_read(phone, message_id)
            
            logger.info(f"✅ Proceso completado para {phone}")
            
        except Exception as e:
            logger.error(f"❌ Error en process_text_message: {e}", exc_info=True)
    async def process_voice_message(
        self,
        phone: str,
        media_url: str,
        message_id: Optional[str] = None
    ) -> None:
        """
        Procesa un mensaje de voz
        
        Args:
            phone: Numero de telefono del cliente
            media_url: URL del archivo de audio
            message_id: ID del mensaje de WAHA
        """
        try:
            logger.info(f"Procesando nota de voz de {phone}")
            
            if not settings.enable_voice_messages:
                error_msg = "Lo siento, actualmente no puedo procesar mensajes de voz. Podrias escribirme?"
                await self.waha.send_text_message(phone, error_msg)
                return
            
            # Descargar audio
            audio_data = await self.waha.download_media({"mediaUrl": media_url})
            
            if not audio_data:
                error_msg = "No pude descargar tu nota de voz. Podrias enviarla de nuevo?"
                await self.waha.send_text_message(phone, error_msg)
                return
            
            # Mostrar que esta procesando
            await self.waha.send_typing(phone, duration=5)
            
            # Transcribir
            transcription = await self.whisper.transcribe_audio(
                audio_data,
                audio_format="ogg"
            )
            
            if not transcription:
                error_msg = "No pude entender tu nota de voz. Podrias repetir o escribirme?"
                await self.waha.send_text_message(phone, error_msg)
                return
            
            logger.info(f"Audio transcrito: {transcription}")
            
            # Procesar como mensaje de texto
            with get_db_context() as db:
                context_manager = ContextManager(db)
                
                # Guardar mensaje original (voz)
                context_manager.save_message(
                    phone=phone,
                    content=transcription,
                    message_type="voice",
                    is_from_bot=False,
                    waha_message_id=message_id
                )
                
                # Obtener contexto
                context = context_manager.get_or_create_context(phone)

                # Establecer contexto de cliente para tracking en logs
                set_client_context(phone, context.get('conversation_id'))

                # Procesar la transcripcion
                response = await self._process_intent(
                    phone=phone,
                    message=transcription,
                    context=context,
                    db=db
                )
                
                # Enviar respuesta
                if response:
                    await self.waha.send_text_message(phone, response)
                    context_manager.save_message(
                        phone=phone,
                        content=response,
                        message_type="text",
                        is_from_bot=True
                    )
            
        except Exception as e:
            logger.error(f"Error procesando voz: {e}", exc_info=True)
            try:
                error_msg = "Hubo un problema procesando tu nota de voz. Podrias escribirme?"
                await self.waha.send_text_message(phone, error_msg)
            except:
                pass
    
    async def process_image_message(
        self,
        phone: str,
        media_url: str,
        caption: str = "",
        message_id: Optional[str] = None
    ) -> None:
        """
        Procesa un mensaje con imagen
        
        Args:
            phone: Numero de telefono del cliente
            media_url: URL de la imagen
            caption: Texto que acompaña la imagen
            message_id: ID del mensaje de WAHA
        """
        try:
            logger.info(f"Procesando imagen de {phone}")
            
            if not settings.enable_image_messages:
                msg = "Recibi tu imagen. Por favor, describeme que necesitas por texto."
                await self.waha.send_text_message(phone, msg)
                return
            
            with get_db_context() as db:
                context_manager = ContextManager(db)
                
                # Guardar mensaje con imagen
                content = f"[Imagen enviada] {caption}" if caption else "[Imagen enviada]"
                context_manager.save_message(
                    phone=phone,
                    content=content,
                    message_type="image",
                    is_from_bot=False,
                    waha_message_id=message_id
                )
                
                # Si hay caption, procesarlo
                if caption:
                    context = context_manager.get_or_create_context(phone)

                    # Establecer contexto de cliente para tracking en logs
                    set_client_context(phone, context.get('conversation_id'))

                    response = await self._process_intent(
                        phone=phone,
                        message=caption,
                        context=context,
                        db=db
                    )
                    
                    if response:
                        await self.waha.send_text_message(phone, response)
                        context_manager.save_message(
                            phone=phone,
                            content=response,
                            message_type="text",
                            is_from_bot=True
                        )
                else:
                    # Sin caption, pedir mas informacion
                    msg = "Recibi tu imagen. En que puedo ayudarte?"
                    await self.waha.send_text_message(phone, msg)
            
        except Exception as e:
            logger.error(f"Error procesando imagen: {e}", exc_info=True)
    
    async def _process_intent(
        self,
        phone: str,
        message: str,
        context: Dict[str, Any],
        db: Session
    ) -> str:
        """
        Procesa el mensaje detectando la intencion y usando el orquestador
        """
        try:
            from app.core.orchestrator import Orchestrator, ConversationState
            
            conversation_state = context.get("conversation_state")
            
            # Si está recolectando slots, usar orquestador directamente
            if conversation_state == ConversationState.COLLECTING_SLOTS:
                orchestrator = Orchestrator(self.ollama, db)
                response = await orchestrator.process_message(message, context)
                return response
            
            # Si está idle, detectar intención primero
            intent_result = await self.intent_detector.detect_intent(
                message=message,
                context=context
            )
            
            intent = intent_result.get("intent")
            logger.info(f"Intencion detectada: {intent}")
            
            # Actualizar contexto con la intención
            context["current_intent"] = intent
            
            # Usar orquestador para manejar la intención
            orchestrator = Orchestrator(self.ollama, db)
            response = await orchestrator.process_message(message, context)
            
            return response
            
        except Exception as e:
            logger.error(f"Error procesando intencion: {e}", exc_info=True)
            return "Disculpa, tuve un problema. Podrias intentarlo de nuevo?"