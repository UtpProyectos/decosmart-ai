"""Pedidos demo (sin cobro). Ver CODEX_HANDOFF §5.1 y doc 04."""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.core.timeutil import today_local
from app.models import Customer, Order, OrderItem, Product
from app.schemas.common import fmt_money
from app.services import catalog
from app.services.codes import next_code
from app.services.quotes import check_transition, get_quote_or_404, resolve_items, update_quote_status

DEMO_MESSAGE = "Pedido de demostración registrado. No se realizó ningún cobro."
ORDER_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"confirmed", "cancelled"},
    "confirmed": {"completed", "cancelled"},
}
STATUS_LABELS = {"pending": "Pendiente", "confirmed": "Confirmado", "completed": "Completado",
                 "cancelled": "Cancelado"}


def create_order(
    db: Session,
    customer: Customer | None = None,
    *,
    quote_code: str | None = None,
    items: list[dict] | None = None,
    channel: str = "web",
    contact_name: str | None = None,
    contact_email: str | None = None,
    contact_phone: str | None = None,
    delivery_address: str | None = None,
    require_same_customer: bool = False,
) -> Order:
    """Desde `quote_code` (usa ítems y precios de la cotización; la marca `accepted`) o desde `items`.

    `customer` puede omitirse si viene `quote_code` (se usa el de la cotización).
    `require_same_customer=True` (agente) rechaza cotizaciones de otro cliente (QUOTE_NOT_FOUND).
    Valida stock (no lo descuenta). status 'pending', is_demo=True, emite order.created.
    """
    from app.automation.events import emit

    quote = None
    if quote_code:
        quote = get_quote_or_404(db, quote_code)
        if customer is None:
            customer = quote.customer
        elif require_same_customer and quote.customer_id != customer.id:
            raise AppError("QUOTE_NOT_FOUND", "Cotización no encontrada", 404, {"code": quote_code})
        if quote.status == "sent" and quote.valid_until < today_local():
            update_quote_status(db, quote, "expired")
            raise AppError("INVALID_TRANSITION", "La cotización está vencida", 409,
                           {"from": "expired", "to": "accepted"})
        check_transition({"sent": {"accepted"}}, quote.status, "accepted")
        lines = [(i.product, i.quantity, i.unit_price) for i in quote.items]
        for p, qty, _ in lines:
            if not p.active:
                raise AppError("PRODUCT_NOT_FOUND", "Producto no disponible", 404, {"product_id": p.id})
            if p.stock < qty:
                raise AppError("INSUFFICIENT_STOCK", f"Stock insuficiente para {p.name}", 409,
                               {"product_id": p.id, "sku": p.sku, "available": p.stock, "requested": qty})
    elif items:
        lines = [(p, qty, p.price) for p, qty in resolve_items(db, items)]
    else:
        raise AppError("VALIDATION_ERROR", "Debes indicar quote_code o items", 422)
    if customer is None:
        raise AppError("VALIDATION_ERROR", "Faltan datos del cliente", 422)

    order = Order(
        code=next_code(db, "PED"), customer_id=customer.id, quote_id=quote.id if quote else None, channel=channel,
        status="pending", is_demo=True,
        contact_name=contact_name or customer.name, contact_email=contact_email or customer.email,
        contact_phone=contact_phone or customer.phone, delivery_address=delivery_address,
    )
    total = Decimal("0")
    for p, qty, unit in lines:
        lt = (unit * qty).quantize(Decimal("0.01"))
        order.items.append(OrderItem(product_id=p.id, quantity=qty, unit_price=unit, line_total=lt))
        total += lt
    order.total = total
    db.add(order)
    db.flush()
    if quote is not None:
        update_quote_status(db, quote, "accepted", commit=False)
    emit(db, "order.created", entity_type="order", entity_id=order.id, customer_id=customer.id,
         payload={"code": order.code, "total": fmt_money(total), "channel": channel,
                  "quote_code": quote.code if quote else None})
    db.commit()
    return order


def get_order(db: Session, code: str) -> Order | None:
    return db.scalar(
        select(Order).options(selectinload(Order.items).selectinload(OrderItem.product), selectinload(Order.customer),
                              selectinload(Order.quote))
        .where(Order.code == code.strip().upper())
    )


def get_order_or_404(db: Session, code: str) -> Order:
    o = get_order(db, code)
    if o is None:
        raise AppError("ORDER_NOT_FOUND", "Pedido no encontrado", 404, {"code": code})
    return o


def update_order_status(db: Session, order: Order, new_status: str) -> Order:
    """Transiciones válidas; confirmed descuenta stock (y evalúa stock bajo); cancelar uno confirmado lo repone."""
    from app.automation.events import emit

    old = order.status
    check_transition(ORDER_TRANSITIONS, old, new_status)
    touched: list[Product] = []
    if new_status == "confirmed":
        for it in order.items:
            p = db.get(Product, it.product_id, with_for_update=True)
            if p.stock < it.quantity:
                raise AppError("INSUFFICIENT_STOCK", f"Stock insuficiente para {p.name}", 409,
                               {"product_id": p.id, "sku": p.sku, "available": p.stock, "requested": it.quantity})
        for it in order.items:
            p = db.get(Product, it.product_id)
            p.stock -= it.quantity
            touched.append(p)
    elif new_status == "cancelled" and old == "confirmed":
        for it in order.items:
            p = db.get(Product, it.product_id)
            p.stock += it.quantity
            touched.append(p)
    order.status = new_status
    db.flush()
    emit(db, "order.status_changed", entity_type="order", entity_id=order.id, customer_id=order.customer_id,
         payload={"code": order.code, "from": old, "to": new_status})
    for p in touched:
        catalog.evaluate_low_stock(db, p)
    db.commit()
    return order


def confirm_order(db: Session, order: Order) -> Order:
    return update_order_status(db, order, "confirmed")


def order_to_public(o: Order) -> dict:
    return {
        "code": o.code, "status": o.status, "channel": o.channel, "total": fmt_money(o.total), "currency": "USD",
        "is_demo": o.is_demo, "quote_code": o.quote.code if o.quote else None,
        "items": [
            {"product_id": i.product_id, "name": i.product.name if i.product else None, "quantity": i.quantity,
             "unit_price": fmt_money(i.unit_price), "line_total": fmt_money(i.line_total)}
            for i in o.items
        ],
        "message": DEMO_MESSAGE,
    }


def format_order_text(order: Order) -> str:
    lines = [f"🛒 Pedido demo {order.code}", ""]
    for i in order.items:
        name = i.product.name if i.product else f"Producto {i.product_id}"
        lines.append(f"• {i.quantity} x {name} — US$ {fmt_money(i.line_total)}")
    lines += ["", f"Total: US$ {fmt_money(order.total)}",
              f"Estado: {STATUS_LABELS.get(order.status, order.status)}", "", DEMO_MESSAGE]
    return "\n".join(lines)
