"""
Script para probar el sistema de órdenes
"""
import sys
sys.path.append('.')

from config.database import SessionLocal
from app.services.order_service import OrderService
from app.services.product_service import ProductService
from app.database.models import Customer
from loguru import logger


def test_order_system():
    """Prueba el sistema de órdenes"""
    
    db = SessionLocal()
    order_service = OrderService(db)
    product_service = ProductService(db)
    
    logger.info("=" * 60)
    logger.info("🧪 Probando Sistema de Órdenes")
    logger.info("=" * 60)
    
    try:
        # 1. Obtener un cliente de prueba
        customer = db.query(Customer).first()
        
        if not customer:
            logger.error("❌ No hay clientes en la BD. Crea uno primero.")
            return
        
        logger.info(f"\n1️⃣ Cliente de prueba: {customer.phone}")
        
        # 2. Obtener algunos productos
        products = product_service.get_all_products()[:3]
        
        logger.info(f"\n2️⃣ Productos para la orden:")
        for p in products:
            logger.info(f"   - {p.name} (${p.price}) - Stock: {p.stock}")
        
        # 3. Crear orden
        logger.info(f"\n3️⃣ Creando orden...")
        
        items = [
            {"product_id": products[0].id, "quantity": 2},
            {"product_id": products[1].id, "quantity": 1}
        ]
        
        order = order_service.create_order(
            customer_id=customer.id,
            items=items,
            delivery_address="Calle 123 #45-67, Bogotá",
            delivery_city="Bogotá",
            payment_method="tarjeta",
            shipping_cost=10.0,
            tax_rate=0.19  # 19% IVA
        )
        
        logger.info(f"✅ Orden creada: {order.order_number}")
        
        # 4. Mostrar resumen
        logger.info(f"\n4️⃣ Resumen de la orden:")
        print(order_service.format_order_summary(order))
        
        # 5. Confirmar orden
        logger.info(f"\n5️⃣ Confirmando orden...")
        confirmed_order = order_service.confirm_order(order.id)
        logger.info(f"✅ Orden confirmada: {confirmed_order.status}")
        
        # 6. Ver órdenes del cliente
        logger.info(f"\n6️⃣ Órdenes del cliente:")
        customer_orders = order_service.get_customer_orders(customer.id)
        for o in customer_orders:
            logger.info(f"   - {o.order_number}: {o.status} (${o.total})")
        
        # 7. Cancelar orden (prueba)
        logger.info(f"\n7️⃣ Probando cancelación...")
        cancelled = order_service.cancel_order(
            order.id,
            reason="Prueba de cancelación"
        )
        logger.info(f"✅ Orden cancelada: {cancelled.status}")
        
        logger.info("\n✅ Pruebas completadas exitosamente")
        
    except Exception as e:
        logger.error(f"❌ Error en pruebas: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    test_order_system()