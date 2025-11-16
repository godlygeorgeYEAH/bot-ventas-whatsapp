"""
Módulo para consultar órdenes
"""
from typing import Dict, Any, Optional
from loguru import logger
from sqlalchemy.orm import Session

from app.services.order_service import OrderService
from app.database.repository import CustomerRepository
from config.database import get_db_context
from app.core.correlation import set_client_context


class CheckOrderModule:
    """Módulo para consultar órdenes existentes"""
    
    def __init__(self):
        self.name = "CheckOrderModule"
        self.intent = "check_order"
        self._setup_slots()
        
    def _setup_slots(self):
        """
        CheckOrderModule NO usa slots.
        
        Siempre muestra la última orden relevante automáticamente.
        El LLM detecta la intención de consultar orden y el módulo
        responde inmediatamente sin pedir información adicional.
        """
        self.slot_definitions = []
        self.slot_manager = None  # No necesitamos slot manager
    
    def get_intent(self) -> str:
        """Retorna la intención que maneja este módulo"""
        return self.intent
    
    def handle(
        self,
        message: str,
        context: Dict[str, Any],
        phone: str
    ) -> Dict[str, Any]:
        """
        Maneja la consulta de órdenes

        ⚡ COMPORTAMIENTO SIMPLE:
        Cuando el LLM detecta intent "check_order", este módulo
        automáticamente muestra la última orden relevante del cliente
        sin pedir ninguna información adicional.

        Args:
            message: Mensaje del usuario (no se usa, solo para contexto)
            context: Contexto de la conversación (no se usa)
            phone: Número de teléfono del usuario

        Returns:
            Dict con response y context_updates
        """
        # Establecer contexto de cliente para tracking en logs
        set_client_context(phone, context.get('conversation_id'))

        logger.info(f"🔍 [CheckOrderModule] Intent detectado por LLM: Mostrando última orden relevante")
        
        try:
            with get_db_context() as db:
                customer_repo = CustomerRepository()
                
                # Obtener cliente
                customer = customer_repo.get_or_create(phone, db)
                if not customer:
                    return {
                        "response": "No encontré tu información de cliente. ¿Podrías verificar?",
                        "context_updates": {
                            "current_module": None,
                            "current_intent": None,
                            "conversation_state": "active"
                        }
                    }
                
                # ✅ Siempre mostrar última orden relevante
                # El LLM ya determinó que el usuario quiere consultar su orden
                return self._show_last_relevant_order(db, customer.id, phone)
                
        except Exception as e:
            logger.error(f"❌ [CheckOrderModule] Error: {e}", exc_info=True)
            return {
                "response": "Hubo un error al consultar tu orden. Por favor, intenta de nuevo.",
                "context_updates": {
                    "current_module": None,
                    "current_intent": None,
                    "conversation_state": "active"
                }
            }
    
    
    def _show_last_relevant_order(
        self,
        db: Session,
        customer_id: str,
        phone: str
    ) -> Dict[str, Any]:
        """
        Muestra la última orden RELEVANTE del cliente
        
        Estados relevantes: confirmed, shipped, delivered
        (No muestra órdenes pending o cancelled)
        """
        order_service = OrderService(db)
        
        # Estados relevantes que queremos mostrar
        relevant_statuses = ['confirmed', 'shipped', 'delivered']
        
        # Obtener todas las órdenes del cliente y filtrar
        all_orders = order_service.get_customer_orders(customer_id, limit=20)
        
        # Filtrar por estados relevantes
        relevant_orders = [
            order for order in all_orders 
            if order.status in relevant_statuses
        ]
        
        if not relevant_orders:
            # No hay órdenes relevantes
            return {
                "response": "No tienes órdenes activas en este momento.\n\n¿Te gustaría hacer un pedido?",
                "context_updates": {
                    "current_module": None,
                    "current_intent": None,
                    "conversation_state": "active"
                }
            }
        
        # Tomar la más reciente
        last_order = relevant_orders[0]
        
        # Mostrar detalles completos de la última orden relevante
        response = self._format_order_details(last_order)
        
        # Agregar nota si hay más órdenes
        if len(relevant_orders) > 1:
            response += f"\n\n💡 Tienes {len(relevant_orders)} órdenes activas en total."
        
        return {
            "response": response,
            "context_updates": {
                "current_module": None,
                "current_intent": None,
                "conversation_state": "active",
                "last_checked_order": last_order.order_number
            }
        }
    
    def _format_order_details(self, order) -> str:
        """Formatea los detalles de una orden para mostrar"""
        status_emoji = self._get_status_emoji(order.status)
        
        response = f"{status_emoji} *Orden {order.order_number}*\n\n"
        response += f"📊 *Estado:* {self._format_status(order.status)}\n"
        response += f"📅 *Fecha:* {order.created_at.strftime('%d/%m/%Y %H:%M')}\n\n"
        
        response += "*Productos:*\n"
        for item in order.items:
            response += f"• {item.product_name} x{item.quantity}\n"
            response += f"  ${item.unit_price:.2f} c/u = ${item.unit_price * item.quantity:.2f}\n"
        
        response += f"\n💰 *Subtotal:* ${order.subtotal:.2f}\n"
        
        if order.tax > 0:
            response += f"📋 *Impuesto:* ${order.tax:.2f}\n"
        
        if order.shipping_cost > 0:
            response += f"🚚 *Envío:* ${order.shipping_cost:.2f}\n"
        
        response += f"💵 *Total:* ${order.total:.2f}\n"
        
        if order.delivery_latitude and order.delivery_longitude:
            response += f"\n📍 *GPS:* {order.delivery_latitude}, {order.delivery_longitude}\n"
            maps_url = f"https://www.google.com/maps?q={order.delivery_latitude},{order.delivery_longitude}"
            response += f"🗺️ Ver en mapa: {maps_url}\n"
        elif order.delivery_address:
            response += f"\n📍 *Ubicación:* {order.delivery_address}\n"
        
        if order.delivery_reference:
            response += f"🏠 *Referencia:* {order.delivery_reference}\n"
        
        # Información adicional según el estado
        if order.status == "pending":
            response += "\n⏳ Tu orden está pendiente de confirmación."
        elif order.status == "confirmed":
            response += "\n✅ Tu orden ha sido confirmada y está siendo preparada."
        elif order.status == "shipped":
            response += "\n🚚 Tu orden está en camino."
        elif order.status == "delivered":
            response += "\n✅ Tu orden ha sido entregada."
        elif order.status == "cancelled":
            response += "\n❌ Esta orden fue cancelada."
        
        return response
    
    def _get_status_emoji(self, status: str) -> str:
        """Retorna el emoji correspondiente al estado"""
        emoji_map = {
            "pending": "⏳",
            "confirmed": "✅",
            "shipped": "🚚",
            "delivered": "🎉",
            "cancelled": "❌"
        }
        return emoji_map.get(status, "📦")
    
    def _format_status(self, status: str) -> str:
        """Formatea el estado para mostrar"""
        status_map = {
            "pending": "Pendiente",
            "confirmed": "Confirmada",
            "shipped": "En camino",
            "delivered": "Entregada",
            "cancelled": "Cancelada"
        }
        return status_map.get(status, status.capitalize())
    
    def get_required_slots(self) -> list:
        """Retorna los slots requeridos (ninguno, es opcional)"""
        return []
    
    def validate_context(self, context: Dict[str, Any]) -> bool:
        """Valida que el contexto sea válido para este módulo"""
        return True  # No hay requisitos específicos
