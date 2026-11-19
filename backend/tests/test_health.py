from sqlalchemy import func, select

from app.models import Product


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["db"] == "ok"
    assert body["ai_mode"] == "mock"


def test_seed_creates_six_products(db):
    assert db.scalar(select(func.count(Product.id))) == 6


def test_static_product_image(client):
    r = client.get("/static/products/sofa-oslo.jpg")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/jpeg"
