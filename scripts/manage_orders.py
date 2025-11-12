"""
Script interactivo para gestionar órdenes
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
from app.database.models import OrderStatus
from loguru import logger
from tabulate import tabulate


def list_orders(limit=10):
    """Lista las órdenes más recientes"""
    with get_db_context() as db:
        order_service = OrderService(db)
        
        # Obtener todas las órdenes ordenadas por fecha
        orders = db.query(
            order_service.db.query(order_service.db.query.__class__).statement.table
        ).order_by('created_at DESC').limit(limit).all()
        
        if not orders:
            print("❌ No hay órdenes en la base de datos")
            return
        
        # Preparar datos para tabla
        table_data = []
        for order in orders:
            table_data.append([
                order.order_number,
                order.customer.phone if hasattr(order, 'customer') else 'N/A',
                order.status,
                f"${order.total:.2f}",
                order.created_at.strftime('%Y-%m-%d %H:%M') if order.created_at else 'N/A'
            ])
        
        headers = ["Número", "Cliente", "Estado", "Total", "Fecha"]
        print("\n📦 ÓRDENES RECIENTES:")
        print(tabulate(table_data, headers=headers, tablefmt="grid"))


def get_order_details(order_number: str):
    """Muestra detalles completos de una orden"""
    with get_db_context() as db:
        order_service = OrderService(db)
        order = order_service.get_order_by_number(order_number)
        
        if not order:
            print(f"❌ Orden {order_number} no encontrada")
            return
        
        print("\n" + "="*60)
        print(order_service.format_order_summary(order))
        print("="*60)


def change_order_status(order_number: str, new_status: str):
    """Cambia el estado de una orden"""
    # Validar estado
    valid_statuses = [status.value for status in OrderStatus]
    if new_status not in valid_statuses:
        print(f"❌ Estado inválido. Opciones: {', '.join(valid_statuses)}")
        return
    
    with get_db_context() as db:
        order_service = OrderService(db)
        order = order_service.get_order_by_number(order_number)
        
        if not order:
            print(f"❌ Orden {order_number} no encontrada")
            return
        
        print(f"📝 Cambiando estado de {order_number}: {order.status} → {new_status}")
        
        try:
            updated_order = order_service.update_order_status(order.id, new_status)
            print(f"✅ Orden {order_number} actualizada a: {new_status}")
            return updated_order
        except Exception as e:
            print(f"❌ Error actualizando orden: {e}")


def cancel_order(order_number: str, reason: str = None):
    """Cancela una orden y restaura el stock"""
    with get_db_context() as db:
        order_service = OrderService(db)
        order = order_service.get_order_by_number(order_number)
        
        if not order:
            print(f"❌ Orden {order_number} no encontrada")
            return
        
        if order.status == OrderStatus.CANCELLED.value:
            print(f"⚠️ La orden {order_number} ya está cancelada")
            return
        
        print(f"🗑️ Cancelando orden {order_number}...")
        
        try:
            cancelled_order = order_service.cancel_order(order.id, reason)
            print(f"✅ Orden {order_number} cancelada exitosamente")
            print(f"   Stock restaurado para {len(cancelled_order.items)} productos")
            return cancelled_order
        except Exception as e:
            print(f"❌ Error cancelando orden: {e}")


def delete_order(order_number: str):
    """Elimina una orden de la base de datos (¡IRREVERSIBLE!)"""
    with get_db_context() as db:
        order_service = OrderService(db)
        order = order_service.get_order_by_number(order_number)
        
        if not order:
            print(f"❌ Orden {order_number} no encontrada")
            return
        
        # Confirmar eliminación
        print(f"⚠️  ¡ADVERTENCIA! Estás a punto de ELIMINAR permanentemente la orden:")
        print(f"   Número: {order.order_number}")
        print(f"   Cliente: {order.customer.phone if hasattr(order, 'customer') else 'N/A'}")
        print(f"   Total: ${order.total:.2f}")
        print(f"   Estado: {order.status}")
        
        confirm = input("\n¿Estás seguro? Escribe 'ELIMINAR' para confirmar: ")
        
        if confirm != "ELIMINAR":
            print("❌ Eliminación cancelada")
            return
        
        try:
            # Si la orden está confirmada, restaurar stock primero
            if order.status == OrderStatus.CONFIRMED.value:
                print("📦 Restaurando stock...")
                for item in order.items:
                    from app.services.product_service import ProductService
                    product_service = ProductService(db)
                    product_service.update_stock(item.product_id, item.quantity)
            
            # Eliminar orden
            db.delete(order)
            db.commit()
            
            print(f"✅ Orden {order_number} eliminada exitosamente")
            
        except Exception as e:
            db.rollback()
            print(f"❌ Error eliminando orden: {e}")


def interactive_menu():
    """Menú interactivo para gestionar órdenes"""
    while True:
        print("\n" + "="*60)
        print("📦 GESTOR DE ÓRDENES")
        print("="*60)
        print("1. Listar órdenes")
        print("2. Ver detalles de una orden")
        print("3. Cambiar estado de orden")
        print("4. Cancelar orden (restaura stock)")
        print("5. Eliminar orden (¡IRREVERSIBLE!)")
        print("0. Salir")
        print("="*60)
        
        choice = input("\nSelecciona una opción: ").strip()
        
        if choice == "0":
            print("👋 ¡Hasta luego!")
            break
        
        elif choice == "1":
            limit = input("¿Cuántas órdenes mostrar? (default: 10): ").strip()
            limit = int(limit) if limit.isdigit() else 10
            list_orders(limit)
        
        elif choice == "2":
            order_number = input("Número de orden: ").strip()
            get_order_details(order_number)
        
        elif choice == "3":
            order_number = input("Número de orden: ").strip()
            print("\nEstados disponibles:")
            for i, status in enumerate(OrderStatus, 1):
                print(f"  {i}. {status.value}")
            
            new_status = input("\nNuevo estado: ").strip()
            change_order_status(order_number, new_status)
        
        elif choice == "4":
            order_number = input("Número de orden: ").strip()
            reason = input("Razón de cancelación (opcional): ").strip()
            cancel_order(order_number, reason if reason else None)
        
        elif choice == "5":
            order_number = input("Número de orden: ").strip()
            delete_order(order_number)
        
        else:
            print("❌ Opción inválida")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Gestionar órdenes")
    parser.add_argument("--list", action="store_true", help="Listar órdenes")
    parser.add_argument("--details", type=str, help="Ver detalles de una orden")
    parser.add_argument("--status", nargs=2, metavar=("ORDER", "STATUS"), help="Cambiar estado de orden")
    parser.add_argument("--cancel", type=str, help="Cancelar orden")
    parser.add_argument("--delete", type=str, help="Eliminar orden")
    
    args = parser.parse_args()
    
    if args.list:
        list_orders()
    elif args.details:
        get_order_details(args.details)
    elif args.status:
        change_order_status(args.status[0], args.status[1])
    elif args.cancel:
        cancel_order(args.cancel)
    elif args.delete:
        delete_order(args.delete)
    else:
        # Modo interactivo
        interactive_menu()

