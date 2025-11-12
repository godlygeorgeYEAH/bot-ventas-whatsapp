"""
Validador de Slots - Valida valores extraídos
"""
from typing import Any, Dict, Tuple, Optional
from loguru import logger
from .slot_definition import SlotType


class SlotValidator:
    """Valida valores de slots según reglas definidas"""
    
    def validate(
        self,
        value: Any,
        slot_type: SlotType,
        validation_rules: Dict[str, Any],
        context: Dict = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Valida un valor según tipo y reglas
        
        Args:
            value: Valor a validar
            slot_type: Tipo de slot
            validation_rules: Reglas de validación
            context: Contexto adicional
            
        Returns:
            Tuple (es_válido, mensaje_error)
        """
        if value is None:
            return False, "Valor no proporcionado"
        
        validators = {
            SlotType.TEXT: self._validate_text,
            SlotType.NUMBER: self._validate_number,
            SlotType.CHOICE: self._validate_choice,
            SlotType.BOOLEAN: self._validate_boolean,
            SlotType.EMAIL: self._validate_email,
            SlotType.PHONE: self._validate_phone,
            SlotType.ADDRESS: self._validate_address,
            SlotType.LOCATION: self._validate_location,
        }
        
        validator = validators.get(slot_type, self._validate_text)
        is_valid, error = validator(value, validation_rules, context or {})
        
        if is_valid:
            logger.info(f"✅ [SlotValidator] Validación exitosa para {slot_type}: '{value}'")
        else:
            logger.warning(f"❌ [SlotValidator] Validación fallida para {slot_type}: {error}")
        
        return is_valid, error
    
    def _validate_text(
        self,
        value: str,
        rules: Dict[str, Any],
        context: Dict
    ) -> Tuple[bool, Optional[str]]:
        """Valida texto"""
        
        # Longitud mínima
        min_length = rules.get('min_length', 0)
        if len(value) < min_length:
            return False, f"Debe tener al menos {min_length} caracteres"
        
        # Longitud máxima
        max_length = rules.get('max_length', float('inf'))
        if len(value) > max_length:
            return False, f"No debe exceder {max_length} caracteres"
        
        # Pattern regex
        pattern = rules.get('pattern')
        if pattern:
            import re
            if not re.match(pattern, value):
                return False, "Formato no válido"
        
        # Validación contra base de datos (para productos)
        validate_against_db = rules.get('validate_against_db', False)
        if validate_against_db:
            # Obtener el nombre del slot desde el contexto si está disponible
            slot_name = context.get('slot_name', '')
            
            # Si es product_name, validar contra catálogo
            if slot_name == 'product_name' or 'product_name' in str(context):
                # 🎯 PRIMERO: Verificar si el usuario está seleccionando de opciones previas
                selected_product = self._try_ordinal_selection(value, context)
                if selected_product:
                    logger.info(f"✅ [SlotValidator] Selección ordinal detectada: '{value}' → '{selected_product}'")
                    # Actualizar el valor en el contexto para que se use el nombre del producto
                    context['_resolved_value'] = selected_product
                    # Validar el producto seleccionado
                    is_valid_product, error_msg = self._validate_product_exists(selected_product, context)
                    if not is_valid_product:
                        return False, error_msg or f"No encontramos '{selected_product}' en nuestro catálogo."
                    return True, None
                
                # Si no es selección ordinal, validar normalmente
                is_valid_product, error_msg = self._validate_product_exists(value, context)
                if not is_valid_product:
                    return False, error_msg or f"No encontramos '{value}' en nuestro catálogo. ¿Podrías verificar el nombre?"
        
        return True, None
    
    def _try_ordinal_selection(self, value: str, context: Dict) -> Optional[str]:
        """
        Intenta detectar si el usuario está seleccionando una opción ordinal
        (ej: "la primera", "segunda", "1", "2")
        
        Returns:
            El nombre del producto seleccionado, o None si no es una selección ordinal
        """
        # Obtener las sugerencias previas del contexto
        suggested_products = context.get('_suggested_products', [])
        if not suggested_products:
            return None
        
        value_lower = value.lower().strip()
        
        # Mapeo de palabras ordinales a índices
        ordinal_map = {
            '1': 0, 'primera': 0, 'primero': 0, '1ra': 0, '1ro': 0,
            '2': 1, 'segunda': 1, 'segundo': 1, '2da': 1, '2do': 1,
            '3': 2, 'tercera': 2, 'tercero': 2, '3ra': 2, '3ro': 2,
            '4': 3, 'cuarta': 3, 'cuarto': 3, '4ta': 3, '4to': 3,
            '5': 4, 'quinta': 4, 'quinto': 4, '5ta': 4, '5to': 4,
        }
        
        # Detectar referencias con artículos ("la primera", "el segundo")
        for word in ['la ', 'el ', 'lo ']:
            if value_lower.startswith(word):
                value_lower = value_lower[len(word):].strip()
                break
        
        # Buscar coincidencia
        if value_lower in ordinal_map:
            index = ordinal_map[value_lower]
            if index < len(suggested_products):
                logger.info(f"🎯 [SlotValidator] Selección ordinal '{value}' mapeada a índice {index}")
                return suggested_products[index]
        
        return None
    
    def _validate_product_exists(self, product_name: str, context: Dict = None) -> Tuple[bool, Optional[str]]:
        """
        Valida que un producto exista en la base de datos
        
        Args:
            product_name: Nombre del producto a validar
            context: Contexto para guardar sugerencias
            
        Returns:
            Tuple (existe, mensaje_error)
        """
        if context is None:
            context = {}
            
        try:
            from config.database import get_db_context
            from app.services.product_service import ProductService
            
            with get_db_context() as db:
                product_service = ProductService(db)
                product = product_service.get_product_by_name_fuzzy(product_name)
                
                if product:
                    logger.info(f"✅ [SlotValidator] Producto validado: '{product_name}' → {product.name}")
                    # Limpiar sugerencias previas si el producto es válido
                    if '_suggested_products' in context:
                        del context['_suggested_products']
                    return True, None
                else:
                    logger.warning(f"❌ [SlotValidator] Producto no encontrado: '{product_name}'")
                    # Sugerir productos similares
                    similar_products = product_service.search_products(product_name)
                    if similar_products:
                        # Guardar las sugerencias en el contexto para la próxima respuesta
                        product_names = [p.name for p in similar_products[:5]]  # Guardar hasta 5
                        context['_suggested_products'] = product_names
                        suggestions = ", ".join(product_names[:3])  # Mostrar solo 3
                        logger.info(f"💡 [SlotValidator] Guardadas {len(product_names)} sugerencias: {product_names}")
                        return False, f"No encontramos '{product_name}'. ¿Te refieres a alguno de estos: {suggestions}?"
                    return False, f"No encontramos '{product_name}' en nuestro catálogo."
                    
        except Exception as e:
            logger.error(f"❌ [SlotValidator] Error validando producto: {e}")
            # En caso de error, permitir el valor pero loguear
            return True, None
    
    def _validate_number(
        self,
        value: float,
        rules: Dict[str, Any],
        context: Dict
    ) -> Tuple[bool, Optional[str]]:
        """Valida número"""
        
        # Valor mínimo
        min_value = rules.get('min')
        if min_value is not None and value < min_value:
            return False, f"Debe ser al menos {min_value}"
        
        # Valor máximo
        max_value = rules.get('max')
        if max_value is not None and value > max_value:
            return False, f"No debe exceder {max_value}"
        
        # Solo enteros
        only_integers = rules.get('only_integers', False)
        if only_integers and not isinstance(value, int) and value != int(value):
            return False, "Debe ser un número entero"
        
        # ⚡ VALIDACIÓN ESPECIAL: Si estamos removiendo de una orden
        max_quantity_available = context.get('max_quantity_available')
        if max_quantity_available is not None:
            if value > max_quantity_available:
                if max_quantity_available == 0:
                    return False, "No tienes este producto en tu orden actual."
                elif max_quantity_available == 1:
                    return False, f"Solo tienes 1 unidad de este producto en tu orden. ¿Cuántas unidades quieres eliminar?"
                else:
                    return False, f"Solo tienes {max_quantity_available} unidades de este producto en tu orden. ¿Cuántas unidades quieres eliminar?"
        
        # ⚡ VALIDACIÓN DE STOCK: Si es quantity, validar contra stock disponible
        slot_name = context.get('slot_name', '')
        if slot_name == 'quantity':
            current_slots = context.get('current_slots', {})
            product_name = current_slots.get('product_name')
            
            if product_name and max_quantity_available is None:  # Solo validar stock si NO estamos removiendo
                is_valid_stock, error_msg = self._validate_stock_availability(product_name, int(value))
                if not is_valid_stock:
                    return False, error_msg
        
        return True, None
    
    def _validate_stock_availability(self, product_name: str, quantity: int) -> Tuple[bool, Optional[str]]:
        """
        Valida que hay suficiente stock del producto
        
        Args:
            product_name: Nombre del producto
            quantity: Cantidad solicitada
            
        Returns:
            Tuple (hay_stock, mensaje_error)
        """
        try:
            from config.database import get_db_context
            from app.services.product_service import ProductService
            
            with get_db_context() as db:
                product_service = ProductService(db)
                product = product_service.get_product_by_name_fuzzy(product_name)
                
                if not product:
                    logger.warning(f"⚠️ [SlotValidator] Producto no encontrado para validación de stock: '{product_name}'")
                    return True, None  # Permitir continuar, se validará después
                
                # Verificar stock
                if product.stock < quantity:
                    logger.warning(f"❌ [SlotValidator] Stock insuficiente: {product.name} (solo {product.stock} disponibles)")
                    return False, f"Solo tenemos {product.stock} unidades disponibles. ¿Cuántas unidades quieres?"
                
                logger.info(f"✅ [SlotValidator] Stock suficiente: {product.name} ({quantity}/{product.stock})")
                return True, None
                    
        except Exception as e:
            logger.error(f"❌ [SlotValidator] Error validando stock: {e}")
            # En caso de error, permitir continuar
            return True, None
    
    def _validate_choice(
        self,
        value: str,
        rules: Dict[str, Any],
        context: Dict
    ) -> Tuple[bool, Optional[str]]:
        """Valida opción de lista"""
        
        choices = rules.get('choices', [])
        
        if not choices:
            # Si no hay opciones definidas, aceptar cualquier texto
            return True, None
        
        # Verificar si está en las opciones (case insensitive)
        value_lower = value.lower()
        for choice in choices:
            if value_lower == choice.lower():
                return True, None
        
        return False, f"Debe ser una de estas opciones: {', '.join(choices)}"
    
    def _validate_boolean(
        self,
        value: bool,
        rules: Dict[str, Any],
        context: Dict
    ) -> Tuple[bool, Optional[str]]:
        """Valida booleano"""
        if isinstance(value, bool):
            return True, None
        return False, "Debe ser Sí o No"
    
    def _validate_email(
        self,
        value: str,
        rules: Dict[str, Any],
        context: Dict
    ) -> Tuple[bool, Optional[str]]:
        """Valida email"""
        import re
        pattern = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$'
        
        if re.match(pattern, value):
            return True, None
        
        return False, "Email no válido"
    
    def _validate_phone(
        self,
        value: str,
        rules: Dict[str, Any],
        context: Dict
    ) -> Tuple[bool, Optional[str]]:
        """Valida teléfono"""
        
        # Limpiar caracteres no numéricos
        import re
        digits = re.sub(r'\D', '', value)
        
        min_digits = rules.get('min_digits', 7)
        max_digits = rules.get('max_digits', 15)
        
        if len(digits) < min_digits:
            return False, f"Teléfono debe tener al menos {min_digits} dígitos"
        
        if len(digits) > max_digits:
            return False, f"Teléfono no debe exceder {max_digits} dígitos"
        
        return True, None
    
    def _validate_address(
        self,
        value: str,
        rules: Dict[str, Any],
        context: Dict
    ) -> Tuple[bool, Optional[str]]:
        """Valida dirección"""
        
        import re
        
        # Debe tener al menos longitud mínima
        min_length = rules.get('min_length', 10)
        if len(value) < min_length:
            return False, f"Dirección debe tener al menos {min_length} caracteres"
        
        # Debe contener al menos un número
        if not re.search(r'\d', value):
            return False, "Dirección debe contener número de calle"
        
        return True, None
    
    def _validate_location(
        self,
        value: str,
        rules: Dict[str, Any],
        context: Dict
    ) -> Tuple[bool, Optional[str]]:
        """
        Valida coordenadas GPS
        
        Args:
            value: String en formato "latitude,longitude"
            rules: Reglas de validación
            context: Contexto adicional
            
        Returns:
            Tuple (es_válido, mensaje_error)
        """
        try:
            # Parsear coordenadas
            parts = value.split(',')
            if len(parts) != 2:
                return False, "Formato de ubicación inválido. Debe ser 'latitud,longitud'"
            
            lat_str, lon_str = parts
            latitude = float(lat_str.strip())
            longitude = float(lon_str.strip())
            
            # Validar rangos de latitud y longitud
            if not (-90 <= latitude <= 90):
                return False, f"Latitud inválida: {latitude}. Debe estar entre -90 y 90"
            
            if not (-180 <= longitude <= 180):
                return False, f"Longitud inválida: {longitude}. Debe estar entre -180 y 180"
            
            # Validar que no sean coordenadas (0, 0) - ubicación predeterminada inválida
            if latitude == 0 and longitude == 0:
                return False, "Ubicación inválida. Por favor comparte tu ubicación real"
            
            logger.info(f"✅ [SlotValidator] Ubicación válida: {latitude}, {longitude}")
            return True, None
            
        except ValueError:
            return False, "No se pudieron leer las coordenadas. Por favor comparte tu ubicación desde WhatsApp"
        except Exception as e:
            logger.error(f"❌ [SlotValidator] Error validando ubicación: {e}")
            return False, "Error validando ubicación. Por favor intenta de nuevo"