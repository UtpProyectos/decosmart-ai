import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ["AI_MODE"] = "mock"
os.environ["APP_ENV"] = "test"
os.environ["TELEGRAM_BOT_TOKEN"] = ""
os.environ["SCHEDULER_ENABLED"] = "false"
os.environ["ADMIN_API_KEY"] = "test-admin-key"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.db import Base, SessionLocal, engine  # noqa: E402


def _reset_db() -> None:
    """Deja la BD vacía, incluida la marca de Alembic.

    Si quedara `alembic_version` (p. ej. CI corre `alembic upgrade head` antes de pytest), el lifespan
    creería que las migraciones ya están aplicadas y no recrearía las tablas → "relation does not exist".
    """
    engine.dispose()  # cierra conexiones abiertas que en Postgres bloquearían el DROP
    Base.metadata.drop_all(engine)
    with engine.begin() as conn:
        conn.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")


@pytest.fixture()
def client():
    _reset_db()
    from app.main import create_app

    with TestClient(create_app()) as c:  # lifespan: migraciones + seed
        yield c
    _reset_db()


@pytest.fixture()
def db(client):
    with SessionLocal() as s:
        yield s


@pytest.fixture()
def admin_headers():
    return {"X-Admin-Key": "test-admin-key"}


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    """Storage local en tmp, admin chat configurado y rate limiter limpio en cada test."""
    from app.core.config import get_settings
    from app.core.security import limiter

    settings = get_settings()
    monkeypatch.setattr(settings, "local_storage_path", str(tmp_path / "storage"))
    monkeypatch.setattr(settings, "admin_telegram_chat_id", "999")
    limiter.reset()
    limiter.force_enabled = False
    yield
    limiter.force_enabled = False
    limiter.reset()


@pytest.fixture(autouse=True)
def sent_messages():
    """Captura los mensajes del notifier: lista de (chat_id, text)."""
    from app.automation import notifier

    msgs: list[tuple] = []

    def _capture(chat_id, text):
        msgs.append((str(chat_id), text))
        return True

    notifier.set_sender(_capture)
    yield msgs
    notifier.set_sender(None)


def admin_texts(msgs) -> list[str]:
    return [t for c, t in msgs if c == "999"]
