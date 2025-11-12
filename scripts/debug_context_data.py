"""
Script para debuggear context_data en la BD
"""
import sys
from pathlib import Path

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from config.database import SessionLocal
from app.database.models import Conversation
from loguru import logger

def debug_context():
    db = SessionLocal()
    
    try:
        # Obtener conversaciones activas
        conversations = db.query(Conversation).filter(
            Conversation.is_active == True
        ).all()
        
        for conv in conversations:
            logger.info(f"\n📊 Conversación {conv.id[:8]}...")
            logger.info(f"   context_data TYPE: {type(conv.context_data).__name__}")
            logger.info(f"   context_data VALUE: {conv.context_data}")
            
            # Verificar si context_data tiene slots_data o validation_attempts
            if conv.context_data:
                if 'slots_data' in conv.context_data:
                    logger.warning(f"   ⚠️ context_data contiene 'slots_data': {conv.context_data['slots_data']} (type: {type(conv.context_data['slots_data']).__name__})")
                if 'validation_attempts' in conv.context_data:
                    logger.warning(f"   ⚠️ context_data contiene 'validation_attempts': {conv.context_data['validation_attempts']} (type: {type(conv.context_data['validation_attempts']).__name__})")
    finally:
        db.close()

if __name__ == "__main__":
    debug_context()

