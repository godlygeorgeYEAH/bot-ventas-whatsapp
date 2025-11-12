"""
Servicio para operaciones con productos
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from app.database.models import Product
from loguru import logger


class ProductService:
    """Servicio para gestionar productos"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_all_products(
        self, 
        category: Optional[str] = None,
        only_available: bool = True
    ) -> List[Product]:
        """
        Obtiene todos los productos
        
        Args:
            category: Filtrar por categoría
            only_available: Solo productos activos y con stock
        """
        query = self.db.query(Product)
        
        if only_available:
            query = query.filter(
                Product.is_active == True,
                Product.stock > 0
            )
        
        if category:
            query = query.filter(Product.category == category)
        
        products = query.order_by(Product.name).all()
        
        logger.info(f"📦 Obtenidos {len(products)} productos" + 
                   (f" de categoría '{category}'" if category else ""))
        
        return products
    
    def get_product_by_id(self, product_id: str) -> Optional[Product]:
        """Obtiene un producto por ID"""
        product = self.db.query(Product).filter(Product.id == product_id).first()
        
        if product:
            logger.info(f"✅ Producto encontrado: {product.name}")
        else:
            logger.warning(f"❌ Producto no encontrado: {product_id}")
        
        return product
    
    def get_product_by_sku(self, sku: str) -> Optional[Product]:
        """Obtiene un producto por SKU"""
        return self.db.query(Product).filter(Product.sku == sku).first()
    
    def search_products(self, search_term: str) -> List[Product]:
        """
        Busca productos por nombre (fuzzy matching)
        
        Args:
            search_term: Término de búsqueda
        """
        search_term = search_term.lower().strip()
        
        # Búsqueda flexible en nombre y descripción
        products = self.db.query(Product).filter(
            Product.is_active == True,
            Product.stock > 0,
            or_(
                func.lower(Product.name).contains(search_term),
                func.lower(Product.description).contains(search_term),
                func.lower(Product.category).contains(search_term)
            )
        ).order_by(Product.name).all()
        
        logger.info(f"🔍 Búsqueda '{search_term}': {len(products)} resultados")
        
        return products
    
    def get_product_by_name_fuzzy(self, name: str) -> Optional[Product]:
        """
        Encuentra un producto por nombre con matching flexible
        
        Args:
            name: Nombre del producto a buscar
        """
        name_lower = name.lower().strip()
        
        # Búsqueda exacta primero
        exact = self.db.query(Product).filter(
            Product.is_active == True,
            func.lower(Product.name) == name_lower
        ).first()
        
        if exact:
            logger.info(f"✅ Match exacto: {exact.name}")
            return exact
        
        # Búsqueda flexible
        fuzzy = self.db.query(Product).filter(
            Product.is_active == True,
            func.lower(Product.name).contains(name_lower)
        ).first()
        
        if fuzzy:
            logger.info(f"✅ Match parcial: '{name}' → {fuzzy.name}")
            return fuzzy
        
        # Si no encuentra, buscar en descripción
        in_description = self.db.query(Product).filter(
            Product.is_active == True,
            func.lower(Product.description).contains(name_lower)
        ).first()
        
        if in_description:
            logger.info(f"✅ Match en descripción: '{name}' → {in_description.name}")
            return in_description
        
        logger.warning(f"❌ No se encontró producto para: '{name}'")
        return None
    
    def check_stock(self, product_id: str, quantity: int) -> bool:
        """
        Verifica si hay stock suficiente
        
        Args:
            product_id: ID del producto
            quantity: Cantidad requerida
        """
        product = self.get_product_by_id(product_id)
        
        if not product:
            return False
        
        has_stock = product.stock >= quantity
        
        if has_stock:
            logger.info(f"✅ Stock suficiente: {product.name} ({product.stock} disponibles)")
        else:
            logger.warning(f"❌ Stock insuficiente: {product.name} (solo {product.stock} disponibles)")
        
        return has_stock
    
    def get_categories(self) -> List[str]:
        """Obtiene todas las categorías de productos"""
        categories = self.db.query(Product.category).distinct().all()
        return [cat[0] for cat in categories if cat[0]]
    
    def format_product_list(self, products: List[Product]) -> str:
        """
        Formatea una lista de productos para mostrar al usuario
        
        Returns:
            String formateado con productos
        """
        if not products:
            return "No hay productos disponibles."
        
        lines = []
        for i, product in enumerate(products, 1):
            stock_info = f"({product.stock} disponibles)" if product.stock < 10 else ""
            lines.append(f"{i}. {product.name} - ${product.price:.2f} {stock_info}")
        
        return "\n".join(lines)
    
    def update_stock(self, product_id: str, quantity_change: int):
        """
        Actualiza el stock de un producto
        
        Args:
            product_id: ID del producto
            quantity_change: Cambio en cantidad (positivo o negativo)
        """
        product = self.get_product_by_id(product_id)
        
        if not product:
            raise ValueError(f"Producto no encontrado: {product_id}")
        
        new_stock = product.stock + quantity_change
        
        if new_stock < 0:
            raise ValueError(f"Stock no puede ser negativo: {product.name}")
        
        product.stock = new_stock
        self.db.commit()
        
        logger.info(f"📊 Stock actualizado: {product.name} → {new_stock}")

    # Actualizar el método format_product_detail:

    def format_product_detail(self, product: Product, include_image: bool = False) -> dict:
        """
        Formatea un producto con todos sus detalles
        
        Args:
            product: Producto a formatear
            include_image: Si True, incluye path de imagen
            
        Returns:
            Dict con texto formateado y path de imagen (opcional)
        """
        text = f"""*{product.name}*

    {product.description}

    💰 Precio: ${product.price:.2f}
    📦 Stock disponible: {product.stock} unidades"""

        if product.stock < 5:
            text += f"\n⚠️ ¡Pocas unidades disponibles!"
        
        result = {
            "text": text,
            "product_id": product.id,
            "has_image": product.has_image  # Usa la property del modelo
        }
        
        if include_image and product.image_path:
            result["image_path"] = product.image_path
        
        return result


    def format_product_list_with_images(self, products: List[Product]) -> dict:
        """
        Formatea lista de productos indicando cuáles tienen imagen
        
        Returns:
            Dict con texto y lista de productos con imágenes
        """
        if not products:
            return {"text": "No hay productos disponibles.", "products": []}
        
        lines = ["*Productos disponibles:*\n"]
        products_with_images = []
        
        for i, product in enumerate(products, 1):
            has_image = "📸" if product.has_image else ""
            stock_info = f"({product.stock} disponibles)" if product.stock < 10 else ""
            lines.append(f"{i}. {product.name} - ${product.price:.2f} {stock_info} {has_image}")
            
            if product.has_image:
                products_with_images.append({
                    "id": product.id,
                    "name": product.name,
                    "image_path": product.image_path
                })
        
        return {
            "text": "\n".join(lines),
            "products": products_with_images
        }