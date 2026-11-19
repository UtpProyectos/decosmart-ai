"""Privacy-preserving image normalization for room simulations."""

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import get_settings


class ImageValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ImageMeta:
    width: int
    height: int
    bytes: int
    format: str
    sha256: str


def sha256_hex(data: bytes) -> str:
    return sha256(data).hexdigest()


def _open(raw: bytes, *, enforce_upload_limit: bool) -> Image.Image:
    settings = get_settings()
    if enforce_upload_limit and len(raw) > settings.max_upload_mb * 1024 * 1024:
        raise ImageValidationError("La imagen supera el tamaño máximo permitido")
    try:
        image = Image.open(BytesIO(raw))
        image.load()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ImageValidationError("El archivo no es una imagen válida") from exc
    image = ImageOps.exif_transpose(image)
    if min(image.size) < 320:
        raise ImageValidationError("La imagen debe tener al menos 320 px en su lado menor")
    return image.convert("RGB")


def _meta(data: bytes, image: Image.Image, fmt: str) -> ImageMeta:
    return ImageMeta(image.width, image.height, len(data), fmt, sha256_hex(data))


def optimize_input(raw: bytes) -> tuple[bytes, ImageMeta]:
    settings = get_settings()
    image = _open(raw, enforce_upload_limit=True)
    image.thumbnail((settings.input_max_side, settings.input_max_side), Image.Resampling.LANCZOS)
    output = BytesIO()
    image.save(
        output,
        format="JPEG",
        quality=settings.input_jpeg_quality,
        optimize=True,
        progressive=True,
        exif=b"",
    )
    data = output.getvalue()
    return data, _meta(data, image, "JPEG")


def optimize_output(raw: bytes) -> tuple[bytes, ImageMeta]:
    settings = get_settings()
    image = _open(raw, enforce_upload_limit=False)
    image.thumbnail((settings.output_max_side, settings.output_max_side), Image.Resampling.LANCZOS)
    target = settings.output_target_max_kb * 1024
    fmt = settings.output_format
    quality = settings.output_quality
    data = b""
    while quality >= 50:
        output = BytesIO()
        kwargs = {"format": fmt, "quality": quality, "optimize": True, "exif": b""}
        if fmt == "JPEG":
            kwargs["progressive"] = True
        image.save(output, **kwargs)
        data = output.getvalue()
        if len(data) <= target or quality == 50:
            break
        quality = max(50, quality - 8)
    return data, _meta(data, image, fmt)
