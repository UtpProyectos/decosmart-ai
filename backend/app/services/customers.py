"""Clientes y conversaciones."""

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.timeutil import as_utc, now_utc
from app.models import Conversation, Customer

CONVERSATION_IDLE_HOURS = 6


def get_or_create_by_telegram(
    db: Session, chat_id: int, username: str | None = None, name: str | None = None
) -> Customer:
    c = db.scalar(select(Customer).where(Customer.telegram_chat_id == chat_id))
    if c is None:
        c = Customer(telegram_chat_id=chat_id, telegram_username=username, name=name, source="telegram")
        db.add(c)
        db.commit()
        return c
    changed = False
    if username and c.telegram_username != username:
        c.telegram_username, changed = username, True
    if name and not c.name:
        c.name, changed = name, True
    if changed:
        db.commit()
    return c


def get_or_create_web(db: Session, name: str | None, email: str | None, phone: str | None = None) -> Customer:
    """Deduplica por email (sin distinguir mayúsculas); actualiza nombre/teléfono si vienen."""
    email_n = email.strip().lower() if email else None
    c = db.scalar(select(Customer).where(Customer.email == email_n).order_by(Customer.id)) if email_n else None
    if c is None:
        c = Customer(name=name, email=email_n, phone=phone, source="web")
        db.add(c)
    else:
        if name:
            c.name = name
        if phone:
            c.phone = phone
    db.commit()
    return c


def get_or_create_conversation(db: Session, customer: Customer, channel: str = "telegram") -> Conversation:
    """Reutiliza la última conversación si tuvo actividad en las últimas 6 h; si no, crea una nueva
    y emite `conversation.started`."""
    from app.automation.events import emit

    conv = db.scalar(
        select(Conversation).where(Conversation.customer_id == customer.id, Conversation.channel == channel)
        .order_by(Conversation.id.desc())
    )
    now = now_utc()
    if conv is not None and as_utc(conv.last_message_at) >= now - timedelta(hours=CONVERSATION_IDLE_HOURS):
        return conv
    conv = Conversation(customer_id=customer.id, channel=channel, state="idle", context={},
                        started_at=now, last_message_at=now)
    db.add(conv)
    db.flush()
    emit(db, "conversation.started", entity_type="conversation", entity_id=conv.id, customer_id=customer.id,
         payload={"channel": channel})
    db.commit()
    return conv


def touch_conversation(db: Session, conv: Conversation, commit: bool = True) -> None:
    conv.last_message_at = now_utc()
    conv.message_count = (conv.message_count or 0) + 1
    if commit:
        db.commit()
