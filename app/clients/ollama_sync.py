"""
Cliente síncrono para Ollama (se ejecuta en proceso separado)
"""
import requests
from loguru import logger


def call_ollama_sync(base_url: str, model: str, prompt: str, temperature: float, max_tokens: int) -> dict:
    """
    Llamada síncrona a Ollama que se ejecutará en un proceso separado
    
    Returns:
        dict con 'success', 'response' o 'error'
    """
    try:
        logger.info(f"[ProcessPool] Llamando a Ollama en proceso separado...")
        
        url = f"{base_url}/api/generate"
        
        payload = {
            "model": model,
            "prompt": prompt,
            "temperature": temperature,
            "stream": False,
            "options": {
                "num_predict": max_tokens
            }
        }
        
        response = requests.post(url, json=payload, timeout=60.0)
        response.raise_for_status()
        
        result = response.json()
        generated_text = result.get("response", "")
        
        logger.info(f"[ProcessPool] ✅ Respuesta recibida: {len(generated_text)} caracteres")
        
        return {
            "success": True,
            "response": generated_text.strip()
        }
        
    except Exception as e:
        logger.error(f"[ProcessPool] ❌ Error: {e}")
        return {
            "success": False,
            "error": str(e)
        }