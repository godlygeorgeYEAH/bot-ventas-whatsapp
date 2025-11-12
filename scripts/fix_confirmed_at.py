"""
Script para arreglar órdenes confirmadas sin confirmed_at
"""
import sys
from pathlib import Path
from datetime import datetime

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from config.database import SessionLocal
from app.database.models import Order
from loguru import logger

def fix_confirmed_at():
    db = SessionLocal()
    
    try:
        # Buscar órdenes confirmadas SIN confirmed_at
        broken_orders = db.query(Order).filter(
            Order.status == "confirmed",
            Order.confirmed_at.is_(None)
        ).all()
        
        logger.info(f"🔍 Encontradas {len(broken_orders)} órdenes confirmadas sin confirmed_at")
        
        for order in broken_orders:
            order.confirmed_at = datetime.utcnow()
            logger.info(f"✅ Actualizada orden {order.order_number}: confirmed_at={order.confirmed_at}")
        
        db.commit()
        logger.info(f"✅ {len(broken_orders)} órdenes actualizadas")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_confirmed_at()

