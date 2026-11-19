# DECISIONES — Registro de decisiones de arquitectura (ADR)

> Formato breve: **Contexto · Decisión · Consecuencias**. Las decisiones ADR-001 a ADR-010 se tomaron el 2026-11-18 y están reflejadas en [`CODEX_HANDOFF.md`](CODEX_HANDOFF.md).
> Regla para agentes ([`AGENTS.md`](../AGENTS.md)): si algo es ambiguo, elegir la opción más simple y **anotarla al final de este archivo** en "Decisiones durante la implementación".

---

## ADR-001 — Monorepo

- **Contexto**: 4 integrantes y agentes de código trabajando en paralelo sobre frontend, backend, dashboard e infraestructura; un solo pipeline de CI/CD y un único Blueprint de Render.
- **Decisión**: un solo repositorio `decosmart-ai/` con carpetas `frontend/`, `backend/`, `dashboard/`, `docs/`, `.github/workflows/` y `render.yaml` en la raíz.
- **Consecuencias**: (+) contratos y documentación versionados junto al código; un PR puede tocar API y frontend de forma atómica; CI único. (−) CI corre todos los jobs en cada cambio (se mitiga con caché; filtros por ruta opcionales). Cada agente trabaja solo en su carpeta.

## ADR-002 — Bot de Telegram dentro del backend con cliente `httpx` propio

- **Contexto**: Render free permite pocos servicios y duerme por inactividad; el bot necesita acceso directo a servicios y BD. `python-telegram-bot` trae su propio bucle de eventos, difícil de combinar con FastAPI y de testear.
- **Decisión**: el bot vive en `backend/app/bot/` con un `TelegramClient` fino sobre la Bot API usando `httpx`. Entrada única `handle_update(db, update: dict)` usada por el webhook (`/telegram/webhook/{secret}`, producción) y por un hilo de polling (local).
- **Consecuencias**: (+) un solo despliegue; tests con `respx` sin red; mismo código en webhook y polling. (−) se implementan a mano los métodos usados (send_message, send_photo, get_file, answer_callback, set_webhook, get_updates…) y la idempotencia.

## ADR-003 — SQLAlchemy 2.0 síncrono

- **Contexto**: carga de prototipo (decenas de usuarios); equipo con poca experiencia en async; tests deben correr en SQLite.
- **Decisión**: SQLAlchemy 2.0 en modo síncrono con `psycopg` 3, endpoints sync en el threadpool de FastAPI, Alembic para migraciones; estados como `VARCHAR` validados en Python (sin enums nativos de Postgres).
- **Consecuencias**: (+) código simple, tests en SQLite, migraciones triviales. (−) menor concurrencia teórica; la generación de imagen (~60 s) ocupa un hilo del pool en `BackgroundTasks` (aceptable a esta escala).

## ADR-004 — Responses API + function calling, sin frameworks de agentes

- **Contexto**: el agente necesita consultar el catálogo real, aplicar guardias de costo y anti-alucinación, e inyectar identidad del cliente desde el servidor.
- **Decisión**: usar el SDK oficial `openai` con `client.responses.create` y herramientas JSON Schema `strict: true`; bucle propio en `agent/runner.py` (máx. `AGENT_MAX_TOOL_ROUNDS=4`). No usar LangChain, CrewAI ni similares.
- **Consecuencias**: (+) ~80 líneas auditables; control total de presupuesto, historial, guard y `customer_id`; menos dependencias. (−) funciones como memoria o trazas se implementan a mano si se necesitan.

## ADR-005 — Modelos `gpt-5.4-nano` y `gpt-image-1-mini` configurables

- **Contexto**: presupuesto de US$ 4; precios verificados el 2026-11-18: nano US$ 0.20/1.25 por 1M tokens; `gpt-image-1-mini` low 1024×1024 ≈ US$ 0.005/imagen.
- **Decisión**: por defecto `OPENAI_CHAT_MODEL=gpt-5.4-nano` (alternativa `gpt-5.4-mini`) y `OPENAI_IMAGE_MODEL=gpt-image-1-mini`, `IMAGE_QUALITY=low`, `IMAGE_SIZE=1024x1024`; todo por variables de entorno; tabla de precios editable en `core/pricing.py` con `PRICING_VERIFIED_AT`.
- **Consecuencias**: (+) costo estimado de la campaña de pruebas ≈ US$ 0.93; cambiar de modelo no requiere código. (−) calidad de imagen limitada (simulación marcada como experimental); los precios deben revalidarse antes de la demo.

## ADR-006 — Modo mock (`AI_MODE=mock`)

- **Contexto**: no se puede gastar crédito en desarrollo, tests ni CI; la demo necesita un plan B.
- **Decisión**: interfaz `AIProvider` con `OpenAIProvider` y `MockProvider`. El mock detecta intención por palabras clave y llama a las **mismas herramientas reales**; para imágenes compone la foto con una franja "SIMULACIÓN DEMO" y la miniatura del producto. Si `AI_MODE=live` sin `OPENAI_API_KEY`, se fuerza mock.
- **Consecuencias**: (+) costo 0 en desarrollo y CI; flujos completos demostrables sin OpenAI. (−) el mock no evalúa la calidad del lenguaje natural; se requiere una sesión live controlada para validar el agente real.

## ADR-007 — Supabase Postgres en lugar de Postgres de Render (reemplaza a Neon)

- **Contexto**: la base de datos free de Render expira a los 30 días; el equipo ya usa Supabase y quiere un único proveedor para BD e imágenes.
- **Decisión**: PostgreSQL de Supabase vía **Supavisor session pooler** (puerto 5432, compatible IPv4, necesario porque Render free no tiene IPv6 para la conexión directa), `sslmode=require`, `pool_pre_ping` + `pool_recycle=300`. Local opcional con `postgres:16-alpine` (`docker compose --profile localdb`).
- **Consecuencias**: (+) persistencia gratis, panel SQL para revisar datos. (−) el proyecto free se pausa tras ~1 semana sin actividad: reactivarlo antes de la demo. No usar el transaction pooler (6543) por incompatibilidad con sentencias preparadas.

## ADR-008 — Supabase Storage (API S3) para imágenes (reemplaza a R2)

- **Contexto**: el disco de Render es efímero; las fotos de clientes son datos personales y no deben ser públicas.
- **Decisión**: bucket **privado** en Supabase Storage usado con `boto3` a través de su endpoint compatible S3 (`https://<ref>.supabase.co/storage/v1/s3`, *path-style*, región del proyecto). Solo fotos de clientes y resultados (`customers/`), con URLs prefirmadas de 10 min. El catálogo se sirve desde el backend (`/static/products`). Retención temporal: `PHOTO_RETENTION_DAYS`.
- **Consecuencias**: (+) mismo proveedor que la BD, 1 GB gratis, sin cambios de código (protocolo `Storage`). (−) claves S3 de Storage con acceso total al proyecto: guardarlas solo como secretos.

## ADR-009 — n8n opcional

- **Contexto**: la automatización es un pilar del proyecto, pero depender de un servicio externo adicional aumenta el riesgo en la demo.
- **Decisión**: la automatización del MVP es interna (`automation/events.py` + handlers). Si `N8N_WEBHOOK_URL` está definido, cada evento se reenvía por POST (timeout 3 s, fire-and-forget). Se documenta un workflow de ejemplo (Webhook → Google Sheets/Email) en [10 §7](10-devops.md).
- **Consecuencias**: (+) el MVP funciona sin n8n; demuestra integración low-code como valor agregado. (−) n8n queda como experimental; sin garantías de entrega (sin reintentos).

## ADR-010 — APScheduler + cron de GitHub Actions como respaldo

- **Contexto**: se necesitan tareas programadas (resumen diario 20:00 Lima, expiración de cotizaciones, limpieza de fotos) y Render free duerme el servicio.
- **Decisión**: `BackgroundScheduler` de APScheduler en el proceso del backend (`SCHEDULER_ENABLED=true`) y `daily-summary.yml` con `cron "0 1 * * *"` que llama a `POST /admin/jobs/daily-summary` (y despierta el servicio).
- **Consecuencias**: (+) sin infraestructura adicional (Celery/Redis); el resumen llega aunque el servicio duerma. (−) posible envío duplicado si ambos disparan: el endpoint debe ser idempotente por fecha (ver propuesta en [10 §3](10-devops.md)); los jobs horarios se ejecutan solo mientras el servicio está despierto.

---

## Decisiones durante la implementación

> Agentes e integrantes: agregar una entrada por decisión, en orden cronológico. Plantilla:
>
> ```
> ### ADR-0NN — Título corto
> - Fecha: AAAA-MM-DD · Autor: <integrante o agente> · PR: #<n>
> - Contexto:
> - Decisión:
> - Consecuencias:
> ```

### Dashboard y DevOps (`feat/ops-dashboard`)

- **Adaptador único de la API admin**: `dashboard/api.py` separa transporte (`fetch_json`), adaptadores puros (`parse_*`) y envoltorios cacheados (`get_*`, `st.cache_data(ttl=30)`). Si la forma de un JSON admin cambia, solo se toca `parse_*`. Los adaptadores aceptan tanto listas planas como `{"items": [...], "total": n}`, convierten dinero string → float y rellenan claves faltantes con valores por defecto.
- **API caída ≠ dashboard caído**: cada llamada devuelve `ApiResult(data, error)`; las páginas muestran `st.warning` y renderizan con valores vacíos/cero.
- **Streamlit ≥ 1.50**: se usa el parámetro `width="stretch"` (reemplazo de `use_container_width`, deprecado). Cumple el "1.40+" del handoff.
- **Tipos de consulta** (página Conversaciones): no hay endpoint específico; se calculan con los eventos `inquiry.created` recientes (`payload.type` / `payload.channel`). Si el backend no incluye `type` en el payload, se muestran como "sin tipo".
- **Galería de simulaciones**: las imágenes se descargan desde el servidor del dashboard (no desde el navegador), porque en Docker `DASHBOARD_API_URL=http://backend:8000` no es accesible para el navegador y en producción las URLs de R2 son prefirmadas. Rutas relativas (`/media/...`) se resuelven contra `DASHBOARD_API_URL`.
- **Gasto acumulado vs. por rango**: la página de costos toma el acumulado y el % de presupuesto de `/admin/metrics/summary` (histórico) y los desgloses de `/admin/usage?days=N`.
- **Umbral de stock bajo en el dashboard**: se resalta `low_stock` de `/api/products` o `stock <= LOW_STOCK_THRESHOLD` (env opcional, default 5).
- **Contraseña del dashboard**: comparación con `hmac.compare_digest` y estado en `st.session_state`; si `DASHBOARD_PASSWORD` está vacío no se pide.
- **Tests de páginas**: `dashboard/tests/test_pages_smoke.py` ejecuta cada página con `streamlit.testing.v1.AppTest` con la API caída y con datos de ejemplo según doc 04.
- **CI**: el job `docker-build` usa matriz (backend/frontend/dashboard) con caché GHA por servicio y depende de todos los jobs de test. El job `dashboard` también ejecuta los tests de `scripts/`.
- **Deploy**: `render.yaml` con `autoDeploy: false` en los tres servicios; `deploy.yml` dispara los deploy hooks solo si CI terminó en `success` para un `push` a `main` (o manualmente) y omite con aviso los hooks no configurados. El smoke test espera 60 s y sondea `/health` hasta ~5 min (cold start de Render free).
- **Resumen diario**: `daily-summary.yml` reintenta hasta 8 veces cada 30 s (servicio dormido) y falla de inmediato ante 401/403.
- **`scripts/check_env.py`**: validación previa a producción solo con stdlib; sale con código 1 si hay errores (secretos por defecto o < 12 caracteres, `AI_MODE=live` sin clave, S3 sin credenciales, webhook sin `PUBLIC_BASE_URL` https, BD local/SQLite). No imprime valores de secretos.

### Backend core (`feat/backend-core`)

#### feat/backend-core
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

### Pendientes de decidir (detectados en la documentación)

- Idempotencia del resumen diario cuando lo disparan APScheduler y GitHub cron el mismo día (propuesta: omitir si ya existe evento `summary.daily` con la misma fecha).
- Uno o dos buckets en R2 según soporte de acceso público por prefijo.
- Definición exacta de `simulations_total` en `/admin/metrics/summary` (propuesta en [08 §2](08-dashboard-kpis.md): completadas, incluidas reutilizadas; "generadas" = completadas sin `reused_from_id`).
- Comportamiento al iniciar en `production` con secretos por defecto (`change-me-…`): advertir o negarse a arrancar.
