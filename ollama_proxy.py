"""
Proxy HTTP simple para Ollama
Ejecutar en una terminal separada
"""
from flask import Flask, request, jsonify
import requests
from loguru import logger

app = Flask(__name__)

@app.route('/generate', methods=['POST'])
def generate():
    """Endpoint para generar texto con Ollama"""
    try:
        data = request.json
        
        logger.info(f"[Proxy] Request recibido: {data.get('model')}")
        
        # Llamar a Ollama directamente
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={
                "model": data.get('model', 'llama3.2:latest'),
                "prompt": data.get('prompt'),
                "temperature": data.get('temperature', 0.7),
                "stream": False,
                "options": {
                    "num_predict": data.get('max_tokens', 500)
                }
            },
            timeout=60.0
        )
        
        response.raise_for_status()
        result = response.json()
        
        generated_text = result.get('response', '')
        logger.info(f"[Proxy] Respuesta generada: {len(generated_text)} caracteres")
        
        return jsonify({
            "success": True,
            "response": generated_text
        })
        
    except Exception as e:
        logger.error(f"[Proxy] Error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    logger.info("🚀 Iniciando Ollama Proxy en http://localhost:5001")
    app.run(host='0.0.0.0', port=5001, debug=False)