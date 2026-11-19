from decimal import Decimal

from sqlalchemy import select

from app.models import Event, Product, Simulation, SimulationRating
from app.services import budget, customers, inquiries
from tests.conftest import admin_texts

CUSTOMER = {"name": "Ana Pérez", "email": "ana@example.com", "phone": "+51999999999"}

SUMMARY_KEYS = {
    "conversations_total", "unique_customers", "inquiries_total", "quotes_total", "quotes_accepted", "orders_total",
    "orders_completed", "simulations_total", "simulations_failed", "simulations_reused", "avg_rating",
    "ratings_count", "api_cost_usd", "budget_usd", "budget_used_pct", "errors_total", "ai_mode",
}


def _order(client, items):
    r = client.post("/api/orders", json={"customer": CUSTOMER, "items": items})
    assert r.status_code == 201
    return r.json()["code"]


def test_admin_requires_key(client):
    for path in ("/admin/metrics/summary", "/admin/usage", "/admin/events", "/admin/quotes"):
        r = client.get(path)
        assert r.status_code == 401 and r.json()["error"]["code"] == "UNAUTHORIZED"
    assert client.get("/admin/usage", headers={"X-Admin-Key": "wrong"}).status_code == 401


def test_order_transitions(client, admin_headers):
    code = _order(client, [{"product_id": 1, "quantity": 1}])
    r = client.patch(f"/admin/orders/{code}", json={"status": "completed"}, headers=admin_headers)
    assert r.status_code == 409 and r.json()["error"]["code"] == "INVALID_TRANSITION"
    assert client.patch(f"/admin/orders/{code}", json={"status": "confirmed"}, headers=admin_headers).json()[
        "status"] == "confirmed"
    assert client.patch(f"/admin/orders/{code}", json={"status": "completed"}, headers=admin_headers).json()[
        "status"] == "completed"
    assert client.patch(f"/admin/orders/{code}", json={"status": "pending"}, headers=admin_headers).status_code == 409
    assert client.patch("/admin/orders/PED-X", json={"status": "confirmed"}, headers=admin_headers).status_code == 404


def test_quote_transitions_admin(client, admin_headers):
    code = client.post("/api/quotes", json={"customer": CUSTOMER, "items": [{"product_id": 1, "quantity": 1}]}).json()[
        "code"]
    r = client.patch(f"/admin/quotes/{code}", json={"status": "draft"}, headers=admin_headers)
    assert r.status_code == 409 and r.json()["error"]["code"] == "INVALID_TRANSITION"
    r = client.patch(f"/admin/quotes/{code}", json={"status": "rejected"}, headers=admin_headers)
    assert r.status_code == 200 and r.json()["status"] == "rejected" and r.json()["customer"]["email"]
    assert client.get("/admin/quotes?status=rejected", headers=admin_headers).json()["total"] == 1
    assert client.get("/admin/quotes?status=sent", headers=admin_headers).json()["total"] == 0


def test_confirm_order_decrements_stock_and_low_stock_once(client, db, admin_headers, sent_messages):
    # Escritorio: stock 10 → confirmar 5 deja 5 (≤ umbral)
    c1 = _order(client, [{"product_id": 6, "quantity": 5}])
    client.patch(f"/admin/orders/{c1}", json={"status": "confirmed"}, headers=admin_headers)
    db.expire_all()
    p = db.get(Product, 6)
    assert p.stock == 5 and p.low_stock_notified
    c2 = _order(client, [{"product_id": 6, "quantity": 1}])
    client.patch(f"/admin/orders/{c2}", json={"status": "confirmed"}, headers=admin_headers)
    low = db.scalars(select(Event).where(Event.type == "product.low_stock")).all()
    assert len(low) == 1 and low[0].notified
    alerts = [t for t in admin_texts(sent_messages) if t.startswith("⚠️ Stock bajo")]
    assert alerts == [f"⚠️ Stock bajo: {p.name} (DS-ESC-001) quedan 5"]
    # reponer resetea el flag; volver a bajar vuelve a avisar
    r = client.patch("/admin/products/6", json={"stock": 20}, headers=admin_headers)
    assert r.json()["stock"] == 20 and r.json()["low_stock"] is False
    db.expire_all()
    assert db.get(Product, 6).low_stock_notified is False
    client.patch("/admin/products/6", json={"stock": 2}, headers=admin_headers)
    assert len([t for t in admin_texts(sent_messages) if t.startswith("⚠️ Stock bajo")]) == 2


def test_confirm_order_insufficient_stock(client, admin_headers):
    code = _order(client, [{"product_id": 5, "quantity": 3}])
    client.patch("/admin/products/5", json={"stock": 1}, headers=admin_headers)
    r = client.patch(f"/admin/orders/{code}", json={"status": "confirmed"}, headers=admin_headers)
    assert r.status_code == 409 and r.json()["error"]["code"] == "INSUFFICIENT_STOCK"


def test_patch_product_validation(client, admin_headers):
    assert client.patch("/admin/products/1", json={"stock": -1}, headers=admin_headers).status_code == 422
    assert client.patch("/admin/products/99", json={"stock": 1}, headers=admin_headers).status_code == 404
    r = client.patch("/admin/products/1", json={"price": "599.00", "active": False}, headers=admin_headers)
    assert r.json()["price"] == "599.00" and r.json()["active"] is False
    assert client.get("/api/products/1").status_code == 404


def test_patch_customer_resets_simulations(client, db, admin_headers):
    c = customers.get_or_create_by_telegram(db, 4242, "u")
    c.simulations_used = 2
    db.commit()
    r = client.patch(f"/admin/customers/{c.id}", json={"simulations_used": 0}, headers=admin_headers)
    assert r.status_code == 200 and r.json()["simulations_used"] == 0
    db.expire_all()
    assert db.get(type(c), c.id).simulations_used == 0
    assert client.patch(f"/admin/customers/{c.id}", json={"simulations_used": -1},
                        headers=admin_headers).status_code == 422
    assert client.patch("/admin/customers/9999", json={"simulations_used": 0}, headers=admin_headers).status_code == 404
    assert client.patch(f"/admin/customers/{c.id}", json={"simulations_used": 0}).status_code == 401


def test_metrics_summary_keys_and_counts(client, db, admin_headers):
    # 2 consultas, 2 cotizaciones (1 aceptada vía pedido), 2 pedidos (1 completado)
    client.get("/api/products/1")
    inquiries.record_inquiry(db, "price", product_id=2)
    q1 = client.post("/api/quotes", json={"customer": CUSTOMER, "items": [{"product_id": 1, "quantity": 1}]}).json()
    client.post("/api/quotes", json={"customer": CUSTOMER, "items": [{"product_id": 2, "quantity": 1}]})
    client.post("/api/orders", json={"quote_code": q1["code"]})
    code = _order(client, [{"product_id": 3, "quantity": 1}])
    client.patch(f"/admin/orders/{code}", json={"status": "confirmed"}, headers=admin_headers)
    client.patch(f"/admin/orders/{code}", json={"status": "completed"}, headers=admin_headers)
    t = customers.get_or_create_by_telegram(db, 1)
    customers.get_or_create_conversation(db, t)
    sim = Simulation(customer_id=t.id, product_id=1, status="completed")
    db.add(sim)
    db.flush()
    db.add(SimulationRating(simulation_id=sim.id, score=4))
    db.commit()
    budget.record_usage(db, operation="image_edit", model="gpt-image-1-mini", cost_usd=Decimal("0.35"), mode="live")

    s = client.get("/admin/metrics/summary", headers=admin_headers).json()
    assert set(s) == SUMMARY_KEYS
    assert s["inquiries_total"] == 2 and s["quotes_total"] == 2 and s["quotes_accepted"] == 1
    assert s["orders_total"] == 2 and s["orders_completed"] == 1
    assert s["conversations_total"] == 1 and s["simulations_total"] == 1 and s["avg_rating"] == 4.0
    assert s["api_cost_usd"] == "0.3500" and s["budget_usd"] == "3.50" and s["budget_used_pct"] == 10.0
    assert s["ai_mode"] == "mock"
    assert client.get("/admin/metrics/summary?from=2000-01-01&to=2000-01-02",
                      headers=admin_headers).json()["quotes_total"] == 0

    daily = client.get("/admin/metrics/daily?days=7", headers=admin_headers).json()
    assert len(daily) == 7 and daily[-1]["quotes"] == 2 and daily[0]["quotes"] == 0
    assert set(daily[0]) == {"date", "conversations", "inquiries", "quotes", "orders", "simulations"}

    top_inq = client.get("/admin/metrics/top-products?kind=inquired", headers=admin_headers).json()
    assert {x["product_id"] for x in top_inq} == {1, 2}
    top_req = client.get("/admin/metrics/top-products?kind=requested", headers=admin_headers).json()
    assert top_req[0]["product_id"] == 1 and top_req[0]["count"] == 2  # quote + order


def test_usage_endpoint(client, db, admin_headers):
    budget.record_usage(db, operation="chat", model="gpt-5.4-nano", input_tokens=1000, output_tokens=100, mode="live")
    budget.record_usage(db, operation="image_edit", model="gpt-image-1-mini", mode="live")
    budget.record_usage(db, operation="chat", model="gpt-5.4-nano", mode="mock")
    u = client.get("/admin/usage?days=30", headers=admin_headers).json()
    assert u["calls"] == 3 and len(u["by_day"]) == 30
    ops = {x["operation"]: x for x in u["by_operation"]}
    assert ops["chat"]["calls"] == 2 and ops["image_edit"]["cost_usd"] == "0.0110"
    assert {x["model"] for x in u["by_model"]} == {"gpt-5.4-nano", "gpt-image-1-mini"}
    assert u["pricing_verified_at"] == "2026-11-18" and u["ai_mode"] == "mock" and u["budget_usd"] == "3.50"
    assert u["budget_used_pct"] > 0 and u["by_day"][-1]["calls"] == 3


def test_events_listing(client, admin_headers):
    client.post("/api/quotes", json={"customer": CUSTOMER, "items": [{"product_id": 1, "quantity": 1}]})
    client.get("/api/products/1")
    all_ev = client.get("/admin/events", headers=admin_headers).json()
    assert all_ev["total"] >= 2
    q = client.get("/admin/events?type=quote.created", headers=admin_headers).json()
    assert q["total"] == 1 and q["items"][0]["notified"] is True and q["items"][0]["payload"]["total"] == "649.00"
    page = client.get("/admin/events?limit=1&offset=1", headers=admin_headers).json()
    assert len(page["items"]) == 1 and page["offset"] == 1


def test_errors_listing(client, db, admin_headers):
    from app.services.errors import log_error

    log_error(db, "bot", "Boom", "algo falló")
    body = client.get("/admin/errors", headers=admin_headers).json()
    assert body["total"] == 1 and body["items"][0]["error_type"] == "Boom"


def test_simulations_listing(client, db, admin_headers):
    from app.storage import get_storage

    t = customers.get_or_create_by_telegram(db, 1)
    get_storage().put("customers/1/outputs/1.jpg", b"x")
    sim = Simulation(customer_id=t.id, product_id=1, status="completed", output_key="customers/1/outputs/1.jpg")
    db.add(sim)
    db.flush()
    db.add(SimulationRating(simulation_id=sim.id, score=5))
    db.commit()
    items = client.get("/admin/simulations", headers=admin_headers).json()["items"]
    assert items[0]["rating"] == 5 and items[0]["output_url"].endswith("/media/customers/1/outputs/1.jpg")


def test_daily_summary_job_idempotent(client, admin_headers, sent_messages):
    client.post("/api/quotes", json={"customer": CUSTOMER, "items": [{"product_id": 1, "quantity": 1}]})
    r = client.post("/admin/jobs/daily-summary", headers=admin_headers).json()
    assert r["sent"] is True and "Cotizaciones: 1" in r["text"]
    summaries = [t for t in admin_texts(sent_messages) if t.startswith("📊 Resumen")]
    assert len(summaries) == 1
    r2 = client.post("/admin/jobs/daily-summary", headers=admin_headers).json()
    assert r2 == {"sent": False, "reason": "already_sent", "date": r["date"]}
    r3 = client.post("/admin/jobs/daily-summary?force=true", headers=admin_headers).json()
    assert r3["sent"] is True
    assert len([t for t in admin_texts(sent_messages) if t.startswith("📊 Resumen")]) == 2


def test_cleanup_photos_endpoint(client, admin_headers):
    assert client.post("/admin/jobs/cleanup-photos", headers=admin_headers).json() == {"deleted": 0}


def test_telegram_quote_sent_to_customer_and_rating_alert(client, db, sent_messages):
    from app.automation.events import emit
    from app.services import quotes

    t = customers.get_or_create_by_telegram(db, 3131, "tg")
    q = quotes.create_quote(db, t, [{"product_id": 2, "quantity": 1}], channel="telegram")
    to_customer = [m for c, m in sent_messages if c == "3131"]
    assert len(to_customer) == 1 and q.code in to_customer[0] and "US$ 149.00" in to_customer[0]
    sim = Simulation(customer_id=t.id, product_id=1, status="completed")
    db.add(sim)
    db.commit()
    emit(db, "simulation.rated", entity_type="simulation", entity_id=sim.id, customer_id=t.id, payload={"score": 4})
    emit(db, "simulation.rated", entity_type="simulation", entity_id=sim.id, customer_id=t.id, payload={"score": 1})
    db.commit()
    assert len([m for m in admin_texts(sent_messages) if "calificada con" in m]) == 1


def test_scheduler_not_started_in_test():
    from app.automation import scheduler

    assert scheduler.should_start() is False
    sched = scheduler.build_scheduler()
    assert {j.id for j in sched.get_jobs()} == {"daily_summary", "expire_quotes", "cleanup_photos"}
