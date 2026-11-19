"""GET /media/{key}: archivos del storage local (solo STORAGE_BACKEND=local).

GET /api/images/{image_id}: imágenes de producto (doc 04 v0.2). Va en este router (sin rate limit) porque
una página de catálogo carga muchas imágenes a la vez; el rate limit de /api/* las bloquearía.
"""

import mimetypes

from fastapi import APIRouter, Depends, Response
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.errors import AppError
from app.models import ProductImage
from app.storage import InvalidKey, LocalStorage, get_storage

router = APIRouter(tags=["media"])


def _not_found() -> AppError:
    return AppError("NOT_FOUND", "Archivo no encontrado", 404)


@router.get("/media/{key:path}")
def get_media(key: str):
    if get_settings().storage_backend != "local":
        raise _not_found()
    storage = get_storage()
    if not isinstance(storage, LocalStorage):
        raise _not_found()
    try:
        path = storage.path_for(key)
    except InvalidKey:
        raise _not_found() from None
    if not path.is_file():
        raise _not_found()
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(path, media_type=media_type, headers={"Cache-Control": "private, max-age=600"})


def _image_not_found() -> AppError:
    return AppError("IMAGE_NOT_FOUND", "Imagen no encontrada", 404)


@router.get("/api/images/{image_id}")
def get_product_image(image_id: int, db: Session = Depends(get_db)):
    """s3 → 302 a URL prefirmada (10 min); local → bytes; imagen seed → 302 a su URL /static."""
    img = db.get(ProductImage, image_id)
    if img is None:
        raise _image_not_found()
    headers = {"Cache-Control": "public, max-age=300"}
    if not img.storage_key:
        if not img.url or img.url.startswith("/api/images/"):
            raise _image_not_found()
        return RedirectResponse(img.url, status_code=302, headers=headers)
    storage = get_storage()
    if get_settings().storage_backend == "s3":
        return RedirectResponse(storage.url(img.storage_key, expires=600), status_code=302, headers=headers)
    try:
        content = storage.get(img.storage_key)
    except (FileNotFoundError, InvalidKey):
        raise _image_not_found() from None
    return Response(content=content, media_type="image/jpeg", headers=headers)
