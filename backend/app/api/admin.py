"""Endpoints admin /admin/* (doc 04). Todos requieren X-Admin-Key."""

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, FastAPI, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.db import get_db
from app.core.errors import AppError
from app.core.security import require_admin
from app.core.timeutil import as_utc
from app.models import Customer, ErrorLog, Event, Order, Product, Quote, Simulation
from app.schemas.api import CustomerPatch, ProductPatch, StatusPatch
from app.schemas.common import fmt_money
from app.services import catalog, metrics, orders, quotes
from app.storage import get_storage

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


def register(app: FastAPI) -> None:
    from app.automation import scheduler

    app.state.startup_hooks.append(scheduler.start)
    app.state.shutdown_hooks.append(scheduler.stop)


def _iso(dt) -> str | None:
    return as_utc(dt).isoformat() if dt else None


# ---------- Métricas ----------
@router.get("/metrics/summary")
def metrics_summary(
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    db: Session = Depends(get_db),
):
    return metrics.summary(db, date_from, date_to)


@router.get("/metrics/daily")
def metrics_daily(days: int = Query(default=14, ge=1, le=365), db: Session = Depends(get_db)):
    return metrics.daily(db, days)


@router.get("/metrics/top-products")
def metrics_top_products(
    kind: Literal["inquired", "requested"] = "inquired",
    limit: int = Query(default=5, ge=1, le=50),
    db: Session = Depends(get_db),
):
    return metrics.top_products(db, kind, limit)


@router.get("/usage")
def usage(days: int = Query(default=30, ge=1, le=365), db: Session = Depends(get_db)):
    return metrics.usage(db, days)


# ---------- Bitácoras ----------
@router.get("/events")
def list_events(
    type: str | None = None,  # noqa: A002
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    conds = [Event.type == type] if type else []
    total = db.scalar(select(func.count(Event.id)).where(*conds)) or 0
    rows = db.scalars(select(Event).where(*conds).order_by(Event.id.desc()).limit(limit).offset(offset)).all()
    return {
        "items": [
            {"id": e.id, "type": e.type, "entity_type": e.entity_type, "entity_id": e.entity_id,
             "customer_id": e.customer_id, "payload": e.payload, "processed": e.processed, "notified": e.notified,
             "created_at": _iso(e.created_at)}
            for e in rows
        ],
        "total": total, "limit": limit, "offset": offset,
    }


@router.get("/errors")
def list_errors(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    source: str | None = None,
    db: Session = Depends(get_db),
):
    conds = [ErrorLog.source == source] if source else []
    total = db.scalar(select(func.count(ErrorLog.id)).where(*conds)) or 0
    rows = db.scalars(select(ErrorLog).where(*conds).order_by(ErrorLog.id.desc()).limit(limit).offset(offset)).all()
    return {
        "items": [
            {"id": e.id, "source": e.source, "error_type": e.error_type, "message": e.message, "context": e.context,
             "customer_id": e.customer_id, "created_at": _iso(e.created_at)}
            for e in rows
        ],
        "total": total, "limit": limit, "offset": offset,
    }


@router.get("/simulations")
def list_simulations(
    limit: int = Query(default=20, ge=1, le=200),
    status: str | None = None,
    db: Session = Depends(get_db),
):
    conds = [Simulation.status == status] if status else []
    rows = db.scalars(
        select(Simulation).options(selectinload(Simulation.rating), selectinload(Simulation.product))
        .where(*conds).order_by(Simulation.id.desc()).limit(limit)
    ).all()
    storage = get_storage()
    items = []
    for s in rows:
        output_url = None
        if s.output_key:
            try:
                output_url = storage.url(s.output_key, expires=600)
            except Exception:  # noqa: BLE001
                output_url = None
        items.append({
            "id": s.id, "customer_id": s.customer_id, "product_id": s.product_id,
            "product_name": s.product.name if s.product else None, "status": s.status,
            "room_width_cm": s.room_width_cm, "room_height_cm": s.room_height_cm, "room_depth_cm": s.room_depth_cm,
            "model": s.model, "size": s.size, "quality": s.quality, "cost_usd": fmt_money(s.cost_usd, 4),
            "reused_from_id": s.reused_from_id, "error_message": s.error_message,
            "rating": s.rating.score if s.rating else None,
            "rating_comment": s.rating.comment if s.rating else None,
            "output_url": output_url, "created_at": _iso(s.created_at), "completed_at": _iso(s.completed_at),
        })
    return {"items": items, "total": len(items)}


# ---------- Cotizaciones y pedidos ----------
def _quote_admin(q: Quote) -> dict:
    data = quotes.quote_to_public(q)
    c = q.customer
    data.update({
        "id": q.id,
        "customer": {"id": c.id, "name": c.name, "email": c.email, "phone": c.phone,
                     "telegram_username": c.telegram_username} if c else None,
        "sent_at": _iso(q.sent_at), "created_at": _iso(q.created_at),
    })
    return data


def _order_admin(o: Order) -> dict:
    data = orders.order_to_public(o)
    data.update({
        "id": o.id, "customer_id": o.customer_id, "contact_name": o.contact_name, "contact_email": o.contact_email,
        "contact_phone": o.contact_phone, "delivery_address": o.delivery_address, "created_at": _iso(o.created_at),
    })
    return data


@router.get("/quotes")
def list_quotes(
    status: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    conds = [Quote.status == status] if status else []
    total = db.scalar(select(func.count(Quote.id)).where(*conds)) or 0
    rows = db.scalars(
        select(Quote).options(selectinload(Quote.items), selectinload(Quote.customer))
        .where(*conds).order_by(Quote.id.desc()).limit(limit).offset(offset)
    ).all()
    return {"items": [_quote_admin(q) for q in rows], "total": total, "limit": limit, "offset": offset}


@router.get("/orders")
def list_orders(
    status: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    conds = [Order.status == status] if status else []
    total = db.scalar(select(func.count(Order.id)).where(*conds)) or 0
    rows = db.scalars(
        select(Order).options(selectinload(Order.items), selectinload(Order.quote))
        .where(*conds).order_by(Order.id.desc()).limit(limit).offset(offset)
    ).all()
    return {"items": [_order_admin(o) for o in rows], "total": total, "limit": limit, "offset": offset}


@router.patch("/quotes/{code}")
def patch_quote(code: str, body: StatusPatch, db: Session = Depends(get_db)):
    q = quotes.get_quote_or_404(db, code)
    quotes.update_quote_status(db, q, body.status)
    return _quote_admin(quotes.get_quote_or_404(db, code))


@router.patch("/orders/{code}")
def patch_order(code: str, body: StatusPatch, db: Session = Depends(get_db)):
    o = orders.get_order_or_404(db, code)
    orders.update_order_status(db, o, body.status)
    return _order_admin(orders.get_order_or_404(db, code))


@router.get("/products")
def list_products_admin(db: Session = Depends(get_db)):
    rows = db.scalars(select(Product).options(selectinload(Product.images), selectinload(Product.category))
                      .order_by(Product.id)).all()
    return {"items": [catalog.product_to_public(p, detail=True) for p in rows], "total": len(rows)}


@router.patch("/products/{product_id}")
def patch_product(product_id: int, body: ProductPatch, db: Session = Depends(get_db)):
    p = catalog.get_product(db, product_id, active_only=False)
    if p is None:
        raise AppError("PRODUCT_NOT_FOUND", "Producto no encontrado", 404)
    if body.stock is not None:
        p.stock = body.stock
    if body.price is not None:
        p.price = body.price
    if body.active is not None:
        p.active = body.active
    db.flush()
    catalog.evaluate_low_stock(db, p)
    db.commit()
    return catalog.product_to_public(p, detail=True)


@router.patch("/customers/{customer_id}")
def patch_customer(customer_id: int, body: CustomerPatch, db: Session = Depends(get_db)):
    c = db.get(Customer, customer_id)
    if c is None:
        raise AppError("CUSTOMER_NOT_FOUND", "Cliente no encontrado", 404)
    c.simulations_used = body.simulations_used
    db.commit()
    return {"id": c.id, "name": c.name, "source": c.source, "telegram_username": c.telegram_username,
            "simulations_used": c.simulations_used}


# ---------- Jobs ----------
@router.post("/jobs/daily-summary")
def job_daily_summary(force: bool = False, db: Session = Depends(get_db)):
    from app.automation.summary import send_daily_summary

    return send_daily_summary(db, force=force)


@router.post("/jobs/cleanup-photos")
def job_cleanup_photos(db: Session = Depends(get_db)):
    from app.automation.scheduler import cleanup_photos

    return {"deleted": cleanup_photos(db)}


@router.post("/jobs/expire-quotes")
def job_expire_quotes(db: Session = Depends(get_db)):
    return {"expired": quotes.expire_quotes(db)}
