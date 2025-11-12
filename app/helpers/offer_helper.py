"""
Helper para enviar ofrecimientos de productos con imagen
"""
import os
from typing import Dict, Optional
from loguru import logger
from config.settings import settings
from app.clients.waha_client import WAHAClient


class OfferHelper:
    """Helper para enviar ofrecimientos de productos"""
    
    def __init__(self, waha_client: WAHAClient = None):
        self.waha = waha_client or WAHAClient()
        self.base_url = os.getenv("APP_BASE_URL", "http://localhost:8000")
    
    def send_offer_sync(
        self,
        phone: str,
        product: Dict,
        offer_message: str
    ) -> bool:
        """
        Envía un ofrecimiento de producto con imagen (versión síncrona)
        
        Args:
            phone: Número de teléfono del cliente
            product: Dict con información del producto (debe incluir image_path)
            offer_message: Mensaje del ofrecimiento
            
        Returns:
            True si se envió exitosamente, False en caso contrario
        """
        try:
            chat_id = self.waha._format_chat_id(phone)
            
            # Verificar si hay imagen
            image_path = product.get("image_path")
            if not image_path or not settings.offer_with_image:
                # Sin imagen, solo texto
                import requests
                response = requests.post(
                    f"{settings.waha_base_url}/api/sendText",
                    json={
                        "chatId": chat_id,
                        "text": offer_message,
                        "session": settings.waha_session_name
                    },
                    headers={"X-Api-Key": settings.waha_api_key},
                    timeout=10.0
                )
                response.raise_for_status()
                logger.info(f"✅ Ofrecimiento (texto) enviado a {phone}")
                return True
            
            # Construir path completo de la imagen
            if image_path.startswith("/"):
                # Path absoluto
                full_image_path = image_path
            else:
                # Path relativo desde la carpeta del proyecto
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                full_image_path = os.path.join(project_root, image_path.lstrip("/"))
            
            # Verificar que el archivo existe
            if not os.path.exists(full_image_path):
                logger.warning(f"⚠️ Imagen no encontrada: {full_image_path}")
                # Enviar solo texto si no hay imagen
                import requests
                response = requests.post(
                    f"{settings.waha_base_url}/api/sendText",
                    json={
                        "chatId": chat_id,
                        "text": offer_message,
                        "session": settings.waha_session_name
                    },
                    headers={"X-Api-Key": settings.waha_api_key},
                    timeout=10.0
                )
                response.raise_for_status()
                return True
            
            logger.info(f"📸 Imagen encontrada: {full_image_path}")
            
            # Enviar según configuración
            if settings.offer_image_as_caption:
                # Opción A: Texto como caption de la imagen
                logger.info(f"📸 Enviando ofrecimiento con imagen+caption")
                try:
                    self.waha.send_image_from_file(
                        chat_id=chat_id,
                        file_path=full_image_path,
                        caption=offer_message
                    )
                    logger.info(f"✅ Ofrecimiento (imagen+caption) enviado a {phone}")
                except Exception as img_error:
                    # Error al enviar imagen, fallback a solo texto
                    logger.error(f"❌ Error enviando imagen: {img_error}")
                    logger.warning(f"⚠️ Fallback: Enviando ofrecimiento solo texto (sin imagen)")
                    import requests
                    response = requests.post(
                        f"{settings.waha_base_url}/api/sendText",
                        json={
                            "chatId": chat_id,
                            "text": offer_message,
                            "session": settings.waha_session_name
                        },
                        headers={"X-Api-Key": settings.waha_api_key},
                        timeout=10.0
                    )
                    response.raise_for_status()
                    logger.info(f"✅ Ofrecimiento (solo texto fallback) enviado a {phone}")
            else:
                # Opción B: Solo texto SIN imagen
                logger.info(f"📝 Enviando ofrecimiento solo texto (sin imagen)")
                import requests
                response = requests.post(
                    f"{settings.waha_base_url}/api/sendText",
                    json={
                        "chatId": chat_id,
                        "text": offer_message,
                        "session": settings.waha_session_name
                    },
                    headers={"X-Api-Key": settings.waha_api_key},
                    timeout=10.0
                )
                response.raise_for_status()
                logger.info(f"✅ Ofrecimiento (solo texto) enviado a {phone}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error enviando ofrecimiento: {e}")
            return False
    
    async def send_offer_async(
        self,
        phone: str,
        product: Dict,
        offer_message: str
    ) -> bool:
        """
        Envía un ofrecimiento de producto con imagen (versión asíncrona)
        
        Args:
            phone: Número de teléfono del cliente
            product: Dict con información del producto (debe incluir image_path)
            offer_message: Mensaje del ofrecimiento
            
        Returns:
            True si se envió exitosamente, False en caso contrario
        """
        try:
            # Para imágenes locales, usamos la versión síncrona
            # ya que send_image_from_file es síncrona
            return self.send_offer_sync(phone, product, offer_message)
            
        except Exception as e:
            logger.error(f"❌ Error enviando ofrecimiento async: {e}")
            return False

