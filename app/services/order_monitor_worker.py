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
        logger.info("🔍 [OrderMonitorWorker] Iniciando chequeo de órdenes...")
        db = SessionLocal()
        
        try:
            notification_service = OrderNotificationService(db)
            
            # 1. Revisar y notificar órdenes confirmadas
            notifications_sent = await notification_service.check_and_notify_confirmed_orders()
            
            if notifications_sent > 0:
                logger.info(f"📨 {notifications_sent} notificaciones enviadas")
            else:
                logger.info("🔍 [OrderMonitorWorker] No hay notificaciones pendientes")
            
            # 2. Revisar órdenes pending con timeout (30 minutos)
            abandoned_count = await self._check_abandoned_orders(db)
            
            if abandoned_count > 0:
                logger.info(f"⏰ {abandoned_count} órdenes marcadas como abandonadas (timeout 30 min)")
            
        except Exception as e:
            logger.error(f"❌ Error en _check_orders: {e}", exc_info=True)
        finally:
            db.close()
    
    async def _check_abandoned_orders(self, db) -> int:
        """
        Revisa órdenes PENDING que llevan más de 30 minutos y las marca como ABANDONED
        
        Returns:
            Número de órdenes abandonadas
        """
        from datetime import datetime, timedelta
        from app.database.models import Order
        
        try:
            # Buscar órdenes PENDING que fueron creadas hace más de 30 minutos
            timeout_threshold = datetime.utcnow() - timedelta(minutes=30)
            
            pending_orders = db.query(Order).filter(
                Order.status == "pending",
                Order.created_at < timeout_threshold
            ).all()

            logger.info(f"🔍 [OrderMonitorWorker] Encontradas {len(pending_orders)} órdenes pending > 30 min")
            
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
                
                abandoned_count += 1
            
            if abandoned_count > 0:
                db.commit()
            
            return abandoned_count
            
        except Exception as e:
            logger.error(f"❌ Error en _check_abandoned_orders: {e}", exc_info=True)
            db.rollback()
            return 0


# Instancia global del worker
order_monitor_worker = OrderMonitorWorker(check_interval_seconds=60)

