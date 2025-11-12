import httpx
from loguru import logger
from config.settings import settings
from typing import Optional, Dict, Any
import requests

class WAHAClient:
    """Cliente completo para interactuar con WAHA (WhatsApp HTTP API)"""
    
    def __init__(self):
        self.base_url = settings.waha_base_url.rstrip('/')
        self.api_key = settings.waha_api_key
        self.session_name = settings.waha_session_name
        self.headers = {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json"
        }
        self.timeout = httpx.Timeout(30.0, connect=10.0)
    
    async def send_text_message(
    self,
    phone: str,
    message: str
) -> Dict:
        """Envía un mensaje de texto"""
        try:
            # Asegurar formato correcto
            chat_id = phone if "@c.us" in phone else f"{phone}@c.us"
            
            logger.info(f"🔵 [WAHA] Enviando a {chat_id}")
            logger.info(f"🔵 [WAHA] Mensaje: '{message[:50]}...'")
            
            url = f"{self.base_url}/api/sendText"
            logger.info(f"🔵 [WAHA] URL: {url}")
            
            payload = {
                "chatId": chat_id,
                "text": message,
                "session": self.session_name
            }
            
            logger.info(f"🔵 [WAHA] Payload: {payload}")
            
            # Timeout más corto
            timeout = httpx.Timeout(10.0, connect=5.0)
            
            async with httpx.AsyncClient(timeout=timeout) as client:
                logger.info(f"🔵 [WAHA] Enviando request...")
                
                try:
                    response = await client.post(
                        url,
                        json=payload,
                        headers=self.headers
                    )
                    
                    logger.info(f"🔵 [WAHA] ✅ Response recibido!")
                    logger.info(f"🔵 [WAHA] Status: {response.status_code}")
                    logger.info(f"🔵 [WAHA] Body: {response.text[:500]}")
                    
                    response.raise_for_status()
                    result = response.json()
                    
                    logger.info(f"✅ Mensaje enviado a {phone}")
                    return result
                    
                except httpx.TimeoutException as e:
                    logger.error(f"⏰ [WAHA] Timeout: {e}")
                    raise Exception(f"WAHA tardó más de 10s en responder")
                except httpx.HTTPStatusError as e:
                    logger.error(f"❌ [WAHA] HTTP Error {e.response.status_code}: {e.response.text}")
                    raise
                
        except Exception as e:
            logger.error(f"❌ Error enviando mensaje: {e}", exc_info=True)
            raise
    async def send_image(
        self,
        phone: str,
        image_url: str,
        caption: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Envia una imagen por URL
        
        Args:
            phone: Numero de telefono
            image_url: URL publica de la imagen
            caption: Texto opcional que acompaña la imagen
        """
        chat_id = self._format_chat_id(phone)
        
        payload = {
            "session": self.session_name,
            "chatId": chat_id,
            "file": {
                "url": image_url
            }
        }
        
        if caption:
            payload["file"]["caption"] = caption
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/sendImage",
                    json=payload,
                    headers=self.headers
                )
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"Imagen enviada a {phone}")
                return result
                
        except Exception as e:
            logger.error(f"Error enviando imagen: {e}")
            raise
    
    def send_image_from_file(
        self,
        chat_id: str,
        file_path: str,
        caption: str = None
    ) -> dict:
        """
        Envía una imagen desde archivo local
        
        Args:
            chat_id: ID del chat (phone@c.us)
            file_path: Path al archivo de imagen local
            caption: Texto que acompaña la imagen (opcional)
        """
        import os
        import base64
        
        try:
            # Verificar que el archivo existe
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Imagen no encontrada: {file_path}")
            
            logger.info(f"📸 Enviando imagen a {chat_id}")
            logger.info(f"   Archivo: {file_path}")
            
            # Leer archivo y convertir a base64
            with open(file_path, 'rb') as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Determinar mimetype
            extension = os.path.splitext(file_path)[1].lower()
            mimetype_map = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.webp': 'image/webp'
            }
            mimetype = mimetype_map.get(extension, 'image/jpeg')
            
            # Preparar payload
            payload = {
                "chatId": chat_id,
                "file": {
                    "mimetype": mimetype,
                    "data": image_data,
                    "filename": os.path.basename(file_path)
                },
                "session": self.session_name
            }
            
            print(payload)
            if caption:
                payload["caption"] = caption
            
            # Enviar
            response = requests.post(
                f"{self.base_url}/api/sendImage",
                headers=self.headers,
                json=payload,
                timeout=30.0
            )


            
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"✅ Imagen enviada exitosamente")
            return result
            
        except FileNotFoundError as e:
            logger.error(f"❌ {e}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error enviando imagen: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Error inesperado: {e}")
            raise
    async def download_media(self, message_data: Dict) -> Optional[bytes]:
        """
        Descarga un archivo multimedia del mensaje
        
        Args:
            message_data: Datos del mensaje de WAHA que contiene media
            
        Returns:
            Bytes del archivo o None si no se pudo descargar
        """
        try:
            # WAHA puede proporcionar la media de diferentes formas
            media_url = message_data.get("mediaUrl")
            
            if not media_url:
                logger.warning("No se encontro mediaUrl en el mensaje")
                return None
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                # Si es una URL relativa, construir URL completa
                if media_url.startswith("/"):
                    media_url = f"{self.base_url}{media_url}"
                
                response = await client.get(
                    media_url,
                    headers={"X-Api-Key": self.api_key}
                )
                response.raise_for_status()
                
                logger.info(f"Media descargada: {len(response.content)} bytes")
                return response.content
                
        except Exception as e:
            logger.error(f"Error descargando media: {e}")
            return None
    
    async def mark_as_read(self, phone: str, message_id: str) -> bool:
        """
        Marca un mensaje como leido
        
        Args:
            phone: Numero de telefono
            message_id: ID del mensaje
        """
        chat_id = self._format_chat_id(phone)
        
        payload = {
            "session": self.session_name,
            "chatId": chat_id,
            "messageId": message_id
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"{self.base_url}/api/markAsRead",
                    json=payload,
                    headers=self.headers
                )
                logger.debug(f"Mensaje {message_id} marcado como leido")
                return True
        except Exception as e:
            logger.warning(f"Error marcando como leido: {e}")
            return False
    
    async def send_location(
        self,
        phone: str,
        latitude: float,
        longitude: float,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Envía una ubicación GPS por WhatsApp
        
        Args:
            phone: Número de teléfono
            latitude: Latitud GPS
            longitude: Longitud GPS
            title: Título opcional de la ubicación
            
        Returns:
            Respuesta de WAHA
        """
        try:
            chat_id = self._format_chat_id(phone)
            
            logger.info(f"📍 [WAHA] Enviando ubicación a {chat_id}: {latitude}, {longitude}")
            
            payload = {
                "session": self.session_name,
                "chatId": chat_id,
                "latitude": latitude,
                "longitude": longitude
            }
            
            if title:
                payload["title"] = title
            
            url = f"{self.base_url}/api/sendLocation"
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self.headers
                )
                
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"✅ [WAHA] Ubicación enviada exitosamente")
                return result
                
        except Exception as e:
            logger.error(f"❌ Error enviando ubicación: {e}", exc_info=True)
            raise
    
    async def send_typing(self, phone: str, duration: int = 3) -> bool:
        """
        Muestra indicador de 'escribiendo...'
        
        Args:
            phone: Numero de telefono
            duration: Duracion en segundos
        """
        chat_id = self._format_chat_id(phone)
        
        payload = {
            "session": self.session_name,
            "chatId": chat_id,
            "duration": duration * 1000  # Convertir a milisegundos
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"{self.base_url}/api/startTyping",
                    json=payload,
                    headers=self.headers
                )
                logger.debug(f"Typing indicator enviado a {phone}")
                return True
        except Exception as e:
            logger.warning(f"Error enviando typing: {e}")
            return False
    
    async def stop_typing(self, phone: str) -> bool:
        """
        Detiene el indicador de 'escribiendo...'
        """
        chat_id = self._format_chat_id(phone)
        
        payload = {
            "session": self.session_name,
            "chatId": chat_id
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"{self.base_url}/api/stopTyping",
                    json=payload,
                    headers=self.headers
                )
                return True
        except Exception as e:
            logger.warning(f"Error deteniendo typing: {e}")
            return False
    
    async def get_session_status(self) -> Dict[str, Any]:
        """Obtiene el estado de la sesion de WhatsApp"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/api/sessions/{self.session_name}",
                    headers=self.headers
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error obteniendo estado de sesion: {e}")
            return {"status": "UNKNOWN"}
    
    def _format_chat_id(self, phone: str) -> str:
        """
        Formatea el numero de telefono para WAHA
        
        Args:
            phone: Numero de telefono en cualquier formato
            
        Returns:
            Numero formateado como chatId de WhatsApp
        """
        # Remover caracteres no numericos excepto '+'
        phone_clean = ''.join(c for c in phone if c.isdigit() or c == '+')
        
        # Remover '+' del inicio si existe
        phone_clean = phone_clean.lstrip('+')
        
        # Agregar sufijo de WhatsApp si no lo tiene
        if not phone_clean.endswith("@c.us"):
            phone_clean = f"{phone_clean}@c.us"
        
        return phone_clean
    
    def _extract_phone_from_chat_id(self, chat_id: str) -> str:
        """
        Extrae el numero de telefono limpio de un chatId
        
        Args:
            chat_id: ID del chat (ej: 1234567890@c.us)
            
        Returns:
            Numero de telefono limpio
        """
        return chat_id.replace("@c.us", "").replace("@g.us", "")