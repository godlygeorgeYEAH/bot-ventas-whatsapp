"""
Servicio para gestión de sesiones de carrito

Este servicio maneja la creación, validación y uso de links únicos
de carrito para la webapp.
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from loguru import logger

from app.database.models import CartSession, Customer, Product
from config.settings import settings


class CartService:
    """Servicio para gestión de sesiones de carrito"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_cart_session(
        self,
        customer_id: str,
        hours_valid: int = 24,
        suggested_products: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Crea una nueva sesión de carrito con token único
        
        Args:
            customer_id: ID del cliente
            hours_valid: Horas de validez del token (default: 24h)
            suggested_products: Lista de product_ids pre-sugeridos (opcional)
            
        Returns:
            Dict con token, link completo y datos de la sesión
        """
        try:
            # Generar token único (UUID)
            token = str(uuid.uuid4())
            
            # Calcular expiración
            expires_at = datetime.utcnow() + timedelta(hours=hours_valid)
            
            # Preparar metadata del carrito
            cart_data = {}
            if suggested_products:
                cart_data['suggested_products'] = suggested_products
            
            # Crear sesión en BD
            cart_session = CartSession(
                token=token,
                customer_id=customer_id,
                expires_at=expires_at,
                used=False,
                cart_data=cart_data
            )
            
            self.db.add(cart_session)
            self.db.commit()
            self.db.refresh(cart_session)
            
            # Generar link completo
            cart_link = f"{settings.webapp_base_url}/cart/{token}"
            
            logger.info(f"🛒 Sesión de carrito creada: {token[:8]}... para customer {customer_id}")
            logger.info(f"   ⏰ Expira en {hours_valid}h: {expires_at.isoformat()}")
            
            return {
                "success": True,
                "session_id": cart_session.id,
                "token": token,
                "cart_link": cart_link,
                "expires_at": expires_at.isoformat(),
                "suggested_products": suggested_products or []
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error creando sesión de carrito: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_cart_session(self, token: str) -> Optional[CartSession]:
        """
        Obtiene una sesión de carrito por token
        
        Args:
            token: Token único del carrito
            
        Returns:
            CartSession o None si no existe
        """
        try:
            session = self.db.query(CartSession).filter(
                CartSession.token == token
            ).first()
            
            if session:
                logger.info(f"🔍 Sesión encontrada: {token[:8]}... (usado: {session.used}, expirado: {session.is_expired})")
            else:
                logger.warning(f"⚠️ Sesión no encontrada: {token[:8]}...")
            
            return session
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo sesión: {e}")
            return None
    
    def validate_cart_session(self, token: str) -> Dict[str, Any]:
        """
        Valida una sesión de carrito y devuelve información
        
        Args:
            token: Token único del carrito
            
        Returns:
            Dict con validación y datos del carrito
        """
        from app.database.models import Order
        
        session = self.get_cart_session(token)
        
        if not session:
            return {
                "valid": False,
                "error": "token_not_found",
                "message": "Este link de carrito no existe"
            }
        
        if session.used:
            # Si está usada, verificar si tiene orden PENDING (permite modificación)
            if session.order_id:
                order = self.db.query(Order).filter(Order.id == session.order_id).first()
                
                if order and order.status == "pending":
                    # Orden PENDING: permitir modificación
                    logger.info(f"✅ Sesión usada pero orden PENDING, permitiendo modificación")
                    return {
                        "valid": True,
                        "session_id": session.id,
                        "customer_id": session.customer_id,
                        "cart_data": session.cart_data,
                        "expires_at": session.expires_at.isoformat(),
                        "has_pending_order": True,
                        "order_id": session.order_id
                    }
            
            # Orden no PENDING o sin orden: rechazar
            return {
                "valid": False,
                "error": "token_already_used",
                "message": "Este link ya fue usado. Si necesitas hacer otra orden, solicita un nuevo link.",
                "order_id": session.order_id
            }
        
        if session.is_expired:
            return {
                "valid": False,
                "error": "token_expired",
                "message": "Este link expiró. Solicita uno nuevo para continuar.",
                "expired_at": session.expires_at.isoformat()
            }
        
        # Session válida
        return {
            "valid": True,
            "session_id": session.id,
            "customer_id": session.customer_id,
            "cart_data": session.cart_data,
            "expires_at": session.expires_at.isoformat()
        }
    
    def get_available_products(self) -> List[Dict[str, Any]]:
        """
        Obtiene todos los productos disponibles para el carrito
        
        Returns:
            Lista de productos con su información
        """
        try:
            products = self.db.query(Product).filter(
                Product.is_active == True,
                Product.stock > 0
            ).order_by(Product.name).all()
            
            return [
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "price": float(p.price),
                    "stock": p.stock,
                    "category": p.category,
                    "sku": p.sku,
                    "image_path": p.image_path
                }
                for p in products
            ]
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo productos: {e}")
            return []
    
    def mark_session_as_used(
        self,
        token: str,
        order_id: str
    ) -> bool:
        """
        Marca una sesión como usada después de completar la orden
        
        Args:
            token: Token único del carrito
            order_id: ID de la orden creada
            
        Returns:
            True si se marcó exitosamente, False en caso contrario
        """
        try:
            session = self.get_cart_session(token)
            
            if not session:
                logger.error(f"❌ Sesión no encontrada: {token[:8]}...")
                return False
            
            session.used = True
            session.order_id = order_id
            session.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"✅ Sesión marcada como usada: {token[:8]}... → Orden {order_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error marcando sesión como usada: {e}")
            return False
    
    def get_customer_active_sessions(self, customer_id: str) -> List[CartSession]:
        """
        Obtiene las sesiones activas (no usadas, no expiradas) de un cliente
        
        Args:
            customer_id: ID del cliente
            
        Returns:
            Lista de sesiones activas
        """
        try:
            now = datetime.utcnow()
            
            sessions = self.db.query(CartSession).filter(
                CartSession.customer_id == customer_id,
                CartSession.used == False,
                CartSession.expires_at > now
            ).order_by(CartSession.created_at.desc()).all()
            
            return sessions
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo sesiones activas: {e}")
            return []
    
    def cleanup_expired_sessions(self, days_old: int = 7) -> int:
        """
        Limpia sesiones expiradas antiguas (para mantenimiento)
        
        Args:
            days_old: Días de antigüedad para considerar limpieza
            
        Returns:
            Número de sesiones eliminadas
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            deleted = self.db.query(CartSession).filter(
                CartSession.expires_at < cutoff_date,
                CartSession.used == False
            ).delete()
            
            self.db.commit()
            
            logger.info(f"🧹 Limpieza: {deleted} sesiones expiradas eliminadas")
            return deleted
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error en limpieza de sesiones: {e}")
            return 0

