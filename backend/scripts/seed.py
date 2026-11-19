"""Seed idempotente del catálogo. Uso: python -m scripts.seed"""

import json
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models import Category, Product, ProductImage

SEED_DIR = Path(__file__).resolve().parents[1] / "seed"


def seed(db: Session) -> int:
    data = json.loads((SEED_DIR / "products.json").read_text(encoding="utf-8"))
    cats: dict[str, Category] = {}
    for c in data["categories"]:
        cat = db.scalar(select(Category).where(Category.slug == c["slug"]))
        if not cat:
            cat = Category(slug=c["slug"], name=c["name"], description=c.get("description"))
            db.add(cat)
        cats[c["slug"]] = cat
    db.flush()

    created = 0
    for p in data["products"]:
        if db.scalar(select(Product).where(Product.sku == p["sku"])):
            continue
        prod = Product(
            sku=p["sku"], category_id=cats[p["category"]].id, name=p["name"], slug=p["slug"],
            description=p["description"], price=Decimal(p["price"]), stock=p["stock"],
            width_cm=p["width_cm"], height_cm=p["height_cm"], depth_cm=p["depth_cm"],
            colors=p["colors"], material=p.get("material"), style=p.get("style"),
            room_types=p.get("room_types", []),
            # Las imágenes de catálogo viajan con el repo/imagen Docker (seed/images) y se sirven en /static.
            reference_image_key=f"seed/images/{p['image']}",
        )
        prod.images.append(ProductImage(url=f"/static/products/{p['image']}", alt=p["name"], is_primary=True))
        db.add(prod)
        created += 1
    db.commit()
    return created


def main() -> None:
    with SessionLocal() as db:
        print(f"Productos creados: {seed(db)}")


if __name__ == "__main__":
    main()
