"""
Script para probar ProductService
"""
import sys
sys.path.append('.')

from config.database import SessionLocal
from app.services.product_service import ProductService
from loguru import logger


def test_product_service():
    db = SessionLocal()
    service = ProductService(db)
    
    logger.info("=" * 60)
    logger.info("🧪 Probando ProductService")
    logger.info("=" * 60)
    
    # 1. Obtener todos los productos
    logger.info("\n1️⃣ Obteniendo todos los productos:")
    all_products = service.get_all_products()
    print(service.format_product_list(all_products))
    
    # 2. Buscar por categoría
    logger.info("\n2️⃣ Productos de categoría 'laptops':")
    laptops = service.get_all_products(category="laptops")
    print(service.format_product_list(laptops))
    
    # 3. Búsqueda fuzzy
    logger.info("\n3️⃣ Búsqueda fuzzy:")
    test_searches = ["laptop", "mac", "mouse", "teclado"]
    for term in test_searches:
        product = service.get_product_by_name_fuzzy(term)
        if product:
            print(f"   '{term}' → {product.name} (${product.price})")
    
    # 4. Verificar stock
    logger.info("\n4️⃣ Verificando stock:")
    if all_products:
        product = all_products[0]
        has_stock = service.check_stock(product.id, 5)
        print(f"   {product.name}: ¿Hay 5 unidades? {has_stock}")
    
    # 5. Categorías
    logger.info("\n5️⃣ Categorías disponibles:")
    categories = service.get_categories()
    print(f"   {', '.join(categories)}")
    
    db.close()
    logger.info("\n✅ Pruebas completadas")


if __name__ == "__main__":
    test_product_service()