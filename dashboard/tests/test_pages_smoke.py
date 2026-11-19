"""Smoke tests: cada página se ejecuta sin excepciones con la API caída y con datos de ejemplo."""

import sys
from pathlib import Path

import pytest
import requests

DASHBOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DASHBOARD))

import api  # noqa: E402

AppTest = pytest.importorskip("streamlit.testing.v1").AppTest

PAGES = [
    "app.py",
    "app_pages/0_Resumen.py",
    "app_pages/1_Conversaciones.py",
    "app_pages/2_Productos.py",
    "app_pages/3_Simulaciones.py",
    "app_pages/4_Costos_API.py",
    "app_pages/5_Eventos_y_Errores.py",
]

SAMPLE = {
    "/health": {"status": "ok", "db": "ok", "ai_mode": "mock"},
    "/admin/metrics/summary": {
        "conversations_total": 42, "unique_customers": 18, "inquiries_total": 120, "quotes_total": 15,
        "quotes_accepted": 4, "orders_total": 6, "orders_completed": 2, "simulations_total": 9,
        "simulations_failed": 1, "simulations_reused": 2, "avg_rating": 4.2, "ratings_count": 7,
        "api_cost_usd": "0.4123", "budget_usd": "3.50", "budget_used_pct": 11.8, "errors_total": 3,
        "ai_mode": "live",
    },
    "/admin/metrics/daily": [
        {"date": "2026-11-17", "conversations": 2, "inquiries": 5, "quotes": 1, "orders": 0, "simulations": 1},
        {"date": "2026-11-18", "conversations": 4, "inquiries": 9, "quotes": 2, "orders": 1, "simulations": 2},
    ],
    "/admin/metrics/top-products": [
        {"product_id": 1, "sku": "DS-SOF-001", "name": "Sofá Oslo 3 plazas", "count": 7},
        {"product_id": 4, "sku": "DS-CAM-001", "name": "Cama Queen Lumbre", "count": 3},
    ],
    "/admin/usage": {
        "total_usd": "0.0220", "budget_usd": "3.50", "budget_used_pct": 0.63,
        "by_operation": [{"operation": "image_edit", "cost_usd": "0.011", "calls": 2},
                         {"operation": "chat", "cost_usd": "0.0001", "calls": 30}],
        "by_model": [{"model": "gpt-image-1-mini", "cost_usd": "0.022", "calls": 2}],
        "by_day": [{"date": "2026-11-18", "cost_usd": "0.022"}],
        "pricing_verified_at": "2026-11-18", "ai_mode": "live",
    },
    "/admin/events": {"items": [
        {"id": 1, "type": "inquiry.created", "entity_type": "inquiry", "entity_id": 3, "customer_id": 1,
         "payload": {"type": "price", "channel": "telegram"}, "created_at": "2026-11-18T10:00:00Z", "notified": False},
    ], "total": 1},
    "/admin/errors": {"items": [
        {"id": 1, "source": "bot", "error_type": "ValueError", "message": "x", "created_at": "2026-11-18T10:00:00Z"},
    ], "total": 1},
    "/admin/simulations": {"items": [
        {"id": 5, "product_name": "Sofá Oslo", "status": "completed", "score": 4, "cost_usd": "0.0110",
         "reused": False, "output_url": "/media/customers/1/outputs/5.jpg", "created_at": "2026-11-18T10:00:00Z"},
        {"id": 6, "product_name": "Cama", "status": "failed", "score": None, "cost_usd": "0",
         "reused": False, "output_url": None, "created_at": "2026-11-18T11:00:00Z"},
    ], "total": 2},
    "/admin/quotes": {"items": [{"code": "COT-20261118-0001", "status": "sent", "total": "649.00",
                                 "items": [{"product_id": 1, "quantity": 1}]}], "total": 1},
    "/admin/orders": {"items": [{"code": "PED-20261118-0001", "status": "pending", "total": "649.00"}], "total": 1},
    "/api/products": {"items": [
        {"id": 1, "sku": "DS-SOF-001", "name": "Sofá Oslo", "category": {"slug": "sofas", "name": "Sofás"},
         "price": "649.00", "stock": 8, "low_stock": False},
        {"id": 5, "sku": "DS-ALM-001", "name": "Librero Cubo", "category": {"slug": "almacenamiento", "name": "Alm."},
         "price": "189.00", "stock": 3, "low_stock": True},
    ], "total": 2},
}


class Resp:
    def __init__(self, payload, status=200, content_type="application/json"):
        self.status_code = status
        self._payload = payload
        self.headers = {"content-type": content_type}
        self.content = b""

    def json(self):
        return self._payload


def sample_get(url, params=None, headers=None, timeout=None):
    path = url.replace(api.api_base_url(), "")
    if path in SAMPLE:
        return Resp(SAMPLE[path])
    return Resp({}, status=404)


def down_get(*args, **kwargs):
    raise requests.ConnectionError("down")


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("DASHBOARD_API_URL", "http://api.test")
    monkeypatch.setenv("DASHBOARD_ADMIN_KEY", "k")
    monkeypatch.delenv("DASHBOARD_PASSWORD", raising=False)
    api.clear_cache()
    yield
    api.clear_cache()


def kpi_cards(at: "AppTest") -> int:
    """Tarjetas KPI (HTML propio) visibles en la página."""
    return sum(md.value.count('class="ds-card ds-kpi"') for md in at.markdown)


def run(page: str) -> "AppTest":
    at = AppTest.from_file(str(DASHBOARD / page), default_timeout=30)
    at.run()
    return at


@pytest.mark.parametrize("page", PAGES)
def test_page_renders_with_api_down(monkeypatch, page):
    monkeypatch.setattr(api.requests, "get", down_get)
    at = run(page)
    assert not at.exception, at.exception
    assert any("No se pudo conectar" in w.value for w in at.warning)


@pytest.mark.parametrize("page", PAGES)
def test_api_down_shows_single_banner_with_retry(monkeypatch, page):
    monkeypatch.setattr(api.requests, "get", down_get)
    at = run(page)
    assert len([w for w in at.warning if "No se pudo conectar" in w.value]) == 1
    retry = [b for b in at.button if b.key == "ds_retry"]
    assert len(retry) == 1

    # La API vuelve: "Reintentar" limpia la caché y la página deja de mostrar el banner.
    monkeypatch.setattr(api.requests, "get", sample_get)
    retry[0].click()
    at.run()
    assert not at.exception
    assert not any("No se pudo conectar" in w.value for w in at.warning)


@pytest.mark.parametrize("page", PAGES)
def test_page_renders_with_sample_data(monkeypatch, page):
    monkeypatch.setattr(api.requests, "get", sample_get)
    at = run(page)
    assert not at.exception, at.exception


def test_password_gate(monkeypatch):
    monkeypatch.setattr(api.requests, "get", sample_get)
    monkeypatch.setenv("DASHBOARD_PASSWORD", "s3cret-pass")
    at = run("app.py")
    assert not at.exception
    assert len(at.metric) == 0 and kpi_cards(at) == 0  # nada visible antes de autenticarse
    at.text_input[0].input("s3cret-pass")
    at.button[0].click()
    at.run()
    assert not at.exception
    assert kpi_cards(at) == 8  # las 8 tarjetas del Resumen
