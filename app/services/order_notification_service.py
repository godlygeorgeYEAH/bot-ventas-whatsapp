"""
Servicio para notificar a usuarios sobre cambios de estado en órdenes
"""
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from loguru import logger

from app.database.models import Order, Customer
from app.clients.waha_client import WAHAClient
from config.settings import settings


class OrderNotificationService:
    """Servicio para monitorear y notificar cambios en órdenes"""
    
    def __init__(self, db: Session):
        self.db = db
        self.waha = WAHAClient()
    
    async def check_and_notify_confirmed_orders(self) -> int:
        """
        Revisa órdenes que pasaron de pending a confirmed
        y notifica a los clientes
        
        Returns:
            Número de notificaciones enviadas
        """
        try:
            # Buscar órdenes confirmadas recientemente (últimas 24 horas)
            # que no han sido notificadas
            recent_confirmed = self.db.query(Order).filter(
                Order.status == "confirmed",
                Order.confirmed_at.isnot(None),
                # Solo órdenes confirmadas en las últimas 24 horas
                Order.confirmed_at >= datetime.utcnow() - timedelta(hours=24)
            ).all()
            
            logger.debug(f"🔍 [OrderNotification] Encontradas {len(recent_confirmed)} órdenes confirmadas en últimas 24h")
            
            notifications_sent = 0
            
            for order in recent_confirmed:
                logger.debug(f"🔍 [OrderNotification] Revisando orden {order.order_number}, confirmed_at={order.confirmed_at}")
                # Verificar si ya fue notificada
                # (podríamos agregar un campo order.notification_sent)
                # Por ahora, verificamos si confirmed_at es muy reciente (últimos 5 minutos)
                time_since_confirmed = datetime.utcnow() - order.confirmed_at
                
                logger.debug(f"   ⏱️ Tiempo desde confirmación: {time_since_confirmed.total_seconds():.0f} segundos")
                
                # Solo notificar órdenes confirmadas en los últimos 30 minutos
                # TODO: Implementar campo notification_sent en Order para evitar duplicados
                if time_since_confirmed > timedelta(minutes=30):
                    logger.debug(f"   ⏭️ Orden {order.order_number} muy antigua para notificar (>{time_since_confirmed.total_seconds():.0f}s)")
                    continue
                
                logger.debug(f"   ✅ Orden {order.order_number} dentro de ventana de notificación")
                
                # Obtener customer
                customer = self.db.query(Customer).filter(
                    Customer.id == order.customer_id
                ).first()
                
                if not customer or not customer.phone:
                    logger.warning(f"⚠️ Customer no encontrado para orden {order.order_number}")
                    continue
                
                logger.debug(f"   📞 Enviando notificación a {customer.phone}...")
                
                # Enviar notificación
                success = await self._send_confirmation_notification(order, customer)
                
                if success:
                    notifications_sent += 1
                    logger.info(f"✅ Notificación enviada para orden {order.order_number} a {customer.phone}")
                else:
                    logger.warning(f"⚠️ Falló enviar notificación para orden {order.order_number}")
            
            return notifications_sent
            
        except Exception as e:
            logger.error(f"❌ Error en check_and_notify_confirmed_orders: {e}")
            return 0
    
    async def _send_confirmation_notification(
        self, 
        order: Order, 
        customer: Customer
    ) -> bool:
        """
        Envía notificación de confirmación de pago al cliente (con retry logic)
        
        Returns:
            True si se envió exitosamente
        """
        try:
            from app.services.webhook_retry_service import webhook_retry_service
            
            # Formatear mensaje
            message = self._format_confirmation_message(order)
            
            # Enviar por WhatsApp con retry logic
            success, result = await webhook_retry_service.execute_with_retry(
                self.waha.send_text_message,
                f"Notificación confirmación orden {order.order_number}",
                customer.phone,
                message
            )
            
            if not success:
                logger.error(f"❌ Error enviando notificación a {customer.phone} después de reintentos: {result}")
                
                # ⚠️ FALLBACK: Notificación crítica después de 4 intentos fallidos
                logger.critical(f"🚨 CRÍTICO: No se pudo notificar confirmación de orden {order.order_number} a {customer.phone}")
                
                # TODO: Implementar notificación al panel de administrador
                # - Crear sección "Notificaciones Pendientes" en dashboard
                # - Mostrar órdenes confirmadas que no se pudieron notificar
                # - Permitir re-intentar manualmente
                # - Botón "Marcar como notificado manualmente" (por llamada, etc)
                # Ejemplo:
                # await admin_notification_service.notify_failed_customer_notification(
                #     order_id=order.id,
                #     customer_phone=customer.phone,
                #     notification_type="ORDER_CONFIRMED",
                #     attempts=4
                # )
                
                # TODO: Actualizar estado del bot si múltiples fallos consecutivos
                # - Si >3 notificaciones fallan en <5 minutos → estado "incomunicado"
                # - Agregar contador de fallos recientes en memoria o Redis
                # - Auto-recuperación cuando notificaciones vuelven a funcionar
                # Ejemplo:
                # await bot_status_service.record_notification_failure(
                #     order_id=order.id,
                #     timestamp=datetime.utcnow()
                # )
                # if await bot_status_service.get_recent_failures_count(minutes=5) >= 3:
                #     await bot_status_service.update_status("incommunicado")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error enviando notificación a {customer.phone}: {e}")
            return False
    
    def _format_confirmation_message(self, order: Order) -> str:
        """Formatea el mensaje de confirmación"""
        
        # Calcular total de items
        total_items = sum(item.quantity for item in order.items)
        
        message = (
            f"🎉 *¡Pago Confirmado!*\n\n"
            f"Tu orden *{order.order_number}* ha sido confirmada.\n\n"
            f"📦 *Resumen:*\n"
        )
        
        # Listar productos
        for item in order.items:
            message += f"  • {item.product_name} x{item.quantity}\n"
        
        message += (
            f"\n💰 *Total:* ${order.total:.2f}\n"
            f"💳 *Método de pago:* {order.payment_method}\n\n"
            f"🚚 Tu pedido está siendo preparado y será enviado pronto.\n"
            f"Te notificaremos cuando esté en camino.\n\n"
            f"¡Gracias por tu compra! 😊"
        )
        
        return message
    
    async def notify_order_shipped(self, order_id: str) -> bool:
        """
        Notifica al cliente que su orden fue enviada
        
        Args:
            order_id: ID de la orden
            
        Returns:
            True si se envió exitosamente
        """
        try:
            order = self.db.query(Order).filter(Order.id == order_id).first()
            
            if not order:
                logger.warning(f"⚠️ Orden no encontrada: {order_id}")
                return False
            
            customer = self.db.query(Customer).filter(
                Customer.id == order.customer_id
            ).first()
            
            if not customer:
                logger.warning(f"⚠️ Customer no encontrado para orden {order.order_number}")
                return False
            
            message = (
                f"🚚 *¡Orden en Camino!*\n\n"
                f"Tu orden *{order.order_number}* ha sido enviada.\n\n"
                f"📍 Será entregada en la ubicación GPS que proporcionaste.\n"
            )
            
            if order.delivery_reference and order.delivery_reference.lower() != "ninguna":
                message += f"🏠 *Referencia:* {order.delivery_reference}\n"
            
            message += (
                f"\n⏰ Tiempo estimado de entrega: 1-2 horas\n\n"
                f"¡Gracias por tu paciencia! 😊"
            )
            
            # Enviar con retry logic
            from app.services.webhook_retry_service import webhook_retry_service
            
            success, result = await webhook_retry_service.execute_with_retry(
                self.waha.send_text_message,
                f"Notificación envío orden {order.order_number}",
                customer.phone,
                message
            )
            
            if success:
                logger.info(f"✅ Notificación de envío enviada para orden {order.order_number}")
            else:
                logger.error(f"❌ Error notificando envío después de reintentos: {result}")
                
                # ⚠️ FALLBACK: Notificación crítica después de 4 intentos fallidos
                logger.critical(f"🚨 CRÍTICO: No se pudo notificar envío de orden {order.order_number} a {customer.phone}")
                
                # TODO: Implementar notificación al panel de administrador
                # - Sección "Notificaciones de Envío Pendientes"
                # - Permitir re-intentar o marcar como "notificado por otro medio"
                # Ejemplo:
                # await admin_notification_service.notify_failed_customer_notification(
                #     order_id=order.id,
                #     customer_phone=customer.phone,
                #     notification_type="ORDER_SHIPPED",
                #     attempts=4
                # )
                
                # TODO: Registrar fallo para actualizar estado del bot si es necesario
                # Mismo sistema que confirmación de pago
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error notificando envío: {e}")
            return False

