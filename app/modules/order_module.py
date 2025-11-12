from typing import List, Dict, Any
from app.modules.base_module import BaseModule, Slot, SlotType
from loguru import logger


class CreateOrderModule(BaseModule):
    """Módulo para crear órdenes de compra con slot filling secuencial"""
    
    def __init__(self):
        super().__init__()
        self.description = "Crea una orden de compra paso a paso"
    
    def get_required_slots(self) -> List[Slot]:
        """Define los slots necesarios para crear una orden"""
        return [
            Slot(
                name="product_name",
                type=SlotType.TEXT,
                description="el nombre del producto que desea comprar",
                question_template="Que producto te gustaria ordenar?",
                required=True,
                validation_rules={
                    "min_length": 2,
                    "max_length": 100
                }
            ),
            Slot(
                name="quantity",
                type=SlotType.NUMBER,
                description="la cantidad de unidades",
                question_template="Cuantas unidades deseas?",
                required=True,
                validation_rules={
                    "min": 1,
                    "max": 100
                }
            ),
            Slot(
                name="delivery_method",
                type=SlotType.CHOICE,
                description="el metodo de entrega preferido",
                question_template="Como prefieres recibir tu pedido?\n- Domicilio\n- Recoger en tienda\n- Express",
                required=True,
                choices=["Domicilio", "Recoger en tienda", "Express"]
            ),
            Slot(
                name="delivery_address",
                type=SlotType.TEXT,
                description="la direccion de entrega",
                question_template="Cual es tu direccion de entrega completa?",
                required=True,
                depends_on="delivery_method",
                skip_if={
                    "delivery_method": ["Recoger en tienda"]
                },
                validation_rules={
                    "min_length": 10
                }
            ),
            Slot(
                name="phone",
                type=SlotType.PHONE,
                description="tu numero de telefono de contacto",
                question_template="A que numero podemos contactarte para confirmar tu pedido?",
                required=True
            ),
            Slot(
                name="special_instructions",
                type=SlotType.TEXT,
                description="instrucciones especiales (opcional)",
                question_template="Tienes alguna instruccion especial para tu pedido? (Si no, escribe 'no')",
                required=False,
                validation_rules={
                    "max_length": 200
                }
            )
        ]
    
    async def execute(self, slots_data: Dict[str, Any], context: Dict) -> Dict:
        """
        Ejecuta la creacion de la orden con todos los datos recolectados
        
        Args:
            slots_data: Todos los slots llenos
            context: Contexto de la conversacion
            
        Returns:
            Resultado de la ejecucion
        """
        try:
            logger.info(f"Creando orden con datos: {slots_data}")
            
            # Aquí iría la lógica real de crear la orden en la BD
            # Por ahora simulamos la creación
            order_id = self._generate_order_id()
            
            # Construir mensaje de confirmación
            product = slots_data.get("product_name")
            quantity = slots_data.get("quantity")
            delivery = slots_data.get("delivery_method")
            address = slots_data.get("delivery_address", "N/A")
            phone = slots_data.get("phone")
            
            confirmation_msg = f"""Orden #{order_id} creada exitosamente!

Resumen de tu pedido:
- Producto: {product}
- Cantidad: {quantity} unidad(es)
- Entrega: {delivery}
"""
            
            if address != "N/A":
                confirmation_msg += f"- Direccion: {address}\n"
            
            confirmation_msg += f"- Contacto: {phone}\n"
            confirmation_msg += "\nTe contactaremos pronto para confirmar tu pedido. Gracias por tu compra!"
            
            return {
                "success": True,
                "message": confirmation_msg,
                "data": {
                    "order_id": order_id,
                    "slots": slots_data
                },
                "next_action": "order_created"
            }
            
        except Exception as e:
            logger.error(f"Error ejecutando CreateOrderModule: {e}")
            return {
                "success": False,
                "message": "Lo siento, hubo un error creando tu orden. Por favor intenta de nuevo.",
                "data": {},
                "next_action": None
            }
    
    def _generate_order_id(self) -> str:
        """Genera un ID de orden único"""
        import random
        import string
        return ''.join(random.choices(string.digits, k=6))