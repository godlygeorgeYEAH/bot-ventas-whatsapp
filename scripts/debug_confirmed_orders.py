"""
Script para debuggear órdenes confirmadas
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from config.database import SessionLocal
from app.database.models import Order
from loguru import logger

def debug_confirmed():
    db = SessionLocal()
    
    try:
        # Buscar TODAS las órdenes confirmadas
        all_confirmed = db.query(Order).filter(
            Order.status == "confirmed"
        ).all()
        
        logger.info(f"🔍 Total órdenes con status=CONFIRMED: {len(all_confirmed)}")
        
        for order in all_confirmed:
            logger.info(f"\n📦 Orden: {order.order_number}")
            logger.info(f"   ID: {order.id}")
            logger.info(f"   Status: {order.status}")
            logger.info(f"   confirmed_at: {order.confirmed_at}")
            logger.info(f"   created_at: {order.created_at}")
            logger.info(f"   customer_id: {order.customer_id}")
            
            if order.confirmed_at:
                time_since = datetime.utcnow() - order.confirmed_at
                logger.info(f"   ⏱️ Tiempo desde confirmación: {time_since.total_seconds():.0f} segundos")
            else:
                logger.warning(f"   ⚠️ confirmed_at es NULL!")
        
        # Buscar órdenes con confirmed_at reciente (últimas 24h)
        recent = db.query(Order).filter(
            Order.status == "confirmed",
            Order.confirmed_at.isnot(None),
            Order.confirmed_at >= datetime.utcnow() - timedelta(hours=24)
        ).all()
        
        logger.info(f"\n🔍 Órdenes confirmadas en últimas 24h: {len(recent)}")
        
    finally:
        db.close()

if __name__ == "__main__":
    debug_confirmed()

