# 14 — Guion de la demostración (≤ 5 minutos)

> Entregable 22. Coordina: Integrante 4. Entorno: **producción** (Render + Supabase Postgres + Supabase Storage) con `AI_MODE=live`.
> Pantalla dividida recomendada: navegador a la izquierda, Telegram Desktop (cliente) a la derecha; un segundo dispositivo con el chat del admin visible (o Telegram Desktop con dos cuentas).

## 1. Cronograma

| Tiempo | Bloque | Presenta | Qué se muestra | Mensaje clave |
|---|---|---|---|---|
| 0:00–0:30 | Problema y solución | Integrante 4 | Diapositiva: 4 problemas (no visualizan, cotización lenta, consultas sin registro, canales dispersos) y las 3 tecnologías | "DecoSmart convierte el chat en ventas medibles con IA, automatización y DevOps." |
| 0:30–1:00 | Tienda web | Dev A | Home → Catálogo → filtro *Sofás* → Sofá Oslo (precio, medidas, stock) → *Agregar al carrito* → carrito | "Precios y stock vienen siempre de la API; el carrito persiste." |
| 1:00–1:50 | Agente IA en Telegram | Dev B | 3 mensajes (§2.1): precio, recomendación por presupuesto, pregunta trampa | "El agente usa herramientas sobre la base de datos real; un validador bloquea cifras inventadas." |
| 1:50–2:50 | Simulación en el ambiente | Dev B | Botón *Simular* → consentimiento → foto real → medidas → confirmación → resultado | "Solo se genera tras confirmar; foto optimizada a 1280 px, resultado ≤ 768 px, costo ≈ US$ 0.011." |
| 2:50–3:00 | Calificación | Dev B | Pulsar ⭐4 | "La calificación alimenta el dashboard." |
| 3:00–3:35 | Cotización y pedido demo | Dev C | *Cotizar* → mensaje COT-… → *Hacer pedido* → teléfono y dirección → PED-… → notificación en el chat del admin | "Automatización: cada evento dispara notificaciones sin intervención humana." |
| 3:35–4:10 | Dashboard | Dev C | Resumen (embudo consulta ≠ cotización ≠ pedido ≠ venta), Simulaciones, **Costos API** (US$ gastado y % de 3.50) | "Todo queda medido, incluido el costo de cada llamada a OpenAI." |
| 4:10–4:40 | Docker, CI/CD, Render | Dev C | `docker-compose.yml` (4 servicios), run verde de `ci.yml` → `deploy.yml`, servicios en Render, `/health` | "Cada merge a main se prueba y se despliega automáticamente." |
| 4:40–5:00 | Cierre | Integrante 4 | Diapositiva de resultados: 20/20 en el set anti-alucinación, simulación < 90 s, gasto total real US$ X.XX < 4, CI < 10 min | "Un prototipo funcional, medible y de bajo costo." |

Durante los ~30–60 s que tarda la generación (bloque 1:50–2:50), Dev B explica el pipeline de imagen y las cuotas mientras se ve el mensaje "Generando tu simulación…".

## 2. Frases exactas

### 2.1 Telegram — agente (Dev B)
1. `/start` (muestra bienvenida y botones; no usa LLM).
2. `¿Cuánto cuesta el sofá Oslo y qué medidas tiene?`
   → Esperado: **US$ 649.00**, **210 × 85 × 90 cm**, colores gris, beige, azul petróleo.
3. `Tengo 250 dólares para mi home office, ¿qué me recomiendas?`
   → Esperado: **Escritorio Home Office Kappa, US$ 229.00**; nada por encima de 250.
4. `¿Tienen un sofá rojo de 50 dólares?`
   → Esperado: indica que no existe; no inventa; ofrece el Sofá Oslo real (US$ 649.00) u otras opciones.

### 2.2 Telegram — simulación (Dev B)
5. `Quiero ver el sofá Oslo en mi sala` (o botón *Simular* de la ficha) → *Acepto*.
6. Enviar la foto preparada `demo-sala.jpg` (sala vacía, de frente, buena luz, sin personas).
7. `380 x 260; contra la pared bajo la ventana`
8. Pulsar **Generar** → esperar → pulsar **⭐4**.

### 2.3 Telegram — cotización y pedido (Dev C)
9. Pulsar **Cotizar** (o escribir `Cotízame el sofá Oslo`) → aparece `COT-AAAAMMDD-NNNN`, total US$ 649.00, validez 7 días.
10. Pulsar **Hacer pedido** → escribir `Juan Demo, +51 999 000 111, Av. Arequipa 123, Lima`.
11. Mostrar en el chat del admin: `🛒 Nuevo pedido demo PED-… US$ 649.00 (Juan Demo, telegram)`.

### 2.4 Dashboard (Dev C)
12. Pulsar *Actualizar* en Resumen; señalar que Pedidos demo aumentó y Ventas concretadas no.
13. Abrir *Costos API*: gasto acumulado, % del presupuesto, costo por simulación, fecha de verificación de precios.

## 3. Checklist previo (T − 24 h y T − 15 min)

### T − 24 h
- [ ] Último deploy en `main` estable; CI verde; tag `v0.1.0`.
- [ ] **Reactivar proyecto Supabase**: el plan free se pausa tras ~1 semana sin actividad; entrar al panel, confirmar estado *Active* (o *Restore project*) y verificar `/health` → `db: ok`. Repetir a T − 15 min.
- [ ] Gasto acumulado en `/admin/usage` y en el panel de OpenAI registrados; quedan ≥ US$ 1.00 bajo el límite.
- [ ] La cuenta de Telegram que se usará en la demo tiene **0 simulaciones usadas** (usar una cuenta distinta a la de los ensayos; `MAX_SIMULATIONS_PER_CUSTOMER=2`).
- [ ] Foto `demo-sala.jpg` probada en un ensayo live (resultado aceptable) y guardada en el escritorio del presentador.
- [ ] Datos de demo: stock del Sofá Oslo suficiente; productos con stock bajo para mostrar la alerta si sobra tiempo.
- [ ] `ADMIN_TELEGRAM_CHAT_ID` correcto: notificaciones llegan al dispositivo del admin.
- [ ] Video de respaldo grabado (flujo completo, ≤ 5 min, 1080p) en local y en la nube.
- [ ] PPT final con capturas actualizadas; enlace de CI y Render abiertos en pestañas.
- [ ] Dos ensayos cronometrados ≤ 5:00.

### T − 15 min
- [ ] **Pre-calentar Render**: abrir `https://decosmart-api.onrender.com/health` (esperar `db: ok`), la tienda y el dashboard; repetir a T − 3 min.
- [ ] Enviar `/start` al bot para despertar el webhook y verificar respuesta en < 3 s.
- [ ] Confirmar `AI_MODE=live` en `/health` y en el dashboard; `budget_used_pct` < 70 %.
- [ ] Dashboard con contraseña ya ingresada.
- [ ] Telegram Desktop con la conversación limpia (o `/cancelar` para estado `idle`).
- [ ] Notificaciones del sistema silenciadas; zoom del navegador al 125 %.
- [ ] Conexión a internet estable + hotspot móvil de respaldo.
- [ ] Ventana de terminal con `docker-compose.yml` y GitHub Actions abiertos.

## 4. Reparto de roles durante la demo

| Persona | Rol en vivo |
|---|---|
| Integrante 4 | Abre y cierra, controla el tiempo (señal a 2:50 y 4:10), activa el plan de contingencia. |
| Dev A | Opera el navegador en el bloque de la tienda. |
| Dev B | Opera Telegram cliente en los bloques de agente y simulación. |
| Dev C | Muestra el chat admin, el dashboard y la evidencia DevOps. |

## 5. Plan de contingencia

| Falla | Señal | Acción inmediata | Tiempo máx. |
|---|---|---|---|
| Render dormido / lento | `/health` no responde en 10 s | Continuar con la diapositiva siguiente mientras despierta; si no responde en 60 s, pasar al **video de respaldo** del bloque | 60 s |
| OpenAI falla o tarda > 90 s en la simulación | Sin resultado tras 90 s o mensaje de disculpa | Explicar que el fallo no consume cuota (se ve en el mensaje); mostrar el resultado del ensayo desde la página *Simulaciones* del dashboard o el video | 20 s |
| Presupuesto bloqueado (`budget_exhausted`) | Mensaje del bot | Mostrarlo como evidencia de la guardia de presupuesto; continuar con dashboard *Costos API* | 15 s |
| API de OpenAI caída por completo | Errores en chat | Cambiar a **modo mock**: en Render `AI_MODE=mock` (reinicio ≈ 1 min) o usar el entorno local `docker compose up` ya levantado en mock; aclarar al jurado que el comportamiento de herramientas es el mismo | 60 s |
| Telegram no entrega mensajes | Sin respuesta al `/start` | `getWebhookInfo`; si hay error, usar el entorno local en polling con el bot de desarrollo, o el video | 60 s |
| Notificación al admin no llega | Chat admin vacío | Mostrar el evento `order.created` en *Eventos y errores* del dashboard | 15 s |
| Internet del aula caído | Sin red | Hotspot móvil; si no, demo completa con el **video de respaldo** + entorno local en mock (no requiere internet salvo Telegram) | — |
| Se excede el tiempo | Señal de Integrante 4 a 4:10 | Saltar Docker/CI al cierre: mostrar solo una captura en la diapositiva final | — |

**Opción segura para la simulación**: si se envía exactamente la misma foto, producto y medidas del ensayo desde una cuenta nueva, el sistema reutiliza el resultado por `cache_key` (entrega inmediata, costo US$ 0, sin consumir cuota). Usarla solo si el tiempo o el presupuesto lo exigen y **decirlo explícitamente** al jurado como demostración de la caché.

## 6. Preguntas probables del jurado (respuestas cortas)

| Pregunta | Respuesta |
|---|---|
| ¿Cómo evitan que la IA invente precios? | Herramientas obligatorias sobre la BD + validador post-respuesta que reemplaza cifras no verificadas; set de 20 preguntas con 20/20. |
| ¿Cuánto costó? | US$ X.XX real (panel OpenAI) de US$ 4; simulación ≈ US$ 0.011 estimado, turno de chat ≈ US$ 0.0016. |
| ¿Qué pasa con las fotos de los clientes? | Consentimiento previo, sin EXIF/GPS, bucket privado, borrado a los 7 días (Ley N° 29733). |
| ¿La simulación es exacta? | No: es orientativa; se calcula la proporción con las medidas, pero no garantiza encaje físico. Está marcada como experimental. |
| ¿Por qué no LangChain? | El bucle de herramientas son ~80 líneas; sin dependencia extra y con control total de guardias y costos. |
| ¿Escala? | Es un prototipo en planes gratuitos; la arquitectura en contenedores permite escalar el backend y pasar a planes pagos sin cambios de código. |
