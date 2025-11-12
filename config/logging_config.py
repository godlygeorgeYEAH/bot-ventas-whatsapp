from loguru import logger
from config.settings import settings
import sys
from typing import Optional


def setup_logging(level: Optional[str] = None):
    """
    Configura el sistema de logging con nivel ajustable
    
    Args:
        level: Nivel de logging (TRACE, DEBUG, INFO, WARNING, ERROR, CRITICAL)
               Si es None, usa settings.log_level
    
    Niveles recomendados:
        - WARNING: Producción (solo errores y advertencias)
        - INFO: Desarrollo normal (flujo principal)
        - DEBUG: Debugging detallado (datos de contexto, estados)
        - TRACE: Debugging exhaustivo (todo)
    """
    log_level = level or settings.log_level
    
    # Remover handler por defecto
    logger.remove()
    
    # Console handler con formato simplificado para niveles bajos
    if log_level in ["WARNING", "ERROR", "CRITICAL"]:
        # Formato simple para producción
        console_format = "<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
    else:
        # Formato detallado para desarrollo
        console_format = "<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
    
    logger.add(
        sys.stdout,
        format=console_format,
        level=log_level,
        colorize=True
    )
    
    # File handler - siempre guarda DEBUG o superior
    logger.add(
        "logs/app_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="30 days",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
        level="DEBUG"
    )
    
    logger.info(f"✓ Logging configurado (nivel: {log_level})")
    return logger