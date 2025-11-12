"""
Aplicación principal FastAPI
"""
import sys
from pathlib import Path
from typing import Dict, List
from contextlib import asynccontextmanager

# Agregar directorio raíz al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from config.settings import settings
from config.logging_config import setup_logging
from loguru import logger
import uvicorn

# Setup logging
logger = setup_logging()

# Importar buffer manager
from app.services.message_buffer import message_buffer_manager

# Importar MessageProcessor
logger.info("🔄 Importando MessageProcessor...")
from app.services.message_processor import MessageProcessor
logger.info("✅ MessageProcessor importado correctamente")

# Crear instancia
message_processor = MessageProcessor()
logger.info("✅ MessageProcessor instanciado")

from app.services.sync_worker import sync_worker
from app.core.module_registry import get_module_registry
from app.modules.create_order_module import CreateOrderModule
from app.modules.check_order_module import CheckOrderModule

async def process_buffered_messages(
    phone: str,
    combined_message: str,
    messages_list: List
):
    """Callback que se llama cuando el buffer está listo"""
    try:
        logger.info(f"🔄 Procesando {len(messages_list)} mensajes de {phone}")
        logger.debug(f"Mensaje combinado: '{combined_message[:100]}...'")
        
        first_message_id = messages_list[0].message_id if messages_list else None
        
        # Encolar en worker síncrono
        sync_worker.enqueue_message(phone, combined_message, first_message_id)
        
        logger.info(f"✓ Mensaje encolado para {phone}")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)

async def process_incoming_message(webhook_data: Dict):
    """Procesa webhooks de WAHA"""
    try:
        payload = webhook_data.get("payload", {})
        message_id = payload.get("id")
        phone_raw = payload.get("from", "")
        from_me = payload.get("fromMe", False)
        message_body = payload.get("body", "")
        message_type = payload.get("type", "chat")
        
        # Log payload completo para mensajes de ubicación (solo en modo TRACE)
        if message_type == "location" or "latitude" in str(payload) or "longitude" in str(payload):
            logger.trace(f"Payload ubicación: {payload}")
        
        if from_me:
            return
        
        if "status@broadcast" in phone_raw:
            return
        
        if "@g.us" in phone_raw:
            return
        
        if "@c.us" not in phone_raw:
            return
        
        phone = phone_raw.replace("@c.us", "")
        
        logger.info(f"📱 Mensaje de {phone}: {message_type}")
        
        # ⚠️ VERIFICACIÓN PRIORITARIA: Revisar si es un mensaje de ubicación ANTES de procesar como texto
        # Verificar en múltiples lugares del payload
        latitude = None
        longitude = None
        
        # 1. Objeto 'location'
        location_obj = payload.get("location", {})
        if isinstance(location_obj, dict):
            latitude = location_obj.get("latitude")
            longitude = location_obj.get("longitude")
        
        # 2. Campos directos
        if latitude is None:
            latitude = payload.get("latitude") or payload.get("lat")
        if longitude is None:
            longitude = payload.get("longitude") or payload.get("lon") or payload.get("lng")
        
        # 3. Desde _data
        if latitude is None or longitude is None:
            location_data = payload.get("_data", {})
            if location_data:
                if latitude is None:
                    latitude = location_data.get("latitude") or location_data.get("lat")
                if longitude is None:
                    longitude = location_data.get("longitude") or location_data.get("lon") or location_data.get("lng")
        
        # Si tiene coordenadas válidas, es un mensaje de ubicación sin importar el tipo
        if latitude is not None and longitude is not None:
            location_string = f"{latitude},{longitude}"
            logger.info(f"📍 Ubicación recibida: {location_string}")
            
            await message_buffer_manager.add_message(
                phone=phone,
                message=location_string,
                message_id=message_id,
                message_type="text"
            )
            return  # ← Salir inmediatamente, no procesar nada más
        
        # Si no hay coordenadas, continuar con el procesamiento normal
        logger.info(f"📝 Contenido: '{message_body[:50]}...'")
        
        if message_type == "chat":
            logger.info(f"✅ Agregando al buffer")
            await message_buffer_manager.add_message(
                phone=phone,
                message=message_body,
                message_id=message_id,
                message_type="text"
            )
            
        elif message_type in ["ptt", "audio"]:
            media_url = payload.get("mediaUrl")
            await message_processor.process_voice_message(
                phone=phone,
                media_url=media_url,
                message_id=message_id
            )
            
        elif message_type == "image":
            media_url = payload.get("mediaUrl")
            caption = payload.get("caption", "")
            
            # Verificar si la imagen contiene datos de ubicación
            # WAHA puede enviar ubicaciones como imágenes con metadata
            latitude = None
            longitude = None
            
            # 1. Intentar extraer del objeto 'location'
            location_obj = payload.get("location", {})
            if isinstance(location_obj, dict):
                latitude = location_obj.get("latitude")
                longitude = location_obj.get("longitude")
            
            # 2. Intentar desde campos directos del payload
            if latitude is None or longitude is None:
                latitude = payload.get("latitude") or payload.get("lat")
                longitude = payload.get("longitude") or payload.get("lon") or payload.get("lng")
            
            # 3. Intentar extraer de _data
            if latitude is None or longitude is None:
                location_data = payload.get("_data", {})
                if location_data:
                    latitude = location_data.get("latitude") or location_data.get("lat")
                    longitude = location_data.get("longitude") or location_data.get("lon") or location_data.get("lng")
            
                # Si tiene coordenadas, es un mensaje de ubicación
                if latitude is not None and longitude is not None:
                    location_string = f"{latitude},{longitude}"
                    logger.info(f"📍 Ubicación (vía imagen): {location_string}")
                    
                    await message_buffer_manager.add_message(
                        phone=phone,
                        message=location_string,
                        message_id=message_id,
                        message_type="text"
                    )
                    return  # ← IMPORTANTE: No procesar el resto de la imagen
            elif caption:
                await message_buffer_manager.add_message(
                    phone=phone,
                    message=caption,
                    message_id=message_id,
                    message_type="text",
                    media_url=media_url
                )
            else:
                await message_processor.process_image_message(
                    phone=phone,
                    media_url=media_url,
                    caption="",
                    message_id=message_id
                )
        
        elif message_type == "location":
            logger.debug(f"Mensaje tipo location detectado")
            
            # Extraer coordenadas GPS del mensaje de ubicación
            latitude = None
            longitude = None
            
            # 1. Intentar extraer del objeto 'location'
            location_obj = payload.get("location", {})
            if isinstance(location_obj, dict):
                latitude = location_obj.get("latitude")
                longitude = location_obj.get("longitude")
                logger.trace(f"Coordenadas desde 'location': {latitude}, {longitude}")
            
            # 2. Intentar desde campos directos del payload
            if latitude is None or longitude is None:
                latitude = payload.get("latitude") or payload.get("lat")
                longitude = payload.get("longitude") or payload.get("lon") or payload.get("lng")
            
            # 3. Intentar extraer de _data
            if latitude is None or longitude is None:
                location_data = payload.get("_data", {})
                if location_data:
                    latitude = location_data.get("latitude") or location_data.get("lat")
                    longitude = location_data.get("longitude") or location_data.get("lon") or location_data.get("lng")
            
            if latitude is not None and longitude is not None:
                # Formatear como string de coordenadas
                location_string = f"{latitude},{longitude}"
                logger.info(f"📍 Ubicación: {location_string}")
                
                # Agregar al buffer como mensaje de texto con las coordenadas
                await message_buffer_manager.add_message(
                    phone=phone,
                    message=location_string,
                    message_id=message_id,
                    message_type="text"
                )
            else:
                logger.warning(f"⚠️ Mensaje de ubicación sin coordenadas válidas")
                logger.trace(f"Payload: {payload}")
    
    except Exception as e:
        logger.error(f"❌ Error procesando webhook: {e}", exc_info=True)


# Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo de vida"""
    logger.info("🚀 Iniciando BotVentasWhatsApp")
    
    # ✅ Inicializar módulos AQUÍ
    logger.info("🔌 Inicializando módulos...")
    registry = get_module_registry()
    
    # ════════════════════════════════════════════════════════════════
    # NUEVO FLUJO: WebApp Cart (en lugar de CreateOrderModule)
    # ════════════════════════════════════════════════════════════════
    # CreateOrderModule DESACTIVADO - Se reemplazó por CartLinkModule
    # El nuevo flujo es: Bot genera link → Usuario usa WebApp → Checkout
    # 
    # create_order_module = CreateOrderModule()
    # registry.register(create_order_module)
    
    # Registrar CartLinkModule (reemplaza a CreateOrderModule para intent: create_order)
    from app.modules.cart_link_module import CartLinkModule
    cart_link_module = CartLinkModule()
    registry.register(cart_link_module)
    logger.info("✅ [Registry] CartLinkModule registrado (intent: create_order)")
    
    # ════════════════════════════════════════════════════════════════
    # Módulos activos normalmente
    # ════════════════════════════════════════════════════════════════
    
    # Registrar CheckOrderModule
    check_order_module = CheckOrderModule()
    registry.register(check_order_module)
    
    # Registrar RemoveFromOrderModule
    from app.modules.remove_from_order_module import RemoveFromOrderModule
    remove_from_order_module = RemoveFromOrderModule()
    registry.register(remove_from_order_module)
    
    # Registrar OfferProductModule
    from app.modules.offer_product_module import OfferProductModule
    offer_product_module = OfferProductModule()
    registry.register(offer_product_module)
    
    # ════════════════════════════════════════════════════════════════
    # CheckoutModule - ACTIVO ✅
    # ════════════════════════════════════════════════════════════════
    # Este módulo maneja GPS + pago después de que la webapp completa el carrito
    # Se activa automáticamente cuando el webhook de la webapp actualiza el contexto
    # con start_checkout=True
    
    from app.modules.checkout_module import CheckoutModule
    checkout_module = CheckoutModule()
    registry.register(checkout_module)
    logger.info("✅ [Registry] CheckoutModule registrado (activado por webhook)")
    
    logger.info("✅ Módulos inicializados")
    
    message_buffer_manager.set_processing_callback(process_buffered_messages)
    logger.info("✓ Buffer Manager configurado")
    
    # Iniciar worker síncrono
    sync_worker.start()
    
    # Iniciar worker de monitoreo de órdenes
    from app.services.order_monitor_worker import order_monitor_worker
    await order_monitor_worker.start()
    logger.info("✓ Order Monitor Worker iniciado")
    
    yield
    
    logger.info("👋 Cerrando aplicación")
    
    # Detener workers
    await order_monitor_worker.stop()
    sync_worker.stop()


# Crear app
app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    version="0.1.0",
    lifespan=lifespan
)

# Configurar CORS para el dashboard y webapp del carrito
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",      # Dashboard admin
        "http://localhost:5174",      # WebApp carrito
        "http://localhost:3000",
        "http://192.168.68.101:5173", # Acceso desde red local
        "http://192.168.68.101:5174", # WebApp carrito desde red local
        "http://192.168.68.102:5174", # WebApp carrito desde tu PC
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Importar y registrar routers del API
from app.api.orders import router as orders_router
from app.api.products import router as products_router
from app.api.cart import router as cart_router

app.include_router(orders_router)
app.include_router(products_router)
app.include_router(cart_router)

# Montar carpeta de archivos estáticos (imágenes de productos)
app.mount("/static", StaticFiles(directory="static"), name="static")

logger.info("✅ FastAPI app creada")


@app.get("/")
async def root():
    return {
        "status": "running",
        "app": settings.app_name,
        "version": "0.1.0"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/webhook/waha")
async def waha_webhook(request: Request, background_tasks: BackgroundTasks):
    """Endpoint webhook WAHA"""
    try:
        data = await request.json()
        event_type = data.get("event")
        
        logger.info(f"📨 Webhook: {event_type}")
        
        payload = data.get("payload", {})
        from_phone = payload.get("from", "")
        body = payload.get("body", "")
        message_type = payload.get("type", "")
        
        # Log detallado para mensajes que no sean de texto
        if message_type and message_type != "chat":
            logger.info(f"🔍 [WEBHOOK] Tipo de mensaje: {message_type}")
            # Log de claves del payload (sin el body si es muy largo)
            payload_keys = {k: v if k != "body" or len(str(v)) < 100 else f"[{len(str(v))} chars]" 
                          for k, v in payload.items()}
            logger.info(f"🔍 [WEBHOOK] Payload keys: {payload_keys}")
        
        if body and from_phone:
            body_preview = body[:100] if len(body) < 100 else f"{body[:100]}..."
            logger.info(f"💬 De {from_phone}: {body_preview}")
        
        background_tasks.add_task(process_incoming_message, data)
        logger.debug(f"✅ Tarea en background")
        
        return {"status": "received"}
        
    except Exception as e:
        logger.error(f"❌ Error en webhook: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    def initialize_modules():
        """Inicializa y registra todos los módulos disponibles"""
        logger.info("🔌 Inicializando módulos...")
        
        registry = get_module_registry()
        
        # Registrar CreateOrderModule
        create_order_module = CreateOrderModule()
        registry.register(create_order_module)
        
        # Registrar CheckOrderModule
        check_order_module = CheckOrderModule()
        registry.register(check_order_module)
        
        logger.info("✅ Módulos inicializados")
    
    logger.info("🚀 Iniciando Bot de Ventas WhatsApp...")
    
    # Inicializar módulos
    initialize_modules()
    
    # Iniciar servidor
    uvicorn.run(app, host="0.0.0.0", port=8000)