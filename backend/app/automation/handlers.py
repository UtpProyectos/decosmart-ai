"""Reacciones a eventos (CODEX_HANDOFF §5.7). Se registran al importar este módulo (lo hace app.main).

Cada handler devuelve True si envió alguna notificación (marca events.notified).
"""

from sqlalchemy.orm import Session

from app.automation import notifier
from app.automation.events import on
from app.models import Customer, Event, Order, Product, Quote, Simulation
from app.schemas.common import fmt_money

QUOTE_STATUS_TEXT = {
    "accepted": "fue aceptada ✅", "rejected": "fue rechazada", "expired": "venció ⌛", "sent": "fue enviada",
}
ORDER_STATUS_TEXT = {
    "confirmed": "fue confirmado ✅", "completed": "fue completado 🎉", "cancelled": "fue cancelado",
}


def _customer_label(c: Customer | None) -> str:
    if c is None:
        return "cliente"
    if c.name:
        return c.name
    if c.telegram_username:
        return f"@{c.telegram_username}"
    return f"cliente #{c.id}"


@on("quote.created")
def on_quote_created(db: Session, event: Event) -> bool:
    from app.services.quotes import format_quote_text

    quote = db.get(Quote, event.entity_id)
    if quote is None:
        return False
    sent = False
    if quote.channel == "telegram" and quote.customer and quote.customer.telegram_chat_id:
        sent |= notifier.send_to_chat(quote.customer.telegram_chat_id, format_quote_text(quote))
    sent |= notifier.send_admin(
        f"🧾 Nueva cotización {quote.code} US$ {fmt_money(quote.total)} "
        f"({_customer_label(quote.customer)}, {quote.channel})"
    )
    return sent


@on("quote.status_changed")
def on_quote_status_changed(db: Session, event: Event) -> bool:
    quote = db.get(Quote, event.entity_id)
    if quote is None or not quote.customer or not quote.customer.telegram_chat_id:
        return False
    to = (event.payload or {}).get("to", quote.status)
    msg = QUOTE_STATUS_TEXT.get(to, f"cambió a {to}")
    return notifier.send_to_chat(quote.customer.telegram_chat_id, f"Tu cotización {quote.code} {msg}.")


@on("order.created")
def on_order_created(db: Session, event: Event) -> bool:
    order = db.get(Order, event.entity_id)
    if order is None:
        return False
    return notifier.send_admin(
        f"🛒 Nuevo pedido demo {order.code} US${fmt_money(order.total)} "
        f"({_customer_label(order.customer)}, {order.channel})"
    )


@on("order.status_changed")
def on_order_status_changed(db: Session, event: Event) -> bool:
    order = db.get(Order, event.entity_id)
    if order is None or not order.customer or not order.customer.telegram_chat_id:
        return False
    to = (event.payload or {}).get("to", order.status)
    msg = ORDER_STATUS_TEXT.get(to, f"cambió a {to}")
    return notifier.send_to_chat(
        order.customer.telegram_chat_id, f"Tu pedido demo {order.code} {msg}. (Pedido de demostración, sin cobro)"
    )


@on("simulation.rated")
def on_simulation_rated(db: Session, event: Event) -> bool:
    payload = event.payload or {}
    score = payload.get("score")
    if score is None and event.entity_id:
        sim = db.get(Simulation, event.entity_id)
        score = sim.rating.score if sim and sim.rating else None
    if score is None or int(score) > 2:
        return False
    sim = db.get(Simulation, event.entity_id) if event.entity_id else None
    product = sim.product.name if sim and sim.product else "producto"
    return notifier.send_admin(f"⭐ Simulación #{event.entity_id} calificada con {score}/5 ({product}). Revisar.")


@on("product.low_stock")
def on_product_low_stock(db: Session, event: Event) -> bool:
    p = db.get(Product, event.entity_id)
    if p is None:
        return False
    return notifier.send_admin(f"⚠️ Stock bajo: {p.name} ({p.sku}) quedan {p.stock}")


@on("budget.warning")
def on_budget_warning(db: Session, event: Event) -> bool:
    pl = event.payload or {}
    return notifier.send_admin(
        f"💸 Presupuesto de IA al {pl.get('pct')}% (umbral {pl.get('threshold')}%): "
        f"US$ {pl.get('spent_usd')} de US$ {pl.get('budget_usd')}"
    )


@on("summary.daily")
def on_summary_daily(db: Session, event: Event) -> bool:
    text = (event.payload or {}).get("text")
    return notifier.send_admin(text) if text else False
