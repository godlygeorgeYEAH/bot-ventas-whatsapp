"""
Servicio de retry logic para webhooks
"""
import asyncio
from typing import Callable, Any, Optional
from loguru import logger


class WebhookRetryService:
    """Servicio para reintentar operaciones de webhook con exponential backoff"""
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0
    ):
        """
        Args:
            max_retries: Número máximo de reintentos
            initial_delay: Delay inicial en segundos
            max_delay: Delay máximo en segundos
            exponential_base: Base para el cálculo exponencial
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
    
    async def execute_with_retry(
        self,
        operation: Callable,
        operation_name: str,
        *args,
        **kwargs
    ) -> tuple[bool, Optional[Any]]:
        """
        Ejecuta una operación con reintentos automáticos
        
        Args:
            operation: Función async a ejecutar
            operation_name: Nombre descriptivo de la operación (para logs)
            *args, **kwargs: Argumentos para la operación
            
        Returns:
            (success: bool, result: Any)
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(f"🔄 [{operation_name}] Intento {attempt + 1}/{self.max_retries + 1}")
                
                # Ejecutar operación
                result = await operation(*args, **kwargs)
                
                logger.info(f"✅ [{operation_name}] Operación exitosa en intento {attempt + 1}")
                return True, result
                
            except Exception as e:
                last_exception = e
                logger.warning(f"⚠️ [{operation_name}] Fallo en intento {attempt + 1}: {e}")
                
                # Si es el último intento, no esperar
                if attempt == self.max_retries:
                    logger.error(f"❌ [{operation_name}] Todos los intentos fallaron")
                    break
                
                # Calcular delay con exponential backoff
                delay = min(
                    self.initial_delay * (self.exponential_base ** attempt),
                    self.max_delay
                )
                
                logger.info(f"⏳ [{operation_name}] Esperando {delay:.1f}s antes del siguiente intento...")
                await asyncio.sleep(delay)
        
        # Todos los intentos fallaron
        return False, last_exception
    
    def calculate_next_delay(self, attempt: int) -> float:
        """
        Calcula el delay para el siguiente intento
        
        Args:
            attempt: Número de intento (0-indexed)
            
        Returns:
            Delay en segundos
        """
        return min(
            self.initial_delay * (self.exponential_base ** attempt),
            self.max_delay
        )


# Instancia global con configuración por defecto
# Distribución de reintentos en ~3 minutos para dar tiempo a que WAHA arranque:
# Intento 1: 0s
# Intento 2: +30s = 30s
# Intento 3: +60s = 90s
# Intento 4: +90s = 180s (3 minutos)
#
# ⚠️ IMPORTANTE: Límite de reintentos
# - Después de estos 4 intentos, NO hay reintentos automáticos adicionales
# - Si todos fallan, se ejecuta el diagnóstico de comunicación (CommunicationDiagnosticService)
# - El diagnóstico es de UN SOLO INTENTO (timeout de 10s)
# - Si el diagnóstico detecta pérdida total, la orden queda en PENDING esperando intervención manual
#
# TODO: Considerar estrategia de reintentos a largo plazo para pérdidas totales
# - ¿Reintentar cada X minutos durante Y horas?
# - ¿Notificar al admin después de N fallos consecutivos?
# - ¿Marcar orden como "requiere_atención_urgente" para vista de admin?
webhook_retry_service = WebhookRetryService(
    max_retries=3,          # 3 reintentos (4 intentos totales)
    initial_delay=30.0,     # Empezar con 30 segundos
    max_delay=90.0,         # Máximo 90 segundos entre intentos
    exponential_base=2.0    # Duplicar cada vez: 30s, 60s, 90s (limitado por max_delay)
)

