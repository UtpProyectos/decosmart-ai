"""Lectura de imágenes de producto (subidas a storage o seed en /static) y selección de referencias.

Compartido por el endpoint público `/api/images/{id}`, el bot de Telegram y el simulador.
"""

import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Product, ProductImage
from app.storage import get_storage

log = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parents[2]
SEED_IMAGES_DIR = BACKEND_ROOT / "seed" / "images"
STATIC_PREFIX = "/static/products/"


def image_url(image: ProductImage) -> str:
    """URL pública relativa: `/api/images/{id}` para subidas; la ruta `/static/...` para las seed."""
    if image.storage_key and image.id is not None:
        return f"/api/images/{image.id}"
    return image.url


def image_to_dict(image: ProductImage) -> dict:
    return {
        "id": image.id, "url": image_url(image), "alt": image.alt, "is_primary": bool(image.is_primary),
        "is_reference": bool(image.is_reference), "sort_order": image.sort_order or 0,
        "width": image.width, "height": image.height,
    }


def sorted_images(product: Product) -> list[ProductImage]:
    return sorted(product.images, key=lambda i: (i.sort_order or 0, i.id or 0))


def primary_image(product: Product) -> ProductImage | None:
    images = sorted_images(product)
    for img in images:
        if img.is_primary:
            return img
    return images[0] if images else None


def _seed_path(url: str) -> Path | None:
    if not url or not url.startswith(STATIC_PREFIX):
        return None
    name = url[len(STATIC_PREFIX):]
    if not name or "/" in name or "\\" in name or name.startswith("."):
        return None
    path = (SEED_IMAGES_DIR / name).resolve()
    if not path.is_relative_to(SEED_IMAGES_DIR.resolve()) or not path.is_file():
        return None
    return path


def load_image_bytes(db: Session | None, image: ProductImage | None) -> bytes | None:
    """Bytes de la imagen (storage o seed). None si no se puede leer; nunca lanza."""
    if image is None:
        return None
    try:
        if image.storage_key:
            return get_storage().get(image.storage_key)
        path = _seed_path(image.url)
        return path.read_bytes() if path else None
    except Exception as exc:  # noqa: BLE001
        log.warning("No se pudo leer la imagen %s: %s", image.id, exc)
        return None


def _reference_key_bytes(product: Product) -> bytes | None:
    key = product.reference_image_key
    if not key:
        return None
    path = (BACKEND_ROOT / key).resolve()
    if path.is_relative_to(BACKEND_ROOT) and path.is_file():
        return path.read_bytes()
    return None


def reference_images(db: Session | None, product: Product, limit: int | None = None) -> list[bytes]:
    """Referencias del mueble para la simulación (doc 04 v0.2).

    `is_reference` por `sort_order` (hasta `limit`); si no hay, la principal; si no, `reference_image_key`.
    """
    limit = get_settings().simulation_max_reference_images if limit is None else limit
    if limit <= 0:
        return []
    refs = [img for img in sorted_images(product) if img.is_reference]
    out = [b for b in (load_image_bytes(db, img) for img in refs) if b][:limit]
    if out:
        return out
    primary = load_image_bytes(db, primary_image(product))
    if primary:
        return [primary]
    fallback = _reference_key_bytes(product)
    return [fallback] if fallback else []
