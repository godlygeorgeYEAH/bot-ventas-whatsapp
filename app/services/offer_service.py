"""
Servicio para gestión de ofrecimientos de productos
"""
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from app.database.models import Product, Customer, Order
from app.services.order_service import OrderService
from app.services.product_service import ProductService
from loguru import logger
import random


class OfferService:
    """Servicio para gestionar ofrecimientos de productos a clientes"""
    
    def __init__(self, db: Session):
        self.db = db
        self.order_service = OrderService(db)
        self.product_service = ProductService(db)
    
    def select_product_to_offer(
        self, 
        customer_id: str, 
        current_order_id: Optional[str] = None,
        exclude_product_ids: Optional[List[str]] = None
    ) -> Optional[Dict]:
        """
        Selecciona un producto para ofrecer basado en el historial del cliente
        
        Prioridad:
        1. El producto que el cliente más ha ordenado (que no esté en la orden actual)
        2. El segundo producto que el cliente más ha ordenado (que no esté en la orden actual)
        3. Un producto aleatorio
        
        Args:
            customer_id: ID del cliente
            current_order_id: ID de la orden actual (para excluir productos ya en ella)
            exclude_product_ids: IDs adicionales de productos a excluir
            
        Returns:
            Dict con información del producto: {
                "product_id": str,
                "product_name": str,
                "price": float,
                "description": str,
                "image_path": str,
                "stock": int,
                "selection_reason": str  # "most_ordered", "second_most_ordered", "random"
            }
            O None si no hay productos disponibles
        """
        try:
            logger.info(f"🎯 Seleccionando producto para ofrecer al cliente {customer_id}")
            
            # 1. Obtener productos que NO deben estar en la oferta
            excluded_ids = exclude_product_ids or []
            if current_order_id:
                products_in_order = self.order_service.get_products_not_in_order(current_order_id)
                # Invertir la lógica: necesitamos los que SÍ están en la orden para excluirlos
                order = self.db.query(Order).filter(Order.id == current_order_id).first()
                if order:
                    excluded_ids.extend([item.product_id for item in order.items])
            
            # 2. Obtener historial del cliente
            history = self.order_service.get_customer_product_history(customer_id, limit=20)
            
            # 3. Filtrar productos del historial que no estén excluidos
            available_history = [
                item for item in history 
                if item["product_id"] not in excluded_ids
            ]
            
            # 4. Intentar ofrecer según prioridad
            selected_product = None
            selection_reason = None
            
            # Prioridad 1: Producto más ordenado
            if len(available_history) >= 1:
                selected_product_id = available_history[0]["product_id"]
                selected_product = self.product_service.get_product_by_id(selected_product_id)
                selection_reason = "most_ordered"
                logger.info(f"  ✅ Seleccionado producto más ordenado: {available_history[0]['product_name']} ({available_history[0]['times_ordered']} veces)")
            
            # Prioridad 2: Segundo producto más ordenado
            elif len(available_history) >= 2:
                selected_product_id = available_history[1]["product_id"]
                selected_product = self.product_service.get_product_by_id(selected_product_id)
                selection_reason = "second_most_ordered"
                logger.info(f"  ✅ Seleccionado segundo producto más ordenado: {available_history[1]['product_name']} ({available_history[1]['times_ordered']} veces)")
            
            # Prioridad 3: Producto aleatorio
            else:
                logger.info("  📦 No hay historial suficiente, seleccionando producto aleatorio...")
                all_products = self.product_service.get_all_products()
                available_products = [
                    p for p in all_products 
                    if p.id not in excluded_ids and p.stock > 0
                ]
                
                if available_products:
                    selected_product = random.choice(available_products)
                    selection_reason = "random"
                    logger.info(f"  ✅ Seleccionado producto aleatorio: {selected_product.name}")
                else:
                    logger.warning("  ⚠️ No hay productos disponibles para ofrecer")
                    return None
            
            # 5. Verificar que el producto esté disponible
            if not selected_product or selected_product.stock <= 0:
                logger.warning(f"  ⚠️ Producto seleccionado no disponible o sin stock")
                return None
            
            # 6. Retornar información del producto
            return {
                "product_id": selected_product.id,
                "product_name": selected_product.name,
                "price": float(selected_product.price),
                "description": selected_product.description or "",
                "image_path": selected_product.image_path or "",
                "stock": selected_product.stock,
                "selection_reason": selection_reason
            }
            
        except Exception as e:
            logger.error(f"❌ Error seleccionando producto para ofrecer: {e}")
            return None
    
    def format_offer_message(self, product: Dict, include_price: bool = True) -> str:
        """
        Formatea el mensaje de ofrecimiento
        
        Args:
            product: Dict con información del producto
            include_price: Si debe incluir el precio en el mensaje
            
        Returns:
            String con el mensaje formateado
        """
        message = f"🎁 *¿Te gustaría agregar esto a tu orden?*\n\n"
        message += f"*{product['product_name']}*\n"
        
        if product['description']:
            message += f"{product['description']}\n\n"
        
        if include_price:
            message += f"💰 Precio: *${product['price']:.2f}*\n\n"
        
        message += "Responde *Sí* para agregarlo o *No* para continuar sin este producto."
        
        return message
    
    def should_offer_after_order(self, customer_id: str, order_id: str) -> bool:
        """
        Determina si se debe hacer un ofrecimiento después de completar una orden
        
        Args:
            customer_id: ID del cliente
            order_id: ID de la orden
            
        Returns:
            True si se debe ofrecer, False si no
        """
        try:
            # Lógica: ofrecer si hay productos disponibles que el cliente pueda querer
            product_to_offer = self.select_product_to_offer(customer_id, order_id)
            return product_to_offer is not None
            
        except Exception as e:
            logger.error(f"❌ Error determinando si ofrecer: {e}")
            return False

