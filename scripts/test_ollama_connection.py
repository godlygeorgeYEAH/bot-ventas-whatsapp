#!/usr/bin/env python3
"""
Script para probar la conexión con Ollama
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


async def test_ollama_connection():
    """Prueba la conexión con Ollama"""
    setup_logging()
    
    logger.info("🤖 Probando conexión con Ollama...")
    logger.info(f"📍 URL: {settings.ollama_base_url}")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Probar endpoint de modelos
            response = await client.get(
                f"{settings.ollama_base_url}/api/tags"
            )
            response.raise_for_status()
            
            data = response.json()
            models = data.get("models", [])
            
            logger.success("✓ Conexión con Ollama exitosa")
            logger.info(f"🧠 Modelos disponibles: {len(models)}")
            
            for model in models:
                name = model.get("name")
                size = model.get("size", 0) / (1024**3)  # GB
                logger.info(f"  - {name} ({size:.1f} GB)")
            
            # Verificar si el modelo configurado está disponible
            model_names = [m.get("name") for m in models]
            if settings.ollama_model in model_names:
                logger.success(f"✓ Modelo configurado '{settings.ollama_model}' está disponible")
            else:
                logger.warning(f"⚠️ Modelo '{settings.ollama_model}' no encontrado")
                logger.info("💡 Descarga el modelo con:")
                logger.info(f"   ollama pull {settings.ollama_model}")
            
            return True
            
    except httpx.ConnectError:
        logger.error("❌ No se pudo conectar con Ollama")
        logger.info("💡 Asegúrate de que Ollama esté corriendo")
        logger.info("💡 Instala Ollama desde: https://ollama.ai")
        logger.info("💡 O inicia el servicio: ollama serve")
        return False
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    result = asyncio.run(test_ollama_connection())
    sys.exit(0 if result else 1)