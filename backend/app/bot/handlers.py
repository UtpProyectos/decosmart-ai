"""Telegram update router and persistent conversation state machine."""

import time
from collections import OrderedDict, defaultdict, deque
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.runner import run_agent_turn
from app.bot import keyboards, texts
from app.core.config import get_settings
from app.core.timeutil import now_utc
from app.models import Customer, Message, Simulation
from app.services import catalog, customers, orders, quotes
from app.services.errors import log_error
from app.simulation import service as simulations

BACKEND_ROOT = Path(__file__).resolve().parents[2]
_processed_updates: OrderedDict[int, None] = OrderedDict()
_chat_hits: dict[int, deque[float]] = defaultdict(deque)
_rate_warned: set[int] = set()


def _remember(update_id: int) -> None:
    _processed_updates[update_id] = None
    _processed_updates.move_to_end(update_id)
    while len(_processed_updates) > 1000:
        _processed_updates.popitem(last=False)


def _allowed(chat_id: int) -> bool:
    now = time.monotonic()
    hits = _chat_hits[chat_id]
    while hits and now - hits[0] >= 60:
        hits.popleft()
    if len(hits) >= 20:
        return False
    hits.append(now)
    _rate_warned.discard(chat_id)
    return True


def _save(db: Session, conv, role: str, content: str, message_id: int | None = None) -> None:
    db.add(Message(conversation_id=conv.id, role=role, content=content,
                   telegram_message_id=message_id))
    customers.touch_conversation(db, conv, commit=False)
    db.commit()


def _send(db: Session, client, conv, chat_id: int, text: str, reply_markup=None, parse_mode=None):
    result = client.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
    message_id = result.get("message_id") if isinstance(result, dict) else None
    _save(db, conv, "assistant", text, message_id)
    return result


def _send_photo(db: Session, client, conv, chat_id: int, data: bytes, caption: str, reply_markup=None):
    result = client.send_photo(chat_id, data, caption, reply_markup)
    message_id = result.get("message_id") if isinstance(result, dict) else None
    _save(db, conv, "assistant", caption, message_id)
    return result


def _context(conv, **changes) -> None:
    value = dict(conv.context or {})
    value.update(changes)
    conv.context = value


def _selected(db: Session, conv):
    return catalog.get_product(db, (conv.context or {}).get("selected_product"))


def _show_catalog(db: Session, client, conv, chat_id: int) -> None:
    _send(db, client, conv, chat_id, "Elige una categoría:", keyboards.categories(catalog.list_categories(db)))


def _show_product(db: Session, client, conv, chat_id: int, product) -> None:
    _context(conv, selected_product=product.sku)
    db.commit()
    path = (BACKEND_ROOT / (product.reference_image_key or "")).resolve()
    if product.reference_image_key and path.is_relative_to(BACKEND_ROOT) and path.is_file():
        _send_photo(db, client, conv, chat_id, path.read_bytes(), texts.product_card(product),
                    keyboards.product_actions(product.id))
    else:
        _send(db, client, conv, chat_id, texts.product_card(product), keyboards.product_actions(product.id))


def _begin_simulation(db: Session, client, conv, customer, chat_id: int, product) -> None:
    if product is None:
        _send(db, client, conv, chat_id, "Primero elige un producto del catálogo.", keyboards.main_menu())
        return
    sim = simulations.prepare(db, customer, product)
    if sim.status == "blocked_quota":
        message = texts.BUDGET_EXHAUSTED if sim.error_message == "budget" else texts.QUOTA_EXHAUSTED.format(
            max=get_settings().max_simulations_per_customer)
        _send(db, client, conv, chat_id, message)
        return
    _context(conv, selected_product=product.sku, simulation_id=sim.id)
    if customer.photo_consent_at is None:
        conv.state = "sim_consent"
        db.commit()
        _send(db, client, conv, chat_id,
              texts.PHOTO_CONSENT.format(days=get_settings().photo_retention_days), keyboards.consent())
    else:
        conv.state = "sim_photo"
        db.commit()
        _send(db, client, conv, chat_id, texts.ASK_PHOTO.format(product=product.name))


def _cancel(db: Session, client, conv, chat_id: int) -> None:
    sim_id = (conv.context or {}).get("simulation_id")
    sim = db.get(Simulation, sim_id) if sim_id else None
    if sim and sim.status not in {"completed", "failed"}:
        sim.status = "cancelled"
    conv.state, conv.context = "idle", {}
    db.commit()
    _send(db, client, conv, chat_id, "Flujo cancelado. ¿Qué deseas hacer?", keyboards.main_menu())


def _handle_photo(db: Session, client, conv, chat_id: int, message: dict) -> None:
    if conv.state != "sim_photo":
        _send(db, client, conv, chat_id, "Selecciona primero un producto y toca Simular.")
        return
    if message.get("photo"):
        file_id = message["photo"][-1]["file_id"]
    else:
        document = message.get("document") or {}
        if not str(document.get("mime_type", "")).startswith("image/"):
            _send(db, client, conv, chat_id, "El documento debe ser una imagen.")
            return
        file_id = document.get("file_id")
    info = client.get_file(file_id)
    raw = client.download_file(info["file_path"])
    simulations.attach_photo(db, int(conv.context["simulation_id"]), raw)
    conv.state = "sim_dimensions"
    db.commit()
    _send(db, client, conv, chat_id, texts.ASK_DIMENSIONS, parse_mode="Markdown")


def _dimensions(db: Session, client, conv, customer, chat_id: int, text: str) -> None:
    try:
        sim = simulations.set_dimensions(db, int(conv.context["simulation_id"]), text)
    except ValueError as exc:
        _send(db, client, conv, chat_id, str(exc))
        return
    conv.state = "sim_confirm"
    db.commit()
    warning = simulations.width_warning(sim)
    dims = f"{sim.product.width_cm} × {sim.product.height_cm} × {sim.product.depth_cm} cm"
    room = f"{sim.room_width_cm} × {sim.room_height_cm}" + (
        f" × {sim.room_depth_cm} cm" if sim.room_depth_cm else " cm"
    )
    left = max(0, get_settings().max_simulations_per_customer - (customer.simulations_used or 0))
    message = texts.CONFIRM_SIMULATION.format(product=sim.product.name, dims=dims, room_dims=room, left=left)
    if warning:
        message = warning + "\n\n" + message
    _send(db, client, conv, chat_id, message, keyboards.confirm_simulation(sim.id))


def _callback(db: Session, client, conv, customer, chat_id: int, callback: dict) -> None:
    data = callback.get("data", "")
    client.answer_callback_query(callback["id"])
    if data == "catalog":
        _show_catalog(db, client, conv, chat_id)
    elif data.startswith("category:"):
        products = catalog.search_products(db, category=data.split(":", 1)[1])
        _send(db, client, conv, chat_id, "Selecciona un producto:", keyboards.products(products))
    elif data.startswith("product:"):
        product = catalog.get_product(db, data.split(":", 1)[1])
        if product:
            _show_product(db, client, conv, chat_id, product)
    elif data.startswith("simulate:"):
        ref = data.split(":", 1)[1]
        _begin_simulation(db, client, conv, customer, chat_id,
                          _selected(db, conv) if ref == "selected" else catalog.get_product(db, ref))
    elif data == "consent:yes" and conv.state == "sim_consent":
        customer.photo_consent_at = now_utc()
        conv.state = "sim_photo"
        db.commit()
        product = _selected(db, conv)
        _send(db, client, conv, chat_id, texts.ASK_PHOTO.format(product=product.name))
    elif data == "sim:cancel":
        _cancel(db, client, conv, chat_id)
    elif data.startswith("sim:go:") and conv.state == "sim_confirm":
        sim_id = int(data.rsplit(":", 1)[1])
        _send(db, client, conv, chat_id, texts.PROCESSING)
        result = simulations.run(db, sim_id)
        conv.state = "idle"
        db.commit()
        if result.status == "completed":
            caption = texts.RESULT_CAPTION.format(product=result.simulation.product.name)
            _send_photo(db, client, conv, chat_id, result.data, caption, keyboards.stars(sim_id))
        elif result.reason == "budget":
            _send(db, client, conv, chat_id, texts.BUDGET_EXHAUSTED)
        elif result.status == "blocked_quota":
            _send(db, client, conv, chat_id,
                  texts.QUOTA_EXHAUSTED.format(max=get_settings().max_simulations_per_customer))
        else:
            _send(db, client, conv, chat_id, texts.GENERIC_ERROR)
    elif data.startswith("sim:again:"):
        original = db.get(Simulation, int(data.rsplit(":", 1)[1]))
        if original and original.customer_id == customer.id:
            sim = Simulation(customer_id=customer.id, product_id=original.product_id,
                             status="awaiting_confirmation", input_key=original.input_key,
                             input_hash=original.input_hash, input_bytes=original.input_bytes,
                             room_width_cm=original.room_width_cm, room_height_cm=original.room_height_cm,
                             room_depth_cm=original.room_depth_cm, placement_hint=original.placement_hint)
            db.add(sim)
            db.flush()
            _context(conv, simulation_id=sim.id, variant=(conv.context or {}).get("variant", 0) + 1)
            conv.state = "sim_confirm"
            db.commit()
            _send(db, client, conv, chat_id, "¿Confirmas generar otra versión?",
                  keyboards.confirm_simulation(sim.id))
    elif data.startswith("rate:"):
        _, sim_id, score = data.split(":")
        simulations.rate(db, int(sim_id), int(score), customer)
        sim = db.get(Simulation, int(sim_id))
        _send(db, client, conv, chat_id, "¡Gracias por tu calificación! ¿Deseas cotizar este producto?",
              keyboards.product_actions(sim.product_id))
    elif data.startswith("quote:"):
        ref = data.split(":", 1)[1]
        product = _selected(db, conv) if ref == "selected" else catalog.get_product(db, ref)
        if not product:
            _send(db, client, conv, chat_id, "Primero elige un producto del catálogo.")
        else:
            quote = quotes.create_quote(db, customer, [{"product_id": product.id, "quantity": 1}], channel="telegram")
            _send(db, client, conv, chat_id, f"Cotización {quote.code} preparada.",
                  keyboards.order_from_quote(quote.code))
    elif data.startswith("order:"):
        _context(conv, quote_code=data.split(":", 1)[1])
        conv.state = "order_contact"
        db.commit()
        _send(db, client, conv, chat_id, "Envíame tu teléfono y dirección de entrega, separados por `;`.",
              parse_mode="Markdown")
    elif data == "recommend":
        _send(db, client, conv, chat_id, "Cuéntame tu presupuesto y el ambiente que deseas amoblar.")


def _text(db: Session, client, conv, customer, chat_id: int, message: dict) -> None:
    text = (message.get("text") or "")[:1000].strip()
    lower = text.lower()
    if lower in {"/cancelar", "cancelar"}:
        _cancel(db, client, conv, chat_id)
        return
    if conv.state == "sim_photo":
        _send(db, client, conv, chat_id, "Necesito una foto del ambiente. Usa /cancelar para salir.")
        return
    if conv.state == "sim_dimensions":
        _dimensions(db, client, conv, customer, chat_id, text)
        return
    if conv.state == "order_contact":
        phone, sep, address = text.partition(";")
        if not sep:
            _send(db, client, conv, chat_id, "Separa teléfono y dirección con `;`.", parse_mode="Markdown")
            return
        order = orders.create_order(db, customer, quote_code=conv.context["quote_code"], channel="telegram",
                                    contact_phone=phone.strip(), delivery_address=address.strip(),
                                    require_same_customer=True)
        conv.state, conv.context = "idle", {}
        db.commit()
        _send(db, client, conv, chat_id, f"Pedido demo {order.code} registrado. No se realizó ningún cobro.")
        return
    if lower.startswith("/start") or lower in {"hola", "menu", "menú", "ayuda"}:
        parts = text.split(maxsplit=1)
        if len(parts) == 2 and parts[1].startswith("sim_"):
            product = catalog.get_product(db, parts[1][4:])
            if product:
                _context(conv, selected_product=product.sku)
                db.commit()
                _begin_simulation(db, client, conv, customer, chat_id, product)
                return
        _send(db, client, conv, chat_id, texts.WELCOME, keyboards.main_menu())
    elif lower == "/catalogo":
        _show_catalog(db, client, conv, chat_id)
    elif lower == "/simular":
        _begin_simulation(db, client, conv, customer, chat_id, _selected(db, conv))
    elif lower == "/cotizar":
        product = _selected(db, conv)
        if product:
            quote = quotes.create_quote(db, customer, [{"product_id": product.id, "quantity": 1}], channel="telegram")
            _send(
                db, client, conv, chat_id, f"Cotización {quote.code} preparada.",
                keyboards.order_from_quote(quote.code),
            )
        else:
            _send(db, client, conv, chat_id, "Primero elige un producto del catálogo.")
    elif lower.startswith("/estado "):
        code = text.split(maxsplit=1)[1].upper()
        item = quotes.get_quote(db, code) if code.startswith("COT-") else orders.get_order(db, code)
        if item and item.customer_id == customer.id:
            _send(db, client, conv, chat_id, f"{item.code}: estado {item.status}.")
        else:
            _send(db, client, conv, chat_id, "No encontré una solicitud con ese código.")
    else:
        reply = run_agent_turn(db, conv, text)
        _send(db, client, conv, chat_id, reply.text, reply.buttons)
        for action in reply.actions:
            if action["type"] == "start_simulation":
                _begin_simulation(db, client, conv, customer, chat_id,
                                  catalog.get_product(db, action["product_id"]))


def handle_update(db: Session, update: dict, client) -> None:
    """Handle one update completely; all failures are logged and swallowed."""
    update_id = int(update.get("update_id", -1))
    message = update.get("message")
    callback = update.get("callback_query")
    source = message or (callback or {}).get("message") or {}
    chat = source.get("chat") or {}
    chat_id = chat.get("id")
    user = (message or callback or {}).get("from") or {}
    customer = conv = None
    try:
        if chat_id is None:
            return
        existing = db.scalar(select(Customer).where(Customer.telegram_chat_id == chat_id))
        if update_id in _processed_updates and existing is not None:
            return
        _remember(update_id)
        if not _allowed(int(chat_id)):
            if int(chat_id) not in _rate_warned:
                client.send_message(chat_id, "Has enviado demasiados mensajes. Intenta nuevamente en un minuto.")
                _rate_warned.add(int(chat_id))
            return
        name = " ".join(x for x in (user.get("first_name"), user.get("last_name")) if x) or None
        customer = customers.get_or_create_by_telegram(db, int(chat_id), user.get("username"), name)
        conv = customers.get_or_create_conversation(db, customer)
        incoming = (message or {}).get("text") or (callback or {}).get("data") or "[imagen]"
        _save(db, conv, "user", incoming[:1000], (message or {}).get("message_id"))
        if callback:
            _callback(db, client, conv, customer, int(chat_id), callback)
        elif message and (message.get("photo") or message.get("document")):
            _handle_photo(db, client, conv, int(chat_id), message)
        elif message:
            _text(db, client, conv, customer, int(chat_id), message)
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        log_error(db, "bot", exc.__class__.__name__, str(exc), {"update_id": update_id},
                  customer_id=customer.id if customer else None)
        try:
            client.send_message(chat_id, texts.GENERIC_ERROR)
            if conv:
                _save(db, conv, "assistant", texts.GENERIC_ERROR)
        except Exception:  # noqa: BLE001
            pass
