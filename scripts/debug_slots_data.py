"""
Script para debuggear slots_data en la BD
"""
import sys
from pathlib import Path

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from config.database import SessionLocal
from app.database.models import Conversation
from loguru import logger

def debug_slots():
    db = SessionLocal()
    
    try:
        # Obtener todas las conversaciones activas
        conversations = db.query(Conversation).filter(
            Conversation.is_active == True
        ).all()
        
        logger.info(f"🔍 Encontradas {len(conversations)} conversaciones activas")
        
        for conv in conversations:
            logger.info(f"\n📊 Conversación {conv.id[:8]}...")
            logger.info(f"   Customer: {conv.customer_id[:8]}...")
            logger.info(f"   Module: {conv.current_module}")
            logger.info(f"   State: {conv.state}")
            logger.info(f"   Current slot: {conv.current_slot}")
            
            # Verificar tipos
            logger.info(f"   slots_data TYPE: {type(conv.slots_data).__name__}")
            logger.info(f"   slots_data VALUE: {conv.slots_data}")
            logger.info(f"   validation_attempts TYPE: {type(conv.validation_attempts).__name__}")
            logger.info(f"   validation_attempts VALUE: {conv.validation_attempts}")
            
    finally:
        db.close()

if __name__ == "__main__":
    debug_slots()

