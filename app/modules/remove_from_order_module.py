"""
Módulo para eliminar productos de una orden confirmada
"""
from typing import Dict, Any, Optional
from loguru import logger
from config.database import get_db_context
from app.core.slots import SlotDefinition, SlotType, SlotManager
from app.services.order_service import OrderService
from app.database.models import Customer


class RemoveFromOrderModule:
    """Módulo para gestionar la eliminación de productos de órdenes"""
    
    def __init__(self):
        self.name = "RemoveFromOrderModule"
        self.intent = "remove_from_order"
        
        # Definir slots necesarios
        self.slots_schema = {
            "product_name": SlotDefinition(
                name="product_name",
                type=SlotType.TEXT,
                required=True,
                prompt="¿Qué producto quieres eliminar de tu orden?",
                validation_rules={
                    "min_length": 2
                },
                examples=["laptop", "mouse", "teclado"],
                auto_extract=True
            ),
            "quantity": SlotDefinition(
                name="quantity",
                type=SlotType.NUMBER,
                required=True,
                prompt="¿Cuántas unidades quieres eliminar?",
                validation_rules={
                    "min": 1,
                    "max": 100,
                    "only_integers": True
                },
                examples=["1", "2", "3"],
                auto_extract=True
            )
        }
        
        self.slot_manager = SlotManager(self.slots_schema)
    
    def handle(
        self,
        message: str,
        context: Dict[str, Any],
        phone: str
    ) -> Dict[str, Any]:
        """
        Maneja el mensaje del usuario para eliminar productos
        
        Args:
            message: Mensaje del usuario
            context: Contexto de la conversación
            phone: Teléfono del usuario
            
        Returns:
            Dict con respuesta y datos actualizados
        """
        logger.debug(f"🗑️ [RemoveFromOrderModule] Procesando: '{message[:30]}...'")
        
        # ═══════════════════════════════════════════════════════════
        # ⚡ LIMPIEZA: Si el estado anterior es "failed", limpiar slots y empezar de nuevo
        # ═══════════════════════════════════════════════════════════
        if context.get('conversation_state') == 'failed':
            logger.info(f"🔄 [RemoveFromOrderModule] Estado 'failed' detectado, limpiando slots para reintentar")
            context['slots_data'] = {}
            context['current_slot'] = None
            context['validation_attempts'] = {}
            context['conversation_state'] = 'collecting_slots'
        
        # Obtener estado actual de slots
        current_slots = context.get('slots_data', {})
        current_slot = context.get('current_slot')
        attempts = context.get('validation_attempts', {})
        
        # ═══════════════════════════════════════════════════════════
        # BUSCAR LA ORDEN CONFIRMADA MÁS RECIENTE (SIEMPRE)
        # ═══════════════════════════════════════════════════════════
        # IMPORTANTE: Buscar siempre para evitar usar órdenes antiguas del contexto
        with get_db_context() as db:
            order_service = OrderService(db)
            customer = db.query(Customer).filter(Customer.phone == phone).first()
            
            if customer:
                recent_order = order_service.get_recent_confirmed_order(customer.id, max_hours=24)
                
                if not recent_order:
                    return {
                        "response": "❌ No tienes órdenes confirmadas recientes de las cuales eliminar productos.\n\n"
                                  "Solo puedes eliminar productos de órdenes confirmadas en las últimas 24 horas.",
                        "context_updates": {
                            "current_module": None,
                            "conversation_state": "completed",
                            "removing_order_id": None,
                            "removing_order_number": None,
                            "max_quantity_available": None
                        }
                    }
                
                # Guardar ID de la orden (siempre actualizar)
                logger.info(f"✅ [RemoveFromOrderModule] Orden confirmada encontrada: {recent_order.order_number}")
                context['removing_order_id'] = recent_order.id
                context['removing_order_number'] = recent_order.order_number
        
        # Procesar mensaje con slot manager
        result = self.slot_manager.process_message(
            message=message,
            current_slots=current_slots,
            current_slot_name=current_slot,
            attempts=attempts,
            context={"max_quantity_available": context.get('max_quantity_available')}
        )
        
        # ═══════════════════════════════════════════════════════════
        # AUTO-DETECTAR CANTIDAD SI SOLO HAY 1 UNIDAD EN LA ORDEN
        # ═══════════════════════════════════════════════════════════
        # Si acabamos de extraer el product_name y aún no tenemos quantity
        if "product_name" in result.filled_slots and "quantity" not in result.filled_slots and result.current_slot == "quantity":
            with get_db_context() as db:
                from app.database.models import Order, OrderItem
                from app.services.product_service import ProductService
                
                order = db.query(Order).filter(Order.id == context.get('removing_order_id')).first()
                if order:
                    product_service = ProductService(db)
                    product_name = result.filled_slots.get("product_name")
                    
                    # Buscar el producto por nombre (fuzzy)
                    product = product_service.get_product_by_name_fuzzy(product_name)
                    
                    if product:
                        # Buscar el item en la orden
                        order_item = next((item for item in order.items if item.product_id == product.id), None)
                        
                        if order_item:
                            # Si solo hay 1 unidad, auto-completar
                            if order_item.quantity == 1:
                                logger.info(f"✅ [RemoveFromOrderModule] Auto-detectado: 1 unidad de {product.name}, completando automáticamente")
                                result.filled_slots["quantity"] = 1
                                result.current_slot = None
                                result.completed = True
                                # Guardar la cantidad máxima en el contexto
                                context['max_quantity_available'] = 1
                            else:
                                # Guardar la cantidad máxima disponible para validación
                                context['max_quantity_available'] = order_item.quantity
                                logger.info(f"📊 [RemoveFromOrderModule] {product.name} tiene {order_item.quantity} unidades en la orden")
                        else:
                            logger.warning(f"⚠️ [RemoveFromOrderModule] Producto {product.name} no encontrado en la orden")
        
        # Preparar respuesta base
        response_data = {
            "context_updates": {
                "current_module": "RemoveFromOrderModule",
                "slots_data": result.filled_slots,
                "current_slot": result.current_slot,
                "validation_attempts": result.attempts,
                "conversation_state": "collecting_slots" if not result.completed else "completed",
                "removing_order_id": context.get('removing_order_id'),
                "removing_order_number": context.get('removing_order_number'),
                "max_quantity_available": context.get('max_quantity_available')
            }
        }
        
        # Verificar si completamos slots
        if result.completed:
            logger.info(f"✅ [RemoveFromOrderModule] Todos los slots llenados, removiendo producto...")
            
            # Remover producto
            remove_result = self._remove_from_order(
                slots_data=result.filled_slots,
                phone=phone,
                order_id=context.get('removing_order_id'),
                order_number=context.get('removing_order_number')
            )
            
            if remove_result["success"]:
                response_data["response"] = remove_result["message"]
                response_data["context_updates"]["conversation_state"] = "completed"
                response_data["context_updates"]["current_module"] = None
                response_data["context_updates"]["removing_order_id"] = None
                response_data["context_updates"]["removing_order_number"] = None
                response_data["context_updates"]["max_quantity_available"] = None
            else:
                response_data["response"] = f"❌ {remove_result['message']}"
                response_data["context_updates"]["conversation_state"] = "failed"
                response_data["context_updates"]["current_module"] = None
                response_data["context_updates"]["removing_order_id"] = None
                response_data["context_updates"]["removing_order_number"] = None
                response_data["context_updates"]["max_quantity_available"] = None
        else:
            # Continuar pidiendo slots
            response_data["response"] = result.next_prompt
        
        return response_data
    
    def _remove_from_order(
        self,
        slots_data: Dict[str, Any],
        phone: str,
        order_id: str,
        order_number: str
    ) -> Dict[str, Any]:
        """
        Remueve producto de la orden
        
        Args:
            slots_data: Datos de los slots
            phone: Teléfono del usuario
            order_id: ID de la orden
            order_number: Número de la orden
            
        Returns:
            Dict con success, message
        """
        try:
            with get_db_context() as db:
                order_service = OrderService(db)
                
                product_name = slots_data.get("product_name")
                quantity = int(slots_data.get("quantity"))
                
                logger.info(f"🗑️ [RemoveFromOrderModule] Removiendo {quantity}x {product_name} de orden {order_number}")
                
                # Remover items de la orden
                try:
                    updated_order = order_service.remove_items_from_order(
                        order_id=order_id,
                        product_name=product_name,
                        quantity=quantity
                    )
                    
                    # Formatear resumen
                    summary = order_service.format_order_summary(updated_order)
                    
                    return {
                        "success": True,
                        "message": f"✅ ¡Producto eliminado exitosamente de tu orden *{order_number}*!\n\n{summary}",
                        "order_id": updated_order.id
                    }
                    
                except ValueError as e:
                    return {
                        "success": False,
                        "message": str(e)
                    }
                
        except Exception as e:
            logger.error(f"❌ [RemoveFromOrderModule] Error eliminando producto: {e}")
            return {
                "success": False,
                "message": "Ocurrió un error al eliminar el producto. Por favor intenta de nuevo."
            }

