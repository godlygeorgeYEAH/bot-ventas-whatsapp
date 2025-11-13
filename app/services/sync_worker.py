"""
Worker síncrono que procesa mensajes fuera del event loop
"""
import queue
import threading
import requests
from loguru import logger
from typing import Dict, Any
from config.database import get_db_context
from app.core.context_manager import ContextManager


class SyncMessageWorker:
    """Worker que procesa mensajes de forma completamente síncrona"""
    
    def __init__(self):
        self.queue = queue.Queue()
        self.worker_thread = None
        self.running = False
    
    def start(self):
        """Inicia el worker thread"""
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        logger.info("✅ SyncMessageWorker iniciado")
    
    def stop(self):
        """Detiene el worker thread"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
    
    def enqueue_message(self, phone: str, message: str, message_id: str = None):
        """Agrega un mensaje a la cola para procesar"""
        self.queue.put({
            "phone": phone,
            "message": message,
            "message_id": message_id
        })
        logger.info(f"📥 Mensaje encolado para {phone}")
    
    def _worker_loop(self):
        """Loop principal del worker"""
        logger.info("🔄 Worker loop iniciado")
        
        while self.running:
            try:
                # Esperar mensaje (timeout 1s para poder verificar self.running)
                try:
                    data = self.queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # Procesar mensaje
                self._process_message_sync(
                    data["phone"],
                    data["message"],
                    data.get("message_id")
                )
                
                self.queue.task_done()
                
            except Exception as e:
                logger.error(f"❌ Error en worker loop: {e}", exc_info=True)
    
    def _process_message_sync(self, phone: str, message: str, message_id: str = None):
        """Procesa un mensaje de forma completamente síncrona"""
        try:
            logger.info(f"🔵 [Worker] Procesando mensaje de {phone}: '{message[:50]}...'")
            
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 1. Guardar mensaje en BD
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            with get_db_context() as db:
                context_manager = ContextManager(db)
                context_manager.save_message(
                    phone=phone,
                    content=message,
                    message_type="text",
                    is_from_bot=False,
                    waha_message_id=message_id
                )
            
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 2. Obtener contexto del usuario
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            with get_db_context() as db:
                context_manager = ContextManager(db)
                user_context = context_manager.get_or_create_context(phone)
                module_context = context_manager.get_module_context(phone)
            
            logger.info(f"🔵 [Worker] Contexto leído de BD: estado={module_context.get('conversation_state')}, módulo={module_context.get('current_module')}, slot={module_context.get('current_slot')}")
            logger.info(f"📦 [Worker] FLAGS: wait_confirm={module_context.get('waiting_location_confirmation')}, "
                        f"prev_offered={module_context.get('previous_location_offered')}")
            
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 3. Verificar si hay un módulo activo EN PROCESO
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            from app.core.module_registry import get_module_registry
            registry = get_module_registry()

            # CASO ESPECIAL 1: Si waiting_offer_response=True, forzar OfferProductModule
            if module_context.get('waiting_offer_response') and not module_context.get('current_module'):
                logger.info(f"🎁 [Worker] Detectado waiting_offer_response=True sin current_module, forzando OfferProductModule")
                module_context['current_module'] = 'OfferProductModule'

            # CASO ESPECIAL 2: Si current_module=CheckoutModule Y conversation_state=collecting_slots, mantener CheckoutModule
            # (solo si está EN PROCESO, no si es el inicio)
            if (module_context.get('current_module') == 'CheckoutModule' and
                module_context.get('conversation_state') == 'collecting_slots'):
                logger.info(f"🛒 [Worker] CheckoutModule en proceso de slot filling, manteniéndolo activo")

            active_module = registry.get_module_by_context(module_context)

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # ⚡ PRIORIDAD: Detectar intents de ALTA PRIORIDAD incluso con módulo activo
            # Algunos intents deben interrumpir el flujo actual (ej: cancel_order)
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            high_priority_intent = None
            if active_module:
                # Detectar intención para verificar si es de alta prioridad
                intent_result = self._detect_intent_with_ollama(message)
                detected_intent = intent_result.get("intent", "other")

                # Lista de intents que deben interrumpir cualquier flujo activo
                high_priority_intents = ["cancel_order"]

                if detected_intent in high_priority_intents:
                    logger.info(f"🚨 [Worker] Intent de ALTA PRIORIDAD detectado: {detected_intent} - Interrumpiendo módulo actual")
                    high_priority_intent = detected_intent

                    # Buscar módulo para este intent
                    target_module = registry.find_module_for_intent(detected_intent, module_context)

                    if target_module:
                        logger.info(f"🎯 [Worker] Módulo de alta prioridad encontrado: {target_module.name}")

                        # Usar módulo de alta prioridad (reemplaza active_module)
                        result = target_module.handle(
                            message=message,
                            context=module_context,
                            phone=phone
                        )

                        # Actualizar contexto
                        with get_db_context() as db:
                            context_manager = ContextManager(db)
                            context_manager.update_module_context(
                                phone=phone,
                                module_name=target_module.name,
                                context_updates=result.get('context_updates', {})
                            )

                        response = result.get('response', '')

                        # Saltar el procesamiento normal del módulo activo
                        active_module = None

            if active_module:
                logger.info(f"🎯 [Worker] Módulo activo detectado: {active_module.name}")
                
                # 🐛 DEBUG: Verificar tipo de slots_data antes de pasar al módulo
                slots_data_type = type(module_context.get('slots_data', {})).__name__
                logger.debug(f"🐛 [Worker] slots_data type: {slots_data_type}, value: {module_context.get('slots_data')}")
                
                # Usar módulo activo
                result = active_module.handle(
                    message=message,
                    context=module_context,
                    phone=phone
                )
                
                # Actualizar contexto
                context_updates = result.get('context_updates', {})
                logger.info(f"📥 [Worker] Guardando updates: {list(context_updates.keys())}")
                logger.info(f"   🔑 current_module en updates: {context_updates.get('current_module')}")
                
                with get_db_context() as db:
                    context_manager = ContextManager(db)
                    context_manager.update_module_context(
                        phone=phone,
                        module_name=active_module.name,
                        context_updates=context_updates
                    )
                
                logger.info(f"✅ [Worker] Contexto guardado en BD")
                
                response = result.get('response', '')
                
                # Si el módulo completó, limpiar contexto
                if result.get('context_updates', {}).get('conversation_state') == 'completed':
                    with get_db_context() as db:
                        context_manager = ContextManager(db)
                        context_manager.clear_module_context(phone)
                
            else:
                # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                # 4. No hay módulo activo, detectar intención
                # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                logger.info(f"🔍 [Worker] No hay módulo activo, detectando intención...")
                intent_result = self._detect_intent_with_ollama(message)
                
                intent = intent_result.get("intent", "other")
                confidence = intent_result.get("confidence", 0.0)
                
                logger.info(f"✅ [Worker] Intención detectada: {intent} (confianza: {confidence})")
                
                # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                # 5. Buscar módulo para esta intención
                # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                target_module = registry.find_module_for_intent(intent, module_context)
                
                if target_module:
                    logger.info(f"🎯 [Worker] Módulo encontrado para intent '{intent}': {target_module.name}")
                    
                    # Usar módulo
                    result = target_module.handle(
                        message=message,
                        context=module_context,
                        phone=phone
                    )
                    
                    # Actualizar contexto
                    with get_db_context() as db:
                        context_manager = ContextManager(db)
                        context_manager.update_module_context(
                            phone=phone,
                            module_name=target_module.name,
                            context_updates=result.get('context_updates', {})
                        )
                    
                    response = result.get('response', '')
                else:
                    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                    # 6. No hay módulo, usar generación normal
                    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                    logger.info(f"💬 [Worker] No hay módulo para '{intent}', usando respuesta genérica...")
                    
                    additional_context = {
                        "intent": intent,
                        "user_state": user_context.get('conversation_state', 'idle'),
                        "user_name": user_context.get('customer_name', None),
                    }
                    
                    response = self._generate_response_with_ollama(
                        message=message,
                        intent=intent,
                        context=additional_context
                    )
            
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 7. Guardar respuesta del bot (si hay respuesta)
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            if response is not None:
                with get_db_context() as db:
                    context_manager = ContextManager(db)
                    context_manager.save_message(
                        phone=phone,
                        content=response,
                        message_type="text",
                        is_from_bot=True
                    )
            
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 8. Enviar por WhatsApp (si hay respuesta)
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            if response is None:
                # Respuesta None indica que el mensaje ya fue enviado (ej: ofrecimiento con imagen)
                logger.info(f"ℹ️ [Worker] Respuesta es None, mensaje ya enviado previamente")
            else:
                from config.settings import settings
                from app.clients.waha_client import WAHAClient
                
                chat_id = phone if "@c.us" in phone else f"{phone}@c.us"
                waha_client = WAHAClient()
                
                waha_response = requests.post(
                    f"{settings.waha_base_url}/api/sendText",
                    json={
                        "chatId": chat_id,
                        "text": response,
                        "session": settings.waha_session_name
                    },
                    headers={"X-Api-Key": settings.waha_api_key},
                    timeout=10.0
                )
                
                waha_response.raise_for_status()
                logger.info(f"✅ [Worker] Respuesta enviada a {phone}")
            
        except Exception as e:
            logger.error(f"❌ [Worker] Error procesando mensaje: {e}", exc_info=True)

    def _detect_intent_with_ollama(self, message: str) -> dict:
        """Detecta la intención usando Ollama (llamada síncrona al proxy)"""
        try:
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 🚨 REGEX FALLBACK: Detectar casos críticos ANTES del LLM
            # El regex es rápido y confiable para patrones obvios
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            import re
            message_lower = message.lower()

            # CASO 1: cancel_order (MÁXIMA PRIORIDAD)
            # Detectar cuando usuario quiere cancelar TODA la orden (no solo un producto)
            cancel_keywords = r'(cancel|anul|ya\s+no\s+quier|no\s+quier|mejor\s+no|desist)'
            order_keywords = r'(orden|ordenar|ordeno|pedido|pedir|pido|compra|comprar|compro)'

            # Detectar si menciona cancelar/anular la orden completa
            if re.search(cancel_keywords, message_lower) and re.search(order_keywords, message_lower):
                # Verificar que NO mencione productos específicos (esto sería remove_from_order)
                product_indicators = r'(el |la |los |las |este |ese |producto|item|artículo)'

                # Si NO menciona productos específicos, es cancel_order
                if not re.search(product_indicators + r'.{0,20}' + cancel_keywords, message_lower):
                    logger.info(f"🎯 [Worker] ✅ REGEX MATCH: cancel_order (bypassing LLM)")
                    return {
                        "intent": "cancel_order",
                        "confidence": 1.0,
                        "detection_method": "regex_fallback"
                    }

            # CASO 2: remove_from_order
            remove_keywords = r'(elimin|quit|remov|borr|sac|cancel)'
            order_keywords = r'(orden|pedido|compra)'

            if re.search(remove_keywords, message_lower) and re.search(order_keywords, message_lower):
                logger.info(f"🎯 [Worker] ✅ REGEX MATCH: remove_from_order (bypassing LLM)")
                return {
                    "intent": "remove_from_order",
                    "confidence": 1.0,
                    "detection_method": "regex_fallback"
                }

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # Continuar con detección LLM si no hay match de regex
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

            prompt = f"""Clasifica el mensaje en UNA de estas categorías. Responde SOLO con la palabra, sin explicaciones.

CATEGORÍAS:
- greeting (saludos)
- goodbye (despedidas)
- create_order (quiere comprar)
- check_order (consultar pedido)
- cancel_order (cancelar orden completa)
- remove_from_order (quitar producto)
- other (otro)

EJEMPLOS:
Usuario: "hola" → greeting
Usuario: "quiero comprar" → create_order
Usuario: "cancela mi orden" → cancel_order
Usuario: "elimina el mouse" → remove_from_order

Usuario: "{message}"
Categoría:"""

            logger.debug(f"🔵 [Worker] Enviando prompt al LLM para detección de intención")

            response = requests.post(
                'http://localhost:5001/generate',
                json={
                    "model": "llama3.2:latest",
                    "prompt": prompt,
                    "temperature": 0.0,  # Completamente determinístico
                    "max_tokens": 5,     # Máximo 5 tokens para una palabra
                    "stop": ["\n", ".", ",", " -"]  # Detener en nueva línea o puntuación
                },
                timeout=30.0
            )
            
            response.raise_for_status()
            result = response.json()
            
            if result.get("success"):
                intent_text = result["response"].strip().lower()

                # Tomar solo la primera palabra (en caso de que el LLM genere más texto)
                import string
                intent_text = intent_text.split()[0] if intent_text.split() else intent_text

                # Limpiar respuesta (remover puntuación EXCEPTO guiones bajos)
                # Crear lista de puntuación sin el guion bajo
                punctuation_without_underscore = string.punctuation.replace('_', '')
                intent_text = intent_text.translate(str.maketrans('', '', punctuation_without_underscore)).strip()

                valid_intents = ["greeting", "goodbye", "create_order", "check_order", "cancel_order", "remove_from_order", "other"]

                # Primero buscar match exacto
                if intent_text in valid_intents:
                    logger.info(f"✅ [Worker] LLM detectó intención: {intent_text}")
                    return {
                        "intent": intent_text,
                        "confidence": 0.95,
                        "detection_method": "llm"
                    }

                # Si no hay match exacto, buscar normalizando guiones bajos (createorder vs create_order)
                intent_normalized = intent_text.replace('_', '')
                for valid_intent in valid_intents:
                    valid_normalized = valid_intent.replace('_', '')
                    if intent_normalized == valid_normalized:
                        logger.info(f"✅ [Worker] LLM respondió: '{intent_text}' → Match normalizado: {valid_intent}")
                        return {
                            "intent": valid_intent,
                            "confidence": 0.95,
                            "detection_method": "llm"
                        }

                # Si no hay match, buscar substring
                for valid_intent in valid_intents:
                    if valid_intent in intent_text or intent_text in valid_intent:
                        logger.info(f"✅ [Worker] LLM respondió: '{intent_text}' → Match parcial: {valid_intent}")
                        return {
                            "intent": valid_intent,
                            "confidence": 0.85,
                            "detection_method": "llm"
                        }

                # Si no hay match, usar 'other'
                logger.warning(f"⚠️ [Worker] LLM respondió valor inesperado: '{intent_text}', usando 'other'")
                return {
                    "intent": "other",
                    "confidence": 0.5,
                    "detection_method": "llm_fallback"
                }
            else:
                raise Exception(f"Ollama proxy error: {result.get('error')}")
            
        except Exception as e:
            logger.error(f"❌ [Worker] Error llamando a Ollama: {e}")
            return {
                "intent": "other",
                "confidence": 0.0,
                "detection_method": "error"
            }

    def _generate_response_with_ollama(
        self, 
        message: str, 
        intent: str, 
        context: dict = None
    ) -> str:
        """
        Genera una respuesta usando Ollama con contexto dinámico
        
        Args:
            message: Mensaje del usuario
            intent: Intención detectada
            context: Diccionario con contexto adicional (slots, datos de módulos, etc)
        """
        try:
            # Construir información de contexto para el prompt
            context = context or {}
            
            context_info = ""
            if context.get("user_name"):
                context_info += f"- Nombre del usuario: {context['user_name']}\n"
            
            if context.get("user_state") and context["user_state"] != "idle":
                context_info += f"- Estado de la conversación: {context['user_state']}\n"
            
            # Los módulos pueden agregar más información aquí
            if context.get("order_info"):
                context_info += f"- Información de pedido: {context['order_info']}\n"
            
            if context.get("product_catalog"):
                context_info += f"- Productos disponibles: {', '.join(context['product_catalog'])}\n"
            
            if context.get("slots_filled"):
                context_info += f"- Datos recopilados: {context['slots_filled']}\n"
            
            # Construir prompt
            prompt = f"""Eres un asistente de ventas profesional por WhatsApp. Tu trabajo es responder de manera amigable y útil.

    INTENCIÓN DETECTADA: {intent}

    MENSAJE DEL USUARIO: "{message}"

    {'CONTEXTO ADICIONAL:\n' + context_info if context_info else ''}

    INSTRUCCIONES:
    - greeting: Saluda cordialmente y ofrece ayuda
    - goodbye: Despídete amablemente
    - create_order: Ayuda al usuario a crear un pedido, pregunta qué producto necesita
    - check_order: Ayuda a consultar el estado de un pedido, pide el número de orden
    - other: Responde de manera natural y continua con la conversacion del usuario

    Genera una respuesta natural, amigable y concisa (máximo 2-3 oraciones).
    No uses emojis excesivos, máximo 1-2 por mensaje."""

            logger.debug(f"🔵 [Worker] Prompt para respuesta:\n{prompt}")
            
            response = requests.post(
                'http://localhost:5001/generate',
                json={
                    "model": "llama3.2:latest",
                    "prompt": prompt,
                    "temperature": 0.7,
                    "max_tokens": 200
                },
                timeout=30.0
            )
            
            response.raise_for_status()
            result = response.json()
            
            if result.get("success"):
                generated_response = result["response"].strip()
                logger.info(f"✅ [Worker] Respuesta de Ollama: '{generated_response[:100]}...'")
                return generated_response
            else:
                raise Exception(f"Ollama proxy error: {result.get('error')}")
            
        except Exception as e:
            logger.error(f"❌ [Worker] Error generando respuesta con Ollama: {e}")
            
            # Fallback: respuesta por defecto según intención
            fallback_responses = {
                "greeting": "¡Hola! ¿En qué puedo ayudarte hoy?",
                "goodbye": "¡Hasta luego! Que tengas un excelente día.",
                "create_order": "Puedo ayudarte a hacer un pedido. ¿Qué producto te interesa?",
                "check_order": "Puedo ayudarte a consultar tu pedido. ¿Tienes el número de orden?",
                "other": "Gracias por tu mensaje. ¿Puedes darme más detalles?"
            }
            
            fallback = fallback_responses.get(intent, fallback_responses["other"])
            logger.warning(f"⚠️ [Worker] Usando respuesta fallback: '{fallback}'")
            return fallback
# Instancia global
sync_worker = SyncMessageWorker()