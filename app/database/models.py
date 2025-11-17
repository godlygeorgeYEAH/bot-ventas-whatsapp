from sqlalchemy import (
    Column, 
    String, 
    Integer, 
    Boolean, 
    DateTime, 
    Text, 
    JSON, 
    ForeignKey,
    Float
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from config.database import Base
import uuid
from datetime import datetime
from enum import Enum

def generate_uuid():
    return str(uuid.uuid4())


class ConversationStateEnum(str, Enum):
    IDLE = "idle"
    COLLECTING_SLOTS = "collecting_slots"
    EXECUTING_ACTION = "executing_action"
    COMPLETED = "completed"


class MessageType(str, Enum):
    TEXT = "text"
    VOICE = "voice"
    IMAGE = "image"


class Customer(Base):
    __tablename__ = "customers"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    phone = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    
    first_contact_at = Column(DateTime, default=datetime.utcnow)
    last_contact_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    total_messages = Column(Integer, default=0)
    
    preferences = Column(JSON, default=dict)
    customer_data = Column(JSON, default=dict)
    
    conversations = relationship("Conversation", back_populates="customer")
    messages = relationship("Message", back_populates="customer")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    customer_id = Column(String, ForeignKey("customers.id"), nullable=False)
    
    state = Column(String, default="idle")
    current_intent = Column(String, nullable=True)
    current_module = Column(String, nullable=True)
    
    slots_data = Column(JSON, default=dict)
    slots_schema = Column(JSON, default=dict)
    current_slot = Column(String, nullable=True)
    validation_attempts = Column(JSON, default=dict)
    
    context_data = Column(JSON, default=dict)
    
    started_at = Column(DateTime, default=datetime.utcnow)
    last_activity_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    
    customer = relationship("Customer", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    customer_id = Column(String, ForeignKey("customers.id"), nullable=False)
    
    message_type = Column(String, default="text")
    content = Column(Text, nullable=False)
    raw_content = Column(Text, nullable=True)
    
    is_from_bot = Column(Boolean, default=False)
    
    waha_message_id = Column(String, nullable=True)
    media_url = Column(String, nullable=True)
    
    intent_detected = Column(String, nullable=True)
    confidence_score = Column(Integer, nullable=True)
    processing_metadata = Column(JSON, default=dict)
    
    conversation = relationship("Conversation", back_populates="messages")
    customer = relationship("Customer", back_populates="messages")
    
    created_at = Column(DateTime, default=datetime.utcnow)

class Product(Base):
    """Modelo de productos del catálogo"""

    __tablename__ = "products"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text)
    price = Column(Float, nullable=False)
    stock = Column(Integer, default=0, nullable=False)
    category = Column(String(100), index=True)
    image_path = Column(String(500))  # ← CAMBIAR DE image_url a image_path
    sku = Column(String(100), unique=True)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<Product {self.name} (${self.price})>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "price": self.price,
            "stock": self.stock,
            "category": self.category,
            "image_path": self.image_path,  # ← CAMBIAR
            "sku": self.sku,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    @property
    def in_stock(self):
        return self.stock > 0 and self.is_active
    
    @property
    def has_image(self):
        """Verifica si el producto tiene imagen"""
        import os
        if not self.image_path:
            return False
        return os.path.exists(self.image_path)
    
class ProductCategory(Base):
    """Categorías de productos"""
    
    __tablename__ = "product_categories"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    parent_id = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    
    def __repr__(self):
        return f"<ProductCategory {self.name}>"
    

# ============================================
# MODELOS DE ÓRDENES
# ============================================

class OrderStatus(str, Enum):
    """Estados posibles de una orden"""
    PENDING = "pending"              # Orden creada, pendiente de confirmación
    CONFIRMED = "confirmed"          # Confirmada por el cliente
    PROCESSING = "processing"        # En proceso de preparación
    SHIPPED = "shipped"              # Enviada
    DELIVERED = "delivered"          # Entregada
    CANCELLED = "cancelled"          # Cancelada
    REFUNDED = "refunded"           # Reembolsada
    ABANDONED = "abandoned"          # Abandonada (timeout de 30 minutos)


class Order(Base):
    """Modelo de órdenes/pedidos"""
    
    __tablename__ = "orders"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    order_number = Column(String(50), unique=True, nullable=False, index=True)  # Ej: ORD-20231103-001
    customer_id = Column(String, ForeignKey("customers.id"), nullable=False, index=True)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=True)
    
    # Estado
    status = Column(String(50), default=OrderStatus.PENDING.value, nullable=False, index=True)
    
    # Montos
    subtotal = Column(Float, nullable=False)  # Suma de productos
    tax = Column(Float, default=0.0)          # Impuestos
    shipping_cost = Column(Float, default=0.0) # Costo de envío
    discount = Column(Float, default=0.0)     # Descuentos
    total = Column(Float, nullable=False)     # Total final
    
    # Información de entrega
    delivery_address = Column(Text, nullable=True)  # Dirección texto (opcional si hay GPS)
    delivery_latitude = Column(Float, nullable=True)  # Latitud GPS
    delivery_longitude = Column(Float, nullable=True)  # Longitud GPS
    delivery_reference = Column(String(200), nullable=True)  # Referencia: nombre de casa, edificio, apt
    delivery_city = Column(String(100))
    delivery_phone = Column(String(50))
    delivery_notes = Column(Text)  # Notas especiales de entrega
    
    # Información de pago
    payment_method = Column(String(50))  # efectivo, tarjeta, transferencia
    payment_status = Column(String(50), default="pending")  # pending, paid, failed
    payment_reference = Column(String(200))  # Referencia de pago
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    confirmed_at = Column(DateTime)
    shipped_at = Column(DateTime)
    delivered_at = Column(DateTime)
    cancelled_at = Column(DateTime)
    abandoned_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Metadata adicional
    order_metadata = Column(JSON, default=dict)  # Datos extra
    cancellation_reason = Column(Text)  # Razón de cancelación
    abandonment_reason = Column(Text)  # Razón de abandono (ej: "Timeout 30 minutos")
    
    # Relaciones
    customer = relationship("Customer", backref="orders")
    conversation = relationship("Conversation", backref="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Order {self.order_number} - {self.status} (${self.total})>"
    
    def to_dict(self):
        """Convierte la orden a diccionario"""
        return {
            "id": self.id,
            "order_number": self.order_number,
            "customer_id": self.customer_id,
            "status": self.status,
            "subtotal": self.subtotal,
            "tax": self.tax,
            "shipping_cost": self.shipping_cost,
            "discount": self.discount,
            "total": self.total,
            "delivery_address": self.delivery_address,
            "delivery_latitude": self.delivery_latitude,
            "delivery_longitude": self.delivery_longitude,
            "delivery_reference": self.delivery_reference,
            "delivery_city": self.delivery_city,
            "payment_method": self.payment_method,
            "payment_status": self.payment_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "confirmed_at": self.confirmed_at.isoformat() if self.confirmed_at else None,
            "items": [item.to_dict() for item in self.items] if self.items else []
        }
    
    @property
    def is_active(self):
        """Verifica si la orden está activa (no cancelada ni entregada)"""
        return self.status not in [OrderStatus.CANCELLED.value, OrderStatus.DELIVERED.value, OrderStatus.REFUNDED.value]
    
    @property
    def can_be_cancelled(self):
        """Verifica si la orden puede ser cancelada"""
        return self.status in [OrderStatus.PENDING.value, OrderStatus.CONFIRMED.value]


class OrderItem(Base):
    """Items/productos de una orden"""
    
    __tablename__ = "order_items"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    order_id = Column(String, ForeignKey("orders.id"), nullable=False, index=True)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    
    # Información del producto al momento de la compra
    product_name = Column(String(200), nullable=False)  # Guardamos nombre por si producto se elimina
    product_sku = Column(String(100))
    
    # Cantidades y precios
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)  # Precio unitario al momento de la compra
    subtotal = Column(Float, nullable=False)    # quantity * unit_price
    
    # Metadata
    item_notes = Column(Text)  # Notas específicas del item
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    order = relationship("Order", back_populates="items")
    product = relationship("Product", backref="order_items")
    
    def __repr__(self):
        return f"<OrderItem {self.product_name} x{self.quantity} (${self.subtotal})>"
    
    def to_dict(self):
        """Convierte el item a diccionario"""
        return {
            "id": self.id,
            "order_id": self.order_id,
            "product_id": self.product_id,
            "product_name": self.product_name,
            "product_sku": self.product_sku,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "subtotal": self.subtotal,
            "item_notes": self.item_notes
        }


class CartSession(Base):
    """
    Sesiones de carrito para webapp
    
    Cada sesión representa un link único enviado al usuario para
    que complete su orden en la webapp. El token es único y tiene
    una expiración de 24 horas.
    
    Estados:
    - Creado: token generado, esperando que usuario abra link
    - Usado: usuario completó orden en webapp, order_id está presente
    - Expirado: expires_at pasó, token ya no válido
    """
    
    __tablename__ = "cart_sessions"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    
    # Token único para el link (UUID)
    token = Column(String(36), unique=True, nullable=False, index=True)
    
    # Cliente asociado
    customer_id = Column(String, ForeignKey("customers.id"), nullable=False, index=True)
    
    # Expiración del token (default: 24 horas desde creación)
    expires_at = Column(DateTime, nullable=False)
    
    # Estado del carrito
    used = Column(Boolean, default=False, nullable=False)
    
    # Orden creada cuando el usuario completa el carrito (opcional)
    order_id = Column(String, ForeignKey("orders.id"), nullable=True)
    
    # Metadata del carrito (puede guardar productos pre-seleccionados, etc.)
    cart_data = Column(JSON, default=dict)
    
    # Auditoría
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    customer = relationship("Customer", backref="cart_sessions")
    order = relationship("Order", backref="cart_session")
    
    def __repr__(self):
        status = "usado" if self.used else ("expirado" if self.is_expired() else "activo")
        return f"<CartSession {self.token[:8]}... ({status})>"
    
    @property
    def is_expired(self):
        """Verifica si el token expiró"""
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_valid(self):
        """Verifica si el token es válido (no usado y no expirado)"""
        return not self.used and not self.is_expired
    
    def to_dict(self):
        """Convierte la sesión a diccionario"""
        return {
            "id": self.id,
            "token": self.token,
            "customer_id": self.customer_id,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "used": self.used,
            "order_id": self.order_id,
            "cart_data": self.cart_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_expired": self.is_expired,
            "is_valid": self.is_valid
        }


class Settings(Base):
    """
    Configuración del sistema

    Almacena parámetros de configuración como números de administrador,
    configuraciones del bot, etc.
    """

    __tablename__ = "settings"

    id = Column(String, primary_key=True, default=generate_uuid)

    # Clave única para identificar el parámetro
    key = Column(String(100), unique=True, nullable=False, index=True)

    # Valor del parámetro (JSON para soportar strings, arrays, objetos)
    value = Column(JSON, nullable=False)

    # Descripción del parámetro
    description = Column(Text, nullable=True)

    # Auditoría
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Settings {self.key}>"

    def to_dict(self):
        """Convierte el setting a diccionario"""
        return {
            "id": self.id,
            "key": self.key,
            "value": self.value,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


# ============================================
# MODELOS DE SISTEMA Y MONITOREO
# ============================================

class BotStatus(Base):
    """
    Estado del bot y sistema de comunicación con WAHA

    Rastrea el estado de salud del bot y detecta problemas de
    comunicación con WAHA.

    Estados posibles:
    - online: Todo funcionando correctamente
    - degraded: Algunos fallos pero bot responde
    - incommunicado_critico: Pérdida total de comunicación
    - offline: Bot detenido
    """

    __tablename__ = "bot_status"

    id = Column(String, primary_key=True, default=generate_uuid)

    # Estado actual del bot
    status = Column(String(50), default="online", nullable=False)  # online/degraded/incommunicado_critico/offline

    # Razón del estado actual
    reason = Column(Text, nullable=True)

    # Timestamps de comunicación con WAHA
    last_update = Column(DateTime, default=datetime.utcnow, nullable=False)
    waha_last_success = Column(DateTime, nullable=True)  # Última vez que WAHA respondió exitosamente

    # Contador de fallos consecutivos
    waha_consecutive_failures = Column(Integer, default=0)

    # Metadata adicional
    metadata = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<BotStatus {self.status} - {self.reason[:50] if self.reason else 'No reason'}>"

    def to_dict(self):
        return {
            "id": self.id,
            "status": self.status,
            "reason": self.reason,
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "waha_last_success": self.waha_last_success.isoformat() if self.waha_last_success else None,
            "waha_consecutive_failures": self.waha_consecutive_failures,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class CommunicationFailure(Base):
    """
    Registro de fallos de comunicación con WAHA

    Cada vez que el bot no puede comunicarse con WAHA después de
    reintentos, se crea un registro para rastrear y diagnosticar el problema.

    Tipos de fallo:
    - WEBHOOK_ONLY: Solo el webhook falló, diagnóstico alcanzó al usuario/admin
    - TOTAL_COMMUNICATION_LOSS: Pérdida total, ni usuario ni admin alcanzables
    """

    __tablename__ = "communication_failures"

    id = Column(String, primary_key=True, default=generate_uuid)

    # Tipo de fallo
    failure_type = Column(String(50), nullable=False)  # WEBHOOK_ONLY / TOTAL_COMMUNICATION_LOSS

    # Orden afectada
    order_id = Column(String, ForeignKey("orders.id"), nullable=True, index=True)

    # Cliente afectado
    customer_phone = Column(String(50), nullable=True)

    # Resultados del diagnóstico
    diagnostic_user_reached = Column(Boolean, default=False)  # ¿Se alcanzó al usuario en diagnóstico?
    diagnostic_admin_reached = Column(Boolean, default=False)  # ¿Se alcanzó al admin en diagnóstico?

    # Resolución
    resolved_at = Column(DateTime, nullable=True)
    resolution_method = Column(String(50), nullable=True)  # manual_contact / bot_recovered / auto_recovery

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relación con orden
    order = relationship("Order", backref="communication_failures")

    def __repr__(self):
        status = "resolved" if self.resolved_at else "pending"
        return f"<CommunicationFailure {self.failure_type} - Order {self.order_id} ({status})>"

    def to_dict(self):
        return {
            "id": self.id,
            "failure_type": self.failure_type,
            "order_id": self.order_id,
            "customer_phone": self.customer_phone,
            "diagnostic_user_reached": self.diagnostic_user_reached,
            "diagnostic_admin_reached": self.diagnostic_admin_reached,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolution_method": self.resolution_method,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }