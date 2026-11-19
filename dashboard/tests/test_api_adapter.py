"""Tests de los adaptadores del dashboard (sin red real ni runtime de Streamlit)."""

import sys
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import api  # noqa: E402

SUMMARY_JSON = {
    "conversations_total": 42,
    "unique_customers": 18,
    "inquiries_total": 120,
    "quotes_total": 15,
    "quotes_accepted": 4,
    "orders_total": 6,
    "orders_completed": 2,
    "simulations_total": 9,
    "simulations_failed": 1,
    "simulations_reused": 2,
    "avg_rating": 4.2,
    "ratings_count": 7,
    "api_cost_usd": "0.4123",
    "budget_usd": "3.50",
    "budget_used_pct": 11.8,
    "errors_total": 3,
    "ai_mode": "live",
}


class FakeResponse:
    def __init__(self, status_code=200, payload=None, content_type="application/json"):
        self.status_code = status_code
        self._payload = payload
        self.headers = {"content-type": content_type}
        self.content = b"img"

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("DASHBOARD_API_URL", "http://api.test/")
    monkeypatch.setenv("DASHBOARD_ADMIN_KEY", "secret")


def fake_get(responses, calls=None):
    def _get(url, params=None, headers=None, timeout=None):
        if calls is not None:
            calls.append({"url": url, "params": params, "headers": headers, "timeout": timeout})
        path = url.replace("http://api.test", "")
        result = responses.get(path)
        if isinstance(result, Exception):
            raise result
        return result if result is not None else FakeResponse(404, {})

    return _get


def test_api_down_returns_defaults(monkeypatch):
    def down(*args, **kwargs):
        raise requests.ConnectionError("down")

    monkeypatch.setattr(api.requests, "get", down)
    summary = api.load_summary()
    assert not summary.ok
    assert "No se pudo conectar" in summary.error
    assert summary.data["conversations_total"] == 0
    assert summary.data["avg_rating"] is None

    assert api.load_daily().data == []
    assert api.load_top_products().data == []
    assert api.load_usage().data["by_operation"] == []
    assert api.load_events().data == {"items": [], "total": 0}
    assert api.load_errors().data == {"items": [], "total": 0}
    assert api.load_simulations().data == {"items": [], "total": 0}
    assert api.load_products().data == []
    assert api.load_image_bytes("/media/x.jpg") is None


def test_timeout_and_http_errors(monkeypatch):
    monkeypatch.setattr(
        api.requests,
        "get",
        fake_get(
            {
                "/admin/metrics/summary": requests.Timeout(),
                "/admin/usage": FakeResponse(401, {"error": {"message": "no"}}),
                "/admin/events": FakeResponse(500, {"error": {"code": "INTERNAL_ERROR", "message": "boom"}}),
            }
        ),
    )
    assert "no respondió" in api.load_summary().error
    assert "401" in api.load_usage().error
    events = api.load_events()
    assert "500" in events.error and "boom" in events.error
    assert "404" in api.load_errors().error


def test_summary_parsing_and_headers(monkeypatch):
    calls = []
    monkeypatch.setattr(
        api.requests, "get", fake_get({"/admin/metrics/summary": FakeResponse(200, SUMMARY_JSON)}, calls)
    )
    result = api.load_summary()
    assert result.ok
    data = result.data
    assert data["conversations_total"] == 42
    assert data["orders_completed"] == 2
    assert data["api_cost_usd"] == pytest.approx(0.4123)
    assert data["budget_usd"] == pytest.approx(3.5)
    assert data["budget_used_pct"] == pytest.approx(11.8)
    assert data["avg_rating"] == pytest.approx(4.2)
    assert data["ai_mode"] == "live"
    assert calls[0]["headers"]["X-Admin-Key"] == "secret"
    assert calls[0]["timeout"] == api.TIMEOUT_SECONDS
    assert calls[0]["url"] == "http://api.test/admin/metrics/summary"


def test_summary_tolerates_missing_keys():
    data = api.parse_summary({"api_cost_usd": "1.75", "budget_usd": "3.50", "conversations_total": None})
    assert data["conversations_total"] == 0
    assert data["quotes_total"] == 0
    assert data["budget_used_pct"] == pytest.approx(50.0)
    assert data["ai_mode"] == "—"
    assert api.parse_summary(None) == api.empty_summary()


def test_daily_and_top_products_parsing():
    daily = api.parse_daily(
        [{"date": "2026-11-18", "conversations": 3, "inquiries": "5"}, {"date": "2026-11-17T00:00:00"}, {"x": 1}]
    )
    assert [r["date"] for r in daily] == ["2026-11-17", "2026-11-18"]
    assert daily[1]["inquiries"] == 5 and daily[1]["orders"] == 0

    top = api.parse_top_products(
        {"items": [{"product_id": 1, "sku": "A", "name": "Sofá", "count": 2}, {"product_id": 2, "count": 9}]}
    )
    assert top[0]["count"] == 9 and top[0]["name"] == "Producto 2"


def test_usage_and_listings_parsing():
    usage = api.parse_usage(
        {
            "total_usd": "0.0110",
            "budget_usd": "3.50",
            "by_operation": [{"operation": "image_edit", "cost_usd": "0.011", "calls": 1}],
            "by_model": [{"model": "gpt-image-1-mini", "cost_usd": 0.011, "calls": 1}],
            "by_day": [{"date": "2026-11-18", "cost_usd": "0.011"}],
            "pricing_verified_at": "2026-11-18",
            "ai_mode": "mock",
        }
    )
    assert usage["total_usd"] == pytest.approx(0.011)
    assert usage["budget_used_pct"] == pytest.approx(0.31, abs=0.01)
    assert usage["by_operation"][0]["cost_usd"] == pytest.approx(0.011)

    sims = api.parse_simulations(
        {"items": [{"id": 1, "status": "completed", "cost_usd": "0.0110", "reused_from_id": 3}], "total": 7}
    )
    assert sims["total"] == 7
    assert sims["items"][0]["reused"] is True
    assert sims["items"][0]["cost_usd"] == pytest.approx(0.011)

    events = api.parse_events([{"id": 1, "type": "quote.created", "extra": "x"}])
    assert events["total"] == 1 and "extra" not in events["items"][0]

    products = api.parse_products(
        {"items": [{"id": 1, "sku": "S", "name": "N", "category": {"name": "Sofás"}, "price": "649.00", "stock": 3}]}
    )
    assert products[0]["category"] == "Sofás" and products[0]["price"] == 649.0


def test_resolve_url():
    assert api.resolve_url("/media/a.jpg") == "http://api.test/media/a.jpg"
    assert api.resolve_url("https://r2.example/a.jpg?sig=1") == "https://r2.example/a.jpg?sig=1"
    assert api.resolve_url(None) is None
