"""
Handler para gestionar órdenes con múltiples productos
"""
from typing import Dict, Any, List, Optional
from loguru import logger
from config.database import get_db_context
from app.services.product_service import ProductService


class MultiProductHandler:
    """Maneja la lógica de múltiples productos en una orden"""
    
    def __init__(self):
        pass
    
    def parse_products_with_quantities(self, product_string: str) -> List[Dict[str, Any]]:
        """
        Parsea string de productos CON cantidades usando LLM
        
        Args:
            product_string: String con productos y cantidades (ej: "dos laptops, 1 mouse")
            
        Returns:
            Lista de dict con {'product': str, 'quantity': int|None}
        """
        import requests
        
        # Usar LLM para parsear productos y cantidades
        prompt = f"""Eres un asistente experto en extraer productos y cantidades de mensajes de clientes.

TAREA: Extrae CADA producto con su cantidad y devuelve en formato JSON.

REGLAS ESTRICTAS:
1. Extrae el nombre del producto (sin artículos ni verbos)
2. SOLO extrae cantidad si hay un NÚMERO EXPLÍCITO antes del producto:
   - Números: "2 laptops", "5 mouses" → extraer el número
   - Palabras: "dos laptops", "tres teclados" → convertir a número
   - Artículos singulares: "un mouse", "una laptop" → cantidad = 1
3. Si NO hay número explícito, USA NULL (incluso si el producto está en plural)
   - "laptops" (sin número) → null
   - "teclados" (sin número) → null
   - "y mouses" (sin número) → null
4. Convierte palabras numéricas: "dos" → 2, "tres" → 3, "cuatro" → 4, etc.
5. Responde SOLO en formato JSON válido, sin explicaciones

FORMATO DE RESPUESTA:
{{"products": [{{"product": "nombre", "quantity": numero_o_null}}, ...]}}

EJEMPLOS:
Mensaje: "dos laptops y un mouse"
Respuesta: {{"products": [{{"product": "laptop", "quantity": 2}}, {{"product": "mouse", "quantity": 1}}]}}

Mensaje: "quiero 3 teclados, una laptop y 2 mouses"
Respuesta: {{"products": [{{"product": "teclado", "quantity": 3}}, {{"product": "laptop", "quantity": 1}}, {{"product": "mouse", "quantity": 2}}]}}

Mensaje: "laptop, mouse"
Respuesta: {{"products": [{{"product": "laptop", "quantity": null}}, {{"product": "mouse", "quantity": null}}]}}

Mensaje: "necesito una laptop HP y 5 mouses Logitech"
Respuesta: {{"products": [{{"product": "laptop HP", "quantity": 1}}, {{"product": "mouse Logitech", "quantity": 5}}]}}

Mensaje: "quiero cuatro laptops, 2 mouse y teclados"
Respuesta: {{"products": [{{"product": "laptop", "quantity": 4}}, {{"product": "mouse", "quantity": 2}}, {{"product": "teclado", "quantity": null}}]}}

Mensaje: "2 laptops y mouses"
Respuesta: {{"products": [{{"product": "laptop", "quantity": 2}}, {{"product": "mouse", "quantity": null}}]}}

MENSAJE DEL CLIENTE: "{product_string}"
Respuesta:"""

        try:
            logger.debug(f"🔵 [MultiProductHandler] Usando LLM para parsear productos y cantidades")
            
            response = requests.post(
                'http://localhost:5001/generate',
                json={
                    "model": "llama3.2:latest",
                    "prompt": prompt,
                    "temperature": 0.1,
                    "max_tokens": 200
                },
                timeout=20.0
            )
            
            response.raise_for_status()
            result = response.json()
            
            if result.get("success"):
                llm_response = result["response"].strip()
                logger.debug(f"📄 [MultiProductHandler] Respuesta LLM: {llm_response[:200]}...")
                
                # Limpiar y parsear JSON
                import json
                import re
                
                # Extraer JSON del texto (puede venir con texto adicional)
                json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    logger.debug(f"🔍 [MultiProductHandler] JSON extraído: {json_str[:200]}...")
                    
                    try:
                        parsed = json.loads(json_str)
                        
                        if "products" in parsed and isinstance(parsed["products"], list):
                            products_with_qty = parsed["products"]
                            
                            logger.info(f"📦 [MultiProductHandler] LLM parseó {len(products_with_qty)} productos con cantidades")
                            for item in products_with_qty:
                                logger.info(f"  - {item.get('product', 'unknown')}: qty={item.get('quantity', 'None')}")
                            
                            return products_with_qty
                        else:
                            logger.warning(f"⚠️ [MultiProductHandler] JSON sin 'products': {parsed}")
                    except json.JSONDecodeError as je:
                        logger.error(f"❌ [MultiProductHandler] Error parseando JSON: {je}")
                        logger.debug(f"   JSON string: {json_str}")
                else:
                    logger.warning(f"⚠️ [MultiProductHandler] No se encontró JSON en respuesta LLM")
        
        except Exception as e:
            logger.error(f"❌ [MultiProductHandler] Error con LLM: {e}", exc_info=True)
        
        # Fallback: parsear sin cantidades
        logger.warning(f"⚠️ [MultiProductHandler] Usando fallback (sin cantidades)")
        simple_products = self.parse_products(product_string)
        return [{"product": p, "quantity": None} for p in simple_products]
    
    def parse_products(self, product_string: str) -> List[str]:
        """
        Parsea string de productos usando LLM y retorna lista de nombres individuales
        
        Args:
            product_string: String con productos (ej: "laptop, mouse" o "una laptop y un mouse")
            
        Returns:
            Lista de nombres de productos limpios
        """
        import requests
        
        # Si no hay comas ni "y", es un solo producto
        if ',' not in product_string and ' y ' not in product_string.lower():
            return [product_string.strip()]
        
        # Usar LLM para parsear y limpiar productos
        prompt = f"""Eres un asistente experto en extraer nombres de productos de mensajes de clientes.

TAREA: Extrae CADA producto mencionado y devuelve una lista separada por comas.

REGLAS ESTRICTAS:
1. Extrae ÚNICAMENTE el nombre de cada producto (sustantivo principal)
2. NO incluyas verbos: quiero, deseo, necesito, comprar, etc.
3. NO incluyas artículos: un, una, el, la, los, las
4. NO incluyas números o cantidades
5. Separa cada producto con COMA
6. Responde SOLO con los nombres de productos separados por comas, sin explicaciones

EJEMPLOS:
Mensaje: "una laptop y un mouse"
Productos: laptop, mouse

Mensaje: "quiero 2 teclados, una laptop y 3 mouses"
Productos: teclado, laptop, mouse

Mensaje: "necesito una laptop HP y un mouse Logitech"
Productos: laptop HP, mouse Logitech

Mensaje: "dame laptop, mouse, teclado"
Productos: laptop, mouse, teclado

MENSAJE DEL CLIENTE: "{product_string}"
Productos:"""

        try:
            logger.debug(f"🔵 [MultiProductHandler] Usando LLM para parsear: '{product_string[:50]}...'")
            
            response = requests.post(
                'http://localhost:5001/generate',
                json={
                    "model": "llama3.2:latest",
                    "prompt": prompt,
                    "temperature": 0.1,
                    "max_tokens": 100
                },
                timeout=15.0
            )
            
            response.raise_for_status()
            result = response.json()
            
            if result.get("success"):
                llm_response = result["response"].strip()
                
                # Limpiar respuesta
                llm_response = llm_response.lower().strip()
                llm_response = llm_response.strip('"').strip("'")
                
                # Separar por comas
                products = [p.strip() for p in llm_response.split(',')]
                
                # Filtrar vacíos
                products = [p for p in products if p and len(p) > 1]
                
                if products:
                    logger.info(f"📦 [MultiProductHandler] LLM parseó {len(products)} productos: {products}")
                    return products
        
        except Exception as e:
            logger.error(f"❌ [MultiProductHandler] Error con LLM: {e}")
        
        # Fallback: split simple por comas
        logger.warning(f"⚠️ [MultiProductHandler] Usando fallback para parsear")
        products = [p.strip() for p in product_string.split(',')]
        products = [p for p in products if p]
        
        logger.info(f"📦 [MultiProductHandler] Parseados {len(products)} productos (fallback): {products}")
        return products
    
    def validate_all_products(self, products_with_qty: List[Dict[str, Any]], db) -> tuple[List[Dict[str, Any]], List[str]]:
        """
        Valida que todos los productos existan en la BD
        
        Args:
            products_with_qty: Lista de dict con {'product': str, 'quantity': int|None}
            db: Sesión de base de datos
            
        Returns:
            Tuple con (productos_validos, productos_invalidos)
        """
        product_service = ProductService(db)
        valid_products = []
        invalid_products = []
        
        for item in products_with_qty:
            product_name = item['product']
            quantity = item.get('quantity')
            
            product = product_service.get_product_by_name_fuzzy(product_name)
            
            if product:
                valid_products.append({
                    'name': product.name,
                    'id': product.id,
                    'price': product.price,
                    'stock': product.stock,
                    'original_input': product_name,
                    'quantity': quantity  # Incluir cantidad si fue detectada
                })
                qty_str = f" (qty: {quantity})" if quantity else ""
                logger.info(f"✅ [MultiProductHandler] Producto válido: {product_name} → {product.name}{qty_str}")
            else:
                invalid_products.append(product_name)
                logger.warning(f"❌ [MultiProductHandler] Producto no encontrado: {product_name}")
        
        return valid_products, invalid_products
    
    def get_current_product_being_processed(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Obtiene el producto que estamos procesando actualmente
        
        Returns:
            Dict con info del producto o None si ya terminamos
        """
        order_items = context.get('order_items', [])
        
        # Buscar el primer producto que no tiene cantidad
        for item in order_items:
            if item.get('quantity') is None:
                return item
        
        return None
    
    def is_multi_product_order(self, context: Dict[str, Any]) -> bool:
        """Verifica si la orden tiene múltiples productos"""
        order_items = context.get('order_items', [])
        return len(order_items) > 1
    
    def all_quantities_filled(self, context: Dict[str, Any]) -> bool:
        """Verifica si todos los productos tienen cantidades asignadas"""
        order_items = context.get('order_items', [])
        
        if not order_items:
            return False
        
        return all(item.get('quantity') is not None for item in order_items)
    
    def initialize_order_items(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Inicializa la lista de items de la orden
        
        Args:
            products: Lista de productos validados (pueden incluir 'quantity')
            
        Returns:
            Lista de order_items (quantity puede ser int o None)
        """
        order_items = []
        
        for product in products:
            # Usar cantidad detectada si existe, sino None
            detected_qty = product.get('quantity')
            
            order_items.append({
                'product_id': product['id'],
                'product_name': product['name'],
                'price': product['price'],
                'stock': product['stock'],
                'quantity': detected_qty,
                'original_input': product['original_input']
            })
        
        # Contar cuántos tienen cantidad pre-asignada
        with_qty = sum(1 for item in order_items if item['quantity'] is not None)
        logger.info(f"📝 [MultiProductHandler] Inicializados {len(order_items)} order_items ({with_qty} con cantidad detectada)")
        
        return order_items
    
    def set_quantity_for_current_product(
        self,
        context: Dict[str, Any],
        quantity: int
    ) -> Dict[str, Any]:
        """
        Asigna cantidad al producto actual
        
        Args:
            context: Contexto de conversación
            quantity: Cantidad a asignar
            
        Returns:
            Contexto actualizado
        """
        order_items = context.get('order_items', [])
        
        # Encontrar primer producto sin cantidad
        for item in order_items:
            if item.get('quantity') is None:
                item['quantity'] = quantity
                logger.info(f"✅ [MultiProductHandler] Cantidad asignada: {item['product_name']} × {quantity}")
                break
        
        context['order_items'] = order_items
        return context
    
    def get_next_product_prompt(self, context: Dict[str, Any]) -> Optional[str]:
        """
        Genera el prompt para pedir la cantidad del siguiente producto
        
        Returns:
            String con el prompt o None si ya terminamos
        """
        current_product = self.get_current_product_being_processed(context)
        
        if not current_product:
            return None
        
        product_name = current_product['product_name']
        stock = current_product['stock']
        
        prompt = f"¿Cuántas unidades de **{product_name}** quieres?\n\n"
        prompt += f"📦 Stock disponible: {stock} unidades"
        
        return prompt
    
    def get_order_summary(self, context: Dict[str, Any]) -> str:
        """
        Genera un resumen de los productos y cantidades
        
        Returns:
            String con el resumen
        """
        order_items = context.get('order_items', [])
        
        if not order_items:
            return ""
        
        summary = "📋 **Resumen de tu orden:**\n\n"
        total = 0
        
        for item in order_items:
            if item.get('quantity'):
                subtotal = item['price'] * item['quantity']
                total += subtotal
                summary += f"• {item['product_name']} × {item['quantity']} = ${subtotal:.2f}\n"
        
        summary += f"\n💰 **Total: ${total:.2f}**"
        
        return summary

