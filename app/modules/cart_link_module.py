"""
Módulo para generar y enviar links únicos de carrito

Este módulo maneja la interacción cuando el usuario quiere hacer un pedido.
En lugar de recoger productos por chat, genera un link único que abre
la webapp del carrito.
"""
from typing import Dict, Any, Optional
from loguru import logger

from config.database import get_db_context
from app.services.cart_service import CartService
from app.database.models import Customer
from app.clients.waha_client import WAHAClient
from config.settings import settings


class CartLinkModule:
    """Módulo para generar links de carrito"""
    
    def __init__(self):
        self.name = "CartLinkModule"
        self.intent = "create_order"
        self.waha = WAHAClient()
    
    def get_intent(self) -> str:
        """Retorna la intención que maneja este módulo"""
        return self.intent
    
    def handle(
        self,
        message: str,
        context: Dict[str, Any],
        phone: str
    ) -> Dict[str, Any]:
        """
        Genera y envía un link único de carrito al usuario
        
        Proceso:
        1. Obtiene/crea cliente
        2. Verifica si ya tiene sesión activa
        3. Genera nuevo token y link
        4. Envía link por WhatsApp
        5. Guarda sesión en contexto
        """
        logger.info(f"🛒 [{self.name}] Generando link de carrito para {phone}")
        
        try:
            with get_db_context() as db:
                # 1. Obtener/crear cliente
                customer = db.query(Customer).filter(Customer.phone == phone).first()
                
                if not customer:
                    logger.warning(f"⚠️ Cliente no encontrado: {phone}")
                    return {
                        "response": "❌ No encontré tu perfil de cliente. Por favor contacta al administrador.",
                        "context_updates": {
                            "current_module": None
                        }
                    }
                
                # 2. Crear servicio de carrito
                cart_service = CartService(db)
                
                # 3. Verificar si ya tiene sesiones activas
                active_sessions = cart_service.get_customer_active_sessions(customer.id)
                
                if active_sessions and len(active_sessions) > 0:
                    # Ya tiene una sesión activa, reenviar el mismo link
                    existing_session = active_sessions[0]
                    cart_link = f"{settings.webapp_base_url}/cart/{existing_session.token}"
                    
                    logger.info(f"♻️ Reenviando link existente: {existing_session.token[:8]}...")
                    
                    response = (
                        f"¡Hola {customer.name}! 👋\n\n"
                        f"Ya tienes un carrito activo. Puedes continuar usando este link:\n\n"
                        f"🛒 {cart_link}\n\n"
                        f"⏰ Este link expira el {existing_session.expires_at.strftime('%d/%m/%Y a las %H:%M')}\n\n"
                        f"✨ *Puedes modificar tu orden las veces que quieras hasta que se procese tu pago*\n\n"
                        f"Selecciona los productos que deseas y confirma tu orden. "
                        f"Luego te pediré tu ubicación GPS y método de pago. 📍💳"
                    )
                else:
                    # 4. Crear nueva sesión de carrito
                    result = cart_service.create_cart_session(
                        customer_id=customer.id,
                        hours_valid=settings.cart_session_hours
                    )
                    
                    if not result.get("success"):
                        logger.error(f"❌ Error creando sesión: {result.get('error')}")
                        return {
                            "response": "❌ Hubo un error al generar tu carrito. Por favor intenta de nuevo.",
                            "context_updates": {
                                "current_module": None
                            }
                        }
                    
                    cart_link = result["cart_link"]
                    expires_at = result["expires_at"]
                    
                    logger.info(f"✅ Sesión creada: {result['token'][:8]}...")
                    
                    from datetime import datetime
                    expires_dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                    
                    response = (
                        f"¡Hola {customer.name}! 👋\n\n"
                        f"He preparado tu carrito de compras personalizado:\n\n"
                        f"🛒 {cart_link}\n\n"
                        f"⏰ Este link expira el {expires_dt.strftime('%d/%m/%Y a las %H:%M')}\n\n"
                        f"*¿Cómo funciona?*\n"
                        f"1. Abre el link en tu navegador\n"
                        f"2. Selecciona los productos que deseas\n"
                        f"3. Confirma tu orden\n"
                        f"4. Yo te pediré tu ubicación GPS y método de pago\n\n"
                        f"✨ *Puedes modificar tu orden las veces que quieras hasta que se procese tu pago*\n\n"
                        f"¿Tienes alguna pregunta? Escríbeme y con gusto te ayudo. 😊"
                    )
                
                # 5. Guardar en contexto
                return {
                    "response": response,
                    "context_updates": {
                        "current_module": None,  # No necesitamos mantener el módulo activo
                        "cart_session_token": result.get("token") if not active_sessions else existing_session.token,
                        "awaiting_cart_completion": True  # Flag para saber que estamos esperando que complete el carrito
                    }
                }
        
        except Exception as e:
            logger.error(f"❌ Error en CartLinkModule: {e}", exc_info=True)
            return {
                "response": "❌ Hubo un error al procesar tu solicitud. Por favor intenta de nuevo.",
                "context_updates": {
                    "current_module": None
                }
            }

