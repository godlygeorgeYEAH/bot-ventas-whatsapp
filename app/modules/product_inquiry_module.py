from typing import List, Dict, Any
from app.modules.base_module import BaseModule, Slot, SlotType
from loguru import logger


class ProductInquiryModule(BaseModule):
    """Módulo para consultas de productos"""
    
    def __init__(self):
        super().__init__()
        self.description = "Ayuda a consultar información sobre productos"
    
    def get_required_slots(self) -> List[Slot]:
        """Define los slots para consultar productos"""
        return [
            Slot(
                name="product_category",
                type=SlotType.CHOICE,
                description="la categoría de producto que te interesa",
                question_template="Que categoria de producto te interesa?\n- Laptops\n- Tablets\n- Smartphones\n- Accesorios",
                required=True,
                choices=["Laptops", "Tablets", "Smartphones", "Accesorios"]
            ),
            Slot(
                name="price_range",
                type=SlotType.CHOICE,
                description="tu rango de presupuesto",
                question_template="Cual es tu rango de presupuesto?\n- Menos de $500\n- $500 - $1000\n- $1000 - $2000\n- Mas de $2000",
                required=False,
                choices=["Menos de $500", "$500 - $1000", "$1000 - $2000", "Mas de $2000"]
            ),
            Slot(
                name="specific_needs",
                type=SlotType.TEXT,
                description="necesidades o características específicas",
                question_template="Tienes alguna necesidad especifica? (gaming, trabajo, estudio, etc.) - Si no, escribe 'ninguna'",
                required=False,
                validation_rules={
                    "max_length": 100
                }
            )
        ]
    
    async def execute(self, slots_data: Dict[str, Any], context: Dict) -> Dict:
        """
        Ejecuta la consulta de productos
        
        Args:
            slots_data: Datos recolectados
            context: Contexto de la conversación
            
        Returns:
            Resultado con información de productos
        """
        try:
            logger.info(f"Consultando productos con: {slots_data}")
            
            category = slots_data.get("product_category")
            price_range = slots_data.get("price_range", "Cualquiera")
            needs = slots_data.get("specific_needs", "ninguna")
            
            # Aquí iría la lógica real de consulta a la BD de productos
            # Por ahora simulamos algunos productos
            products = self._get_mock_products(category, price_range)
            
            response_msg = f"""Encontre algunas opciones en {category}:\n\n"""
            
            for i, product in enumerate(products, 1):
                response_msg += f"{i}. {product['name']}\n"
                response_msg += f"   Precio: ${product['price']}\n"
                response_msg += f"   {product['description']}\n\n"
            
            response_msg += "Te gustaria hacer un pedido de algun producto? Solo dime cual te interesa!"
            
            return {
                "success": True,
                "message": response_msg,
                "data": {
                    "products": products,
                    "filters": slots_data
                },
                "next_action": "products_shown"
            }
            
        except Exception as e:
            logger.error(f"Error ejecutando ProductInquiryModule: {e}")
            return {
                "success": False,
                "message": "Lo siento, hubo un error consultando los productos. Intenta de nuevo.",
                "data": {},
                "next_action": None
            }
    
    def _get_mock_products(self, category: str, price_range: str) -> List[Dict]:
        """Retorna productos simulados según categoría"""
        
        mock_db = {
            "Laptops": [
                {"name": "Laptop HP Pavilion", "price": 899, "description": "Core i5, 8GB RAM, 512GB SSD"},
                {"name": "Laptop Dell Inspiron", "price": 749, "description": "Core i3, 8GB RAM, 256GB SSD"},
                {"name": "MacBook Air M2", "price": 1199, "description": "Chip M2, 8GB RAM, 256GB SSD"}
            ],
            "Tablets": [
                {"name": "iPad 10th Gen", "price": 449, "description": "10.9 pulgadas, 64GB"},
                {"name": "Samsung Galaxy Tab S9", "price": 599, "description": "11 pulgadas, 128GB"},
                {"name": "Amazon Fire HD 10", "price": 149, "description": "10.1 pulgadas, 32GB"}
            ],
            "Smartphones": [
                {"name": "iPhone 14", "price": 799, "description": "128GB, 6.1 pulgadas"},
                {"name": "Samsung Galaxy S23", "price": 899, "description": "256GB, 6.1 pulgadas"},
                {"name": "Google Pixel 8", "price": 699, "description": "128GB, 6.2 pulgadas"}
            ],
            "Accesorios": [
                {"name": "AirPods Pro", "price": 249, "description": "Cancelacion de ruido activa"},
                {"name": "Mouse Logitech MX Master 3", "price": 99, "description": "Ergonomico, inalambrico"},
                {"name": "Teclado Mecanico Keychron", "price": 89, "description": "RGB, switches blue"}
            ]
        }
        
        return mock_db.get(category, [])[:3]  # Retornar máximo 3 productos


class GreetingModule(BaseModule):
    """Módulo simple para manejar saludos (sin slots)"""
    
    def __init__(self):
        super().__init__()
        self.description = "Maneja saludos iniciales"
    
    def get_required_slots(self) -> List[Slot]:
        """No requiere slots"""
        return []
    
    async def execute(self, slots_data: Dict[str, Any], context: Dict) -> Dict:
        """Ejecuta el saludo"""
        customer_name = context.get("customer_name")
        
        if customer_name:
            greeting = f"Hola {customer_name}!"
        else:
            greeting = "Hola!"
        
        message = f"""{greeting} Bienvenido a nuestro servicio de ventas.

Puedo ayudarte con:
- Consultar productos y precios
- Realizar pedidos paso a paso
- Informacion sobre entregas

Que necesitas hoy?"""
        
        return {
            "success": True,
            "message": message,
            "data": {},
            "next_action": None
        }