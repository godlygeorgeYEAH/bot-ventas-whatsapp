"""
Servicio para rastrear y gestionar el estado del bot

Responsable de:
- Monitorear el estado de comunicación con WAHA
- Actualizar estados del bot (online, degraded, incommunicado_critico)
- Rastrear fallos consecutivos
- Proporcionar métricas de salud del sistema
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from loguru import logger

from app.database.models import BotStatus, CommunicationFailure


class BotStatusService:
    """Servicio para gestionar el estado del bot"""

    def __init__(self, db: Session):
        self.db = db
        self.failure_threshold = 3  # Fallos antes de marcar incomunicado
        self.failure_window_minutes = 5

    def _get_or_create_bot_status(self) -> BotStatus:
        """Obtiene el registro de estado del bot o lo crea si no existe"""
        bot_status = self.db.query(BotStatus).first()

        if not bot_status:
            logger.info("📊 Creando registro inicial de bot_status")
            bot_status = BotStatus(
                status="online",
                reason="Sistema iniciado",
                last_update=datetime.utcnow(),
                waha_last_success=datetime.utcnow()
            )
            self.db.add(bot_status)
            self.db.commit()
            self.db.refresh(bot_status)

        return bot_status

    async def update_status(
        self,
        status: str,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> BotStatus:
        """
        Actualiza el estado del bot

        Args:
            status: Nuevo estado (online, degraded, incommunicado_critico, offline)
            reason: Razón del cambio de estado
            metadata: Información adicional

        Returns:
            BotStatus actualizado
        """
        bot_status = self._get_or_create_bot_status()

        # Log del cambio de estado
        if bot_status.status != status:
            logger.warning(f"🤖 Estado del bot cambiando: {bot_status.status} → {status}")
            if reason:
                logger.warning(f"   Razón: {reason}")

        # Actualizar campos
        bot_status.status = status
        bot_status.last_update = datetime.utcnow()

        if reason:
            bot_status.reason = reason

        if metadata:
            bot_status.metadata = metadata

        # Actualizar contador de fallos
        if status == "incommunicado_critico":
            bot_status.waha_consecutive_failures += 1
        elif status == "online":
            bot_status.waha_consecutive_failures = 0
            bot_status.waha_last_success = datetime.utcnow()

        self.db.commit()
        self.db.refresh(bot_status)

        return bot_status

    async def record_success(self) -> None:
        """Registra una comunicación exitosa con WAHA"""
        bot_status = self._get_or_create_bot_status()

        # Si estaba en estado degradado o peor, recuperar a online
        if bot_status.status in ["degraded", "incommunicado_critico"]:
            logger.info(f"✅ Bot recuperado: {bot_status.status} → online")
            await self.update_status(
                status="online",
                reason="Comunicación con WAHA restablecida"
            )
        else:
            # Solo actualizar timestamp
            bot_status.waha_last_success = datetime.utcnow()
            bot_status.waha_consecutive_failures = 0
            self.db.commit()

    async def record_failure(self, reason: str) -> None:
        """Registra un fallo de comunicación con WAHA"""
        bot_status = self._get_or_create_bot_status()
        bot_status.waha_consecutive_failures += 1

        logger.warning(
            f"⚠️ Fallo de comunicación registrado "
            f"({bot_status.waha_consecutive_failures}/{self.failure_threshold}): {reason}"
        )

        self.db.commit()

    async def get_current_status(self) -> Dict[str, Any]:
        """
        Obtiene el estado actual del bot

        Returns:
            Diccionario con información del estado
        """
        bot_status = self._get_or_create_bot_status()

        return {
            "status": bot_status.status,
            "reason": bot_status.reason,
            "last_update": bot_status.last_update,
            "waha_last_success": bot_status.waha_last_success,
            "consecutive_failures": bot_status.waha_consecutive_failures,
            "metadata": bot_status.metadata
        }

    async def get_recent_failures_count(self, minutes: int = 5) -> int:
        """
        Obtiene el conteo de fallos recientes

        Args:
            minutes: Ventana de tiempo en minutos

        Returns:
            Número de fallos en la ventana de tiempo
        """
        threshold = datetime.utcnow() - timedelta(minutes=minutes)

        count = self.db.query(CommunicationFailure).filter(
            CommunicationFailure.created_at >= threshold,
            CommunicationFailure.resolved_at.is_(None)
        ).count()

        return count

    async def is_healthy(self) -> bool:
        """
        Verifica si el bot está en estado saludable

        Returns:
            True si el bot está online, False si está degraded o peor
        """
        bot_status = self._get_or_create_bot_status()
        return bot_status.status == "online"

    async def get_health_summary(self) -> Dict[str, Any]:
        """
        Obtiene un resumen completo de salud del sistema

        Returns:
            Diccionario con métricas de salud
        """
        bot_status = self._get_or_create_bot_status()

        # Contar fallos sin resolver
        unresolved_failures = self.db.query(CommunicationFailure).filter(
            CommunicationFailure.resolved_at.is_(None)
        ).count()

        # Tiempo desde última comunicación exitosa
        time_since_success = None
        if bot_status.waha_last_success:
            time_since_success = (datetime.utcnow() - bot_status.waha_last_success).total_seconds()

        return {
            "status": bot_status.status,
            "is_healthy": bot_status.status == "online",
            "reason": bot_status.reason,
            "consecutive_failures": bot_status.waha_consecutive_failures,
            "unresolved_communication_failures": unresolved_failures,
            "last_success_timestamp": bot_status.waha_last_success,
            "seconds_since_last_success": time_since_success,
            "last_update": bot_status.last_update,
            "metadata": bot_status.metadata
        }
