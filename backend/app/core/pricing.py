"""Tabla de precios OpenAI (USD) y estimadores. Ver CODEX_HANDOFF §5.6.

Revalidar en la página oficial antes de la demo y actualizar PRICING_VERIFIED_AT.
"""

from decimal import ROUND_HALF_UP, Decimal

PRICING_VERIFIED_AT = "2026-11-18"  # https://developers.openai.com/api/docs/pricing

# USD por 1M tokens
TEXT_MODELS: dict[str, dict[str, float]] = {
    "gpt-5.4-nano": {"input": 0.20, "cached_input": 0.02, "output": 1.25},
    "gpt-5.4-mini": {"input": 0.75, "cached_input": 0.075, "output": 4.50},
    "gpt-5-mini": {"input": 0.25, "cached_input": 0.025, "output": 2.00},
    "gpt-5-nano": {"input": 0.05, "cached_input": 0.005, "output": 0.40},
}
# Precio por imagen de salida (tabla oficial) como estimación previa y fallback.
IMAGE_OUTPUT_PER_IMAGE: dict[tuple[str, str, str], float] = {
    ("gpt-image-1-mini", "low", "1024x1024"): 0.005,
    ("gpt-image-2", "low", "1024x1024"): 0.006,
    ("gpt-image-1.5", "low", "1024x1024"): 0.009,
    ("gpt-image-1", "low", "1024x1024"): 0.011,
}
IMAGE_INPUT_SURCHARGE_USD = 0.006  # margen conservador por imágenes de entrada (edit)
DEFAULT_UNKNOWN_IMAGE_COST = 0.05  # si el modelo/tamaño no está en tabla → asumir caro

_SIX = Decimal("0.000001")


def _q(value: float | Decimal) -> Decimal:
    return Decimal(str(value)).quantize(_SIX, rounding=ROUND_HALF_UP)


def _rates(model: str) -> dict[str, float]:
    if model in TEXT_MODELS:
        return TEXT_MODELS[model]
    # Modelo desconocido → tarifa del más caro de la tabla (por campo).
    return {k: max(r[k] for r in TEXT_MODELS.values()) for k in ("input", "cached_input", "output")}


def estimate_chat(model: str, input_tokens: int = 0, cached_input_tokens: int = 0, output_tokens: int = 0) -> Decimal:
    """Costo USD de una llamada de chat.

    `input_tokens` sigue la semántica de OpenAI (incluye los cacheados); se cobran
    `input_tokens - cached_input_tokens` a tarifa normal y los cacheados a tarifa cached.
    """
    r = _rates(model)
    cached = max(cached_input_tokens or 0, 0)
    uncached = max((input_tokens or 0) - cached, 0)
    cost = (uncached * r["input"] + cached * r["cached_input"] + max(output_tokens or 0, 0) * r["output"]) / 1_000_000
    return _q(cost)


def estimate_image_edit(model: str, quality: str, size: str, usage: dict | None = None) -> Decimal:
    """Estimación conservadora: precio por imagen de salida + recargo por imágenes de entrada.

    `usage` se acepta por compatibilidad (los tokens se guardan aparte en api_usage); no altera la estimación.
    """
    per_image = IMAGE_OUTPUT_PER_IMAGE.get((model, quality, size), DEFAULT_UNKNOWN_IMAGE_COST)
    return _q(per_image + IMAGE_INPUT_SURCHARGE_USD)


def estimate_image_cost() -> Decimal:
    """Estimación con los parámetros configurados (OPENAI_IMAGE_MODEL / IMAGE_QUALITY / IMAGE_SIZE)."""
    from app.core.config import get_settings

    s = get_settings()
    return estimate_image_edit(s.openai_image_model, s.image_quality, s.image_size)
