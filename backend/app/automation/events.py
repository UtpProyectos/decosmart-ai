"""Bus de eventos síncrono. Ver CODEX_HANDOFF §5.7.

`emit()` inserta en `events` y ejecuta los handlers registrados con `@on("tipo")`.
Los errores de handler se registran en `error_logs` (source=automation) y nunca se propagan.
El caller es responsable de hacer `db.commit()` (los services lo hacen).
"""

import logging
import threading
from collections import defaultdict
from collections.abc import Callable

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Event
from app.services.errors import log_error

log = logging.getLogger(__name__)

# handler(db, event) -> True si envió una notificación (marca event.notified)
Handler = Callable[[Session, Event], bool | None]
_HANDLERS: dict[str, list[Handler]] = defaultdict(list)


def on(event_type: str) -> Callable[[Handler], Handler]:
    def deco(fn: Handler) -> Handler:
        if fn not in _HANDLERS[event_type]:
            _HANDLERS[event_type].append(fn)
        return fn

    return deco


def handlers_for(event_type: str) -> list[Handler]:
    return list(_HANDLERS.get(event_type, []))


def unregister(event_type: str, fn: Handler) -> None:
    if fn in _HANDLERS.get(event_type, []):
        _HANDLERS[event_type].remove(fn)


def emit(
    db: Session,
    type: str,  # noqa: A002
    entity_type: str | None = None,
    entity_id: int | None = None,
    customer_id: int | None = None,
    payload: dict | None = None,
) -> Event:
    event = Event(
        type=type, entity_type=entity_type, entity_id=entity_id, customer_id=customer_id, payload=payload or {}
    )
    db.add(event)
    db.flush()

    notified = False
    for handler in handlers_for(type):
        try:
            with db.begin_nested():
                if handler(db, event):
                    notified = True
        except Exception as exc:  # noqa: BLE001
            log.exception("Handler %s falló para %s", getattr(handler, "__name__", handler), type)
            log_error(
                db, "automation", exc.__class__.__name__, str(exc),
                {"event_type": type, "event_id": event.id, "handler": getattr(handler, "__name__", str(handler))},
                customer_id=customer_id, commit=False,
            )
    event.processed = True
    if notified:
        event.notified = True
    db.flush()
    _forward_n8n(event)
    return event


def _forward_n8n(event: Event) -> None:
    url = get_settings().n8n_webhook_url
    if not url:
        return
    body = {
        "id": event.id, "type": event.type, "entity_type": event.entity_type, "entity_id": event.entity_id,
        "customer_id": event.customer_id, "payload": event.payload,
    }

    def _post() -> None:
        try:
            httpx.post(url, json=body, timeout=3.0)
        except Exception as exc:  # noqa: BLE001
            log.warning("n8n forward falló: %s", exc.__class__.__name__)

    threading.Thread(target=_post, daemon=True).start()
