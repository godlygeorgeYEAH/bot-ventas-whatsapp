#!/usr/bin/env python3
"""
Script para probar la conexión con WAHA
"""
import sys
import asyncio
from pathlib import Path

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from config.settings import settings
from config.logging_config import setup_logging
from loguru import logger
import httpx


async def test_waha_connection():
    """Prueba la conexión con WAHA"""
    setup_logging()
    
    logger.info("🔌 Probando conexión con WAHA...")
    logger.info(f"📍 URL: {settings.waha_base_url}")
    
    headers = {
        "X-Api-Key": settings.waha_api_key
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Probar endpoint de status
            response = await client.get(
                f"{settings.waha_base_url}/api/sessions",
                headers=headers
            )
            response.raise_for_status()
            
            sessions = response.json()
            logger.success("✓ Conexión con WAHA exitosa")
            logger.info(f"📱 Sesiones disponibles: {len(sessions)}")
            
            for session in sessions:
                logger.info(f"  - {session.get('name')}: {session.get('status')}")
            
            return True
            
    except httpx.ConnectError:
        logger.error("❌ No se pudo conectar con WAHA")
        logger.info("💡 Asegúrate de que WAHA esté corriendo en " + settings.waha_base_url)
        logger.info("💡 Puedes iniciar WAHA con Docker:")
        logger.info("   docker run -it -p 3000:3000 devlikeapro/waha")
        return False
        
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ Error HTTP: {e.response.status_code}")
        if e.response.status_code == 401:
            logger.error("🔐 API Key inválida. Verifica WAHA_API_KEY en .env")
        return False
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    result = asyncio.run(test_waha_connection())
    sys.exit(0 if result else 1)