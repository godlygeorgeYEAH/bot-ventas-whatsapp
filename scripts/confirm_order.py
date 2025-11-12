#!/usr/bin/env python3
"""
Script para marcar una orden como confirmada manualmente
Uso: python scripts/confirm_order.py ORD-20251112-020
"""
import sys
from datetime import datetime
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.database import SessionLocal
from app.database.models import Order
from app.utils.logger import logger


def confirm_order(order_number: str):
    """
    Marca una orden como confirmada

    Args:
        order_number: Número de orden (ej. ORD-20251112-020)
    """
    db = SessionLocal()

    try:
        # Buscar orden por número
        order = db.query(Order).filter(Order.order_number == order_number).first()

        if not order:
            logger.error(f"❌ No se encontró la orden {order_number}")
            return False

        # Mostrar estado actual
        logger.info(f"📦 Orden encontrada: {order.order_number}")
        logger.info(f"   Estado actual: {order.status}")
        logger.info(f"   confirmed_at: {order.confirmed_at}")
        logger.info(f"   notification_sent_at: {order.notification_sent_at}")

        # Marcar como confirmada
        order.status = "confirmed"
        order.confirmed_at = datetime.utcnow()
        # notification_sent_at queda NULL para que el notificador la detecte

        db.commit()
        db.refresh(order)

        logger.info(f"✅ Orden {order.order_number} marcada como CONFIRMED")
        logger.info(f"   confirmed_at: {order.confirmed_at}")
        logger.info(f"   notification_sent_at: {order.notification_sent_at}")
        logger.info(f"\n🔔 El OrderMonitorWorker debería detectar y notificar esta orden en el próximo ciclo (máx. 60 segundos)")

        return True

    except Exception as e:
        logger.error(f"❌ Error confirmando orden: {e}", exc_info=True)
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python scripts/confirm_order.py <NUMERO_ORDEN>")
        print("Ejemplo: python scripts/confirm_order.py ORD-20251112-020")
        sys.exit(1)

    order_number = sys.argv[1]
    success = confirm_order(order_number)
    sys.exit(0 if success else 1)
