"""Regresiones detectadas en la prueba real con AI_MODE=live."""

import json

from app.ai.provider import ChatResult
from app.bot.handlers import _is_greeting
from app.bot.texts import to_telegram_html


def test_greetings_with_extra_words_use_menu():
    assert _is_greeting("hola buen dia")
    assert _is_greeting("buenas tardes!")
    assert _is_greeting("menu")
    assert not _is_greeting("hola quiero un sofá gris para mi sala grande")
    assert not _is_greeting("quiero un mueble")


def test_markdown_to_telegram_html_escapes_and_formats():
    out = to_telegram_html("**Sofá** <b>x</b> & *nuevo*")
    assert out.startswith("<b>Sofá</b>")
    assert "&lt;b&gt;x&lt;/b&gt;" in out and "&amp;" in out
    assert "<i>nuevo</i>" in out


class ScriptedProvider:
    """Primera llamada pide una herramienta; la segunda verifica el input reenviado."""

    def __init__(self):
        self.calls = 0
        self.second_input = None

    def chat(self, instructions, input_items, tools):
        self.calls += 1
        if self.calls == 1:
            return ChatResult(output_items=[{"type": "function_call", "name": "get_product",
                                             "arguments": {"product_ref": "DS-SOF-001"}, "call_id": "c1"}],
                              text="", usage={})
        self.second_input = input_items
        return ChatResult(output_items=[], text="El Sofá Oslo cuesta US$ 649.00.", usage={})


def test_function_call_arguments_are_resent_as_json_string(db, monkeypatch):
    from app.agent import runner
    from app.services import customers

    provider = ScriptedProvider()
    monkeypatch.setattr(runner, "get_provider", lambda *a, **k: provider)
    customer = customers.get_or_create_by_telegram(db, 555, "ana", "Ana")
    conv = customers.get_or_create_conversation(db, customer)
    reply = runner.run_agent_turn(db, conv, "¿cuánto cuesta el sofá oslo?")
    fc = next(i for i in provider.second_input if i.get("type") == "function_call")
    assert isinstance(fc["arguments"], str)
    assert json.loads(fc["arguments"]) == {"product_ref": "DS-SOF-001"}
    assert "649.00" in reply.text
    assert reply.tool_calls


def test_agent_reply_has_menu_buttons_and_is_saved_once(db, monkeypatch):
    from sqlalchemy import func, select

    from app.agent import runner
    from app.bot import handlers
    from app.models import Message

    monkeypatch.setattr(handlers, "run_agent_turn",
                        lambda db_, conv, text: runner.AgentReply("**Hola** ¿qué buscas?"))
    sent = []

    class Client:
        def send_message(self, chat_id, text, reply_markup=None, parse_mode=None):
            sent.append((text, reply_markup, parse_mode))
            return {"message_id": 1}

        def __getattr__(self, name):
            return lambda *a, **k: {}

    update = {"update_id": 424242, "message": {"message_id": 9, "text": "necesito algo para mi cuarto",
              "chat": {"id": 777, "type": "private"}, "from": {"id": 777, "first_name": "Leo"}}}
    handlers.handle_update(db, update, Client())
    text, markup, mode = sent[-1]
    assert mode == "HTML" and text.startswith("<b>Hola</b>")
    assert markup and markup.get("inline_keyboard")
    assert db.scalar(select(func.count(Message.id)).where(Message.role == "assistant")) == 1


def test_cache_key_depends_on_ai_mode(monkeypatch):
    from app.core.config import get_settings
    from app.models import Simulation
    from app.simulation.service import _cache_key

    sim = Simulation(input_hash="abc", product_id=1, room_width_cm=300, room_height_cm=250)
    settings = get_settings()
    monkeypatch.setattr(settings, "ai_mode", "mock")
    k_mock = _cache_key(sim, 0, [])
    monkeypatch.setattr(settings, "ai_mode", "live")
    assert _cache_key(sim, 0, []) != k_mock


def test_mock_label_is_ascii():
    from app.ai.mock_provider import _ascii

    assert _ascii("SIMULACION DEMO - Sofá Oslo – niño") == "SIMULACION DEMO - Sofa Oslo  nino"
