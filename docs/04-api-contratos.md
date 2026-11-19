# 04 — Contratos de API y endpoints

> Entregable 10. Backend FastAPI. Base local: `http://localhost:8000`. OpenAPI automático en `/docs`.
> Todas las respuestas JSON. Errores con formato único:
> ```json
> {"error": {"code": "PRODUCT_NOT_FOUND", "message": "Producto no encontrado", "details": {}}}
> ```
> Dinero: string decimal con 2 decimales (`"649.00"`), moneda fija `USD`.

## Autenticación
- Endpoints públicos `/api/*`: sin auth, con CORS restringido a `FRONTEND_ORIGIN` y rate limit simple en memoria (60 req/min/IP).
- Endpoints `/admin/*`: header `X-Admin-Key: <ADMIN_API_KEY>`. 401 si falta o no coincide.
- Webhook Telegram: `POST /telegram/webhook/{TELEGRAM_WEBHOOK_SECRET}` + header `X-Telegram-Bot-Api-Secret-Token` igual a `TELEGRAM_WEBHOOK_SECRET` (Telegram lo envía si se configura con `secret_token` en `setWebhook`).

## Salud
| Método | Ruta | Respuesta |
|---|---|---|
| GET | `/health` | `{"status":"ok","db":"ok","ai_mode":"mock","storage":"local","version":"0.1.0"}` |

## Catálogo (público)

### GET `/api/categories`
```json
[{"id":1,"slug":"sofas","name":"Sofás","product_count":1}]
```

### GET `/api/products`
Query: `category` (slug), `q` (texto en nombre/descripción), `min_price`, `max_price`, `room` (`sala`…), `in_stock` (bool), `limit` (≤50, default 20), `offset`.
```json
{
  "items": [{
    "id": 1, "sku": "DS-SOF-001", "slug": "sofa-oslo-3-plazas", "name": "Sofá Oslo 3 plazas",
    "category": {"slug": "sofas", "name": "Sofás"},
    "price": "649.00", "currency": "USD", "stock": 8, "in_stock": true, "low_stock": false,
    "dimensions": {"width_cm": 210, "height_cm": 85, "depth_cm": 90},
    "colors": ["gris","beige","azul petróleo"], "material": "Tela y madera", "style": "nordico",
    "room_types": ["sala"], "primary_image": "/media/products/sofa-oslo.jpg"
  }],
  "total": 6, "limit": 20, "offset": 0
}
```

### GET `/api/products/{id_or_slug}`
Producto completo (lo anterior + `description`, `images: [{url, alt}]`). 404 `PRODUCT_NOT_FOUND`.
Registra una `inquiry` tipo `product_info`, canal `web` (sin cliente).

## Cotizaciones y pedidos (público, web)

### POST `/api/quotes`
```json
{
  "customer": {"name":"Ana Pérez","email":"ana@example.com","phone":"+51999999999"},
  "items": [{"product_id":1,"quantity":1},{"product_id":2,"quantity":2}],
  "notes": "Entrega en Lima",
  "channel": "web"
}
```
Respuesta 201:
```json
{"code":"COT-20261118-0001","status":"sent","items":[{"product_id":1,"name":"Sofá Oslo 3 plazas","quantity":1,"unit_price":"649.00","line_total":"649.00"}],
 "subtotal":"947.00","total":"947.00","currency":"USD","valid_until":"2026-11-25",
 "disclaimer":"Cotización referencial. Precios sujetos a stock al momento de confirmar."}
```
Errores: 422 validación; 409 `INSUFFICIENT_STOCK` (`details.product_id`, `details.available`); 404 `PRODUCT_NOT_FOUND`.
Efectos: crea customer (dedupe por email), quote + items con precio congelado, evento `quote.created`.

### GET `/api/quotes/{code}`
Devuelve la cotización (público por código; no expone datos de contacto).

### POST `/api/orders`
```json
{
  "quote_code": "COT-20261118-0001",
  "customer": {"name":"Ana Pérez","email":"ana@example.com","phone":"+51999999999"},
  "items": [{"product_id":1,"quantity":1}],
  "delivery_address": "Av. Siempre Viva 123",
  "channel": "web"
}
```
`quote_code` o `items` (al menos uno). Si viene `quote_code`, se usan sus ítems y precios.
Respuesta 201: `{"code":"PED-20261118-0001","status":"pending","total":"649.00","is_demo":true,"message":"Pedido de demostración registrado. No se realizó ningún cobro."}`
Efectos: evento `order.created` → notificación al admin por Telegram.

### GET `/api/orders/{code}`
Estado público del pedido.

## Contacto
### GET `/api/config/public`
`{"telegram_bot_url":"https://t.me/DecoSmartBot","store_name":"DecoSmart","currency":"USD"}`

## Media
### GET `/media/{key:path}`
Solo con `STORAGE_BACKEND=local`: sirve archivos de `LOCAL_STORAGE_PATH`. Con `s3`, las URLs públicas de productos apuntan a `S3_PUBLIC_BASE_URL` y las fotos de clientes **no** son públicas (se sirven por URL prefirmada de 10 min solo al admin).

## Telegram
### POST `/telegram/webhook/{secret}`
Cuerpo: objeto `Update` de Telegram. Responde siempre `200 {"ok":true}` rápido; el procesamiento se hace en `BackgroundTasks`. 403 si el secreto no coincide.

## Admin (`X-Admin-Key`)

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/admin/metrics/summary?from=&to=` | KPIs agregados (ver abajo) |
| GET | `/admin/metrics/daily?days=14` | Serie diaria: conversations, inquiries, quotes, orders, simulations |
| GET | `/admin/metrics/top-products?kind=inquired\|requested&limit=5` | inquired = por `inquiries`; requested = por cantidad en `quote_items` + `order_items` |
| GET | `/admin/usage?days=30` | Consumo: total USD, por operación, por modelo, por día, `% del presupuesto` |
| GET | `/admin/events?type=&limit=50&offset=0` | Historial de eventos |
| GET | `/admin/errors?limit=50` | Errores de procesamiento |
| GET | `/admin/simulations?limit=20` | Simulaciones con calificación y URL de resultado |
| GET | `/admin/quotes?status=` / `/admin/orders?status=` | Listados |
| PATCH | `/admin/quotes/{code}` | `{"status":"accepted"}` — valida transición |
| PATCH | `/admin/orders/{code}` | `{"status":"confirmed"}` — al confirmar descuenta stock y evalúa stock bajo |
| PATCH | `/admin/products/{id}` | `{"stock": 10, "price": "599.00", "active": true}` |
| POST | `/admin/jobs/daily-summary` | Genera y envía resumen al admin (también lo dispara el scheduler) |
| POST | `/admin/jobs/cleanup-photos` | Borra fotos de clientes más antiguas que `PHOTO_RETENTION_DAYS` |

### `/admin/metrics/summary`
```json
{
  "conversations_total": 42, "unique_customers": 18,
  "inquiries_total": 120, "quotes_total": 15, "quotes_accepted": 4,
  "orders_total": 6, "orders_completed": 2,
  "simulations_total": 9, "simulations_failed": 1, "simulations_reused": 2,
  "avg_rating": 4.2, "ratings_count": 7,
  "api_cost_usd": "0.4123", "budget_usd": "3.50", "budget_used_pct": 11.8,
  "errors_total": 3, "ai_mode": "live"
}
```

### Transiciones válidas
- Quote: `draft→sent`, `sent→accepted|rejected|expired`. Otras → 409 `INVALID_TRANSITION`.
- Order: `pending→confirmed|cancelled`, `confirmed→completed|cancelled`.
- Simulation: definida en el handoff (no editable por API pública).

## Códigos de error
`VALIDATION_ERROR` (422), `PRODUCT_NOT_FOUND`, `QUOTE_NOT_FOUND`, `ORDER_NOT_FOUND` (404), `INSUFFICIENT_STOCK`, `INVALID_TRANSITION` (409), `UNAUTHORIZED` (401), `RATE_LIMITED` (429), `BUDGET_EXCEEDED` (402, solo interno/admin), `INTERNAL_ERROR` (500).
