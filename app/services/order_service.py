"""
Servicio para gestión de órdenes
"""
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from datetime import datetime
from app.database.models import Order, OrderItem, OrderStatus, Product, Customer
from app.services.product_service import ProductService
from loguru import logger
import uuid
import asyncio


class OrderService:
    """Servicio para gestionar órdenes"""

    def __init__(self, db: Session):
        self.db = db
        self.product_service = ProductService(db)

    def _notify_admins_async(self, notification_coro):
        """
        Helper para ejecutar notificaciones de admin de forma asíncrona sin bloquear

        Args:
            notification_coro: Corutina de notificación a ejecutar
        """
        try:
            asyncio.create_task(notification_coro)
            logger.debug("📤 Tarea de notificación de admin programada")
        except Exception as e:
            logger.warning(f"⚠️ Error programando notificación de admin: {e}")
    
    def generate_order_number(self) -> str:
        """
        Genera un número de orden único
        Formato: ORD-YYYYMMDD-XXX
        """
        from datetime import datetime
        
        date_str = datetime.now().strftime("%Y%m%d")
        
        # Contar órdenes del día
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        count = self.db.query(Order).filter(
            Order.created_at >= today_start
        ).count()
        
        order_number = f"ORD-{date_str}-{count + 1:03d}"
        
        logger.info(f"📝 Número de orden generado: {order_number}")
        
        return order_number
    
    def create_order(
        self,
        customer_id: str,
        items: List[Dict],  # [{"product_id": "...", "quantity": 2}, ...]
        delivery_address: str = None,
        delivery_latitude: float = None,
        delivery_longitude: float = None,
        delivery_reference: str = None,
        payment_method: str = None,
        delivery_city: str = None,
        delivery_phone: str = None,
        delivery_notes: str = None,
        conversation_id: str = None,
        tax_rate: float = 0.0,
        shipping_cost: float = 0.0
    ) -> Order:
        """
        Crea una nueva orden
        
        Args:
            customer_id: ID del cliente
            items: Lista de items con product_id y quantity
            delivery_address: Dirección de entrega
            payment_method: Método de pago
            ... otros parámetros opcionales
            
        Returns:
            Order creada
        """
        try:
            logger.info(f"🛒 Creando orden para cliente {customer_id}")
            logger.info(f"   Items: {len(items)}")
            
            # Verificar que el cliente existe
            customer = self.db.query(Customer).filter(Customer.id == customer_id).first()
            if not customer:
                raise ValueError(f"Cliente no encontrado: {customer_id}")
            
            # Validar y preparar items
            order_items = []
            subtotal = 0.0
            
            for item_data in items:
                product_id = item_data.get("product_id")
                quantity = item_data.get("quantity", 1)
                
                # Obtener producto
                product = self.product_service.get_product_by_id(product_id)
                if not product:
                    raise ValueError(f"Producto no encontrado: {product_id}")
                
                # Verificar stock
                if not self.product_service.check_stock(product_id, quantity):
                    raise ValueError(f"Stock insuficiente para {product.name}")
                
                # Crear OrderItem
                item_subtotal = product.price * quantity
                
                order_item = OrderItem(
                    product_id=product.id,
                    product_name=product.name,
                    product_sku=product.sku,
                    quantity=quantity,
                    unit_price=product.price,
                    subtotal=item_subtotal,
                    item_notes=item_data.get("notes")
                )
                
                order_items.append(order_item)
                subtotal += item_subtotal
                
                logger.info(f"   ✅ Item: {product.name} x{quantity} = ${item_subtotal}")
            
            # Calcular totales
            tax = subtotal * tax_rate
            total = subtotal + tax + shipping_cost
            
            logger.info(f"   Subtotal: ${subtotal:.2f}")
            logger.info(f"   Tax: ${tax:.2f}")
            logger.info(f"   Shipping: ${shipping_cost:.2f}")
            logger.info(f"   TOTAL: ${total:.2f}")
            
            # Crear orden con coordenadas GPS
            order = Order(
                order_number=self.generate_order_number(),
                customer_id=customer_id,
                conversation_id=conversation_id,
                status=OrderStatus.PENDING.value,
                subtotal=subtotal,
                tax=tax,
                shipping_cost=shipping_cost,
                discount=0.0,
                total=total,
                delivery_address=delivery_address,
                delivery_latitude=delivery_latitude,
                delivery_longitude=delivery_longitude,
                delivery_reference=delivery_reference,
                delivery_city=delivery_city,
                delivery_phone=delivery_phone or customer.phone,
                delivery_notes=delivery_notes,
                payment_method=payment_method,
                payment_status="pending",
                items=order_items
            )
            
            self.db.add(order)
            self.db.commit()
            self.db.refresh(order)

            logger.info(f"✅ Orden creada: {order.order_number}")

            # Notificar a administradores
            try:
                from app.services.admin_notification_service import AdminNotificationService
                admin_service = AdminNotificationService(self.db)
                self._notify_admins_async(admin_service.notify_order_created(order))
            except Exception as e:
                logger.warning(f"⚠️ Error al programar notificación de admin: {e}")

            return order
            
        except Exception as e:
            logger.error(f"❌ Error creando orden: {e}")
            self.db.rollback()
            raise
    
    def confirm_order(self, order_id: str) -> Order:
        """
        Confirma una orden y reduce el stock
        
        Args:
            order_id: ID de la orden
        """
        try:
            order = self.get_order_by_id(order_id)
            
            if not order:
                raise ValueError(f"Orden no encontrada: {order_id}")
            
            if order.status != OrderStatus.PENDING.value:
                raise ValueError(f"Orden no puede ser confirmada. Estado actual: {order.status}")
            
            logger.info(f"✅ Confirmando orden: {order.order_number}")
            
            # Reducir stock de cada producto
            for item in order.items:
                logger.info(f"   📉 Reduciendo stock: {item.product_name} x{item.quantity}")
                self.product_service.update_stock(item.product_id, -item.quantity)
            
            # Actualizar estado
            order.status = OrderStatus.CONFIRMED.value
            order.confirmed_at = datetime.utcnow()

            self.db.commit()
            self.db.refresh(order)

            logger.info(f"✅ Orden confirmada: {order.order_number}")

            # Notificar a administradores
            try:
                from app.services.admin_notification_service import AdminNotificationService
                admin_service = AdminNotificationService(self.db)
                self._notify_admins_async(admin_service.notify_order_confirmed(order))
            except Exception as e:
                logger.warning(f"⚠️ Error al programar notificación de admin: {e}")

            return order
            
        except Exception as e:
            logger.error(f"❌ Error confirmando orden: {e}")
            self.db.rollback()
            raise
    
    def cancel_order(self, order_id: str, reason: str = None) -> Order:
        """
        Cancela una orden y restaura el stock
        
        Args:
            order_id: ID de la orden
            reason: Razón de cancelación
        """
        try:
            order = self.get_order_by_id(order_id)
            
            if not order:
                raise ValueError(f"Orden no encontrada: {order_id}")
            
            if not order.can_be_cancelled:
                raise ValueError(f"Orden no puede ser cancelada. Estado actual: {order.status}")
            
            logger.info(f"🚫 Cancelando orden: {order.order_number}")
            
            # Si ya fue confirmada, restaurar stock
            if order.status == OrderStatus.CONFIRMED.value:
                for item in order.items:
                    logger.info(f"   📈 Restaurando stock: {item.product_name} x{item.quantity}")
                    self.product_service.update_stock(item.product_id, item.quantity)
            
            # Actualizar estado
            order.status = OrderStatus.CANCELLED.value
            order.cancelled_at = datetime.utcnow()
            order.cancellation_reason = reason

            self.db.commit()
            self.db.refresh(order)

            logger.info(f"✅ Orden cancelada: {order.order_number}")

            # Notificar a administradores
            try:
                from app.services.admin_notification_service import AdminNotificationService
                admin_service = AdminNotificationService(self.db)
                self._notify_admins_async(admin_service.notify_order_cancelled(order, reason))
            except Exception as e:
                logger.warning(f"⚠️ Error al programar notificación de admin: {e}")

            return order
            
        except Exception as e:
            logger.error(f"❌ Error cancelando orden: {e}")
            self.db.rollback()
            raise
    
    def update_order_status(self, order_id: str, new_status: str) -> Order:
        """
        Actualiza el estado de una orden
        
        Args:
            order_id: ID de la orden
            new_status: Nuevo estado (de OrderStatus)
        """
        try:
            order = self.get_order_by_id(order_id)
            
            if not order:
                raise ValueError(f"Orden no encontrada: {order_id}")
            
            logger.info(f"🔄 Actualizando orden {order.order_number}: {order.status} → {new_status}")
            
            # Actualizar timestamps según el estado
            if new_status == OrderStatus.SHIPPED.value:
                order.shipped_at = datetime.utcnow()
            elif new_status == OrderStatus.DELIVERED.value:
                order.delivered_at = datetime.utcnow()

            old_status = order.status
            order.status = new_status

            self.db.commit()
            self.db.refresh(order)

            logger.info(f"✅ Estado actualizado: {order.order_number} → {new_status}")

            # Notificar a administradores según el nuevo estado
            try:
                from app.services.admin_notification_service import AdminNotificationService
                admin_service = AdminNotificationService(self.db)

                if new_status == OrderStatus.SHIPPED.value:
                    self._notify_admins_async(admin_service.notify_order_shipped(order))
                elif new_status == OrderStatus.DELIVERED.value:
                    self._notify_admins_async(admin_service.notify_order_delivered(order))
                else:
                    # Para otros cambios de estado, notificar como modificación
                    self._notify_admins_async(admin_service.notify_order_modified(order, "status_changed"))
            except Exception as e:
                logger.warning(f"⚠️ Error al programar notificación de admin: {e}")

            return order
            
        except Exception as e:
            logger.error(f"❌ Error actualizando estado: {e}")
            self.db.rollback()
            raise
    
    def get_order_by_id(self, order_id: str) -> Optional[Order]:
        """Obtiene una orden por ID"""
        return self.db.query(Order).filter(Order.id == order_id).first()
    
    def get_order_by_number(self, order_number: str) -> Optional[Order]:
        """Obtiene una orden por número"""
        order = self.db.query(Order).filter(Order.order_number == order_number).first()
        
        if order:
            logger.info(f"✅ Orden encontrada: {order_number}")
        else:
            logger.warning(f"❌ Orden no encontrada: {order_number}")
        
        return order
    
    def get_customer_last_location(self, customer_id: str) -> Optional[tuple]:
        """
        Obtiene la última ubicación GPS y referencia usada por un cliente
        
        Args:
            customer_id: ID del cliente
            
        Returns:
            Tuple (latitude, longitude, reference) o None si no hay ubicación previa
        """
        try:
            # Buscar la orden más reciente con coordenadas GPS
            last_order = self.db.query(Order).filter(
                Order.customer_id == customer_id,
                Order.delivery_latitude.isnot(None),
                Order.delivery_longitude.isnot(None)
            ).order_by(Order.created_at.desc()).first()
            
            if last_order:
                logger.info(f"📍 Última ubicación encontrada para cliente {customer_id}: "
                          f"{last_order.delivery_latitude}, {last_order.delivery_longitude}")
                if last_order.delivery_reference:
                    logger.info(f"   Referencia: {last_order.delivery_reference}")
                return (
                    last_order.delivery_latitude, 
                    last_order.delivery_longitude,
                    last_order.delivery_reference
                )
            
            logger.info(f"📍 No se encontró ubicación previa para cliente {customer_id}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo última ubicación: {e}")
            return None
    
    def get_customer_orders(
        self,
        customer_id: str,
        status: str = None,
        limit: int = 10
    ) -> List[Order]:
        """
        Obtiene las órdenes de un cliente
        
        Args:
            customer_id: ID del cliente
            status: Filtrar por estado (opcional)
            limit: Máximo de órdenes a retornar
        """
        query = self.db.query(Order).filter(Order.customer_id == customer_id)
        
        if status:
            query = query.filter(Order.status == status)
        
        orders = query.order_by(Order.created_at.desc()).limit(limit).all()
        
        logger.info(f"📦 Órdenes de cliente {customer_id}: {len(orders)}")
        
        return orders
    
    def format_order_summary(self, order: Order) -> str:
        """
        Formatea un resumen de la orden para mostrar al usuario
        
        Args:
            order: Orden a formatear
            
        Returns:
            String formateado con el resumen
        """
        status_emoji = {
            OrderStatus.PENDING.value: "⏳",
            OrderStatus.CONFIRMED.value: "✅",
            OrderStatus.PROCESSING.value: "⚙️",
            OrderStatus.SHIPPED.value: "🚚",
            OrderStatus.DELIVERED.value: "📦",
            OrderStatus.CANCELLED.value: "❌"
        }
        
        emoji = status_emoji.get(order.status, "📋")
        
        summary = f"""*{emoji} Orden #{order.order_number}*

*Estado:* {order.status.upper()}

*Productos:*"""
        
        for item in order.items:
            summary += f"\n  • {item.product_name} x{item.quantity} - ${item.subtotal:.2f}"
        
        summary += f"""

*Subtotal:* ${order.subtotal:.2f}
*Envío:* ${order.shipping_cost:.2f}
*Impuestos:* ${order.tax:.2f}
*TOTAL:* ${order.total:.2f}

*Ubicación de entrega:*"""
        
        # Mostrar coordenadas GPS si están disponibles
        if order.delivery_latitude and order.delivery_longitude:
            summary += f"\n📍 GPS: {order.delivery_latitude}, {order.delivery_longitude}"
            # Agregar enlace a Google Maps
            maps_url = f"https://www.google.com/maps?q={order.delivery_latitude},{order.delivery_longitude}"
            summary += f"\n🗺️ Ver en mapa: {maps_url}"
            # Agregar referencia si existe
            if order.delivery_reference:
                summary += f"\n📝 Referencia: {order.delivery_reference}"
        
        if order.delivery_address:
            summary += f"\n📬 {order.delivery_address}"
        
        summary += f"""

*Método de pago:* {order.payment_method}
*Estado de pago:* {order.payment_status}

*Fecha:* {order.created_at.strftime('%d/%m/%Y %H:%M')}"""
        
        return summary
    
    def get_recent_confirmed_order(self, customer_id: str, max_hours: int = 24) -> Optional[Order]:
        """
        Obtiene la orden activa más reciente de un cliente (confirmed, pending, shipped)
        
        IMPORTANTE: Excluye órdenes delivered y cancelled (solo son históricas)
        
        Args:
            customer_id: ID del cliente
            max_hours: Máximo de horas atrás para buscar (default: 24h)
            
        Returns:
            Orden activa más reciente o None
        """
        from datetime import timedelta
        
        try:
            time_limit = datetime.now() - timedelta(hours=max_hours)
            
            # Estados ACTIVOS: confirmed, pending, shipped
            # Estados IGNORADOS: delivered (histórico), cancelled (histórico)
            active_statuses = [
                OrderStatus.CONFIRMED.value,
                OrderStatus.PENDING.value,
                OrderStatus.SHIPPED.value
            ]
            
            order = self.db.query(Order).filter(
                Order.customer_id == customer_id,
                Order.status.in_(active_statuses),  # Solo órdenes activas
                Order.created_at >= time_limit
            ).order_by(Order.created_at.desc()).first()
            
            if order:
                logger.info(f"✅ Orden activa reciente encontrada: {order.order_number} (Estado: {order.status})")
            else:
                logger.info(f"❌ No se encontró orden activa reciente para cliente {customer_id}")
            
            return order
            
        except Exception as e:
            logger.error(f"❌ Error buscando orden activa reciente: {e}")
            return None
    
    def add_items_to_order(
        self,
        order_id: str,
        items: List[Dict]  # [{"product_id": "...", "quantity": 2}, ...]
    ) -> Order:
        """
        Agrega items adicionales a una orden existente
        
        Args:
            order_id: ID de la orden
            items: Lista de items a agregar
            
        Returns:
            Orden actualizada
        """
        try:
            # 1. Obtener la orden
            order = self.db.query(Order).filter(Order.id == order_id).first()
            
            if not order:
                raise ValueError(f"Orden {order_id} no encontrada")
            
            if order.status != OrderStatus.CONFIRMED.value:
                raise ValueError(f"Solo se pueden agregar items a órdenes confirmadas. Estado actual: {order.status}")
            
            logger.info(f"➕ Agregando {len(items)} items a orden {order.order_number}")
            
            # 2. Agregar cada item
            subtotal_added = 0.0
            
            for item_data in items:
                product = self.db.query(Product).filter(
                    Product.id == item_data["product_id"]
                ).first()
                
                if not product:
                    logger.warning(f"⚠️ Producto {item_data['product_id']} no encontrado, saltando")
                    continue
                
                quantity = item_data["quantity"]
                
                # Verificar stock
                if not self.product_service.check_stock(product.id, quantity):
                    raise ValueError(f"Stock insuficiente para {product.name}. Disponible: {product.stock}")
                
                # Calcular subtotal del item
                item_subtotal = product.price * quantity
                subtotal_added += item_subtotal
                
                # Crear OrderItem
                order_item = OrderItem(
                    id=str(uuid.uuid4()),
                    order_id=order.id,
                    product_id=product.id,
                    product_name=product.name,
                    product_sku=product.sku,
                    quantity=quantity,
                    unit_price=product.price,
                    subtotal=item_subtotal
                )
                
                self.db.add(order_item)
                
                # Reducir stock
                product.stock -= quantity
                
                logger.info(f"  ✅ Agregado: {product.name} x{quantity} (${item_subtotal:.2f})")
            
            # 3. Recalcular totales de la orden
            order.subtotal += subtotal_added
            order.tax = order.subtotal * 0.19  # Recalcular impuesto
            order.total = order.subtotal + order.tax + order.shipping_cost
            order.updated_at = datetime.now()

            self.db.commit()
            self.db.refresh(order)

            logger.info(f"✅ Items agregados exitosamente. Nuevo total: ${order.total:.2f}")

            # Notificar a administradores
            try:
                from app.services.admin_notification_service import AdminNotificationService
                admin_service = AdminNotificationService(self.db)
                self._notify_admins_async(admin_service.notify_order_modified(order, "items_added"))
            except Exception as e:
                logger.warning(f"⚠️ Error al programar notificación de admin: {e}")

            return order
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error agregando items a orden: {e}")
            raise
    
    def remove_items_from_order(
        self,
        order_id: str,
        product_name: str,
        quantity: int
    ) -> Order:
        """
        Remueve items de una orden existente
        
        Args:
            order_id: ID de la orden
            product_name: Nombre del producto a remover
            quantity: Cantidad a remover
            
        Returns:
            Orden actualizada
            
        Raises:
            ValueError: Si hay problemas con la orden o el producto
        """
        try:
            # 1. Obtener la orden
            order = self.db.query(Order).filter(Order.id == order_id).first()
            
            if not order:
                raise ValueError(f"Orden {order_id} no encontrada")
            
            if order.status != OrderStatus.CONFIRMED.value:
                raise ValueError(f"Solo se pueden remover items de órdenes confirmadas. Estado actual: {order.status}")
            
            logger.info(f"➖ Removiendo {quantity} unidades de '{product_name}' de orden {order.order_number}")
            
            # 2. Primero, intentar encontrar el producto por nombre fuzzy en el catálogo
            product = self.product_service.get_product_by_name_fuzzy(product_name)
            
            # 3. Buscar el OrderItem correspondiente (por product_id si encontramos el producto)
            order_item = None
            if product:
                # Buscar por product_id (más confiable)
                logger.info(f"  🔍 Buscando en orden por product_id: {product.id} ({product.name})")
                for item in order.items:
                    if item.product_id == product.id:
                        order_item = item
                        break
            
            # Si no lo encontramos por product_id, intentar por nombre (fallback)
            if not order_item:
                logger.info(f"  🔍 Buscando en orden por nombre (fallback)")
                for item in order.items:
                    if item.product_name.lower() == product_name.lower():
                        order_item = item
                        break
            
            if not order_item:
                raise ValueError(f"El producto '{product_name}' no está en tu orden")
            
            # 4. Validar cantidad
            if quantity > order_item.quantity:
                raise ValueError(f"Solo tienes {order_item.quantity} unidades de '{product_name}' en tu orden. No puedes eliminar {quantity}")
            
            if quantity <= 0:
                raise ValueError("La cantidad a eliminar debe ser mayor a 0")
            
            # 5. Devolver stock al inventario
            product_for_stock = self.db.query(Product).filter(Product.id == order_item.product_id).first()
            if product_for_stock:
                product_for_stock.stock += quantity
                logger.info(f"  ✅ Stock devuelto: {product_for_stock.name} +{quantity} (total: {product_for_stock.stock})")
            
            # 6. Actualizar o eliminar el OrderItem
            if quantity == order_item.quantity:
                # Eliminar completamente el item
                logger.info(f"  🗑️ Eliminando item completamente (todas las unidades)")
                self.db.delete(order_item)
                subtotal_removed = order_item.subtotal
            else:
                # Reducir cantidad
                logger.info(f"  📉 Reduciendo cantidad: {order_item.quantity} → {order_item.quantity - quantity}")
                order_item.quantity -= quantity
                subtotal_removed = order_item.unit_price * quantity
                order_item.subtotal = order_item.unit_price * order_item.quantity
            
            # 7. Recalcular totales de la orden
            order.subtotal -= subtotal_removed
            order.tax = order.subtotal * 0.19  # Recalcular impuesto
            order.total = order.subtotal + order.tax + order.shipping_cost
            order.updated_at = datetime.now()
            
            # 8. Validar que la orden no quede vacía
            remaining_items = [item for item in order.items if item.id != order_item.id or quantity != order_item.quantity]
            if not remaining_items and quantity == order_item.quantity:
                raise ValueError("No puedes eliminar todos los productos de la orden. Si deseas cancelarla, usa la opción de cancelar orden")
            
            self.db.commit()
            self.db.refresh(order)

            logger.info(f"✅ Items removidos exitosamente. Nuevo total: ${order.total:.2f}")

            # Notificar a administradores
            try:
                from app.services.admin_notification_service import AdminNotificationService
                admin_service = AdminNotificationService(self.db)
                self._notify_admins_async(admin_service.notify_order_modified(order, "items_removed"))
            except Exception as e:
                logger.warning(f"⚠️ Error al programar notificación de admin: {e}")

            return order
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error removiendo items de orden: {e}")
            raise
    
    def get_customer_product_history(self, customer_id: str, limit: int = 10) -> List[Dict]:
        """
        Obtiene el historial de productos ordenados por un cliente,
        ordenados por frecuencia (más ordenados primero)
        
        Args:
            customer_id: ID del cliente
            limit: Número máximo de productos a retornar
            
        Returns:
            Lista de dicts con: {"product_id", "product_name", "times_ordered", "total_quantity"}
        """
        from sqlalchemy import func
        
        try:
            # Query para agrupar productos por frecuencia
            history = self.db.query(
                OrderItem.product_id,
                OrderItem.product_name,
                func.count(OrderItem.id).label('times_ordered'),
                func.sum(OrderItem.quantity).label('total_quantity')
            ).join(
                Order, OrderItem.order_id == Order.id
            ).filter(
                Order.customer_id == customer_id,
                Order.status == OrderStatus.CONFIRMED.value
            ).group_by(
                OrderItem.product_id,
                OrderItem.product_name
            ).order_by(
                func.count(OrderItem.id).desc()  # Más ordenados primero
            ).limit(limit).all()
            
            result = [
                {
                    "product_id": item.product_id,
                    "product_name": item.product_name,
                    "times_ordered": item.times_ordered,
                    "total_quantity": item.total_quantity
                }
                for item in history
            ]
            
            logger.info(f"📊 Historial de cliente: {len(result)} productos únicos")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo historial: {e}")
            return []
    
    def get_products_not_in_order(self, order_id: str) -> List[str]:
        """
        Obtiene lista de product_ids que NO están en una orden específica
        
        Args:
            order_id: ID de la orden
            
        Returns:
            Lista de product_ids que no están en la orden
        """
        try:
            order = self.db.query(Order).filter(Order.id == order_id).first()
            if not order:
                return []
            
            # IDs de productos en la orden
            products_in_order = [item.product_id for item in order.items]
            
            # Todos los productos activos que NO están en la orden
            all_products = self.db.query(Product.id).filter(
                Product.is_active == True,
                Product.stock > 0,
                ~Product.id.in_(products_in_order)  # NOT IN
            ).all()
            
            return [p.id for p in all_products]
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo productos no en orden: {e}")
            return []

    def get_last_delivery_info(self, customer_id: str) -> Optional[Dict]:
        """
        Obtiene la información de entrega de la última orden completada del cliente

        Busca la orden más reciente (confirmada o entregada) que tenga
        latitud, longitud y referencia guardadas.

        Args:
            customer_id: ID del cliente

        Returns:
            Dict con {latitude, longitude, reference} o None si no hay historial
        """
        try:
            # Buscar la orden más reciente con GPS válido
            # Estados válidos: confirmed, delivered, shipped
            valid_statuses = [
                OrderStatus.CONFIRMED.value,
                OrderStatus.DELIVERED.value,
                OrderStatus.SHIPPED.value
            ]

            order = self.db.query(Order).filter(
                Order.customer_id == customer_id,
                Order.status.in_(valid_statuses),
                Order.delivery_latitude.isnot(None),
                Order.delivery_longitude.isnot(None)
            ).order_by(Order.created_at.desc()).first()

            if not order:
                logger.info(f"❌ No se encontró historial de entrega para cliente {customer_id}")
                return None

            result = {
                "latitude": order.delivery_latitude,
                "longitude": order.delivery_longitude,
                "reference": order.delivery_reference or ""
            }

            logger.info(f"✅ Historial de entrega encontrado para cliente {customer_id}")
            logger.info(f"   GPS: {result['latitude']}, {result['longitude']}")
            logger.info(f"   Referencia: {result['reference']}")

            return result

        except Exception as e:
            logger.error(f"❌ Error obteniendo historial de entrega: {e}")
            return None