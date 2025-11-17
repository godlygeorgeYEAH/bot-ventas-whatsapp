"""
Servicio para diagnosticar pérdida de comunicación con WAHA

Cuando un webhook falla después de todos los reintentos, este servicio
ejecuta un diagnóstico para determinar si:
1. Solo el webhook falló (bot aún puede comunicarse)
2. Hay pérdida total de comunicación (bot completamente incomunicado)

El diagnóstico intenta:
- Enviar mensaje simple al usuario
- Enviar notificación al administrador

Si ambos fallan → Pérdida total
Si alguno funciona → Bot comunicado pero webhook falló
"""

import asyncio
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from loguru import logger
from datetime import datetime

from app.clients.waha_client import WAHAClient
from app.database.models import CommunicationFailure, Order
from app.services.bot_status_service import BotStatusService
from config.settings import settings


class CommunicationDiagnosticService:
    """Servicio para diagnosticar pérdida de comunicación"""

    def __init__(self, db: Session):
        self.db = db
        self.waha = WAHAClient()
        self.bot_status_service = BotStatusService(db)
        self.diagnostic_timeout = 10  # Timeout corto para diagnóstico rápido

    async def diagnose_after_webhook_failure(
        self,
        order_id: str,
        customer_phone: str,
        order_number: str
    ) -> Dict[str, Any]:
        """
        Diagnóstica si el bot está comunicado después de fallo de webhook

        Args:
            order_id: ID de la orden afectada
            customer_phone: Teléfono del cliente
            order_number: Número de orden (para logs/mensajes)

        Returns:
            {
                "bot_reachable": bool,
                "user_reached": bool,
                "admin_reached": bool,
                "failure_type": "WEBHOOK_ONLY" | "TOTAL_COMMUNICATION_LOSS",
                "status": "degraded" | "incommunicado_critico"
            }
        """
        logger.info("🔍 Iniciando diagnóstico de comunicación...")
        logger.info(f"   Orden: {order_number}, Cliente: {customer_phone}")

        # Paso 1: Intentar mensaje simple al usuario
        user_reached = await self._try_simple_user_message(
            customer_phone,
            order_number
        )

        if user_reached:
            logger.info("✅ Diagnóstico: Usuario alcanzable - Bot comunicado")
            return await self._handle_webhook_only_failure(
                order_id,
                customer_phone,
                user_reached=True,
                admin_reached=None
            )

        # Paso 2: Usuario no alcanzable, intentar notificar al admin
        admin_reached = await self._try_admin_notification(
            customer_phone,
            order_number,
            order_id
        )

        if admin_reached:
            logger.info("✅ Diagnóstico: Admin alcanzable - Bot comunicado")
            return await self._handle_webhook_only_failure(
                order_id,
                customer_phone,
                user_reached=False,
                admin_reached=True
            )

        # 🚨 CRÍTICO: Ninguno alcanzable - Pérdida total
        logger.critical("🚨🚨🚨 BOT COMPLETAMENTE INCOMUNICADO 🚨🚨🚨")
        return await self._handle_total_communication_loss(
            order_id,
            customer_phone
        )

    async def _try_simple_user_message(
        self,
        phone: str,
        order_number: str
    ) -> bool:
        """
        Intenta enviar mensaje simple al usuario

        Args:
            phone: Teléfono del usuario
            order_number: Número de orden

        Returns:
            True si el mensaje se envió exitosamente
        """
        try:
            logger.info(f"🔍 Intentando mensaje de diagnóstico al usuario {phone}")

            message = (
                f"🤝 *Hemos recibido tu orden*\n\n"
                f"*Orden:* {order_number}\n\n"
                f"Un agente se comunicará contigo pronto para "
                f"completar tu pedido.\n\n"
                f"¡Gracias por tu paciencia! 😊"
            )

            # Intento rápido con timeout corto
            await asyncio.wait_for(
                self.waha.send_text_message(phone, message),
                timeout=self.diagnostic_timeout
            )

            logger.info(f"✅ Usuario {phone} alcanzado en diagnóstico")
            return True

        except asyncio.TimeoutError:
            logger.warning(f"⚠️ Diagnóstico: Timeout al contactar usuario")
            return False
        except Exception as e:
            logger.warning(f"⚠️ Diagnóstico: Usuario no alcanzable - {e}")
            return False

    async def _try_admin_notification(
        self,
        customer_phone: str,
        order_number: str,
        order_id: str
    ) -> bool:
        """
        Intenta notificar al administrador

        Args:
            customer_phone: Teléfono del cliente
            order_number: Número de orden
            order_id: ID de la orden

        Returns:
            True si la notificación se envió exitosamente
        """
        try:
            admin_phone = settings.admin_phone

            if not admin_phone:
                logger.warning("⚠️ ADMIN_PHONE no configurado en settings")
                return False

            logger.info(f"🔍 Intentando notificación de diagnóstico al admin")

            message = (
                f"🚨 *Atención Requerida*\n\n"
                f"*Orden:* {order_number}\n"
                f"*Cliente:* {customer_phone}\n\n"
                f"El webhook falló después de 4 reintentos. "
                f"Por favor contacta al cliente manualmente.\n\n"
                f"⚠️ *Nota:* No se pudo notificar al cliente automáticamente."
            )

            # Intento rápido con timeout corto
            await asyncio.wait_for(
                self.waha.send_text_message(admin_phone, message),
                timeout=self.diagnostic_timeout
            )

            logger.info(f"✅ Admin alcanzado en diagnóstico")
            return True

        except asyncio.TimeoutError:
            logger.warning(f"⚠️ Diagnóstico: Timeout al contactar admin")
            return False
        except Exception as e:
            logger.warning(f"⚠️ Diagnóstico: Admin no alcanzable - {e}")
            return False

    async def _handle_webhook_only_failure(
        self,
        order_id: str,
        customer_phone: str,
        user_reached: bool,
        admin_reached: Optional[bool]
    ) -> Dict[str, Any]:
        """
        Maneja el caso donde solo el webhook falló pero el bot está comunicado

        Args:
            order_id: ID de la orden
            customer_phone: Teléfono del cliente
            user_reached: Si se alcanzó al usuario
            admin_reached: Si se alcanzó al admin

        Returns:
            Resultado del diagnóstico
        """
        logger.warning("⚠️ Bot COMUNICADO pero webhook falló")

        # Crear registro de fallo
        failure = CommunicationFailure(
            failure_type="WEBHOOK_ONLY",
            order_id=order_id,
            customer_phone=customer_phone,
            diagnostic_user_reached=user_reached,
            diagnostic_admin_reached=admin_reached if admin_reached is not None else False
        )
        self.db.add(failure)
        self.db.commit()

        # Actualizar estado del bot
        await self.bot_status_service.update_status(
            status="degraded",
            reason="Webhook de orden falló pero bot responde",
            metadata={
                "order_id": order_id,
                "customer_phone": customer_phone,
                "user_reached": user_reached,
                "admin_reached": admin_reached,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

        return {
            "bot_reachable": True,
            "user_reached": user_reached,
            "admin_reached": admin_reached,
            "failure_type": "WEBHOOK_ONLY",
            "status": "degraded",
            "failure_id": failure.id
        }

    async def _handle_total_communication_loss(
        self,
        order_id: str,
        customer_phone: str
    ) -> Dict[str, Any]:
        """
        Maneja el caso de pérdida total de comunicación

        Args:
            order_id: ID de la orden
            customer_phone: Teléfono del cliente

        Returns:
            Resultado del diagnóstico
        """
        logger.critical("🚨🚨🚨 BOT COMPLETAMENTE INCOMUNICADO 🚨🚨🚨")
        logger.critical(f"   Orden: {order_id}")
        logger.critical(f"   Cliente: {customer_phone}")
        logger.critical(f"   Timestamp: {datetime.utcnow().isoformat()}")

        # Crear registro de fallo
        failure = CommunicationFailure(
            failure_type="TOTAL_COMMUNICATION_LOSS",
            order_id=order_id,
            customer_phone=customer_phone,
            diagnostic_user_reached=False,
            diagnostic_admin_reached=False
        )
        self.db.add(failure)
        self.db.commit()

        # Actualizar estado del bot
        await self.bot_status_service.update_status(
            status="incommunicado_critico",
            reason="No se pudo enviar ningún mensaje después de webhook fallido",
            metadata={
                "order_id": order_id,
                "customer_phone": customer_phone,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

        # TODO: Notificar por canales alternativos
        # - Email urgente al admin
        # - SMS al admin
        # - Webhook a sistema de monitoreo externo
        # - Escribir a archivo de log especial

        return {
            "bot_reachable": False,
            "user_reached": False,
            "admin_reached": False,
            "failure_type": "TOTAL_COMMUNICATION_LOSS",
            "status": "incommunicado_critico",
            "failure_id": failure.id
        }

    async def mark_failure_resolved(
        self,
        failure_id: str,
        resolution_method: str
    ) -> None:
        """
        Marca un fallo de comunicación como resuelto

        Args:
            failure_id: ID del fallo
            resolution_method: Método de resolución (manual_contact, bot_recovered, auto_recovery)
        """
        failure = self.db.query(CommunicationFailure).filter(
            CommunicationFailure.id == failure_id
        ).first()

        if failure:
            failure.resolved_at = datetime.utcnow()
            failure.resolution_method = resolution_method
            self.db.commit()

            logger.info(f"✅ Fallo {failure_id} marcado como resuelto ({resolution_method})")
