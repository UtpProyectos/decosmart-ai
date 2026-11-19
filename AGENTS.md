# AGENTS.md — Reglas para agentes (Codex, Claude y otros)

Proyecto: **DECOSMART AI** — tienda de muebles + agente IA en Telegram + simulador de ambientes + automatización + dashboard.

## Antes de escribir código
1. Lee `docs/CODEX_HANDOFF.md` (fuente única de verdad: estructura, stack, variables, contratos, orden).
2. Consulta según tu tarea: `docs/03-modelo-datos.md`, `docs/04-api-contratos.md`, `docs/05-agente-ia-prompts.md`, `docs/07-presupuesto-costos.md`.
3. No reinventes decisiones ya tomadas en esos documentos. Si algo es ambiguo, elige la opción más simple y anótala en `docs/DECISIONES.md`.

## Reglas duras
- **Nunca** llames a la API real de OpenAI en tests ni en CI. Tests siempre con `AI_MODE=mock`.
- **Nunca** hardcodees secretos. Todo por variables de entorno (ver `.env.example`).
- El agente IA **nunca** inventa precios, stock, medidas ni descuentos: siempre vienen de la BD vía herramientas.
- Sin pagos reales, sin AR/VR/IoT.
- Toda llamada a OpenAI pasa por `backend/app/services/budget.py` (guardia de presupuesto) y se registra en `api_usage`.
- Generación de imágenes solo tras confirmación explícita del usuario y verificación de cuotas.
- Código en inglés (nombres), textos de UI y mensajes del bot en español.
- Python: 3.11, ruff, type hints, FastAPI + SQLAlchemy 2 (sync) + Pydantic v2. Frontend: React 18 + Vite + TypeScript.
- Cada cambio de backend con test en `backend/tests/`. Ejecuta `pytest` antes de terminar.
- Trabaja solo dentro de los directorios de tu tarea; no reformatees archivos ajenos.

## Comandos
- Backend: `cd backend && pip install -r requirements-dev.txt && pytest`
- Frontend: `cd frontend && npm ci && npm run lint && npm test && npm run build`
- Todo: `docker compose up --build`
