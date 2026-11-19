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


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    from app.main import create_app

    with TestClient(create_app()) as c:  # lifespan: migraciones + seed
        yield c
    Base.metadata.drop_all(engine)
    with engine.begin() as conn:
        conn.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")


@pytest.fixture()
def db(client):
    with SessionLocal() as s:
        yield s


@pytest.fixture()
def admin_headers():
    return {"X-Admin-Key": "test-admin-key"}
