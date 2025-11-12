from typing import Dict, Any, Optional
from loguru import logger


class ConfirmationManager:
    """Maneja confirmaciones antes de ejecutar acciones"""
    
    @staticmethod
    def generate_confirmation_message(
        module_name: str,
        slots_data: Dict[str, Any]
    ) -> str:
        """
        Genera un mensaje de confirmación basado en el módulo y datos
        
        Args:
            module_name: Nombre del módulo
            slots_data: Datos recolectados
            
        Returns:
            Mensaje de confirmación
        """
        
        if module_name == "CreateOrderModule":
            return ConfirmationManager._confirm_order(slots_data)
        
        elif module_name == "ProductInquiryModule":
            return ConfirmationManager._confirm_product_inquiry(slots_data)
        
        # Por defecto, confirmación genérica
        return ConfirmationManager._confirm_generic(slots_data)
    
    @staticmethod
    def _confirm_order(slots_data: Dict[str, Any]) -> str:
        """Confirmación específica para órdenes"""
        
        product = slots_data.get("product_name", "N/A")
        quantity = slots_data.get("quantity", "N/A")
        delivery = slots_data.get("delivery_method", "N/A")
        address = slots_data.get("delivery_address", "N/A")
        phone = slots_data.get("phone", "N/A")
        
        message = """📋 RESUMEN DE TU PEDIDO

Por favor confirma que todo es correcto:

"""
        message += f"🛍️ Producto: {product}\n"
        message += f"📦 Cantidad: {quantity}\n"
        message += f"🚚 Entrega: {delivery}\n"
        
        if address != "N/A":
            message += f"📍 Direccion: {address}\n"
        
        message += f"📱 Contacto: {phone}\n"
        
        message += "\n¿Todo es correcto?\n"
        message += "Responde 'SI' para confirmar o 'NO' para cancelar\n"
        message += "O dime que campo quieres corregir (producto, cantidad, direccion, etc.)"
        
        return message
    
    @staticmethod
    def _confirm_product_inquiry(slots_data: Dict[str, Any]) -> str:
        """Confirmación para consulta de productos"""
        
        category = slots_data.get("product_category", "N/A")
        price_range = slots_data.get("price_range", "Cualquiera")
        
        message = f"""Perfecto! Voy a buscar {category} """
        
        if price_range != "Cualquiera":
            message += f"en el rango de {price_range}"
        
        message += ".\n\n¿Procedemos con la busqueda?"
        
        return message
    
    @staticmethod
    def _confirm_generic(slots_data: Dict[str, Any]) -> str:
        """Confirmación genérica"""
        
        message = "He recopilado la siguiente informacion:\n\n"
        
        for key, value in slots_data.items():
            formatted_key = key.replace("_", " ").title()
            message += f"- {formatted_key}: {value}\n"
        
        message += "\n¿Es correcto? (Si/No)"
        
        return message
    
    @staticmethod
    def parse_confirmation_response(message: str) -> Optional[str]:
        """
        Determina la respuesta del usuario a una confirmación
        
        Args:
            message: Mensaje del usuario
            
        Returns:
            "yes", "no", "edit:{field}", o None
        """
        message_lower = message.lower().strip()
        
        # Respuestas afirmativas
        yes_keywords = ["si", "sí", "yes", "confirmar", "correcto", "ok", "dale", "adelante"]
        if any(keyword in message_lower for keyword in yes_keywords):
            return "yes"
        
        # Respuestas negativas
        no_keywords = ["no", "cancelar", "incorrecto", "mal"]
        if any(keyword in message_lower for keyword in no_keywords):
            return "no"
        
        # Intentar detectar corrección de campo
        fields_map = {
            "producto": "product_name",
            "cantidad": "quantity",
            "entrega": "delivery_method",
            "direccion": "delivery_address",
            "dirección": "delivery_address",
            "telefono": "phone",
            "teléfono": "phone",
        }
        
        for field_name, slot_name in fields_map.items():
            if field_name in message_lower:
                return f"edit:{slot_name}"
        
        return None