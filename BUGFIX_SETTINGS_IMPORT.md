# 🐛 BugFix: Import de settings faltante en CreateOrderModule

## 📋 Error Reportado

```
11:00:46 | INFO     | app.services.order_service:create_order - ✅ Orden creada: ORD-20251110-001
2025-11-10 11:00:46,114 INFO sqlalchemy.engine.Engine ROLLBACK
11:00:46 | ERROR    | config.database:get_db_context - Error en transacción DB: name 'settings' is not defined
11:00:46 | ERROR    | app.modules.create_order_module:_create_order - ❌ [CreateOrderModule] Error creando orden: name 'settings' is not defined
```

---

## 🔍 Causa Raíz

Al implementar el módulo de ofrecimientos de productos, agregamos código en `_create_order()` que usa `settings`:

```python
# Línea 694 en create_order_module.py
if settings.enable_product_offers and settings.offer_after_order:
    ...
```

Sin embargo, **NO importamos `settings`** al inicio del archivo.

---

## ✅ Solución

Agregar el import faltante:

```python
from config.settings import settings
```

---

## 📂 Archivo Modificado

**`app/modules/create_order_module.py`**

**ANTES:**
```python
from typing import Dict, Any, Optional
from loguru import logger
from config.database import get_db_context
from app.core.slots import SlotDefinition, SlotType, SlotManager
from app.services.product_service import ProductService
from app.services.order_service import OrderService
```

**DESPUÉS:**
```python
from typing import Dict, Any, Optional
from loguru import logger
from config.database import get_db_context
from config.settings import settings  # ← NUEVO
from app.core.slots import SlotDefinition, SlotType, SlotManager
from app.services.product_service import ProductService
from app.services.order_service import OrderService
```

---

## ✅ Verificación

- [x] Import agregado
- [x] Sin errores de linter
- [x] Código funcional

---

**¡Bug resuelto!** Las órdenes ahora se crean correctamente con el sistema de ofrecimientos. ✅


