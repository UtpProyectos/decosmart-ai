from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.agent.guard import validate
from app.agent.prompts import build_simulation_prompt
from app.agent.runner import run_agent_turn
from app.agent.tools import ToolContext, dispatch
from app.models import ApiUsage, ErrorLog, Product
from app.services import customers
from app.simulation.service import parse_dimensions


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("300 x 250", (300, 250, None, None)),
        ("300x250x400", (300, 250, 400, None)),
        ("3 x 2.5", (300, 250, None, None)),
        ("3,0 × 2,5", (300, 250, None, None)),
        ("300*250; contra la ventana!", (300, 250, None, "contra la ventana")),
    ],
)
def test_parse_dimensions_variants(text, expected):
    assert parse_dimensions(text) == expected


@pytest.mark.parametrize("text", ["tres por dos", "20 x 30"])
def test_parse_dimensions_rejects_bad(text):
    with pytest.raises(ValueError):
        parse_dimensions(text)


def test_simulation_prompt_real_dimensions_and_ratios(db):
    product = db.scalar(select(Product).where(Product.sku == "DS-SOF-001"))
    sim = SimpleNamespace(room_width_cm=300, room_height_cm=250, room_depth_cm=400,
                          placement_hint="junto a la ventana")
    prompt = build_simulation_prompt(product, sim, "beige")
    assert "210 cm de ancho × 85 cm de alto × 90 cm" in prompt
    assert "70% del ancho visible" in prompt and "34% del alto" in prompt
    assert "profundidad: 400 cm" in prompt and "junto a la ventana" in prompt


def test_tools_get_product_returns_database_price(db):
    customer = customers.get_or_create_by_telegram(db, 8101)
    conv = customers.get_or_create_conversation(db, customer)
    result = dispatch(db, "get_product", {"product_ref": "DS-SOF-001"}, ToolContext(customer, conv))
    assert result["product"]["price_usd"] == "649.00"


def test_tools_select_product_updates_context(db):
    customer = customers.get_or_create_by_telegram(db, 8102)
    conv = customers.get_or_create_conversation(db, customer)
    dispatch(db, "select_product", {"product_ref": "DS-SOF-001"}, ToolContext(customer, conv))
    db.refresh(conv)
    assert conv.context["selected_product"] == "DS-SOF-001"


def test_guard_replaces_invented_price_and_logs(db):
    ok, text = validate("Cuesta US$ 999.00", [{"ok": True, "product": {
        "name": "Sofá Oslo", "price_usd": "649.00", "dims_cm": "210x85x90", "stock": 8,
    }}], db, None)
    assert not ok and "649.00" in text and "999" not in text
    assert db.scalar(select(ErrorLog).where(ErrorLog.error_type == "unverified_number"))


def test_guard_accepts_verified_price():
    assert validate("Cuesta US$ 649.00", [{"price_usd": "649.00"}]) == (True, "Cuesta US$ 649.00")


def test_mock_provider_end_to_end_price(db):
    customer = customers.get_or_create_by_telegram(db, 8103)
    conv = customers.get_or_create_conversation(db, customer)
    reply = run_agent_turn(db, conv, "¿cuánto cuesta el sofá oslo?")
    assert "649.00" in reply.text
    assert db.scalar(select(ApiUsage).where(ApiUsage.operation == "chat"))


def test_runner_start_simulation_action(db):
    customer = customers.get_or_create_by_telegram(db, 8104)
    conv = customers.get_or_create_conversation(db, customer)
    reply = run_agent_turn(db, conv, "Quiero simular el sofá Oslo")
    assert reply.actions[0]["type"] == "start_simulation"
