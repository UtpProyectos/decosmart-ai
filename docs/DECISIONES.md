# Decisiones

## Decisiones durante la implementación

### feat/backend-core
- **Búsqueda de catálogo**: los filtros de precio, categoría, stock y `active` se hacen en SQL. El texto libre y `room` (lista JSON) se filtran en Python, sin distinguir acentos y con un plural simple. El texto se parte en palabras y los resultados se ordenan por número de coincidencias (basta una). El catálogo es pequeño y así funciona igual en SQLite y en Postgres.
- **`primary_image`**: se devuelve la URL guardada (`/static/products/<archivo>`), no `/media/products/...` como dice el ejemplo de doc 04. Las imágenes del catálogo no pasan por el storage.
- **Stock bajo**: `catalog.evaluate_low_stock()` emite `product.low_stock` solo si `Product.low_stock_notified` es falso y fija el flag. El flag se reinicia cuando el stock vuelve a superar `LOW_STOCK_THRESHOLD`.
- **Pedido desde cotización**: usa el cliente de la cotización; el `customer` del body solo da los datos de contacto. Una cotización vencida o que no está en estado `sent` → 409 `INVALID_TRANSITION`. Al crear el pedido se valida el stock, pero no se descuenta.
- **Conversación nueva**: si la anterior lleva más de 6 h inactiva (no se corta al cambiar de día).
- **`budget.warning`**: se emite una vez por umbral, en `BUDGET_WARN_PCT` y en 100 %.
- **Límite de mensajes LLM por cliente**: cuenta las filas `api_usage` de chat del día local, en cualquier modo (mock o live).
- **`/admin/metrics/daily`**: devuelve una lista `[{date, conversations, inquiries, quotes, orders, simulations}]` con ceros en los días sin datos.
- **`/admin/usage`**: los costos se dan como strings con 4 decimales. Se añaden `avg_cost_per_simulation`, `avg_cost_per_conversation`, `spent_live_usd` y `failed_calls`.
- **Resumen diario**: es idempotente por día local, salvo con `?force=true`. El handler de `summary.daily` es quien envía el texto al admin.
- **Endpoints admin extra**: `GET /admin/products` y `POST /admin/jobs/expire-quotes`.
- **Storage S3**: compatible con la API S3 de Supabase Storage (path-style, `region_name=S3_REGION`), con URLs prefirmadas.
