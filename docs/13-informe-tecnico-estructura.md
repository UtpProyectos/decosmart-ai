# 13 — Estructura del informe técnico

> Entregable 21. Responsable de integración y redacción final: Integrante 4; cada desarrollador redacta las secciones de su módulo.
> Formato sugerido: A4, Times New Roman/Arial 11–12 pt, interlineado 1.5, márgenes 2.5 cm, citas y referencias **APA 7.ª edición**. Extensión total sugerida: **40–55 páginas** sin anexos.
> Regla: el informe **resume y justifica**; los detalles técnicos completos van como anexos o se citan desde `docs/`.

## Estructura

| # | Sección | Qué incluir | Fuente en `docs/` | Págs. | Redacta |
|---|---|---|---|---|---|
| — | **Portada** | Universidad, facultad, curso, título formal ("DECOSMART AI — Plataforma inteligente de venta de muebles con asistente IA, simulación de ambientes y automatización comercial"), integrantes y roles, docente, ciudad y fecha. | 01 §1 | 1 | Int. 4 |
| — | **Resumen** | 200–250 palabras: problema, solución, 3 tecnologías, resultados medidos (precisión del agente, tiempo de simulación, gasto real vs US$ 4, CI), conclusión. 4–6 palabras clave. | 01, 07, 09 | 1 | Int. 4 |
| — | **Abstract** | Traducción fiel al inglés del resumen + *keywords*. | — | 1 | Int. 4 |
| — | **Índice** | General, de figuras y de tablas (automáticos). | — | 2 | Int. 4 |
| 1 | **Introducción** | Contexto del comercio de muebles en pymes, motivación, aporte del proyecto, organización del documento. | 01 §2–§3 | 2 | Int. 4 |
| 2 | **Planteamiento del problema** | Problemas P1–P4, consecuencias, pregunta de desarrollo, justificación (social, técnica, económica). | 01 §3, §5 | 2–3 | Int. 4 |
| 3 | **Objetivos** | Objetivo general y OE1–OE8 con indicadores. | 01 §4 | 1–2 | Int. 4 |
| 4 | **Marco teórico** | 4.1 IA generativa: LLM, *function calling*, *grounding*, alucinaciones, modelos de edición de imagen. 4.2 Automatización de procesos: bots conversacionales, arquitectura orientada a eventos, orquestación low-code (n8n). 4.3 Contenedores y CI/CD: Docker, imágenes, Compose, integración y despliegue continuos, PaaS. 4.4 Protección de datos (Ley N° 29733). | 01 §5, 06 §7 | 6–8 | Dev B (4.1), Dev C (4.2–4.3), Int. 4 (4.4) |
| 5 | **Estado del arte** | 4–6 soluciones comparables (visualizadores de muebles de grandes retailers, chatbots de e-commerce, plataformas de cotización) y tabla comparativa: canal, IA, simulación, costo, limitaciones. Posicionamiento de DECOSMART AI. | — (investigación) | 3–4 | Int. 4 + Dev A |
| 6 | **Metodología** | Scrum ligero: 4 sprints, roles, ceremonias, herramientas (GitHub Projects, PRs). Flujo Git. Uso de agentes de código y documento de traspaso. | 11 | 2 | Int. 4 |
| 7 | **Análisis de requisitos** | Tabla de requisitos funcionales (RF-01… con prioridad MoSCoW y módulo) y no funcionales (RNF: costo < US$ 4, simulación < 90 s, seguridad, privacidad, disponibilidad free tier, usabilidad 375 px, mantenibilidad/CI). Actores y casos de uso. Alcance, experimental, futuro, fuera de alcance. | 01 §6–§7, 11 §2, handoff §8 | 4–5 | Int. 4 + todos |
| 8 | **Diseño** | 8.1 Arquitectura (diagrama de componentes, despliegue). 8.2 Datos (ERD, tablas clave, conceptos consulta/cotización/pedido/venta). 8.3 API (tabla resumida de endpoints, auth, errores). 8.4 Agente (bucle, herramientas, guard, máquina de estados del bot). 8.5 Prompts (sistema y simulación, decisiones de diseño, iteraciones). 8.6 Interfaz (wireframes/capturas). | 02, 03, 04, 05, 08 | 8–10 | Dev B, Dev A (8.6), Int. 4 |
| 9 | **Implementación** | Estructura del repo, tecnologías y versiones, fragmentos de código relevantes (≤ 20 líneas c/u: bucle de tools, guard, cache_key, pipeline de imagen, emit de eventos), dificultades y soluciones. | handoff §2–§5 | 5–6 | Dev A, Dev B, Dev C |
| 10 | **DevOps** | Dockerfiles, Compose, workflows CI/CD (diagrama), Render/Supabase, matriz de entornos, rollback. | 10 | 3 | Dev C |
| 11 | **Pruebas y resultados** | Estrategia, cobertura, tabla resumida de casos (aprobados/fallidos), **métricas a reportar** (abajo), UAT, defectos y correcciones. | 09 | 4–5 | Int. 4 |
| 12 | **Costos** | Precios verificados (fecha y fuente), estimación vs real, conciliación con OpenAI, mecanismos de control, costo por simulación y por conversación. | 07 | 2 | Int. 4 + Dev B |
| 13 | **Seguridad y privacidad** | Medidas, tabla de amenazas resumida, cumplimiento de la Ley N° 29733, transparencia de IA, checklist QA. | 06 | 2 | Int. 4 |
| 14 | **Limitaciones** | Calidad variable de la simulación (escala aproximada, posibles alteraciones), dependencia de proveedores, Render free (arranque en frío), catálogo pequeño, sin pagos/login, muestra UAT reducida, precios de API cambiantes. | 01, 07 | 1 | Int. 4 |
| 15 | **Conclusiones** | Una conclusión por objetivo específico, respaldada por un indicador medido. | 01 §4, 11 | 1–2 | Todos |
| 16 | **Trabajo futuro** | Pagos, login, WhatsApp, embeddings, multi-idioma, CRUD admin, AR, mejora de la simulación (máscaras, segmentación), monitoreo. | 01 §6.3 | 1 | Int. 4 |
| — | **Referencias (APA 7)** | Mínimo 12–15: documentación oficial (OpenAI, FastAPI, Docker, GitHub Actions, Render, Telegram Bot API, Streamlit), ley peruana, artículos académicos sobre LLM, alucinación, e-commerce y automatización. | — | 2 | Int. 4 |
| — | **Anexos** | A: Manual de instalación (runbook). B: Contratos de API. C: Prompts completos. D: Set anti-alucinación con resultados. E: Capturas de evidencias. F: Encuesta UAT y resultados. G: Matriz de rúbrica. H: Backlog y Gantt. I: Enlaces (repo, URLs de producción, bot). | 04, 05, 09, 10, 11, 12 | — | Int. 4 |

## Métricas a reportar en "Pruebas y resultados"

| Métrica | Fuente | Meta |
|---|---|---|
| Cobertura de pruebas backend | `pytest --cov=app` | ≥ 70 % |
| Casos de prueba aprobados / total | Doc 09 §2 | 100 % críticos |
| Exactitud del agente (set de 20) en mock y live | Doc 09 §5 | 20/20 |
| Intervenciones del guard | `error_logs` `unverified_number` | Reportar número |
| Tiempo de respuesta del bot (p50/p95) | `messages` | p95 < 8 s |
| Tiempo de simulación (p50/p95) | `simulations` | p95 < 90 s |
| Peso y resolución de entrada/salida | Metadatos de `simulations` | ≤ 1280 px / ≤ 768 px y ≤ 400 KB |
| Simulaciones generadas / fallidas / reutilizadas | Dashboard | Reportar |
| Rating promedio de simulaciones | Dashboard | ≥ 3.5 |
| Gasto estimado vs real (OpenAI) | `/admin/usage` vs panel OpenAI | < US$ 4; desviación ≤ 25 % |
| Costo promedio por simulación y por conversación | Dashboard *Costos API* | Reportar |
| Duración del pipeline CI | GitHub Actions | < 10 min |
| Tiempo de deploy | Render | Reportar |
| Arranque en frío | Medición manual | Reportar |
| Resultados UAT por ítem | Encuesta | ≥ 3.5 / 5 |

## Guía de estilo

- Redactar en tercera persona impersonal ("se implementó", "el sistema registra").
- Cada figura y tabla numerada, con título y fuente ("Elaboración propia").
- Diagramas Mermaid exportados como PNG/SVG (Mermaid Live Editor o extensión de VS Code).
- No pegar código extenso: usar fragmentos breves y remitir al repositorio.
- Usar los términos del doc 08 §1 de forma consistente (consulta, cotización, pedido demo, venta concretada).
- Indicar siempre la fecha de verificación de precios (2026-11-18) al citar costos.
- Marcar claramente qué es MVP, experimental y futuro.

## Ejemplos de referencias (APA 7)

- Congreso de la República del Perú. (2011). *Ley N.° 29733, Ley de Protección de Datos Personales*. Diario Oficial El Peruano.
- OpenAI. (2026). *Image generation guide*. https://developers.openai.com/api/docs/guides/image-generation
- OpenAI. (2026). *GPT-5.4 nano model*. https://developers.openai.com/api/docs/models/gpt-5.4-nano
- OpenAI. (2026). *gpt-image-1-mini model*. https://developers.openai.com/api/docs/models/gpt-image-1-mini
- OpenAI. (2026). *Introducing GPT-5.4 mini and nano*. https://openai.com/index/introducing-gpt-5-4-mini-and-nano/
- Telegram. (s. f.). *Telegram Bot API*. https://core.telegram.org/bots/api
- Docker Inc. (s. f.). *Docker documentation*. https://docs.docker.com/

(Completar fecha de consulta cuando la fuente cambie con frecuencia; verificar año de publicación de cada página.)
