"""
Servicio para enviar notificaciones a administradores sobre cambios en órdenes
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from loguru import logger

from app.database.models import Order, Settings, Customer
from app.clients.waha_client import WAHAClient
from app.core.correlation import set_client_context


class AdminNotificationService:
    """Servicio para notificar a administradores sobre eventos de órdenes"""

    def __init__(self, db: Session):
        self.db = db
        self.waha = WAHAClient()

    def get_admin_numbers(self) -> List[str]:
        """
        Obtiene la lista de números de administradores desde la configuración

        Returns:
            Lista de números de teléfono de administradores
        """
        try:
            setting = self.db.query(Settings).filter(
                Settings.key == "admin_numbers"
            ).first()

            if not setting or not isinstance(setting.value, list):
                logger.warning("⚠️ No hay números de administrador configurados")
                return []

            admin_numbers = setting.value
            logger.debug(f"📱 {len(admin_numbers)} números de admin encontrados")
            return admin_numbers

        except Exception as e:
            logger.error(f"❌ Error obteniendo números de admin: {e}")
            return []

    async def notify_order_created(self, order: Order) -> int:
        """
        Notifica a los admins cuando se crea una nueva orden

        Args:
            order: La orden creada

        Returns:
            Número de notificaciones enviadas exitosamente
        """
        return await self._send_order_notification(
            order=order,
            event_type="created",
            title="🆕 Nueva Orden",
            status_emoji="⏳"
        )

    async def notify_order_confirmed(self, order: Order) -> int:
        """
        Notifica a los admins cuando una orden es confirmada

        Args:
            order: La orden confirmada

        Returns:
            Número de notificaciones enviadas exitosamente
        """
        return await self._send_order_notification(
            order=order,
            event_type="confirmed",
            title="✅ Orden Confirmada",
            status_emoji="✅"
        )

    async def notify_order_shipped(self, order: Order) -> int:
        """
        Notifica a los admins cuando una orden es enviada

        Args:
            order: La orden enviada

        Returns:
            Número de notificaciones enviadas exitosamente
        """
        return await self._send_order_notification(
            order=order,
            event_type="shipped",
            title="🚚 Orden Enviada",
            status_emoji="🚚"
        )

    async def notify_order_delivered(self, order: Order) -> int:
        """
        Notifica a los admins cuando una orden es entregada

        Args:
            order: La orden entregada

        Returns:
            Número de notificaciones enviadas exitosamente
        """
        return await self._send_order_notification(
            order=order,
            event_type="delivered",
            title="📦 Orden Entregada",
            status_emoji="✅"
        )

    async def notify_order_cancelled(self, order: Order, reason: str = None) -> int:
        """
        Notifica a los admins cuando una orden es cancelada

        Args:
            order: La orden cancelada
            reason: Razón de cancelación (opcional)

        Returns:
            Número de notificaciones enviadas exitosamente
        """
        extra_info = f"\n❌ *Razón:* {reason}" if reason else ""

        return await self._send_order_notification(
            order=order,
            event_type="cancelled",
            title="❌ Orden Cancelada",
            status_emoji="❌",
            extra_info=extra_info
        )

    async def notify_order_modified(self, order: Order, modification_type: str) -> int:
        """
        Notifica a los admins cuando una orden es modificada

        Args:
            order: La orden modificada
            modification_type: Tipo de modificación ("items_added", "items_removed", etc.)

        Returns:
            Número de notificaciones enviadas exitosamente
        """
        modification_messages = {
            "items_added": "➕ Items agregados",
            "items_removed": "➖ Items eliminados",
            "status_changed": "🔄 Estado actualizado"
        }

        extra_info = f"\n🔧 *Modificación:* {modification_messages.get(modification_type, modification_type)}"

        return await self._send_order_notification(
            order=order,
            event_type="modified",
            title="🔧 Orden Modificada",
            status_emoji="🔄",
            extra_info=extra_info
        )

    async def _send_order_notification(
        self,
        order: Order,
        event_type: str,
        title: str,
        status_emoji: str,
        extra_info: str = ""
    ) -> int:
        """
        Envía notificación sobre una orden a todos los administradores

        Args:
            order: La orden
            event_type: Tipo de evento (created, confirmed, etc.)
            title: Título de la notificación
            status_emoji: Emoji para el estado
            extra_info: Información adicional (opcional)

        Returns:
            Número de notificaciones enviadas exitosamente
        """
        try:
            # Obtener números de admin
            admin_numbers = self.get_admin_numbers()

            if not admin_numbers:
                logger.warning(f"⚠️ No se enviaron notificaciones de admin para orden {order.order_number} (no hay admins configurados)")
                return 0

            # Obtener cliente
            customer = self.db.query(Customer).filter(
                Customer.id == order.customer_id
            ).first()

            if not customer:
                logger.warning(f"⚠️ Customer no encontrado para orden {order.order_number}")
                return 0

            # Establecer contexto de cliente para tracking en logs
            set_client_context(customer.phone, order.conversation_id)

            # Formatear mensaje
            message = self._format_order_message(
                order=order,
                customer=customer,
                title=title,
                status_emoji=status_emoji,
                extra_info=extra_info
            )

            # Enviar a todos los admins
            sent_count = 0
            for admin_number in admin_numbers:
                try:
                    # Usar retry logic si está disponible
                    from app.services.webhook_retry_service import webhook_retry_service

                    success, result = await webhook_retry_service.execute_with_retry(
                        self.waha.send_text_message,
                        f"Notificación admin - {event_type} - {order.order_number}",
                        admin_number,
                        message
                    )

                    if success:
                        sent_count += 1
                        logger.info(f"✅ Notificación enviada a admin {admin_number}: {order.order_number} ({event_type})")
                    else:
                        logger.error(f"❌ Error enviando notificación a admin {admin_number}: {result}")

                except Exception as e:
                    logger.error(f"❌ Error enviando notificación a admin {admin_number}: {e}")
                    continue

            logger.info(f"📤 Notificaciones de admin enviadas: {sent_count}/{len(admin_numbers)} para orden {order.order_number}")
            return sent_count

        except Exception as e:
            logger.error(f"❌ Error enviando notificaciones de admin: {e}")
            return 0

    def _format_order_message(
        self,
        order: Order,
        customer: Customer,
        title: str,
        status_emoji: str,
        extra_info: str = ""
    ) -> str:
        """
        Formatea el mensaje de notificación para administradores

        Args:
            order: La orden
            customer: El cliente
            title: Título del mensaje
            status_emoji: Emoji del estado
            extra_info: Información adicional

        Returns:
            Mensaje formateado
        """
        # Calcular total de items
        total_items = sum(item.quantity for item in order.items)

        # Construir mensaje
        message = (
            f"🔔 *{title}*\n\n"
            f"📝 *Orden:* {order.order_number}\n"
            f"👤 *Cliente:* {customer.name or 'N/A'}\n"
            f"📱 *Teléfono:* +{customer.phone}\n"
            f"💰 *Total:* ${order.total:.2f}\n"
            f"{status_emoji} *Estado:* {self._get_status_text(order.status)}\n\n"
        )

        # Agregar items
        message += "📦 *Items:*\n"
        for item in order.items[:5]:  # Mostrar máximo 5 items
            message += f"  • {item.product_name} x{item.quantity} (${item.subtotal:.2f})\n"

        if len(order.items) > 5:
            remaining = len(order.items) - 5
            message += f"  ... y {remaining} más\n"

        # Agregar información de entrega si existe
        if order.delivery_latitude and order.delivery_longitude:
            message += f"\n📍 *Ubicación GPS:* {order.delivery_latitude}, {order.delivery_longitude}\n"

        if order.delivery_reference and order.delivery_reference.lower() != "ninguna":
            message += f"🏠 *Referencia:* {order.delivery_reference}\n"

        # Método de pago
        if order.payment_method:
            message += f"\n💳 *Pago:* {order.payment_method}\n"

        # Información adicional
        if extra_info:
            message += extra_info

        # Timestamp
        message += f"\n🕐 {order.updated_at.strftime('%d/%m/%Y %H:%M')}"

        return message

    def _get_status_text(self, status: str) -> str:
        """
        Convierte el código de estado a texto legible en español

        Args:
            status: Código de estado

        Returns:
            Texto del estado en español
        """
        status_map = {
            "pending": "Pendiente",
            "confirmed": "Confirmada",
            "shipped": "En Camino",
            "delivered": "Entregada",
            "cancelled": "Cancelada",
            "abandoned": "Abandonada",
            "processing": "En Proceso"
        }

        return status_map.get(status, status.capitalize())
