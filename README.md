# DECOSMART AI

Plataforma inteligente de venta de muebles con asistente IA en Telegram, simulación de ambientes con IA generativa y automatización comercial. Proyecto final universitario.

- **Tienda web**: React + Vite
- **Backend**: FastAPI + PostgreSQL (bot de Telegram, agente IA con OpenAI, simulador, automatizaciones)
- **Dashboard**: Streamlit
- **DevOps**: Docker Compose, GitHub Actions, Render

Toda la documentación está en [`docs/`](docs/00-indice.md). El documento de implementación es [`docs/CODEX_HANDOFF.md`](docs/CODEX_HANDOFF.md).

## Arranque rápido (local, modo MOCK sin costo de API)

```bash
cp .env.example .env          # AI_MODE=mock por defecto
docker compose up --build
```

| Servicio | URL |
|---|---|
| Tienda | http://localhost:5173 |
| API + OpenAPI | http://localhost:8000/docs |
| Dashboard | http://localhost:8501 |

Para usar el bot, define `TELEGRAM_BOT_TOKEN` (BotFather) en `.env`; en local corre en modo *polling*.
Para usar IA real, define `OPENAI_API_KEY` y `AI_MODE=live` (ver [presupuesto](docs/07-presupuesto-costos.md)).

## Desarrollo sin Docker

```bash
cd backend && python -m venv .venv && .venv/Scripts/pip install -r requirements-dev.txt
.venv/Scripts/pytest
.venv/Scripts/uvicorn app.main:app --reload
```
