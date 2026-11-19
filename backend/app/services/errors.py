"""Registro de errores en error_logs, saneado (sin tokens, teléfonos, emails ni secretos)."""

import logging
import re
from typing import Any

from sqlalchemy.orm import Session

from app.models import ErrorLog

log = logging.getLogger(__name__)

_SENSITIVE_KEYS = ("token", "secret", "password", "passwd", "api_key", "apikey", "authorization",
                   "phone", "telefono", "email", "address", "direccion", "photo", "image_bytes", "key_id")
_PATTERNS = [
    (re.compile(r"\b\d{6,12}:[A-Za-z0-9_-]{30,}\b"), "[telegram-token]"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{10,}\b"), "[api-key]"),
    (re.compile(r"/bot[^/\s]+/"), "/bot[token]/"),
    (re.compile(r"(?i)bearer\s+[A-Za-z0-9._-]+"), "Bearer [token]"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[email]"),
    (re.compile(r"\+?\d[\d\s-]{7,}\d"), "[phone]"),
]
MAX_MESSAGE = 2000


def sanitize_text(text: str) -> str:
    for pattern, repl in _PATTERNS:
        text = pattern.sub(repl, text)
    return text[:MAX_MESSAGE]


def sanitize_context(value: Any, _depth: int = 0) -> Any:
    if _depth > 5:
        return "[truncated]"
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if any(s in str(k).lower() for s in _SENSITIVE_KEYS):
                out[str(k)] = "[redacted]"
            else:
                out[str(k)] = sanitize_context(v, _depth + 1)
        return out
    if isinstance(value, list | tuple):
        return [sanitize_context(v, _depth + 1) for v in value[:50]]
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, int | float | bool) or value is None:
        return value
    return sanitize_text(str(value))


def log_error(
    db: Session,
    source: str,
    error_type: str,
    message: str,
    context: dict | None = None,
    customer_id: int | None = None,
    commit: bool = True,
) -> ErrorLog | None:
    """Inserta un ErrorLog. Nunca lanza excepción (si falla la BD, solo registra en el log)."""
    try:
        entry = ErrorLog(
            source=source[:20],
            error_type=error_type[:80],
            message=sanitize_text(str(message)),
            context=sanitize_context(context or {}),
            customer_id=customer_id,
        )
        db.add(entry)
        if commit:
            db.commit()
        else:
            db.flush()
        return entry
    except Exception:  # noqa: BLE001
        log.exception("No se pudo registrar error_log (%s/%s)", source, error_type)
        try:
            db.rollback()
        except Exception:  # noqa: BLE001
            pass
        return None
