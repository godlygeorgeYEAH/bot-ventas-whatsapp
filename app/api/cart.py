"""
API endpoints para gestión de carrito
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from loguru import logger

from config.database import get_db
from app.services.cart_service import CartService
from app.services.order_service import OrderService
from app.database.models import Customer, Order, OrderItem, Product, OrderStatus
from app.core.context_manager import ContextManager
from app.clients.waha_client import WAHAClient

router = APIRouter(prefix="/api/cart", tags=["cart"])


# ============================================================================
# MODELOS DE REQUEST/RESPONSE
# ============================================================================

class CreateCartRequest(BaseModel):
    """Request para crear sesión de carrito"""
    customer_phone: str = Field(..., description="Teléfono del cliente")
    suggested_products: Optional[List[str]] = Field(
        None, 
        description="IDs de productos pre-sugeridos (opcional)"
    )
    hours_valid: Optional[int] = Field(
        24, 
        description="Horas de validez del token",
        ge=1,
        le=168  # max 1 semana
    )


class CreateCartResponse(BaseModel):
    """Response de creación de carrito"""
    success: bool
    session_id: Optional[str] = None
    token: Optional[str] = None
    cart_link: Optional[str] = None
    expires_at: Optional[str] = None
    suggested_products: Optional[List[str]] = None
    error: Optional[str] = None


class CartSessionInfo(BaseModel):
    """Información de sesión de carrito"""
    valid: bool
    session_id: Optional[str] = None
    customer_id: Optional[str] = None
    cart_data: Optional[Dict[str, Any]] = None
    expires_at: Optional[str] = None
    error: Optional[str] = None
    message: Optional[str] = None


class ProductInfo(BaseModel):
    """Información de producto"""
    id: str
    name: str
    description: Optional[str]
    price: float
    stock: int
    category: Optional[str]
    sku: Optional[str]
    image_path: Optional[str]


class CompleteCartRequest(BaseModel):
    """Request para completar carrito (desde webapp)"""
    products: List[Dict[str, Any]] = Field(
        ..., 
        description="Lista de productos con {product_id, quantity}"
    )
    total: float = Field(..., description="Total de la orden", ge=0)


class CompleteCartResponse(BaseModel):
    """Response de completar carrito"""
    success: bool
    message: str
    order_id: Optional[str] = None
    error: Optional[str] = None


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/create", response_model=CreateCartResponse)
async def create_cart_session(
    request: CreateCartRequest,
    db: Session = Depends(get_db)
):
    """
    Crea una nueva sesión de carrito con token único
    
    Este endpoint es llamado por el bot cuando el usuario
    quiere hacer un pedido. Genera un link único que se
    envía por WhatsApp.
    
    **Proceso:**
    1. Valida que el cliente exista
    2. Genera token UUID único
    3. Crea sesión en BD con expiración
    4. Retorna link completo para webapp
    
    **Ejemplo de respuesta:**
    ```json
    {
        "success": true,
        "token": "abc123-xyz-...",
        "cart_link": "http://localhost:5173/cart/abc123-xyz-...",
        "expires_at": "2025-11-12T10:00:00",
        "suggested_products": ["product-id-1"]
    }
    ```
    """
    try:
        # Validar que el cliente existe
        customer = db.query(Customer).filter(
            Customer.phone == request.customer_phone
        ).first()
        
        if not customer:
            raise HTTPException(
                status_code=404,
                detail=f"Cliente no encontrado: {request.customer_phone}"
            )
        
        # Crear sesión de carrito
        cart_service = CartService(db)
        result = cart_service.create_cart_session(
            customer_id=customer.id,
            hours_valid=request.hours_valid or 24,
            suggested_products=request.suggested_products
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Error creando sesión de carrito")
            )
        
        logger.info(f"✅ API: Sesión de carrito creada para {request.customer_phone}")
        
        return CreateCartResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ API: Error creando sesión de carrito: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{token}", response_model=CartSessionInfo)
async def get_cart_session(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Obtiene información de una sesión de carrito por token
    
    Este endpoint es llamado por la webapp cuando se abre
    el link del carrito. Valida el token y devuelve los
    datos necesarios para mostrar la interfaz.
    
    **Validaciones:**
    - Token existe
    - Token no ha sido usado
    - Token no ha expirado
    
    **Ejemplo de respuesta válida:**
    ```json
    {
        "valid": true,
        "session_id": "session-id",
        "customer_id": "customer-id",
        "cart_data": {"suggested_products": ["product-id-1"]},
        "expires_at": "2025-11-12T10:00:00"
    }
    ```
    
    **Ejemplo de respuesta inválida:**
    ```json
    {
        "valid": false,
        "error": "token_expired",
        "message": "Este link expiró. Solicita uno nuevo."
    }
    ```
    """
    try:
        cart_service = CartService(db)
        validation = cart_service.validate_cart_session(token)
        
        logger.info(f"🔍 API: Validación de token {token[:8]}... → valid={validation.get('valid')}")
        
        return CartSessionInfo(**validation)
        
    except Exception as e:
        logger.error(f"❌ API: Error validando sesión: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{token}/products", response_model=List[ProductInfo])
async def get_cart_products(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Obtiene la lista de productos disponibles para el carrito
    
    Este endpoint es llamado por la webapp después de validar
    el token, para mostrar el catálogo de productos disponibles.
    
    **Solo devuelve productos:**
    - Activos (is_active=true)
    - Con stock disponible (stock > 0)
    
    **Respuesta:**
    Lista de productos ordenados alfabéticamente
    """
    try:
        # Validar token primero
        cart_service = CartService(db)
        validation = cart_service.validate_cart_session(token)
        
        if not validation.get("valid"):
            raise HTTPException(
                status_code=400,
                detail=validation.get("message", "Token inválido")
            )
        
        # Obtener productos disponibles
        products = cart_service.get_available_products()
        
        logger.info(f"📦 API: Devolviendo {len(products)} productos para token {token[:8]}...")
        
        return [ProductInfo(**p) for p in products]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ API: Error obteniendo productos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{token}/complete", response_model=CompleteCartResponse)
async def complete_cart(
    token: str,
    request: CompleteCartRequest,
    db: Session = Depends(get_db)
):
    """
    Completa el carrito y crea la orden (webhook desde webapp)
    
    Este endpoint es llamado por la webapp cuando el usuario
    presiona "Confirmar Orden". Crea una orden PENDING con los
    productos seleccionados y notifica al bot para que pida
    la ubicación GPS y método de pago.
    
    **Proceso:**
    1. Valida token (no usado, no expirado)
    2. Crea orden PENDING con productos
    3. Marca sesión como usada
    4. Notifica al bot (webhook interno o queue)
    5. Bot continúa con CheckoutModule (GPS + Pago)
    
    **Request body:**
    ```json
    {
        "products": [
            {"product_id": "id-1", "quantity": 2},
            {"product_id": "id-2", "quantity": 1}
        ],
        "total": 150.00
    }
    ```
    
    **Response:**
    ```json
    {
        "success": true,
        "message": "Orden creada exitosamente",
        "order_id": "order-id-123"
    }
    ```
    """
    try:
        # Validar token
        cart_service = CartService(db)
        validation = cart_service.validate_cart_session(token)
        
        if not validation.get("valid"):
            raise HTTPException(
                status_code=400,
                detail=validation.get("message", "Token inválido")
            )
        
        customer_id = validation["customer_id"]
        
        logger.info(f"🎉 API: Carrito completado por customer {customer_id}")
        logger.info(f"   📦 Productos: {len(request.products)}, Total: ${request.total}")
        
        # 1. Obtener customer
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        
        # 2. Verificar si ya existe una orden PENDING para esta sesión
        session = cart_service.get_cart_session(token)
        existing_order = None
        is_modification = False
        
        if session.order_id:
            existing_order = db.query(Order).filter(
                Order.id == session.order_id,
                Order.status == "pending"
            ).first()
            
            if existing_order:
                is_modification = True
                logger.info(f"🔄 Modificando orden existente: {existing_order.order_number}")
        
        # 3. Crear o actualizar orden
        order_service = OrderService(db)
        
        if is_modification:
            # Eliminar items antiguos y crear nuevos
            for item in existing_order.items:
                db.delete(item)
            db.flush()
            
            # Actualizar items
            total = 0
            for product_data in request.products:
                product = db.query(Product).filter(Product.id == product_data["product_id"]).first()
                if not product:
                    continue
                    
                item = OrderItem(
                    order_id=existing_order.id,
                    product_id=product.id,
                    product_name=product.name,
                    product_sku=product.sku,
                    quantity=product_data["quantity"],
                    unit_price=product.price,
                    subtotal=product.price * product_data["quantity"]
                )
                db.add(item)
                total += item.subtotal
            
            existing_order.total = total
            existing_order.subtotal = total
            existing_order.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing_order)
            
            order = existing_order
            logger.info(f"✅ Orden modificada: {order.order_number}, nuevo total: ${order.total}")
        else:
            # Crear nueva orden
            order = order_service.create_order(
                customer_id=customer_id,
                items=request.products
            )
            
            if not order:
                raise HTTPException(status_code=500, detail="Error creando orden")
            
            logger.info(f"✅ Orden PENDING creada: {order.order_number} (ID: {order.id})")
            
            # Marcar sesión como usada
            cart_service.mark_session_as_used(token, order.id)
        
        # 4. Notificar al bot para activar CheckoutModule
        # Actualizar contexto del usuario para que CheckoutModule se active
        phone = customer.phone
        
        # Crear instancia de ContextManager con la sesión de BD actual
        context_mgr = ContextManager(db)
        
        # Actualizar el contexto del módulo (marcar checkout como iniciado)
        context_mgr.update_module_context(
            phone=phone,
            module_name="CheckoutModule",
            context_updates={
                "start_checkout": False,  # Ya lo iniciamos, no volver a iniciar
                "checkout_order_id": order.id,
                "current_module": "CheckoutModule",
                "conversation_state": "collecting_slots",
                "slots_data": {},  # Inicializar como dict vacío
                "current_slot": "gps_location",  # Primer slot
                "validation_attempts": {}  # Inicializar intentos
            }
        )
        
        logger.info(f"🔔 Contexto actualizado para {phone}: checkout iniciado, order_id={order.id}")
        
        # 5. Enviar mensajes al usuario por WhatsApp (con retry logic)
        try:
            from app.services.webhook_retry_service import webhook_retry_service
            
            waha = WAHAClient()
            chat_id = f"{phone}@c.us"
            
            summary = order_service.format_order_summary(order)
            
            if is_modification:
                # Mensaje para modificación de orden
                initial_message = (
                    f"🔄 *¡Orden Actualizada!*\n\n"
                    f"He actualizado tu orden:\n\n"
                    f"{summary}\n\n"
                    f"Los cambios se han guardado. Tu orden sigue pendiente de pago."
                )
                
                success1, _ = await webhook_retry_service.execute_with_retry(
                    waha.send_text_message,
                    "Notificar modificación de orden",
                    chat_id,
                    initial_message
                )
                
                if success1:
                    logger.info(f"✅ Notificación de modificación enviada a {phone}")
                else:
                    logger.error(f"❌ Falló notificar modificación a {phone}")
                
                # TODO: Notificar al administrador de la modificación
                # - Enviar mensaje al admin indicando que se modificó una orden
                # - Incluir orden_number, productos cambiados, nuevo total
                # - Usar webhook_retry_service para el envío
                # Ejemplo:
                # admin_message = f"🔄 Orden {order.order_number} fue modificada por el usuario\nNuevo total: ${order.total}"
                # await webhook_retry_service.execute_with_retry(waha.send_text_message, ...)
                
                success2 = True  # No pedir GPS de nuevo en modificaciones
            else:
                # Mensaje para orden nueva (con retry)
                initial_message = (
                    f"✅ *¡Orden recibida!*\n\n"
                    f"{summary}\n\n"
                    f"Ahora necesito algunos datos adicionales para completar tu pedido. "
                    f"Empecemos... 📋"
                )
                
                success1, _ = await webhook_retry_service.execute_with_retry(
                    waha.send_text_message,
                    "Enviar mensaje inicial",
                    chat_id,
                    initial_message
                )
                
                if success1:
                    logger.info(f"✅ Mensaje inicial enviado a {phone}")
                else:
                    logger.error(f"❌ Falló enviar mensaje inicial a {phone}")
                
                # Mensaje 2: Verificar si hay historial de entrega
                # Si existe, ofrecer reutilizar. Si no, pedir GPS normalmente
                last_delivery = order_service.get_last_delivery_info(customer_id)

                if last_delivery:
                    # ✅ Tiene historial - Ofrecer reutilizar
                    logger.info(f"📍 Cliente tiene historial de entrega, ofreciendo reutilizar")

                    # Primero enviar la ubicación GPS
                    try:
                        success_location, _ = await webhook_retry_service.execute_with_retry(
                            waha.send_location,
                            "Enviar ubicación GPS previa",
                            chat_id,
                            last_delivery["latitude"],
                            last_delivery["longitude"],
                            "Tu última ubicación de entrega"
                        )

                        if success_location:
                            logger.info(f"✅ Ubicación GPS previa enviada a {phone}")
                        else:
                            logger.error(f"❌ Falló enviar ubicación GPS previa a {phone}")
                    except Exception as e:
                        logger.error(f"❌ Error enviando ubicación GPS previa: {e}")
                        success_location = False

                    # Luego enviar mensaje preguntando si quiere reutilizar
                    reference_text = last_delivery["reference"] if last_delivery["reference"] else "Sin referencia"
                    reuse_prompt = (
                        f"📍 *Esta es tu última dirección de entrega registrada.*\n\n"
                        f"🏠 *Referencia anterior:* {reference_text}\n\n"
                        f"¿Quieres usar esta misma dirección y referencia para esta orden?\n\n"
                        f"Responde *SÍ* para reutilizar, o *NO* para ingresar una nueva dirección."
                    )

                    success2, _ = await webhook_retry_service.execute_with_retry(
                        waha.send_text_message,
                        "Preguntar reutilización de dirección",
                        chat_id,
                        reuse_prompt
                    )

                    if success2:
                        logger.info(f"✅ Prompt de reutilización enviado a {phone}")
                    else:
                        logger.error(f"❌ Falló enviar prompt de reutilización a {phone}")

                    # Actualizar contexto con flag de reutilización y datos previos
                    context_mgr.update_module_context(
                        phone=phone,
                        module_name="CheckoutModule",
                        context_updates={
                            "awaiting_delivery_reuse_confirmation": True,
                            "last_delivery_info": last_delivery,
                            "current_slot": None  # No estamos en un slot específico aún
                        }
                    )
                    logger.info(f"   Contexto actualizado: esperando confirmación de reutilización")

                else:
                    # ❌ No tiene historial - Pedir GPS normalmente
                    logger.info(f"📍 Cliente NO tiene historial de entrega, pidiendo GPS")

                    from app.modules.checkout_module import CheckoutModule
                    checkout_module = CheckoutModule()
                    gps_prompt = checkout_module.SLOTS[0].prompt  # Primer slot es GPS

                    success2, _ = await webhook_retry_service.execute_with_retry(
                        waha.send_text_message,
                        "Enviar prompt GPS",
                        chat_id,
                        gps_prompt
                    )

                    if success2:
                        logger.info(f"✅ Prompt de GPS enviado a {phone}")
                    else:
                        logger.error(f"❌ Falló enviar prompt GPS a {phone}")
                    logger.info(f"   current_slot ya fue seteado a '{checkout_module.SLOTS[0].name}' en el contexto inicial")
            
            # ⚠️ FALLBACK: Si ambos mensajes fallaron después de todos los reintentos
            if not success1 and not success2:
                logger.critical(f"🚨 CRÍTICO: No se pudo comunicar con WAHA después de 4 intentos para orden {order.order_number}")
                logger.critical(f"   Customer: {phone}, Order: {order.id}")
                
                # TODO: Implementar notificación al panel de administrador
                # - Mostrar alerta en dashboard admin
                # - Enviar email/SMS al administrador
                # - Mostrar órdenes "sin notificar" en sección especial
                # Ejemplo:
                # await admin_notification_service.notify_communication_failure(
                #     order_id=order.id,
                #     customer_phone=phone,
                #     error_type="WAHA_UNREACHABLE"
                # )
                
                # TODO: Actualizar estado del bot a "incomunicado"
                # - Agregar tabla bot_status (status: online/offline/degraded/incommunicado)
                # - Actualizar: bot_status.status = "incommunicado"
                # - Guardar timestamp del último fallo
                # - Dashboard muestra estado del bot en tiempo real
                # - Lógica de recuperación automática cuando WAHA vuelve
                # Ejemplo:
                # from app.services.bot_status_service import bot_status_service
                # await bot_status_service.update_status(
                #     status="incommunicado",
                #     reason="Failed to reach WAHA after 4 retries",
                #     affected_orders=[order.id]
                # )
                
                # Por ahora, solo logging crítico
                pass
            
        except Exception as e:
            logger.error(f"⚠️ Error enviando mensajes iniciales: {e}")
            # No fallar el endpoint si no se pudo enviar el mensaje
        
        return CompleteCartResponse(
            success=True,
            message="Orden recibida. Pronto recibirás un mensaje para completar tu pedido.",
            order_id=order.id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ API: Error completando carrito: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{token}/pending-order")
async def get_pending_order(
    token: str,
    db: Session = Depends(get_db)
):
    """Obtiene la orden PENDING asociada a esta sesión si existe"""
    try:
        cart_service = CartService(db)
        session = cart_service.get_cart_session(token)
        
        if not session or not session.order_id:
            return {"has_pending_order": False}
        
        order = db.query(Order).filter(
            Order.id == session.order_id,
            Order.status == "pending"
        ).first()
        
        if not order:
            return {"has_pending_order": False}
        
        return {
            "has_pending_order": True,
            "order": {
                "id": order.id,
                "order_number": order.order_number,
                "total": float(order.total),
                "items": [
                    {
                        "product_id": item.product_id,
                        "product_name": item.product_name,
                        "quantity": item.quantity,
                        "unit_price": float(item.unit_price),
                        "subtotal": float(item.subtotal)
                    }
                    for item in order.items
                ]
            }
        }
    except Exception as e:
        logger.error(f"Error obteniendo orden pending: {e}")
        raise HTTPException(500, "Error obteniendo orden")


@router.get("/{token}/status")
async def check_cart_status(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Verifica el estado actual de una sesión de carrito
    
    Útil para que la webapp verifique periódicamente si
    el carrito fue completado o expiró.
    """
    try:
        cart_service = CartService(db)
        session = cart_service.get_cart_session(token)
        
        if not session:
            return {
                "exists": False,
                "message": "Sesión no encontrada"
            }
        
        return {
            "exists": True,
            "used": session.used,
            "expired": session.is_expired,
            "valid": session.is_valid,
            "order_id": session.order_id,
            "expires_at": session.expires_at.isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ API: Error verificando estado: {e}")
        raise HTTPException(status_code=500, detail=str(e))

