# 02 — Arquitectura del sistema

> Entregables 6 y 7. Detalle de módulos en [`CODEX_HANDOFF.md`](CODEX_HANDOFF.md) §2 y §5; endpoints en [04](04-api-contratos.md); tablas en [03](03-modelo-datos.md).

## 1. Diagrama de componentes

```mermaid
flowchart LR
    subgraph Usuarios
        CW["Cliente web<br/>(navegador)"]
        CT["Cliente Telegram<br/>(app móvil/escritorio)"]
        ADM["Administrador<br/>(chat admin + dashboard)"]
    end

    subgraph Render["Render (plan free)"]
        FE["Frontend React + Vite<br/>static site decosmart-web"]
        DASH["Dashboard Streamlit<br/>web decosmart-dashboard"]
        subgraph BE["Backend FastAPI — web decosmart-api"]
            PUB["API pública<br/>/api/*"]
            ADMAPI["API admin<br/>/admin/* (X-Admin-Key)"]
            WH["Webhook Telegram<br/>/telegram/webhook/{secret}"]
            BOT["Bot: handlers +<br/>máquina de estados"]
            AG["Agente IA<br/>runner + tools + guard"]
            SIM["Simulador<br/>simulation/service + imaging"]
            AUT["Automatización<br/>events + handlers + APScheduler"]
            BUD["Budget guard<br/>pricing + api_usage"]
            STO["Storage<br/>local | s3"]
            SVC["Servicios de dominio<br/>catalog, quotes, orders, metrics"]
        end
    end

    subgraph Externos["Servicios externos"]
        OAI["OpenAI API<br/>Responses + Images (edit) + Moderation"]
        TG["Telegram Bot API"]
        SUPADB[("Supabase Postgres<br/>session pooler")]
        SUPAST[("Supabase Storage<br/>bucket privado · customers/")]
        N8N["n8n (opcional)"]
    end

    subgraph GH["GitHub"]
        CI["Actions: ci.yml"]
        DEP["Actions: deploy.yml<br/>(deploy hooks)"]
        CRON["Actions: daily-summary.yml<br/>(cron 20:00 Lima)"]
    end

    CW -->|HTTPS| FE
    FE -->|fetch VITE_API_URL| PUB
    CT <-->|mensajes| TG
    TG -->|Update POST + secret token| WH
    WH --> BOT
    BOT --> AG
    BOT --> SIM
    AG --> SVC
    AG --> BUD
    SIM --> BUD
    SIM --> STO
    BUD -->|solo si AI_MODE=live| OAI
    BOT -->|httpx sendMessage/sendPhoto| TG
    PUB --> SVC
    ADMAPI --> SVC
    SVC --> AUT
    AUT -->|notificaciones| TG
    AUT -.->|POST evento, 3 s| N8N
    SVC --> SUPADB
    BUD --> SUPADB
    STO --> SUPAST
    ADM --> DASH
    DASH -->|X-Admin-Key| ADMAPI
    TG -->|alertas| ADM
    CI --> DEP
    DEP -->|POST deploy hook| Render
    CRON -->|POST /admin/jobs/daily-summary| ADMAPI
```

### Responsabilidad de cada componente

| Componente | Código | Responsabilidad |
|---|---|---|
| Frontend | `frontend/src/` | Catálogo, detalle, carrito (zustand + localStorage), cotización, checkout demo, deep link a Telegram. Nunca hardcodea precios. |
| API pública | `app/api/public.py` | Catálogo, cotizaciones, pedidos, config pública. CORS restringido + rate limit. |
| API admin | `app/api/admin.py` | Métricas, uso de API, eventos, errores, simulaciones, PATCH de estados/stock, jobs. |
| Webhook Telegram | `app/api/telegram.py` | Valida secreto, responde 200 inmediato y procesa en `BackgroundTasks`. |
| Bot | `app/bot/` | Máquina de estados (`conversations.state`), router de reglas sin LLM, teclados, textos fijos, cliente `httpx`. |
| Agente IA | `app/agent/` | Bucle de *function calling* con la Responses API, herramientas sobre servicios, validador anti-alucinación. |
| Simulador | `app/simulation/`, `app/imaging/` | Cuotas, caché, prompt, `images.edit`, optimización de entrada/salida, rating. |
| Automatización | `app/automation/` | `emit()` de eventos, handlers de notificación, scheduler (resumen, expiración, limpieza), reenvío a n8n. |
| Budget guard | `app/services/budget.py`, `app/core/pricing.py` | Estima costo, bloquea si se excede `BUDGET_USD_LIMIT`, registra `api_usage`. |
| Storage | `app/storage/` | Protocolo `put/get/url/delete` con backend local o S3 (Supabase Storage). |
| Proveedor IA | `app/ai/` | `AIProvider` con `OpenAIProvider` y `MockProvider` (`AI_MODE`). |
| Dashboard | `dashboard/` | KPIs vía `/admin/*` con `st.cache_data(ttl=30)`. |

## 2. Diagramas de secuencia

### 2.1 Consulta por chat con *tool calling* y guardia

```mermaid
sequenceDiagram
    autonumber
    actor C as Cliente
    participant TG as Telegram
    participant WH as Webhook
    participant H as bot.handlers
    participant R as agent.runner
    participant B as budget
    participant P as AIProvider (OpenAI/Mock)
    participant T as agent.tools
    participant DB as PostgreSQL
    participant G as agent.guard

    C->>TG: "¿Cuánto cuesta el sofá Oslo y qué medidas tiene?"
    TG->>WH: POST Update (secret token)
    WH-->>TG: 200 {"ok":true}
    WH->>H: handle_update (BackgroundTasks)
    H->>H: idempotencia update_id, rate limit 20/min, truncar >1000 chars
    H->>DB: guardar message (user)
    H->>H: router de reglas (no aplica: texto libre)
    H->>R: run_agent_turn(conversation, text)
    R->>B: check_llm(customer)
    alt presupuesto o límite diario excedido
        B-->>R: denegado
        R-->>H: texto ai_unavailable
    else permitido
        R->>P: responses.create(instructions, últimos 6 mensajes, tools)
        P-->>R: function_call get_product("DS-SOF-001")
        R->>T: dispatch(get_product, args, ctx con customer_id del servidor)
        T->>DB: SELECT producto
        T->>DB: INSERT inquiry (price)
        T-->>R: JSON compacto {price_usd:"649.00", dims_cm:"210x85x90"}
        R->>P: responses.create(+ function_call_output)
        P-->>R: texto final
        R->>B: registrar api_usage (tokens, costo) por cada llamada
        R->>G: validate(texto, resultados de tools)
        alt número no presente en resultados
            G-->>R: reemplazar por render_product_card + error_logs unverified_number
        else válido
            G-->>R: texto OK
        end
        R-->>H: AgentReply(text, buttons, side_effects)
    end
    H->>DB: guardar message (assistant)
    H->>TG: sendMessage
    TG-->>C: respuesta con datos reales
```

### 2.2 Flujo completo de simulación

```mermaid
sequenceDiagram
    autonumber
    actor C as Cliente
    participant H as bot.handlers
    participant S as simulation.service
    participant B as budget
    participant I as imaging.pipeline
    participant ST as Storage (Supabase)
    participant P as AIProvider
    participant DB as PostgreSQL
    participant TG as Telegram

    C->>H: botón Simular (simulate:{id}) o tool start_simulation
    H->>S: prepare(customer, product)
    S->>DB: verificar simulations_used < 2 y cuota diaria
    alt sin cuota
        H-->>C: quota_exhausted
    end
    S->>DB: INSERT simulation (awaiting_photo)
    alt photo_consent_at nulo
        H-->>C: photo_consent [Acepto][Cancelar]
        C->>H: consent:yes
        H->>DB: customers.photo_consent_at = now
    end
    H-->>C: ask_photo
    C->>H: foto
    H->>TG: getFile + descarga (mayor resolución)
    H->>I: optimize_input (tipo, ≤10 MB, lado menor ≥320, EXIF fuera, ≤1280 px, JPEG 85)
    I-->>H: jpeg + meta (sha256)
    H->>ST: put customers/{cid}/inputs/{uuid}.jpg
    H-->>C: ask_dimensions
    C->>H: "300 x 250#59; junto a la ventana"
    H->>H: parse regex, metros→cm, placement_hint ≤80 chars
    H-->>C: confirm_simulation (+ aviso si mueble > ancho) [Generar][Cancelar]
    C->>H: sim:go:{sim_id}
    H->>S: run(simulation_id)
    S->>DB: cuotas: cliente, día
    S->>B: can_spend(estimate_image_cost)
    alt bloqueado
        S->>DB: status = blocked_quota
        S-->>C: quota_exhausted / budget_exhausted
    else permitido
        S->>DB: buscar completed con mismo cache_key
        alt cache hit
            S->>DB: copiar output_key, reused_from_id, cost 0 (no consume cuota)
        else cache miss
            S->>DB: status = processing
            S-->>C: processing
            S->>P: moderación placement_hint (live)
            S->>P: images.edit([habitación, referencia], prompt, 1024x1024, low)
            P-->>S: b64 imagen + usage
            S->>I: optimize_output (≤768 px, JPEG/WebP, ≤400 KB)
            S->>ST: put customers/{cid}/outputs/{sim_id}.jpg
            S->>B: api_usage (costo estimado conservador)
            S->>DB: simulations_used += 1, completed, evento simulation.completed
        end
        S->>TG: sendPhoto + result_caption + ⭐1..⭐5
        C->>H: rate:{sim_id}:4
        H->>DB: INSERT simulation_ratings, evento simulation.rated
        H-->>C: gracias + ofrecer cotizar
    end
    Note over S,DB: Error del proveedor → status failed, error_logs, simulation.failed, NO consume cuota
```

### 2.3 Cotización, pedido demo y notificación al admin

```mermaid
sequenceDiagram
    autonumber
    actor C as Cliente (Telegram)
    participant H as bot.handlers
    participant Q as services.quotes / orders
    participant E as automation.events
    participant AH as automation.handlers
    participant DB as PostgreSQL
    participant TG as Telegram
    actor A as Admin

    C->>H: botón Cotizar (quote:{id}) o tool create_quote
    H->>Q: create_quote(customer, items, channel=telegram)
    Q->>DB: validar stock (sin reservar), congelar unit_price, code COT-AAAAMMDD-NNNN
    Q->>E: emit quote.created
    E->>DB: INSERT events
    E->>AH: handler quote.created
    AH->>TG: enviar cotización formateada al cliente
    AH->>TG: notificar admin
    TG-->>C: "Cotización COT-… Total US$…, válida hasta …" [Hacer pedido]
    C->>H: order:{quote_code}
    H-->>C: pedir teléfono y dirección (estado order_contact)
    C->>H: "+51 999… - Av. …"
    H->>Q: create_order(quote_code, contacto)
    Q->>DB: order pending, is_demo=true, quote → accepted
    Q->>E: emit order.created
    E->>AH: handler order.created
    AH->>TG: "🛒 Nuevo pedido demo PED-… US$… (cliente, canal)"
    TG-->>A: notificación
    E-->>E: POST a N8N_WEBHOOK_URL si existe (opcional)
    A->>Q: PATCH /admin/orders/{code} {"status":"confirmed"}
    Q->>DB: descontar stock
    alt stock ≤ LOW_STOCK_THRESHOLD
        Q->>E: emit product.low_stock
        AH->>TG: "⚠️ Stock bajo: … quedan N"
    end
    Q->>E: emit order.status_changed → notificar cliente
```

### 2.4 Flujo de despliegue

```mermaid
sequenceDiagram
    autonumber
    actor D as Desarrollador
    participant GH as GitHub
    participant CI as Actions ci.yml
    participant DP as Actions deploy.yml
    participant RD as Render
    participant NE as Supabase Postgres
    participant TG as Telegram

    D->>GH: push feat/* + Pull Request
    GH->>CI: backend (ruff, pytest SQLite, pytest Postgres), frontend (lint, vitest, build), dashboard (py_compile), docker build ×3
    CI-->>GH: checks verdes (AI_MODE=mock, sin OpenAI)
    D->>GH: review + merge a main
    GH->>CI: CI en main
    CI-->>DP: workflow_run success
    DP->>RD: POST RENDER_DEPLOY_HOOK_BACKEND / FRONTEND / DASHBOARD
    RD->>RD: build Docker / npm run build
    RD->>NE: lifespan: alembic upgrade head + seed idempotente
    RD-->>DP: servicio live, healthCheck /health
    Note over D,TG: Una sola vez: python scripts/set_webhook.py → setWebhook(PUBLIC_BASE_URL/telegram/webhook/{secret}, secret_token)
```

## 3. Despliegue: local vs producción

```mermaid
flowchart TB
    subgraph LOCAL["Local — docker compose (Windows + Docker Desktop)"]
        LFE["frontend<br/>nginx :5173→80"]
        LBE["backend<br/>uvicorn :8000<br/>TELEGRAM_MODE=polling<br/>STORAGE_BACKEND=local"]
        LDB[("db<br/>postgres:16-alpine<br/>volumen pgdata")]
        LDA["dashboard<br/>streamlit :8501"]
        LVOL[["./backend/storage<br/>→ /app/storage"]]
        LFE --> LBE
        LDA -->|http://backend:8000| LBE
        LBE --> LDB
        LBE --> LVOL
    end
    LBE -->|getUpdates polling| TGL["Telegram Bot API"]
    LBE -.->|solo AI_MODE=live| OAIL["OpenAI"]

    subgraph PROD["Producción — Render free"]
        PFE["decosmart-web<br/>static site (dist)"]
        PBE["decosmart-api<br/>Docker, /health<br/>TELEGRAM_MODE=webhook<br/>STORAGE_BACKEND=s3"]
        PDA["decosmart-dashboard<br/>Docker"]
        PFE --> PBE
        PDA --> PBE
    end
    PBE --> PNE[("Supabase Postgres<br/>session pooler :5432<br/>sslmode=require")]
    PBE --> PST[("Supabase Storage<br/>API S3, bucket privado")]
    TGP["Telegram Bot API"] -->|webhook| PBE
    PBE --> OAIP["OpenAI"]
```

| Aspecto | Local | Producción |
|---|---|---|
| Telegram | `polling` (hilo daemon en `lifespan`) | `webhook` con `secret_token` |
| BD | Supabase (por defecto, `DATABASE_URL` de `.env`) o contenedor `postgres:16-alpine` opcional (`--profile localdb`) | Supabase Postgres (free, persistente; session pooler) |
| Imágenes | Disco local `./backend/storage` servido en `/media/*` | Supabase Storage: bucket privado, solo `customers/` con URL prefirmada; catálogo servido por el backend en `/static/products` |
| IA | `AI_MODE=mock` por defecto | `AI_MODE=live` solo en sesiones controladas |
| Scheduler | APScheduler | APScheduler + respaldo `daily-summary.yml` |
| Frontend | nginx en contenedor | Static site de Render con rewrite `/* → /index.html` |

## 4. Decisiones clave de arquitectura

Resumen; el registro formal está en [`DECISIONES.md`](DECISIONES.md).

| Decisión | Justificación |
|---|---|
| **Bot dentro del backend** | Un solo servicio desplegable (importante en Render free) y acceso directo a servicios y BD sin una segunda API interna. El webhook es solo un endpoint más de FastAPI. |
| **Cliente Telegram propio con `httpx`** | Evita el bucle de eventos de `python-telegram-bot`; el mismo `handle_update(update: dict)` sirve para webhook y polling; tests con `respx` sin red. |
| **SQLAlchemy 2.0 síncrono** | Endpoints sync en threadpool bastan para la carga de un prototipo; tests más simples (SQLite) y menos errores de concurrencia. |
| **Modo mock (`AI_MODE=mock`)** | `MockProvider` llama a las mismas herramientas reales con reglas por palabras clave: desarrollo, CI y contingencia de demo con costo 0. |
| **Sin frameworks de agentes** | El bucle de *function calling* cabe en ~80 líneas, es auditable y permite inyectar el `customer_id` desde el servidor y aplicar la guardia y el presupuesto en un único punto. |
| **Router de reglas antes del LLM** | Saludos, menú, botones y comandos no gastan tokens. |
| **Guardias en el servidor** | Anti-alucinación (`guard.py`) y presupuesto (`budget.py`) no dependen del comportamiento del modelo. |
| **Procesamiento en `BackgroundTasks`** | El webhook responde 200 de inmediato; la imagen (hasta ~60 s) se genera fuera del ciclo de respuesta, evitando reintentos de Telegram. |
| **Storage desacoplado** | El protocolo `Storage` permite disco local en desarrollo y Supabase Storage (API S3) en producción sin cambiar el código de negocio. |
