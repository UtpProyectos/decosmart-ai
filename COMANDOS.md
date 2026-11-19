# Comandos para ejecutar DecoSmart AI (local)

Requisitos: Python 3.11, Node 20, y el archivo `.env` en la raíz del repo (copiado de `.env.example`).
La base de datos (Supabase Postgres) y el bucket (Supabase Storage) se configuran en `.env`; las tablas y los 6 muebles se crean solos al arrancar el backend.

Abre **3 terminales** (PowerShell o Git Bash), todas desde la raíz `D:\Repositorios\decosmart-ai`.

---

## Instalación (solo la primera vez)

```powershell
# Backend
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
cd ..

# Frontend
cd frontend
npm ci
cd ..

# Dashboard
cd dashboard
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
cd ..
```

---

## Terminal 1 — Backend (API + bot de Telegram)

```powershell
cd backend
.venv\Scripts\uvicorn app.main:app --reload --port 8000
```

- API: http://localhost:8000/docs
- Salud: http://localhost:8000/health (debe decir `"db": "ok"`)
- Con `TELEGRAM_MODE=polling` el bot arranca junto con el backend: escríbele `/start` a tu bot.

## Terminal 2 — Frontend (tienda web)

```powershell
cd frontend
npm run dev
```

- Tienda: http://localhost:5173

## Terminal 3 — Dashboard (Streamlit)

PowerShell:
```powershell
cd dashboard
$env:DASHBOARD_API_URL="http://localhost:8000"; .venv\Scripts\streamlit run app.py
```

Git Bash:
```bash
cd dashboard
DASHBOARD_API_URL=http://localhost:8000 .venv/Scripts/streamlit run app.py
```

- Dashboard: http://localhost:8501

---

## Alternativa: todo con Docker (requiere Docker Desktop abierto)

```powershell
docker compose up --build
```

| Servicio | URL |
|---|---|
| Tienda | http://localhost:5173 |
| API | http://localhost:8000/docs |
| Dashboard | http://localhost:8501 |

Detener: `Ctrl+C` y luego `docker compose down`.

---

## Tests

```powershell
cd backend;   .venv\Scripts\python -m pytest
cd frontend;  npm run lint; npm test; npm run build
cd dashboard; .venv\Scripts\python -m pytest tests
```

## Modo de IA

- `AI_MODE=mock` (por defecto): sin costo, respuestas simuladas con el catálogo real.
- `AI_MODE=live`: usa OpenAI (gasta crédito). Cambiarlo en `.env` y reiniciar el backend. El límite es `BUDGET_USD_LIMIT=3.50`.

## Problemas comunes

| Síntoma | Solución |
|---|---|
| `/health` dice `"db": "error"` | Revisa `DATABASE_URL` (Session pooler de Supabase) o reactiva el proyecto en Supabase si estaba pausado. |
| El bot no responde | Solo una instancia puede hacer *polling* por token: cierra otros backends con el mismo bot. |
| La tienda no carga productos | El backend debe estar corriendo en el puerto 8000 (`VITE_API_URL`). |
| No llegan notificaciones al grupo | Falta `ADMIN_TELEGRAM_CHAT_ID`, o el bot no fue agregado al grupo. |
