# CODEX_HANDOFF — Documento técnico de traspaso

> Fuente única de verdad para implementar **DECOSMART AI**. Si un documento contradice a este, manda este.
> Complementos obligatorios: `03-modelo-datos.md` (tablas), `04-api-contratos.md` (endpoints), `05-agente-ia-prompts.md` (tools y prompts), `07-presupuesto-costos.md` (costos).
> Fecha de decisiones: 2026-11-18.

---

## 1. Qué se construye (resumen)

1. **Tienda web** React: catálogo de 6 muebles, detalle, carrito (localStorage), cotización, pedido demo, botón Telegram.
2. **Backend** FastAPI: API pública + admin, BD PostgreSQL, bot de Telegram integrado, agente IA con herramientas, simulador de imágenes, automatizaciones, control de presupuesto.
3. **Dashboard** Streamlit: KPIs consumiendo `/admin/*`.
4. **DevOps**: Docker Compose local, GitHub Actions (CI + deploy), Render (prod), Supabase Postgres (BD), Supabase Storage (imágenes, API S3).

Clasificación:
- **Implementable (MVP)**: todo lo de este documento salvo lo marcado.
- **Experimental**: simulación visual con IA (calidad variable; orientativa), n8n opcional, `IMAGE_SIZE=auto`.
- **Futuro (no implementar)**: pagos reales, login de clientes, AR/VR, multi-idioma, panel admin CRUD completo, recomendación por embeddings, WhatsApp.

---

## 2. Estructura del repositorio

```
decosmart-ai/
├── AGENTS.md
├── README.md
├── .env.example
├── docker-compose.yml
├── render.yaml
├── .github/workflows/
│   ├── ci.yml                 # lint + tests + build en PR y push
│   ├── deploy.yml             # en push a main tras CI: dispara deploy hooks de Render
│   └── daily-summary.yml      # cron diario: POST /admin/jobs/daily-summary
├── docs/                      # toda la documentación (este archivo incluido)
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── pyproject.toml         # config ruff + pytest
│   ├── alembic.ini
│   ├── alembic/versions/
│   ├── seed/
│   │   ├── products.json
│   │   └── images/            # imágenes de producto (catálogo + referencia limpia)
│   ├── app/
│   │   ├── main.py            # create_app(): routers, CORS, handlers de error, lifespan (scheduler, polling)
│   │   ├── core/
│   │   │   ├── config.py      # Settings (pydantic-settings), única lectura de env
│   │   │   ├── db.py          # engine, SessionLocal, get_db
│   │   │   ├── errors.py      # AppError(code, message, status, details) + handler
│   │   │   ├── pricing.py     # tabla de precios OpenAI + estimate_*()
│   │   │   ├── security.py    # require_admin, rate limiter en memoria
│   │   │   └── logging.py
│   │   ├── models/            # SQLAlchemy (un archivo por agregado)
│   │   ├── schemas/           # Pydantic I/O
│   │   ├── api/
│   │   │   ├── public.py      # /api/*
│   │   │   ├── admin.py       # /admin/*
│   │   │   ├── telegram.py    # /telegram/webhook/{secret}
│   │   │   └── media.py       # /media/* (solo storage local)
│   │   ├── services/
│   │   │   ├── catalog.py     # búsqueda, detalle, stock, recomendación
│   │   │   ├── customers.py
│   │   │   ├── inquiries.py
│   │   │   ├── quotes.py
│   │   │   ├── orders.py
│   │   │   ├── budget.py      # guardia de presupuesto + registro api_usage
│   │   │   ├── metrics.py     # consultas para dashboard
│   │   │   └── codes.py       # COT-/PED- correlativos
│   │   ├── storage/
│   │   │   ├── base.py        # Storage protocol: put(key, bytes, content_type), get(key), url(key, public), delete(key)
│   │   │   ├── local.py
│   │   │   └── s3.py          # boto3, compatible S3 (Supabase Storage)
│   │   ├── imaging/
│   │   │   └── pipeline.py    # optimize_input(), optimize_output(), sha256
│   │   ├── ai/
│   │   │   ├── provider.py    # AIProvider protocol + get_provider()
│   │   │   ├── openai_provider.py
│   │   │   └── mock_provider.py
│   │   ├── agent/
│   │   │   ├── prompts.py
│   │   │   ├── tools.py       # schemas + dispatch a services
│   │   │   ├── guard.py       # validador anti-alucinación
│   │   │   └── runner.py      # run_agent_turn(conversation, text) -> AgentReply
│   │   ├── simulation/
│   │   │   └── service.py     # flujo completo, cuotas, caché, llamada a provider
│   │   ├── bot/
│   │   │   ├── client.py      # TelegramClient (httpx): send_message, send_photo, edit_reply_markup, get_file, download, answer_callback, set_webhook, get_updates
│   │   │   ├── handlers.py    # handle_update(update: dict) → máquina de estados
│   │   │   ├── keyboards.py
│   │   │   ├── texts.py       # mensajes fijos (doc 05 §6)
│   │   │   └── polling.py     # bucle getUpdates para local
│   │   └── automation/
│   │       ├── events.py      # emit(db, type, ...) + dispatch síncrono a handlers registrados
│   │       ├── handlers.py    # reacciones: notificar admin, enviar cotización, stock bajo, n8n
│   │       └── scheduler.py   # APScheduler: resumen diario, expirar cotizaciones, limpiar fotos
│   ├── scripts/
│   │   ├── seed.py            # idempotente
│   │   └── set_webhook.py
│   └── tests/
├── frontend/
│   ├── Dockerfile             # build Vite → nginx
│   ├── nginx.conf
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── main.tsx, App.tsx (react-router)
│       ├── api/client.ts      # fetch a VITE_API_URL
│       ├── store/cart.ts      # zustand + persist (localStorage)
│       ├── pages/ Home, Catalog, ProductDetail, Cart, QuoteRequest, QuoteResult, Checkout, OrderConfirmation, NotFound
│       ├── components/ Header, Footer, ProductCard, CategoryFilter, TelegramButton, PriceTag, StockBadge, DimensionList
│       └── styles/            # CSS Modules o CSS plano con variables; sin framework pesado
└── dashboard/
    ├── Dockerfile
    ├── requirements.txt
    ├── app.py                 # página principal (KPIs)
    ├── api.py                 # cliente HTTP con X-Admin-Key, st.cache_data(ttl=30)
    └── pages/ 1_Conversaciones.py, 2_Productos.py, 3_Simulaciones.py, 4_Costos_API.py, 5_Eventos_y_Errores.py
```

---

## 3. Stack y versiones (fijar en requirements / package.json)

| Pieza | Versión |
|---|---|
| Python | 3.11 |
| fastapi | ≥0.115 · uvicorn[standard] ≥0.32 |
| sqlalchemy | 2.0.x (**síncrono**) · psycopg[binary] 3.2 · alembic 1.14 |
| pydantic | 2.x · pydantic-settings 2.x |
| openai | ≥1.60 (SDK oficial; Responses API + images.edit) |
| httpx | 0.27+ (cliente Telegram) |
| pillow | 11.x |
| boto3 | 1.35+ |
| apscheduler | 3.10.x |
| tests | pytest, pytest-cov, respx (mock httpx), ruff |
| Node | 20 LTS · React 18 · Vite 5 · TypeScript 5 · react-router-dom 6 · zustand 4 · vitest + @testing-library/react · eslint |
| Streamlit | 1.40+ · pandas · plotly (o gráficos nativos `st.bar_chart`/`st.line_chart`) |
| PostgreSQL | 16 |

**Telegram**: no usar `python-telegram-bot`; cliente propio fino con `httpx` sobre la Bot API (`https://api.telegram.org/bot<TOKEN>/<method>`). Motivo: un solo modelo de ejecución (webhook FastAPI o polling) y tests simples con `respx`.

**Concurrencia**: endpoints sync. El webhook responde 200 y procesa el update en `BackgroundTasks` (threadpool). La generación de imagen corre en ese mismo background task (hasta ~60 s; aceptable). Polling local: hilo daemon iniciado en `lifespan` si `TELEGRAM_MODE=polling`.

---

## 4. Variables de entorno (`.env.example`)

```dotenv
# --- General ---
APP_ENV=development                 # development | production | test
APP_VERSION=0.1.0
LOG_LEVEL=INFO
FRONTEND_ORIGIN=http://localhost:5173
PUBLIC_BASE_URL=http://localhost:8000   # URL pública del backend (para webhook y media)

# --- Base de datos ---
# Supabase (session pooler, puerto 5432, IPv4). Local opcional: postgresql+psycopg://decosmart:decosmart@db:5432/decosmart (--profile localdb)
DATABASE_URL=postgresql+psycopg://postgres.<PROJECT_REF>:<PASSWORD>@aws-0-<REGION>.pooler.supabase.com:5432/postgres?sslmode=require
AUTO_MIGRATE=true                   # alembic upgrade head al iniciar
AUTO_SEED=true                      # seed idempotente al iniciar si no hay productos

# --- Seguridad ---
ADMIN_API_KEY=change-me-admin-key
RATE_LIMIT_PER_MIN=60

# --- IA ---
AI_MODE=mock                        # mock | live
OPENAI_API_KEY=
OPENAI_CHAT_MODEL=gpt-5.4-nano
OPENAI_REASONING_EFFORT=low         # vacío = no se envía el parámetro
OPENAI_CHAT_MAX_OUTPUT_TOKENS=400
OPENAI_IMAGE_MODEL=gpt-image-1-mini
IMAGE_SIZE=1024x1024                # 1024x1024 | 1536x1024 | 1024x1536 | auto
IMAGE_QUALITY=low                   # low | medium | high
SIMULATION_USE_PRODUCT_REFERENCE=true
OPENAI_MODERATION=true              # moderar texto libre de placement_hint (endpoint gratuito)
AGENT_HISTORY_TURNS=6
AGENT_MAX_TOOL_ROUNDS=4

# --- Presupuesto y cuotas ---
BUDGET_USD_LIMIT=3.50
BUDGET_WARN_PCT=80
MAX_SIMULATIONS_PER_CUSTOMER=2
MAX_SIMULATIONS_PER_DAY=15
MAX_LLM_MESSAGES_PER_CUSTOMER_PER_DAY=40

# --- Imágenes ---
INPUT_MAX_SIDE=1280
INPUT_JPEG_QUALITY=85
OUTPUT_MAX_SIDE=768
OUTPUT_FORMAT=JPEG                  # JPEG | WEBP
OUTPUT_QUALITY=82
OUTPUT_TARGET_MAX_KB=400
MAX_UPLOAD_MB=10
PHOTO_RETENTION_DAYS=7
STORE_FULL_OUTPUT=false

# --- Storage ---
STORAGE_BACKEND=local               # local | s3
LOCAL_STORAGE_PATH=/app/storage
S3_ENDPOINT_URL=                    # https://<PROJECT_REF>.supabase.co/storage/v1/s3
S3_BUCKET=decosmart
S3_ACCESS_KEY_ID=
S3_SECRET_ACCESS_KEY=
S3_REGION=us-east-1                 # región del proyecto Supabase
S3_PUBLIC_BASE_URL=                 # sin uso (bucket privado; catálogo servido en /static/products)

# --- Telegram ---
TELEGRAM_BOT_TOKEN=
TELEGRAM_BOT_USERNAME=DecoSmartBot
TELEGRAM_MODE=polling               # polling | webhook | disabled
TELEGRAM_WEBHOOK_SECRET=change-me-webhook-secret
ADMIN_TELEGRAM_CHAT_ID=             # chat que recibe notificaciones

# --- Automatización ---
LOW_STOCK_THRESHOLD=5
QUOTE_VALIDITY_DAYS=7
DAILY_SUMMARY_HOUR=20               # hora local America/Lima
TIMEZONE=America/Lima
SCHEDULER_ENABLED=true
N8N_WEBHOOK_URL=                    # opcional: si existe, se reenvían eventos

# --- Frontend (build time) ---
VITE_API_URL=http://localhost:8000
VITE_TELEGRAM_BOT_URL=https://t.me/DecoSmartBot

# --- Dashboard ---
DASHBOARD_API_URL=http://backend:8000
DASHBOARD_ADMIN_KEY=change-me-admin-key
DASHBOARD_PASSWORD=                 # si se define, el dashboard pide contraseña
```

`Settings` valida: con `APP_ENV=production`, si `ADMIN_API_KEY` o `TELEGRAM_WEBHOOK_SECRET` empiezan por `change-me` → error y no arranca. Si `AI_MODE=live` y falta `OPENAI_API_KEY` → arranca forzando `mock` y registra advertencia. Si `TELEGRAM_BOT_TOKEN` vacío → `TELEGRAM_MODE=disabled`.

---

## 5. Módulos — especificación

### 5.1 Catálogo y comercio (`services/catalog.py`, `quotes.py`, `orders.py`)
- `search_products(db, query, category, max_price, room, in_stock=None, limit, offset)`: filtro ILIKE (en SQLite `lower() LIKE`), solo `active`.
- `get_product(db, ref)`: acepta id (`int`), SKU o slug.
- `recommend(db, budget, room, category, max_width_cm, style)`: filtra `stock>0`, `price<=budget`, `width_cm<=max_width_cm`; ordena por coincidencia de estilo/ambiente y luego precio descendente dentro del presupuesto; máx. 3.
- `create_quote(db, customer, items, channel, notes)`: valida stock (no reserva), congela `unit_price`, `code` correlativo diario, `status='sent'`, emite `quote.created`.
- `create_order(db, ...)`: desde quote o ítems; `status='pending'`, `is_demo=True`; si viene de quote → quote `accepted`; emite `order.created`.
- `confirm_order` (admin): descuenta stock, emite `order.status_changed` y `product.low_stock` si `stock <= LOW_STOCK_THRESHOLD`.

### 5.2 Bot de Telegram (`bot/handlers.py`)

Entrada única: `handle_update(db, update: dict)`. Tipos: `message.text`, `message.photo` / `message.document` (imagen), `callback_query`.

Máquina de estados (`conversations.state`):

| Estado | Entrada esperada | Acción |
|---|---|---|
| `idle` | texto libre | Router de reglas → si no aplica, `run_agent_turn` |
| `idle` | `/start`, `hola`, `menu` | `welcome` + teclado |
| `idle` | callback `catalog` | lista categorías → productos (sin LLM) |
| `idle` | callback `product:<id>` | ficha del producto (foto + texto desde BD) + botones `Simular` `Cotizar` |
| cualquiera | callback `simulate:<id>` o tool `start_simulation` | verifica cuotas (§5.4); si `photo_consent_at` nulo → `sim_consent`; si no → `sim_photo` |
| `sim_consent` | callback `consent:yes` | fija `photo_consent_at`; → `sim_photo` |
| `sim_photo` | foto | descarga la de mayor resolución (`getFile`), valida tipo/tamaño, `optimize_input`, guarda en storage `customers/<cid>/inputs/<uuid>.jpg`; → `sim_dimensions` |
| `sim_photo` | texto | recuerda que se necesita una foto (`cancelar` sale) |
| `sim_dimensions` | texto `A x B [x C]` | parse regex `(\d{2,4})\s*[x×*,]\s*(\d{2,4})(?:\s*[x×*,]\s*(\d{2,4}))?` (cm; si valores < 10 se asumen metros y se multiplican ×100); opcional "dónde" tras `;`; → `sim_confirm` con aviso de ancho si aplica |
| `sim_confirm` | callback `sim:go:<sim_id>` | **aquí y solo aquí** se llama a `simulation.service.run()`; → `idle` |
| `sim_confirm` | callback `sim:cancel` | simulación `cancelled`; → `idle` |
| `idle` | callback `rate:<sim_id>:<n>` | guarda `simulation_ratings`; agradece; ofrece cotizar |
| `idle` | callback `quote:<id>` | `create_quote` con 1 unidad → envía cotización formateada |
| `idle` | callback `order:<quote_code>` | pide teléfono y dirección (`order_contact`) → crea pedido demo |
| `order_contact` | texto | guarda contacto → `create_order` → `idle` |
| cualquiera | `/cancelar` o `cancelar` | limpia `context`, → `idle` |
| `idle` | `/catalogo`, `/simular`, `/cotizar`, `/estado <código>` | equivalentes a los botones: catálogo, simular el producto seleccionado (o pedir elegir uno), cotizar el seleccionado, `get_request_status` |

Reglas:
- Idempotencia: ignorar `update_id` ya procesado (cache LRU en memoria de 1000 ids).
- Rate limit por `chat_id`: 20 mensajes/min; excedente se ignora con un aviso único.
- Mensajes de texto > 1000 caracteres se truncan antes del LLM.
- Toda excepción se captura: `error_logs` + mensaje genérico al usuario. Nunca romper el webhook.
- Cada mensaje entrante/saliente se guarda en `messages`.

### 5.3 Agente (`agent/runner.py`)
`run_agent_turn(db, conversation, user_text) -> AgentReply(text, buttons, side_effects)`:
1. `budget.check_llm(customer)` (presupuesto global + `MAX_LLM_MESSAGES_PER_CUSTOMER_PER_DAY`). Si falla → texto `ai_unavailable`.
2. Construye input: últimos `AGENT_HISTORY_TURNS` mensajes user/assistant (sin tool outputs antiguos) + mensaje actual. `instructions` = SYSTEM_PROMPT formateado.
3. Llama provider con `tools`. Bucle: por cada `function_call` ejecuta `tools.dispatch(name, args, ctx)`, agrega `function_call_output`, repite hasta respuesta de texto o `AGENT_MAX_TOOL_ROUNDS`.
4. Registra `api_usage` por cada llamada (tokens de `response.usage`).
5. `guard.validate(text, tool_results)`.
6. Side effects de herramientas (p. ej. `start_simulation` → el handler cambia estado y envía `photo_consent`/`ask_photo`; `create_quote` → envía la cotización formateada además del texto).

`MockProvider.chat`: detecta intención por palabras clave (`precio`, `cuánto`, `medida`, `stock`, `recomienda`, `presupuesto` + número, `simular`, `cotiza`) y llama a la herramienta real correspondiente, respondiendo con plantilla. Devuelve usage con tokens = 0 y `mode='mock'`.

### 5.4 Simulación (`simulation/service.py`)

`prepare(db, customer, product)` → crea `simulations(status='awaiting_photo')` si pasa cuotas.
`run(db, simulation_id) -> SimulationResult`:

1. **Cuotas** (en este orden; cualquier fallo → `blocked_quota` + mensaje):
   - `customer.simulations_used < MAX_SIMULATIONS_PER_CUSTOMER`
   - simulaciones `completed` hoy < `MAX_SIMULATIONS_PER_DAY`
   - `budget.can_spend(estimate_image_cost())` (gastado + estimado ≤ `BUDGET_USD_LIMIT`)
2. **Caché**: `cache_key = sha256(input_hash|product_id|w|h|d|model|size|quality|placement)`. Si existe simulación `completed` con ese `cache_key` → copiar `output_key`, `reused_from_id`, `cost_usd=0`, **no** incrementa `simulations_used`, envía resultado.
3. `status='processing'`, enviar `processing`.
4. Prompt con `build_simulation_prompt` (doc 05 §5). `placement_hint` pasa moderación si `OPENAI_MODERATION=true` y `AI_MODE=live`.
5. `provider.edit_image(room_bytes, reference_bytes|None, prompt, size, quality)` → `ImageResult(bytes, usage)`.
   - Mock: devuelve la foto de entrada con una franja inferior y el texto "SIMULACIÓN DEMO – {producto}" y la miniatura del producto pegada (Pillow). Costo 0.
6. `optimize_output` → guardar `customers/<cid>/outputs/<sim_id>.jpg`.
7. `cost_usd = pricing.estimate_image_edit(model, quality, size, usage)`; `api_usage` insert; `simulations_used += 1`; `status='completed'`; evento `simulation.completed`.
8. Enviar foto (≤768 px) con `result_caption` + botones ⭐1–5.
9. Error → `status='failed'`, `error_logs`, evento `simulation.failed`, **no** consume cuota del cliente; mensaje de disculpa.

**Métricas**: `simulations_total` = simulaciones `completed` (incluye reutilizadas); `simulations_reused` = con `reused_from_id`; generadas con costo = total − reutilizadas. El admin puede reiniciar la cuota con `PATCH /admin/customers/{id}` `{"simulations_used": 0}` (útil para la demo).

**Regeneración**: botón "Generar otra versión" solo si quedan cuotas; exige nueva confirmación explícita (nuevo `sim_confirm`) y no usa caché (agrega `variant` al cache_key).

### 5.5 Pipeline de imágenes (`imaging/pipeline.py`)
- `optimize_input(raw: bytes) -> (jpeg_bytes, meta)`: abrir con Pillow, `ImageOps.exif_transpose`, convertir a RGB, redimensionar con `thumbnail((INPUT_MAX_SIDE, INPUT_MAX_SIDE), LANCZOS)` (mantiene aspecto), quitar EXIF (privacidad: GPS), JPEG `quality=INPUT_JPEG_QUALITY, optimize=True, progressive=True`. Rechazar si no es imagen válida, > `MAX_UPLOAD_MB`, o lado menor < 320 px.
- `optimize_output(raw) -> (bytes, meta)`: redimensionar a `OUTPUT_MAX_SIDE`, guardar en `OUTPUT_FORMAT` con `OUTPUT_QUALITY`; si supera `OUTPUT_TARGET_MAX_KB`, bajar calidad en pasos de 8 hasta 50.
- `meta`: `{width, height, bytes, format, sha256}` → se guarda en la simulación.
- Imagen de referencia del producto: `products.reference_image_key` (pre-optimizada en el seed a ≤768 px, fondo neutro).

### 5.6 Presupuesto y precios (`core/pricing.py`, `services/budget.py`)

`pricing.py` contiene una tabla editable (USD por 1M tokens) con fecha de verificación:

```python
PRICING_VERIFIED_AT = "2026-11-18"  # https://developers.openai.com/api/docs/pricing
TEXT_MODELS = {
    "gpt-5.4-nano": {"input": 0.20, "cached_input": 0.02, "output": 1.25},
    "gpt-5.4-mini": {"input": 0.75, "cached_input": 0.075, "output": 4.50},
    "gpt-5-mini":   {"input": 0.25, "cached_input": 0.025, "output": 2.00},
    "gpt-5-nano":   {"input": 0.05, "cached_input": 0.005, "output": 0.40},
}
# Precio por imagen de salida (tabla oficial) como estimación previa y fallback.
IMAGE_OUTPUT_PER_IMAGE = {
    ("gpt-image-1-mini", "low", "1024x1024"): 0.005,
    ("gpt-image-2", "low", "1024x1024"): 0.006,
    ("gpt-image-1.5", "low", "1024x1024"): 0.009,
    ("gpt-image-1", "low", "1024x1024"): 0.011,
}
IMAGE_INPUT_SURCHARGE_USD = 0.006  # margen conservador por imágenes de entrada (edit)
DEFAULT_UNKNOWN_IMAGE_COST = 0.05  # si el modelo/tamaño no está en tabla → asumir caro
```
- **Nota**: el `cached_input` de gpt-5.4-nano y los precios de imagen deben revalidarse en la página oficial antes de la demo; actualizar la tabla y `PRICING_VERIFIED_AT`.
- `estimate_chat(model, usage)`: tokens × tarifa. Modelo desconocido → tarifa del más caro de la tabla.
- `estimate_image_edit(model, quality, size, usage=None)`: `IMAGE_OUTPUT_PER_IMAGE[...] + IMAGE_INPUT_SURCHARGE_USD` (estimación conservadora); guardar también los tokens de `usage` si vienen.
- `budget.spent_usd(db)`: `SUM(api_usage.cost_usd WHERE mode='live')`.
- `budget.can_spend(db, est)`: `spent + est <= BUDGET_USD_LIMIT`. Al cruzar `BUDGET_WARN_PCT` emite `budget.warning` (una vez por umbral).
- Todas las llamadas reales pasan por `budget.track(...)` (context manager que mide latencia y registra éxito/fallo).

### 5.7 Automatización (`automation/`)

`emit(db, type, entity_type, entity_id, customer_id, payload)` inserta en `events` y ejecuta handlers registrados síncronamente (errores de handler → `error_logs`, no propagan). Si `N8N_WEBHOOK_URL` existe, POST del evento (timeout 3 s, fire-and-forget).

| Evento | Disparador | Reacción |
|---|---|---|
| `conversation.started` | nueva conversación | — (métrica) |
| `inquiry.created` | herramienta de catálogo / detalle web | — (métrica) |
| `quote.created` | create_quote | Si canal telegram → enviar cotización formateada al cliente; notificar admin |
| `quote.status_changed` | PATCH admin / pedido desde quote | Notificar cliente por Telegram si tiene chat |
| `order.created` | create_order | Notificar admin: "🛒 Nuevo pedido demo PED-… US$… (cliente, canal)" |
| `order.status_changed` | PATCH admin | Notificar cliente |
| `simulation.completed` / `simulation.failed` | simulador | Métrica; fallos → error_logs |
| `simulation.rated` | rating | Si score ≤ 2 → notificar admin |
| `product.low_stock` | stock ≤ umbral tras confirmar pedido o PATCH | Notificar admin "⚠️ Stock bajo: … quedan N" (una vez por producto hasta reponer) |
| `budget.warning` | 80% presupuesto | Notificar admin |
| `summary.daily` | scheduler 20:00 / endpoint | Notificar admin: conversaciones, consultas, cotizaciones, pedidos, simulaciones, rating promedio, gasto API del día |

`summary.daily` es idempotente: si ya existe un evento `summary.daily` con la fecha local de hoy, el endpoint/job no reenvía (respuesta `{"sent": false, "reason": "already_sent"}`), salvo `?force=true`.

Scheduler (APScheduler `BackgroundScheduler`, si `SCHEDULER_ENABLED`): resumen diario, expirar cotizaciones vencidas (cada hora), limpiar fotos (diario). En Render free el servicio duerme; por eso `daily-summary.yml` en GitHub Actions llama al endpoint como respaldo (y despierta el servicio).

**n8n (opcional)**: documentar en `docs/10-devops.md` un workflow de ejemplo (Webhook → Google Sheets/Email). No es dependencia del MVP.

### 5.8 Dashboard (`dashboard/`)
- Autenticación: si `DASHBOARD_PASSWORD` está definido, `st.text_input(type="password")` antes de mostrar nada.
- `app.py` (Resumen): fila de métricas `st.metric` — Conversaciones, Consultas, Cotizaciones, Pedidos demo, Ventas concretadas (completed), Simulaciones, Rating promedio, Gasto API (US$ y % de presupuesto). Gráfico de línea "Actividad diaria" (14 días). Etiquetas explícitas: *Consulta ≠ Cotización ≠ Pedido ≠ Venta*.
- `1_Conversaciones`: serie diaria de conversaciones e inquiries; tabla de tipos de consulta.
- `2_Productos`: top consultados vs top solicitados (barras lado a lado), stock actual con resaltado de stock bajo.
- `3_Simulaciones`: total, completadas/fallidas/reutilizadas, distribución de ratings, galería de últimas 6 (URL de resultado vía admin).
- `4_Costos_API`: gasto acumulado vs límite (barra de progreso), por operación y por día, costo promedio por simulación y por conversación, modo actual (mock/live), fecha de verificación de precios.
- `5_Eventos_y_Errores`: tablas filtrables de `/admin/events` y `/admin/errors`.
- Todas las llamadas con `st.cache_data(ttl=30)` y botón "Actualizar".

### 5.9 Frontend
- Rutas: `/`, `/catalogo`, `/catalogo/:categoria`, `/producto/:slug`, `/carrito`, `/cotizacion`, `/cotizacion/:code`, `/checkout`, `/pedido/:code`.
- Home: hero, categorías, 3 destacados, sección "Simula en tu ambiente con IA" → botón Telegram.
- Producto: galería, precio, stock (badge "Últimas unidades" si `low_stock`), dimensiones, selector de color (solo informativo), cantidad, `Agregar al carrito`, `Simular por Telegram` (deep link `https://t.me/<bot>?start=sim_<sku>`; el bot interpreta `/start sim_<sku>` y entra al flujo de simulación de ese producto).
- Carrito: zustand persistido; editar cantidades; `Solicitar cotización` → formulario (nombre, email, teléfono, notas) → `POST /api/quotes` → `/cotizacion/:code`.
- Checkout demo: desde cotización o carrito → `POST /api/orders` → confirmación con aviso "Pedido de demostración, sin cobro".
- Botón flotante de Telegram en todas las páginas.
- Responsive (mobile-first, breakpoints 640/1024). Accesible: alt en imágenes, foco visible, contraste AA.
- Precios siempre desde la API, nunca hardcodeados.

---

## 6. Docker, CI/CD y Render

### docker-compose.yml (local)
- `db` (opcional, `profiles: ["localdb"]`): postgres:16-alpine, volumen `pgdata`, healthcheck `pg_isready`. Solo con `docker compose --profile localdb up`; por defecto se usa Supabase vía `DATABASE_URL` de `.env`.
- `backend`: build `./backend`, `env_file: .env`, puerto 8000, volumen `./backend/storage:/app/storage`.
- `frontend`: build `./frontend` con args `VITE_API_URL`, `VITE_TELEGRAM_BOT_URL`; puerto `5173:80`.
- `dashboard`: build `./dashboard`, puerto 8501, `DASHBOARD_API_URL=http://backend:8000`.

### Dockerfiles
- Backend: `python:3.11-slim`, usuario no root, `pip install --no-cache-dir -r requirements.txt`, `CMD ["sh","-c","uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]`. Migraciones y seed en `lifespan` según `AUTO_MIGRATE`/`AUTO_SEED`.
- Frontend: multi-stage `node:20-alpine` (build) → `nginx:alpine` con `try_files $uri /index.html`.
- Dashboard: `python:3.11-slim`, `streamlit run app.py --server.port ${PORT:-8501} --server.address 0.0.0.0 --server.headless true`.

### GitHub Actions
- `ci.yml` (push y PR): jobs `backend` (ruff check, pytest con `AI_MODE=mock`, `DATABASE_URL=sqlite:///./test.db` **y** un job con servicio postgres:16 que corre `alembic upgrade head` + pytest), `frontend` (npm ci, lint, vitest, build), `dashboard` (pip install, `python -m py_compile`), `docker` (build de las 3 imágenes sin push).
- `deploy.yml`: `on: workflow_run` de CI exitoso en `main` → `curl -X POST "$RENDER_DEPLOY_HOOK_BACKEND"` (y frontend, dashboard). Secrets en GitHub. Tras deploy, `scripts/set_webhook.py` no se ejecuta aquí (se hace una vez manualmente).
- `daily-summary.yml`: `schedule: cron "0 1 * * *"` (20:00 Lima) → POST con `X-Admin-Key`.

### Render (`render.yaml`, Blueprint)
- `decosmart-api`: web, runtime docker, `rootDir: backend`, plan free, healthCheckPath `/health`, envVars (sync: false para secretos), `TELEGRAM_MODE=webhook`, `STORAGE_BACKEND=s3`.
- `decosmart-web`: static site, `rootDir: frontend`, build `npm ci && npm run build`, publish `dist`, rewrite `/* → /index.html`.
- `decosmart-dashboard`: web, docker, `rootDir: dashboard`.
- Base de datos: **Supabase Postgres** (free, persistente, 500 MB) vía **session pooler** (puerto 5432, compatible IPv4; Render free no tiene IPv6 para la conexión directa) → `DATABASE_URL=postgresql+psycopg://postgres.<PROJECT_REF>:<PASSWORD>@aws-0-<REGION>.pooler.supabase.com:5432/postgres?sslmode=require` (contraseña URL-encoded). No usar el transaction pooler (6543). SQLAlchemy con `pool_pre_ping` y `pool_recycle=300`. El proyecto free se pausa tras ~1 semana sin actividad: reactivarlo antes de la demo. No usar Postgres free de Render (expira a los 30 días). Local opcional: `docker compose --profile localdb up`.
- Imágenes: **Supabase Storage** (1 GB gratis; bucket **privado** `decosmart`, endpoint S3 `https://<PROJECT_REF>.supabase.co/storage/v1/s3`, boto3 con *path-style* y SigV4, claves S3 solo en el backend) solo para fotos de clientes y resultados de simulación (`customers/`, privado, URLs prefirmadas). Las imágenes de **catálogo** viajan en el repo (`backend/seed/images`) dentro de la imagen Docker y se sirven en `GET /static/products/<archivo>` (ya implementado en el esqueleto); `products.reference_image_key` es la ruta relativa `seed/images/<archivo>`. El frontend antepone `VITE_API_URL` a URLs relativas.
- Nada se escribe en el disco de Render (efímero).

---

## 7. Orden de implementación (para agentes paralelos)

| Paso | Rama | Contenido | Depende de |
|---|---|---|---|
| 0 | `main` | Esqueleto: estructura, config, db, modelos, Alembic inicial, seed, `/health`, compose | — |
| 1a | `feat/backend-core` | services catálogo/quotes/orders/customers/inquiries/metrics, API pública + admin, storage, pricing/budget, automation (events + handlers + scheduler), tests | 0 |
| 1b | `feat/frontend` | toda la tienda | 0 (contratos doc 04) |
| 1c | `feat/ops-dashboard` | dashboard, Dockerfiles finales, CI/CD, render.yaml | 0 |
| 2 | `feat/ai-bot` | imaging, ai providers, agent, simulation, bot, webhook/polling, tests | 1a |
| 3 | `main` | integración, e2e mock, docs finales | todo |

---

## 8. Definición de "hecho" por módulo (criterios de aceptación)

- **E-commerce**: 6 productos visibles con imagen, precio, medidas, colores, stock; filtro por categoría; carrito persiste tras recarga; `POST /api/quotes` devuelve código y aparece en dashboard; pedido demo muestra aviso "sin cobro"; usable a 375 px de ancho sin scroll horizontal.
- **Agente**: en mock y live responde precio/medidas idénticos a BD; ante "¿tienen sofá rojo de 50 dólares?" no inventa (responde que no hay y ofrece alternativas reales); test del guard reemplaza una respuesta con precio inventado.
- **Simulador**: no se llama al provider sin callback `sim:go`; cliente con 2 simulaciones recibe `quota_exhausted`; misma foto+producto+medidas reutiliza resultado con costo 0; entrada ≤1280 px, salida ≤768 px y ≤400 KB; rating 1–5 registrado.
- **Automatización**: crear cotización por Telegram envía el mensaje con código y total; pedido nuevo notifica al admin; confirmar pedido que deja stock ≤5 emite `product.low_stock`; endpoint de resumen envía mensaje.
- **Dashboard**: muestra los 11 indicadores pedidos con datos reales; distingue consultas/cotizaciones/pedidos/ventas.
- **Presupuesto**: con `BUDGET_USD_LIMIT=0.001` en live, cualquier simulación queda `blocked_quota` sin llamar a OpenAI (test con provider espía).
- **DevOps**: `docker compose up --build` levanta los servicios (BD en Supabase; con `--profile localdb`, también Postgres local); CI verde; deploy en Render responde `/health` con `db: ok`.

---

## 9. Qué NO hacer
- No integrar pagos, login de clientes, ni panel admin web aparte del dashboard.
- No usar LangChain, CrewAI ni frameworks de agentes: el bucle de tools es ~80 líneas.
- No llamar a OpenAI en tests/CI. No guardar fotos de clientes en el repo.
- No usar enums nativos de Postgres ni features async de SQLAlchemy.
- No exponer `/admin/*` sin `X-Admin-Key`. No loggear tokens, teléfonos ni fotos.
- No generar imágenes en calidad `medium/high` por defecto.
