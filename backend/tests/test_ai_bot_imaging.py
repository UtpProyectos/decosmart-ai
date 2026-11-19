from io import BytesIO

import pytest
from PIL import Image

from app.core.config import get_settings
from app.imaging.pipeline import ImageValidationError, optimize_input, optimize_output, sha256_hex


def image_bytes(size=(1600, 900), fmt="JPEG", color="navy", exif=None):
    out = BytesIO()
    Image.new("RGB", size, color).save(out, fmt, quality=95, exif=exif or b"")
    return out.getvalue()


def test_optimize_input_resizes_and_keeps_aspect():
    data, meta = optimize_input(image_bytes())
    assert (meta.width, meta.height) == (1280, 720)
    assert meta.bytes == len(data) and meta.sha256 == sha256_hex(data)


def test_optimize_input_strips_exif():
    exif = Image.Exif()
    exif[0x010E] = "private"
    data, _ = optimize_input(image_bytes(exif=exif.tobytes()))
    assert not Image.open(BytesIO(data)).getexif()


def test_optimize_output_bounds(monkeypatch):
    monkeypatch.setattr(get_settings(), "output_target_max_kb", 30)
    data, meta = optimize_output(image_bytes((1400, 1000), color=(120, 50, 200)))
    assert max(meta.width, meta.height) <= 768
    assert len(data) <= 30 * 1024


@pytest.mark.parametrize("raw", [b"", b"hello", b"\x89PNGbroken"])
def test_rejects_invalid_images(raw):
    with pytest.raises(ImageValidationError):
        optimize_input(raw)


@pytest.mark.parametrize("size", [(319, 500), (500, 319)])
def test_rejects_tiny_short_side(size):
    with pytest.raises(ImageValidationError):
        optimize_input(image_bytes(size))


def test_rejects_large_upload(monkeypatch):
    monkeypatch.setattr(get_settings(), "max_upload_mb", 0)
    with pytest.raises(ImageValidationError):
        optimize_input(image_bytes((400, 400)))


def test_sha256_is_deterministic():
    assert sha256_hex(b"abc") == sha256_hex(b"abc")
    assert sha256_hex(b"abc") != sha256_hex(b"abd")
