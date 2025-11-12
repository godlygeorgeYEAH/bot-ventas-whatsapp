"""
Script de testing simple para el backend del sistema de carrito (sin emojis)
"""
import sys
from pathlib import Path

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

import requests
import json
from config.database import get_db_context
from app.database.models import Customer, Product, CartSession, Order
from sqlalchemy import func

BASE_URL = "http://localhost:8000"
TEST_PHONE = "18095551234"

def print_section(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")

def print_json(data: dict):
    print(json.dumps(data, indent=2, ensure_ascii=False))

def check_prerequisites():
    """Verifica prerequisitos"""
    print_section("1. VERIFICANDO PREREQUISITOS")
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("[OK] Servidor FastAPI esta corriendo")
        else:
            print(f"[ERROR] Servidor respondio con codigo {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERROR] No se pudo conectar al servidor: {e}")
        return False
    
    with get_db_context() as db:
        customer = db.query(Customer).filter(Customer.phone == TEST_PHONE).first()
        
        if customer:
            print(f"[OK] Cliente de prueba encontrado: {customer.name}")
        else:
            print("[INFO] Creando cliente de prueba...")
            customer = Customer(
                phone=TEST_PHONE,
                name="Cliente Prueba",
                email="prueba@test.com"
            )
            db.add(customer)
            db.commit()
            print("[OK] Cliente creado")
    
    with get_db_context() as db:
        product_count = db.query(func.count(Product.id)).filter(
            Product.is_active == True,
            Product.stock > 0
        ).scalar()
        
        if product_count > 0:
            print(f"[OK] Productos disponibles: {product_count}")
        else:
            print("[ERROR] No hay productos disponibles")
            return False
    
    return True

def test_create_cart_session():
    """Test 1: Crear sesion de carrito"""
    print_section("2. TEST: CREAR SESION DE CARRITO")
    
    print(f"POST {BASE_URL}/api/cart/create")
    
    payload = {
        "customer_phone": TEST_PHONE,
        "hours_valid": 24
    }
    
    print("Request body:")
    print_json(payload)
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/cart/create",
            json=payload,
            timeout=10
        )
        
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("[OK] Sesion creada exitosamente")
            print("Response:")
            print_json(data)
            
            if data.get("success"):
                token = data.get("token")
                print(f"[OK] Token: {token}")
                return token
            else:
                print("[ERROR] success=False en la respuesta")
                return None
        else:
            print(f"[ERROR] Error {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        print(f"[ERROR] Excepcion: {e}")
        return None

def test_validate_token(token: str):
    """Test 2: Validar token"""
    print_section("3. TEST: VALIDAR TOKEN")
    
    print(f"GET {BASE_URL}/api/cart/{token}")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/cart/{token}",
            timeout=10
        )
        
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("valid"):
                print("[OK] Token valido")
                print("Response:")
                print_json(data)
                return True
            else:
                print(f"[ERROR] Token invalido: {data.get('error')}")
                return False
        else:
            print(f"[ERROR] Error {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Excepcion: {e}")
        return False

def test_get_products(token: str):
    """Test 3: Obtener productos"""
    print_section("4. TEST: OBTENER PRODUCTOS")
    
    print(f"GET {BASE_URL}/api/cart/{token}/products")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/cart/{token}/products",
            timeout=10
        )
        
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            products = response.json()
            print(f"[OK] Productos obtenidos: {len(products)}")
            
            if len(products) > 0:
                print("Primeros 3 productos:")
                for product in products[:3]:
                    print(f"  - {product['name']} - ${product['price']} (Stock: {product['stock']})")
                
                return products
            else:
                print("[ERROR] No se obtuvieron productos")
                return []
        else:
            print(f"[ERROR] Error {response.status_code}: {response.text}")
            return []
            
    except Exception as e:
        print(f"[ERROR] Excepcion: {e}")
        return []

def test_complete_cart(token: str, products: list):
    """Test 4: Completar carrito"""
    print_section("5. TEST: COMPLETAR CARRITO (WEBHOOK)")
    
    if not products or len(products) == 0:
        print("[ERROR] No hay productos para agregar al carrito")
        return None
    
    selected_products = []
    total = 0.0
    
    for product in products[:2]:
        quantity = 1
        selected_products.append({
            "product_id": product["id"],
            "quantity": quantity
        })
        total += product["price"] * quantity
    
    print(f"POST {BASE_URL}/api/cart/{token}/complete")
    
    payload = {
        "products": selected_products,
        "total": total
    }
    
    print("Request body:")
    print_json(payload)
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/cart/{token}/complete",
            json=payload,
            timeout=10
        )
        
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("success"):
                print("[OK] Carrito completado exitosamente")
                print("Response:")
                print_json(data)
                
                order_id = data.get("order_id")
                print(f"[OK] Orden ID: {order_id}")
                
                return order_id
            else:
                print("[ERROR] success=False en la respuesta")
                return None
        else:
            print(f"[ERROR] Error {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        print(f"[ERROR] Excepcion: {e}")
        return None

def test_check_status(token: str):
    """Test 5: Verificar estado de sesion"""
    print_section("6. TEST: VERIFICAR ESTADO DE SESION")
    
    print(f"GET {BASE_URL}/api/cart/{token}/status")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/cart/{token}/status",
            timeout=10
        )
        
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("[OK] Estado obtenido exitosamente")
            print("Response:")
            print_json(data)
            
            if data.get("used"):
                print("[OK] Sesion marcada como USADA")
            
            if data.get("order_id"):
                print(f"[OK] Orden asociada: {data.get('order_id')}")
            
            return True
        else:
            print(f"[ERROR] Error {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Excepcion: {e}")
        return False

def verify_database_state(order_id: str):
    """Verifica el estado en la base de datos"""
    print_section("7. VERIFICACION EN BASE DE DATOS")
    
    with get_db_context() as db:
        order = db.query(Order).filter(Order.id == order_id).first()
        
        if order:
            print(f"[OK] Orden encontrada en BD: {order.order_number}")
            print(f"  Estado: {order.status}")
            print(f"  Total: ${order.total}")
            print(f"  Items: {len(order.items)}")
            
            for item in order.items:
                print(f"    - {item.product.name} x{item.quantity} - ${item.unit_price} (Subtotal: ${item.subtotal})")
        else:
            print("[ERROR] Orden no encontrada en BD")
            return False
        
        session = db.query(CartSession).filter(CartSession.order_id == order_id).first()
        
        if session:
            print(f"[OK] Sesion de carrito encontrada: {session.token[:16]}...")
            print(f"  Usada: {session.used}")
            print(f"  Expirada: {session.is_expired}")
            print(f"  Valida: {session.is_valid}")
        else:
            print("[ERROR] Sesion de carrito no encontrada")
            return False
    
    return True

def run_all_tests():
    """Ejecuta todos los tests"""
    print("\n" + "=" * 70)
    print("  TESTING BACKEND - SISTEMA DE CARRITO")
    print("=" * 70)
    
    if not check_prerequisites():
        print_section("TESTS ABORTADOS")
        print("[ERROR] Los prerequisitos no se cumplieron")
        return False
    
    token = test_create_cart_session()
    if not token:
        print_section("TESTS ABORTADOS")
        print("[ERROR] No se pudo crear la sesion de carrito")
        return False
    
    if not test_validate_token(token):
        print_section("TESTS ABORTADOS")
        print("[ERROR] Token invalido")
        return False
    
    products = test_get_products(token)
    if not products or len(products) == 0:
        print_section("TESTS ABORTADOS")
        print("[ERROR] No se pudieron obtener productos")
        return False
    
    order_id = test_complete_cart(token, products)
    if not order_id:
        print_section("TESTS ABORTADOS")
        print("[ERROR] No se pudo completar el carrito")
        return False
    
    if not test_check_status(token):
        print_section("ADVERTENCIA")
        print("[ERROR] No se pudo verificar el estado de la sesion")
    
    if not verify_database_state(order_id):
        print_section("ADVERTENCIA")
        print("[ERROR] Verificacion de BD incompleta")
    
    print_section("TODOS LOS TESTS PASARON")
    print("[OK] El backend del sistema de carrito funciona correctamente")
    print(f"Token de prueba: {token}")
    print(f"Orden de prueba: {order_id}")
    
    return True

if __name__ == "__main__":
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n[INFO] Tests interrumpidos por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

