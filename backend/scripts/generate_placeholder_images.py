"""Genera imágenes placeholder de producto (siluetas simples sobre fondo neutro).

Uso: python scripts/generate_placeholder_images.py
Reemplazar por fotos reales del producto (fondo neutro, ≤768 px) antes de la demo final.
"""

import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "seed"
OUT = SEED / "images"
W, H = 768, 576
BG = (246, 243, 238)
FLOOR = (225, 219, 210)


def _hex(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _shade(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c)


def draw(category: str, color) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, int(H * 0.78), W, H], fill=FLOOR)
    dark, wood = _shade(color, 0.7), (150, 110, 75)
    if category == "sofas":
        d.rounded_rectangle([130, 220, 640, 330], 30, fill=dark)  # respaldo
        d.rounded_rectangle([110, 300, 660, 400], 25, fill=color)  # asiento
        d.rounded_rectangle([95, 260, 165, 410], 20, fill=dark)
        d.rounded_rectangle([605, 260, 675, 410], 20, fill=dark)
        for x in (140, 620):
            d.rectangle([x, 405, x + 12, 450], fill=wood)
    elif category == "mesas":
        d.rectangle([170, 300, 600, 325], fill=color)
        d.rectangle([200, 390, 570, 402], fill=_shade(color, 0.85))
        for x in (190, 565):
            d.polygon([(x, 325), (x + 16, 325), (x + 10, 450), (x + 6, 450)], fill=_shade(color, 0.75))
    elif category == "sillas":
        for ox in (180, 430):
            d.rounded_rectangle([ox, 170, ox + 160, 290], 40, fill=color, outline=(200, 200, 200), width=3)
            d.rounded_rectangle([ox - 5, 285, ox + 165, 330], 18, fill=color, outline=(200, 200, 200), width=3)
            for x in (ox + 10, ox + 140):
                d.line([(x, 330), (x - 10 if x < ox + 80 else x + 10, 450)], fill=wood, width=9)
    elif category == "camas":
        d.rounded_rectangle([150, 150, 620, 330], 20, fill=color)
        d.rectangle([120, 320, 650, 400], fill=_shade(color, 0.85))
        d.rounded_rectangle([140, 290, 630, 345], 15, fill=(240, 240, 235))
        d.rounded_rectangle([180, 255, 340, 300], 15, fill=(250, 250, 248))
        d.rounded_rectangle([430, 255, 590, 300], 15, fill=(250, 250, 248))
        for x in (130, 630):
            d.rectangle([x, 400, x + 12, 445], fill=dark)
    elif category == "almacenamiento":
        x0, y0, cw, ch = 234, 60, 150, 95
        d.rectangle([x0 - 10, y0 - 10, x0 + 2 * cw + 10, y0 + 4 * ch + 10], fill=_shade(color, 0.85))
        for r in range(4):
            for c in range(2):
                d.rectangle([x0 + c * cw + 6, y0 + r * ch + 6, x0 + (c + 1) * cw - 6, y0 + (r + 1) * ch - 6],
                            fill=_shade(color, 0.7))
    elif category == "escritorios":
        d.rectangle([140, 260, 630, 285], fill=(190, 150, 105))
        d.rectangle([520, 285, 630, 300], fill=(190, 150, 105))
        for x in (150, 610):
            d.rectangle([x, 285, x + 10, 450], fill=color)
        d.line([(150, 440), (620, 440)], fill=color, width=8)
    return img


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    data = json.loads((SEED / "products.json").read_text(encoding="utf-8"))
    for p in data["products"]:
        img = draw(p["category"], _hex(p["color_hex"]))
        img.save(OUT / p["image"], "JPEG", quality=85, optimize=True)
        print("ok", p["image"])


if __name__ == "__main__":
    main()
