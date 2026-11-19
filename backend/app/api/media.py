"""GET /media/{key}: sirve archivos del storage local (solo STORAGE_BACKEND=local)."""

import mimetypes

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.core.config import get_settings
from app.core.errors import AppError
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
