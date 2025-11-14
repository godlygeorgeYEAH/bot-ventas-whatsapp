"""
API endpoints para gestión de configuración del sistema
"""
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from config.database import get_db
from app.database.models import Settings
from loguru import logger

router = APIRouter(prefix="/api/settings", tags=["settings"])


# Schemas de respuesta
class SettingResponse(BaseModel):
    id: str
    key: str
    value: Any
    description: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class UpdateSettingRequest(BaseModel):
    value: Any


class CreateSettingRequest(BaseModel):
    key: str
    value: Any
    description: Optional[str] = None


@router.get("", response_model=List[SettingResponse])
async def get_all_settings(db: Session = Depends(get_db)):
    """
    Obtener todas las configuraciones del sistema
    """
    try:
        settings = db.query(Settings).all()

        result = []
        for setting in settings:
            result.append({
                "id": setting.id,
                "key": setting.key,
                "value": setting.value,
                "description": setting.description,
                "created_at": setting.created_at.isoformat(),
                "updated_at": setting.updated_at.isoformat()
            })

        return result

    except Exception as e:
        logger.error(f"Error obteniendo configuraciones: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al obtener configuraciones")


@router.get("/{key}", response_model=SettingResponse)
async def get_setting(key: str, db: Session = Depends(get_db)):
    """
    Obtener una configuración específica por key
    """
    try:
        setting = db.query(Settings).filter(Settings.key == key).first()

        if not setting:
            raise HTTPException(status_code=404, detail=f"Configuración '{key}' no encontrada")

        return {
            "id": setting.id,
            "key": setting.key,
            "value": setting.value,
            "description": setting.description,
            "created_at": setting.created_at.isoformat(),
            "updated_at": setting.updated_at.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo configuración {key}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al obtener configuración")


@router.post("", response_model=SettingResponse)
async def create_setting(request: CreateSettingRequest, db: Session = Depends(get_db)):
    """
    Crear una nueva configuración
    """
    try:
        # Verificar si ya existe
        existing = db.query(Settings).filter(Settings.key == request.key).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Configuración '{request.key}' ya existe")

        # Crear nueva configuración
        setting = Settings(
            key=request.key,
            value=request.value,
            description=request.description
        )

        db.add(setting)
        db.commit()
        db.refresh(setting)

        logger.info(f"✅ Configuración creada: {request.key}")

        return {
            "id": setting.id,
            "key": setting.key,
            "value": setting.value,
            "description": setting.description,
            "created_at": setting.created_at.isoformat(),
            "updated_at": setting.updated_at.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creando configuración: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al crear configuración")


@router.patch("/{key}", response_model=SettingResponse)
async def update_setting(
    key: str,
    request: UpdateSettingRequest,
    db: Session = Depends(get_db)
):
    """
    Actualizar una configuración existente
    """
    try:
        setting = db.query(Settings).filter(Settings.key == key).first()

        if not setting:
            raise HTTPException(status_code=404, detail=f"Configuración '{key}' no encontrada")

        # Actualizar valor
        setting.value = request.value

        db.commit()
        db.refresh(setting)

        logger.info(f"✅ Configuración actualizada: {key}")

        return {
            "id": setting.id,
            "key": setting.key,
            "value": setting.value,
            "description": setting.description,
            "created_at": setting.created_at.isoformat(),
            "updated_at": setting.updated_at.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error actualizando configuración {key}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al actualizar configuración")


@router.delete("/{key}")
async def delete_setting(key: str, db: Session = Depends(get_db)):
    """
    Eliminar una configuración

    ADVERTENCIA: Esta acción no se puede deshacer
    """
    try:
        setting = db.query(Settings).filter(Settings.key == key).first()

        if not setting:
            raise HTTPException(status_code=404, detail=f"Configuración '{key}' no encontrada")

        db.delete(setting)
        db.commit()

        logger.info(f"✅ Configuración eliminada: {key}")

        return {
            "success": True,
            "message": f"Configuración '{key}' eliminada correctamente"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error eliminando configuración {key}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al eliminar configuración")


# ============================================
# ENDPOINTS ESPECÍFICOS PARA NÚMEROS DE ADMIN
# ============================================

@router.get("/admin-numbers/list", response_model=List[str])
async def get_admin_numbers(db: Session = Depends(get_db)):
    """
    Obtener la lista de números de administrador

    Devuelve un array de números de teléfono que tienen permisos de admin
    """
    try:
        setting = db.query(Settings).filter(Settings.key == "admin_numbers").first()

        if not setting:
            # Si no existe, devolver array vacío
            return []

        # El valor debe ser un array de strings
        if not isinstance(setting.value, list):
            logger.warning(f"⚠️ admin_numbers tiene formato inválido: {type(setting.value)}")
            return []

        return setting.value

    except Exception as e:
        logger.error(f"Error obteniendo números de admin: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al obtener números de administrador")


class AddAdminNumberRequest(BaseModel):
    phone_number: str


@router.post("/admin-numbers/add")
async def add_admin_number(request: AddAdminNumberRequest, db: Session = Depends(get_db)):
    """
    Agregar un número de teléfono a la lista de administradores
    """
    try:
        phone = request.phone_number.strip()

        if not phone:
            raise HTTPException(status_code=400, detail="Número de teléfono no puede estar vacío")

        # Obtener o crear el setting
        setting = db.query(Settings).filter(Settings.key == "admin_numbers").first()

        if not setting:
            # Crear nuevo setting con el número
            setting = Settings(
                key="admin_numbers",
                value=[phone],
                description="Números de teléfono con permisos de administrador"
            )
            db.add(setting)
        else:
            # Verificar que value sea una lista
            if not isinstance(setting.value, list):
                setting.value = []

            # Verificar si el número ya existe
            if phone in setting.value:
                raise HTTPException(status_code=400, detail="Este número ya está en la lista de administradores")

            # Agregar número (crear nueva lista para que SQLAlchemy detecte el cambio)
            setting.value = setting.value + [phone]

        db.commit()
        db.refresh(setting)

        logger.info(f"✅ Número de admin agregado: {phone}")

        return {
            "success": True,
            "message": f"Número {phone} agregado a administradores",
            "admin_numbers": setting.value
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error agregando número de admin: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al agregar número de administrador")


class RemoveAdminNumberRequest(BaseModel):
    phone_number: str


@router.post("/admin-numbers/remove")
async def remove_admin_number(request: RemoveAdminNumberRequest, db: Session = Depends(get_db)):
    """
    Eliminar un número de teléfono de la lista de administradores
    """
    try:
        phone = request.phone_number.strip()

        if not phone:
            raise HTTPException(status_code=400, detail="Número de teléfono no puede estar vacío")

        # Obtener el setting
        setting = db.query(Settings).filter(Settings.key == "admin_numbers").first()

        if not setting or not isinstance(setting.value, list):
            raise HTTPException(status_code=404, detail="No hay números de administrador configurados")

        # Verificar si el número existe
        if phone not in setting.value:
            raise HTTPException(status_code=404, detail="Este número no está en la lista de administradores")

        # Eliminar número (crear nueva lista para que SQLAlchemy detecte el cambio)
        setting.value = [n for n in setting.value if n != phone]

        db.commit()
        db.refresh(setting)

        logger.info(f"✅ Número de admin eliminado: {phone}")

        return {
            "success": True,
            "message": f"Número {phone} eliminado de administradores",
            "admin_numbers": setting.value
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error eliminando número de admin: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al eliminar número de administrador")


# ============================================
# ENDPOINTS PARA CONFIGURACIÓN DE TIMEOUT DE ÓRDENES
# ============================================

@router.get("/order-timeout/minutes", response_model=int)
async def get_order_timeout(db: Session = Depends(get_db)):
    """
    Obtener el timeout de órdenes en minutos

    Devuelve el número de minutos después de los cuales una orden pending
    se marca como abandonada automáticamente (default: 30)
    """
    try:
        setting = db.query(Settings).filter(Settings.key == "order_timeout_minutes").first()

        if not setting:
            # Devolver default de 30 minutos si no existe
            return 30

        # El valor debe ser un número
        if isinstance(setting.value, (int, float)):
            return int(setting.value)
        else:
            logger.warning(f"⚠️ order_timeout_minutes tiene formato inválido: {type(setting.value)}")
            return 30

    except Exception as e:
        logger.error(f"Error obteniendo timeout de órdenes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al obtener timeout de órdenes")


class UpdateOrderTimeoutRequest(BaseModel):
    timeout_minutes: int


@router.put("/order-timeout/minutes")
async def update_order_timeout(
    request: UpdateOrderTimeoutRequest,
    db: Session = Depends(get_db)
):
    """
    Actualizar el timeout de órdenes en minutos

    Args:
        timeout_minutes: Número de minutos (mínimo: 5, máximo: 1440 = 24 horas)
    """
    try:
        timeout = request.timeout_minutes

        # Validar rango
        if timeout < 5:
            raise HTTPException(status_code=400, detail="El timeout mínimo es 5 minutos")
        if timeout > 1440:  # 24 horas
            raise HTTPException(status_code=400, detail="El timeout máximo es 1440 minutos (24 horas)")

        # Obtener o crear el setting
        setting = db.query(Settings).filter(Settings.key == "order_timeout_minutes").first()

        if not setting:
            # Crear nuevo setting
            setting = Settings(
                key="order_timeout_minutes",
                value=timeout,
                description="Tiempo en minutos después del cual una orden pending se marca como abandonada"
            )
            db.add(setting)
        else:
            # Actualizar valor existente
            setting.value = timeout

        db.commit()
        db.refresh(setting)

        logger.info(f"✅ Timeout de órdenes actualizado a {timeout} minutos")

        return {
            "success": True,
            "message": f"Timeout actualizado a {timeout} minutos",
            "timeout_minutes": timeout
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error actualizando timeout de órdenes: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al actualizar timeout de órdenes")
