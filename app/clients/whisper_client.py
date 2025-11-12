import tempfile
import os
from pathlib import Path
from loguru import logger
from config.settings import settings
from typing import Optional
import subprocess


class WhisperClient:
    """Cliente para transcribir audio usando Whisper"""
    
    def __init__(self):
        self.model = settings.whisper_model
        self.language = settings.whisper_language
        self.use_ollama = True  # Intentar usar Ollama primero
    
    async def transcribe_audio(
        self, 
        audio_data: bytes,
        audio_format: str = "ogg"
    ) -> Optional[str]:
        """
        Transcribe audio a texto
        
        Args:
            audio_data: Bytes del archivo de audio
            audio_format: Formato del audio (ogg, mp3, wav, etc)
            
        Returns:
            Texto transcrito o None si falla
        """
        try:
            # Guardar audio temporalmente
            with tempfile.NamedTemporaryFile(
                suffix=f".{audio_format}",
                delete=False
            ) as temp_audio:
                temp_audio.write(audio_data)
                temp_path = temp_audio.name
            
            try:
                # Intentar con Ollama primero (si está disponible)
                if self.use_ollama:
                    text = await self._transcribe_with_ollama(temp_path)
                    if text:
                        return text
                
                # Fallback a Whisper local
                text = await self._transcribe_with_whisper(temp_path)
                return text
                
            finally:
                # Limpiar archivo temporal
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            
        except Exception as e:
            logger.error(f"Error transcribiendo audio: {e}")
            return None
    
    async def _transcribe_with_ollama(self, audio_path: str) -> Optional[str]:
        """
        Transcribe usando Ollama (si tiene soporte para Whisper)
        
        Nota: Ollama puede no tener Whisper integrado aún.
        Esta es una implementación preparada para el futuro.
        """
        try:
            # TODO: Implementar cuando Ollama soporte Whisper
            logger.debug("Transcripción con Ollama no disponible aún")
            return None
            
        except Exception as e:
            logger.debug(f"Ollama whisper no disponible: {e}")
            return None
    
    async def _transcribe_with_whisper(self, audio_path: str) -> Optional[str]:
        """
        Transcribe usando Whisper CLI local
        
        Requiere: pip install openai-whisper
        """
        try:
            logger.info(f"🎤 Transcribiendo audio con Whisper ({self.model})...")
            
            # Usar subprocess para llamar a whisper
            cmd = [
                "whisper",
                audio_path,
                "--model", self.model,
                "--language", self.language,
                "--output_format", "txt",
                "--output_dir", tempfile.gettempdir()
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                logger.error(f"Error en whisper: {result.stderr}")
                return None
            
            # Leer el archivo de salida
            audio_name = Path(audio_path).stem
            txt_path = Path(tempfile.gettempdir()) / f"{audio_name}.txt"
            
            if txt_path.exists():
                text = txt_path.read_text().strip()
                txt_path.unlink()  # Limpiar
                
                logger.info(f"✓ Audio transcrito: {len(text)} caracteres")
                return text
            
            return None
            
        except subprocess.TimeoutExpired:
            logger.error("Timeout transcribiendo audio")
            return None
        except FileNotFoundError:
            logger.error("Whisper no está instalado. Instala con: pip install openai-whisper")
            return None
        except Exception as e:
            logger.error(f"Error con Whisper: {e}")
            return None