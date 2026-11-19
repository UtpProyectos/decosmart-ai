"""Gestión admin de productos e imágenes (doc 04, Ampliación v0.2)."""

from io import BytesIO

from PIL import Image
from sqlalchemy import inspect, select

from app.core.config import get_settings
from app.core.db import engine
from app.models import Event, Product, ProductImage
from app.services import product_admin
from app.storage import get_storage

NEW = {
    "sku": "DS-SOF-002", "category_slug": "sofas", "name": "Sofá Lino 2 plazas", "description": "Sofá de lino.",
    "price": "499.00", "stock": 8, "width_cm": 160, "height_cm": 85, "depth_cm": 88, "colors": ["crudo", "gris"],
    "material": "Lino y madera", "style": "nordico", "room_types": ["sala"],
}


def img_bytes(fmt="JPEG", size=(2000, 1500), color="red") -> bytes:
    out = BytesIO()
    Image.new("RGB", size, color).save(out, fmt)
    return out.getvalue()


def create(client, headers, **overrides) -> dict:
    r = client.post("/admin/products", json={**NEW, **overrides}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def upload(client, headers, product_id, files, **form):
    return client.post(f"/admin/products/{product_id}/images", headers=headers,
                       files=[("files", f) for f in files], data=form)


# ---------- Migración ----------
def test_migration_adds_v02_columns_and_marks_seed_reference(client, db):
    cols = {c["name"] for c in inspect(engine).get_columns("product_images")}
    assert {"storage_key", "is_reference", "width", "height", "bytes"} <= cols
    with engine.connect() as conn:
        assert conn.exec_driver_sql("SELECT version_num FROM alembic_version").scalar() == "4b8e947453ad"
    seed = db.scalars(select(ProductImage)).all()
    assert seed and all(i.is_reference and i.is_primary and i.storage_key is None for i in seed)


# ---------- Productos ----------
def test_create_product_auto_slug_and_shape(client, admin_headers):
    p = create(client, admin_headers, name="Sofá Lino Ñandú 2 plazas")
    assert p["slug"] == "sofa-lino-nandu-2-plazas"
    assert p["price"] == "499.00" and p["active"] is True and p["images"] == [] and p["primary_image"] is None
    assert p["created_at"] and p["updated_at"] and p["category"] == {"slug": "sofas", "name": "Sofás"}
    assert client.get(f"/api/products/{p['slug']}").status_code == 200


def test_create_product_sku_taken_and_slug_taken(client, admin_headers):
    r = client.post("/admin/products", json={**NEW, "sku": "ds-sof-001"}, headers=admin_headers)
    assert r.status_code == 409 and r.json()["error"]["code"] == "SKU_TAKEN"
    r = client.post("/admin/products", json={**NEW, "slug": "sofa-oslo-3-plazas"}, headers=admin_headers)
    assert r.status_code == 409 and r.json()["error"]["code"] == "SLUG_TAKEN"


def test_create_product_auto_slug_collision_gets_suffix(client, admin_headers):
    p = create(client, admin_headers, name="Sofá Oslo 3 plazas")
    assert p["slug"] == "sofa-oslo-3-plazas-2"


def test_create_product_validation(client, admin_headers):
    r = client.post("/admin/products", json={**NEW, "category_slug": "nope"}, headers=admin_headers)
    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR"
    missing = {k: v for k, v in NEW.items() if k != "price"}
    assert client.post("/admin/products", json=missing, headers=admin_headers).status_code == 422
    assert client.post("/admin/products", json={**NEW, "stock": -1}, headers=admin_headers).status_code == 422


def test_patch_all_fields(client, admin_headers):
    p = create(client, admin_headers)
    body = {"sku": "DS-SOF-003", "category_slug": "camas", "name": "Cama Lino", "slug": "cama-lino",
            "description": "Nueva", "price": "350.50", "stock": 9, "width_cm": 150, "height_cm": 40, "depth_cm": 200,
            "colors": ["blanco"], "material": "Pino", "style": "moderno", "room_types": ["dormitorio"],
            "active": True}
    r = client.patch(f"/admin/products/{p['id']}", json=body, headers=admin_headers)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["sku"] == "DS-SOF-003" and d["category"]["slug"] == "camas" and d["slug"] == "cama-lino"
    assert d["price"] == "350.50" and d["dimensions"] == {"width_cm": 150, "height_cm": 40, "depth_cm": 200}
    assert d["colors"] == ["blanco"] and d["room_types"] == ["dormitorio"] and d["description"] == "Nueva"
    r = client.patch(f"/admin/products/{p['id']}", json={"slug": "sofa-oslo-3-plazas"}, headers=admin_headers)
    assert r.status_code == 409 and r.json()["error"]["code"] == "SLUG_TAKEN"
    assert client.patch(f"/admin/products/{p['id']}", json={"name": None}, headers=admin_headers).status_code == 422


def test_patch_stock_emits_low_stock(client, admin_headers, db):
    p = create(client, admin_headers)
    client.patch(f"/admin/products/{p['id']}", json={"stock": 2}, headers=admin_headers)
    events = db.scalars(select(Event).where(Event.type == "product.low_stock", Event.entity_id == p["id"])).all()
    assert len(events) == 1


def test_deactivate_hides_from_public_visible_in_admin(client, admin_headers):
    p = create(client, admin_headers)
    assert client.delete(f"/admin/products/{p['id']}", headers=admin_headers).status_code == 204
    assert client.get(f"/api/products/{p['id']}").status_code == 404
    assert p["id"] not in [i["id"] for i in client.get("/api/products?limit=50").json()["items"]]
    admin = client.get("/admin/products?include_inactive=true", headers=admin_headers).json()
    row = next(i for i in admin["items"] if i["id"] == p["id"])
    assert row["active"] is False and admin["total"] == 7
    assert client.get(f"/admin/products/{p['id']}", headers=admin_headers).json()["active"] is False
    only_active = client.get("/admin/products?include_inactive=false", headers=admin_headers).json()
    assert only_active["total"] == 6
    assert client.delete("/admin/products/999", headers=admin_headers).status_code == 404


def test_admin_categories(client, admin_headers):
    cats = client.get("/admin/categories", headers=admin_headers).json()
    assert cats[0] == {"id": 1, "slug": "sofas", "name": "Sofás"} and len(cats) == 6


def test_admin_product_endpoints_require_key(client):
    assert client.get("/admin/products").status_code == 401
    assert client.post("/admin/products", json=NEW).status_code == 401
    assert client.get("/admin/categories").status_code == 401
    r = client.post("/admin/products/1/images", files=[("files", ("a.jpg", img_bytes(), "image/jpeg"))])
    assert r.status_code == 401 and r.json()["error"]["code"] == "UNAUTHORIZED"


def test_admin_open_when_key_empty(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "admin_api_key", "")
    assert client.get("/admin/categories").status_code == 200
    assert client.post("/admin/products", json=NEW).status_code == 201


# ---------- Imágenes ----------
def test_upload_two_images_first_becomes_primary(client, admin_headers, db):
    p = create(client, admin_headers)
    r = upload(client, admin_headers, p["id"], [("a.jpg", img_bytes(), "image/jpeg"),
                                                 ("b.png", img_bytes("PNG", (800, 600), "blue"), "image/png")],
               alt="Vista frontal", is_reference="true")
    assert r.status_code == 201, r.text
    images = r.json()["images"]
    assert len(images) == 2
    first, second = images
    assert first["url"] == f"/api/images/{first['id']}" and second["url"] == f"/api/images/{second['id']}"
    assert first["is_primary"] is True and second["is_primary"] is False
    assert first["is_reference"] and first["alt"] == "Vista frontal"
    assert (first["width"], first["height"]) == (1280, 960) and (second["width"], second["height"]) == (800, 600)
    assert [first["sort_order"], second["sort_order"]] == [0, 1]
    row = db.get(ProductImage, first["id"])
    assert row.storage_key.startswith(f"products/{p['id']}/") and row.storage_key.endswith(".jpg")
    stored = get_storage().get(row.storage_key)
    assert len(stored) == row.bytes
    with Image.open(BytesIO(stored)) as im:
        assert im.format == "JPEG" and max(im.size) <= 1280
    detail = client.get(f"/api/products/{p['id']}").json()
    assert detail["primary_image"] == first["url"] and [i["id"] for i in detail["images"]] == [first["id"],
                                                                                                second["id"]]
    listed = next(i for i in client.get("/api/products?limit=50").json()["items"] if i["id"] == p["id"])
    assert listed["images"][0]["url"] == first["url"]


def test_upload_webp_and_second_upload_not_primary(client, admin_headers):
    p = create(client, admin_headers)
    upload(client, admin_headers, p["id"], [("a.jpg", img_bytes(), "image/jpeg")])
    r = upload(client, admin_headers, p["id"], [("c.webp", img_bytes("WEBP", (640, 640)), "image/webp")])
    assert r.status_code == 201 and r.json()["images"][0]["is_primary"] is False
    assert r.json()["images"][0]["is_reference"] is False


def test_upload_invalid_image(client, admin_headers):
    p = create(client, admin_headers)
    r = upload(client, admin_headers, p["id"], [("fake.jpg", b"not an image", "image/jpeg")])
    assert r.status_code == 422 and r.json()["error"]["code"] == "INVALID_IMAGE"
    r = upload(client, admin_headers, p["id"], [("anim.gif", img_bytes("GIF", (640, 640)), "image/gif")])
    assert r.status_code == 422 and r.json()["error"]["code"] == "INVALID_IMAGE"
    r = upload(client, admin_headers, p["id"], [("tiny.jpg", img_bytes(size=(200, 200)), "image/jpeg")])
    assert r.status_code == 422 and r.json()["error"]["code"] == "INVALID_IMAGE"
    assert client.get(f"/admin/products/{p['id']}", headers=admin_headers).json()["images"] == []


def test_upload_too_large(client, admin_headers, monkeypatch):
    monkeypatch.setattr(get_settings(), "max_upload_mb", 0)
    p = create(client, admin_headers)
    r = upload(client, admin_headers, p["id"], [("a.jpg", img_bytes(), "image/jpeg")])
    assert r.status_code == 422 and r.json()["error"]["code"] == "INVALID_IMAGE"


def test_upload_too_many_images(client, admin_headers, monkeypatch):
    monkeypatch.setattr(get_settings(), "max_images_per_product", 3)
    p = create(client, admin_headers)
    small = ("a.jpg", img_bytes(size=(640, 480)), "image/jpeg")
    assert upload(client, admin_headers, p["id"], [small, small]).status_code == 201
    r = upload(client, admin_headers, p["id"], [small, small])
    assert r.status_code == 422 and r.json()["error"]["code"] == "TOO_MANY_IMAGES"
    r = upload(client, admin_headers, p["id"], [small] * 9)
    assert r.status_code == 422 and r.json()["error"]["code"] == "TOO_MANY_IMAGES"


def _three_images(client, headers) -> tuple[dict, list[dict]]:
    p = create(client, headers)
    small = ("a.jpg", img_bytes(size=(640, 480)), "image/jpeg")
    images = upload(client, headers, p["id"], [small, small, small]).json()["images"]
    return p, images


def test_set_primary_keeps_single_primary(client, admin_headers):
    p, images = _three_images(client, admin_headers)
    r = client.patch(f"/admin/products/{p['id']}/images/{images[2]['id']}",
                     json={"is_primary": True, "is_reference": True, "alt": "Detalle"}, headers=admin_headers)
    assert r.status_code == 200 and r.json()["is_primary"] and r.json()["alt"] == "Detalle"
    imgs = client.get(f"/admin/products/{p['id']}", headers=admin_headers).json()["images"]
    assert [i["id"] for i in imgs if i["is_primary"]] == [images[2]["id"]]
    # desmarcar la principal: pasa a la primera de las demás
    client.patch(f"/admin/products/{p['id']}/images/{images[2]['id']}", json={"is_primary": False},
                 headers=admin_headers)
    imgs = client.get(f"/admin/products/{p['id']}", headers=admin_headers).json()["images"]
    assert [i["id"] for i in imgs if i["is_primary"]] == [images[0]["id"]]
    r = client.patch(f"/admin/products/{p['id']}/images/99999", json={"alt": "x"}, headers=admin_headers)
    assert r.status_code == 404 and r.json()["error"]["code"] == "IMAGE_NOT_FOUND"


def test_reorder_images(client, admin_headers):
    p, images = _three_images(client, admin_headers)
    order = [images[2]["id"], images[0]["id"], images[1]["id"]]
    r = client.put(f"/admin/products/{p['id']}/images/order", json={"image_ids": order}, headers=admin_headers)
    assert r.status_code == 200
    out = r.json()["images"]
    assert [i["id"] for i in out] == order and [i["sort_order"] for i in out] == [0, 1, 2]
    r = client.put(f"/admin/products/{p['id']}/images/order", json={"image_ids": order[:2]}, headers=admin_headers)
    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_delete_primary_reassigns_and_removes_from_storage(client, admin_headers, db):
    p, images = _three_images(client, admin_headers)
    key = db.get(ProductImage, images[0]["id"]).storage_key
    assert get_storage().exists(key)
    r = client.delete(f"/admin/products/{p['id']}/images/{images[0]['id']}", headers=admin_headers)
    assert r.status_code == 204
    assert not get_storage().exists(key)
    imgs = client.get(f"/admin/products/{p['id']}", headers=admin_headers).json()["images"]
    assert [i["id"] for i in imgs] == [images[1]["id"], images[2]["id"]]
    assert [i["is_primary"] for i in imgs] == [True, False]
    assert client.delete(f"/admin/products/{p['id']}/images/{images[0]['id']}",
                         headers=admin_headers).status_code == 404


def test_get_image_local_bytes_and_seed_redirect(client, admin_headers, db):
    p = create(client, admin_headers)
    img = upload(client, admin_headers, p["id"], [("a.jpg", img_bytes(), "image/jpeg")]).json()["images"][0]
    r = client.get(img["url"])
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
    assert r.headers["cache-control"] == "public, max-age=300" and r.content[:2] == b"\xff\xd8"
    seed = db.scalar(select(ProductImage).where(ProductImage.storage_key.is_(None)))
    r = client.get(f"/api/images/{seed.id}", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"] == seed.url
    r = client.get("/api/images/99999")
    assert r.status_code == 404 and r.json()["error"]["code"] == "IMAGE_NOT_FOUND"


def test_get_image_s3_redirects_to_presigned(client, admin_headers, db, monkeypatch):
    p = create(client, admin_headers)
    img = upload(client, admin_headers, p["id"], [("a.jpg", img_bytes(), "image/jpeg")]).json()["images"][0]

    class FakeS3:
        def url(self, key, expires=600):
            return f"https://s3.example.com/{key}?exp={expires}"

    from app.api import media

    monkeypatch.setattr(get_settings(), "storage_backend", "s3")
    monkeypatch.setattr(media, "get_storage", lambda: FakeS3())
    r = client.get(img["url"], follow_redirects=False)
    key = db.get(ProductImage, img["id"]).storage_key
    assert r.status_code == 302 and r.headers["location"] == f"https://s3.example.com/{key}?exp=600"


def test_service_slugify():
    assert product_admin.slugify("  Mesa Ñuñoa — Comedor (6 pers.) ") == "mesa-nunoa-comedor-6-pers"


def test_patch_legacy_fields_still_work(client, admin_headers, db):
    r = client.patch("/admin/products/2", json={"stock": 3, "price": "150.00"}, headers=admin_headers)
    assert r.status_code == 200 and r.json()["stock"] == 3 and r.json()["price"] == "150.00"
    db.expire_all()
    assert db.get(Product, 2).low_stock_notified is True
