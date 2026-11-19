# Decisiones

## Decisiones durante la implementación

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
