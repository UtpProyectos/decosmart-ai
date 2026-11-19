"""Consultas para el dashboard y el resumen diario. Días calculados en settings.timezone."""

from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import pricing
from app.core.config import get_settings
from app.core.timeutil import local_day_start_utc, to_local_date, today_local
from app.models import (
    ApiUsage,
    Conversation,
    Customer,
    ErrorLog,
    Inquiry,
    Order,
    OrderItem,
    Product,
    Quote,
    QuoteItem,
    Simulation,
    SimulationRating,
)
from app.schemas.common import fmt_money
from app.services import budget


def _bounds(date_from: date | None, date_to: date | None) -> tuple[datetime | None, datetime | None]:
    start = local_day_start_utc(date_from) if date_from else None
    end = local_day_start_utc(date_to + timedelta(days=1)) if date_to else None
    return start, end


def _where(model, start, end, *conds):
    c = list(conds)
    if start is not None:
        c.append(model.created_at >= start)
    if end is not None:
        c.append(model.created_at < end)
    return c


def _count(db: Session, model, start=None, end=None, *conds) -> int:
    return db.scalar(select(func.count(model.id)).where(*_where(model, start, end, *conds))) or 0


def _sum_cost(db: Session, start=None, end=None, *conds) -> Decimal:
    v = db.scalar(select(func.coalesce(func.sum(ApiUsage.cost_usd), 0)).where(*_where(ApiUsage, start, end, *conds)))
    return Decimal(str(v or 0))


def _rating_stats(db: Session, start=None, end=None) -> tuple[float | None, int]:
    row = db.execute(
        select(func.avg(SimulationRating.score), func.count(SimulationRating.id))
        .where(*_where(SimulationRating, start, end))
    ).one()
    avg = round(float(row[0]), 2) if row[0] is not None else None
    return avg, int(row[1] or 0)


def summary(db: Session, date_from: date | None = None, date_to: date | None = None) -> dict:
    s = get_settings()
    start, end = _bounds(date_from, date_to)
    avg_rating, ratings_count = _rating_stats(db, start, end)
    spent_total = budget.spent_usd(db)
    return {
        "conversations_total": _count(db, Conversation, start, end),
        "unique_customers": _count(db, Customer, start, end),
        "inquiries_total": _count(db, Inquiry, start, end),
        "quotes_total": _count(db, Quote, start, end),
        "quotes_accepted": _count(db, Quote, start, end, Quote.status == "accepted"),
        "orders_total": _count(db, Order, start, end),
        "orders_completed": _count(db, Order, start, end, Order.status == "completed"),
        "simulations_total": _count(db, Simulation, start, end),
        "simulations_failed": _count(db, Simulation, start, end, Simulation.status == "failed"),
        "simulations_reused": _count(db, Simulation, start, end, Simulation.reused_from_id.is_not(None)),
        "avg_rating": avg_rating,
        "ratings_count": ratings_count,
        "api_cost_usd": fmt_money(_sum_cost(db, start, end, ApiUsage.mode == "live"), 4),
        "budget_usd": fmt_money(s.budget_usd_limit, 2),
        "budget_used_pct": budget.used_pct(spent_total),
        "errors_total": _count(db, ErrorLog, start, end),
        "ai_mode": s.ai_mode,
    }


def _bucket(db: Session, model, start: datetime, days: list[date], *conds) -> dict[date, int]:
    out: dict[date, int] = defaultdict(int)
    for (created,) in db.execute(select(model.created_at).where(model.created_at >= start, *conds)):
        d = to_local_date(created)
        out[d] += 1
    return out


def daily(db: Session, days: int = 14) -> list[dict]:
    """Serie diaria con ceros: [{date, conversations, inquiries, quotes, orders, simulations}] (más antiguo primero)."""
    days = max(1, min(days, 365))
    today = today_local()
    day_list = [today - timedelta(days=i) for i in range(days - 1, -1, -1)]
    start = local_day_start_utc(day_list[0])
    series = {
        "conversations": _bucket(db, Conversation, start, day_list),
        "inquiries": _bucket(db, Inquiry, start, day_list),
        "quotes": _bucket(db, Quote, start, day_list),
        "orders": _bucket(db, Order, start, day_list),
        "simulations": _bucket(db, Simulation, start, day_list),
    }
    return [{"date": d.isoformat(), **{k: v.get(d, 0) for k, v in series.items()}} for d in day_list]


def top_products(db: Session, kind: str = "inquired", limit: int = 5) -> list[dict]:
    counts: dict[int, int] = defaultdict(int)
    if kind == "requested":
        for model in (QuoteItem, OrderItem):
            for pid, qty in db.execute(select(model.product_id, func.sum(model.quantity)).group_by(model.product_id)):
                counts[pid] += int(qty or 0)
    else:
        for pid, n in db.execute(
            select(Inquiry.product_id, func.count(Inquiry.id)).where(Inquiry.product_id.is_not(None))
            .group_by(Inquiry.product_id)
        ):
            counts[pid] += int(n or 0)
    if not counts:
        return []
    products = {p.id: p for p in db.scalars(select(Product).where(Product.id.in_(counts.keys())))}
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
    return [
        {"product_id": pid, "sku": products[pid].sku, "name": products[pid].name, "count": n,
         "stock": products[pid].stock}
        for pid, n in ranked if pid in products
    ]


def usage(db: Session, days: int = 30) -> dict:
    s = get_settings()
    days = max(1, min(days, 365))
    today = today_local()
    start = local_day_start_utc(today - timedelta(days=days - 1))
    rows = db.scalars(select(ApiUsage).where(ApiUsage.created_at >= start)).all()

    def agg(key) -> list[dict]:
        acc: dict[str, list] = defaultdict(lambda: [0, Decimal("0")])
        for r in rows:
            k = key(r)
            acc[k][0] += 1
            acc[k][1] += Decimal(str(r.cost_usd or 0))
        return [{"key": k, "calls": v[0], "cost_usd": fmt_money(v[1], 4)} for k, v in sorted(acc.items())]

    by_op = [{"operation": x.pop("key"), **x} for x in agg(lambda r: r.operation)]
    by_model = [{"model": x.pop("key"), **x} for x in agg(lambda r: r.model)]
    day_acc = {(today - timedelta(days=i)).isoformat(): [0, Decimal("0")] for i in range(days - 1, -1, -1)}
    for r in rows:
        k = to_local_date(r.created_at).isoformat()
        if k in day_acc:
            day_acc[k][0] += 1
            day_acc[k][1] += Decimal(str(r.cost_usd or 0))
    total = sum((Decimal(str(r.cost_usd or 0)) for r in rows), Decimal("0"))
    sim_costs = [Decimal(str(r.cost_usd or 0)) for r in rows if r.operation == "image_edit" and r.success]
    chat_cost = sum((Decimal(str(r.cost_usd or 0)) for r in rows if r.operation == "chat"), Decimal("0"))
    conversations = _count(db, Conversation, start)
    spent = budget.spent_usd(db)
    return {
        "days": days,
        "total_usd": fmt_money(total, 4),
        "calls": len(rows),
        "failed_calls": sum(1 for r in rows if not r.success),
        "by_operation": by_op,
        "by_model": by_model,
        "by_day": [{"date": k, "calls": v[0], "cost_usd": fmt_money(v[1], 4)} for k, v in day_acc.items()],
        "avg_cost_per_simulation": fmt_money(sum(sim_costs) / len(sim_costs) if sim_costs else 0, 4),
        "avg_cost_per_conversation": fmt_money(chat_cost / conversations if conversations else 0, 4),
        "spent_live_usd": fmt_money(spent, 4),
        "budget_usd": fmt_money(s.budget_usd_limit, 2),
        "budget_used_pct": budget.used_pct(spent),
        "pricing_verified_at": pricing.PRICING_VERIFIED_AT,
        "ai_mode": s.ai_mode,
    }


def day_stats(db: Session, day: date | None = None) -> dict:
    """Cifras de un día local (para el resumen diario)."""
    day = day or today_local()
    start, end = _bounds(day, day)
    avg_rating, ratings_count = _rating_stats(db, start, end)
    return {
        "date": day.isoformat(),
        "conversations": _count(db, Conversation, start, end),
        "inquiries": _count(db, Inquiry, start, end),
        "quotes": _count(db, Quote, start, end),
        "orders": _count(db, Order, start, end),
        "orders_completed": _count(db, Order, start, end, Order.status == "completed"),
        "simulations": _count(db, Simulation, start, end, Simulation.status == "completed"),
        "simulations_failed": _count(db, Simulation, start, end, Simulation.status == "failed"),
        "avg_rating": avg_rating,
        "ratings_count": ratings_count,
        "api_cost_usd": fmt_money(_sum_cost(db, start, end, ApiUsage.mode == "live"), 4),
        "errors": _count(db, ErrorLog, start, end),
    }
