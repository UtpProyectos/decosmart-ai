"""Endpoints públicos /api/* (doc 04)."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.errors import AppError
from app.core.security import rate_limit
from app.schemas.api import (
    CategoryOut,
    OrderCreate,
    OrderOut,
    ProductDetailOut,
    ProductPage,
    PublicConfig,
    QuoteCreate,
    QuoteOut,
)
from app.services import catalog, customers, inquiries, orders, quotes

router = APIRouter(prefix="/api", tags=["public"], dependencies=[Depends(rate_limit)])


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return catalog.list_categories(db)


@router.get("/products", response_model=ProductPage)
def list_products(
    category: str | None = None,
    q: str | None = Query(default=None, max_length=100),
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    room: str | None = None,
    in_stock: bool | None = None,
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    items, total = catalog.search_products_with_total(
        db, query=q, category=category, max_price=max_price, room=room, in_stock=in_stock, limit=limit,
        offset=offset, min_price=min_price,
    )
    return {"items": [catalog.product_to_public(p) for p in items], "total": total, "limit": limit, "offset": offset}


@router.get("/products/{id_or_slug}", response_model=ProductDetailOut)
def product_detail(id_or_slug: str, db: Session = Depends(get_db)):
    p = catalog.get_product(db, id_or_slug)
    if p is None:
        raise AppError("PRODUCT_NOT_FOUND", "Producto no encontrado", 404)
    data = catalog.product_to_public(p, detail=True)
    inquiries.record_inquiry(db, "product_info", product_id=p.id, category_id=p.category_id, channel="web",
                             payload={"ref": id_or_slug})
    return data


@router.post("/quotes", response_model=QuoteOut, status_code=201)
def create_quote(body: QuoteCreate, db: Session = Depends(get_db)):
    cust = customers.get_or_create_web(db, body.customer.name, body.customer.email, body.customer.phone)
    q = quotes.create_quote(db, cust, [i.model_dump() for i in body.items], channel=body.channel, notes=body.notes)
    return quotes.quote_to_public(quotes.get_quote_or_404(db, q.code))


@router.get("/quotes/{code}", response_model=QuoteOut)
def get_quote(code: str, db: Session = Depends(get_db)):
    return quotes.quote_to_public(quotes.get_quote_or_404(db, code))


@router.post("/orders", response_model=OrderOut, status_code=201)
def create_order(body: OrderCreate, db: Session = Depends(get_db)):
    cust = None
    if body.customer and not body.quote_code:
        cust = customers.get_or_create_web(db, body.customer.name, body.customer.email, body.customer.phone)
    o = orders.create_order(
        db, cust, quote_code=body.quote_code, items=[i.model_dump() for i in body.items or []] or None,
        channel=body.channel, delivery_address=body.delivery_address,
        contact_name=body.customer.name if body.customer else None,
        contact_email=body.customer.email.lower() if body.customer else None,
        contact_phone=body.customer.phone if body.customer else None,
    )
    return orders.order_to_public(orders.get_order_or_404(db, o.code))


@router.get("/orders/{code}", response_model=OrderOut)
def get_order(code: str, db: Session = Depends(get_db)):
    return orders.order_to_public(orders.get_order_or_404(db, code))


@router.get("/config/public", response_model=PublicConfig)
def public_config():
    s = get_settings()
    return {"telegram_bot_url": s.telegram_bot_url, "store_name": "DecoSmart", "currency": "USD"}
