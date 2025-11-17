from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Configuración centralizada de la aplicación"""
    
    # Message Buffering
    message_debounce_seconds: float = 40.0  # Tiempo de espera después del último mensaje
    enable_message_buffering: bool = True  # Habilitar/deshabilitar agrupación
    max_buffered_messages: int = 4  # Máximo de mensajes a agrupar
    
    # Application
    app_name: str = "BotVentasWhatsApp"
    app_env: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    webhook_secret: str
    
    # WAHA
    waha_base_url: str
    waha_api_key: str
    waha_session_name: str = "default"
    
    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:latest"
    ollama_timeout: int = 120
    
    # Whisper
    whisper_model: str = "base"
    whisper_language: str = "es"
    
    # Database
    database_url: str
    
    # Redis (opcional)
    redis_url: str = "redis://localhost:6379/0"
    
    # Business Rules
    max_validation_attempts: int = 3
    session_timeout_minutes: int = 30
    max_context_messages: int = 10
    
    # Feature Flags
    enable_voice_messages: bool = True
    enable_image_messages: bool = True
    enable_rate_limiting: bool = True
    
    # Product Offerings
    enable_product_offers: bool = True  # Habilitar/deshabilitar ofrecimientos
    offer_after_order: bool = True  # Ofrecer producto después de completar orden
    offer_after_greeting: bool = True  # Ofrecer producto después de saludo
    offer_with_image: bool = True  # Incluir imagen del producto en el ofrecimiento
    offer_image_as_caption: bool = True  # True: imagen con caption, False: solo texto sin imagen
    
    # WebApp Carrito
    webapp_base_url: str = "http://localhost:5174"  # URL base de la webapp del carrito
    cart_session_hours: int = 24  # Horas de validez de una sesión de carrito

    # Admin Configuration
    admin_phone: str = ""  # Número de WhatsApp del administrador para notificaciones

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Singleton de configuración"""
    return Settings()


settings = get_settings()