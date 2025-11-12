"""
Módulo para manejar ofrecimientos de productos
"""
from typing import Dict, Any
from loguru import logger
from config.database import get_db_context
from config.settings import settings
from app.services.offer_service import OfferService
from app.services.order_service import OrderService
from app.helpers.offer_helper import OfferHelper


class OfferProductModule:
    """
    Módulo para gestionar ofrecimientos de productos a clientes
    
    Maneja:
    - Respuestas a ofrecimientos (Sí/No)
    - Agregar producto ofrecido a orden existente o crear nueva orden
    - Confirmación de orden después de aceptar/rechazar ofrecimiento
    """
    
    def __init__(self):
        self.name = "OfferProductModule"
        self.intent = "respond_to_offer"
    
    def can_handle(self, intent: str, context: Dict[str, Any]) -> bool:
        """
        Determina si este módulo puede manejar el intent/contexto
        
        Args:
            intent: Intent detectado
            context: Contexto actual de la conversación
            
        Returns:
            True si puede manejar, False si no
        """
        # Puede manejar si hay un ofrecimiento pendiente
        return context.get("waiting_offer_response") is True
    
    def handle(self, message: str, context: Dict[str, Any], phone: str) -> Dict[str, Any]:
        """
        Maneja la respuesta del usuario a un ofrecimiento
        
        Args:
            message: Mensaje del usuario
            context: Contexto de la conversación
            phone: Número del usuario
            
        Returns:
            Dict con "response" y "context_updates"
        """
        logger.info(f"🎁 [OfferProductModule] Procesando respuesta a ofrecimiento: '{message[:30]}...'")
        
        # Obtener información del ofrecimiento
        offered_product = context.get("offered_product")
        pending_order_id = context.get("pending_order_id")
        
        if not offered_product:
            logger.error("❌ No hay producto ofrecido en el contexto")
            return {
                "response": "❌ Hubo un error con el ofrecimiento. Por favor intenta de nuevo.",
                "context_updates": {
                    "current_module": None,
                    "waiting_offer_response": False,
                    "offered_product": None,
                    "pending_order_id": None
                }
            }
        
        # Detectar respuesta (Sí o No)
        message_lower = message.lower().strip()
        
        # Patrones de aceptación
        accept_patterns = ["si", "sí", "s", "ok", "vale", "dale", "acepto", "quiero", "yes", "y"]
        # Patrones de rechazo
        reject_patterns = ["no", "n", "nop", "nope", "paso", "no gracias", "no quiero"]
        
        accepted = any(pattern in message_lower for pattern in accept_patterns)
        rejected = any(pattern in message_lower for pattern in reject_patterns)
        
        if not accepted and not rejected:
            # Respuesta ambigua, pedir clarificación
            return {
                "response": "⚠️ No entendí tu respuesta. Por favor responde *Sí* para agregar el producto o *No* para continuar sin él.",
                "context_updates": {
                    "current_module": self.name,
                    "waiting_offer_response": True
                }
            }
        
        with get_db_context() as db:
            order_service = OrderService(db)
            
            if accepted:
                # Usuario aceptó el ofrecimiento
                logger.info(f"✅ Usuario aceptó el ofrecimiento de {offered_product['product_name']}")
                
                try:
                    if pending_order_id:
                        # Obtener la orden
                        from app.database.models import Order
                        order = db.query(Order).filter(Order.id == pending_order_id).first()
                        
                        if not order:
                            raise ValueError("Orden no encontrada")
                        
                        logger.info(f"  📦 Orden encontrada: {order.order_number} (Estado: {order.status})")
                        
                        # ⚠️ VALIDACIÓN: Verificar que la orden sea modificable
                        # Órdenes delivered y cancelled son solo históricas
                        if order.status in ['delivered', 'cancelled']:
                            logger.warning(f"  ⚠️ Orden {order.order_number} está en estado {order.status}, no es modificable")
                            return {
                                "response": f"⚠️ Esta orden ya fue {order.status}. No puedo agregar productos a órdenes finalizadas.\n\n"
                                           f"Si quieres hacer una nueva orden, solo dime qué producto te interesa.",
                                "context_updates": {
                                    "current_module": None,
                                    "waiting_offer_response": False,
                                    "offered_product": None,
                                    "pending_order_id": None
                                }
                            }
                        
                        # Si la orden está PENDING, confirmarla primero
                        if order.status == "pending":
                            logger.info(f"  ✅ Confirmando orden PENDING antes de agregar producto adicional")
                            order = order_service.confirm_order(order.id)
                        
                        # Ahora agregar el producto adicional
                        logger.info(f"  ➕ Agregando producto adicional: {offered_product['product_name']}")
                        
                        items = [{
                            "product_id": offered_product["product_id"],
                            "quantity": 1  # Por defecto 1 unidad
                        }]
                        
                        order = order_service.add_items_to_order(order.id, items)
                        
                        # Formatear resumen
                        summary = order_service.format_order_summary(order)
                        
                        response = f"✅ ¡Genial! He agregado *{offered_product['product_name']}* a tu orden.\n\n{summary}"
                        
                    else:
                        # No hay orden pendiente, crear una nueva
                        # Este caso normalmente no debería ocurrir en el flujo después de GPS
                        # pero podría pasar después de un greeting
                        response = f"✅ ¡Perfecto! Para procesar tu orden de *{offered_product['product_name']}*, necesito algunos datos.\n\n¿Cuál es tu dirección de entrega?"
                        
                        return {
                            "response": response,
                            "context_updates": {
                                "current_module": "CreateOrderModule",
                                "waiting_offer_response": False,
                                "offered_product": None,
                                "pending_order_id": None,
                                "slots_data": {
                                    "product_name": offered_product["product_name"],
                                    "quantity": 1
                                }
                            }
                        }
                    
                    return {
                        "response": response,
                        "context_updates": {
                            "current_module": None,
                            "waiting_offer_response": False,
                            "offered_product": None,
                            "pending_order_id": None,
                            "conversation_state": "completed"
                        }
                    }
                    
                except Exception as e:
                    logger.error(f"❌ Error agregando producto ofrecido: {e}")
                    return {
                        "response": f"❌ Hubo un error agregando el producto: {str(e)}",
                        "context_updates": {
                            "current_module": None,
                            "waiting_offer_response": False,
                            "offered_product": None,
                            "pending_order_id": None
                        }
                    }
            
            elif rejected:
                # Usuario rechazó el ofrecimiento
                logger.info(f"❌ Usuario rechazó el ofrecimiento de {offered_product['product_name']}")
                
                if pending_order_id:
                    # Confirmar la orden sin agregar el producto
                    try:
                        # Verificar que la orden sea modificable
                        from app.database.models import Order
                        order = db.query(Order).filter(Order.id == pending_order_id).first()
                        
                        if order and order.status in ['delivered', 'cancelled']:
                            logger.warning(f"  ⚠️ Orden {order.order_number} está en estado {order.status}, no es modificable")
                            return {
                                "response": f"👍 Entendido. Esta orden ya fue {order.status}.\n\n"
                                           f"Si necesitas algo más, solo avísame.",
                                "context_updates": {
                                    "current_module": None,
                                    "waiting_offer_response": False,
                                    "offered_product": None,
                                    "pending_order_id": None,
                                    "conversation_state": "idle"
                                }
                            }
                        
                        logger.info(f"  ✅ Confirmando orden sin producto adicional: {pending_order_id}")
                        confirmed_order = order_service.confirm_order(pending_order_id)
                        
                        # Formatear resumen
                        summary = order_service.format_order_summary(confirmed_order)
                        
                        response = f"Entendido, continuamos con tu orden actual.\n\n{summary}"
                        
                        return {
                            "response": response,
                            "context_updates": {
                                "current_module": None,
                                "waiting_offer_response": False,
                                "offered_product": None,
                                "pending_order_id": None,
                                "conversation_state": "completed"
                            }
                        }
                        
                    except Exception as e:
                        logger.error(f"❌ Error confirmando orden: {e}")
                        return {
                            "response": f"❌ Hubo un error confirmando tu orden: {str(e)}",
                            "context_updates": {
                                "current_module": None,
                                "waiting_offer_response": False,
                                "offered_product": None,
                                "pending_order_id": None
                            }
                        }
                else:
                    # No hay orden pendiente (ofrecimiento después de greeting)
                    response = "Entendido. ¿Hay algo más en lo que pueda ayudarte?"
                    
                    return {
                        "response": response,
                        "context_updates": {
                            "current_module": None,
                            "waiting_offer_response": False,
                            "offered_product": None,
                            "pending_order_id": None,
                            "conversation_state": "idle"
                        }
                    }


def make_offer(
    phone: str,
    product: Dict,
    pending_order_id: str = None
) -> Dict[str, Any]:
    """
    Función helper para hacer un ofrecimiento de producto
    
    Args:
        phone: Número del cliente
        product: Dict con información del producto
        pending_order_id: ID de orden pendiente (opcional)
        
    Returns:
        Dict con context_updates para aplicar
    """
    try:
        logger.info(f"🎁 Haciendo ofrecimiento de {product['product_name']} a {phone}")
        
        # Crear mensaje del ofrecimiento
        with get_db_context() as db:
            offer_service = OfferService(db)
            offer_message = offer_service.format_offer_message(product, include_price=True)
        
        # Enviar ofrecimiento con imagen
        offer_helper = OfferHelper()
        success = offer_helper.send_offer_sync(phone, product, offer_message)
        
        if not success:
            logger.error("❌ Error enviando ofrecimiento")
            return {
                "current_module": None,
                "waiting_offer_response": False
            }
        
        # Retornar context updates
        return {
            "current_module": "OfferProductModule",
            "waiting_offer_response": True,
            "offered_product": product,
            "pending_order_id": pending_order_id,
            "conversation_state": "waiting_offer_response"
        }
        
    except Exception as e:
        logger.error(f"❌ Error haciendo ofrecimiento: {e}")
        return {
            "current_module": None,
            "waiting_offer_response": False
        }

