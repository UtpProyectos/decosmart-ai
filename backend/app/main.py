"""Punto de entrada FastAPI. Ver docs/CODEX_HANDOFF.md."""

import importlib
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.errors import register_error_handlers

BACKEND_ROOT = Path(__file__).resolve().parents[1]
log = logging.getLogger("decosmart")


def run_migrations() -> None:
    from alembic.config import Config

    from alembic import command

    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    command.upgrade(cfg, "head")


def run_seed() -> None:
    from scripts.seed import seed

    with SessionLocal() as db:
        n = seed(db)
        if n:
            log.info("Seed: %s productos creados", n)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if settings.auto_migrate:
        run_migrations()
    if settings.auto_seed:
        run_seed()
    # Hooks de arranque registrados por otros módulos (scheduler, polling del bot).
    for hook in getattr(app.state, "startup_hooks", []):
        hook()
    yield
    for hook in getattr(app.state, "shutdown_hooks", []):
        hook()


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    # httpx registra la URL completa, que incluye el token del bot: no loggear a nivel INFO.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    app = FastAPI(title="DecoSmart AI API", version=settings.app_version, lifespan=lifespan)
    app.state.startup_hooks = []
    app.state.shutdown_hooks = []
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.frontend_origin.split(",") if o.strip()],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)
    importlib.import_module("app.automation.handlers")  # registra reacciones a eventos

    app.mount("/static/products", StaticFiles(directory=BACKEND_ROOT / "seed" / "images"), name="products")

    @app.get("/health")
    def health():
        db_status = "ok"
        try:
            with SessionLocal() as db:
                db.execute(text("SELECT 1"))
        except Exception:  # noqa: BLE001
            db_status = "error"
        return {
            "status": "ok" if db_status == "ok" else "degraded",
            "db": db_status,
            "ai_mode": settings.ai_mode,
            "storage": settings.storage_backend,
            "telegram": settings.telegram_mode,
            "version": settings.app_version,
        }

    # Routers (se agregan en feat/backend-core y feat/ai-bot).
    _include_optional_routers(app)
    return app


def _include_optional_routers(app: FastAPI) -> None:
    for mod in ("app.api.public", "app.api.admin", "app.api.media", "app.api.telegram"):
        try:
            module = importlib.import_module(mod)
        except ModuleNotFoundError as exc:
            if exc.name == mod:
                continue
            raise
        app.include_router(module.router)
        if hasattr(module, "register"):
            module.register(app)


app = create_app()
