"""
Script para probar envío de imagen
"""
import sys
sys.path.append('.')

from app.clients.waha_client import WAHAClient
from loguru import logger
import os

def test_send_image():
    """Prueba envío de imagen"""
    
    # Crear imagen de prueba si no existe
    test_image = "static/products/images/test.png"
    
    if not os.path.exists(test_image):
        logger.warning(f"⚠️  Imagen de prueba no existe: {test_image}")
        logger.info("Crea una imagen de prueba o usa una existente")
        return
    
    # Número de prueba (tu número)
    test_phone = "15737457069@c.us"  # Reemplaza con tu número
    
    try:
        waha_client = WAHAClient()
        
        logger.info("📸 Enviando imagen de prueba...")
        
        result = waha_client.send_image_from_file(
            chat_id=test_phone,
            file_path=test_image,
            caption="Prueba de imagen de producto"
        )
        
        logger.info(f"✅ Imagen enviada: {result}")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")

if __name__ == "__main__":
    test_send_image()
