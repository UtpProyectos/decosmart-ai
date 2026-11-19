from io import BytesIO

import pytest
import respx
from httpx import Response
from PIL import Image
from sqlalchemy import select

from app.bot.client import TelegramClient, TelegramError
from app.bot.handlers import handle_update
from app.models import ErrorLog, Simulation, SimulationRating


class FakeTelegram:
    def __init__(self):
        self.calls = []

    def send_message(self, chat_id, text, reply_markup=None, parse_mode=None):
        self.calls.append(("message", chat_id, text, reply_markup))
        return {"message_id": len(self.calls)}

    def send_photo(self, chat_id, photo_bytes, caption="", reply_markup=None):
        self.calls.append(("photo", chat_id, caption, reply_markup, photo_bytes))
        return {"message_id": len(self.calls)}

    def answer_callback_query(self, callback_query_id, text=None):
        self.calls.append(("answer", callback_query_id, text))

    def get_file(self, file_id):
        return {"file_path": "photos/room.jpg"}

    def download_file(self, file_path):
        out = BytesIO()
        Image.new("RGB", (640, 480), "white").save(out, "JPEG")
        return out.getvalue()


def message(update_id, chat_id, text=None, **extra):
    body = {"message_id": update_id, "chat": {"id": chat_id},
            "from": {"id": chat_id, "first_name": "Ana"}}
    if text is not None:
        body["text"] = text
    body.update(extra)
    return {"update_id": update_id, "message": body}


def callback(update_id, chat_id, data):
    return {"update_id": update_id, "callback_query": {"id": f"cb-{update_id}", "data": data,
            "from": {"id": chat_id, "first_name": "Ana"},
            "message": {"message_id": update_id, "chat": {"id": chat_id}}}}


def test_handler_start_welcome(db):
    fake = FakeTelegram()
    handle_update(db, message(9001, 8301, "/start"), fake)
    assert any("Soy Deco" in c[2] and c[3] for c in fake.calls if c[0] == "message")


def test_handler_catalog_flow_and_product_card(db):
    fake = FakeTelegram()
    handle_update(db, message(9002, 8302, "/start"), fake)
    handle_update(db, callback(9003, 8302, "catalog"), fake)
    handle_update(db, callback(9004, 8302, "category:sofas"), fake)
    handle_update(db, callback(9005, 8302, "product:1"), fake)
    assert any(c[0] == "photo" and "649.00" in c[2] for c in fake.calls)


def test_handler_deep_link_starts_simulation(db):
    fake = FakeTelegram()
    handle_update(db, message(9006, 8303, "/start sim_DS-SOF-001"), fake)
    sim = db.scalar(select(Simulation).where(Simulation.customer_id == 1))
    assert sim and sim.status == "awaiting_photo"
    assert any("Para simular necesito" in c[2] for c in fake.calls if c[0] == "message")


def test_full_simulation_flow_and_rating(db):
    fake = FakeTelegram()
    chat = 8304
    handle_update(db, message(9010, chat, "/start sim_DS-SOF-001"), fake)
    handle_update(db, callback(9011, chat, "consent:yes"), fake)
    handle_update(db, message(9012, chat, photo=[{"file_id": "small"}, {"file_id": "large"}]), fake)
    handle_update(db, message(9013, chat, "300 x 250"), fake)
    sim = db.scalar(select(Simulation).order_by(Simulation.id.desc()))
    assert not any(c[0] == "photo" and "Así podría" in c[2] for c in fake.calls)
    handle_update(db, callback(9014, chat, f"sim:go:{sim.id}"), fake)
    assert any(c[0] == "photo" and "Así podría" in c[2] and c[3]["inline_keyboard"] for c in fake.calls)
    handle_update(db, callback(9015, chat, f"rate:{sim.id}:4"), fake)
    assert db.scalar(select(SimulationRating).where(SimulationRating.simulation_id == sim.id)).score == 4


def test_handler_quote_callback_sends_short_confirmation(db, sent_messages):
    fake = FakeTelegram()
    chat = 8305
    handle_update(db, message(9020, chat, "/start"), fake)
    handle_update(db, callback(9021, chat, "product:1"), fake)
    handle_update(db, callback(9022, chat, "quote:1"), fake)
    assert any("Cotización COT-" in c[2] and "preparada" in c[2] for c in fake.calls if c[0] == "message")
    assert sum("Cotización COT-" in text for target, text in sent_messages if target == str(chat)) == 1


def test_handler_cancel(db):
    fake = FakeTelegram()
    handle_update(db, message(9030, 8306, "/start sim_DS-SOF-001"), fake)
    handle_update(db, message(9031, 8306, "/cancelar"), fake)
    assert "Flujo cancelado" in fake.calls[-1][2]


def test_duplicate_update_ignored(db):
    fake = FakeTelegram()
    update = message(9040, 8307, "/start")
    handle_update(db, update, fake)
    count = len(fake.calls)
    handle_update(db, update, fake)
    assert len(fake.calls) == count


def test_exception_is_logged_and_apology_sent(db, monkeypatch):
    from app.bot import handlers

    fake = FakeTelegram()
    monkeypatch.setattr(handlers.catalog, "list_categories", lambda db: (_ for _ in ()).throw(RuntimeError("boom")))
    handle_update(db, message(9050, 8308, "/catalogo"), fake)
    assert db.scalar(select(ErrorLog).where(ErrorLog.source == "bot"))
    assert "Lo siento" in fake.calls[-1][2]


def test_webhook_secrets(client, monkeypatch):
    from app.api import telegram

    seen = []
    monkeypatch.setattr(telegram, "_process", lambda update: seen.append(update))
    assert client.post("/telegram/webhook/wrong", json={"update_id": 1},
                       headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"}).status_code == 403
    secret = "change-me-webhook-secret"
    response = client.post(f"/telegram/webhook/{secret}", json={"update_id": 2},
                           headers={"X-Telegram-Bot-Api-Secret-Token": secret})
    assert response.status_code == 200 and response.json() == {"ok": True} and seen == [{"update_id": 2}]


@respx.mock
def test_telegram_client_send_message():
    route = respx.post("https://api.telegram.org/botTOKEN/sendMessage").mock(
        return_value=Response(200, json={"ok": True, "result": {"message_id": 7}}))
    assert TelegramClient("TOKEN").send_message(1, "hola")["message_id"] == 7
    assert route.called


@respx.mock
def test_telegram_client_file_and_updates():
    respx.post("https://api.telegram.org/botTOKEN/getFile").mock(
        return_value=Response(200, json={"ok": True, "result": {"file_path": "x.jpg"}}))
    respx.get("https://api.telegram.org/file/botTOKEN/x.jpg").mock(return_value=Response(200, content=b"img"))
    respx.post("https://api.telegram.org/botTOKEN/getUpdates").mock(
        return_value=Response(200, json={"ok": True, "result": [{"update_id": 1}]}))
    tg = TelegramClient("TOKEN")
    assert tg.download_file(tg.get_file("f")["file_path"]) == b"img"
    assert tg.get_updates(offset=1) == [{"update_id": 1}]


@respx.mock
def test_telegram_client_raises_on_ok_false():
    respx.post("https://api.telegram.org/botTOKEN/deleteWebhook").mock(
        return_value=Response(200, json={"ok": False, "description": "bad"}))
    with pytest.raises(TelegramError, match="bad"):
        TelegramClient("TOKEN").delete_webhook()


def test_group_messages_are_ignored(db):
    from sqlalchemy import func, select

    from app.bot.handlers import handle_update
    from app.models import Customer

    class Spy:
        def __init__(self):
            self.calls = []

        def __getattr__(self, name):
            return lambda *a, **k: self.calls.append((name, a, k))

    spy = Spy()
    update = {"update_id": 987654, "message": {"message_id": 1, "text": "@bot hola",
              "chat": {"id": -1001234567890, "type": "supergroup", "title": "Equipo"},
              "from": {"id": 1, "first_name": "Ana"}}}
    handle_update(db, update, spy)
    assert spy.calls == []
    assert db.scalar(select(func.count(Customer.id)).where(Customer.telegram_chat_id < 0)) == 0
