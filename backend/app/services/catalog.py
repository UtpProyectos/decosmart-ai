"""Catálogo: búsqueda, detalle, stock, recomendación y serialización. Ver CODEX_HANDOFF §5.1.

Filtros de precio/categoría/estado se hacen en SQL; texto libre y ambiente (JSON) en Python,
con normalización de acentos (el catálogo es pequeño).
"""

import unicodedata
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.models import Category, Product
from app.schemas.common import fmt_money

_STOPWORDS = {
    "de", "del", "la", "el", "los", "las", "un", "una", "unos", "unas", "para", "con", "en", "y", "o", "que",
    "por", "mi", "me", "tienen", "tiene", "hay", "quiero", "busco", "algo", "muy", "mas", "más", "al", "a",
}


def normalize(text: str | None) -> str:
    text = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def _tokens(query: str) -> list[str]:
    raw = [t.strip(".,;:!?¿¡()\"'") for t in normalize(query).split()]
    toks = [t for t in raw if len(t) >= 3 and t not in _STOPWORDS and not t.isdigit()]
    # Plural simple: "sofas" ↔ "sofa", "sillas" ↔ "silla"
    return [t[:-1] if len(t) > 4 and t.endswith("s") else t for t in toks]


def _haystack(p: Product) -> str:
    parts = [p.name, p.description, p.slug, p.sku, p.material, p.style, " ".join(p.colors or []),
             " ".join(p.room_types or [])]
    if p.category:
        parts += [p.category.name, p.category.slug]
    return normalize(" ".join(x for x in parts if x))


def _base_query(category: str | None, min_price, max_price, in_stock: bool | None, active_only: bool = True):
    stmt = select(Product).options(selectinload(Product.images), selectinload(Product.category))
    if active_only:
        stmt = stmt.where(Product.active.is_(True))
    if category:
        stmt = stmt.join(Category).where(Category.slug == category)
    if min_price is not None:
        stmt = stmt.where(Product.price >= Decimal(str(min_price)))
    if max_price is not None:
        stmt = stmt.where(Product.price <= Decimal(str(max_price)))
    if in_stock is True:
        stmt = stmt.where(Product.stock > 0)
    elif in_stock is False:
        stmt = stmt.where(Product.stock <= 0)
    return stmt.order_by(Product.id)


def search_products_with_total(
    db: Session,
    query: str | None = None,
    category: str | None = None,
    max_price: float | Decimal | None = None,
    room: str | None = None,
    in_stock: bool | None = None,
    limit: int = 20,
    offset: int = 0,
    min_price: float | Decimal | None = None,
) -> tuple[list[Product], int]:
    products = list(db.scalars(_base_query(category, min_price, max_price, in_stock)).all())
    if room:
        r = normalize(room)
        products = [p for p in products if r in [normalize(x) for x in (p.room_types or [])]]
    if query and query.strip():
        toks = _tokens(query)
        if toks:
            scored = []
            for p in products:
                hay = _haystack(p)
                score = sum(1 for t in toks if t in hay)
                if score:
                    scored.append((score, p))
            scored.sort(key=lambda sp: (-sp[0], sp[1].id))
            products = [p for _, p in scored]
    total = len(products)
    return products[offset: offset + limit], total


def search_products(
    db: Session,
    query: str | None = None,
    category: str | None = None,
    max_price: float | Decimal | None = None,
    room: str | None = None,
    in_stock: bool | None = None,
    limit: int = 20,
    offset: int = 0,
    min_price: float | Decimal | None = None,
) -> list[Product]:
    items, _ = search_products_with_total(db, query, category, max_price, room, in_stock, limit, offset, min_price)
    return items


def get_product(db: Session, ref: int | str | None, active_only: bool = True) -> Product | None:
    """Acepta id (int o dígitos), SKU (sin distinguir mayúsculas) o slug."""
    if ref is None:
        return None
    stmt = select(Product).options(selectinload(Product.images), selectinload(Product.category))
    if isinstance(ref, int) or (isinstance(ref, str) and ref.strip().isdigit()):
        stmt = stmt.where(Product.id == int(ref))
    else:
        r = ref.strip()
        stmt = stmt.where((func.upper(Product.sku) == r.upper()) | (Product.slug == r.lower()))
    if active_only:
        stmt = stmt.where(Product.active.is_(True))
    return db.scalars(stmt).first()


def check_stock(db: Session, ref: int | str, quantity: int = 1) -> dict:
    p = get_product(db, ref)
    if not p:
        return {"ok": False, "error": "PRODUCT_NOT_FOUND", "ref": str(ref)}
    return {
        "ok": True, "ref": p.sku, "product_id": p.id, "name": p.name, "requested": quantity,
        "available": p.stock, "sufficient": p.stock >= quantity, "low_stock": is_low_stock(p),
    }


def recommend(
    db: Session,
    budget: float | Decimal | None = None,
    room: str | None = None,
    category: str | None = None,
    max_width_cm: int | None = None,
    style: str | None = None,
    limit: int = 3,
) -> list[Product]:
    """stock>0, price<=budget, width<=max_width; orden: coincidencia estilo/ambiente, luego precio desc. Máx. 3."""
    products = list(db.scalars(_base_query(category, None, budget, True)).all())
    if max_width_cm:
        products = [p for p in products if p.width_cm <= max_width_cm]
    r, st = normalize(room), normalize(style)

    def score(p: Product) -> int:
        s = 0
        if st and normalize(p.style) == st:
            s += 2
        if r and r in [normalize(x) for x in (p.room_types or [])]:
            s += 1
        return s

    products.sort(key=lambda p: (-score(p), -p.price, p.id))
    return products[: min(limit, 3)]


def list_categories(db: Session) -> list[dict]:
    counts = dict(
        db.execute(
            select(Product.category_id, func.count(Product.id)).where(Product.active.is_(True))
            .group_by(Product.category_id)
        ).all()
    )
    cats = db.scalars(select(Category).order_by(Category.id)).all()
    return [{"id": c.id, "slug": c.slug, "name": c.name, "product_count": counts.get(c.id, 0)} for c in cats]


def is_low_stock(p: Product) -> bool:
    return p.stock <= get_settings().low_stock_threshold


def evaluate_low_stock(db: Session, product: Product) -> bool:
    """Emite `product.low_stock` una vez por producto hasta reponer; resetea el flag al reponer.

    Devuelve True si emitió el evento. No hace commit.
    """
    from app.automation.events import emit

    if is_low_stock(product):
        if not product.low_stock_notified:
            product.low_stock_notified = True
            db.flush()
            emit(db, "product.low_stock", entity_type="product", entity_id=product.id, payload={
                "sku": product.sku, "name": product.name, "stock": product.stock,
                "threshold": get_settings().low_stock_threshold,
            })
            return True
    elif product.low_stock_notified:
        product.low_stock_notified = False
        db.flush()
    return False


def dims_text(p: Product) -> str:
    return f"{p.width_cm}x{p.height_cm}x{p.depth_cm}"


def product_to_public(p: Product, detail: bool = False) -> dict:
    from app.services import product_images

    primary = product_images.primary_image(p)
    data = {
        "id": p.id, "sku": p.sku, "slug": p.slug, "name": p.name,
        "category": {"slug": p.category.slug, "name": p.category.name} if p.category else None,
        "price": fmt_money(p.price), "currency": "USD", "stock": p.stock,
        "in_stock": p.stock > 0, "low_stock": is_low_stock(p),
        "dimensions": {"width_cm": p.width_cm, "height_cm": p.height_cm, "depth_cm": p.depth_cm},
        "colors": list(p.colors or []), "material": p.material, "style": p.style,
        "room_types": list(p.room_types or []),
        "primary_image": product_images.image_url(primary) if primary else None,
        "images": [product_images.image_to_dict(i) for i in product_images.sorted_images(p)],
    }
    if detail:
        data["description"] = p.description
        data["active"] = p.active
    return data


def product_to_admin(p: Product) -> dict:
    """ProductAdmin (doc 04 v0.2) = producto público con detalle + active, images, created_at, updated_at."""
    from app.core.timeutil import as_utc

    data = product_to_public(p, detail=True)
    data["category_slug"] = p.category.slug if p.category else None
    data["created_at"] = as_utc(p.created_at).isoformat() if p.created_at else None
    data["updated_at"] = as_utc(p.updated_at).isoformat() if p.updated_at else None
    return data


def product_to_tool(p: Product) -> dict:
    """Formato compacto para herramientas del agente (doc 05 §3)."""
    return {
        "ref": p.sku, "name": p.name, "price_usd": fmt_money(p.price), "stock": p.stock, "dims_cm": dims_text(p),
        "colors": list(p.colors or []), "category": p.category.slug if p.category else None, "material": p.material,
    }
