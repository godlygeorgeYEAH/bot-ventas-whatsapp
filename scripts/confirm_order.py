"""
Script para confirmar órdenes manualmente desde línea de comandos

Uso:
    python scripts/confirm_order.py --list                    # Listar órdenes pendientes
    python scripts/confirm_order.py --order ORD-20250112-001  # Confirmar por número de orden
    python scripts/confirm_order.py --id <order-id>           # Confirmar por ID
    python scripts/confirm_order.py --all                     # Confirmar todas las pendientes
"""

import sys
import os
import argparse
from datetime import datetime
from typing import Optional, List

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from loguru import logger
from config.database import get_db_context
from app.database.models import Order, OrderStatus, Customer
from app.services.order_service import OrderService

# Configurar loguru
logger.remove()  # Remover handler por defecto
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO"
)
logger.add(
    "logs/confirm_order_{time:YYYY-MM-DD}.log",
    rotation="00:00",
    retention="30 days",
    level="DEBUG"
)


def list_pending_orders() -> List[Order]:
    """Lista todas las órdenes pendientes"""
    logger.info("📋 Listando órdenes pendientes...")

    try:
        with get_db_context() as db:
            orders = db.query(Order).filter(
                Order.status == OrderStatus.PENDING.value
            ).order_by(Order.created_at.desc()).all()

            if not orders:
                logger.warning("⚠️  No hay órdenes pendientes")
                return []

            logger.info(f"✅ Encontradas {len(orders)} órdenes pendientes:\n")

            for order in orders:
                customer = db.query(Customer).filter(Customer.id == order.customer_id).first()
                customer_name = customer.name if customer and customer.name else "Sin nombre"
                customer_phone = customer.phone if customer else "Sin teléfono"

                logger.info(f"  📦 {order.order_number}")
                logger.info(f"     ID: {order.id}")
                logger.info(f"     Cliente: {customer_name} ({customer_phone})")
                logger.info(f"     Total: ${order.total:.2f}")
                logger.info(f"     Items: {len(order.items)}")
                logger.info(f"     Creada: {order.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info(f"     Pago: {order.payment_method or 'No especificado'}")

                # Mostrar productos
                for item in order.items:
                    logger.info(f"       • {item.product_name} x{item.quantity} = ${item.subtotal:.2f}")

                logger.info("")

            return orders

    except Exception as e:
        logger.error(f"❌ Error listando órdenes: {e}")
        return []


def confirm_order_by_id(order_id: str) -> bool:
    """Confirma una orden por su ID"""
    logger.info(f"🔄 Confirmando orden ID: {order_id}")

    try:
        with get_db_context() as db:
            order_service = OrderService(db)

            # Obtener la orden
            order = order_service.get_order_by_id(order_id)

            if not order:
                logger.error(f"❌ Orden no encontrada: {order_id}")
                return False

            if order.status != OrderStatus.PENDING.value:
                logger.warning(f"⚠️  Orden {order.order_number} ya está en estado: {order.status}")
                return False

            logger.info(f"📦 Orden encontrada: {order.order_number}")
            logger.info(f"   Total: ${order.total:.2f}")
            logger.info(f"   Items: {len(order.items)}")

            # Confirmar orden (esto reduce el stock automáticamente)
            confirmed_order = order_service.confirm_order(order_id)

            logger.success(f"✅ Orden {confirmed_order.order_number} CONFIRMADA exitosamente")
            logger.info(f"   Estado: {confirmed_order.status}")
            logger.info(f"   Confirmada en: {confirmed_order.confirmed_at.strftime('%Y-%m-%d %H:%M:%S')}")

            return True

    except ValueError as e:
        logger.error(f"❌ Error de validación: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Error confirmando orden: {e}")
        return False


def confirm_order_by_number(order_number: str) -> bool:
    """Confirma una orden por su número de orden"""
    logger.info(f"🔄 Confirmando orden: {order_number}")

    try:
        with get_db_context() as db:
            # Buscar orden por número
            order = db.query(Order).filter(
                Order.order_number == order_number
            ).first()

            if not order:
                logger.error(f"❌ Orden no encontrada: {order_number}")
                return False

            # Confirmar usando el ID
            return confirm_order_by_id(order.id)

    except Exception as e:
        logger.error(f"❌ Error buscando orden: {e}")
        return False


def confirm_all_pending_orders() -> int:
    """Confirma todas las órdenes pendientes"""
    logger.warning("⚠️  ¿Estás seguro de confirmar TODAS las órdenes pendientes?")
    response = input("Escribe 'SI' para continuar: ")

    if response.upper() != "SI":
        logger.info("❌ Operación cancelada")
        return 0

    logger.info("🔄 Confirmando todas las órdenes pendientes...")

    try:
        with get_db_context() as db:
            orders = db.query(Order).filter(
                Order.status == OrderStatus.PENDING.value
            ).all()

            if not orders:
                logger.warning("⚠️  No hay órdenes pendientes")
                return 0

            logger.info(f"📦 Encontradas {len(orders)} órdenes pendientes")

            confirmed_count = 0
            for order in orders:
                try:
                    logger.info(f"\n🔄 Procesando {order.order_number}...")
                    if confirm_order_by_id(order.id):
                        confirmed_count += 1
                except Exception as e:
                    logger.error(f"❌ Error confirmando {order.order_number}: {e}")
                    continue

            logger.success(f"\n✅ Confirmadas {confirmed_count}/{len(orders)} órdenes")
            return confirmed_count

    except Exception as e:
        logger.error(f"❌ Error en confirmación masiva: {e}")
        return 0


def get_order_details(order_number_or_id: str) -> Optional[Order]:
    """Muestra detalles de una orden"""
    logger.info(f"🔍 Buscando orden: {order_number_or_id}")

    try:
        with get_db_context() as db:
            # Intentar buscar por número primero
            order = db.query(Order).filter(
                Order.order_number == order_number_or_id
            ).first()

            # Si no se encuentra, intentar por ID
            if not order:
                order = db.query(Order).filter(
                    Order.id == order_number_or_id
                ).first()

            if not order:
                logger.error(f"❌ Orden no encontrada: {order_number_or_id}")
                return None

            # Obtener cliente
            customer = db.query(Customer).filter(Customer.id == order.customer_id).first()

            logger.info(f"\n📦 DETALLES DE ORDEN\n")
            logger.info(f"  Número: {order.order_number}")
            logger.info(f"  ID: {order.id}")
            logger.info(f"  Estado: {order.status}")
            logger.info("")
            logger.info(f"  👤 Cliente:")
            if customer:
                logger.info(f"     Nombre: {customer.name or 'Sin nombre'}")
                logger.info(f"     Teléfono: {customer.phone}")
                logger.info(f"     Email: {customer.email or 'No especificado'}")
            logger.info("")
            logger.info(f"  💰 Montos:")
            logger.info(f"     Subtotal: ${order.subtotal:.2f}")
            logger.info(f"     Impuestos: ${order.tax:.2f}")
            logger.info(f"     Envío: ${order.shipping_cost:.2f}")
            logger.info(f"     Descuento: ${order.discount:.2f}")
            logger.info(f"     TOTAL: ${order.total:.2f}")
            logger.info("")
            logger.info(f"  📍 Entrega:")
            logger.info(f"     GPS: {order.delivery_latitude},{order.delivery_longitude}" if order.delivery_latitude else "     GPS: No especificado")
            logger.info(f"     Referencia: {order.delivery_reference or 'No especificada'}")
            logger.info(f"     Ciudad: {order.delivery_city or 'No especificada'}")
            logger.info("")
            logger.info(f"  💳 Pago:")
            logger.info(f"     Método: {order.payment_method or 'No especificado'}")
            logger.info(f"     Estado: {order.payment_status}")
            logger.info("")
            logger.info(f"  📦 Productos ({len(order.items)} items):")
            for item in order.items:
                logger.info(f"     • {item.product_name}")
                logger.info(f"       Cantidad: {item.quantity}")
                logger.info(f"       Precio unitario: ${item.unit_price:.2f}")
                logger.info(f"       Subtotal: ${item.subtotal:.2f}")
            logger.info("")
            logger.info(f"  📅 Fechas:")
            logger.info(f"     Creada: {order.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            if order.confirmed_at:
                logger.info(f"     Confirmada: {order.confirmed_at.strftime('%Y-%m-%d %H:%M:%S')}")
            if order.shipped_at:
                logger.info(f"     Enviada: {order.shipped_at.strftime('%Y-%m-%d %H:%M:%S')}")
            if order.delivered_at:
                logger.info(f"     Entregada: {order.delivered_at.strftime('%Y-%m-%d %H:%M:%S')}")

            return order

    except Exception as e:
        logger.error(f"❌ Error obteniendo detalles: {e}")
        return None


def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description="Script para confirmar órdenes del bot de ventas WhatsApp"
    )

    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='Listar todas las órdenes pendientes'
    )

    parser.add_argument(
        '--order', '-o',
        type=str,
        help='Confirmar orden por número de orden (ej: ORD-20250112-001)'
    )

    parser.add_argument(
        '--id',
        type=str,
        help='Confirmar orden por ID'
    )

    parser.add_argument(
        '--all',
        action='store_true',
        help='Confirmar todas las órdenes pendientes'
    )

    parser.add_argument(
        '--details', '-d',
        type=str,
        help='Ver detalles de una orden (por número o ID)'
    )

    args = parser.parse_args()

    # Si no hay argumentos, mostrar ayuda
    if len(sys.argv) == 1:
        parser.print_help()
        return

    logger.info("🚀 Iniciando script de confirmación de órdenes\n")

    try:
        if args.list:
            list_pending_orders()

        elif args.order:
            success = confirm_order_by_number(args.order)
            sys.exit(0 if success else 1)

        elif args.id:
            success = confirm_order_by_id(args.id)
            sys.exit(0 if success else 1)

        elif args.all:
            confirmed = confirm_all_pending_orders()
            sys.exit(0 if confirmed > 0 else 1)

        elif args.details:
            order = get_order_details(args.details)
            sys.exit(0 if order else 1)

        else:
            parser.print_help()

    except KeyboardInterrupt:
        logger.warning("\n⚠️  Operación cancelada por el usuario")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Error inesperado: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
