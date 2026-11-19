from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.security import limiter
from app.models import Event, Inquiry, Product
from tests.conftest import admin_texts

CUSTOMER = {"name": "Ana Pérez", "email": "ana@example.com", "phone": "+51999999999"}


def _quote(client, items, **extra):
    return client.post("/api/quotes", json={"customer": CUSTOMER, "items": items, **extra})


def test_categories(client):
    r = client.get("/api/categories")
    assert r.status_code == 200
    cats = r.json()
    assert len(cats) == 6 and all(c["product_count"] == 1 for c in cats)


def test_list_products_shape(client):
    body = client.get("/api/products").json()
    assert body["total"] == 6 and body["limit"] == 20 and body["offset"] == 0
    p = next(i for i in body["items"] if i["sku"] == "DS-SOF-001")
    assert p["price"] == "649.00" and p["currency"] == "USD"
    assert p["category"] == {"slug": "sofas", "name": "Sofás"}
    assert p["dimensions"] == {"width_cm": 210, "height_cm": 85, "depth_cm": 90}
    assert p["in_stock"] is True and p["low_stock"] is False
    assert p["primary_image"].startswith("/static/products/")


def test_list_products_filters(client):
    assert [i["sku"] for i in client.get("/api/products?category=sofas").json()["items"]] == ["DS-SOF-001"]
    body = client.get("/api/products?max_price=150&min_price=120").json()
    assert [i["sku"] for i in body["items"]] == ["DS-MES-001"]
    body = client.get("/api/products?limit=2&offset=1").json()
    assert body["total"] == 6 and len(body["items"]) == 2
    assert client.get("/api/products?q=escritorio").json()["items"][0]["sku"] == "DS-ESC-001"
    assert client.get("/api/products?limit=51").status_code == 422


def test_product_detail_and_inquiry(client, db):
    r = client.get("/api/products/sofa-oslo-3-plazas")
    assert r.status_code == 200
    d = r.json()
    assert d["description"] and d["images"][0]["url"].endswith("sofa-oslo.jpg")
    assert client.get(f"/api/products/{d['id']}").status_code == 200
    inq = db.scalars(select(Inquiry)).all()
    assert len(inq) == 2 and inq[0].type == "product_info" and inq[0].channel == "web" and inq[0].customer_id is None


def test_product_detail_404_format(client):
    r = client.get("/api/products/no-existe")
    assert r.status_code == 404
    assert r.json() == {"error": {"code": "PRODUCT_NOT_FOUND", "message": "Producto no encontrado", "details": {}}}


def test_validation_error_format(client):
    r = client.post("/api/quotes", json={"customer": {"name": "x", "email": "bad"}, "items": []})
    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_create_quote_frozen_price_and_totals(client, db, admin_headers, sent_messages):
    r = _quote(client, [{"product_id": 1, "quantity": 1}, {"product_id": 2, "quantity": 2}], notes="Entrega en Lima")
    assert r.status_code == 201
    q = r.json()
    assert q["code"].startswith("COT-") and q["code"].endswith("-0001")
    assert q["status"] == "sent" and q["subtotal"] == "947.00" and q["total"] == "947.00"
    assert q["items"][1] == {"product_id": 2, "sku": "DS-MES-001", "name": "Mesa de centro Nórdica", "quantity": 2,
                             "unit_price": "149.00", "line_total": "298.00"}
    assert q["disclaimer"].startswith("Cotización referencial")
    # Cambiar precio no altera la cotización
    client.patch("/admin/products/1", json={"price": "599.00"}, headers=admin_headers)
    again = client.get(f"/api/quotes/{q['code']}").json()
    assert again["items"][0]["unit_price"] == "649.00"
    assert db.scalar(select(func.count(Event.id)).where(Event.type == "quote.created")) == 1
    assert any(q["code"] in t for t in admin_texts(sent_messages))


def test_create_quote_insufficient_stock(client):
    r = _quote(client, [{"product_id": 5, "quantity": 4}])
    assert r.status_code == 409
    err = r.json()["error"]
    assert err["code"] == "INSUFFICIENT_STOCK"
    assert err["details"]["product_id"] == 5 and err["details"]["available"] == 3


def test_create_quote_unknown_product(client):
    r = _quote(client, [{"product_id": 999, "quantity": 1}])
    assert r.status_code == 404 and r.json()["error"]["code"] == "PRODUCT_NOT_FOUND"


def test_get_quote_hides_contact(client):
    code = _quote(client, [{"product_id": 1, "quantity": 1}]).json()["code"]
    r = client.get(f"/api/quotes/{code}")
    assert r.status_code == 200
    raw = r.text
    assert "ana@example.com" not in raw and "+51999999999" not in raw and "Ana" not in raw
    assert client.get("/api/quotes/COT-00000000-0001").json()["error"]["code"] == "QUOTE_NOT_FOUND"


def test_order_from_quote(client, db, admin_headers, sent_messages):
    code = _quote(client, [{"product_id": 1, "quantity": 1}]).json()["code"]
    r = client.post("/api/orders", json={"quote_code": code, "customer": CUSTOMER, "delivery_address": "Av. 123"})
    assert r.status_code == 201
    o = r.json()
    assert o["code"].startswith("PED-") and o["status"] == "pending" and o["total"] == "649.00"
    assert o["is_demo"] is True and "No se realizó ningún cobro" in o["message"]
    assert client.get(f"/api/quotes/{code}").json()["status"] == "accepted"
    assert any(t.startswith(f"🛒 Nuevo pedido demo {o['code']} US$649.00 (Ana Pérez, web)")
               for t in admin_texts(sent_messages))
    # misma cotización otra vez → transición inválida
    r2 = client.post("/api/orders", json={"quote_code": code})
    assert r2.status_code == 409 and r2.json()["error"]["code"] == "INVALID_TRANSITION"
    assert db.get(Product, 1).stock == 8  # crear pedido no descuenta stock
    assert client.get(f"/api/orders/{o['code']}").json()["quote_code"] == code


def test_order_from_items(client):
    r = client.post("/api/orders", json={"customer": CUSTOMER, "items": [{"product_id": 3, "quantity": 2}]})
    assert r.status_code == 201 and r.json()["total"] == "238.00"
    assert client.post("/api/orders", json={"items": [{"product_id": 3, "quantity": 1}]}).status_code == 422
    assert client.get("/api/orders/PED-00000000-0009").status_code == 404


def test_public_config(client):
    assert client.get("/api/config/public").json() == {
        "telegram_bot_url": "https://t.me/DecoSmartBot", "store_name": "DecoSmart", "currency": "USD"}


def test_rate_limit(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "rate_limit_per_min", 2)
    assert client.get("/api/categories").status_code == 200  # deshabilitado en test por defecto
    limiter.force_enabled = True
    assert client.get("/api/categories").status_code == 200
    assert client.get("/api/categories").status_code == 200
    r = client.get("/api/categories")
    assert r.status_code == 429 and r.json()["error"]["code"] == "RATE_LIMITED"


def test_media_serves_local_and_blocks_traversal(client, tmp_path):
    from app.storage import get_storage

    st = get_storage()
    st.put("customers/1/outputs/1.jpg", b"\xff\xd8jpeg", "image/jpeg")
    r = client.get("/media/customers/1/outputs/1.jpg")
    assert r.status_code == 200 and r.content == b"\xff\xd8jpeg"
    (tmp_path / "secret.txt").write_text("secret")
    for path in ("/media/..%2Fsecret.txt", "/media/customers/..%2F..%2Fsecret.txt", "/media/%2e%2e/secret.txt",
                 "/media/..\\secret.txt", "/media/missing.jpg"):
        resp = client.get(path)
        assert resp.status_code == 404, path
        assert "secret" not in resp.text


def test_media_404_when_s3(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "storage_backend", "s3")
    assert client.get("/media/customers/1/outputs/1.jpg").status_code == 404
