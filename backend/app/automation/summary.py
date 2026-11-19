"""Resumen diario para el admin (idempotente por día local salvo force=True)."""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.timeutil import local_day_bounds_utc, today_local
from app.models import Event
from app.services import budget, metrics


def build_daily_summary_text(stats: dict, spent_total_pct: float | None = None) -> str:
    d = date.fromisoformat(stats["date"])
    rating = f"{stats['avg_rating']:.1f} ({stats['ratings_count']})" if stats["avg_rating"] is not None else "—"
    lines = [
        f"📊 Resumen DecoSmart {d:%d/%m/%Y}",
        "",
        f"💬 Conversaciones: {stats['conversations']}",
        f"🔎 Consultas: {stats['inquiries']}",
        f"🧾 Cotizaciones: {stats['quotes']}",
        f"🛒 Pedidos demo: {stats['orders']} (completados: {stats['orders_completed']})",
        f"🖼️ Simulaciones: {stats['simulations']} (fallidas: {stats['simulations_failed']})",
        f"⭐ Rating promedio: {rating}",
        f"💸 Gasto API del día: US$ {stats['api_cost_usd']}",
    ]
    if spent_total_pct is not None:
        lines.append(f"📈 Presupuesto usado: {spent_total_pct}%")
    if stats.get("errors"):
        lines.append(f"⚠️ Errores: {stats['errors']}")
    return "\n".join(lines)


def summary_sent_today(db: Session, day: date | None = None) -> bool:
    start, end = local_day_bounds_utc(day or today_local())
    return (db.scalar(
        select(func.count(Event.id)).where(Event.type == "summary.daily", Event.created_at >= start,
                                           Event.created_at < end)
    ) or 0) > 0


def send_daily_summary(db: Session, force: bool = False) -> dict:
    """Genera el resumen del día local y emite `summary.daily` (el handler lo envía al admin).

    Devuelve {"sent": bool, "text": str, "reason"?: str}. Si ya se emitió hoy y no hay `force` →
    {"sent": False, "reason": "already_sent"}.
    """
    from app.automation.events import emit

    day = today_local()
    if not force and summary_sent_today(db, day):
        return {"sent": False, "reason": "already_sent", "date": day.isoformat()}
    stats = metrics.day_stats(db, day)
    text = build_daily_summary_text(stats, budget.used_pct(db=db))
    event = emit(db, "summary.daily", entity_type="system", payload={"text": text, "stats": stats})
    db.commit()
    result = {"sent": bool(event.notified), "text": text, "date": day.isoformat()}
    if not event.notified:
        result["reason"] = "no_admin_chat" if not get_settings().admin_telegram_chat_id else "send_failed"
    return result
