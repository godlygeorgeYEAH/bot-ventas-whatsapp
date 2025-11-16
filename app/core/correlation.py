"""
Módulo de correlación para tracking de logs por cliente.

Usa contextvars para propagar automáticamente el teléfono del cliente
y el ID de conversación a través de todas las llamadas async/sync,
permitiendo filtrar logs por cliente sin modificar cada logger.xxx().
"""

from contextvars import ContextVar
from typing import Optional

# Variables de contexto para tracking por cliente
current_client_phone: ContextVar[Optional[str]] = ContextVar('current_client_phone', default=None)
current_conversation_id: ContextVar[Optional[str]] = ContextVar('current_conversation_id', default=None)


def set_client_context(phone: str, conversation_id: Optional[str] = None) -> None:
    """
    Establecer el contexto del cliente actual.

    Args:
        phone: Número de teléfono del cliente
        conversation_id: UUID de la conversación (opcional)
    """
    current_client_phone.set(phone)
    if conversation_id:
        current_conversation_id.set(conversation_id)


def get_client_context() -> tuple[Optional[str], Optional[str]]:
    """
    Obtener el contexto del cliente actual.

    Returns:
        Tupla (phone, conversation_id)
    """
    return current_client_phone.get(), current_conversation_id.get()


def clear_client_context() -> None:
    """
    Limpiar el contexto del cliente actual.
    Útil para operaciones del sistema o jobs programados.
    """
    current_client_phone.set(None)
    current_conversation_id.set(None)


def correlation_filter(record: dict) -> bool:
    """
    Filter de Loguru para agregar correlation IDs a cada log record.

    Args:
        record: Record de Loguru

    Returns:
        True (siempre permite el log)
    """
    phone = current_client_phone.get()
    conv_id = current_conversation_id.get()

    # Formatear cliente: teléfono o SYSTEM
    record["extra"]["client"] = phone if phone else "SYSTEM"

    # Formatear conversation_id: primeros 8 caracteres o "--------"
    if conv_id:
        record["extra"]["conv_id"] = conv_id[:8]
    else:
        record["extra"]["conv_id"] = "--------"

    return True
