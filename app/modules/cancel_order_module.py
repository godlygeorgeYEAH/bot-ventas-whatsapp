"""
Módulo para cancelar órdenes pendientes
"""
from typing import Dict, Any, Optional
from loguru import logger
from sqlalchemy.orm import Session

from app.services.order_service import OrderService
from app.database.repository import CustomerRepository
from app.database.models import OrderStatus
from config.database import get_db_context


class CancelOrderModule:
    """Módulo para cancelar órdenes pendientes con confirmación"""

    def __init__(self):
        self.name = "CancelOrderModule"
        self.intent = "cancel_order"
        self.slot_definitions = []
        self.slot_manager = None

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
        Maneja la cancelación de órdenes con flujo de confirmación

        FLUJO:
        1. Usuario expresa deseo de cancelar
        2. Bot pregunta confirmación
        3. Usuario responde SÍ/NO
        4. Bot cancela o no según respuesta

        Args:
            message: Mensaje del usuario
            context: Contexto de la conversación
            phone: Número de teléfono del usuario

        Returns:
            Dict con response y context_updates
        """
        logger.info(f"🚫 [CancelOrderModule] Procesando solicitud de cancelación")

        try:
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # CASO 1: Esperando confirmación (segundo mensaje)
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            if context.get("waiting_cancel_confirmation"):
                return self._handle_cancel_confirmation(message, context, phone)

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # CASO 2: Primera solicitud de cancelación
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            return self._request_cancel_confirmation(phone)

        except Exception as e:
            logger.error(f"❌ [CancelOrderModule] Error: {e}", exc_info=True)
            return {
                "response": "⚠️ Ocurrió un error al intentar cancelar tu orden. Por favor intenta de nuevo.",
                "context_updates": {
                    "current_module": None,
                    "waiting_cancel_confirmation": False,
                    "cancel_order_id": None,
                    "conversation_state": "active"
                }
            }

    def _request_cancel_confirmation(self, phone: str) -> Dict[str, Any]:
        """
        Primera paso: Buscar orden pendiente y pedir confirmación

        Args:
            phone: Número de teléfono del usuario

        Returns:
            Dict con mensaje de confirmación y contexto actualizado
        """
        try:
            with get_db_context() as db:
                customer_repo = CustomerRepository()
                order_service = OrderService(db)

                # Obtener cliente
                customer = customer_repo.get_or_create(phone, db)
                if not customer:
                    logger.warning(f"⚠️ Cliente no encontrado para {phone}")
                    return {
                        "response": "⚠️ No encontré tu información. Por favor intenta de nuevo.",
                        "context_updates": {
                            "current_module": None,
                            "conversation_state": "active"
                        }
                    }

                # Buscar orden pendiente o confirmada (las únicas que se pueden cancelar)
                orders = order_service.get_customer_orders(customer.id)

                # Filtrar órdenes que pueden cancelarse
                cancellable_orders = [
                    order for order in orders
                    if order.status in [OrderStatus.PENDING.value, OrderStatus.CONFIRMED.value]
                ]

                if not cancellable_orders:
                    logger.info(f"ℹ️ No hay órdenes cancelables para {phone}")
                    return {
                        "response": "No tienes ninguna orden pendiente o confirmada que pueda cancelarse.",
                        "context_updates": {
                            "current_module": None,
                            "conversation_state": "active"
                        }
                    }

                # Tomar la orden más reciente cancelable
                order = cancellable_orders[0]

                logger.info(f"📋 Orden encontrada para cancelar: {order.order_number} (estado: {order.status})")

                # Formatear resumen de la orden
                summary = order_service.format_order_summary(order)

                # Estado en español
                status_text = "pendiente de pago" if order.status == OrderStatus.PENDING.value else "confirmada"

                confirmation_message = (
                    f"🚫 *¿Estás seguro que deseas cancelar tu orden?*\n\n"
                    f"📋 *Orden:* #{order.order_number}\n"
                    f"📊 *Estado:* {status_text}\n\n"
                    f"{summary}\n\n"
                    f"⚠️ Esta acción no se puede deshacer.\n\n"
                    f"Responde *SÍ* para confirmar la cancelación o *NO* para mantener tu orden."
                )

                return {
                    "response": confirmation_message,
                    "context_updates": {
                        "current_module": "CancelOrderModule",
                        "waiting_cancel_confirmation": True,
                        "cancel_order_id": order.id,
                        "cancel_order_number": order.order_number,
                        "conversation_state": "waiting_confirmation"
                    }
                }

        except Exception as e:
            logger.error(f"❌ Error solicitando confirmación: {e}", exc_info=True)
            return {
                "response": "⚠️ Ocurrió un error al buscar tu orden. Por favor intenta de nuevo.",
                "context_updates": {
                    "current_module": None,
                    "conversation_state": "active"
                }
            }

    def _handle_cancel_confirmation(
        self,
        message: str,
        context: Dict[str, Any],
        phone: str
    ) -> Dict[str, Any]:
        """
        Segundo paso: Procesar respuesta de confirmación y cancelar o no

        Args:
            message: Mensaje del usuario (SÍ/NO)
            context: Contexto con order_id a cancelar
            phone: Número de teléfono

        Returns:
            Dict con resultado de cancelación y contexto limpio
        """
        message_lower = message.lower().strip()
        order_id = context.get("cancel_order_id")
        order_number = context.get("cancel_order_number")

        logger.info(f"🔍 Respuesta de confirmación recibida: '{message_lower}'")

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # CASO A: Usuario confirma cancelación (SÍ)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if any(word in message_lower for word in ['si', 'sí', 'yes', 'ok', 'confirmo', 'cancela']):
            logger.info(f"✅ Usuario confirmó cancelación de orden {order_number}")

            try:
                with get_db_context() as db:
                    order_service = OrderService(db)

                    # Cancelar orden (esto restaura stock si es necesario)
                    cancelled_order = order_service.cancel_order(
                        order_id=order_id,
                        reason="Cancelada por el usuario vía WhatsApp"
                    )

                    logger.info(f"✅ Orden {order_number} cancelada exitosamente")

                    # Notificar al usuario y limpiar conversación
                    from app.services.order_notification_service import OrderNotificationService
                    import asyncio

                    notification_service = OrderNotificationService(db)

                    # Ejecutar notificación asíncrona
                    try:
                        asyncio.create_task(
                            notification_service.notify_order_cancelled(
                                order_id=order_id,
                                cancelled_by_admin=False  # Cancelada por el usuario
                            )
                        )
                        logger.info(f"📤 Notificación de cancelación programada para orden {order_number}")
                    except Exception as notify_error:
                        logger.error(f"⚠️ Error programando notificación: {notify_error}")

                    return {
                        "response": (
                            f"✅ *Orden #{order_number} cancelada exitosamente*\n\n"
                            f"Tu orden ha sido cancelada. "
                            f"Si deseas hacer un nuevo pedido, simplemente escribe lo que necesitas."
                        ),
                        "context_updates": {
                            "current_module": None,
                            "waiting_cancel_confirmation": False,
                            "cancel_order_id": None,
                            "cancel_order_number": None,
                            "conversation_state": "idle"
                        }
                    }

            except Exception as e:
                logger.error(f"❌ Error cancelando orden: {e}", exc_info=True)
                return {
                    "response": (
                        f"⚠️ Ocurrió un error al cancelar tu orden.\n\n"
                        f"Por favor intenta de nuevo o contacta con soporte."
                    ),
                    "context_updates": {
                        "current_module": None,
                        "waiting_cancel_confirmation": False,
                        "cancel_order_id": None,
                        "cancel_order_number": None,
                        "conversation_state": "active"
                    }
                }

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # CASO B: Usuario rechaza cancelación (NO)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        elif any(word in message_lower for word in ['no', 'nop', 'nope', 'mantenla', 'conserva', 'dejala']):
            logger.info(f"❌ Usuario rechazó cancelación de orden {order_number}")

            return {
                "response": (
                    f"✅ Perfecto, tu orden #{order_number} se mantiene activa.\n\n"
                    f"¿Hay algo más en lo que pueda ayudarte?"
                ),
                "context_updates": {
                    "current_module": None,
                    "waiting_cancel_confirmation": False,
                    "cancel_order_id": None,
                    "cancel_order_number": None,
                    "conversation_state": "idle"
                }
            }

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # CASO C: Respuesta no reconocida
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        else:
            logger.warning(f"⚠️ Respuesta no reconocida: '{message}'")

            return {
                "response": (
                    f"⚠️ No entendí tu respuesta.\n\n"
                    f"Por favor responde *SÍ* para cancelar tu orden #{order_number} "
                    f"o *NO* para mantenerla."
                ),
                "context_updates": {
                    "current_module": "CancelOrderModule",
                    "waiting_cancel_confirmation": True,
                    "cancel_order_id": order_id,
                    "cancel_order_number": order_number,
                    "conversation_state": "waiting_confirmation"
                }
            }
