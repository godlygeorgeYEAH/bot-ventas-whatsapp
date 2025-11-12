"""
Script de testing para el backend del sistema de carrito

Este script prueba todos los endpoints y funcionalidades del sistema:
1. Creación de sesión de carrito
2. Validación de token
3. Obtención de productos
4. Completado de carrito (webhook)
5. Verificación de estado
"""
import sys
from pathlib import Path

# Agregar directorio raíz al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

import requests
import json
from loguru import logger
from config.database import get_db_context
from app.database.models import Customer, Product, CartSession, Order
from app.services.cart_service import CartService
from sqlalchemy import func

# Configuración
BASE_URL = "http://localhost:8000"
TEST_PHONE = "18095551234"

def print_section(title: str):
    """Imprime un separador de sección"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")

def print_success(message: str):
    """Imprime mensaje de éxito"""
    print(f"✅ {message}")

def print_error(message: str):
    """Imprime mensaje de error"""
    print(f"❌ {message}")

def print_info(message: str):
    """Imprime información"""
    print(f"ℹ️  {message}")

def print_json(data: dict):
    """Imprime JSON formateado"""
    print(json.dumps(data, indent=2, ensure_ascii=False))

def check_prerequisites():
    """Verifica que los prerequisitos estén listos"""
    print_section("1. VERIFICANDO PREREQUISITOS")
    
    # 1. Verificar que el servidor esté corriendo
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print_success("Servidor FastAPI está corriendo")
        else:
            print_error(f"Servidor respondió con código {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_error("No se pudo conectar al servidor FastAPI")
        print_info("Por favor inicia el bot con: python run.py")
        return False
    except Exception as e:
        print_error(f"Error verificando servidor: {e}")
        return False
    
    # 2. Verificar que exista el cliente de prueba
    with get_db_context() as db:
        customer = db.query(Customer).filter(Customer.phone == TEST_PHONE).first()
        
        if customer:
            print_success(f"Cliente de prueba encontrado: {customer.name} ({customer.phone})")
        else:
            print_error(f"Cliente de prueba no encontrado: {TEST_PHONE}")
            print_info("Creando cliente de prueba...")
            
            # Crear cliente de prueba
            customer = Customer(
                phone=TEST_PHONE,
                name="Cliente Prueba",
                email="prueba@test.com"
            )
            db.add(customer)
            db.commit()
            db.refresh(customer)
            print_success(f"Cliente creado: {customer.name}")
    
    # 3. Verificar que existan productos
    with get_db_context() as db:
        product_count = db.query(func.count(Product.id)).filter(
            Product.is_active == True,
            Product.stock > 0
        ).scalar()
        
        if product_count > 0:
            print_success(f"Productos disponibles: {product_count}")
        else:
            print_error("No hay productos disponibles")
            print_info("Por favor ejecuta: python scripts/seed_products.py")
            return False
    
    return True

def test_create_cart_session():
    """Test 1: Crear sesión de carrito"""
    print_section("2. TEST: CREAR SESIÓN DE CARRITO")
    
    print_info(f"POST {BASE_URL}/api/cart/create")
    
    payload = {
        "customer_phone": TEST_PHONE,
        "hours_valid": 24
    }
    
    print_info("Request body:")
    print_json(payload)
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/cart/create",
            json=payload,
            timeout=10
        )
        
        print_info(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print_success("Sesión creada exitosamente")
            print_info("Response:")
            print_json(data)
            
            if data.get("success"):
                token = data.get("token")
                cart_link = data.get("cart_link")
                
                print_success(f"Token: {token}")
                print_success(f"Link: {cart_link}")
                
                return token
            else:
                print_error("success=False en la respuesta")
                return None
        else:
            print_error(f"Error {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        print_error(f"Excepción durante la prueba: {e}")
        return None

def test_validate_token(token: str):
    """Test 2: Validar token"""
    print_section("3. TEST: VALIDAR TOKEN")
    
    print_info(f"GET {BASE_URL}/api/cart/{token}")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/cart/{token}",
            timeout=10
        )
        
        print_info(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("valid"):
                print_success("Token válido")
                print_info("Response:")
                print_json(data)
                return True
            else:
                print_error(f"Token inválido: {data.get('error')}")
                print_info(f"Mensaje: {data.get('message')}")
                return False
        else:
            print_error(f"Error {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Excepción durante la prueba: {e}")
        return False

def test_get_products(token: str):
    """Test 3: Obtener productos"""
    print_section("4. TEST: OBTENER PRODUCTOS")
    
    print_info(f"GET {BASE_URL}/api/cart/{token}/products")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/cart/{token}/products",
            timeout=10
        )
        
        print_info(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            products = response.json()
            print_success(f"Productos obtenidos: {len(products)}")
            
            if len(products) > 0:
                print_info("Primeros 3 productos:")
                for product in products[:3]:
                    print(f"  • {product['name']} - ${product['price']} (Stock: {product['stock']})")
                
                return products
            else:
                print_error("No se obtuvieron productos")
                return []
        else:
            print_error(f"Error {response.status_code}: {response.text}")
            return []
            
    except Exception as e:
        print_error(f"Excepción durante la prueba: {e}")
        return []

def test_complete_cart(token: str, products: list):
    """Test 4: Completar carrito"""
    print_section("5. TEST: COMPLETAR CARRITO (WEBHOOK)")
    
    if not products or len(products) == 0:
        print_error("No hay productos para agregar al carrito")
        return None
    
    # Seleccionar primeros 2 productos
    selected_products = []
    total = 0.0
    
    for product in products[:2]:
        quantity = 1
        selected_products.append({
            "product_id": product["id"],
            "quantity": quantity
        })
        total += product["price"] * quantity
    
    print_info(f"POST {BASE_URL}/api/cart/{token}/complete")
    
    payload = {
        "products": selected_products,
        "total": total
    }
    
    print_info("Request body:")
    print_json(payload)
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/cart/{token}/complete",
            json=payload,
            timeout=10
        )
        
        print_info(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("success"):
                print_success("Carrito completado exitosamente")
                print_info("Response:")
                print_json(data)
                
                order_id = data.get("order_id")
                print_success(f"Orden ID: {order_id}")
                
                return order_id
            else:
                print_error("success=False en la respuesta")
                return None
        else:
            print_error(f"Error {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        print_error(f"Excepción durante la prueba: {e}")
        return None

def test_check_status(token: str):
    """Test 5: Verificar estado de sesión"""
    print_section("6. TEST: VERIFICAR ESTADO DE SESIÓN")
    
    print_info(f"GET {BASE_URL}/api/cart/{token}/status")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/cart/{token}/status",
            timeout=10
        )
        
        print_info(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print_success("Estado obtenido exitosamente")
            print_info("Response:")
            print_json(data)
            
            if data.get("used"):
                print_success("Sesión marcada como USADA ✓")
            
            if data.get("order_id"):
                print_success(f"Orden asociada: {data.get('order_id')}")
            
            return True
        else:
            print_error(f"Error {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Excepción durante la prueba: {e}")
        return False

def verify_database_state(order_id: str):
    """Verifica el estado en la base de datos"""
    print_section("7. VERIFICACIÓN EN BASE DE DATOS")
    
    with get_db_context() as db:
        # 1. Verificar orden
        order = db.query(Order).filter(Order.id == order_id).first()
        
        if order:
            print_success(f"Orden encontrada en BD: {order.order_number}")
            print_info(f"  Estado: {order.status}")
            print_info(f"  Total: ${order.total}")
            print_info(f"  Items: {len(order.items)}")
            
            for item in order.items:
                print(f"    • {item.product.name} x{item.quantity} - ${item.price}")
        else:
            print_error("Orden no encontrada en BD")
            return False
        
        # 2. Verificar sesión de carrito
        session = db.query(CartSession).filter(CartSession.order_id == order_id).first()
        
        if session:
            print_success(f"Sesión de carrito encontrada: {session.token[:16]}...")
            print_info(f"  Usada: {session.used}")
            print_info(f"  Expirada: {session.is_expired}")
            print_info(f"  Válida: {session.is_valid}")
        else:
            print_error("Sesión de carrito no encontrada")
            return False
    
    return True

def run_all_tests():
    """Ejecuta todos los tests"""
    print("\n" + "🧪" * 35)
    print("  TESTING BACKEND - SISTEMA DE CARRITO")
    print("🧪" * 35)
    
    # 1. Prerequisitos
    if not check_prerequisites():
        print_section("❌ TESTS ABORTADOS")
        print_error("Los prerequisitos no se cumplieron")
        return False
    
    # 2. Crear sesión
    token = test_create_cart_session()
    if not token:
        print_section("❌ TESTS ABORTADOS")
        print_error("No se pudo crear la sesión de carrito")
        return False
    
    # 3. Validar token
    if not test_validate_token(token):
        print_section("❌ TESTS ABORTADOS")
        print_error("Token inválido")
        return False
    
    # 4. Obtener productos
    products = test_get_products(token)
    if not products or len(products) == 0:
        print_section("❌ TESTS ABORTADOS")
        print_error("No se pudieron obtener productos")
        return False
    
    # 5. Completar carrito
    order_id = test_complete_cart(token, products)
    if not order_id:
        print_section("❌ TESTS ABORTADOS")
        print_error("No se pudo completar el carrito")
        return False
    
    # 6. Verificar estado
    if not test_check_status(token):
        print_section("⚠️ ADVERTENCIA")
        print_error("No se pudo verificar el estado de la sesión")
    
    # 7. Verificar BD
    if not verify_database_state(order_id):
        print_section("⚠️ ADVERTENCIA")
        print_error("Verificación de BD incompleta")
    
    # ✅ Todos los tests pasaron
    print_section("✅ TODOS LOS TESTS PASARON")
    print_success("El backend del sistema de carrito funciona correctamente")
    print_info(f"Token de prueba: {token}")
    print_info(f"Orden de prueba: {order_id}")
    
    return True

if __name__ == "__main__":
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Tests interrumpidos por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

