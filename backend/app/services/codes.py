"""Códigos correlativos diarios: COT-YYYYMMDD-0001 / PED-YYYYMMDD-0001 (día en settings.timezone)."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.timeutil import today_local
from app.models import Order, Quote

_MODELS = {"COT": Quote, "PED": Order}


def next_code(db: Session, prefix: str, day: date | None = None) -> str:
    if prefix not in _MODELS:
        raise ValueError(f"Prefijo desconocido: {prefix}")
    model = _MODELS[prefix]
    day = day or today_local()
    base = f"{prefix}-{day:%Y%m%d}-"
    codes = db.scalars(select(model.code).where(model.code.like(f"{base}%"))).all()
    seq = 0
    for c in codes:
        try:
            seq = max(seq, int(c.rsplit("-", 1)[1]))
        except (IndexError, ValueError):
            continue
    return f"{base}{seq + 1:04d}"
