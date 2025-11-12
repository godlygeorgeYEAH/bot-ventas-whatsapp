"""
Script para crear un cliente de prueba
"""
import sys
sys.path.append('.')

from config.database import SessionLocal
from app.database.models import Customer
from loguru import logger


def create_test_customer():
    """Crea un cliente de prueba"""
    
    db = SessionLocal()
    
    try:
        # Verificar si ya existe
        existing = db.query(Customer).filter(Customer.phone == "15737457069").first()
        
        if existing:
            logger.info(f"✅ Cliente de prueba ya existe: {existing.phone}")
            logger.info(f"   ID: {existing.id}")
            logger.info(f"   Nombre: {existing.name}")
            return existing
        
        # Crear cliente
        logger.info("👤 Creando cliente de prueba...")
        
        customer = Customer(
            phone="15737457069",
            name="Usuario de Prueba",
            email="prueba@example.com",
            total_messages=0,
            preferences={},
            customer_data={}
        )
        
        db.add(customer)
        db.commit()
        db.refresh(customer)
        
        logger.info("✅ Cliente de prueba creado:")
        logger.info(f"   ID: {customer.id}")
        logger.info(f"   Phone: {customer.phone}")
        logger.info(f"   Nombre: {customer.name}")
        
        return customer
        
    except Exception as e:
        logger.error(f"❌ Error creando cliente: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_test_customer()