# 08 — Dashboard y KPIs

> Entregable 15. Implementación: `dashboard/` (Streamlit), consumiendo `/admin/*` con `X-Admin-Key` ([`CODEX_HANDOFF.md`](CODEX_HANDOFF.md) §5.8, [04](04-api-contratos.md)).
> Estado: **Implementable (MVP)**.

## 1. Definiciones: consulta ≠ cotización ≠ pedido ≠ venta

Esta distinción es obligatoria en el dashboard, el informe y la demo. Cada término corresponde a una tabla o estado distinto ([03](03-modelo-datos.md)).

| Término | Qué es | Qué **no** es | Registro | Ejemplo |
|---|---|---|---|---|
| **Conversación** | Sesión de chat de un cliente en Telegram | No es una consulta: una conversación puede tener 0 o muchas | `conversations` (nueva si es el primer mensaje del día o la anterior lleva > 6 h inactiva) | El cliente escribe "hola" a las 10:00 |
| **Consulta** | Pregunta concreta sobre producto/categoría resuelta con datos del catálogo | No implica intención de compra | `inquiries` (cada herramienta de catálogo con resultado, o vista de detalle en la web) | "¿Cuánto mide el sofá Oslo?" |
| **Cotización** | Documento con ítems, precios congelados, total y validez | No es un pedido ni compromete stock | `quotes` (`COT-AAAAMMDD-NNNN`) | COT-20261118-0001 por US$ 947.00 |
| **Pedido demo** | Intención de compra registrada con datos de contacto | **No es una venta**: no hay pago | `orders` con `is_demo=true` (`PED-AAAAMMDD-NNNN`) | PED-20261118-0001 en `pending` |
| **Venta concretada** | Pedido que el admin marca como entregado/pagado fuera del sistema | No la crea el cliente ni el bot | `orders.status='completed'` (PATCH admin) | PED-20261118-0001 → `completed` |

Embudo: **Conversaciones → Consultas → Cotizaciones → Pedidos demo → Ventas concretadas**. Las tasas de conversión se calculan entre etapas consecutivas y se rotulan como tales.

## 2. Catálogo de KPIs

Rango por defecto: todo el histórico (filtros `from`/`to` del endpoint de resumen). "Hoy" = zona `TIMEZONE=America/Lima`.

| # | KPI | Definición / fórmula | Fuente (endpoint → campo) | Tabla(s) |
|---|---|---|---|---|
| K1 | Conversaciones totales | `COUNT(conversations)` en el rango | `/admin/metrics/summary` → `conversations_total` | `conversations` |
| K2 | Clientes únicos | `COUNT(DISTINCT customer_id)` de conversaciones | `summary` → `unique_customers` | `conversations` |
| K3 | Consultas por día | `COUNT(inquiries)` agrupado por `date(created_at)` en TZ Lima, últimos 14 días | `/admin/metrics/daily?days=14` → `inquiries` | `inquiries` |
| K4 | Consultas totales | `COUNT(inquiries)` | `summary` → `inquiries_total` | `inquiries` |
| K5 | Productos más consultados | Top 5 por `COUNT(inquiries)` con `product_id` no nulo | `/admin/metrics/top-products?kind=inquired&limit=5` | `inquiries` |
| K6 | Productos más solicitados | Top 5 por `SUM(quantity)` en `quote_items` + `order_items` | `/admin/metrics/top-products?kind=requested&limit=5` | `quote_items`, `order_items` |
| K7 | Cotizaciones generadas | `COUNT(quotes)` (cualquier estado) | `summary` → `quotes_total` | `quotes` |
| K8 | Cotizaciones aceptadas | `COUNT(quotes WHERE status='accepted')` | `summary` → `quotes_accepted` | `quotes` |
| K9 | Pedidos demo | `COUNT(orders)` (incluye `cancelled`; se muestra desglose por estado en la tabla) | `summary` → `orders_total`; `/admin/orders` | `orders` |
| K10 | Ventas concretadas | `COUNT(orders WHERE status='completed')` | `summary` → `orders_completed` | `orders` |
| K11 | Simulaciones generadas | Simulaciones `completed` con `reused_from_id IS NULL` (llamaron al modelo) | `summary` → `simulations_total` − `simulations_reused` | `simulations` |
| K12 | Simulaciones fallidas | `COUNT(simulations WHERE status='failed')` | `summary` → `simulations_failed` | `simulations` |
| K13 | Simulaciones reutilizadas | `COUNT(simulations WHERE status='completed' AND reused_from_id IS NOT NULL)` (costo 0) | `summary` → `simulations_reused` | `simulations` |
| K14 | Calificación promedio de la IA | `AVG(simulation_ratings.score)` (1–5) y `COUNT` | `summary` → `avg_rating`, `ratings_count` | `simulation_ratings` |
| K15 | Gasto estimado de API | `SUM(api_usage.cost_usd WHERE mode='live')` | `summary` → `api_cost_usd`; `/admin/usage?days=30` | `api_usage` |
| K16 | % del presupuesto usado | `api_cost_usd / BUDGET_USD_LIMIT × 100` | `summary` → `budget_used_pct`, `budget_usd` | `api_usage` + config |
| K17 | Historial de eventos | Lista paginada filtrable por `type` | `/admin/events?type=&limit=50&offset=0` | `events` |
| K18 | Errores de procesamiento | `COUNT(error_logs)` y lista por `source`, `error_type` | `summary` → `errors_total`; `/admin/errors?limit=50` | `error_logs` |

### KPIs derivados (calculados en el dashboard)

| KPI | Fórmula | Nota |
|---|---|---|
| Tasa consulta → cotización | `quotes_total / inquiries_total` | Aproximada (no todas las cotizaciones vienen de una consulta registrada). |
| Tasa cotización → pedido | `orders_total / quotes_total` | |
| Tasa pedido → venta | `orders_completed / orders_total` | |
| Tasa de éxito de simulación | `completed / (completed + failed)` | |
| Costo promedio por simulación | `SUM(cost_usd operation='image_edit') / K11` | `/admin/usage` por operación |
| Costo promedio por conversación | `SUM(cost_usd operation='chat') / K1` | |
| Alucinaciones bloqueadas | `COUNT(error_logs WHERE source='agent' AND error_type='unverified_number')` | Página 5, filtro |

## 3. Páginas

| Archivo | Página | Contenido | Endpoints |
|---|---|---|---|
| `app.py` | **Resumen** | Fila de `st.metric`: Conversaciones (K1), Consultas (K4), Cotizaciones (K7), Pedidos demo (K9), Ventas concretadas (K10), Simulaciones (K11+K13), Rating promedio (K14), Gasto API US$ y % (K15–K16). Gráfico de línea "Actividad diaria" 14 días. Leyenda *Consulta ≠ Cotización ≠ Pedido ≠ Venta*. Indicador de modo `mock`/`live`. | `summary`, `daily` |
| `pages/1_Conversaciones.py` | Conversaciones | Serie diaria de conversaciones y consultas (K3); tabla de consultas por `type` (`price`, `dimensions`, `stock`, `recommendation`, `product_info`, `catalog`); clientes únicos (K2). | `daily`, `summary` |
| `pages/2_Productos.py` | Productos | Barras lado a lado: más consultados (K5) vs más solicitados (K6); tabla de stock actual con resaltado si `stock ≤ LOW_STOCK_THRESHOLD`. | `top-products`, `/api/products` |
| `pages/3_Simulaciones.py` | Simulaciones | Totales generadas/fallidas/reutilizadas (K11–K13), tasa de éxito, distribución de ratings 1–5, galería de las últimas 6 (URL prefirmada). | `summary`, `/admin/simulations` |
| `pages/4_Costos_API.py` | Costos API | Barra de progreso gasto vs límite (K16, amarillo ≥ 80 %), gasto por operación, por modelo y por día, costo promedio por simulación y por conversación, modo actual, `PRICING_VERIFIED_AT`. | `/admin/usage` |
| `pages/5_Eventos_y_Errores.py` | Eventos y errores | Tablas filtrables de eventos (K17) y errores (K18). | `/admin/events`, `/admin/errors` |

Reglas comunes: autenticación con `DASHBOARD_PASSWORD` si está definido; todas las llamadas con `st.cache_data(ttl=30)`; botón "Actualizar" que limpia la caché; dinero con formato `US$ 0.00` (costos API con 4 decimales); mensajes claros si el backend está dormido (Render free) — "El backend está despertando, reintenta en 30 s".

## 4. Wireframe de la página principal

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ DecoSmart · Dashboard                          Modo IA: LIVE   [Actualizar]  │
│ Consulta ≠ Cotización ≠ Pedido ≠ Venta                                        │
├──────────────┬──────────────┬──────────────┬──────────────┬──────────────────┤
│Conversaciones│  Consultas   │ Cotizaciones │ Pedidos demo │ Ventas concretad.│
│      42      │     120      │      15      │      6       │        2         │
│  18 clientes │              │ 4 aceptadas  │  (sin cobro) │   (completed)    │
├──────────────┼──────────────┼──────────────┴──────────────┴──────────────────┤
│ Simulaciones │ Rating IA    │ Gasto API                                       │
│ 9 (2 reutil.)│  4.2 ★ (7)   │ US$ 0.4123 de 3.50   [███░░░░░░░░░░] 11.8 %     │
│ 1 fallida    │              │                                                 │
├──────────────┴──────────────┴─────────────────────────────────────────────────┤
│ Actividad diaria (14 días)                                                    │
│  30 ┤            ╭─╮                    ── conversaciones                     │
│  20 ┤      ╭─────╯ ╰──╮      ╭──        ── consultas                          │
│  10 ┤ ╭────╯          ╰──────╯          ── cotizaciones                       │
│   0 ┼──────────────────────────────     ── pedidos  ── simulaciones           │
│      05/11            12/11      18/11                                        │
├───────────────────────────────────────────────────────────────────────────────┤
│ Embudo: 42 conv. → 120 consultas → 15 cotiz. (12.5 %) → 6 pedidos (40 %)      │
│         → 2 ventas (33 %)                                                     │
│ Errores registrados: 3  ·  Precios verificados: 2026-11-18                    │
└───────────────────────────────────────────────────────────────────────────────┘
```

## 5. Criterios de aceptación

- [ ] Con `DASHBOARD_PASSWORD` definido, no se muestra ningún dato antes de ingresar la contraseña correcta.
- [ ] Los 11 indicadores exigidos (handoff §8) —K1, K3, K5, K6, K7, K9, K10, K11–K13, K14, K15–K16, K17, K18— se muestran con datos reales del backend.
- [ ] Tras crear una cotización por Telegram y pulsar "Actualizar", K7 aumenta en 1 (máx. 30 s de caché).
- [ ] Un pedido demo incrementa K9 pero **no** K10; al pasar a `completed` vía `PATCH /admin/orders/{code}`, K10 aumenta.
- [ ] Una simulación reutilizada incrementa K13, no K11, y no cambia K15.
- [ ] K15 coincide con `SUM(api_usage.cost_usd WHERE mode='live')` consultado directamente en la BD.
- [ ] La barra de presupuesto se muestra en color de advertencia a partir del 80 %.
- [ ] Con el backend caído, el dashboard muestra un mensaje de error legible (sin traza).
