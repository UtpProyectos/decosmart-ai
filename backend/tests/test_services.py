from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.automation import events
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.timeutil import now_utc, today_local
from app.models import ApiUsage, Conversation, ErrorLog, Event, Inquiry, Product, Simulation
from app.services import budget, catalog, customers, inquiries, orders, quotes
from app.services.codes import next_code
from app.services.errors import log_error, sanitize_text
from tests.conftest import admin_texts


def _sku(db, sku):
    return db.scalar(select(Product).where(Product.sku == sku))


# ---------- codes ----------
def test_next_code_daily_sequence(db):
    day = today_local().strftime("%Y%m%d")
    assert next_code(db, "COT") == f"COT-{day}-0001"
    c = customers.get_or_create_web(db, "Ana", "ana@example.com")
    quotes.create_quote(db, c, [{"product_id": 1, "quantity": 1}])
    quotes.create_quote(db, c, [{"product_id": 2, "quantity": 1}])
    assert next_code(db, "COT") == f"COT-{day}-0003"
    assert next_code(db, "PED") == f"PED-{day}-0001"


# ---------- catalog ----------
def test_search_by_text_accent_insensitive(db):
    res = catalog.search_products(db, query="sofa")
    assert [p.sku for p in res] == ["DS-SOF-001"]
    assert catalog.search_products(db, query="Sofás grises")[0].sku == "DS-SOF-001"


def test_search_filters(db):
    assert {p.sku for p in catalog.search_products(db, category="camas")} == {"DS-CAM-001"}
    assert all(p.price <= 200 for p in catalog.search_products(db, max_price=200))
    assert {p.sku for p in catalog.search_products(db, room="oficina")} >= {"DS-ESC-001"}


def test_get_product_by_id_sku_slug(db):
    assert catalog.get_product(db, 1).id == 1
    assert catalog.get_product(db, "1").id == 1
    assert catalog.get_product(db, "ds-sof-001").sku == "DS-SOF-001"
    assert catalog.get_product(db, "sofa-oslo-3-plazas").sku == "DS-SOF-001"
    assert catalog.get_product(db, "NOPE") is None


def test_check_stock(db):
    r = catalog.check_stock(db, "DS-ALM-001", 5)
    assert r["ok"] and r["available"] == 3 and r["sufficient"] is False
    assert catalog.check_stock(db, "XX", 1)["ok"] is False


def test_recommend_budget_width_stock_max3(db):
    recs = catalog.recommend(db, budget=250)
    assert 0 < len(recs) <= 3
    assert all(p.price <= 250 and p.stock > 0 for p in recs)
    # precio descendente dentro del presupuesto
    assert [p.price for p in recs] == sorted([p.price for p in recs], reverse=True)
    assert all(p.width_cm <= 110 for p in catalog.recommend(db, max_width_cm=110))
    _sku(db, "DS-ESC-001").stock = 0
    db.commit()
    assert "DS-ESC-001" not in [p.sku for p in catalog.recommend(db, budget=250)]


def test_recommend_style_first(db):
    recs = catalog.recommend(db, budget=1000, style="nordico")
    assert recs[0].style == "nordico"


def test_product_serializers(db):
    p = _sku(db, "DS-ALM-001")
    pub = catalog.product_to_public(p)
    assert pub["price"] == "189.00" and pub["low_stock"] is True and pub["in_stock"] is True
    tool = catalog.product_to_tool(p)
    assert tool == {"ref": "DS-ALM-001", "name": p.name, "price_usd": "189.00", "stock": 3, "dims_cm": "120x180x35",
                    "colors": p.colors, "category": "almacenamiento", "material": p.material}


# ---------- customers / inquiries ----------
def test_customers_dedupe_and_conversation(db):
    a = customers.get_or_create_web(db, "Ana", "Ana@Example.com", "+51 1")
    b = customers.get_or_create_web(db, "Ana P", "ana@example.com", "+51 2")
    assert a.id == b.id and b.phone == "+51 2" and b.name == "Ana P"
    t = customers.get_or_create_by_telegram(db, 12345, "anita", "Ana")
    assert customers.get_or_create_by_telegram(db, 12345).id == t.id
    c1 = customers.get_or_create_conversation(db, t)
    assert customers.get_or_create_conversation(db, t).id == c1.id
    c1.last_message_at = now_utc() - timedelta(hours=7)
    db.commit()
    c2 = customers.get_or_create_conversation(db, t)
    assert c2.id != c1.id
    assert db.scalar(select(func.count(Event.id)).where(Event.type == "conversation.started")) == 2
    assert db.scalar(select(func.count(Conversation.id))) == 2


def test_record_inquiry_emits_event(db):
    inq = inquiries.record_inquiry(db, "price", product_id=1, channel="telegram", payload={"q": "precio"})
    assert db.get(Inquiry, inq.id).type == "price"
    ev = db.scalar(select(Event).where(Event.type == "inquiry.created"))
    assert ev.entity_id == inq.id
    assert ev.payload["type"] == "price" and ev.payload["channel"] == "telegram"


# ---------- quotes / orders ----------
def test_quote_transitions(db):
    c = customers.get_or_create_web(db, "Ana", "ana@example.com")
    q = quotes.create_quote(db, c, [{"product_ref": "DS-SOF-001", "quantity": 1}, {"product_id": 1, "quantity": 1}])
    assert len(q.items) == 1 and q.items[0].quantity == 2 and q.total == Decimal("1298.00")
    assert q.valid_until == today_local() + timedelta(days=get_settings().quote_validity_days)
    quotes.update_quote_status(db, q, "rejected")
    with pytest.raises(AppError) as e:
        quotes.update_quote_status(db, q, "accepted")
    assert e.value.code == "INVALID_TRANSITION" and e.value.status == 409


def test_format_quote_text(db):
    c = customers.get_or_create_web(db, "Ana", "ana@example.com")
    q = quotes.create_quote(db, c, [{"product_id": 1, "quantity": 2}])
    text = quotes.format_quote_text(q)
    assert q.code in text and "US$ 649.00" in text and "US$ 1298.00" in text and "Cotización referencial" in text


def test_expire_quotes(db, sent_messages):
    c = customers.get_or_create_by_telegram(db, 555, "x")
    q = quotes.create_quote(db, c, [{"product_id": 1, "quantity": 1}], channel="telegram")
    q.valid_until = today_local() - timedelta(days=1)
    db.commit()
    assert quotes.expire_quotes(db) == 1
    db.refresh(q)
    assert q.status == "expired"
    assert any("venció" in t for chat, t in sent_messages if chat == "555")


def test_cancel_confirmed_order_restores_stock(db):
    c = customers.get_or_create_web(db, "Ana", "ana@example.com")
    o = orders.create_order(db, c, items=[{"product_id": 2, "quantity": 3}])
    orders.confirm_order(db, o)
    assert db.get(Product, 2).stock == 12
    orders.update_order_status(db, o, "cancelled")
    assert db.get(Product, 2).stock == 15
    with pytest.raises(AppError):
        orders.update_order_status(db, o, "completed")


# ---------- budget ----------
def test_budget_can_spend_and_spent_only_live(db, monkeypatch):
    monkeypatch.setattr(get_settings(), "budget_usd_limit", 1.0)
    budget.record_usage(db, operation="chat", model="gpt-5.4-nano", cost_usd=5, mode="mock")
    assert budget.spent_usd(db) == Decimal("0")
    budget.record_usage(db, operation="chat", model="gpt-5.4-nano", cost_usd=Decimal("0.5"), mode="live")
    assert budget.spent_usd(db) == Decimal("0.5")
    assert budget.can_spend(db, Decimal("0.5")) is True
    assert budget.can_spend(db, Decimal("0.51")) is False


def test_budget_warning_emitted_once(db, monkeypatch, sent_messages):
    monkeypatch.setattr(get_settings(), "budget_usd_limit", 1.0)
    budget.record_usage(db, operation="chat", model="m", cost_usd=Decimal("0.85"), mode="live")
    budget.record_usage(db, operation="chat", model="m", cost_usd=Decimal("0.01"), mode="live")
    budget.can_spend(db, 0.01)
    warns = db.scalars(select(Event).where(Event.type == "budget.warning")).all()
    assert len(warns) == 1 and warns[0].payload["threshold"] == 80 and warns[0].notified
    assert len([t for t in admin_texts(sent_messages) if "Presupuesto" in t]) == 1


def test_check_llm_customer_limit(db, monkeypatch):
    monkeypatch.setattr(get_settings(), "max_llm_messages_per_customer_per_day", 2)
    c = customers.get_or_create_by_telegram(db, 777)
    budget.check_llm(db, c)
    for _ in range(2):
        budget.record_usage(db, operation="chat", model="gpt-5.4-nano", customer_id=c.id)
    with pytest.raises(budget.BudgetExceeded) as e:
        budget.check_llm(db, c)
    assert e.value.reason == "customer_limit"


def test_check_llm_budget_live(db, monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "ai_mode", "live")
    monkeypatch.setattr(s, "budget_usd_limit", 0.001)
    budget.record_usage(db, operation="chat", model="m", cost_usd=Decimal("0.001"), mode="live")
    with pytest.raises(budget.BudgetExceeded) as e:
        budget.check_llm(db, None)
    assert e.value.reason == "budget"


def test_track_records_success_and_failure(db):
    with budget.track(db, operation="chat", model="gpt-5.4-nano", mode="live") as t:
        t.input_tokens, t.output_tokens = 1000, 100
    with pytest.raises(RuntimeError), budget.track(db, operation="image_edit", model="gpt-image-1-mini", mode="live"):
        raise RuntimeError("boom")
    rows = db.scalars(select(ApiUsage).order_by(ApiUsage.id)).all()
    assert rows[0].success and rows[0].cost_usd == pricing_chat()
    assert rows[1].success is False and rows[1].cost_usd == 0


def pricing_chat():
    from app.core.pricing import estimate_chat

    return estimate_chat("gpt-5.4-nano", 1000, 0, 100)


# ---------- events / errors ----------
def test_emit_handler_failure_logged_not_raised(db):
    def broken(db_, event):
        raise ValueError("handler roto")

    events.on("test.event")(broken)
    try:
        ev = events.emit(db, "test.event", payload={"a": 1})
        db.commit()
    finally:
        events.unregister("test.event", broken)
    assert ev.id and ev.processed
    err = db.scalar(select(ErrorLog).where(ErrorLog.source == "automation"))
    assert err.error_type == "ValueError" and "handler roto" in err.message


def test_log_error_sanitizes(db):
    e = log_error(db, "bot", "X", "token 123456789:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA tel +51 999 999 999",
                  {"phone": "+51999", "nested": {"api_key": "sk-123"}, "ok": 1})
    assert "AAAA" not in e.message and "999 999" not in e.message
    assert e.context == {"phone": "[redacted]", "nested": {"api_key": "[redacted]"}, "ok": 1}
    assert sanitize_text("x@y.com") == "[email]"


def test_cleanup_photos(db, monkeypatch):
    from app.automation.scheduler import cleanup_photos
    from app.storage import get_storage

    st = get_storage()
    c = customers.get_or_create_by_telegram(db, 1)
    st.put("customers/1/inputs/old.jpg", b"x")
    st.put("customers/1/inputs/new.jpg", b"y")
    old = Simulation(customer_id=c.id, product_id=1, input_key="customers/1/inputs/old.jpg",
                     created_at=now_utc() - timedelta(days=30))
    new = Simulation(customer_id=c.id, product_id=1, input_key="customers/1/inputs/new.jpg")
    db.add_all([old, new])
    db.commit()
    assert cleanup_photos(db) == 1
    db.refresh(old)
    assert old.input_key is None and not st.exists("customers/1/inputs/old.jpg")
    assert st.exists("customers/1/inputs/new.jpg")
