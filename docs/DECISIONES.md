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

## ADR-007 — Neon en lugar de Postgres de Render

- **Contexto**: la base de datos free de Render expira a los 30 días; el proyecto dura más y debe conservar datos para la demo y el informe.
- **Decisión**: PostgreSQL 16 en Neon (free, persistente) con `sslmode=require`; local con `postgres:16-alpine`.
- **Consecuencias**: (+) persistencia sin costo, *branching* para pruebas y restauración. (−) un proveedor más que configurar; ligera latencia en el primer acceso tras suspensión.

## ADR-008 — Cloudflare R2 para imágenes

- **Contexto**: el disco de Render es efímero; las fotos de clientes son datos personales y no deben ser públicas.
- **Decisión**: almacenamiento S3-compatible en Cloudflare R2 vía `boto3` (`STORAGE_BACKEND=s3`), con prefijo público `products/` y privado `customers/` (URLs prefirmadas de 10 min solo para el admin). Backend `local` para desarrollo.
- **Consecuencias**: (+) 10 GB gratis sin costo de egreso; privacidad por diseño; código desacoplado por el protocolo `Storage`. (−) configuración de token, CORS y acceso público; si R2 no permite exponer solo un prefijo, se usan dos buckets (registrar aquí).

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

### Pendientes de decidir (detectados en la documentación)

- Idempotencia del resumen diario cuando lo disparan APScheduler y GitHub cron el mismo día (propuesta: omitir si ya existe evento `summary.daily` con la misma fecha).
- Uno o dos buckets en R2 según soporte de acceso público por prefijo.
- Definición exacta de `simulations_total` en `/admin/metrics/summary` (propuesta en [08 §2](08-dashboard-kpis.md): completadas, incluidas reutilizadas; "generadas" = completadas sin `reused_from_id`).
- Comportamiento al iniciar en `production` con secretos por defecto (`change-me-…`): advertir o negarse a arrancar.
