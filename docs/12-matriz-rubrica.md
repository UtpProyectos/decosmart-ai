# 12 — Matriz de cumplimiento de la rúbrica

> Entregable 20.
>
> **⚠️ IMPORTANTE — ACCIÓN DEL EQUIPO**: el texto oficial de la rúbrica no estaba disponible al redactar este documento. Los 9 criterios siguientes son los **más probables** según los requisitos del curso. **Antes de entregar, reemplazar el nombre y la descripción de cada criterio por la redacción oficial** (y su puntaje), reordenar si es necesario y verificar que cada evidencia responda a lo que la rúbrica pide literalmente.
>
> Responsable de mantener este documento: Integrante 4. Estado: marcar `[x]` solo cuando la evidencia exista y esté enlazada.

## Resumen

| # | Criterio (provisional) | Responsable | Estado |
|---|---|---|---|
| C1 | Integración de ≥ 3 tecnologías emergentes | Int. 4 (consolida) | [ ] |
| C2 | Prototipo funcional | Dev A + Dev B | [ ] |
| C3 | Uso de la API de OpenAI | Dev B | [ ] |
| C4 | Prompt Engineering | Dev B | [ ] |
| C5 | Docker / contenedores | Dev C | [ ] |
| C6 | CI/CD | Dev C | [ ] |
| C7 | Arquitectura y diseño técnico | Dev B + Int. 4 | [ ] |
| C8 | Documentación técnica | Int. 4 | [ ] |
| C9 | Demostración técnica / presentación | Todos (Int. 4 coordina) | [ ] |

## Detalle por criterio

### C1 — Integración de al menos 3 tecnologías emergentes

| Cómo se cumple | Evidencia | Estado |
|---|---|---|
| **IA generativa**: agente con *function calling* (Responses API) y simulación con `images.edit`. | `backend/app/agent/`, `backend/app/simulation/`; captura de conversación y simulación en Telegram. | [ ] |
| **Automatización de procesos**: bot, eventos, notificaciones, stock bajo, resumen diario, n8n opcional. | `backend/app/automation/`, `backend/app/bot/`; capturas de notificaciones al admin; tabla `events` en dashboard (página 5). | [ ] |
| **Contenedores + CI/CD**: Docker, Compose, GitHub Actions, Render. | `docker-compose.yml`, `*/Dockerfile`, `.github/workflows/`; captura de CI verde. | [ ] |
| Las tres están **integradas** (no aisladas): un evento de la conversación IA dispara automatización y todo corre en contenedores desplegados por CI/CD. | Diagrama de componentes [02 §1](02-arquitectura.md); secuencia [02 §2.3](02-arquitectura.md). | [ ] |
| Justificación técnica de cada tecnología. | [01 §5](01-proyecto-problema-objetivos.md). | [ ] |

**Responsable**: Integrante 4 (consolida evidencias de Dev B y Dev C).

### C2 — Prototipo funcional

| Cómo se cumple | Evidencia | Estado |
|---|---|---|
| Tienda web desplegada con catálogo, carrito, cotización y pedido demo. | URL `https://decosmart-web.onrender.com`; capturas desktop y 375 px. | [ ] |
| Bot de Telegram operativo en producción. | Enlace `https://t.me/DecoSmartBot`; capturas. | [ ] |
| Backend con API documentada. | `https://decosmart-api.onrender.com/docs` y `/health` con `db: ok`. | [ ] |
| Dashboard en producción. | URL `decosmart-dashboard`; capturas de 6 páginas. | [ ] |
| Criterios de aceptación por módulo cumplidos. | [09 §4](09-plan-pruebas.md) con casos en verde. | [ ] |
| Pruebas automatizadas. | Salida de `pytest --cov`, `vitest`. | [ ] |

**Responsable**: Dev A (tienda) y Dev B (backend/bot).

### C3 — Uso de la API de OpenAI

| Cómo se cumple | Evidencia | Estado |
|---|---|---|
| Responses API con 9 herramientas `strict` sobre el catálogo real. | `backend/app/agent/tools.py`, `runner.py`; [05 §3](05-agente-ia-prompts.md). | [ ] |
| Edición de imágenes `gpt-image-1-mini`, `low`, 1024×1024. | `backend/app/ai/openai_provider.py`; registros en `/admin/simulations`. | [ ] |
| Moderación de texto libre. | `OPENAI_MODERATION=true`; fila `operation='moderation'` en `api_usage`. | [ ] |
| Control de costos y registro de uso. | `/admin/usage`; página *Costos API*; conciliación [07 §7.3](07-presupuesto-costos.md); captura del panel de uso de OpenAI (< US$ 4). | [ ] |
| Proveedor intercambiable (mock/live). | `backend/app/ai/provider.py`; tests sin OpenAI en CI. | [ ] |

**Responsable**: Dev B.

### C4 — Prompt Engineering

| Cómo se cumple | Evidencia | Estado |
|---|---|---|
| Prompt de sistema estructurado (rol, objetivo, 10 reglas, contexto dinámico). | `backend/app/agent/prompts.py`; [05 §4](05-agente-ia-prompts.md). | [ ] |
| Prompt de simulación parametrizado con datos de BD y proporciones calculadas. | `build_simulation_prompt`; [05 §5](05-agente-ia-prompts.md). | [ ] |
| Técnicas anti-alucinación: grounding por herramientas, validador post-respuesta, salidas compactas. | `guard.py`; TC-23; error_logs `unverified_number`. | [ ] |
| Defensa contra prompt injection. | Preguntas 17–20 del set [09 §5](09-plan-pruebas.md). | [ ] |
| Evaluación con set de 20 preguntas (mock y live). | Tabla de resultados 20/20. | [ ] |
| Iteraciones del prompt documentadas (versión, cambio, motivo, resultado). | Sección en el informe (doc 13) + `DECISIONES.md`. | [ ] |

**Responsable**: Dev B (con Int. 4 para la evaluación).

### C5 — Docker / contenedores

| Cómo se cumple | Evidencia | Estado |
|---|---|---|
| 3 Dockerfiles (backend, frontend multi-stage, dashboard), usuario no root. | `backend/Dockerfile`, `frontend/Dockerfile`, `dashboard/Dockerfile`. | [ ] |
| Compose con 4 servicios, healthcheck y volúmenes. | `docker-compose.yml`; captura de `docker compose ps`. | [ ] |
| Producción en contenedores (Render runtime docker). | `render.yaml`; logs de build en Render. | [ ] |
| Runbook reproducible. | [10 §2](10-devops.md). | [ ] |

**Responsable**: Dev C.

### C6 — CI/CD

| Cómo se cumple | Evidencia | Estado |
|---|---|---|
| CI en cada push/PR: lint, tests (SQLite y Postgres), build front, compilación dashboard, build Docker. | `.github/workflows/ci.yml`; captura de run verde con duración < 10 min. | [ ] |
| CD: deploy automático a Render tras CI exitoso en `main`. | `.github/workflows/deploy.yml`; captura del run y del evento de deploy en Render. | [ ] |
| Automatización programada. | `.github/workflows/daily-summary.yml`; captura del run y del mensaje recibido. | [ ] |
| Protección de rama y revisión de PRs. | Captura de *branch protection*; PRs con revisión. | [ ] |

**Responsable**: Dev C.

### C7 — Arquitectura y diseño técnico

| Cómo se cumple | Evidencia | Estado |
|---|---|---|
| Diagrama de componentes y de despliegue. | [02 §1, §3](02-arquitectura.md). | [ ] |
| Diagramas de secuencia de los 4 flujos principales. | [02 §2](02-arquitectura.md). | [ ] |
| Modelo de datos (ERD + diccionario). | [03](03-modelo-datos.md). | [ ] |
| Contratos de API. | [04](04-api-contratos.md) + OpenAPI `/docs`. | [ ] |
| Decisiones justificadas (ADR). | [`DECISIONES.md`](DECISIONES.md). | [ ] |
| Seguridad y privacidad por diseño. | [06](06-seguridad-privacidad.md). | [ ] |

**Responsable**: Dev B (técnico) e Integrante 4 (presentación).

### C8 — Documentación técnica

| Cómo se cumple | Evidencia | Estado |
|---|---|---|
| Juego completo de documentos 00–14 + handoff + ADR. | [00-indice.md](00-indice.md). | [ ] |
| Informe técnico con estructura formal y referencias APA 7. | Informe (PDF) según [13](13-informe-tecnico-estructura.md). | [ ] |
| README con instrucciones de ejecución. | `README.md`. | [ ] |
| Plan de pruebas y evidencias. | [09](09-plan-pruebas.md) + anexos del informe. | [ ] |
| Presupuesto y costos reales. | [07](07-presupuesto-costos.md) + tabla de conciliación. | [ ] |

**Responsable**: Integrante 4.

### C9 — Demostración técnica / presentación

| Cómo se cumple | Evidencia | Estado |
|---|---|---|
| Demo ≤ 5 minutos que recorre los 3 pilares tecnológicos. | Guion [14](14-guion-demo.md); 2 ensayos cronometrados. | [ ] |
| Presentación (PPT) coherente con el informe. | Archivo PPT en la entrega. | [ ] |
| Plan de contingencia (video de respaldo, modo mock). | [14 §5](14-guion-demo.md); video grabado. | [ ] |
| Todos los integrantes participan. | Reparto en el guion. | [ ] |

**Responsable**: Todos; coordina Integrante 4.

## Capturas a tomar (lista consolidada)

| # | Captura | Criterio | Responsable |
|---|---|---|---|
| 1 | Home y detalle de producto (desktop y 375 px) | C2 | Dev A |
| 2 | Cotización web con código y pedido demo "sin cobro" | C2 | Dev A |
| 3 | Conversación Telegram con precio correcto y pregunta anti-alucinación | C3, C4 | Dev B |
| 4 | Flujo de simulación completo + resultado + rating | C1, C3 | Dev B |
| 5 | Notificaciones admin (pedido, stock bajo, resumen) | C1 | Dev C |
| 6 | Dashboard: Resumen y Costos API | C2, C3 | Dev C |
| 7 | `docker compose ps` | C5 | Dev C |
| 8 | Run de CI verde + deploy | C6 | Dev C |
| 9 | Servicios en Render y `/health` | C2, C5 | Dev C |
| 10 | Panel de uso de OpenAI | C3 | Int. 4 |
| 11 | `error_logs` con `unverified_number` (guard) | C4 | Dev B |
| 12 | `/docs` (OpenAPI) | C7 | Dev B |
