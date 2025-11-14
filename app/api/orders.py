"""
API endpoints para gestión de órdenes del dashboard
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from config.database import get_db
from app.services.order_service import OrderService
from app.database.models import Order, OrderItem
from loguru import logger

router = APIRouter(prefix="/api/orders", tags=["orders"])


# Schemas de respuesta
class OrderItemResponse(BaseModel):
    id: str
    product_id: str
    product_name: str
    quantity: int
    unit_price: float
    subtotal: float

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    id: str
    order_number: str
    customer_id: str
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    status: str
    subtotal: float
    tax: float
    shipping_cost: float
    total: float
    payment_method: str
    delivery_address: Optional[str] = None
    delivery_latitude: Optional[float] = None
    delivery_longitude: Optional[float] = None
    delivery_reference: Optional[str] = None
    items: List[OrderItemResponse]
    created_at: str
    updated_at: str
    confirmed_at: Optional[str] = None
    shipped_at: Optional[str] = None
    delivered_at: Optional[str] = None
    cancelled_at: Optional[str] = None

    class Config:
        from_attributes = True


class OrderStatsResponse(BaseModel):
    total: int
    pending: int
    confirmed: int
    shipped: int
    delivered: int
    cancelled: int


class UpdateStatusRequest(BaseModel):
    status: str


@router.get("", response_model=List[OrderResponse])
async def get_orders(
    status: Optional[str] = Query(None, description="Filtrar por estado"),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Obtener todas las órdenes con filtros opcionales
    """
    try:
        query = db.query(Order)
        
        # Filtrar por estado si se proporciona
        if status:
            query = query.filter(Order.status == status)
        
        # Ordenar por fecha de creación (más recientes primero)
        query = query.order_by(Order.created_at.desc())
        
        # Aplicar límite y offset
        orders = query.offset(offset).limit(limit).all()
        
        # Enriquecer con datos del cliente
        result = []
        for order in orders:
            order_dict = {
                "id": str(order.id),
                "order_number": order.order_number,
                "customer_id": str(order.customer_id),
                "customer_name": order.customer.name if order.customer else None,
                "customer_phone": order.customer.phone if order.customer else None,
                "status": order.status,
                "subtotal": float(order.subtotal),
                "tax": float(order.tax),
                "shipping_cost": float(order.shipping_cost),
                "total": float(order.total),
                "payment_method": order.payment_method or "N/A",
                "delivery_address": order.delivery_address,
                "delivery_latitude": float(order.delivery_latitude) if order.delivery_latitude else None,
                "delivery_longitude": float(order.delivery_longitude) if order.delivery_longitude else None,
                "delivery_reference": order.delivery_reference,
                "items": [
                    {
                        "id": str(item.id),
                        "product_id": str(item.product_id),
                        "product_name": item.product_name,
                        "quantity": item.quantity,
                        "unit_price": float(item.unit_price),
                        "subtotal": float(item.unit_price * item.quantity)
                    }
                    for item in order.items
                ],
                "created_at": order.created_at.isoformat(),
                "updated_at": order.updated_at.isoformat(),
                "confirmed_at": order.confirmed_at.isoformat() if order.confirmed_at else None,
                "shipped_at": order.shipped_at.isoformat() if order.shipped_at else None,
                "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None,
                "cancelled_at": order.cancelled_at.isoformat() if order.cancelled_at else None,
            }
            result.append(order_dict)
        
        return result
    
    except Exception as e:
        logger.error(f"Error obteniendo órdenes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al obtener órdenes")


@router.get("/stats", response_model=OrderStatsResponse)
async def get_order_stats(db: Session = Depends(get_db)):
    """
    Obtener estadísticas de órdenes por estado
    """
    try:
        total = db.query(Order).count()
        pending = db.query(Order).filter(Order.status == "pending").count()
        confirmed = db.query(Order).filter(Order.status == "confirmed").count()
        shipped = db.query(Order).filter(Order.status == "shipped").count()
        delivered = db.query(Order).filter(Order.status == "delivered").count()
        cancelled = db.query(Order).filter(Order.status == "cancelled").count()
        
        return {
            "total": total,
            "pending": pending,
            "confirmed": confirmed,
            "shipped": shipped,
            "delivered": delivered,
            "cancelled": cancelled
        }
    
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al obtener estadísticas")


@router.delete("/{order_id}")
async def delete_order(order_id: str, db: Session = Depends(get_db)):
    """
    Eliminar una orden permanentemente
    
    ADVERTENCIA: Esta acción no se puede deshacer
    """
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        
        if not order:
            raise HTTPException(status_code=404, detail="Orden no encontrada")
        
        # Guardar número de orden para el mensaje
        order_number = order.order_number
        
        # Si la orden está confirmada o en camino, restaurar stock antes de eliminar
        if order.status in ["confirmed", "shipped"]:
            logger.info(f"Restaurando stock antes de eliminar orden {order_number}")
            from app.services.product_service import ProductService
            product_service = ProductService(db)
            
            for item in order.items:
                product_service.restore_stock(item.product_id, item.quantity)
                logger.info(f"Stock restaurado: {item.product_name} +{item.quantity}")
        
        # Eliminar items de la orden primero (foreign key)
        for item in order.items:
            db.delete(item)
        
        # Eliminar la orden
        db.delete(order)
        db.commit()
        
        logger.info(f"✅ Orden {order_number} eliminada permanentemente")
        
        return {
            "success": True,
            "message": f"Orden {order_number} eliminada correctamente",
            "order_id": order_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error eliminando orden {order_id}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al eliminar orden")


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: str, db: Session = Depends(get_db)):
    """
    Obtener una orden específica por ID
    """
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        
        if not order:
            raise HTTPException(status_code=404, detail="Orden no encontrada")
        
        return {
            "id": str(order.id),
            "order_number": order.order_number,
            "customer_id": str(order.customer_id),
            "customer_name": order.customer.name if order.customer else None,
            "customer_phone": order.customer.phone if order.customer else None,
            "status": order.status,
            "subtotal": float(order.subtotal),
            "tax": float(order.tax),
            "shipping_cost": float(order.shipping_cost),
            "total": float(order.total),
            "payment_method": order.payment_method or "N/A",
            "delivery_address": order.delivery_address,
            "delivery_latitude": float(order.delivery_latitude) if order.delivery_latitude else None,
            "delivery_longitude": float(order.delivery_longitude) if order.delivery_longitude else None,
            "delivery_reference": order.delivery_reference,
            "items": [
                {
                    "id": str(item.id),
                    "product_id": str(item.product_id),
                    "product_name": item.product_name,
                    "quantity": item.quantity,
                    "unit_price": float(item.unit_price),
                    "subtotal": float(item.unit_price * item.quantity)
                }
                for item in order.items
            ],
            "created_at": order.created_at.isoformat(),
            "updated_at": order.updated_at.isoformat(),
            "confirmed_at": order.confirmed_at.isoformat() if order.confirmed_at else None,
            "shipped_at": order.shipped_at.isoformat() if order.shipped_at else None,
            "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None,
            "cancelled_at": order.cancelled_at.isoformat() if order.cancelled_at else None,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo orden {order_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al obtener orden")


@router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: str,
    request: UpdateStatusRequest,
    db: Session = Depends(get_db)
):
    """
    Actualizar el estado de una orden
    """
    try:
        order_service = OrderService(db)
        
        # Validar estado
        valid_statuses = ["pending", "confirmed", "shipped", "delivered", "cancelled", "abandoned"]
        if request.status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Estado inválido. Debe ser uno de: {', '.join(valid_statuses)}")
        
        # Obtener orden
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Orden no encontrada")
        
        # Actualizar estado según el método del servicio
        if request.status == "shipped":
            order = order_service.ship_order(order_id)
        elif request.status == "delivered":
            order = order_service.deliver_order(order_id)
        elif request.status == "cancelled":
            order = order_service.cancel_order(order_id)
        elif request.status == "confirmed":
            # Actualizar estado a confirmed y establecer timestamp
            from datetime import datetime
            order.status = "confirmed"
            order.confirmed_at = datetime.utcnow()
            db.commit()
            db.refresh(order)
            logger.info(f"✅ Orden {order.order_number} marcada como CONFIRMED en {order.confirmed_at}")
        else:
            # Para otros estados (pending), actualizar directamente
            order.status = request.status
            db.commit()
            db.refresh(order)

        return await get_order(order_id, db)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error actualizando estado de orden {order_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al actualizar estado de la orden")


@router.post("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(order_id: str, db: Session = Depends(get_db)):
    """
    Cancelar una orden (restaura stock)
    
    Solo permitido si la orden NO está cancelada o entregada
    """
    try:
        # Verificar estado de la orden
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Orden no encontrada")
        
        # Validar que no esté cancelada o entregada
        if order.status == "cancelled":
            raise HTTPException(status_code=400, detail="La orden ya está cancelada")
        
        if order.status == "delivered":
            raise HTTPException(status_code=400, detail="No se puede cancelar una orden ya entregada")
        
        order_service = OrderService(db)
        order = order_service.cancel_order(order_id, reason="Cancelada por administrador desde el panel")

        # Notificar al usuario y limpiar la conversación
        from app.services.order_notification_service import OrderNotificationService
        notification_service = OrderNotificationService(db)

        try:
            await notification_service.notify_order_cancelled(
                order_id=order_id,
                cancelled_by_admin=True  # Cancelada desde el panel de admin
            )
            logger.info(f"✅ Usuario notificado de cancelación de orden {order.order_number}")
        except Exception as e:
            logger.error(f"⚠️ Error notificando cancelación de orden, pero orden fue cancelada: {e}")
            # No lanzar error, la orden ya está cancelada exitosamente

        return await get_order(order_id, db)
    
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error cancelando orden {order_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al cancelar orden")


@router.post("/{order_id}/assign-driver")
async def assign_driver(order_id: str, db: Session = Depends(get_db)):
    """
    Asignar conductor a una orden (funcionalidad futura)
    
    Solo disponible para órdenes confirmadas
    """
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        
        if not order:
            raise HTTPException(status_code=404, detail="Orden no encontrada")
        
        # Validar que esté confirmada
        if order.status != "confirmed":
            raise HTTPException(
                status_code=400, 
                detail=f"Solo se pueden asignar conductores a órdenes confirmadas. Estado actual: {order.status}"
            )
        
        # TODO: Implementar lógica de asignación de conductor
        # Por ahora, solo retornamos un mensaje
        
        return {
            "success": True,
            "message": "Funcionalidad de asignación de conductor en desarrollo",
            "order_id": order_id,
            "order_number": order.order_number,
            "status": "pending_implementation"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error asignando conductor a orden {order_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al asignar conductor")

