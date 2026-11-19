"""Cotizaciones: precio congelado, validez, transiciones y formato de texto. Ver CODEX_HANDOFF §5.1."""

from collections import OrderedDict
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.timeutil import now_utc, today_local
from app.models import Customer, Product, Quote, QuoteItem
from app.schemas.common import fmt_money
from app.services import catalog
from app.services.codes import next_code

DISCLAIMER = "Cotización referencial. Precios sujetos a stock al momento de confirmar."
QUOTE_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"sent"},
    "sent": {"accepted", "rejected", "expired"},
}
STATUS_LABELS = {
    "draft": "Borrador", "sent": "Enviada", "accepted": "Aceptada", "rejected": "Rechazada", "expired": "Vencida",
}


def resolve_items(db: Session, items: list[dict]) -> list[tuple[Product, int]]:
    """items: [{"product_id": 1 | "product_ref": "DS-SOF-001", "quantity": 2}]. Agrupa duplicados y valida stock.

    Errores: PRODUCT_NOT_FOUND (404), INSUFFICIENT_STOCK (409), VALIDATION_ERROR (422).
    """
    if not items:
        raise AppError("VALIDATION_ERROR", "Debes incluir al menos un producto", 422)
    merged: OrderedDict[int, tuple[Product, int]] = OrderedDict()
    for it in items:
        ref = it.get("product_id") if it.get("product_id") is not None else it.get("product_ref")
        qty = int(it.get("quantity") or 0)
        if qty <= 0:
            raise AppError("VALIDATION_ERROR", "La cantidad debe ser mayor a 0", 422, {"product_ref": str(ref)})
        p = catalog.get_product(db, ref)
        if p is None:
            raise AppError("PRODUCT_NOT_FOUND", "Producto no encontrado", 404, {"product_ref": str(ref)})
        prev = merged.get(p.id)
        merged[p.id] = (p, (prev[1] if prev else 0) + qty)
    for p, qty in merged.values():
        if p.stock < qty:
            raise AppError(
                "INSUFFICIENT_STOCK", f"Stock insuficiente para {p.name}", 409,
                {"product_id": p.id, "sku": p.sku, "available": p.stock, "requested": qty},
            )
    return list(merged.values())


def create_quote(
    db: Session, customer: Customer, items: list[dict], channel: str = "web", notes: str | None = None
) -> Quote:
    """Valida stock (no reserva), congela unit_price, código diario, status 'sent', emite quote.created."""
    from app.automation.events import emit

    lines = resolve_items(db, items)
    quote = Quote(
        code=next_code(db, "COT"), customer_id=customer.id, channel=channel, status="sent", notes=notes,
        valid_until=today_local() + timedelta(days=get_settings().quote_validity_days), sent_at=now_utc(),
    )
    total = Decimal("0")
    for p, qty in lines:
        line_total = (p.price * qty).quantize(Decimal("0.01"))
        quote.items.append(QuoteItem(product_id=p.id, quantity=qty, unit_price=p.price, line_total=line_total))
        total += line_total
    quote.subtotal = total
    quote.total = total
    db.add(quote)
    db.flush()
    emit(db, "quote.created", entity_type="quote", entity_id=quote.id, customer_id=customer.id,
         payload={"code": quote.code, "total": fmt_money(total), "channel": channel})
    db.commit()
    return quote


def get_quote(db: Session, code: str) -> Quote | None:
    return db.scalar(
        select(Quote).options(selectinload(Quote.items).selectinload(QuoteItem.product), selectinload(Quote.customer))
        .where(Quote.code == code.strip().upper())
    )


def get_quote_or_404(db: Session, code: str) -> Quote:
    q = get_quote(db, code)
    if q is None:
        raise AppError("QUOTE_NOT_FOUND", "Cotización no encontrada", 404, {"code": code})
    return q


def check_transition(table: dict[str, set[str]], current: str, new: str) -> None:
    if new not in table.get(current, set()):
        raise AppError("INVALID_TRANSITION", f"Transición no permitida: {current} → {new}", 409,
                       {"from": current, "to": new})


def update_quote_status(db: Session, quote: Quote, new_status: str, commit: bool = True) -> Quote:
    from app.automation.events import emit

    old = quote.status
    check_transition(QUOTE_TRANSITIONS, old, new_status)
    quote.status = new_status
    if new_status == "sent" and quote.sent_at is None:
        quote.sent_at = now_utc()
    db.flush()
    emit(db, "quote.status_changed", entity_type="quote", entity_id=quote.id, customer_id=quote.customer_id,
         payload={"code": quote.code, "from": old, "to": new_status})
    if commit:
        db.commit()
    return quote


def expire_quotes(db: Session) -> int:
    """sent y valid_until < hoy → expired (emite quote.status_changed). Devuelve cuántas expiró."""
    today = today_local()
    quotes = db.scalars(select(Quote).where(Quote.status == "sent", Quote.valid_until < today)).all()
    for q in quotes:
        update_quote_status(db, q, "expired", commit=False)
    db.commit()
    return len(quotes)


def quote_to_public(q: Quote) -> dict:
    """Formato público (doc 04). No incluye datos de contacto."""
    return {
        "code": q.code, "status": q.status, "channel": q.channel,
        "items": [
            {"product_id": i.product_id, "sku": i.product.sku if i.product else None,
             "name": i.product.name if i.product else None, "quantity": i.quantity,
             "unit_price": fmt_money(i.unit_price), "line_total": fmt_money(i.line_total)}
            for i in q.items
        ],
        "subtotal": fmt_money(q.subtotal), "total": fmt_money(q.total), "currency": "USD",
        "valid_until": q.valid_until.isoformat(), "notes": q.notes, "disclaimer": DISCLAIMER,
    }


def format_quote_text(quote: Quote) -> str:
    """Texto plano (Telegram) de la cotización, en español."""
    lines = [f"🧾 Cotización {quote.code}", ""]
    for i in quote.items:
        name = i.product.name if i.product else f"Producto {i.product_id}"
        lines.append(f"• {name}")
        lines.append(f"  {i.quantity} x US$ {fmt_money(i.unit_price)} = US$ {fmt_money(i.line_total)}")
    lines += [
        "",
        f"Total: US$ {fmt_money(quote.total)}",
        f"Válida hasta: {quote.valid_until:%d/%m/%Y}",
        f"Estado: {STATUS_LABELS.get(quote.status, quote.status)}",
        "",
        DISCLAIMER,
    ]
    return "\n".join(lines)
