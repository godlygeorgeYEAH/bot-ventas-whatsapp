import sys
from pathlib import Path

# Agregar el directorio raíz al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from config.database import get_db
from app.database.models import Product

db = next(get_db())

# Productos de prueba
productos = [
    Product(
        name='Laptop HP',
        description='Laptop HP Pavilion 15, Intel Core i5, 8GB RAM, 256GB SSD',
        price=2500000,
        stock=10,
        category='computadores',
        sku='LAP-HP-001',
        is_active=True
    ),
    Product(
        name='Mouse Logitech',
        description='Mouse inalámbrico Logitech M185',
        price=45000,
        stock=50,
        category='accesorios',
        sku='MOU-LOG-001',
        is_active=True
    ),
    Product(
        name='Teclado Mecánico',
        description='Teclado mecánico RGB para gaming',
        price=180000,
        stock=25,
        category='accesorios',
        sku='TEC-MEC-001',
        is_active=True
    ),
    Product(
        name='Monitor Samsung',
        description='Monitor Samsung 24 pulgadas Full HD',
        price=650000,
        stock=15,
        category='monitores',
        sku='MON-SAM-001',
        is_active=True
    )
]

try:
    db.add_all(productos)
    db.commit()
    print('✅ Productos agregados:')
    for p in productos:
        print(f'  - {p.name}: \${p.price:,}')
except Exception as e:
    print(f'❌ Error: {e}')
    db.rollback()
finally:
    db.close()