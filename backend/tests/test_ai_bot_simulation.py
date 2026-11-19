from io import BytesIO

from PIL import Image
from sqlalchemy import select

from app.ai.provider import ImageResult
from app.core.config import get_settings
from app.models import Event, Product
from app.services import customers
from app.simulation import service


def room_bytes(color="white"):
    out = BytesIO()
    Image.new("RGB", (640, 480), color).save(out, "JPEG")
    return out.getvalue()


def product(db):
    return db.scalar(select(Product).where(Product.sku == "DS-SOF-001"))


def ready(db, customer, color="white"):
    sim = service.prepare(db, customer, product(db))
    service.attach_photo(db, sim.id, room_bytes(color))
    service.set_dimensions(db, sim.id, "300 x 250 x 400")
    return sim


class SpyProvider:
    def __init__(self, fail=False):
        self.calls = 0
        self.fail = fail

    def edit_image(self, room, reference, prompt, size, quality):
        self.calls += 1
        if self.fail:
            raise RuntimeError("provider down")
        return ImageResult(room, {})

    def moderate(self, text):
        return True


def test_prepare_does_not_call_provider(db, monkeypatch):
    spy = SpyProvider()
    monkeypatch.setattr(service, "get_provider", lambda *a, **k: spy)
    customer = customers.get_or_create_by_telegram(db, 8201)
    sim = ready(db, customer)
    assert sim.status == "awaiting_confirmation" and spy.calls == 0


def test_simulation_runs_only_when_run_called(db, monkeypatch):
    spy = SpyProvider()
    monkeypatch.setattr(service, "get_provider", lambda *a, **k: spy)
    customer = customers.get_or_create_by_telegram(db, 8202)
    result = service.run(db, ready(db, customer).id)
    assert result.status == "completed" and spy.calls == 1 and result.data


def test_customer_quota_exhausted_after_two(db):
    customer = customers.get_or_create_by_telegram(db, 8203)
    customer.simulations_used = 2
    db.commit()
    sim = service.prepare(db, customer, product(db))
    assert sim.status == "blocked_quota" and sim.error_message == "customer"


def test_budget_blocks_live_before_provider(db, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "ai_mode", "live")
    monkeypatch.setattr(settings, "budget_usd_limit", 0.001)
    spy = SpyProvider()
    monkeypatch.setattr(service, "get_provider", lambda *a, **k: spy)
    customer = customers.get_or_create_by_telegram(db, 8204)
    sim = service.prepare(db, customer, product(db))
    assert sim.status == "blocked_quota" and sim.error_message == "budget" and spy.calls == 0


def test_cache_reuse_cost_zero_no_quota_increment(db, monkeypatch):
    spy = SpyProvider()
    monkeypatch.setattr(service, "get_provider", lambda *a, **k: spy)
    customer = customers.get_or_create_by_telegram(db, 8205)
    first = service.run(db, ready(db, customer).id)
    used = customer.simulations_used
    second = service.run(db, ready(db, customer).id)
    assert first.status == second.status == "completed"
    assert second.reused and second.simulation.cost_usd == 0 and customer.simulations_used == used
    assert spy.calls == 1


def test_failure_does_not_consume_quota_and_emits_event(db, monkeypatch):
    spy = SpyProvider(fail=True)
    monkeypatch.setattr(service, "get_provider", lambda *a, **k: spy)
    customer = customers.get_or_create_by_telegram(db, 8206)
    result = service.run(db, ready(db, customer).id)
    assert result.status == "failed" and customer.simulations_used == 0
    assert db.scalar(select(Event).where(Event.type == "simulation.failed"))


def test_rating_stored_and_event_emitted(db, monkeypatch):
    monkeypatch.setattr(service, "get_provider", lambda *a, **k: SpyProvider())
    customer = customers.get_or_create_by_telegram(db, 8207)
    result = service.run(db, ready(db, customer).id)
    rating = service.rate(db, result.simulation.id, 5, customer)
    assert rating.score == 5
    assert db.scalar(select(Event).where(Event.type == "simulation.rated")).payload["score"] == 5


def test_width_warning(db):
    customer = customers.get_or_create_by_telegram(db, 8208)
    sim = service.prepare(db, customer, product(db))
    sim.room_width_cm = 180
    assert "210 cm" in service.width_warning(sim) and "180 cm" in service.width_warning(sim)
