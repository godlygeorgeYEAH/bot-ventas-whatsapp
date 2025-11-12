"""
Extractor de valores de slots desde mensajes de usuarios
"""
from typing import Optional, Dict, Any
import re
from datetime import datetime
from loguru import logger
import requests

from app.core.slots.slot_definition import SlotType


class SlotExtractor:
    """
    Extrae valores de diferentes tipos de slots desde mensajes de texto
    """
    
    def extract(
        self, 
        slot_type: SlotType, 
        message: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Extrae un valor según el tipo de slot
        
        Args:
            slot_type: Tipo de slot a extraer
            message: Mensaje del usuario
            context: Contexto adicional (puede incluir 'is_product_name', 'choices', etc.)
            
        Returns:
            Valor extraído o None si no se pudo extraer
        """
        extractors = {
            SlotType.TEXT: self._extract_text,
            SlotType.NUMBER: self._extract_number,
            SlotType.EMAIL: self._extract_email,
            SlotType.PHONE: self._extract_phone,
            SlotType.DATE: self._extract_date,
            SlotType.CHOICE: self._extract_choice,
            SlotType.ADDRESS: self._extract_address,
            SlotType.LOCATION: self._extract_location,
            SlotType.CONFIRMATION: self._extract_confirmation,
        }
        
        extractor = extractors.get(slot_type)
        if not extractor:
            logger.error(f"❌ [SlotExtractor] No hay extractor para tipo: {slot_type}")
            return None
            
        try:
            # Pasar contexto al extractor si es necesario
            if context and 'is_product_name' in context:
                result = extractor(message, is_product_name=context.get('is_product_name', False))
            else:
                result = extractor(message)
            
            if result:
                logger.info(f"✅ [SlotExtractor] Extraído {slot_type}: '{result}'")
            else:
                logger.warning(f"⚠️ [SlotExtractor] No se pudo extraer {slot_type} de: '{message}'")
            return result
        except Exception as e:
            logger.error(f"❌ [SlotExtractor] Error extrayendo {slot_type}: {e}")
            return None
    
    def _extract_text(self, message: str, is_product_name: bool = False) -> Optional[str]:
        """
        Extrae texto usando LLM para identificar inteligentemente el producto/item mencionado
        
        Args:
            message: Mensaje del usuario
            is_product_name: Si True, usa LLM para extraer nombre de producto
        """
        # Si es un nombre de producto, usar LLM para extracción inteligente
        if is_product_name:
            return self._extract_product_name_with_llm(message)
        
        # Para otros tipos de texto, usar fallback simple
        return self._extract_text_fallback(message)
    
    def _extract_product_name_with_llm(self, message: str) -> Optional[str]:
        """
        Extrae nombre(s) de producto(s) usando LLM con prompt mejorado
        
        Retorna:
            - String con productos separados por comas si hay múltiples
            - String con un solo producto si hay uno
            - None si no hay productos
        """
        try:
            # Obtener lista de productos disponibles para contexto
            available_products = self._get_available_products_list()
            
            prompt = f"""Eres un asistente experto en extraer nombres de productos de mensajes de clientes.

TAREA: Extrae el nombre o nombres de productos que el cliente menciona (para comprar, agregar, eliminar, etc.).

REGLAS ESTRICTAS:
1. Extrae ÚNICAMENTE el nombre del producto (sustantivo principal)
2. NO incluyas verbos ni partes de verbos: quiero, deseo, necesito, comprar, adquirir, ordenar, orden (del verbo ordenar), eliminar, quitar, remover
3. NO incluyas artículos: un, una, el, la, los, las
4. NO incluyas saludos: hola, buenos días, gracias
5. NO incluyas palabras de contexto: orden, pedido, compra, carrito
6. NO incluyas palabras de relleno: por favor, me gustaría, podría, de mi
7. Si hay marca y modelo, inclúyelos: "laptop HP" no solo "laptop"
8. Si el cliente menciona MÚLTIPLES productos, sepáralos por comas
9. Responde SOLO con el/los nombre(s) del producto, sin explicaciones
10. Si el mensaje no menciona un producto claro, responde "NO_PRODUCTO"
11. IMPORTANTE: Si el mensaje dice "ordenar una [PRODUCTO]", extrae solo [PRODUCTO], NO "orden"

PRODUCTOS DISPONIBLES (para referencia):
{available_products}

EJEMPLOS CORRECTOS (COMPRAR/ORDENAR):
Mensaje: "Hola! Quiero comprar una laptop"
Producto: laptop

Mensaje: "Quiero ordenar una laptop"
Producto: laptop

Mensaje: "Quisiera ordenar un mouse"
Producto: mouse

Mensaje: "Quiero una laptop y un mouse"
Producto: laptop, mouse

Mensaje: "Me gustaría una laptop HP y auriculares"
Producto: laptop HP, auriculares

EJEMPLOS CORRECTOS (ELIMINAR/QUITAR):
Mensaje: "quiero eliminar la laptop de mi orden"
Producto: laptop

Mensaje: "quiero eliminar la dell de mi orden"
Producto: dell

Mensaje: "quitar el mouse de mi pedido"
Producto: mouse

Mensaje: "remover laptop HP 15 de la orden"
Producto: laptop HP 15

EJEMPLOS INCORRECTOS:
Mensaje: "Hola, buenos días"
Producto: NO_PRODUCTO

Mensaje: "¿cómo está mi orden?"
Producto: NO_PRODUCTO

EJEMPLOS DE ERRORES COMUNES (EVITAR):
❌ Mensaje: "quiero ordenar una laptop"
   Respuesta incorrecta: orden
   Respuesta correcta: laptop

❌ Mensaje: "quiero eliminar la dell de mi orden"
   Respuesta incorrecta: orden
   Respuesta correcta: dell

MENSAJE DEL CLIENTE: "{message}"
Producto:"""

            logger.info(f"🔵 [SlotExtractor] Usando LLM para extraer producto de: '{message[:50]}...'")
            
            response = requests.post(
                'http://localhost:5001/generate',
                json={
                    "model": "llama3.2:latest",
                    "prompt": prompt,
                    "temperature": 0.1,  # Baja temperatura para respuestas más consistentes
                    "max_tokens": 30  # Reducido para respuestas más cortas
                },
                timeout=20.0
            )
            
            response.raise_for_status()
            result = response.json()
            
            if result.get("success"):
                extracted = result["response"].strip()
                
                # Limpiar respuesta
                extracted = extracted.lower().strip()
                
                # Remover comillas si las hay
                extracted = extracted.strip('"').strip("'")
                
                # Invalidar respuestas no válidas
                invalid_responses = [
                    '', 'none', 'null', 'n/a', 'no hay', 'ninguno',
                    'no se menciona', 'no especificado', 'no_producto',
                    'no producto', 'no hay producto', 'no menciona producto'
                ]
                
                # Verificar que no sea una respuesta inválida
                if extracted and extracted not in invalid_responses:
                    # Verificar que no sea solo un saludo o palabra de relleno
                    stop_words_only = all(word in [
                        'hola', 'buenos', 'días', 'tardes', 'noches',
                        'gracias', 'por', 'favor', 'quiero', 'deseo',
                        'necesito', 'comprar', 'adquirir', 'ordenar'
                    ] for word in extracted.split())
                    
                    if not stop_words_only and len(extracted) >= 2:
                        logger.info(f"✅ [SlotExtractor] LLM extrajo producto: '{message[:50]}...' → '{extracted}'")
                        return extracted
                    else:
                        logger.warning(f"⚠️ [SlotExtractor] LLM extrajo solo palabras de relleno: '{extracted}'")
                else:
                    logger.warning(f"⚠️ [SlotExtractor] LLM no pudo extraer producto válido: '{extracted}'")
                
                # Si el LLM falla, intentar fallback
                logger.info(f"🔄 [SlotExtractor] Intentando fallback después de LLM...")
                return self._extract_text_fallback(message)
                
        except requests.exceptions.Timeout:
            logger.error(f"⏱️ [SlotExtractor] Timeout esperando respuesta del LLM")
            return self._extract_text_fallback(message)
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ [SlotExtractor] Error de conexión con LLM: {e}")
            return self._extract_text_fallback(message)
        except Exception as e:
            logger.error(f"❌ [SlotExtractor] Error usando LLM para extraer producto: {e}")
            return self._extract_text_fallback(message)
    
    def _get_available_products_list(self) -> str:
        """
        Obtiene lista de productos disponibles para contexto del LLM
        """
        try:
            from config.database import get_db_context
            from app.services.product_service import ProductService
            
            with get_db_context() as db:
                product_service = ProductService(db)
                products = product_service.get_all_products(only_available=True)
                
                if products:
                    # Limitar a 20 productos para no saturar el prompt
                    product_names = [p.name for p in products[:20]]
                    return ", ".join(product_names)
                else:
                    return "laptop, mouse, teclado, monitor, auriculares"
        except Exception as e:
            logger.debug(f"⚠️ [SlotExtractor] No se pudo obtener lista de productos: {e}")
            return "laptop, mouse, teclado, monitor, auriculares"
        
    def _extract_text_fallback(self, message: str) -> Optional[str]:
        """
        Fallback simple si el LLM falla
        """
        # Limpiar mensaje
        cleaned = message.lower().strip()
        
        # Palabras a remover (más completo)
        stop_words = [
            'quiero', 'deseo', 'necesito', 'busco', 'me', 'gustaría',
            'comprar', 'adquirir', 'conseguir', 'obtener', 'ordenar',
            'pedir', 'solicitar', 'encargar',
            'un', 'una', 'unos', 'unas', 'el', 'la', 'los', 'las',
            'hola', 'buenos', 'días', 'tardes', 'noches',
            'por', 'favor', 'ayuda', 'para', 'de', 'del', 'a', 'al',
            'que', 'con', 'en', 'y', 'o'
        ]
        
        # Remover stop words y números
        words = cleaned.split()
        filtered_words = []
        for w in words:
            # Saltar números puros
            if w.isdigit():
                continue
            # Saltar stop words
            if w not in stop_words:
                filtered_words.append(w)
        
        result = ' '.join(filtered_words).strip()
        
        if result:
            logger.info(f"🧹 [SlotExtractor] Fallback extrajo: '{message}' → '{result}'")
            return result
        
        return None
    
    def _extract_number(self, message: str) -> Optional[str]:
        """
        Extrae un número del mensaje
        Detecta tanto números escritos como palabras (una, uno, un)
        """
        message_lower = message.lower()
        
        # Detectar palabras que significan "1"
        uno_patterns = [
            r'\buna\b',      # "quiero una laptop"
            r'\buno\b',      # "quiero uno"
            r'\bun\b',       # "quiero un mouse"
        ]
        
        for pattern in uno_patterns:
            if re.search(pattern, message_lower):
                logger.info(f"✅ [SlotExtractor] Detectado 'una/uno/un' → cantidad = 1")
                return 1
        
        # Buscar números escritos en el mensaje
        numbers = re.findall(r'\b\d+\b', message)
        if numbers:
            return int(numbers[0])
        
        return None
    
    def _extract_email(self, message: str) -> Optional[str]:
        """
        Extrae un email del mensaje
        """
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, message)
        if emails:
            return emails[0].lower()
        return None
    
    def _extract_phone(self, message: str) -> Optional[str]:
        """
        Extrae un teléfono del mensaje
        Soporta formatos colombianos: 3001234567, 300-123-4567, +57 300 123 4567
        """
        # Remover espacios y caracteres especiales
        cleaned = re.sub(r'[^\d+]', '', message)
        
        # Buscar número colombiano (10 dígitos empezando con 3)
        if re.match(r'^3\d{9}$', cleaned):
            return cleaned
        
        # Buscar número con código de país (+57)
        if re.match(r'^\+?57?3\d{9}$', cleaned):
            # Normalizar a formato sin +57
            return re.sub(r'^\+?57', '', cleaned)
        
        return None
    
    def _extract_date(self, message: str) -> Optional[str]:
        """
        Extrae una fecha del mensaje
        Soporta: DD/MM/YYYY, DD-MM-YYYY, "hoy", "mañana"
        """
        message_lower = message.lower()
        
        # Palabras clave para fechas relativas
        if 'hoy' in message_lower:
            return datetime.now().strftime('%Y-%m-%d')
        
        if 'mañana' in message_lower or 'manana' in message_lower:
            tomorrow = datetime.now().replace(day=datetime.now().day + 1)
            return tomorrow.strftime('%Y-%m-%d')
        
        # Buscar fechas en formato DD/MM/YYYY o DD-MM-YYYY
        date_pattern = r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b'
        dates = re.findall(date_pattern, message)
        if dates:
            day, month, year = dates[0]
            try:
                date = datetime(int(year), int(month), int(day))
                return date.strftime('%Y-%m-%d')
            except ValueError:
                return None
        
        return None
    
    def _extract_choice(self, message: str) -> Optional[str]:
        """
        Extrae una elección del mensaje
        Busca números (1, 2, 3) o palabras clave
        """
        message_lower = message.lower().strip()
        
        # Si el mensaje es solo un número
        if message_lower.isdigit():
            return message_lower
        
        # Buscar número al inicio
        number_match = re.match(r'^(\d+)', message_lower)
        if number_match:
            return number_match.group(1)
        
        # Buscar palabras clave comunes
        choice_map = {
            'efectivo': 'efectivo',
            'tarjeta': 'tarjeta',
            'transferencia': 'transferencia',
            'si': 'si',
            'sí': 'si',
            'no': 'no',
        }
        
        for keyword, value in choice_map.items():
            if keyword in message_lower:
                return value
        
        return None
    
    def _extract_address(self, message: str) -> Optional[str]:
        """
        Extrae una dirección del mensaje
        Busca patrones como "Calle X #Y-Z" o texto largo que parezca dirección
        """
        # Si el mensaje tiene más de 10 caracteres y contiene números, probablemente es una dirección
        if len(message) > 10 and re.search(r'\d', message):
            # Limpiar un poco
            address = message.strip()
            
            # Capitalizar primera letra de cada palabra para mejor formato
            # pero solo si no tiene formato especial de direcciones colombianas
            if not re.search(r'#\d+-\d+', address):
                address = ' '.join(word.capitalize() for word in address.split())
            
            return address
        
        return None
    
    def _extract_location(self, message: str) -> Optional[str]:
        """
        Extrae coordenadas GPS de un mensaje de ubicación
        
        Formato esperado de WhatsApp/WAHA:
        - Puede venir como JSON string con latitude/longitude
        - O puede venir como texto con coordenadas
        
        Returns:
            String en formato "latitude,longitude" o None
        """
        try:
            import json
            
            # Intentar parsear como JSON (formato WAHA)
            try:
                data = json.loads(message)
                if isinstance(data, dict):
                    lat = data.get('latitude') or data.get('lat')
                    lon = data.get('longitude') or data.get('lon') or data.get('lng')
                    
                    if lat is not None and lon is not None:
                        logger.info(f"📍 [SlotExtractor] Ubicación extraída de JSON: {lat}, {lon}")
                        return f"{lat},{lon}"
            except (json.JSONDecodeError, ValueError):
                pass
            
            # Intentar extraer coordenadas del texto
            # Formato: "latitud, longitud" o "lat: X, lon: Y"
            coords_pattern = r'(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)'
            match = re.search(coords_pattern, message)
            if match:
                lat, lon = match.groups()
                logger.info(f"📍 [SlotExtractor] Ubicación extraída de texto: {lat}, {lon}")
                return f"{lat},{lon}"
            
            # Si no se pudo extraer, verificar si es solicitud de ubicación
            logger.warning(f"⚠️ [SlotExtractor] No se pudieron extraer coordenadas de: '{message[:100]}'")
            return None
            
        except Exception as e:
            logger.error(f"❌ [SlotExtractor] Error extrayendo ubicación: {e}")
            return None
    
    def _extract_confirmation(self, message: str) -> Optional[str]:
        """
        Extrae una confirmación (sí/no) del mensaje
        """
        message_lower = message.lower().strip()
        
        # Respuestas afirmativas
        affirmative = ['si', 'sí', 'yes', 'ok', 'vale', 'confirmo', 'confirmar', 'claro', 'por supuesto']
        if any(word in message_lower for word in affirmative):
            return 'si'
        
        # Respuestas negativas
        negative = ['no', 'nop', 'nope', 'cancelar', 'cancelo']
        if any(word in message_lower for word in negative):
            return 'no'
        
        return None