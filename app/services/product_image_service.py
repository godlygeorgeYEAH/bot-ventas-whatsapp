"""
Servicio para manejar imágenes de productos
"""
from typing import Optional, Dict
from app.database.models import Product
from loguru import logger


class ProductImageService:
    """Servicio para determinar cuándo y cómo enviar imágenes de productos"""
    
    @staticmethod
    def should_send_image(intent: str, context: dict) -> bool:
        """
        Determina si se debe enviar imagen según el contexto
        
        Args:
            intent: Intención detectada
            context: Contexto de la conversación
            
        Returns:
            True si debe enviar imagen
        """
        # Enviar imagen cuando:
        # 1. Usuario está viendo catálogo (create_order en estado inicial)
        # 2. Usuario pidió información de un producto específico
        # 3. Bot está ofreciendo un producto
        
        send_image_intents = [
            "create_order",      # Mostrando productos para comprar
            "product_info",      # Usuario pidió info de producto
            "show_catalog"       # Mostrando catálogo
        ]
        
        return intent in send_image_intents
    
    @staticmethod
    def prepare_product_with_image(product: Product) -> Optional[Dict]:
        """
        Prepara datos del producto para enviar con imagen
        
        Args:
            product: Producto a preparar
            
        Returns:
            Dict con datos del producto o None si no tiene imagen
        """
        if not product or not product.has_image:
            logger.info(f"[ProductImageService] Producto sin imagen")
            return None
        
        logger.info(f"[ProductImageService] Preparando imagen para: {product.name}")
        
        return {
            "id": product.id,
            "name": product.name,
            "image_path": product.image_path,
            "price": product.price,
            "stock": product.stock
        }