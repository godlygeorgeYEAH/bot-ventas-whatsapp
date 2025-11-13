"""
Script simple para confirmar órdenes pendientes

Este script:
1. Lista todas las órdenes PENDING (pendientes de confirmación)
2. Permite seleccionar una orden para confirmar
3. Al confirmar, reduce el stock y cambia el estado a CONFIRMED

Uso:
    python scripts/confirm_order.py
    python scripts/confirm_order.py --order ORD-20251113-001
"""
import sys
from pathlib import Path
import io

# Configurar UTF-8 para Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Agregar directorio raíz al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from config.database import get_db_context
from app.services.order_service import OrderService
from app.database.models import OrderStatus, Order
from loguru import logger
from datetime import datetime


def list_pending_orders():
    """Lista todas las órdenes pendientes de confirmación"""
    with get_db_context() as db:
        orders = db.query(Order).filter(
            Order.status == OrderStatus.PENDING.value
        ).order_by(Order.created_at.desc()).all()

        if not orders:
            print("✅ No hay órdenes pendientes de confirmación")
            return []

        print(f"\n⏳ ÓRDENES PENDIENTES DE CONFIRMACIÓN ({len(orders)}):")
        print("-" * 120)
        print(f"{'#':<3} {'Número':<20} {'Cliente':<15} {'Total':>10} {'Método Pago':<15} {'Fecha':<19}")
        print("-" * 120)

        for i, order in enumerate(orders, 1):
            customer_phone = order.customer.phone if order.customer else 'N/A'
            fecha = order.created_at.strftime('%Y-%m-%d %H:%M:%S') if order.created_at else 'N/A'
            payment = order.payment_method or 'No especificado'
            print(f"{i:<3} {order.order_number:<20} {customer_phone:<15} ${order.total:>9.2f} {payment:<15} {fecha}")

        print("-" * 120)
        return orders


def show_order_details(order: Order):
    """Muestra detalles de una orden"""
    print("\n" + "="*80)
    print("📦 DETALLES DE LA ORDEN")
    print("="*80)
    print(f"Número: {order.order_number}")
    print(f"Cliente: {order.customer.phone if order.customer else 'N/A'}")
    print(f"Estado: {order.status}")
    print(f"Total: ${order.total:.2f}")
    print(f"Método de pago: {order.payment_method or 'No especificado'}")

    if order.delivery_latitude and order.delivery_longitude:
        print(f"Ubicación GPS: {order.delivery_latitude}, {order.delivery_longitude}")

    if order.delivery_reference:
        print(f"Referencia: {order.delivery_reference}")

    print(f"\nProductos:")
    print("-" * 80)
    for item in order.items:
        print(f"  • {item.product_name} x{item.quantity} - ${item.price:.2f} c/u = ${item.subtotal:.2f}")
    print("-" * 80)
    print(f"Total: ${order.total:.2f}")
    print("="*80)


def confirm_order_interactive(order_number: str = None):
    """Confirma una orden de manera interactiva"""
    with get_db_context() as db:
        order_service = OrderService(db)

        # Si no se proporciona número, listar y seleccionar
        if not order_number:
            pending_orders = list_pending_orders()

            if not pending_orders:
                return False

            print("\n¿Qué orden deseas confirmar?")
            choice = input("Ingresa el número (o 0 para cancelar): ").strip()

            if choice == "0":
                print("❌ Cancelado")
                return False

            # Buscar por índice o número de orden
            if choice.isdigit() and 1 <= int(choice) <= len(pending_orders):
                order = pending_orders[int(choice) - 1]
            else:
                order = order_service.get_order_by_number(choice)
        else:
            order = order_service.get_order_by_number(order_number)

        if not order:
            print(f"❌ Orden no encontrada: {order_number or choice}")
            return False

        # Mostrar detalles
        show_order_details(order)

        # Confirmar acción
        print("\n⚠️  Al confirmar esta orden:")
        print("   • El estado cambiará a CONFIRMED")
        print("   • Se reducirá el stock de los productos")
        print("   • Se notificará al cliente por WhatsApp")

        confirm = input("\n¿Confirmar orden? (SI/no): ").strip().upper()

        if confirm not in ['SI', 'SÍ', 'S', 'YES', 'Y', '']:
            print("❌ Confirmación cancelada")
            return False

        try:
            # Confirmar orden (esto reduce el stock automáticamente)
            confirmed_order = order_service.confirm_order(order.id)

            print("\n" + "="*80)
            print("✅ ORDEN CONFIRMADA EXITOSAMENTE")
            print("="*80)
            print(f"Número: {confirmed_order.order_number}")
            print(f"Estado: {confirmed_order.status}")
            print(f"Total: ${confirmed_order.total:.2f}")

            if confirmed_order.confirmed_at:
                print(f"Confirmada: {confirmed_order.confirmed_at.strftime('%Y-%m-%d %H:%M:%S')}")

            print("\n📦 Stock reducido para:")
            for item in confirmed_order.items:
                print(f"  • {item.product_name}: -{item.quantity} unidades")

            print("\n💬 El cliente recibirá una notificación por WhatsApp")
            print("="*80)

            return True

        except Exception as e:
            print(f"\n❌ Error confirmando orden: {e}")
            logger.error(f"Error confirmando orden {order.order_number}: {e}", exc_info=True)
            return False


def confirm_all_pending():
    """Confirma todas las órdenes pendientes (usar con precaución)"""
    with get_db_context() as db:
        order_service = OrderService(db)

        pending_orders = list_pending_orders()

        if not pending_orders:
            return

        print(f"\n⚠️  ¡ADVERTENCIA! Vas a confirmar {len(pending_orders)} órdenes")
        confirm = input("¿Estás seguro? Escribe 'CONFIRMAR TODAS': ").strip()

        if confirm != "CONFIRMAR TODAS":
            print("❌ Cancelado")
            return

        success_count = 0
        failed_count = 0

        for order in pending_orders:
            try:
                order_service.confirm_order(order.id)
                print(f"✅ {order.order_number} confirmada")
                success_count += 1
            except Exception as e:
                print(f"❌ {order.order_number} falló: {e}")
                failed_count += 1

        print(f"\n📊 Resultado:")
        print(f"   ✅ Confirmadas: {success_count}")
        print(f"   ❌ Fallidas: {failed_count}")


def main():
    """Función principal"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Confirma órdenes pendientes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python scripts/confirm_order.py                    # Modo interactivo
  python scripts/confirm_order.py --order ORD-20251113-001  # Confirmar orden específica
  python scripts/confirm_order.py --list            # Solo listar pendientes
  python scripts/confirm_order.py --all             # Confirmar todas (¡cuidado!)
        """
    )

    parser.add_argument(
        "--order",
        type=str,
        help="Número de orden a confirmar"
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="Solo listar órdenes pendientes"
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Confirmar TODAS las órdenes pendientes (usar con precaución)"
    )

    args = parser.parse_args()

    print("\n" + "="*80)
    print("✅ CONFIRMADOR DE ÓRDENES")
    print("="*80)

    if args.list:
        list_pending_orders()

    elif args.all:
        confirm_all_pending()

    elif args.order:
        confirm_order_interactive(args.order)

    else:
        # Modo interactivo por defecto
        confirm_order_interactive()


if __name__ == "__main__":
    main()
