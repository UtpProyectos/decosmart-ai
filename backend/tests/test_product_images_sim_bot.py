"""Imágenes de producto en simulación y bot de Telegram (doc 04 v0.2)."""

import json
from decimal import Decimal
from io import BytesIO

import respx
from httpx import Response
from PIL import Image
from sqlalchemy import select

from app.ai.provider import ImageResult
from app.bot.client import TelegramClient
from app.bot.handlers import handle_update
from app.core import pricing
from app.core.config import get_settings
from app.models import Product, ProductImage
from app.services import customers, product_admin, product_images
from app.simulation import service
from tests.test_ai_bot_telegram import FakeTelegram, callback, message


def img(color, size=(640, 480)) -> bytes:
    out = BytesIO()
    Image.new("RGB", size, color).save(out, "JPEG")
    return out.getvalue()


def color_of(data: bytes) -> tuple:
    with Image.open(BytesIO(data)) as im:
        return im.convert("RGB").getpixel((im.width // 2, im.height // 2))


def sofa(db) -> Product:
    return product_admin.get_product_admin(db, db.scalar(select(Product.id).where(Product.sku == "DS-SOF-001")))


def add(db, product, colors, is_reference=False) -> list[ProductImage]:
    files = [(f"{c}.jpg", img(c), "image/jpeg") for c in colors]
    return product_admin.add_images(db, product, files, is_reference=is_reference)


class SpyProvider:
    def __init__(self):
        self.references: list[bytes] | None = None
        self.calls = 0

    def edit_image(self, room, references, prompt, size, quality):
        self.calls += 1
        self.references = list(references)
        return ImageResult(room, {})

    def moderate(self, text):
        return True


def ready(db, customer, product):
    sim = service.prepare(db, customer, product)
    service.attach_photo(db, sim.id, img("white"))
    service.set_dimensions(db, sim.id, "300 x 250")
    return sim


# ---------- Simulación ----------
def test_simulation_uses_reference_images_in_order_capped(db, monkeypatch):
    spy = SpyProvider()
    monkeypatch.setattr(service, "get_provider", lambda *a, **k: spy)
    p = sofa(db)
    # La imagen seed deja de ser referencia; se suben 3 referencias y una que no lo es.
    seed = next(i for i in p.images if i.storage_key is None)
    product_admin.update_image(db, p, seed.id, {"is_reference": False})
    refs = add(db, p, ["red", "green", "blue"], is_reference=True)
    add(db, p, ["yellow"])
    product_admin.reorder_images(db, p, [refs[2].id, seed.id, refs[0].id, refs[1].id,
                                         *[i.id for i in p.images if i.id not in {seed.id, *[r.id for r in refs]}]])
    customer = customers.get_or_create_by_telegram(db, 8701)
    result = service.run(db, ready(db, customer, p).id)
    assert result.status == "completed"
    assert len(spy.references) == get_settings().simulation_max_reference_images == 2
    blue, red = (color_of(b) for b in spy.references)
    assert blue[2] > 200 and blue[0] < 50 and red[0] > 200 and red[2] < 50


def test_simulation_falls_back_to_primary_then_reference_key(db):
    p = sofa(db)
    seed = next(i for i in p.images if i.storage_key is None)
    product_admin.update_image(db, p, seed.id, {"is_reference": False})
    refs = product_images.reference_images(db, p)
    assert refs == [product_images.load_image_bytes(db, seed)]
    product_admin.delete_image(db, p, seed.id)
    refs = product_images.reference_images(db, p)
    assert len(refs) == 1 and refs[0][:2] == b"\xff\xd8"  # reference_image_key (seed/images)


def test_simulation_reference_cap_setting(db, monkeypatch):
    monkeypatch.setattr(get_settings(), "simulation_max_reference_images", 1)
    p = sofa(db)
    add(db, p, ["red", "green"], is_reference=True)
    assert len(product_images.reference_images(db, p)) == 1


def test_cache_key_changes_with_references(db):
    customer = customers.get_or_create_by_telegram(db, 8702)
    p = sofa(db)
    sim = ready(db, customer, p)
    one = service._cache_key(sim, 0, [img("red")])
    two = service._cache_key(sim, 0, [img("red"), img("blue")])
    other = service._cache_key(sim, 0, [img("green")])
    assert len({one, two, other, service._cache_key(sim, 0, [])}) == 4
    assert one == service._cache_key(sim, 0, [img("red")])


def test_pricing_surcharge_per_extra_reference():
    base = pricing.estimate_image_edit("gpt-image-1-mini", "low", "1024x1024")
    assert base == pricing.estimate_image_edit("gpt-image-1-mini", "low", "1024x1024", input_images=2)
    three = pricing.estimate_image_edit("gpt-image-1-mini", "low", "1024x1024", input_images=3)
    assert three - base == Decimal(str(pricing.IMAGE_INPUT_SURCHARGE_USD))


def test_mock_provider_pastes_first_reference(db):
    from app.ai.mock_provider import MockProvider

    out = MockProvider().edit_image(img("white"), [img("red", (400, 400)), img("blue", (400, 400))],
                                    "- Producto: Sofá", "1024x1024", "low")
    with Image.open(BytesIO(out.data)) as im:
        px = im.convert("RGB").getpixel((640 - 12 - 20, 480 - 12 - 20))
    assert px[0] > 200 and px[2] < 60


def test_openai_provider_sends_room_and_all_references():
    from types import SimpleNamespace

    from app.ai.openai_provider import OpenAIProvider

    seen = {}

    class Images:
        def edit(self, **kwargs):
            seen.update(kwargs)
            import base64

            return SimpleNamespace(data=[SimpleNamespace(b64_json=base64.b64encode(b"x").decode())], usage=None)

    provider = OpenAIProvider(client=SimpleNamespace(images=Images()))
    provider.edit_image(b"room", [b"r1", b"r2"], "prompt", "1024x1024", "low")
    assert [name for name, _, _ in seen["image"]] == ["room.jpg", "product-1.jpg", "product-2.jpg"]
    assert [data for _, data, _ in seen["image"]] == [b"room", b"r1", b"r2"]


# ---------- Bot ----------
class AlbumTelegram(FakeTelegram):
    def send_media_group(self, chat_id, photos):
        self.calls.append(("album", chat_id, [p for p, _ in photos]))
        return [{"message_id": len(self.calls)}]


def test_bot_category_listing_sends_photo_per_product_with_buttons(db):
    fake = AlbumTelegram()
    handle_update(db, message(9701, 8710, "/start"), fake)
    handle_update(db, callback(9702, 8710, "category:sillas"), fake)
    photos = [c for c in fake.calls if c[0] == "photo"]
    assert len(photos) == 1
    caption, markup = photos[0][2], photos[0][3]
    assert caption.startswith("Silla Arco Comedor (set x2)\nUS$ 119.00 · 47×82×55 cm · ")
    buttons = markup["inline_keyboard"][0]
    pid = db.scalar(select(Product.id).where(Product.sku == "DS-SIL-001"))
    assert [b["text"] for b in buttons] == ["Ver detalle", "Simular", "Cotizar"]
    assert [b["callback_data"] for b in buttons] == [f"product:{pid}", f"simulate:{pid}", f"quote:{pid}"]


def test_bot_category_listing_limits_batch_and_text_fallback(db, monkeypatch):
    from app.bot import handlers

    fake = AlbumTelegram()
    products = [sofa(db)] * 8
    monkeypatch.setattr(handlers.catalog, "search_products", lambda db, **k: products)
    monkeypatch.setattr(handlers, "_primary_bytes", lambda db, p: None)
    handle_update(db, callback(9705, 8711, "category:sofas"), fake)
    messages = [c for c in fake.calls if c[0] == "message"]
    assert len(messages) == 7  # 6 tarjetas de texto (sin imagen) + "Más productos"
    assert messages[0][3]["inline_keyboard"][0][0]["text"] == "Ver detalle"
    assert "Más productos" in messages[-1][2]


def test_bot_detail_with_three_images_sends_album_then_card(db):
    p = sofa(db)
    add(db, p, ["red", "green"])  # + seed = 3 imágenes
    fake = AlbumTelegram()
    handle_update(db, callback(9710, 8712, f"product:{p.id}"), fake)
    kinds = [c[0] for c in fake.calls if c[0] != "answer"]
    assert kinds == ["album", "message"]
    album = next(c for c in fake.calls if c[0] == "album")
    assert len(album[2]) == 3
    card = next(c for c in fake.calls if c[0] == "message")
    assert "649.00" in card[2] and card[3]["inline_keyboard"]


def test_bot_detail_single_image_sends_photo_card(db):
    fake = AlbumTelegram()
    handle_update(db, callback(9715, 8713, "product:1"), fake)
    assert [c[0] for c in fake.calls if c[0] != "answer"] == ["photo"]


def test_bot_agent_search_sends_product_cards(db):
    fake = AlbumTelegram()
    handle_update(db, message(9720, 8714, "busco algo de madera para mi sala"), fake)
    photos = [c for c in fake.calls if c[0] == "photo"]
    assert 1 <= len(photos) <= 3
    assert all(c[3]["inline_keyboard"][0][0]["text"] == "Ver detalle" for c in photos)
    first_photo = next(i for i, c in enumerate(fake.calls) if c[0] == "photo")
    assert any(c[0] == "message" for c in fake.calls[:first_photo])  # texto del agente antes de las fotos


@respx.mock
def test_telegram_client_send_media_group_multipart():
    route = respx.post("https://api.telegram.org/botTOKEN/sendMediaGroup").mock(
        return_value=Response(200, json={"ok": True, "result": [{"message_id": 1}, {"message_id": 2}]}))
    result = TelegramClient("TOKEN").send_media_group(5, [(b"one", "Sofá"), (b"two", None)])
    assert len(result) == 2 and route.called
    request = route.calls[0].request
    assert request.headers["content-type"].startswith("multipart/form-data")
    body = request.content.decode("utf-8", errors="replace")
    assert 'name="photo0"' in body and 'name="photo1"' in body and "one" in body and "two" in body
    media_part = body.split('name="media"', 1)[1].split("\r\n\r\n", 1)[1].split("\r\n--", 1)[0]
    media = json.loads(media_part)
    assert media == [{"type": "photo", "media": "attach://photo0", "caption": "Sofá"},
                     {"type": "photo", "media": "attach://photo1"}]
