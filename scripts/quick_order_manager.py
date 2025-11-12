"""
Script rápido para gestionar órdenes
"""
import sys
from pathlib import Path
import io

# Configurar UTF-8 para Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from config.database import get_db_context
from app.services.order_service import OrderService
from app.database.models import OrderStatus, Order
from loguru import logger


def list_recent_orders(limit=20):
    """Lista las órdenes más recientes"""
    with get_db_context() as db:
        orders = db.query(Order).order_by(Order.created_at.desc()).limit(limit).all()
        
        if not orders:
            print("❌ No hay órdenes")
            return []
        
        print(f"\n📦 ÚLTIMAS {len(orders)} ÓRDENES:")
        print("-" * 100)
        print(f"{'#':<3} {'Número':<20} {'Cliente':<15} {'Estado':<12} {'Total':>10} {'Fecha':<19}")
        print("-" * 100)
        
        for i, order in enumerate(orders, 1):
            customer_phone = order.customer.phone if order.customer else 'N/A'
            fecha = order.created_at.strftime('%Y-%m-%d %H:%M:%S') if order.created_at else 'N/A'
            print(f"{i:<3} {order.order_number:<20} {customer_phone:<15} {order.status:<12} ${order.total:>9.2f} {fecha}")
        
        print("-" * 100)
        return orders


def complete_order(order_number: str):
    """Marca una orden como completada/entregada"""
    with get_db_context() as db:
        order_service = OrderService(db)
        order = order_service.get_order_by_number(order_number)
        
        if not order:
            print(f"❌ Orden {order_number} no encontrada")
            return False
        
        print(f"\n📦 Orden: {order.order_number}")
        print(f"   Cliente: {order.customer.phone if order.customer else 'N/A'}")
        print(f"   Estado actual: {order.status}")
        print(f"   Total: ${order.total:.2f}")
        
        # Marcar como entregada
        order_service.update_order_status(order.id, OrderStatus.DELIVERED.value)
        print(f"\n✅ Orden {order_number} marcada como ENTREGADA")
        return True


def cancel_order(order_number: str, reason: str = "Cancelada por administrador"):
    """Cancela una orden"""
    with get_db_context() as db:
        order_service = OrderService(db)
        order = order_service.get_order_by_number(order_number)
        
        if not order:
            print(f"❌ Orden {order_number} no encontrada")
            return False
        
        print(f"\n📦 Orden: {order.order_number}")
        print(f"   Estado actual: {order.status}")
        
        cancelled = order_service.cancel_order(order.id, reason)
        print(f"\n✅ Orden {order_number} cancelada. Stock restaurado.")
        return True


def delete_order_permanently(order_number: str):
    """Elimina una orden PERMANENTEMENTE"""
    with get_db_context() as db:
        order_service = OrderService(db)
        order = order_service.get_order_by_number(order_number)
        
        if not order:
            print(f"❌ Orden {order_number} no encontrada")
            return False
        
        print(f"\n⚠️  ELIMINAR ORDEN: {order.order_number}")
        print(f"   Total: ${order.total:.2f}")
        
        # Restaurar stock si estaba confirmada
        if order.status == OrderStatus.CONFIRMED.value:
            print("   Restaurando stock...")
            for item in order.items:
                from app.services.product_service import ProductService
                ps = ProductService(db)
                ps.update_stock(item.product_id, item.quantity)
        
        db.delete(order)
        db.commit()
        print(f"\n🗑️  Orden {order_number} ELIMINADA permanentemente")
        return True


def change_status(order_number: str, new_status: str):
    """Cambia el estado de una orden"""
    with get_db_context() as db:
        order_service = OrderService(db)
        order = order_service.get_order_by_number(order_number)
        
        if not order:
            print(f"❌ Orden {order_number} no encontrada")
            return False
        
        print(f"\n📝 {order.order_number}: {order.status} → {new_status}")
        order_service.update_order_status(order.id, new_status)
        print(f"✅ Estado actualizado")
        return True


if __name__ == "__main__":
    print("\n" + "="*100)
    print("📦 GESTOR RÁPIDO DE ÓRDENES")
    print("="*100)
    
    # Listar órdenes
    orders = list_recent_orders()
    
    if not orders:
        sys.exit(0)
    
    print("\n¿Qué deseas hacer?")
    print("1. Marcar orden como ENTREGADA")
    print("2. Cambiar estado de orden")
    print("3. Cancelar orden (restaura stock)")
    print("4. Eliminar orden (¡IRREVERSIBLE!)")
    print("0. Salir")
    
    choice = input("\nOpción: ").strip()
    
    if choice == "0":
        print("👋 Adiós")
        sys.exit(0)
    
    order_num = input("\nNúmero de orden: ").strip()
    
    if choice == "1":
        complete_order(order_num)
    
    elif choice == "2":
        print("\nEstados disponibles:")
        for status in OrderStatus:
            print(f"  - {status.value}")
        new_status = input("\nNuevo estado: ").strip()
        change_status(order_num, new_status)
    
    elif choice == "3":
        reason = input("Razón (opcional): ").strip()
        cancel_order(order_num, reason if reason else None)
    
    elif choice == "4":
        confirm = input(f"⚠️  ¿ELIMINAR {order_num}? Escribe 'SI': ").strip()
        if confirm == "SI":
            delete_order_permanently(order_num)
        else:
            print("❌ Cancelado")

