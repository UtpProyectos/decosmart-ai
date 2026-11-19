"""Gestión admin de productos e imágenes (doc 04, Ampliación v0.2).

Las funciones hacen commit al terminar una operación completa (como el resto de servicios admin).
"""

import re
import uuid
from io import BytesIO

from PIL import Image, UnidentifiedImageError
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.errors import AppError
from app.imaging.pipeline import ImageValidationError, optimize_input
from app.models import Category, Product, ProductImage
from app.services import catalog
from app.services.product_images import sorted_images
from app.storage import get_storage

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_FILES_PER_UPLOAD = 8

UploadFileData = tuple[str, bytes, str | None]  # (filename, contenido, content_type)


# ---------- Productos ----------
def slugify(text: str) -> str:
    base = catalog.normalize(text)
    return re.sub(r"[^a-z0-9]+", "-", base).strip("-")[:160].strip("-") or "producto"


def _not_found() -> AppError:
    return AppError("PRODUCT_NOT_FOUND", "Producto no encontrado", 404)


def _image_not_found() -> AppError:
    return AppError("IMAGE_NOT_FOUND", "Imagen no encontrada", 404)


def get_product_admin(db: Session, product_id: int) -> Product:
    p = db.scalar(select(Product).options(selectinload(Product.images), selectinload(Product.category))
                  .where(Product.id == product_id).execution_options(populate_existing=True))
    if p is None:
        raise _not_found()
    return p


def list_products(db: Session, include_inactive: bool = True) -> list[Product]:
    stmt = select(Product).options(selectinload(Product.images), selectinload(Product.category))
    if not include_inactive:
        stmt = stmt.where(Product.active.is_(True))
    return list(db.scalars(stmt.order_by(Product.id)).all())


def _category(db: Session, slug: str) -> Category:
    cat = db.scalar(select(Category).where(Category.slug == slug))
    if cat is None:
        raise AppError("VALIDATION_ERROR", "Categoría desconocida", 422,
                       {"errors": [{"loc": ["body", "category_slug"], "msg": f"Categoría '{slug}' no existe"}]})
    return cat


def _check_sku(db: Session, sku: str, exclude_id: int | None = None) -> None:
    stmt = select(Product.id).where(func.upper(Product.sku) == sku.upper())
    if exclude_id is not None:
        stmt = stmt.where(Product.id != exclude_id)
    if db.scalar(stmt) is not None:
        raise AppError("SKU_TAKEN", "Ya existe un producto con ese SKU", 409, {"sku": sku})


def _slug_taken(db: Session, slug: str, exclude_id: int | None = None) -> bool:
    stmt = select(Product.id).where(Product.slug == slug)
    if exclude_id is not None:
        stmt = stmt.where(Product.id != exclude_id)
    return db.scalar(stmt) is not None


def _auto_slug(db: Session, name: str, exclude_id: int | None = None) -> str:
    base = slugify(name)
    slug, n = base, 2
    while _slug_taken(db, slug, exclude_id):
        suffix = f"-{n}"
        slug = base[: 160 - len(suffix)] + suffix
        n += 1
    return slug


def _check_slug(db: Session, slug: str, exclude_id: int | None = None) -> None:
    if _slug_taken(db, slug, exclude_id):
        raise AppError("SLUG_TAKEN", "Ya existe un producto con ese slug", 409, {"slug": slug})


def create_product(db: Session, data: dict) -> Product:
    data = dict(data)
    sku = data["sku"].strip()
    _check_sku(db, sku)
    cat = _category(db, data.pop("category_slug"))
    slug = data.pop("slug", None)
    if slug:
        _check_slug(db, slug)
    else:
        slug = _auto_slug(db, data["name"])
    data["sku"] = sku
    product = Product(**data, slug=slug, category_id=cat.id, low_stock_notified=False)
    db.add(product)
    db.flush()
    catalog.evaluate_low_stock(db, product)
    db.commit()
    return get_product_admin(db, product.id)


def update_product(db: Session, product: Product, changes: dict) -> Product:
    changes = dict(changes)
    if "sku" in changes:
        changes["sku"] = changes["sku"].strip()
        _check_sku(db, changes["sku"], product.id)
    if "category_slug" in changes:
        product.category_id = _category(db, changes.pop("category_slug")).id
    if "slug" in changes:
        _check_slug(db, changes["slug"], product.id)
    for field, value in changes.items():
        setattr(product, field, value)
    db.flush()
    catalog.evaluate_low_stock(db, product)  # emite product.low_stock o resetea el flag al reponer
    db.commit()
    return get_product_admin(db, product.id)


def deactivate_product(db: Session, product: Product) -> None:
    product.active = False
    db.commit()


# ---------- Imágenes ----------
def _invalid(message: str, filename: str | None = None) -> AppError:
    return AppError("INVALID_IMAGE", message, 422, {"filename": filename} if filename else {})


def _validate_upload(filename: str, raw: bytes) -> None:
    settings = get_settings()
    if not raw:
        raise _invalid("El archivo está vacío", filename)
    if len(raw) > settings.max_upload_mb * 1024 * 1024:
        raise _invalid(f"La imagen supera {settings.max_upload_mb} MB", filename)
    try:
        with Image.open(BytesIO(raw)) as probe:
            fmt = (probe.format or "").upper()
            probe.verify()
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as exc:
        raise _invalid("El archivo no es una imagen válida", filename) from exc
    if fmt not in ALLOWED_FORMATS:
        raise _invalid("Formato no permitido: usa JPG, PNG o WEBP", filename)


def _ensure_single_primary(product: Product, primary: ProductImage | None = None) -> None:
    images = sorted_images(product)
    if not images:
        return
    if primary is None:
        primary = next((i for i in images if i.is_primary), images[0])
    for img in images:
        img.is_primary = img is primary


def add_images(
    db: Session, product: Product, files: list[UploadFileData], alt: str | None = None, is_reference: bool = False
) -> list[ProductImage]:
    settings = get_settings()
    if not files:
        raise _invalid("Debes adjuntar al menos una imagen")
    if len(files) > MAX_FILES_PER_UPLOAD:
        raise AppError("TOO_MANY_IMAGES", f"Máximo {MAX_FILES_PER_UPLOAD} archivos por subida", 422,
                       {"max_per_upload": MAX_FILES_PER_UPLOAD})
    existing = len(product.images)
    if existing + len(files) > settings.max_images_per_product:
        raise AppError("TOO_MANY_IMAGES", f"Máximo {settings.max_images_per_product} imágenes por producto", 422,
                       {"max": settings.max_images_per_product, "current": existing})
    # Validar y optimizar todo antes de escribir nada (todo o nada).
    prepared = []
    for filename, raw, _content_type in files:
        _validate_upload(filename, raw)
        try:
            data, meta = optimize_input(raw)
        except ImageValidationError as exc:
            raise _invalid(str(exc), filename) from exc
        prepared.append((data, meta))

    storage = get_storage()
    next_order = max((i.sort_order or 0 for i in product.images), default=-1) + 1
    had_images = existing > 0
    created: list[ProductImage] = []
    written: list[str] = []
    try:
        for idx, (data, meta) in enumerate(prepared):
            key = f"products/{product.id}/{uuid.uuid4().hex}.jpg"
            storage.put(key, data, "image/jpeg")
            written.append(key)
            img = ProductImage(
                product_id=product.id, url="", alt=(alt or None), storage_key=key,
                is_primary=not had_images and idx == 0, is_reference=bool(is_reference),
                sort_order=next_order + idx, width=meta.width, height=meta.height, bytes=meta.bytes,
            )
            product.images.append(img)
            created.append(img)
        db.flush()
        for img in created:
            img.url = f"/api/images/{img.id}"
        _ensure_single_primary(product)
        db.commit()
    except Exception:
        db.rollback()
        for key in written:
            try:
                storage.delete(key)
            except Exception:  # noqa: BLE001
                pass
        raise
    return created


def get_image(db: Session, product: Product, image_id: int) -> ProductImage:
    img = next((i for i in product.images if i.id == image_id), None)
    if img is None:
        raise _image_not_found()
    return img


def update_image(db: Session, product: Product, image_id: int, changes: dict) -> ProductImage:
    img = get_image(db, product, image_id)
    if "alt" in changes:
        img.alt = changes["alt"] or None
    if changes.get("is_reference") is not None:
        img.is_reference = bool(changes["is_reference"])
    if changes.get("sort_order") is not None:
        img.sort_order = int(changes["sort_order"])
    if changes.get("is_primary") is True:
        _ensure_single_primary(product, img)
    elif changes.get("is_primary") is False and img.is_primary:
        # Debe quedar exactamente una principal: pasa a la primera de las demás por sort_order.
        others = [i for i in sorted_images(product) if i is not img]
        if others:
            _ensure_single_primary(product, others[0])
    db.commit()
    return img


def reorder_images(db: Session, product: Product, image_ids: list[int]) -> list[ProductImage]:
    current = {i.id: i for i in product.images}
    if len(set(image_ids)) != len(image_ids) or set(image_ids) != set(current):
        raise AppError("VALIDATION_ERROR", "image_ids debe contener exactamente las imágenes del producto", 422,
                       {"errors": [{"loc": ["body", "image_ids"], "msg": "Lista de imágenes inválida"}]})
    for pos, image_id in enumerate(image_ids):
        current[image_id].sort_order = pos
    db.commit()
    return sorted_images(product)


def delete_image(db: Session, product: Product, image_id: int) -> None:
    img = get_image(db, product, image_id)
    key = img.storage_key
    was_primary = img.is_primary
    product.images.remove(img)
    db.delete(img)
    if was_primary:
        _ensure_single_primary(product, sorted_images(product)[0] if product.images else None)
    db.commit()
    if key:
        try:
            get_storage().delete(key)
        except Exception:  # noqa: BLE001
            pass
