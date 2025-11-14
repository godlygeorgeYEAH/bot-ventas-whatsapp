"""
Worker para monitorear cambios de estado en órdenes y notificar clientes
"""
import asyncio
from typing import Optional
from loguru import logger

from config.database import SessionLocal
from app.services.order_notification_service import OrderNotificationService


class OrderMonitorWorker:
    """Worker que monitorea órdenes y envía notificaciones"""
    
    def __init__(self, check_interval_seconds: int = 60):
        """
        Args:
            check_interval_seconds: Intervalo entre chequeos (default: 60s)
        """
        self.check_interval = check_interval_seconds
        self.running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Inicia el worker de monitoreo"""
        if self.running:
            logger.warning("⚠️ OrderMonitorWorker ya está corriendo")
            return
        
        self.running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info(f"✅ OrderMonitorWorker iniciado (intervalo: {self.check_interval}s)")
    
    async def stop(self):
        """Detiene el worker de monitoreo"""
        if not self.running:
            return
        
        self.running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("🛑 OrderMonitorWorker detenido")
    
    async def _monitor_loop(self):
        """Loop principal de monitoreo"""
        logger.info("🔄 OrderMonitorWorker loop iniciado")
        
        while self.running:
            try:
                await self._check_orders()
            except Exception as e:
                logger.error(f"❌ Error en monitor loop: {e}")
            
            # Esperar antes del siguiente chequeo
            try:
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
    
    async def _check_orders(self):
        """Revisa órdenes y envía notificaciones si es necesario"""
        logger.debug("🔍 [OrderMonitorWorker] Iniciando chequeo de órdenes...")
        db = SessionLocal()
        
        try:
            notification_service = OrderNotificationService(db)
            
            # 1. Revisar y notificar órdenes confirmadas
            notifications_sent = await notification_service.check_and_notify_confirmed_orders()
            
            if notifications_sent > 0:
                logger.info(f"📨 {notifications_sent} notificaciones enviadas")
            else:
                logger.debug("🔍 [OrderMonitorWorker] No hay notificaciones pendientes")
            
            # 2. Revisar órdenes pending con timeout configurado
            abandoned_count = await self._check_abandoned_orders(db)

            if abandoned_count > 0:
                logger.info(f"⏰ {abandoned_count} órdenes marcadas como abandonadas")
            
        except Exception as e:
            logger.error(f"❌ Error en _check_orders: {e}", exc_info=True)
        finally:
            db.close()
    
    async def _check_abandoned_orders(self, db) -> int:
        """
        Revisa órdenes PENDING que exceden el timeout configurado y las marca como ABANDONED

        El timeout es configurable desde settings (default: 30 minutos)

        Returns:
            Número de órdenes abandonadas
        """
        from datetime import datetime, timedelta
        from app.database.models import Order, Settings

        try:
            # Leer timeout desde settings (default: 30 minutos)
            timeout_minutes = 30  # Default
            timeout_setting = db.query(Settings).filter(Settings.key == "order_timeout_minutes").first()
            if timeout_setting and isinstance(timeout_setting.value, (int, float)):
                timeout_minutes = int(timeout_setting.value)
                logger.debug(f"🕐 Timeout configurado: {timeout_minutes} minutos")

            # Buscar órdenes PENDING que fueron creadas hace más del timeout configurado
            timeout_threshold = datetime.utcnow() - timedelta(minutes=timeout_minutes)
            
            pending_orders = db.query(Order).filter(
                Order.status == "pending",
                Order.created_at < timeout_threshold
            ).all()

            logger.debug(f"🔍 [OrderMonitorWorker] Encontradas {len(pending_orders)} órdenes pending > {timeout_minutes} min")
            
            abandoned_count = 0
            
            for order in pending_orders:
                age_minutes = (datetime.utcnow() - order.created_at).total_seconds() / 60
                logger.info(f"⏰ Orden {order.order_number} sin completar por {age_minutes:.0f} minutos → Marcando como ABANDONED")
                
                # Marcar como abandonada
                order.status = "abandoned"
                order.abandoned_at = datetime.utcnow()
                order.abandonment_reason = f"Timeout: Sin completar después de {age_minutes:.0f} minutos"

                # Restaurar stock de los items
                for item in order.items:
                    if item.product_id:
                        from app.database.models import Product
                        product = db.query(Product).filter(Product.id == item.product_id).first()
                        if product:
                            product.stock += item.quantity
                            logger.debug(f"   📦 Stock restaurado para {product.name}: +{item.quantity} (nuevo stock: {product.stock})")

                # Limpiar conversación del cliente (marcar como inactiva)
                self._clear_customer_conversation(db, order.customer_id)

                abandoned_count += 1
            
            if abandoned_count > 0:
                db.commit()
            
            return abandoned_count
            
        except Exception as e:
            logger.error(f"❌ Error en _check_abandoned_orders: {e}", exc_info=True)
            db.rollback()
            return 0

    def _clear_customer_conversation(self, db, customer_id: str) -> int:
        """
        Limpia (marca como inactiva) todas las conversaciones activas de un cliente

        Args:
            db: Sesión de base de datos
            customer_id: ID del cliente

        Returns:
            Número de conversaciones limpiadas
        """
        try:
            from app.database.models import Conversation

            # Marcar todas las conversaciones como inactivas
            conversations = db.query(Conversation).filter(
                Conversation.customer_id == customer_id,
                Conversation.is_active == True
            ).all()

            for conv in conversations:
                conv.is_active = False
                logger.debug(f"   🧹 Conversación {conv.id} marcada como inactiva")

            logger.info(f"   🧹 {len(conversations)} conversaciones limpiadas para customer {customer_id}")
            return len(conversations)

        except Exception as e:
            logger.error(f"❌ Error limpiando conversaciones: {e}")
            return 0


# Instancia global del worker
order_monitor_worker = OrderMonitorWorker(check_interval_seconds=60)

