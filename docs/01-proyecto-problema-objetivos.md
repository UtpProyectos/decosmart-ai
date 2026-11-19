# 01 — Proyecto, problema y objetivos

> Entregables 1 a 5. Fuente técnica: [`CODEX_HANDOFF.md`](CODEX_HANDOFF.md).

## 1. Nombre del proyecto

**DECOSMART AI — Plataforma inteligente de venta de muebles con asistente IA, simulación de ambientes y automatización comercial**

Nombre comercial de la tienda ficticia: **DecoSmart**. Nombre del asistente: **Deco** (bot de Telegram `@DecoSmartBot`, configurable con `TELEGRAM_BOT_USERNAME`).

## 2. Descripción formal

DECOSMART AI es un prototipo funcional de comercio electrónico para una tienda pequeña de muebles que integra tres tecnologías emergentes:

1. **Inteligencia artificial generativa** (OpenAI API): un agente conversacional en Telegram que responde consultas de precio, medidas, stock y recomendaciones **exclusivamente a partir del catálogo real** mediante *function calling*, y un simulador que inserta un mueble del catálogo en la fotografía del ambiente del cliente mediante edición de imágenes.
2. **Automatización de procesos comerciales**: bot de atención, eventos de negocio, notificaciones automáticas al cliente y al administrador, alertas de stock bajo, expiración de cotizaciones y resumen diario; integración opcional con n8n.
3. **Contenedores y CI/CD**: todos los servicios se empaquetan con Docker, se validan con GitHub Actions y se despliegan en Render.

El sistema se compone de una tienda web (React + Vite), un backend (FastAPI + PostgreSQL) que aloja la API, el bot y el agente, un dashboard de indicadores (Streamlit) y almacenamiento de imágenes en Cloudflare R2. Opera con un presupuesto de API de **US$ 4** (límite operativo US$ 3.50 + reserva US$ 0.50), controlado por una guardia de presupuesto en el backend.

## 3. Planteamiento del problema

Las tiendas pequeñas y medianas de muebles (con catálogos de decenas de productos y uno a tres vendedores) enfrentan cuatro problemas recurrentes:

| # | Problema | Consecuencia |
|---|---|---|
| P1 | **El cliente no puede visualizar el mueble en su espacio.** Las fotos de catálogo muestran el mueble en un ambiente ajeno; las medidas en cm son abstractas para la mayoría de compradores. | Indecisión, abandono de la compra, devoluciones por "no se veía así" o "no entraba". |
| P2 | **Cotización manual y lenta.** El vendedor responde por chat, busca precios y stock en hojas de cálculo y arma la cotización a mano. | Tiempos de respuesta de horas; errores de precio; clientes que compran en otra tienda. |
| P3 | **Consultas no registradas.** Las preguntas por precio, medidas o disponibilidad se pierden en chats personales. | La tienda no sabe qué productos interesan más ni cuántas consultas se convierten en venta. |
| P4 | **Canales dispersos.** Web, redes y mensajería funcionan como islas sin trazabilidad común. | No hay indicadores, ni notificaciones oportunas (pedido nuevo, stock bajo), ni historial unificado. |

**Pregunta de investigación / desarrollo**: ¿Cómo puede una tienda pequeña de muebles usar IA generativa, automatización y prácticas DevOps, con un presupuesto mínimo, para atender consultas con datos fiables, permitir visualizar el mueble en el ambiente del cliente y registrar y medir todo el embudo comercial?

## 4. Objetivos

### 4.1 Objetivo general

Desarrollar y desplegar un prototipo funcional de plataforma de venta de muebles que integre un agente conversacional con IA generativa conectado al catálogo real, un simulador visual de ambientes, automatizaciones comerciales y un dashboard de indicadores, empaquetado en contenedores con integración y despliegue continuos, con un gasto de API de OpenAI inferior a US$ 4.

### 4.2 Objetivos específicos (SMART)

Todos se miden al cierre del proyecto (semana 4) con la evidencia indicada.

| ID | Objetivo | Indicador / meta | Evidencia |
|---|---|---|---|
| OE1 | Implementar una tienda web con catálogo de 6 productos, carrito, cotización y pedido demo. | 6/6 productos visibles con precio, medidas, colores y stock; `POST /api/quotes` devuelve código `COT-…`; usable a 375 px sin scroll horizontal. | Capturas, casos TC-WEB del doc 09. |
| OE2 | Implementar un agente IA en Telegram que responda con datos del catálogo sin alucinar. | **100 %** de coincidencia de precio/medidas/stock con la BD en el set de **20 preguntas** del doc 09 §5; 0 productos inventados. | Tabla de resultados del set anti-alucinación (mock y live). |
| OE3 | Implementar la simulación visual de un mueble en la foto del cliente. | Resultado entregado en Telegram en **< 90 s** (p95) desde la confirmación; imagen ≤ 768 px y ≤ 400 KB; rating promedio ≥ 3.5/5 en las pruebas de usuario. | `simulations.completed_at − created_at`, `/admin/simulations`. |
| OE4 | Automatizar el ciclo comercial con eventos y notificaciones. | 100 % de cotizaciones por Telegram envían el mensaje con código y total; 100 % de pedidos demo notifican al admin en < 10 s; alerta de stock bajo al cruzar `LOW_STOCK_THRESHOLD=5`; resumen diario enviado. | Tabla `events`, capturas del chat admin. |
| OE5 | Construir un dashboard con los indicadores del embudo comercial y del costo de IA. | 11+ KPIs con datos reales que distinguen consulta / cotización / pedido / venta; gasto API mostrado con % del presupuesto. | Capturas del dashboard, doc 08. |
| OE6 | Mantener el gasto de OpenAI bajo control. | Gasto total real **< US$ 4** (objetivo operativo ≤ US$ 3.50); desviación entre `api_usage` y el panel de OpenAI ≤ 25 %; 0 llamadas a OpenAI en CI. | `/admin/usage`, captura del panel de uso de OpenAI. |
| OE7 | Contenerizar y automatizar el despliegue. | `docker compose up --build` levanta 4 servicios; pipeline CI en **< 10 min**; deploy automático a Render tras merge en `main`; `/health` responde `db: ok`. | Logs de GitHub Actions, URL de Render. |
| OE8 | Asegurar privacidad y seguridad básicas. | 100 % de fotos sin EXIF/GPS; borrado automático de fotos tras `PHOTO_RETENTION_DAYS=7`; `/admin/*` responde 401 sin clave; checklist del doc 06 §9 completo. | Casos TC-SEC del doc 09. |

## 5. Justificación técnica

### 5.1 Tecnologías emergentes elegidas

| Tecnología | Por qué es emergente | Qué problema resuelve | Cómo se usa |
|---|---|---|---|
| **IA generativa (OpenAI API)** | Modelos de lenguaje con *function calling* y modelos de edición de imágenes accesibles por API a costo marginal. | P1 (visualizar) y P2 (respuesta rápida y fiable). | Responses API con herramientas sobre el catálogo (`gpt-5.4-nano`); `images.edit` con `gpt-image-1-mini` calidad `low` 1024×1024 para la simulación. |
| **Automatización de procesos** (bots, flujos, notificaciones) | Bots conversacionales y orquestación por eventos (*event-driven*, low-code como n8n) reemplazan tareas manuales repetitivas. | P2, P3 y P4. | Bot de Telegram, catálogo de eventos (`quote.created`, `order.created`, `product.low_stock`…), notificaciones, scheduler y n8n opcional. |
| **Contenedores + CI/CD** | Docker y pipelines en la nube estandarizan entornos y despliegues reproducibles. | Calidad y entrega continua del prototipo; despliegue gratuito. | 3 Dockerfiles, Docker Compose, GitHub Actions (CI, deploy, cron), Render Blueprint. |

Se descartan explícitamente AR/VR e IoT: requieren hardware o SDKs nativos que no aportan al problema con el presupuesto disponible; la simulación 2D con IA cubre P1 de forma suficiente para un prototipo.

### 5.2 Justificación del stack

| Pieza | Elección | Motivo | Alternativa descartada |
|---|---|---|---|
| Frontend | React 18 + Vite 5 + TypeScript | Ecosistema conocido por el equipo, build estático desplegable gratis. | Next.js (SSR innecesario). |
| Estado carrito | zustand + localStorage | Mínimo código, persistencia sin login. | Redux (exceso). |
| Backend | FastAPI (Python 3.11) | OpenAPI automático en `/docs`, Pydantic v2, SDK oficial de OpenAI en Python. | Node/Express (el equipo de IA trabaja en Python). |
| ORM | SQLAlchemy 2.0 **síncrono** + Alembic | Simplicidad, tests con SQLite, migraciones versionadas. | SQLAlchemy async (complejidad sin beneficio a esta escala). |
| BD | PostgreSQL 16 (Neon en prod) | Relacional, JSON, free tier persistente. | Postgres free de Render (expira a los 30 días). |
| Bot | Cliente propio con `httpx` sobre Bot API | Un solo modelo de ejecución (webhook o polling), tests con `respx`. | `python-telegram-bot` (bucle propio, difícil de testear dentro de FastAPI). |
| IA texto | Responses API, `gpt-5.4-nano` | Function calling nativo, US$ 0.20 / 1.25 por 1M tokens. | Frameworks de agentes (LangChain, CrewAI): dependencia pesada para ~80 líneas. |
| IA imagen | `gpt-image-1-mini`, `low`, 1024×1024 | ≈ US$ 0.005/imagen (tabla oficial), el más barato con edición. | `gpt-image-1` low (≈ US$ 0.011, 2× más caro). |
| Imágenes | Pillow | Redimensionado, EXIF, compresión. | — |
| Storage | Cloudflare R2 (S3-compatible, boto3) | 10 GB gratis, sin costo de egreso; disco de Render es efímero. | Disco local en Render (se pierde). |
| Scheduler | APScheduler + cron de GitHub Actions | En proceso, sin infraestructura extra; GitHub cron como respaldo cuando Render duerme. | Celery/Redis (infraestructura adicional). |
| Dashboard | Streamlit | KPIs en pocas líneas de Python. | Panel React propio (más tiempo). |
| Contenedores | Docker + Compose | Paridad local/producción. | — |
| CI/CD | GitHub Actions + deploy hooks de Render | Gratis para repos del curso, integración directa. | Jenkins (requiere servidor). |
| Hosting | Render (free) | Docker + static sites + Blueprint `render.yaml`. | Heroku (sin plan gratis). |

## 6. Alcance

### 6.1 Implementable (MVP)

- Tienda web: catálogo de 6 muebles, filtro por categoría, detalle, carrito persistente, solicitud de cotización, checkout demo (sin cobro), botón y deep link a Telegram.
- Backend: API pública y admin (`X-Admin-Key`), modelo de datos completo, seed idempotente, códigos `COT-`/`PED-`.
- Bot de Telegram con máquina de estados, router de reglas sin LLM y agente IA con 9 herramientas.
- Guardia anti-alucinación (`agent/guard.py`) y guardia de presupuesto (`services/budget.py`).
- Simulador de ambientes con consentimiento, cuotas, caché, pipeline de optimización de imágenes y rating 1–5.
- Automatización: eventos, notificaciones al cliente y admin, stock bajo, expiración de cotizaciones, limpieza de fotos, resumen diario.
- Dashboard Streamlit (6 páginas) con KPIs y costos.
- `AI_MODE=mock` completo para desarrollo, tests y contingencia.
- Docker Compose, CI/CD en GitHub Actions, despliegue en Render + Neon + R2.

### 6.2 Experimental

- **Calidad visual de la simulación**: depende del modelo; es orientativa (escala aproximada, posibles alteraciones menores del ambiente).
- **n8n**: reenvío de eventos a un workflow externo (Google Sheets / email) si `N8N_WEBHOOK_URL` está definido.
- **`IMAGE_SIZE=auto`**: tamaños 1536×1024 / 1024×1536, más caros; solo para pruebas.

### 6.3 Futuro (no se implementa)

Pagos reales, login/cuentas de clientes, AR/VR, multi-idioma, panel admin CRUD completo, recomendación por embeddings, canal WhatsApp.

## 7. Fuera de alcance (explícito)

- Cobros, pasarelas de pago, facturación electrónica o boletas.
- Gestión real de inventario multi-almacén, logística o despacho.
- Autenticación de clientes y roles múltiples (solo existe la clave admin).
- Medición exacta de espacios o garantía de que el mueble encaje físicamente.
- Realidad aumentada, realidad virtual, IoT o apps móviles nativas.
- Integraciones con ERP/CRM comerciales.
- Alta disponibilidad, escalado horizontal o SLA de producción (Render free duerme tras inactividad).
- Moderación de contenido de las fotos más allá de las validaciones técnicas y del aviso al usuario.
