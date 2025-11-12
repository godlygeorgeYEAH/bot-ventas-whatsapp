"""
Módulo para crear órdenes - Usa slot-filling para recolectar información
"""
from typing import Dict, Any, Optional
from loguru import logger
from config.database import get_db_context
from config.settings import settings
from app.core.slots import SlotDefinition, SlotType, SlotManager
from app.services.product_service import ProductService
from app.services.order_service import OrderService
from app.modules.multi_product_handler import MultiProductHandler
from app.database.models import Customer


class CreateOrderModule:
    """Módulo para gestionar la creación de órdenes"""
    
    def __init__(self):
        self.name = "CreateOrderModule"
        self.intent = "create_order"
        self.multi_product_handler = MultiProductHandler()
        
        # Definir slots necesarios para crear una orden
        self.slots_schema = {
            "product_name": SlotDefinition(
                name="product_name",
                type=SlotType.TEXT,
                required=True,
                prompt="¿Qué producto te interesa? Tenemos laptops, mouses, teclados, monitores y más.",
                validation_rules={
                    "min_length": 2,
                    "validate_against_db": True  # Validar contra catálogo
                },
                examples=["laptop", "mouse logitech", "teclado mecánico"]
            ),
            "quantity": SlotDefinition(
                name="quantity",
                type=SlotType.NUMBER,
                required=True,
                prompt="¿Cuántas unidades quieres?",
                validation_rules={
                    "min": 1,
                    "max": 100,
                    "only_integers": True,
                    "validate_stock": True  # Validar stock disponible
                },
                examples=["1", "2", "5"]
            ),
            "delivery_location": SlotDefinition(
                name="delivery_location",
                type=SlotType.LOCATION,
                required=True,
                prompt="📍 Por favor comparte tu ubicación GPS desde WhatsApp.\n\n"
                       "👉 Toca el ícono de 📎 (adjuntar) → Ubicación → Enviar ubicación actual",
                validation_rules={},
                examples=["4.7110,-74.0721", "-33.4489,70.6693"],
                auto_extract=False  # NO extraer del mensaje inicial, solo cuando se pida explícitamente
            ),
            "delivery_reference": SlotDefinition(
                name="delivery_reference",
                type=SlotType.TEXT,
                required=True,
                prompt="📝 Por favor proporciona una referencia de tu ubicación.\n\n"
                       "Ejemplos: Casa azul, Edificio Torre Sur Apto 305, Frente al supermercado",
                validation_rules={
                    "min_length": 3,
                    "max_length": 200
                },
                examples=["Casa azul con portón negro", "Edificio Central Apto 504", "Frente al parque"],
                auto_extract=False  # NO extraer del mensaje inicial, solo cuando se pida explícitamente
            ),
            "payment_method": SlotDefinition(
                name="payment_method",
                type=SlotType.CHOICE,
                required=True,
                prompt="¿Cómo prefieres pagar?",
                validation_rules={
                    "choices": ["efectivo", "tarjeta", "transferencia"]
                }
            )
        }
        
        self.slot_manager = SlotManager(self.slots_schema)
    
    def handle(
        self,
        message: str,
        context: Dict[str, Any],
        phone: str
    ) -> Dict[str, Any]:
        """
        Maneja el mensaje del usuario en el contexto de crear orden
        
        Args:
            message: Mensaje del usuario
            context: Contexto de la conversación
            phone: Teléfono del usuario
            
        Returns:
            Dict con respuesta y datos actualizados
        """
        logger.debug(f"🛒 [CreateOrderModule] Procesando: '{message[:30]}...'")
        logger.trace(f"📦 [CreateOrderModule] Contexto: state={context.get('conversation_state')}, "
                    f"slot={context.get('current_slot')}, wait_confirm={context.get('waiting_location_confirmation')}")
        
        # ═══════════════════════════════════════════════════════════
        # ⚡ LIMPIEZA: Si el estado anterior es "failed", limpiar slots y empezar de nuevo
        # ═══════════════════════════════════════════════════════════
        if context.get('conversation_state') == 'failed':
            logger.info(f"🔄 [CreateOrderModule] Estado 'failed' detectado, limpiando slots para reintentar")
            context['slots_data'] = {}
            context['current_slot'] = None
            context['validation_attempts'] = {}
            context['conversation_state'] = 'collecting_slots'
        
        # Obtener estado actual de slots
        current_slots = context.get('slots_data', {})
        current_slot = context.get('current_slot')
        attempts = context.get('validation_attempts', {})
        
        # ═══════════════════════════════════════════════════════════
        # ⚡ VALIDAR: NO PERMITIR CREAR ORDEN SI YA EXISTE UNA CONFIRMADA ACTIVA
        # El usuario debe esperar a que su orden sea entregada o cancelada
        # ═══════════════════════════════════════════════════════════
        if (not current_slots or len(current_slots) == 0) and not context.get('adding_to_existing_order'):
            with get_db_context() as db:
                from app.database.models import OrderStatus
                order_service = OrderService(db)
                customer = db.query(Customer).filter(Customer.phone == phone).first()
                
                if customer:
                    # Buscar orden confirmada reciente (últimas 72 horas)
                    recent_order = order_service.get_recent_confirmed_order(customer.id, max_hours=72)
                    
                    if recent_order:
                        logger.info(f"🔍 [CreateOrderModule] Orden confirmada encontrada: {recent_order.order_number} (Estado: {recent_order.status})")
                        
                        # ⚠️ VALIDACIÓN DE NEGOCIO: Si hay orden activa, automáticamente agregar a ella
                        if recent_order.status in ['confirmed', 'pending', 'shipped']:
                            logger.info(f"✅ [CreateOrderModule] Orden activa detectada, cambiando a modo 'agregar a orden existente'")
                            # Configurar contexto para agregar a orden existente
                            context['adding_to_existing_order'] = True
                            context['existing_order_id'] = recent_order.id
                            context['existing_order_number'] = recent_order.order_number
                            # Continuar normalmente con el flujo de agregar productos
                        else:
                            # Si está entregada o cancelada, permitir nueva orden normalmente
                            logger.info(f"✅ [CreateOrderModule] Orden anterior finalizada ({recent_order.status}), permitiendo nueva orden")
                            # NO configurar adding_to_existing_order, es una orden NUEVA
        
        # ⚡ RESETEAR FLAGS: Si es el inicio de una nueva orden O estado inconsistente
        # Limpiar los flags de ubicación Y multi-producto para permitir un inicio limpio
        should_reset_flags = (
            len(current_slots) == 0 or  # Primera ejecución, sin slots
            (len(current_slots) == 1 and 'product_name' in current_slots and current_slot == 'product_name') or  # Primer slot siendo procesado
            (context.get('previous_location_offered') and context.get('offered_location') is None and not current_slots.get('delivery_location'))  # Estado inconsistente de conversación previa
        )
        
        # Si es inicio de nueva orden, limpiar datos de multi-producto anteriores INMEDIATAMENTE
        if (current_slot == 'product_name' or current_slot is None) and len(current_slots) == 0:
            if context.get('order_items') or context.get('collecting_product_quantities'):
                logger.info(f"🔄 [CreateOrderModule] Limpiando datos de multi-producto de conversación anterior")
                # Limpiar AHORA para que el pre-intercept funcione correctamente
                context['order_items'] = None
                context['collecting_product_quantities'] = False
                # Marcar para persistir en el return
                should_reset_flags = True
        
        if should_reset_flags and context.get('previous_location_offered'):
            logger.info(f"🔄 [CreateOrderModule] Nueva orden o estado inconsistente detectado, reseteando flags de ubicación")
            # No modificamos el contexto directamente aquí, lo haremos al devolver el resultado
        
        # Si estamos esperando confirmación de ubicación previa
        if context.get('waiting_location_confirmation'):
            logger.info(f"✅ [CreateOrderModule] DETECTADO: Esperando confirmación de ubicación")
            return self._handle_location_confirmation(message, context, phone)
        
        # ═══════════════════════════════════════════════════════════
        # ⚡ PRE-INTERCEPTAR: Detectar múltiples productos ANTES del slot manager
        # Si estamos pidiendo product_name y el mensaje contiene separadores (comas o "y"), procesarlo como multi-producto
        # ═══════════════════════════════════════════════════════════
        has_separator = (',' in message or ' y ' in message.lower())
        
        logger.info(f"🔍 [CreateOrderModule] Verificando pre-intercept: slot={current_slot}, "
                    f"tiene_separador={has_separator}, order_items={context.get('order_items') is not None}, "
                    f"collecting={context.get('collecting_product_quantities')}")
        
        if ((current_slot == 'product_name' or current_slot is None) and 
            has_separator and 
            not context.get('order_items') and
            not context.get('collecting_product_quantities')):
            
            logger.info(f"🎯 [CreateOrderModule] Detectadas comas en mensaje, procesando como multi-producto")
            
            with get_db_context() as db:
                # Parsear productos CON cantidades usando LLM
                products_with_qty = self.multi_product_handler.parse_products_with_quantities(message)
                
                # Solo procesar como multi-producto si hay al menos 2 productos después de parsear
                if len(products_with_qty) >= 2:
                    logger.info(f"🎯 [CreateOrderModule] Múltiples productos detectados: {len(products_with_qty)}")
                    
                    # Validar todos los productos
                    valid_products, invalid_products = self.multi_product_handler.validate_all_products(
                        products_with_qty, db
                    )
                    
                    # Si hay productos inválidos, informar al usuario
                    if invalid_products:
                        error_msg = f"❌ No pude encontrar estos productos: {', '.join(invalid_products)}\n\n"
                        error_msg += "Por favor verifica los nombres e intenta de nuevo."
                        
                        # Incrementar intentos de validación
                        new_attempts = attempts.copy()
                        new_attempts['product_name'] = new_attempts.get('product_name', 0) + 1
                        
                        return {
                            "response": error_msg,
                            "context_updates": {
                                "current_module": "CreateOrderModule",
                                "slots_data": current_slots,
                                "current_slot": "product_name",
                                "validation_attempts": new_attempts,
                                "conversation_state": "collecting_slots"
                            }
                        }
                    
                    # Todos los productos son válidos
                    # Inicializar order_items
                    order_items = self.multi_product_handler.initialize_order_items(valid_products)
                    
                    # Verificar si TODOS los productos ya tienen cantidad
                    if self.multi_product_handler.all_quantities_filled({'order_items': order_items}):
                        logger.info(f"✅ [CreateOrderModule] Todas las cantidades detectadas automáticamente")
                        
                        # Validar stock para cada producto
                        stock_errors = []
                        for item in order_items:
                            if item['quantity'] > item['stock']:
                                stock_errors.append(
                                    f"• {item['product_name']}: Solo tenemos {item['stock']} unidades (pediste {item['quantity']})"
                                )
                        
                        if stock_errors:
                            error_msg = "❌ No hay suficiente stock:\n\n" + "\n".join(stock_errors)
                            error_msg += "\n\nPor favor ajusta las cantidades."
                            
                            return {
                                "response": error_msg,
                                "context_updates": {
                                    "current_module": "CreateOrderModule",
                                    "slots_data": current_slots,
                                    "current_slot": "product_name",
                                    "validation_attempts": attempts,
                                    "conversation_state": "collecting_slots"
                                }
                            }
                        
                        # Generar resumen y continuar con delivery_location
                        summary = self.multi_product_handler.get_order_summary({'order_items': order_items})
                        
                        # Marcar slots como llenados
                        cleaned_slots = {k: v for k, v in current_slots.items() 
                                       if k not in ['product_name', 'quantity']}
                        cleaned_slots['product_name'] = "multi_product"
                        cleaned_slots['quantity'] = len(order_items)
                        
                        return {
                            "response": summary + "\n\n" + "📍 Por favor comparte tu ubicación GPS desde WhatsApp.\n\n"
                                       "👉 Toca el ícono de 📎 (adjuntar) → Ubicación → Enviar ubicación actual",
                            "context_updates": {
                                "current_module": "CreateOrderModule",
                                "order_items": order_items,
                                "collecting_product_quantities": False,
                                "slots_data": cleaned_slots,
                                "current_slot": "delivery_location",
                                "validation_attempts": attempts,
                                "conversation_state": "collecting_slots"
                            }
                        }
                    
                    # Si hay cantidades faltantes, pedir la primera
                    first_product_prompt = self.multi_product_handler.get_next_product_prompt(
                        {'order_items': order_items}
                    )
                    
                    logger.info(f"✅ [CreateOrderModule] Iniciando recolección de cantidades faltantes")
                    
                    return {
                        "response": first_product_prompt,
                        "context_updates": {
                            "current_module": "CreateOrderModule",
                            "order_items": order_items,
                            "collecting_product_quantities": True,
                            "slots_data": current_slots,
                            "current_slot": "quantity",
                            "validation_attempts": attempts,
                            "conversation_state": "collecting_slots"
                        }
                    }
        
        # ═══════════════════════════════════════════════════════════
        # ⚡ SI ESTAMOS AGREGANDO A ORDEN EXISTENTE: Pre-llenar ubicación y pago
        # La orden existente ya tiene estos datos, no hay que pedirlos de nuevo
        # ═══════════════════════════════════════════════════════════
        if context.get('adding_to_existing_order'):
            logger.info(f"➕ [CreateOrderModule] Agregando a orden existente - omitiendo ubicación y pago")
            
            # Pre-llenar slots de ubicación y pago si no están ya llenados
            if 'delivery_location' not in current_slots:
                current_slots['delivery_location'] = "existing_order"  # Placeholder
                logger.info(f"   ✅ delivery_location marcado como completado (orden existente)")
            
            if 'delivery_reference' not in current_slots:
                current_slots['delivery_reference'] = "existing_order"  # Placeholder
                logger.info(f"   ✅ delivery_reference marcado como completado (orden existente)")
            
            if 'payment_method' not in current_slots:
                current_slots['payment_method'] = "existing_order"  # Placeholder
                logger.info(f"   ✅ payment_method marcado como completado (orden existente)")
        
        # Preparar contexto limpio para SlotManager (solo campos relevantes)
        # Excluir campos de conversación que ya están en la BD
        slot_context = {k: v for k, v in context.items() 
                       if k not in {'current_module', 'current_intent', 'conversation_state', 
                                   'current_slot', 'slots_data', 'validation_attempts'}}
        
        # Procesar mensaje con slot manager (para productos únicos)
        result = self.slot_manager.process_message(
            message=message,
            current_slots=current_slots,
            current_slot_name=current_slot,
            attempts=attempts,
            context=slot_context  # Pasar solo contexto relevante (sin campos de BD)
        )
        
        # ═══════════════════════════════════════════════════════════
        # ⚡ INTERCEPTAR: Si estamos recolectando cantidades de productos individuales
        # ═══════════════════════════════════════════════════════════
        if context.get('collecting_product_quantities'):
            logger.info(f"📊 [CreateOrderModule] Procesando cantidad para producto individual")
            
            # Extraer la cantidad del mensaje
            try:
                quantity = int(message.strip())
                
                # Obtener el producto actual primero para mensajes personalizados
                current_product = self.multi_product_handler.get_current_product_being_processed(context)
                product_name = current_product.get('product_name', 'este producto') if current_product else 'este producto'
                
                if quantity <= 0:
                    return {
                        "response": f"❌ La cantidad debe ser mayor a 0. ¿Cuántas unidades de *{product_name}* quieres?",
                        "context_updates": {
                            "current_module": "CreateOrderModule",
                            "order_items": context.get('order_items'),
                            "collecting_product_quantities": True,
                            "slots_data": result.filled_slots,
                            "current_slot": "quantity",
                            "validation_attempts": result.attempts,
                            "conversation_state": "collecting_slots"
                        }
                    }
                
                if not current_product:
                    logger.error("❌ [CreateOrderModule] No se encontró producto actual")
                    return {
                        "response": "❌ Error interno. Empecemos de nuevo.",
                        "context_updates": {
                            "current_module": "CreateOrderModule",
                            "order_items": [],
                            "collecting_product_quantities": False,
                            "slots_data": {},
                            "current_slot": None,
                            "validation_attempts": {},
                            "conversation_state": "collecting_slots"
                        }
                    }
                
                # Validar stock
                if quantity > current_product['stock']:
                    return {
                        "response": f"❌ Solo tenemos {current_product['stock']} unidades de *{product_name}* disponibles.\n\n"
                                  f"¿Cuántas unidades quieres?",
                        "context_updates": {
                            "current_module": "CreateOrderModule",
                            "order_items": context.get('order_items'),
                            "collecting_product_quantities": True,
                            "slots_data": result.filled_slots,
                            "current_slot": "quantity",
                            "validation_attempts": result.attempts,
                            "conversation_state": "collecting_slots"
                        }
                    }
                
                # Asignar cantidad al producto actual
                updated_context = self.multi_product_handler.set_quantity_for_current_product(
                    context, quantity
                )
                
                # Verificar si terminamos de recolectar todas las cantidades
                if self.multi_product_handler.all_quantities_filled(updated_context):
                    logger.info(f"✅ [CreateOrderModule] Todas las cantidades recolectadas")
                    
                    # Generar resumen
                    summary = self.multi_product_handler.get_order_summary(updated_context)
                    
                    # Ahora remover 'quantity' y 'product_name' de filled_slots
                    # porque los productos ya están en order_items
                    cleaned_slots = {k: v for k, v in result.filled_slots.items() 
                                   if k not in ['product_name', 'quantity']}
                    
                    # Marcar quantity como llenado en filled_slots para que el SlotManager continúe
                    cleaned_slots['product_name'] = "multi_product"  # Placeholder
                    cleaned_slots['quantity'] = len(updated_context['order_items'])  # Total de productos
                    
                    return {
                        "response": summary + "\n\n" + "📍 Por favor comparte tu ubicación GPS desde WhatsApp.\n\n"
                                   "👉 Toca el ícono de 📎 (adjuntar) → Ubicación → Enviar ubicación actual",
                        "context_updates": {
                            "current_module": "CreateOrderModule",
                            "order_items": updated_context['order_items'],
                            "collecting_product_quantities": False,
                            "slots_data": cleaned_slots,
                            "current_slot": "delivery_location",
                            "validation_attempts": result.attempts,
                            "conversation_state": "collecting_slots"
                        }
                    }
                else:
                    # Pedir cantidad del siguiente producto
                    next_prompt = self.multi_product_handler.get_next_product_prompt(updated_context)
                    
                    return {
                        "response": next_prompt,
                        "context_updates": {
                            "current_module": "CreateOrderModule",
                            "order_items": updated_context['order_items'],
                            "collecting_product_quantities": True,
                            "slots_data": result.filled_slots,
                            "current_slot": "quantity",
                            "validation_attempts": result.attempts,
                            "conversation_state": "collecting_slots"
                        }
                    }
            
            except ValueError:
                # No es un número válido - obtener nombre del producto para mensaje personalizado
                current_product = self.multi_product_handler.get_current_product_being_processed(context)
                product_name = current_product.get('product_name', 'este producto') if current_product else 'este producto'
                
                return {
                    "response": f"❌ Por favor ingresa un número válido. ¿Cuántas unidades de *{product_name}* quieres?",
                    "context_updates": {
                        "current_module": "CreateOrderModule",
                        "order_items": context.get('order_items'),
                        "collecting_product_quantities": True,
                        "slots_data": result.filled_slots,
                        "current_slot": "quantity",
                        "validation_attempts": result.attempts,
                        "conversation_state": "collecting_slots"
                    }
                }
        
        # ⚡ INTERCEPTAR: Si el siguiente slot es delivery_location y no está llenado
        # Verificar si hay ubicación previa ANTES de mostrar el prompt
        # Nota: Si should_reset_flags es True, tratamos previous_location_offered como False
        previous_location_was_offered = context.get('previous_location_offered', False) and not should_reset_flags
        
        if (result.current_slot == 'delivery_location' and 
            not result.filled_slots.get('delivery_location') and
            not previous_location_was_offered and
            not context.get('waiting_location_confirmation', False)):  # ← No ofrecer si ya estamos esperando
            
            logger.info("🔍 [CreateOrderModule] Verificando ubicación previa antes de pedir una nueva...")
            
            # Intentar ofrecer ubicación previa
            location_offer_result = self._offer_previous_location(phone, context)
            if location_offer_result:
                # Mantener el estado actual de slots llenados
                location_offer_result['context_updates']['slots_data'] = result.filled_slots
                location_offer_result['context_updates']['current_slot'] = result.current_slot
                location_offer_result['context_updates']['validation_attempts'] = result.attempts
                return location_offer_result
        
        # Preparar respuesta
        # Preparar context_updates filtrando campos que no deben sobrescribirse
        context_updates = {
                "current_module": "CreateOrderModule",  # ⚠️ CRÍTICO: Preservar módulo activo
                "slots_data": result.filled_slots,
                "current_slot": result.current_slot,
                "validation_attempts": result.attempts,
                "conversation_state": "collecting_slots"
            }
        
        # Agregar contexto adicional del slot manager (sugerencias, etc.)
        # PERO filtrar campos que ya se manejan en la conversación
        excluded_fields = {'current_slot', 'slots_data', 'validation_attempts', 'conversation_state', 'current_module', 'current_intent'}
        for key, value in result.context.items():
            if key not in excluded_fields:
                context_updates[key] = value
        
        # ⚡ IMPORTANTE: Preservar flags de orden existente si están configurados
        if context.get('adding_to_existing_order'):
            context_updates['adding_to_existing_order'] = context['adding_to_existing_order']
            context_updates['existing_order_id'] = context.get('existing_order_id')
            context_updates['existing_order_number'] = context.get('existing_order_number')
        
        response_data = {
            "response": "",
            "context_updates": context_updates
        }
        
        # ⚡ RESETEAR FLAGS de ubicación Y multi-producto si es una nueva orden o estado inconsistente
        if should_reset_flags:
            logger.info(f"🔄 [CreateOrderModule] Reseteando flags de ubicación y multi-producto para nueva orden")
            response_data["context_updates"]["previous_location_offered"] = False
            response_data["context_updates"]["waiting_location_confirmation"] = False
            response_data["context_updates"]["offered_location"] = None
            response_data["context_updates"]["order_items"] = None
            response_data["context_updates"]["collecting_product_quantities"] = False
        
        # Si slot filling completado, crear la orden
        if result.completed:
            logger.info("✅ [CreateOrderModule] Todos los slots llenados, creando orden...")
            
            order_result = self._create_order(
                slots_data=result.filled_slots,
                phone=phone,
                context=context
            )
            
            if order_result["success"]:
                # Limpiar flags de orden existente después de agregar exitosamente
                response_data["context_updates"]["adding_to_existing_order"] = None
                response_data["context_updates"]["existing_order_id"] = None
                response_data["context_updates"]["existing_order_number"] = None
                
                # Verificar si se hizo un ofrecimiento
                if order_result.get("offer_made"):
                    # Se hizo ofrecimiento, el mensaje ya fue enviado por make_offer
                    logger.info("  🎁 Ofrecimiento enviado, esperando respuesta del usuario...")
                    
                    # Aplicar context_updates del ofrecimiento
                    if "context_updates" in order_result:
                        response_data["context_updates"].update(order_result["context_updates"])
                    
                    # NO enviar mensaje adicional (ya se envió el ofrecimiento)
                    response_data["response"] = None
                    response_data["context_updates"]["order_id"] = order_result.get("order_id")
                else:
                    # Sin ofrecimiento, flujo normal
                    response_data["response"] = order_result["message"]
                    response_data["context_updates"]["conversation_state"] = "completed"
                    response_data["context_updates"]["order_id"] = order_result.get("order_id")
            else:
                response_data["response"] = f"❌ {order_result['message']}\n\n¿Quieres intentar de nuevo?"
                response_data["context_updates"]["conversation_state"] = "failed"
        else:
            # Continuar pidiendo slots
            response_data["response"] = result.next_prompt
        
        return response_data
    
    def _create_order(
        self,
        slots_data: Dict[str, Any],
        phone: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Crea la orden usando los slots llenados O agrega items a una orden existente
        
        Args:
            slots_data: Datos de los slots
            phone: Teléfono del usuario
            context: Contexto de la conversación (opcional, para order_items y adding_to_existing_order)
            
        Returns:
            Dict con success, message, order_id
        """
        try:
            with get_db_context() as db:
                product_service = ProductService(db)
                order_service = OrderService(db)
                
                # ═══════════════════════════════════════════════════════════
                # CASO ESPECIAL: AGREGAR A ORDEN EXISTENTE
                # ═══════════════════════════════════════════════════════════
                if context and context.get('adding_to_existing_order'):
                    existing_order_id = context.get('existing_order_id')
                    existing_order_number = context.get('existing_order_number')
                    
                    if not existing_order_id:
                        return {
                            "success": False,
                            "message": "❌ Error: No se encontró la orden a actualizar."
                        }
                    
                    logger.info(f"➕ [CreateOrderModule] Agregando productos a orden existente: {existing_order_number}")
                    
                    # Construir lista de items a agregar
                    items_to_add = []
                    
                    if context.get('order_items'):
                        # Multi-producto
                        for item in context['order_items']:
                            items_to_add.append({
                                "product_id": item['product_id'],
                                "quantity": item['quantity']
                            })
                    else:
                        # Producto único
                        product_name = slots_data.get("product_name")
                        product = product_service.get_product_by_name_fuzzy(product_name)
                        
                        if not product:
                            return {
                                "success": False,
                                "message": f"No encontramos el producto '{product_name}' en nuestro catálogo."
                            }
                        
                        quantity = int(slots_data.get("quantity"))
                        
                        if not product_service.check_stock(product.id, quantity):
                            return {
                                "success": False,
                                "message": f"Lo siento, solo tenemos {product.stock} unidades de {product.name} disponibles."
                            }
                        
                        items_to_add.append({
                            "product_id": product.id,
                            "quantity": quantity
                        })
                    
                    # Agregar items a la orden existente
                    try:
                        updated_order = order_service.add_items_to_order(existing_order_id, items_to_add)
                        
                        summary = order_service.format_order_summary(updated_order)
                        
                        return {
                            "success": True,
                            "message": f"➕ ¡Productos agregados automáticamente a tu orden existente *{existing_order_number}*!\n\n{summary}",
                            "order_id": updated_order.id
                        }
                        
                    except ValueError as e:
                        return {
                            "success": False,
                            "message": f"❌ {str(e)}"
                        }
                
                # ═══════════════════════════════════════════════════════════
                # DETERMINAR SI ES ORDEN MULTI-PRODUCTO O SINGLE-PRODUCTO
                # ═══════════════════════════════════════════════════════════
                order_items_list = []
                
                if context and context.get('order_items'):
                    # CASO 1: Múltiples productos (desde order_items)
                    logger.info(f"🛒 [CreateOrderModule] Creando orden con múltiples productos")
                    
                    for item in context['order_items']:
                        order_items_list.append({
                            "product_id": item['product_id'],
                            "quantity": item['quantity']
                        })
                
                else:
                    # CASO 2: Producto único (desde slots)
                    logger.info(f"🛒 [CreateOrderModule] Creando orden con producto único")
                    
                    # 1. Buscar producto
                    product_name = slots_data.get("product_name")
                    product = product_service.get_product_by_name_fuzzy(product_name)
                    
                    if not product:
                        return {
                            "success": False,
                            "message": f"No encontramos el producto '{product_name}' en nuestro catálogo."
                        }
                    
                    # 2. Verificar stock
                    quantity = int(slots_data.get("quantity"))
                    if not product_service.check_stock(product.id, quantity):
                        return {
                            "success": False,
                            "message": f"Lo siento, solo tenemos {product.stock} unidades de {product.name} disponibles."
                        }
                    
                    # 3. Agregar a la lista de items
                    order_items_list.append({
                        "product_id": product.id,
                        "quantity": quantity
                    })
                
                # 3. Obtener o crear cliente
                from app.database.models import Customer
                customer = db.query(Customer).filter(Customer.phone == phone).first()
                
                if not customer:
                    customer = Customer(
                        phone=phone,
                        name="Cliente",
                        total_messages=0
                    )
                    db.add(customer)
                    db.commit()
                    db.refresh(customer)
                
                # 4. Extraer coordenadas GPS
                location_data = slots_data.get("delivery_location", "")
                latitude, longitude = None, None
                
                if location_data and ',' in location_data:
                    try:
                        lat_str, lon_str = location_data.split(',')
                        latitude = float(lat_str.strip())
                        longitude = float(lon_str.strip())
                        logger.info(f"📍 Coordenadas extraídas: {latitude}, {longitude}")
                    except Exception as e:
                        logger.error(f"❌ Error parseando coordenadas: {e}")
                
                # 5. Crear orden con coordenadas GPS y referencia
                order = order_service.create_order(
                    customer_id=customer.id,
                    items=order_items_list,  # Usa la lista de items (single o multi)
                    delivery_address=f"GPS: {latitude}, {longitude}" if latitude and longitude else "Ubicación GPS",
                    delivery_latitude=latitude,
                    delivery_longitude=longitude,
                    delivery_reference=slots_data.get("delivery_reference"),
                    payment_method=slots_data.get("payment_method"),
                    shipping_cost=0.0,  # Gratis por ahora
                    tax_rate=0.19  # 19% IVA
                )
                
                # 6. PUNTO DE OFRECIMIENTO: Verificar si hacer ofrecimiento antes de confirmar
                if settings.enable_product_offers and settings.offer_after_order:
                    from app.services.offer_service import OfferService
                    from app.modules.offer_product_module import make_offer
                    
                    logger.info(f"🎁 [CreateOrderModule] Verificando si hacer ofrecimiento...")
                    
                    # Seleccionar producto para ofrecer
                    offer_service = OfferService(db)
                    product_to_offer = offer_service.select_product_to_offer(
                        customer_id=customer.id,
                        current_order_id=order.id
                    )
                    
                    if product_to_offer:
                        # Hay un producto para ofrecer
                        logger.info(f"  ✅ Producto seleccionado: {product_to_offer['product_name']}")
                        
                        # Hacer el ofrecimiento (envía mensaje + imagen)
                        context_updates = make_offer(
                            phone=phone,
                            product=product_to_offer,
                            pending_order_id=order.id
                        )
                        
                        # NO confirmar la orden todavía - OfferProductModule la confirmará
                        return {
                            "success": True,
                            "message": None,  # Mensaje ya enviado por make_offer
                            "order_id": order.id,
                            "offer_made": True,
                            "context_updates": context_updates
                        }
                    else:
                        logger.info(f"  ℹ️ No hay productos disponibles para ofrecer")
                
                # 7. Si no hay ofrecimiento, confirmar orden normalmente
                order = order_service.confirm_order(order.id)
                
                # 8. Formatear respuesta
                summary = order_service.format_order_summary(order)
                
                return {
                    "success": True,
                    "message": f"✅ ¡Orden creada exitosamente!\n\n{summary}",
                    "order_id": order.id
                }
                
        except Exception as e:
            logger.error(f"❌ [CreateOrderModule] Error creando orden: {e}")
            return {
                "success": False,
                "message": "Ocurrió un error al crear tu orden. Por favor intenta de nuevo."
            }
    
    def _offer_previous_location(self, phone: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Detecta si el cliente tiene una ubicación previa y la ofrece
        
        Returns:
            Dict con respuesta o None si no hay ubicación previa
        """
        try:
            from app.database.models import Customer
            
            with get_db_context() as db:
                order_service = OrderService(db)
                
                # Buscar cliente
                customer = db.query(Customer).filter(Customer.phone == phone).first()
                
                if not customer:
                    logger.info(f"📍 [CreateOrderModule] Cliente {phone} no existe aún")
                    return None
                
                # Obtener última ubicación y referencia
                last_location = order_service.get_customer_last_location(customer.id)
                
                if not last_location:
                    logger.info(f"📍 [CreateOrderModule] No hay ubicación previa para {phone}")
                    return None
                
                latitude, longitude, reference = last_location
                
                logger.info(f"📍 [CreateOrderModule] Ubicación previa: {latitude}, {longitude}")
                if reference:
                    logger.info(f"   Referencia: {reference}")
                
                # Enviar la ubicación por WhatsApp (usando sync worker para evitar problemas de asyncio)
                from app.services.sync_worker import sync_worker
                from app.clients.waha_client import WAHAClient
                import asyncio
                
                # Enviar ubicación
                try:
                    waha = WAHAClient()
                    # Ejecutar de forma síncrona
                    loop = asyncio.new_event_loop()
                    loop.run_until_complete(
                        waha.send_location(phone, latitude, longitude, "Última ubicación usada")
                    )
                    loop.close()
                    logger.debug(f"✅ [CreateOrderModule] Ubicación enviada")
                except Exception as e:
                    logger.error(f"❌ Error enviando ubicación: {e}")
                
                # Construir mensaje con referencia si existe
                response_message = "📍 Te envié tu última ubicación de entrega."
                if reference:
                    response_message += f"\n📝 Referencia: *{reference}*"
                response_message += "\n\n¿Deseas usar la misma ubicación?\n\n"
                response_message += "Responde *SÍ* para usar esta ubicación o *NO* para enviar una nueva."
                
                # Devolver respuesta pidiendo confirmación
                context_updates = {
                    "current_module": "CreateOrderModule",  # ⚠️ CRÍTICO: Preservar módulo activo
                    "previous_location_offered": True,
                    "offered_location": f"{latitude},{longitude}",
                    "offered_reference": reference,
                    "waiting_location_confirmation": True,
                    "conversation_state": "collecting_slots"
                }
                
                logger.debug(f"📤 [CreateOrderModule] Pidiendo confirmación de ubicación")
                
                return {
                    "response": response_message,
                    "context_updates": context_updates
                }
                
        except Exception as e:
            logger.error(f"❌ [CreateOrderModule] Error ofreciendo ubicación previa: {e}")
            return None
    
    def _handle_location_confirmation(
        self, 
        message: str, 
        context: Dict[str, Any], 
        phone: str
    ) -> Dict[str, Any]:
        """
        Maneja la confirmación del usuario sobre usar la ubicación previa
        
        Args:
            message: Mensaje del usuario (sí/no)
            context: Contexto de la conversación
            phone: Teléfono del usuario
            
        Returns:
            Dict con respuesta y actualizaciones de contexto
        """
        message_lower = message.lower().strip()
        
        # Respuestas afirmativas
        if any(word in message_lower for word in ['si', 'sí', 'yes', 'ok', 'vale', 'claro', 'confirmo']):
            logger.info(f"✅ [CreateOrderModule] Usuario confirmó ubicación previa")
            
            # Obtener la ubicación y referencia ofrecidas
            offered_location = context.get('offered_location')
            offered_reference = context.get('offered_reference')
            logger.debug(f"📍 [CreateOrderModule] Usando: {offered_location}")
            if offered_reference:
                logger.debug(f"   Referencia: {offered_reference}")
            
            # Preparar contexto limpio para SlotManager
            slot_context = {k: v for k, v in context.items() 
                           if k not in {'current_module', 'current_intent', 'conversation_state', 
                                       'current_slot', 'slots_data', 'validation_attempts'}}
            
            # Procesar la ubicación GPS
            result = self.slot_manager.process_message(
                message=offered_location,
                current_slots=context.get('slots_data', {}),
                current_slot_name='delivery_location',
                attempts=context.get('validation_attempts', {}),
                context=slot_context
            )
            
            # Si hay referencia, también llenar ese slot automáticamente
            if offered_reference and result.current_slot == 'delivery_reference':
                logger.debug(f"📝 [CreateOrderModule] Procesando referencia automáticamente")
                result = self.slot_manager.process_message(
                    message=offered_reference,
                    current_slots=result.filled_slots,
                    current_slot_name='delivery_reference',
                    attempts=result.attempts,
                    context=result.context  # Ya está limpio del paso anterior
                )
            
            logger.debug(f"➡️ [CreateOrderModule] Siguiente slot: {result.current_slot}")
            
            context_updates = {
                "current_module": "CreateOrderModule",  # ⚠️ CRÍTICO: Preservar módulo activo
                "slots_data": result.filled_slots,
                "current_slot": result.current_slot,
                "validation_attempts": result.attempts,
                "waiting_location_confirmation": False,
                "previous_location_offered": True,
                "offered_location": None,
                "offered_reference": None,
                "conversation_state": "collecting_slots"
            }
            
            return {
                "response": result.next_prompt if not result.completed else "",
                "context_updates": context_updates
            }
        
        # Respuestas negativas
        elif any(word in message_lower for word in ['no', 'nop', 'nope']):
            logger.info(f"❌ [CreateOrderModule] Usuario rechazó ubicación previa, solicitando nueva")
            
            return {
                "response": "📍 Perfecto. Por favor comparte tu nueva ubicación GPS desde WhatsApp.\n\n"
                           "👉 Toca el ícono de 📎 (adjuntar) → Ubicación → Enviar ubicación actual",
                "context_updates": {
                    "current_module": "CreateOrderModule",  # ⚠️ CRÍTICO: Preservar módulo activo
                    "waiting_location_confirmation": False,
                    "previous_location_offered": True,  # ← Evitar re-ofrecimiento
                    "offered_location": None,  # ← Limpiar ubicación ofrecida
                    "conversation_state": "collecting_slots"
                }
            }
        
        # Respuesta no clara
        else:
            logger.warning(f"⚠️ [CreateOrderModule] Respuesta no clara: {message}")
            
            return {
                "response": "Por favor responde *SÍ* para usar la ubicación anterior o *NO* para enviar una nueva.",
                "context_updates": {
                    "current_module": "CreateOrderModule",  # ⚠️ CRÍTICO: Preservar módulo activo
                    "waiting_location_confirmation": True,
                    "conversation_state": "collecting_slots"
                }
            }
    
    def can_handle(self, intent: str, context: Dict[str, Any]) -> bool:
        """
        Verifica si este módulo puede manejar la intención
        
        Args:
            intent: Intención detectada
            context: Contexto de la conversación
            
        Returns:
            True si puede manejar
        """
        # Puede manejar si:
        # 1. El intent es create_order
        # 2. O si ya está en proceso de recolectar slots
        return (
            intent == self.intent or
            context.get('current_module') == self.name or
            context.get('conversation_state') == 'collecting_slots'
        )