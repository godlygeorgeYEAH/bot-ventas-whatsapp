"""
Módulo para completar el checkout después de webapp

Este módulo se activa automáticamente cuando la webapp envía el webhook
indicando que el usuario completó su carrito. Solicita GPS y método de pago,
y finalmente confirma la orden.
"""
from typing import Dict, Any, List
from loguru import logger

from config.database import get_db_context
from app.database.models import Order, OrderItem, Customer, Product
from app.services.order_service import OrderService
from app.core.slots.slot_definition import SlotDefinition, SlotType
from app.core.slots.slot_manager import SlotManager


class CheckoutModule:
    """Módulo para checkout después de webapp"""
    
    # Definir slots necesarios
    SLOTS = [
        SlotDefinition(
            name="gps_location",
            type=SlotType.LOCATION,
            prompt="📍 *Para completar tu pedido, necesito tu ubicación de entrega.*\n\n"
                   "Por favor, envíame tu ubicación GPS usando la opción de WhatsApp:\n"
                   "📎 → Ubicación → Enviar tu ubicación actual",
            required=True,
            auto_extract=False
        ),
        SlotDefinition(
            name="delivery_reference",
            type=SlotType.TEXT,
            prompt="🏠 *¿Hay alguna referencia que me ayude a encontrar tu dirección?*\n\n"
                   "Por ejemplo: 'Casa azul con portón blanco', 'Edificio Torre Norte, apto 501', etc.\n\n"
                   "_(O escribe 'ninguna' si no hay referencia)_",
            required=False,
            auto_extract=True,
            examples=["Casa azul con portón blanco", "Edificio Torre Norte, apto 501", "ninguna"]
        ),
        SlotDefinition(
            name="payment_method",
            type=SlotType.CHOICE,
            prompt="💳 *¿Cómo te gustaría pagar?*\n\n"
                   "Opciones disponibles:\n"
                   "• Efectivo\n"
                   "• Tarjeta\n"
                   "• Transferencia",
            required=True,
            auto_extract=True,
            validation_rules={
                "choices": ["efectivo", "tarjeta", "transferencia"],
                "fuzzy_match": True
            },
            examples=["efectivo", "tarjeta", "transferencia"]
        )
    ]
    
    def __init__(self):
        self.name = "CheckoutModule"
        self.intent = None  # No se activa por intent, sino por webhook
        # Convertir lista de slots a diccionario {nombre: SlotDefinition}
        slots_dict = {slot.name: slot for slot in self.SLOTS}
        self.slot_manager = SlotManager(slots_dict)
    
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
        Maneja el proceso de checkout
        
        Proceso:
        1. Verifica que hay una orden para checkout
        2. Inicia slot filling (GPS + referencia + pago)
        3. Cuando todo está completo, confirma la orden
        """
        logger.info(f"🔄 [{self.name}] Procesando checkout para {phone}")
        logger.info(f"   Mensaje: {message[:50]}...")
        logger.info(f"   Contexto: current_module={context.get('current_module')}, order_id={context.get('checkout_order_id')}")
        
        # El checkout ya fue iniciado por el API (envió confirmación + prompt de GPS)
        # Aquí solo procesamos las respuestas del usuario mediante slot filling
        try:
            # ⚠️ Validación robusta: Asegurar que slots_data y validation_attempts sean SIEMPRE diccionarios
            slots_data = context.get("slots_data", {})
            logger.debug(f"🐛 [CheckoutModule] slots_data ANTES de validar: type={type(slots_data).__name__}, value={slots_data}")
            if isinstance(slots_data, list):
                logger.warning(f"⚠️ [CheckoutModule] slots_data era lista, corrigiendo: {slots_data}")
                slots_data = {}
            
            validation_attempts = context.get("validation_attempts", {})
            logger.debug(f"🐛 [CheckoutModule] validation_attempts ANTES de validar: type={type(validation_attempts).__name__}, value={validation_attempts}")
            if isinstance(validation_attempts, list):
                logger.warning(f"⚠️ [CheckoutModule] validation_attempts era lista, corrigiendo: {validation_attempts}")
                validation_attempts = {}
            
            logger.debug(f"🐛 [CheckoutModule] Llamando slot_manager.process_message con:")
            logger.debug(f"   - current_slots type: {type(slots_data).__name__}")
            logger.debug(f"   - attempts type: {type(validation_attempts).__name__}")
            
            result = self.slot_manager.process_message(
                message=message,
                current_slots=slots_data,
                current_slot_name=context.get("current_slot"),
                attempts=validation_attempts,
                context=context
            )
            
            logger.info(f"📊 [{self.name}] Slot filling result: completed={result.completed}")
            logger.info(f"   Filled slots: {list(result.filled_slots.keys())}")
            
            # Preparar context updates
            context_updates = {
                "current_module": self.name if not result.completed else None,
                "conversation_state": "completed" if result.completed else "collecting_slots",
                "slots_data": result.filled_slots,
                "current_slot": result.current_slot,
                "validation_attempts": result.attempts,
                "checkout_order_id": context.get("checkout_order_id")  # Mantener el order_id
            }
            
            # Si no está completo, devolver el próximo prompt
            if not result.completed:
                return {
                    "response": result.next_prompt,
                    "context_updates": context_updates
                }
            
            # ✅ Slots completos, confirmar orden
            logger.info(f"✅ [{self.name}] Todos los slots completos, confirmando orden")
            
            with get_db_context() as db:
                order_id = context.get("checkout_order_id")
                order = db.query(Order).filter(Order.id == order_id).first()
                
                if not order:
                    logger.error(f"❌ Orden no encontrada: {order_id}")
                    return {
                        "response": "❌ Hubo un error al confirmar la orden.",
                        "context_updates": {
                            "current_module": None,
                            "checkout_order_id": None,
                            "start_checkout": False,
                            "slots_data": {},
                            "conversation_state": "completed"
                        }
                    }
                
                # Actualizar orden con los datos del checkout
                gps_location = result.filled_slots.get("gps_location")
                
                # Parsear GPS location (formato: "latitud,longitud")
                if gps_location and "," in gps_location:
                    try:
                        lat, lon = gps_location.split(",")
                        order.delivery_latitude = float(lat.strip())
                        order.delivery_longitude = float(lon.strip())
                        logger.info(f"📍 GPS parseado: lat={order.delivery_latitude}, lon={order.delivery_longitude}")
                    except (ValueError, AttributeError) as e:
                        logger.error(f"❌ Error parseando GPS: {e}")
                        order.delivery_latitude = None
                        order.delivery_longitude = None
                
                order.delivery_reference = result.filled_slots.get("delivery_reference", "")
                order.payment_method = result.filled_slots.get("payment_method")
                # ⚠️ Mantener en PENDING - El admin confirmará cuando reciba el pago
                # order.status permanece como "pending"
                
                db.commit()
                db.refresh(order)
                
                logger.info(f"✅ Orden completada (pending confirmación de pago): {order.order_number}")
                logger.info(f"   GPS: {order.delivery_latitude},{order.delivery_longitude}")
                logger.info(f"   Pago: {order.payment_method}")
                
                order_service = OrderService(db)
                summary = order_service.format_order_summary(order)
                
                # Formatear GPS para mostrar
                gps_display = f"{order.delivery_latitude},{order.delivery_longitude}" if order.delivery_latitude else "No especificada"
                
                response = (
                    f"✅ *¡Orden Recibida!*\n\n"
                    f"{summary}\n\n"
                    f"📍 *Ubicación:* {gps_display}\n"
                )
                
                if order.delivery_reference and order.delivery_reference.lower() != "ninguna":
                    response += f"🏠 *Referencia:* {order.delivery_reference}\n"
                
                response += (
                    f"💳 *Método de pago:* {order.payment_method}\n\n"
                    f"⏳ Tu orden está *pendiente de confirmación*.\n"
                    f"Te notificaremos cuando confirmemos tu pago y tu pedido esté listo para ser procesado.\n\n"
                    f"¡Gracias por tu compra! 😊"
                )
                
                # Limpiar contexto
                context_updates.update({
                    "current_module": None,
                    "checkout_order_id": None,
                    "start_checkout": False,
                    "cart_session_token": None,
                    "awaiting_cart_completion": False,
                    "slots_data": {},
                    "current_slot": None,
                    "validation_attempts": {},
                    "conversation_state": "completed"
                })
                
                return {
                    "response": response,
                    "context_updates": context_updates
                }
        
        except Exception as e:
            import traceback
            logger.error(f"❌ Error en CheckoutModule: {e}")
            logger.error(f"📜 Traceback completo:\n{traceback.format_exc()}")
            return {
                "response": "❌ Hubo un error procesando tu checkout. Por favor contacta al administrador.",
                "context_updates": {
                    "current_module": None,
                    "conversation_state": "failed"
                }
            }

