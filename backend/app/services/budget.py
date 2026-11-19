"""Guardia de presupuesto y registro de api_usage. Ver CODEX_HANDOFF §5.6.

Toda llamada real a OpenAI debe pasar por `track(...)` (o `record_usage`).
"""

import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import pricing
from app.core.config import get_settings
from app.core.timeutil import local_day_bounds_utc, today_local
from app.models import ApiUsage, Customer, Event


class BudgetExceeded(Exception):
    """reason: 'budget' (presupuesto global) | 'customer_limit' (mensajes/día del cliente)."""

    def __init__(self, reason: str, message: str = ""):
        super().__init__(message or reason)
        self.reason = reason


def spent_usd(db: Session) -> Decimal:
    total = db.scalar(select(func.coalesce(func.sum(ApiUsage.cost_usd), 0)).where(ApiUsage.mode == "live"))
    return Decimal(str(total or 0))


def budget_limit() -> Decimal:
    return Decimal(str(get_settings().budget_usd_limit))


def used_pct(spent: Decimal | None = None, db: Session | None = None) -> float:
    if spent is None:
        assert db is not None
        spent = spent_usd(db)
    limit = budget_limit()
    if limit <= 0:
        return 100.0
    return round(float(spent / limit * 100), 1)


def can_spend(db: Session, estimated: Decimal | float) -> bool:
    spent = spent_usd(db)
    check_warning(db, spent)
    return spent + Decimal(str(estimated)) <= budget_limit()


def check_warning(db: Session, spent: Decimal | None = None) -> list[int]:
    """Emite `budget.warning` al cruzar BUDGET_WARN_PCT y 100 % (una vez por umbral). Devuelve umbrales emitidos."""
    from app.automation.events import emit

    if spent is None:
        spent = spent_usd(db)
    pct = used_pct(spent)
    thresholds = sorted({get_settings().budget_warn_pct, 100})
    already = {
        (e.payload or {}).get("threshold")
        for e in db.scalars(select(Event).where(Event.type == "budget.warning"))
    }
    emitted = []
    for t in thresholds:
        if pct >= t and t not in already:
            emit(db, "budget.warning", entity_type="system", payload={
                "threshold": t, "pct": pct, "spent_usd": f"{spent:.4f}", "budget_usd": f"{budget_limit():.2f}",
            })
            emitted.append(t)
    if emitted:
        db.commit()
    return emitted


def llm_messages_today(db: Session, customer_id: int) -> int:
    start, end = local_day_bounds_utc(today_local())
    return db.scalar(
        select(func.count(ApiUsage.id)).where(
            ApiUsage.customer_id == customer_id, ApiUsage.operation == "chat",
            ApiUsage.created_at >= start, ApiUsage.created_at < end,
        )
    ) or 0


def estimate_chat_call() -> Decimal:
    s = get_settings()
    return pricing.estimate_chat(s.openai_chat_model, 3000, 0, s.openai_chat_max_output_tokens)


def check_llm(db: Session, customer: Customer | None) -> None:
    """Lanza BudgetExceeded si no se debe llamar al LLM para este cliente."""
    s = get_settings()
    if customer is not None and llm_messages_today(db, customer.id) >= s.max_llm_messages_per_customer_per_day:
        raise BudgetExceeded("customer_limit", "Límite diario de mensajes con IA alcanzado")
    if s.ai_mode == "live" and not can_spend(db, estimate_chat_call()):
        raise BudgetExceeded("budget", "Presupuesto de IA agotado")


def record_usage(
    db: Session,
    *,
    operation: str,
    model: str,
    provider: str = "openai",
    input_tokens: int = 0,
    cached_input_tokens: int = 0,
    output_tokens: int = 0,
    image_input_tokens: int = 0,
    images: int = 0,
    cost_usd: Decimal | float | None = None,
    mode: str | None = None,
    customer_id: int | None = None,
    simulation_id: int | None = None,
    latency_ms: int = 0,
    success: bool = True,
    quality: str | None = None,
    size: str | None = None,
    commit: bool = True,
) -> ApiUsage:
    """Inserta un registro en api_usage. Si `cost_usd` es None se estima con pricing (mock → 0)."""
    s = get_settings()
    mode = mode or s.ai_mode
    if cost_usd is None:
        if mode != "live":
            cost_usd = Decimal("0")
        elif operation == "chat":
            cost_usd = pricing.estimate_chat(model, input_tokens, cached_input_tokens, output_tokens)
        elif operation == "image_edit" and success:
            cost_usd = pricing.estimate_image_edit(model, quality or s.image_quality, size or s.image_size)
        else:
            cost_usd = Decimal("0")
    row = ApiUsage(
        provider=provider, model=model, operation=operation, input_tokens=input_tokens or 0,
        cached_input_tokens=cached_input_tokens or 0, output_tokens=output_tokens or 0,
        image_input_tokens=image_input_tokens or 0, images=images or 0, cost_usd=Decimal(str(cost_usd)),
        mode=mode, customer_id=customer_id, simulation_id=simulation_id, latency_ms=int(latency_ms),
        success=success,
    )
    db.add(row)
    db.flush()
    if mode == "live":
        check_warning(db)
    if commit:
        db.commit()
    return row


@dataclass
class UsageTracker:
    """Objeto que el caller completa dentro de `track()` con los datos de `response.usage`."""

    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    image_input_tokens: int = 0
    images: int = 0
    cost_usd: Decimal | float | None = None
    quality: str | None = None
    size: str | None = None
    extra: dict = field(default_factory=dict)
    usage: object | None = None  # se rellena al salir con el ApiUsage creado


@contextmanager
def track(
    db: Session,
    *,
    operation: str,
    model: str,
    provider: str = "openai",
    mode: str | None = None,
    customer_id: int | None = None,
    simulation_id: int | None = None,
) -> Iterator[UsageTracker]:
    """Mide latencia y registra api_usage con success True/False. Re-lanza la excepción original."""
    tracker = UsageTracker()
    start = time.perf_counter()
    success = True
    try:
        yield tracker
    except BaseException:
        success = False
        raise
    finally:
        latency = int((time.perf_counter() - start) * 1000)
        try:
            tracker.usage = record_usage(
                db, operation=operation, model=model, provider=provider, mode=mode,
                input_tokens=tracker.input_tokens, cached_input_tokens=tracker.cached_input_tokens,
                output_tokens=tracker.output_tokens, image_input_tokens=tracker.image_input_tokens,
                images=tracker.images, cost_usd=tracker.cost_usd if success else (tracker.cost_usd or 0),
                customer_id=customer_id, simulation_id=simulation_id, latency_ms=latency, success=success,
                quality=tracker.quality, size=tracker.size,
            )
        except Exception:  # noqa: BLE001
            if success:
                raise
