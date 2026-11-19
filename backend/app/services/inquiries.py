"""Consultas (inquiries): cada pregunta concreta sobre producto/categoría. Emite `inquiry.created`."""

from sqlalchemy.orm import Session

from app.models import Inquiry

INQUIRY_TYPES = {"product_info", "price", "dimensions", "stock", "recommendation", "catalog"}


def record_inquiry(
    db: Session,
    type: str,  # noqa: A002
    customer_id: int | None = None,
    product_id: int | None = None,
    category_id: int | None = None,
    channel: str = "telegram",
    payload: dict | None = None,
    commit: bool = True,
) -> Inquiry:
    from app.automation.events import emit

    inq = Inquiry(type=type, customer_id=customer_id, product_id=product_id, category_id=category_id,
                  channel=channel, payload=payload or {})
    db.add(inq)
    db.flush()
    emit(db, "inquiry.created", entity_type="inquiry", entity_id=inq.id, customer_id=customer_id,
         payload={"type": type, "channel": channel, "product_id": product_id})
    if commit:
        db.commit()
    return inq
