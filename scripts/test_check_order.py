"""
Script de prueba para CheckOrderModule
"""
import sys
from pathlib import Path

# Agregar directorio raíz al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

import asyncio
from loguru import logger
from config.database import get_db_context
from app.modules.check_order_module import CheckOrderModule
from app.database.repository import CustomerRepository
from app.services.order_service import OrderService
from app.services.product_service import ProductService


async def test_check_order():
    """Test del módulo CheckOrderModule"""
    
    logger.info("=" * 60)
    logger.info("TEST: CheckOrderModule")
    logger.info("=" * 60)
    
    module = CheckOrderModule()
    
    # Obtener cliente de prueba
    with get_db_context() as db:
        customer_repo = CustomerRepository()
        order_service = OrderService(db)
        
        # Buscar un cliente con órdenes (get_or_create crea si no existe)
        customer = customer_repo.get_or_create("573001234567", db)
        
        if not customer:
            logger.error("❌ No hay cliente de prueba. Ejecuta seed_customers.py primero")
            return
        
        logger.info(f"✅ Cliente encontrado: {customer.phone}")
        
        # Verificar si tiene órdenes
        orders = order_service.get_customer_orders(customer.id)
        
        if not orders:
            logger.warning("⚠️ El cliente no tiene órdenes. Creando una orden de prueba...")
            
            # Crear orden de prueba
            product_service = ProductService(db)
            products = product_service.get_all_products()
            
            if not products:
                logger.error("❌ No hay productos. Ejecuta seed_products.py primero")
                return
            
            # Crear orden simple
            order = order_service.create_order(
                customer_id=customer.id,
                items=[
                    {"product_id": products[0].id, "quantity": 1}
                ],
                delivery_address="Calle de Prueba 123",
                delivery_latitude=10.9685,
                delivery_longitude=-74.7813,
                delivery_reference="Casa amarilla",
                payment_method="cash"
            )
            
            # Confirmar orden
            order_service.confirm_order(order.id)
            
            logger.info(f"✅ Orden de prueba creada: {order.order_number}")
            
            orders = [order]
        
        test_order = orders[0]
        logger.info(f"📦 Usando orden para prueba: {test_order.order_number}")
    
    # ===== TEST 1: Consulta simple (sin especificar número) =====
    logger.info("\n" + "=" * 60)
    logger.info("TEST 1: Consulta simple - Muestra última orden relevante automáticamente")
    logger.info("=" * 60)
    logger.info("💡 El usuario NO tiene que dar el número de orden")
    logger.info("💡 El LLM detecta la intención y el módulo responde automáticamente")
    
    result = await module.handle(
        message="cómo va mi pedido",  # Mensaje natural
        context={},
        phone=customer.phone
    )
    
    logger.info(f"\n📤 Respuesta:\n{result['response']}")
    logger.info(f"\n📊 Context updates: {result['context_updates']}")
    
    # ===== TEST 2: Última orden relevante (NEW BEHAVIOR) =====
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: Última orden relevante (confirmed/shipped/delivered)")
    logger.info("=" * 60)
    
    result = await module.handle(
        message="mi orden",
        context={},
        phone=customer.phone
    )
    
    logger.info(f"\n📤 Respuesta:\n{result['response']}")
    logger.info("\n💡 NOTA: Solo muestra órdenes con estado confirmed/shipped/delivered")
    logger.info("         (No muestra pending ni cancelled)")
    
    # ===== TEST 3: Diferentes formas de preguntar =====
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: Diferentes maneras de consultar (variación de lenguaje)")
    logger.info("=" * 60)
    
    test_messages = [
        "dónde está mi pedido",
        "ya enviaron mi orden",
        "cuándo llega",
        "información de mi compra"
    ]
    
    for msg in test_messages:
        logger.info(f"\n🔹 Mensaje: '{msg}'")
        result = await module.handle(
            message=msg,
            context={},
            phone=customer.phone
        )
        # Solo mostrar primeras líneas para no saturar
        response_preview = result['response'][:200] + "..." if len(result['response']) > 200 else result['response']
        logger.info(f"✅ Respuesta (preview): {response_preview}")
    
    # ===== TEST 4: Cliente sin órdenes =====
    logger.info("\n" + "=" * 60)
    logger.info("TEST 4: Cliente sin órdenes")
    logger.info("=" * 60)
    
    result = await module.handle(
        message="mis pedidos",
        context={},
        phone="999999999"  # Teléfono que no existe
    )
    
    logger.info(f"\n📤 Respuesta:\n{result['response']}")
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ TESTS COMPLETADOS")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_check_order())

