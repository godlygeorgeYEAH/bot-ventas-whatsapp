"""
Script para limpiar la conversación activa de un usuario
"""
import sys
from pathlib import Path
import io

# Configurar UTF-8 para Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from config.database import get_db_context
from app.database.models import Customer, Conversation

if __name__ == "__main__":
    phone = "15737457069"  # Tu número de prueba
    
    with get_db_context() as db:
        customer = db.query(Customer).filter(Customer.phone == phone).first()
        
        if customer:
            # Marcar todas las conversaciones como inactivas
            conversations = db.query(Conversation).filter(
                Conversation.customer_id == customer.id,
                Conversation.is_active == True
            ).all()
            
            for conv in conversations:
                conv.is_active = False
                print(f"✅ Conversación {conv.id} marcada como inactiva")
            
            db.commit()
            print(f"\n✅ {len(conversations)} conversaciones limpiadas para {phone}")
        else:
            print(f"❌ Cliente {phone} no encontrado")

