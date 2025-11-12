from typing import Dict, Any, List, Optional
from loguru import logger
from app.clients.ollama_client import OllamaClient


class IntentDetector:
    """Detector de intenciones usando LLM"""
    
    # Intenciones soportadas
    INTENTS = {
        "greeting": {
            "name": "Saludo",
            "description": "El usuario saluda o inicia conversación",
            "examples": ["hola", "buenos días", "qué tal", "hey"]
        },
        "product_inquiry": {
            "name": "Consulta de Producto",
            "description": "El usuario pregunta por productos o servicios",
            "examples": ["qué productos tienen", "cuánto cuesta", "tienen laptops"]
        },
        "create_order": {
            "name": "Crear Orden",
            "description": "El usuario quiere COMPRAR, ORDENAR o AGREGAR productos nuevos (NO eliminar). Palabras clave: quiero, comprar, ordenar, necesito + producto",
            "examples": ["quiero comprar", "hacer un pedido", "necesito ordenar", "quiero una laptop"]
        },
        "check_order": {
            "name": "Consultar Orden",
            "description": "El usuario pregunta por el estado, ubicación o información de su pedido/orden existente. También cuando pregunta cuándo llega, dónde está, cómo va, etc.",
            "examples": [
                "dónde está mi pedido",
                "estado de mi orden",
                "cuándo llega",
                "cómo va mi compra",
                "ya enviaron",
                "información de mi pedido",
                "rastrear mi orden",
                "seguimiento",
                "ya llegó"
            ]
        },
        "remove_from_order": {
            "name": "Eliminar de Orden",
            "description": "El usuario quiere ELIMINAR, QUITAR o REMOVER productos de su orden/pedido confirmado existente. Palabras clave: eliminar, quitar, remover, borrar + de mi orden/pedido",
            "examples": [
                "quiero eliminar una laptop de mi orden",
                "quitar mouse de mi pedido",
                "eliminar un mouse de mi orden",
                "remover producto de mi orden",
                "borrar de mi orden",
                "ya no quiero el teclado en mi pedido"
            ]
        },
        "help": {
            "name": "Ayuda",
            "description": "El usuario necesita ayuda o no sabe qué hacer",
            "examples": ["ayuda", "qué puedes hacer", "no entiendo"]
        },
        "goodbye": {
            "name": "Despedida",
            "description": "El usuario se despide o termina la conversación",
            "examples": ["adiós", "gracias", "hasta luego", "eso es todo"]
        },
        "other": {
            "name": "Otro",
            "description": "No encaja en ninguna categoría específica",
            "examples": []
        }
    }
    
    def __init__(self, ollama_client: OllamaClient):
        self.ollama = ollama_client
    
    async def detect_intent(
        self,
        message: str,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Detecta la intención del mensaje"""
        try:
            logger.info(f"🔵 [IntentDetector] Iniciando detección...")
            logger.info(f"🔵 [IntentDetector] Mensaje: '{message[:50]}...'")
            
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 🚨 REGEX FALLBACK: Detectar casos críticos ANTES del LLM
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            import re
            message_lower = message.lower()
            
            # CASO 1: remove_from_order (MÁXIMA PRIORIDAD)
            remove_keywords = r'(eliminar|quitar|remover|borrar|sacar|cancelar)'
            order_keywords = r'(orden|pedido|compra)'
            
            if re.search(remove_keywords, message_lower) and re.search(order_keywords, message_lower):
                logger.info(f"🎯 [IntentDetector] ✅ REGEX MATCH: remove_from_order (bypassing LLM)")
                return {
                    "intent": "remove_from_order",
                    "confidence": 1.0,
                    "entities": {},
                    "detection_method": "regex_fallback"
                }
            
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # Continuar con detección LLM si no hay match de regex
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            
            # Construir prompt
            logger.info(f"🔵 [IntentDetector] Construyendo prompt para LLM...")
            prompt = self._build_intent_prompt(message, context)
            logger.debug(f"🔵 [IntentDetector] Prompt: {prompt[:200]}...")
            
            # Llamar a Ollama
            logger.info(f"🔵 [IntentDetector] Llamando a Ollama...")
            response = await self.ollama.generate(
                prompt=prompt,
                temperature=0.3,
                max_tokens=200
            )
            logger.info(f"🔵 [IntentDetector] Respuesta de Ollama recibida: {response[:100]}...")
            
            # Parsear respuesta
            logger.info(f"🔵 [IntentDetector] Parseando respuesta...")
            result = self._parse_response(response)
            result["detection_method"] = "llm"
            logger.info(f"🔵 [IntentDetector] ✅ Intención (LLM): {result.get('intent')} (confianza: {result.get('confidence')})")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ [IntentDetector] Error: {e}", exc_info=True)
            return {
                "intent": "other",
                "confidence": 0.0,
                "entities": {}
            }
        
    async def generate_response(
        self,
        intent_result: Dict[str, Any],
        message: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Genera una respuesta apropiada basada en la intención
        """
        intent = intent_result.get("intent")
        
        # Respuestas directas para intenciones simples
        if intent == "greeting":
            return await self._handle_greeting(context)
        
        elif intent == "goodbye":
            return await self._handle_goodbye(context)
        
        elif intent == "help":
            return await self._handle_help()
        
        # Intenciones que requieren procesamiento complejo
        elif intent == "product_inquiry":
            return await self._handle_product_inquiry(message, context, intent_result)
        
        elif intent == "create_order":
            return await self._handle_create_order(message, context, intent_result)
        
        elif intent == "check_order":
            return await self._handle_check_order(message, context, intent_result)
        
        else:
            return await self._handle_other(message, context)
    
    def _build_intent_prompt(
        self,
        message: str,
        context: Dict[str, Any]
    ) -> str:
        """Construye el prompt para detección de intención"""
        
        # Listar intenciones con ejemplos
        intents_list = []
        for key, info in self.INTENTS.items():
            examples_str = ", ".join([f'"{ex}"' for ex in info['examples'][:3]])
            intents_list.append(f"- {key}: {info['description']}\n  Ejemplos: {examples_str}")
        
        intents_text = "\n".join(intents_list)
        
        # Contexto de conversación
        conversation_context = ""
        if context.get("message_history"):
            recent = context["message_history"][-3:]
            conversation_context = "Mensajes recientes:\n" + "\n".join([
                f"{'Bot' if msg['is_from_bot'] else 'Usuario'}: {msg['content']}"
                for msg in recent
            ])
        
        prompt = f"""Eres un asistente de ventas por WhatsApp. Tu tarea es identificar la intención del usuario.

INTENCIONES DISPONIBLES:
{intents_text}

🚨 REGLA #1 - MÁXIMA PRIORIDAD (VERIFICAR PRIMERO):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Si el mensaje contiene CUALQUIERA de estas palabras:
   "eliminar", "quitar", "remover", "borrar", "sacar", "cancelar"
   
Y ADEMÁS menciona:
   "orden", "pedido", "compra" o "de mi orden/pedido"

→ ES **remove_from_order** SIN EXCEPCIONES

NO IMPORTA si también dice "quiero" o cualquier otra palabra.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Ejemplos de remove_from_order:
   ✓ "quiero eliminar un mouse de mi orden"
   ✓ "quiero eliminar el monitor de mi orden" 
   ✓ "quitar laptop de mi pedido"
   ✓ "eliminar teclado"
   ✓ "borrar de mi orden el mouse"
   ✓ "ya no quiero el mouse en mi pedido"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

REGLAS ADICIONALES:

2. **AGREGAR/COMPRAR productos** (create_order):
   - Si el mensaje contiene "quiero", "comprar", "ordenar", "necesito" + producto
   - Y NO contiene palabras de eliminación
   → create_order
   - Ejemplos: "quiero una laptop", "comprar mouse", "ordenar teclado"

3. **CONSULTAR orden** (check_order):
   - Si pregunta "dónde está", "cuándo llega", "estado", "cómo va"
   → check_order

{conversation_context}

MENSAJE DEL USUARIO:
"{message}"

Analiza el mensaje siguiendo las REGLAS CRÍTICAS en orden de prioridad.

Responde SOLO en formato JSON:
{{
    "intent": "nombre_de_la_intención",
    "confidence": 0.95,
    "entities": {{
        "product": "laptop",
        "quantity": 2
    }},
    "requires_action": true
}}"""
        
        return prompt
    
    async def _handle_greeting(self, context: Dict[str, Any]) -> str:
        """Maneja saludos"""
        customer_name = context.get("customer_name")
        
        if customer_name:
            greeting = f"Hola {customer_name}!"
        else:
            greeting = "Hola!"
        
        response = f"{greeting}\n\n"
        response += "Soy tu asistente de ventas. Puedo ayudarte con:\n"
        response += "- Consultar productos y precios\n"
        response += "- Realizar pedidos\n"
        response += "- Revisar el estado de tus ordenes\n\n"
        response += "En que puedo ayudarte hoy?"
        
        return response
    
    async def _handle_goodbye(self, context: Dict[str, Any]) -> str:
        """Maneja despedidas"""
        response = "Hasta pronto!\n\n"
        response += "Si necesitas algo mas, solo escribeme. Que tengas un excelente dia!"
        return response
    
    async def _handle_help(self) -> str:
        """Maneja solicitudes de ayuda"""
        response = "Con gusto te ayudo!\n\n"
        response += "Puedo asistirte con:\n\n"
        response += "- Productos: Preguntame por nuestros productos disponibles\n"
        response += "- Precios: Consulta precios y ofertas\n"
        response += "- Pedidos: Te ayudo a crear una orden paso a paso\n"
        response += "- Seguimiento: Revisa el estado de tus pedidos\n\n"
        response += "Solo dime que necesitas y te guiare en el proceso."
        return response
    
    async def _handle_product_inquiry(
        self,
        message: str,
        context: Dict[str, Any],
        intent_result: Dict[str, Any]
    ) -> str:
        """Maneja consultas de productos"""
        entities = intent_result.get("entities", {})
        product = entities.get("product", "")
        
        if product:
            response = f"Entiendo que te interesa {product}.\n\n"
            response += "En este momento estoy configurando el catalogo completo, "
            response += "pero puedo ayudarte a hacer un pedido.\n\n"
            response += f"Te gustaria proceder con una orden de {product}?"
            return response
        else:
            response = "Claro! Tenemos una variedad de productos disponibles.\n\n"
            response += "Que tipo de producto te interesa? Por ejemplo:\n"
            response += "- Laptops\n"
            response += "- Tablets\n"
            response += "- Smartphones\n"
            response += "- Accesorios"
            return response
    
    async def _handle_create_order(
        self,
        message: str,
        context: Dict[str, Any],
        intent_result: Dict[str, Any]
    ) -> str:
        """Maneja creación de órdenes"""
        response = "Perfecto! Te ayudo a crear tu orden.\n\n"
        response += "Para comenzar, necesito algunos datos. Vamos paso a paso.\n\n"
        response += "Que producto te gustaria ordenar?"
        return response
    
    async def _handle_check_order(
        self,
        message: str,
        context: Dict[str, Any],
        intent_result: Dict[str, Any]
    ) -> str:
        """Maneja consulta de órdenes"""
        response = "Para consultar tu orden, necesito tu numero de orden.\n\n"
        response += "Tienes el numero de orden a mano? Tiene este formato: #12345"
        return response
    
    async def _handle_other(
        self,
        message: str,
        context: Dict[str, Any]
    ) -> str:
        """Maneja mensajes que no encajan en categorías"""
        try:
            conversation_summary = "\n".join([
                f"{'Bot' if msg['is_from_bot'] else 'Usuario'}: {msg['content']}"
                for msg in context.get("message_history", [])[-5:]
            ])
            
            prompt = f"""Eres un asistente de ventas amigable por WhatsApp.

CONVERSACION PREVIA:
{conversation_summary}

MENSAJE ACTUAL DEL USUARIO:
"{message}"

Responde de forma natural, amigable y util. Si no entiendes bien, pide clarificación.
Manten la respuesta breve (maximo 3 lineas).

IMPORTANTE: No inventes informacion sobre productos o precios. Si te preguntan algo especifico que no sabes, reconocelo."""
            
            result = await self.ollama.generate(
                prompt=prompt,
                temperature=0.7
            )
            
            return result.get("response", "").strip()
            
        except Exception as e:
            logger.error(f"Error generando respuesta: {e}")
            return "Disculpa, no estoy seguro de entender. Podrias reformular tu pregunta?"