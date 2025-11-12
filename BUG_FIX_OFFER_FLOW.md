# 🐛 Bug Fix: Flujo de Ofrecimientos de Productos

**Fecha**: 2025-11-10

## 📋 Resumen

Se identificaron y resolvieron 3 bugs críticos en el flujo de ofrecimientos de productos que impedían el correcto funcionamiento de la funcionalidad:

## 🔴 Bugs Identificados

### Bug #1: Error al agregar producto ofrecido a orden PENDING

**Síntoma**: 
```
❌ Error: Solo se pueden agregar items a órdenes confirmadas. Estado actual: pending
```

**Causa**: 
Cuando se hacía un ofrecimiento de producto, la orden se creaba en estado `PENDING` para esperar la respuesta del usuario. Al aceptar el ofrecimiento, `OfferProductModule` intentaba agregar el producto usando `add_items_to_order()`, que requiere que la orden esté en estado `CONFIRMED`.

**Solución**:
Modificar `OfferProductModule.handle()` para que **primero confirme la orden PENDING** y luego agregue el producto adicional.

```python
# Obtener la orden
order = db.query(Order).filter(Order.id == pending_order_id).first()

# Si la orden está PENDING, confirmarla primero
if order.status == "pending":
    logger.info(f"✅ Confirmando orden PENDING antes de agregar producto adicional")
    order = order_service.confirm_order(order.id)

# Ahora agregar el producto adicional
items = [{
    "product_id": offered_product["product_id"],
    "quantity": 1
}]
order = order_service.add_items_to_order(order.id, items)
```

---

### Bug #2: Error de constraint en base de datos (content=NULL)

**Síntoma**:
```
sqlite3.IntegrityError: NOT NULL constraint failed: messages.content
```

**Causa**: 
Cuando se enviaba un ofrecimiento con imagen, el módulo retornaba `response=None` (porque el mensaje ya fue enviado por el helper). Sin embargo, `sync_worker` intentaba guardar este mensaje en la base de datos con `content=None`, violando la constraint NOT NULL de la columna `content`.

**Solución**:
Modificar `sync_worker` para **solo guardar el mensaje si `response is not None`**.

```python
# 7. Guardar respuesta del bot (si hay respuesta)
if response is not None:
    with get_db_context() as db:
        context_manager = ContextManager(db)
        context_manager.save_message(
            phone=phone,
            content=response,
            message_type="text",
            is_from_bot=True
        )
```

---

### Bug #3: Bot no detecta que debe usar OfferProductModule

**Síntoma**:
- Usuario pide un producto después de tener `waiting_offer_response=True` de un ofrecimiento anterior
- Bot detecta intent `create_order` en lugar de usar `OfferProductModule`
- Bot completa automáticamente ubicación y pago con valores de orden anterior
- Bot hace un nuevo ofrecimiento sin procesar el mensaje del usuario

**Causa**: 
El contexto tenía `waiting_offer_response=True` (de un ofrecimiento anterior mal limpiado) pero `current_module=None`. Cuando el usuario respondía, el bot no detectaba que debía usar `OfferProductModule` y en su lugar detectaba el intent como `create_order`.

**Solución**:
Agregar lógica en `sync_worker` para **forzar `OfferProductModule` si `waiting_offer_response=True`** y no hay módulo activo.

```python
# CASO ESPECIAL: Si waiting_offer_response=True, forzar OfferProductModule
if module_context.get('waiting_offer_response') and not module_context.get('current_module'):
    logger.info(f"🎁 [Worker] Detectado waiting_offer_response=True sin current_module, forzando OfferProductModule")
    module_context['current_module'] = 'OfferProductModule'

active_module = registry.get_module_by_context(module_context)
```

---

## 📁 Archivos Modificados

### 1. `app/modules/offer_product_module.py`
- Agregado lógica para confirmar orden PENDING antes de agregar productos
- Agregado import de `Order` model
- Agregado logging detallado del estado de la orden

### 2. `app/services/sync_worker.py`
- Modificado para solo guardar mensajes si `response is not None`
- Agregado detección automática de `OfferProductModule` cuando `waiting_offer_response=True`

---

## ✅ Resultados

- ✅ Los ofrecimientos ahora se procesan correctamente
- ✅ La orden se confirma antes de agregar el producto ofrecido
- ✅ No más errores de constraint en la base de datos
- ✅ El bot detecta correctamente que debe usar `OfferProductModule` para respuestas a ofrecimientos
- ✅ El flujo de ofrecimientos es robusto ante estados residuales de conversaciones anteriores

---

## 🧪 Flujo Esperado (Después del Fix)

### Flujo Exitoso:
1. **Usuario**: "quiero ordenar un mouse"
2. **Bot**: Procesa orden (producto + ubicación GPS + pago)
3. **Bot**: Crea orden en estado PENDING
4. **Bot**: Selecciona producto para ofrecer (ej: Audífonos)
5. **Bot**: Envía ofrecimiento con imagen
6. **Bot**: Marca `waiting_offer_response=True` y `current_module=OfferProductModule`
7. **Usuario**: "si"
8. **Bot**: Detecta que debe usar `OfferProductModule` (gracias al fix #3)
9. **Bot**: Confirma la orden PENDING (fix #1)
10. **Bot**: Agrega los Audífonos a la orden confirmada
11. **Bot**: Envía resumen de orden completa

### Protección contra estados residuales:
- Si `waiting_offer_response=True` pero `current_module=None` (de conversación anterior mal limpiada)
- El bot automáticamente fuerza `OfferProductModule` (fix #3)
- No se activa la lógica de `adding_to_existing_order`

---

## 🔍 Notas Técnicas

### ¿Por qué la orden se crea en PENDING?
Cuando se hace un ofrecimiento después de crear la orden, **no se confirma inmediatamente** para permitir que el usuario acepte o rechace el producto adicional. Si se confirmara antes, el usuario recibiría una confirmación prematura.

### ¿Por qué no usar create_order + agregar producto después?
El flujo actual es más eficiente: 
1. Crea la orden con el producto inicial
2. Ofrece un producto adicional
3. Si acepta: confirma + agrega adicional
4. Si rechaza: solo confirma

Esto evita múltiples transacciones y actualizaciones de stock.

---

## 📚 Documentos Relacionados

- `PRODUCT_OFFERS_FEATURE.md`: Documentación completa del módulo de ofrecimientos
- `BUG_FIX_MODULE_LOST.md`: Fix anterior de pérdida de contexto
- `ADD_TO_ORDER_FEATURE.md`: Feature de agregar productos a órdenes existentes


