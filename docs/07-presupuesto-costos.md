# 07 — Presupuesto y control de costos de la API

> Entregable 14. Implementación: `backend/app/core/pricing.py` y `backend/app/services/budget.py` ([`CODEX_HANDOFF.md`](CODEX_HANDOFF.md) §5.6).
> Presupuesto total: **US$ 4.00** de crédito OpenAI = **US$ 3.50 límite operativo** (`BUDGET_USD_LIMIT=3.50`) + **US$ 0.50 de reserva** (nunca se planifica gastarla; cubre desviaciones entre la estimación y la facturación real).

## 1. Estrategia

1. **Desarrollar en mock** (`AI_MODE=mock`, costo 0): toda la lógica, tests y CI funcionan sin OpenAI.
2. **Modelos más baratos que cumplen**: `gpt-5.4-nano` para chat y `gpt-image-1-mini` en calidad `low`, 1024×1024, para imágenes.
3. **No llamar al LLM cuando no hace falta**: router de reglas, botones y textos fijos.
4. **Medir cada llamada** (`api_usage`) y **bloquear antes de gastar** (guardia de presupuesto).
5. **Estimar de forma conservadora** y **conciliar** con el panel de uso de OpenAI.

## 2. Precios verificados

Verificación: **2026-11-18** en developers.openai.com (valores en `pricing.py`, `PRICING_VERIFIED_AT = "2026-11-18"`).

### 2.1 Modelos de texto (USD por 1M tokens)

| Modelo | Entrada | Entrada en caché | Salida | Uso en el proyecto |
|---|---|---|---|---|
| **gpt-5.4-nano** | 0.20 | 0.02 (*revalidar*) | 1.25 | **Por defecto** (`OPENAI_CHAT_MODEL`) |
| gpt-5.4-mini | 0.75 | 0.075 | 4.50 | Alternativa si la calidad de nano no alcanza |
| gpt-5-mini | 0.25 | 0.025 | 2.00 | Solo tabla de referencia |
| gpt-5-nano | 0.05 | 0.005 | 0.40 | Solo tabla de referencia |

### 2.2 Modelos de imagen (USD por imagen, calidad `low`, 1024×1024, tabla oficial)

| Modelo | Por imagen | + recargo conservador de entrada (edit) | Estimación usada |
|---|---|---|---|
| **gpt-image-1-mini** | ≈ 0.005 | 0.006 | **0.011** (por defecto) |
| gpt-image-2 | ≈ 0.006 | 0.006 | 0.012 |
| gpt-image-1.5 | ≈ 0.009 | 0.006 | 0.015 |
| gpt-image-1 | ≈ 0.011 | 0.006 | 0.017 |
| Modelo/tamaño no tabulado | — | — | **0.05** (`DEFAULT_UNKNOWN_IMAGE_COST`) |

**Advertencia**: reportes de la comunidad indican que la facturación real de edición de imágenes (por tokens de imagen de entrada y salida) puede diferir de la tabla por imagen. Por eso el proyecto suma `IMAGE_INPUT_SURCHARGE_USD = 0.006` a cada edición y concilia con el panel de uso de OpenAI (§6.3). El endpoint de moderación es gratuito.

Fuentes:
- https://developers.openai.com/api/docs/models/gpt-image-1-mini
- https://developers.openai.com/api/docs/guides/image-generation
- https://developers.openai.com/api/docs/models/gpt-5.4-nano
- https://openai.com/index/introducing-gpt-5-4-mini-and-nano/
- https://developers.openai.com/api/docs/pricing

## 3. Fórmulas de costo

**Chat** (`pricing.estimate_chat(model, usage)`), por cada llamada a la Responses API:

```
costo_chat = [ (input_tokens − cached_input_tokens) × p_in
             + cached_input_tokens × p_cached
             + output_tokens × p_out ] / 1 000 000
```
Los tokens de razonamiento se facturan como salida y vienen incluidos en `output_tokens`. Modelo desconocido → tarifa del modelo más caro de la tabla.

**Turno de chat** = suma de sus llamadas (1 llamada sin herramientas; 2 o más con herramientas; máximo `AGENT_MAX_TOOL_ROUNDS + 1 = 5`).

**Edición de imagen** (`pricing.estimate_image_edit(model, quality, size, usage)`):
```
costo_imagen = IMAGE_OUTPUT_PER_IMAGE[(model, quality, size)] + IMAGE_INPUT_SURCHARGE_USD
             = 0.005 + 0.006 = US$ 0.011   (gpt-image-1-mini, low, 1024x1024)
```
Si `usage` trae tokens, se guardan en `api_usage` (`image_input_tokens`, `output_tokens`) para conciliación, pero el costo registrado sigue siendo la estimación conservadora.

**Gasto acumulado**: `budget.spent_usd = SUM(api_usage.cost_usd) WHERE mode = 'live'`.
**Permiso**: `budget.can_spend(est) ⇔ spent_usd + est ≤ BUDGET_USD_LIMIT`.

## 4. Estimación de la campaña de pruebas

### 4.1 Supuestos (escenario base)

| Concepto | Valor |
|---|---|
| Turnos de chat que llegan al LLM | 300 (botones y comandos no cuentan) |
| Llamadas por turno (promedio, con herramientas) | 2 |
| Tokens promedio por llamada | 2 500 entrada (sistema + 9 tools + historial + resultados) / 250 salida |
| Simulaciones nuevas generadas | 40 (sin contar reutilizaciones por caché, que cuestan 0) |
| Moderaciones | ~40 (gratis) |

### 4.2 Cálculo

| Partida | Cálculo | US$ |
|---|---|---|
| Costo por llamada (nano) | 2 500 × 0.20/1M + 250 × 1.25/1M = 0.000500 + 0.0003125 | 0.0008125 |
| Chat: 300 turnos × 2 llamadas = 600 llamadas | 600 × 0.0008125 | **0.49** |
| Simulaciones: 40 × 0.011 | | **0.44** |
| Moderación | 40 × 0 | 0.00 |
| **Total escenario base** | | **≈ 0.93** |
| % del límite operativo (3.50) | 0.93 / 3.50 | **26.6 %** |
| Margen restante hasta el límite | 3.50 − 0.93 | 2.57 |

### 4.3 Escenario pesimista (mismo volumen, condiciones peores)

| Partida | Supuesto | US$ |
|---|---|---|
| Chat | 300 turnos × 2.5 llamadas = 750 llamadas; 4 000 entrada / 400 salida (más razonamiento) → 0.0008 + 0.0005 = 0.0013 por llamada | 0.98 |
| Simulaciones | Facturación real 3× la estimación de tabla: 40 × 0.033 | 1.32 |
| **Total pesimista** | | **≈ 2.30 (66 % del límite)** |

### 4.4 Peor caso (error de configuración)

Si por error se usa `gpt-5.4-mini` con el volumen pesimista: 750 × (4 000 × 0.75/1M + 400 × 4.50/1M) = 750 × 0.0048 = **US$ 3.60** solo en chat. **La guardia bloquea al llegar a US$ 3.50** (las llamadas posteriores reciben `ai_unavailable` / `budget_exhausted`) y la reserva de US$ 0.50 absorbe la desviación de estimación. El aviso al 80 % (US$ 2.80) llega antes al admin, que puede volver a `AI_MODE=mock`.

### 4.5 Techos impuestos por configuración

| Límite | Valor | Gasto máximo estimado |
|---|---|---|
| Simulaciones por día (`MAX_SIMULATIONS_PER_DAY=15`) | 15 × 0.011 | US$ 0.165 / día |
| Simulaciones por cliente (`MAX_SIMULATIONS_PER_CUSTOMER=2`) | 2 × 0.011 | US$ 0.022 / cliente |
| Mensajes LLM por cliente/día (`MAX_LLM_MESSAGES_PER_CUSTOMER_PER_DAY=40`) | 40 × 5 llamadas × ≤ 0.0014 | ≤ US$ 0.28 / cliente / día |
| Presupuesto global | `BUDGET_USD_LIMIT=3.50` | US$ 3.50 total |

## 5. Mecanismos de control

| # | Mecanismo | Dónde | Efecto |
|---|---|---|---|
| 1 | `AI_MODE=mock` | `ai/provider.py` | `MockProvider` llama a las herramientas reales con reglas; costo 0. Por defecto en local, tests y CI. |
| 2 | Arranque seguro | `core/config.py` | `AI_MODE=live` sin `OPENAI_API_KEY` → fuerza `mock` y advierte. |
| 3 | Guardia de presupuesto | `services/budget.py` | `check_llm()` y `can_spend()` antes de **toda** llamada; `track()` registra latencia, éxito y costo en `api_usage`. |
| 4 | Límites por cliente y por día | `budget.py`, `simulation/service.py` | 40 mensajes LLM/cliente/día; 2 simulaciones/cliente; 15 simulaciones/día. |
| 5 | Router de reglas antes del LLM | `bot/handlers.py` | `/start`, `hola`, `menu`, `catálogo`, `ayuda`, botones y comandos sin tokens. |
| 6 | Recorte de historial | `agent/runner.py` | Solo `AGENT_HISTORY_TURNS=6` mensajes user/assistant, sin tool outputs antiguos. |
| 7 | Tope de salida | `OPENAI_CHAT_MAX_OUTPUT_TOKENS=400`, `OPENAI_REASONING_EFFORT=low` | Limita tokens de salida y razonamiento. |
| 8 | Tope de rondas | `AGENT_MAX_TOOL_ROUNDS=4` | Máximo 5 llamadas por turno. |
| 9 | Salidas de herramientas compactas | `agent/tools.py` | JSON mínimo (`ref`, `name`, `price_usd`, `stock`, `dims_cm`, `colors`). |
| 10 | Truncado de entrada | `bot/handlers.py` | Mensajes > 1000 caracteres se truncan. |
| 11 | Prompt de simulación en servidor | `agent/prompts.py` | No se gasta una llamada de chat para redactarlo. |
| 12 | Caché de simulación | `cache_key` = sha256(input_hash, product_id, medidas, modelo, tamaño, calidad, placement) | Misma foto + producto + medidas → reutiliza resultado, costo 0, no consume cuota. |
| 13 | Confirmación explícita | Callback `sim:go:<sim_id>` | `images.edit` solo se llama tras pulsar *Generar*. |
| 14 | Sin regeneración automática | "Generar otra versión" | Requiere cuota disponible y **nueva** confirmación; nunca se reintenta solo. |
| 15 | Fallos no consumen cuota del cliente | `simulation/service.py` | `failed` no incrementa `simulations_used` (sí se registra el costo si OpenAI lo facturó). |
| 16 | Aviso al 80 % | `BUDGET_WARN_PCT=80` | Evento `budget.warning` → notificación al admin (una vez por umbral). |
| 17 | Calidad baja por defecto | `IMAGE_QUALITY=low` | `medium/high` prohibidos por defecto ([handoff §9](CODEX_HANDOFF.md)). |
| 18 | Tamaño fijo | `IMAGE_SIZE=1024x1024` | `auto` (más caro) es solo experimental. |
| 19 | Moderación gratuita | `OPENAI_MODERATION=true` | Evita gastar generación en textos rechazables. |
| 20 | Límite duro en OpenAI | Panel del proyecto | Créditos prepagados de US$ 4 y límite de proyecto (ver §6.2). |

## 6. Optimización de imágenes

Implementación: `backend/app/imaging/pipeline.py` ([handoff §5.5](CODEX_HANDOFF.md)). Todo es configurable por variables de entorno.

| Requisito | Implementación | Variable |
|---|---|---|
| Redimensionar la foto del cliente a máx. 1280 px en el lado mayor | `Image.thumbnail((1280, 1280), LANCZOS)` | `INPUT_MAX_SIDE=1280` |
| Comprimir antes de enviar | JPEG `quality=85, optimize=True, progressive=True` | `INPUT_JPEG_QUALITY=85` |
| Mantener la relación de aspecto | `thumbnail` conserva proporción; nunca se recorta ni deforma | — |
| Calidad `low` inicialmente | Parámetro `quality` de `images.edit` | `IMAGE_QUALITY=low` |
| 1024×1024 cuando corresponda | Tamaño por defecto; `auto` elige 1536×1024 / 1024×1536 (experimental, más caro) | `IMAGE_SIZE=1024x1024` |
| Evitar alterar la habitación | Prompt: conservar paredes, piso, ventanas, iluminación, perspectiva y encuadre; no agregar ni quitar objetos ([05 §5](05-agente-ia-prompts.md)) | — |
| Referencia del producto liviana | Imagen limpia pre-optimizada ≤ 768 px en el seed | `SIMULATION_USE_PRODUCT_REFERENCE=true` |
| Comprimir el resultado a JPEG/WebP | `optimize_output` guarda en formato configurado | `OUTPUT_FORMAT=JPEG` \| `WEBP`, `OUTPUT_QUALITY=82` |
| Entregar a Telegram con máx. 768 px | Redimensionado del resultado | `OUTPUT_MAX_SIDE=768` |
| Peso objetivo 150–400 KB | Si supera 400 KB, baja la calidad en pasos de 8 hasta 50. El límite inferior es orientativo: no se infla una imagen que ya pesa menos | `OUTPUT_TARGET_MAX_KB=400` |
| Límite de 2 simulaciones por cliente | Contador `customers.simulations_used` | `MAX_SIMULATIONS_PER_CUSTOMER=2` |
| Guardar imagen optimizada y metadatos | `input_key`, `output_key`, `input_hash`, `input_bytes`, `output_bytes`, `model`, `size`, `quality`, `prompt`; meta `{width, height, bytes, format, sha256}`. El original del modelo no se guarda | `STORE_FULL_OUTPUT=false` |
| Registrar costo estimado por generación | `simulations.cost_usd` + fila en `api_usage` (`operation='image_edit'`) | — |
| Nunca regenerar sin confirmación | Solo con callback `sim:go`; "Generar otra versión" exige nuevo `sim_confirm` y agrega `variant` al `cache_key` | — |
| Tamaño máximo de subida | Rechazo previo | `MAX_UPLOAD_MB=10` |
| Retención | Borrado automático | `PHOTO_RETENTION_DAYS=7` |

Beneficios: menos bytes subidos (menor latencia y menor costo de tokens de imagen de entrada), resultados que Telegram muestra sin recomprimir, almacenamiento en R2 mínimo (≈ 40 simulaciones × (≤ 400 KB + ≤ 400 KB) < 35 MB).

## 7. Protocolo de pruebas con costo

### 7.1 Fases

| Fase | Modo | Objetivo | Gasto esperado |
|---|---|---|---|
| Desarrollo (semanas 1–3) | `mock` | Toda la lógica, tests, CI | US$ 0 |
| Humo live (semana 3) | `live`, 1 integrante | 10 turnos + 2 simulaciones; validar integración y costos reales | ≤ US$ 0.05 |
| Sesión controlada 1 (semana 4) | `live`, 4 integrantes | Set anti-alucinación de 20 preguntas + 10 simulaciones | ≤ US$ 0.25 |
| Pruebas de usuario (UAT) | `live` | 5–8 usuarios externos, 2 simulaciones c/u | ≤ US$ 0.40 |
| Ensayo y demo | `live` | Guion doc 14 | ≤ US$ 0.10 por ensayo |

Fuera de estas sesiones, el entorno de producción vuelve a `AI_MODE=mock` o se deja en `live` solo con el límite de presupuesto activo.

### 7.2 Configuración del proyecto OpenAI
1. Crear un **proyecto** exclusivo "decosmart-ai" en la plataforma de OpenAI y generar la API key dentro de él.
2. Cargar crédito prepagado (US$ 4) y desactivar la recarga automática.
3. En la configuración de límites del proyecto, fijar un límite de gasto igual al crédito y alertas de correo.
4. Restringir el proyecto a los modelos usados (`gpt-5.4-nano`, `gpt-image-1-mini`, moderación) si la plataforma lo permite.

### 7.3 Conciliación
Tras cada sesión live:
1. Anotar `api_cost_usd` de `/admin/usage` (dashboard → *Costos API*).
2. Abrir la página de uso (*Usage*) del proyecto en OpenAI y anotar el gasto del mismo intervalo (puede tardar unos minutos en reflejarse).
3. Calcular desviación = (real − estimado) / estimado. Registrar en la tabla del informe.
4. Si la desviación de imágenes > +25 %, aumentar `IMAGE_INPUT_SURCHARGE_USD` en `pricing.py` para que la estimación siga siendo conservadora.
5. Si el gasto real acumulado supera US$ 3.00, pasar a `AI_MODE=mock` salvo para el ensayo final y la demo.

## 8. Cómo actualizar `pricing.py` cuando cambian los precios

1. Revisar las páginas oficiales de modelos y precios (§2, fuentes).
2. Editar `backend/app/core/pricing.py`: `TEXT_MODELS`, `IMAGE_OUTPUT_PER_IMAGE` y, si corresponde, `IMAGE_INPUT_SURCHARGE_USD`.
3. Actualizar `PRICING_VERIFIED_AT` con la fecha de verificación (`AAAA-MM-DD`) y la URL en el comentario.
4. Actualizar las tablas de este documento (§2) y, si cambia el modelo por defecto, `.env.example` y el handoff §4.
5. Ajustar/añadir el test unitario de `estimate_chat` y `estimate_image_edit` (valores esperados).
6. Abrir PR `chore(pricing): actualizar precios AAAA-MM-DD`; registrar el cambio en [`DECISIONES.md`](DECISIONES.md).
7. El dashboard (*Costos API*) muestra `PRICING_VERIFIED_AT` para que el evaluador vea la vigencia.

Los costos ya registrados en `api_usage` **no** se recalculan; la tabla nueva aplica a llamadas futuras.
