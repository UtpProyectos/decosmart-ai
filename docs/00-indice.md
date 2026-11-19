# 00 — Índice de documentación

> Proyecto **DECOSMART AI**: plataforma inteligente de venta de muebles con asistente IA, simulación de ambientes y automatización comercial.
> Fecha de referencia de decisiones y precios: **2026-11-18**.
> Regla de precedencia: si un documento contradice a [`CODEX_HANDOFF.md`](CODEX_HANDOFF.md), manda el handoff.

## 1. Documentos

| # | Archivo | Contenido (una línea) |
|---|---|---|
| 00 | [00-indice.md](00-indice.md) | Este índice y el mapa de entregables → archivos. |
| 01 | [01-proyecto-problema-objetivos.md](01-proyecto-problema-objetivos.md) | Nombre formal, descripción, problema, objetivos SMART, justificación de tecnologías y stack, alcance y fuera de alcance. |
| 02 | [02-arquitectura.md](02-arquitectura.md) | Diagrama de componentes, diagramas de secuencia (chat, simulación, cotización/pedido, despliegue), despliegue local vs producción, decisiones de arquitectura. |
| 03 | [03-modelo-datos.md](03-modelo-datos.md) | ERD en Mermaid, diseño de cada tabla, conceptos (conversación ≠ consulta ≠ cotización ≠ pedido ≠ venta) y seed de 6 productos. |
| 04 | [04-api-contratos.md](04-api-contratos.md) | Endpoints públicos, admin y webhook de Telegram con ejemplos JSON, autenticación, transiciones de estado y códigos de error. |
| 05 | [05-agente-ia-prompts.md](05-agente-ia-prompts.md) | Enfoque del agente (Responses API + function calling), herramientas en JSON Schema, prompt de sistema, prompt de simulación y textos fijos del bot. |
| 06 | [06-seguridad-privacidad.md](06-seguridad-privacidad.md) | Secretos, autenticación admin, webhook, CORS, rate limits, validación de imágenes, defensas contra prompt injection, privacidad (Ley N° 29733), amenazas y checklist QA. |
| 07 | [07-presupuesto-costos.md](07-presupuesto-costos.md) | Precios verificados, fórmulas, estimación de la campaña de pruebas, peor caso, mecanismos de control y optimización de imágenes. |
| 08 | [08-dashboard-kpis.md](08-dashboard-kpis.md) | Páginas del dashboard Streamlit, definición y fórmula de cada KPI, fuente (endpoint/tabla) y wireframe. |
| 09 | [09-plan-pruebas.md](09-plan-pruebas.md) | Estrategia de pruebas, ~35 casos de prueba, criterios de aceptación por módulo, set anti-alucinación de 20 preguntas y checklist de evidencias. |
| 10 | [10-devops.md](10-devops.md) | Docker y Compose, runbook local (Windows), workflows de GitHub Actions, Render, Supabase (Postgres + Storage), Telegram, OpenAI, n8n opcional, rollback. |
| 11 | [11-backlog-equipo.md](11-backlog-equipo.md) | Backlog por fases en historias de usuario (MoSCoW, puntos, responsable, criterios), Gantt de 4 semanas, RACI y flujo Git. |
| 12 | [12-matriz-rubrica.md](12-matriz-rubrica.md) | Matriz de cumplimiento de los 9 criterios de la rúbrica con evidencias, responsables y estado. |
| 13 | [13-informe-tecnico-estructura.md](13-informe-tecnico-estructura.md) | Estructura del informe técnico: secciones, qué escribir, de qué documento extraerlo y extensión sugerida. |
| 14 | [14-guion-demo.md](14-guion-demo.md) | Guion de demostración de ≤5 minutos con tiempos, frases exactas, checklist previo y plan de contingencia. |
| — | [CODEX_HANDOFF.md](CODEX_HANDOFF.md) | **Fuente única de verdad técnica** para implementar: estructura del repo, stack, variables de entorno, módulos, orden de implementación y definición de "hecho". |
| — | [DECISIONES.md](DECISIONES.md) | Registro de decisiones de arquitectura (ADR-001…ADR-010) y bitácora de decisiones durante la implementación. |
| — | [`../AGENTS.md`](../AGENTS.md) | Reglas duras para agentes de código (Codex, Claude, etc.). |

## 2. Mapa de entregables → archivos

> La numeración corresponde a los 22 entregables solicitados para el proyecto. La columna "Entregable" resume el contenido esperado; si la redacción oficial difiere, reemplazar el texto manteniendo el archivo destino.

| N° | Entregable | Archivo |
|---|---|---|
| 1 | Nombre del proyecto | [01](01-proyecto-problema-objetivos.md) §1 |
| 2 | Descripción formal | [01](01-proyecto-problema-objetivos.md) §2 |
| 3 | Planteamiento del problema | [01](01-proyecto-problema-objetivos.md) §3 |
| 4 | Objetivo general y específicos | [01](01-proyecto-problema-objetivos.md) §4 |
| 5 | Justificación de tecnologías emergentes, stack y alcance | [01](01-proyecto-problema-objetivos.md) §5–§7 |
| 6 | Arquitectura del sistema | [02](02-arquitectura.md) §1, §3 |
| 7 | Diagramas de flujo / secuencia | [02](02-arquitectura.md) §2 |
| 8 | Modelo entidad-relación (ERD) | [03](03-modelo-datos.md) |
| 9 | Diseño de tablas | [03](03-modelo-datos.md) |
| 10 | Contratos de API / endpoints | [04](04-api-contratos.md) |
| 11 | Diseño del agente IA y herramientas | [05](05-agente-ia-prompts.md) §1–§3 |
| 12 | Prompts (sistema y simulación) | [05](05-agente-ia-prompts.md) §4–§6 |
| 13 | Seguridad y privacidad | [06](06-seguridad-privacidad.md) |
| 14 | Presupuesto y control de costos de API | [07](07-presupuesto-costos.md) |
| 15 | Dashboard y KPIs | [08](08-dashboard-kpis.md) |
| 16 | Plan de pruebas | [09](09-plan-pruebas.md) |
| 17 | DevOps: Docker, CI/CD y despliegue | [10](10-devops.md) |
| 18 | Backlog del proyecto | [11](11-backlog-equipo.md) §1–§2 |
| 19 | División del trabajo del equipo | [11](11-backlog-equipo.md) §3–§4 |
| 20 | Matriz de cumplimiento de la rúbrica | [12](12-matriz-rubrica.md) |
| 21 | Estructura del informe técnico | [13](13-informe-tecnico-estructura.md) |
| 22 | Guion de la demostración | [14](14-guion-demo.md) |
| — | Traspaso técnico para agentes de código (Codex) | [CODEX_HANDOFF.md](CODEX_HANDOFF.md) |

## 3. Rutas de lectura recomendadas

| Rol | Orden sugerido |
|---|---|
| Agente de código / desarrollador | `AGENTS.md` → `CODEX_HANDOFF.md` → 03 → 04 → 05 → 07 → `DECISIONES.md` |
| Dev A (frontend/tienda) | 01 → 02 → 04 → `CODEX_HANDOFF.md` §5.9 → 09 |
| Dev B (backend + bot + IA) | `CODEX_HANDOFF.md` → 03 → 04 → 05 → 06 → 07 |
| Dev C (automatización + dashboard + DevOps) | `CODEX_HANDOFF.md` §5.7–§6 → 08 → 10 |
| Integrante 4 (documentación, PPT, QA) | 01 → 02 → 09 → 12 → 13 → 14 |
| Docente / evaluador | 01 → 02 → 12 → 14 |

## 4. Convenciones de etiquetado

En toda la documentación se usan tres etiquetas de alcance:

| Etiqueta | Significado |
|---|---|
| **Implementable (MVP)** | Se construye, prueba y demuestra en el proyecto. |
| **Experimental** | Se construye pero su resultado es variable o es opcional (simulación visual con IA, n8n, `IMAGE_SIZE=auto`). |
| **Futuro** | Se documenta, **no** se implementa (pagos reales, login de clientes, AR/VR, multi-idioma, CRUD admin completo, embeddings, WhatsApp). |
