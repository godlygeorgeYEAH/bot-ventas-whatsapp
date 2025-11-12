import httpx
from loguru import logger
import requests
import asyncio 
from config.settings import settings
from typing import Dict, Any, Optional, List
import json
import concurrent.futures
import aiohttp
class OllamaClient:
    """Cliente completo para interactuar con Ollama"""
    
    def __init__(self):
        self.base_url = settings.ollama_base_url.rstrip('/')
        self.model = settings.ollama_model
        self.timeout = httpx.Timeout(settings.ollama_timeout, connect=300.0)
    
    async def generate(
        self,
        prompt: str,
        model: str = "llama3.2:latest",
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> str:
        """Genera texto usando Ollama via proxy HTTP"""
        logger.info(f"🤖 [Ollama] Llamando a Ollama via proxy: {model}")
        logger.info(f"📝 [Ollama] Prompt (primeros 100 chars): {prompt[:100]}...")
        
        try:
            import aiohttp
            
            # Llamar al proxy (no directamente a Ollama)
            proxy_url = "http://localhost:5001/generate"
            
            payload = {
                "model": model,
                "prompt": prompt,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            logger.info(f"⏱️ [Ollama] Enviando a proxy...")
            
            timeout = aiohttp.ClientTimeout(total=70.0)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(proxy_url, json=payload) as response:
                    result = await response.json()
                    
                    if result.get("success"):
                        generated_text = result["response"]
                        logger.info(f"✅ [Ollama] Texto generado: {len(generated_text)} caracteres")
                        return generated_text.strip()
                    else:
                        raise Exception(f"Proxy error: {result.get('error')}")
            
        except Exception as e:
            logger.error(f"❌ [Ollama] Error: {e}", exc_info=True)
            raise

    async def chat(
        self,
        messages: List[Dict[str, str]],
        format: Optional[str] = None,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Chat con contexto de mensajes (API de chat)
        
        Args:
            messages: Lista de mensajes [{"role": "user", "content": "..."}]
            format: 'json' si se espera respuesta en JSON
            temperature: Temperatura del modelo
            
        Returns:
            Dict con la respuesta
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }
        
        if format == "json":
            payload["format"] = "json"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.debug(f"🤖 Chat con Ollama: {len(messages)} mensajes")
                
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload
                )
                response.raise_for_status()
                
                result = response.json()
                
                # Parsear respuesta si es JSON
                if format == "json":
                    try:
                        content = result["message"]["content"]
                        result["parsed"] = json.loads(content)
                    except json.JSONDecodeError as e:
                        logger.error(f"Error parseando JSON: {e}")
                        result["parsed"] = {}
                
                logger.debug(f"✓ Chat response recibida")
                return result
                
        except Exception as e:
            logger.error(f"Error en chat con Ollama: {e}")
            raise
    
    async def embed(self, text: str) -> List[float]:
        """
        Genera embeddings para un texto
        
        Args:
            text: Texto para generar embeddings
            
        Returns:
            Lista de floats representando el embedding
        """
        payload = {
            "model": self.model,
            "prompt": text
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json=payload
                )
                response.raise_for_status()
                
                result = response.json()
                return result.get("embedding", [])
                
        except Exception as e:
            logger.error(f"Error generando embeddings: {e}")
            raise
    
    async def check_model_availability(self) -> bool:
        """
        Verifica si el modelo configurado está disponible
        
        Returns:
            True si el modelo está disponible
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                
                data = response.json()
                models = [m["name"] for m in data.get("models", [])]
                
                is_available = self.model in models
                if is_available:
                    logger.info(f"✓ Modelo {self.model} disponible")
                else:
                    logger.warning(f"⚠️ Modelo {self.model} no encontrado")
                    logger.info(f"Modelos disponibles: {', '.join(models)}")
                
                return is_available
                
        except Exception as e:
            logger.error(f"Error verificando modelo: {e}")
            return False