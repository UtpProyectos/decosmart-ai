"""Room-simulation lifecycle, quotas, cache and storage."""

import re
from dataclasses import dataclass
from hashlib import sha256

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agent.prompts import build_simulation_prompt
from app.ai.provider import get_provider
from app.automation.events import emit
from app.core import pricing
from app.core.config import get_settings
from app.core.timeutil import local_day_bounds_utc, now_utc, today_local
from app.imaging.pipeline import optimize_input, optimize_output
from app.models import Customer, Simulation, SimulationRating
from app.services import budget, product_images
from app.services.errors import log_error
from app.storage import get_storage

_DIMS = re.compile(r"^\s*(\d+(?:[.,]\d+)?)\s*[x×*,]\s*(\d+(?:[.,]\d+)?)"
                   r"(?:\s*[x×*,]\s*(\d+(?:[.,]\d+)?))?\s*$", re.I)


@dataclass
class SimulationResult:
    simulation: Simulation
    status: str
    data: bytes | None = None
    reason: str | None = None
    reused: bool = False

    @property
    def output(self) -> bytes | None:
        return self.data


def parse_dimensions(text: str) -> tuple[int, int, int | None, str | None]:
    dimensions, sep, hint = text.partition(";")
    match = _DIMS.match(dimensions)
    if not match:
        raise ValueError("Usa el formato 300 x 250 o 300 x 250 x 400")
    raw = [float(v.replace(",", ".")) if v else None for v in match.groups()]
    values = [round(v * 100) if v is not None and v < 10 else round(v) if v is not None else None for v in raw]
    if any(v is not None and (v < 50 or v > 5000) for v in values):
        raise ValueError("Las medidas del ambiente no son válidas")
    clean_hint = None
    if sep and hint.strip():
        clean_hint = re.sub(r"[^\w áéíóúüñ,.-]", "", hint.strip(), flags=re.I)[:80].strip()
    return values[0], values[1], values[2], clean_hint


def _quota_reason(db: Session, customer: Customer) -> str | None:
    settings = get_settings()
    if (customer.simulations_used or 0) >= settings.max_simulations_per_customer:
        return "customer"
    start, end = local_day_bounds_utc(today_local())
    daily = db.scalar(select(func.count(Simulation.id)).where(
        Simulation.status == "completed", Simulation.created_at >= start, Simulation.created_at < end)) or 0
    if daily >= settings.max_simulations_per_day:
        return "daily"
    if settings.ai_mode == "live" and not budget.can_spend(
            db, pricing.estimate_image_edit(settings.openai_image_model, settings.image_quality, settings.image_size,
                                            input_images=1 + max(1, settings.simulation_max_reference_images))):
        return "budget"
    return None


def prepare(db: Session, customer: Customer, product) -> Simulation:
    reason = _quota_reason(db, customer)
    sim = Simulation(customer_id=customer.id, product_id=product.id,
                     status="blocked_quota" if reason else "awaiting_photo")
    if reason:
        sim.error_message = reason
    db.add(sim)
    db.commit()
    return sim


def attach_photo(db: Session, simulation_id: int, raw: bytes) -> Simulation:
    sim = db.get(Simulation, simulation_id)
    if sim is None:
        raise ValueError("Simulación no encontrada")
    data, meta = optimize_input(raw)
    key = f"customers/{sim.customer_id}/inputs/{sim.id}-{meta.sha256[:16]}.jpg"
    get_storage().put(key, data, "image/jpeg")
    sim.input_key, sim.input_hash, sim.input_bytes = key, meta.sha256, meta.bytes
    sim.status = "awaiting_dimensions"
    db.commit()
    return sim


def set_dimensions(db: Session, simulation_id: int, text: str) -> Simulation:
    sim = db.get(Simulation, simulation_id)
    if sim is None:
        raise ValueError("Simulación no encontrada")
    width, height, depth, hint = parse_dimensions(text)
    sim.room_width_cm, sim.room_height_cm, sim.room_depth_cm = width, height, depth
    sim.placement_hint = hint or "contra la pared principal"
    sim.status = "awaiting_confirmation"
    db.commit()
    return sim


def width_warning(sim: Simulation) -> str | None:
    if sim.room_width_cm and sim.product.width_cm > sim.room_width_cm:
        return (f"Según las medidas, el mueble ({sim.product.width_cm} cm) es más ancho que el espacio "
                f"({sim.room_width_cm} cm). ¿Deseas simular de todas formas?")
    return None


def _references(db: Session, sim: Simulation) -> list[bytes]:
    if not get_settings().simulation_use_product_reference:
        return []
    return product_images.reference_images(db, sim.product)


def _cache_key(sim: Simulation, variant: int, references: list[bytes] | None = None) -> str:
    s = get_settings()
    refs = references or []
    # Huella de las referencias: cambian si el admin marca/reordena/sube otras imágenes del mueble.
    ref_digest = sha256(b"".join(sha256(r).digest() for r in refs)).hexdigest()[:16] if refs else ""
    raw = "|".join(str(x or "") for x in (sim.input_hash, sim.product_id, sim.room_width_cm,
                    sim.room_height_cm, sim.room_depth_cm, sim.placement_hint, s.openai_image_model,
                    s.image_size, s.image_quality, variant, f"refs={len(refs)}", ref_digest))
    return sha256(raw.encode()).hexdigest()


def _blocked(db: Session, sim: Simulation, reason: str) -> SimulationResult:
    sim.status, sim.error_message = "blocked_quota", reason
    db.commit()
    return SimulationResult(sim, sim.status, reason=reason)


def run(db: Session, simulation_id: int, *, variant: int = 0) -> SimulationResult:
    sim = db.get(Simulation, simulation_id)
    if sim is None:
        raise ValueError("Simulación no encontrada")
    reason = _quota_reason(db, sim.customer)
    if reason:
        return _blocked(db, sim, reason)
    if not sim.input_key or not sim.input_hash or not sim.room_width_cm or not sim.room_height_cm:
        raise ValueError("La simulación no está lista para generarse")
    references = _references(db, sim)
    sim.cache_key = _cache_key(sim, variant, references)
    cached = db.scalar(select(Simulation).where(Simulation.status == "completed",
                       Simulation.cache_key == sim.cache_key, Simulation.id != sim.id).order_by(Simulation.id))
    storage = get_storage()
    if cached and cached.output_key and storage.exists(cached.output_key):
        sim.output_key, sim.output_bytes = cached.output_key, cached.output_bytes
        sim.reused_from_id, sim.cost_usd = cached.id, 0
        sim.status, sim.completed_at = "completed", now_utc()
        emit(db, "simulation.completed", "simulation", sim.id, sim.customer_id,
             {"reused": True, "reused_from_id": cached.id})
        db.commit()
        return SimulationResult(sim, sim.status, storage.get(sim.output_key), reused=True)
    settings = get_settings()
    sim.status = "processing"
    size = settings.image_size
    room = storage.get(sim.input_key)
    if size == "auto":
        from io import BytesIO

        from PIL import Image

        image = Image.open(BytesIO(room))
        size = "1536x1024" if image.width >= image.height else "1024x1536"
    sim.model, sim.size, sim.quality = settings.openai_image_model, size, settings.image_quality
    sim.prompt = build_simulation_prompt(sim.product, sim)
    db.commit()
    try:
        provider = get_provider(db, customer_id=sim.customer_id, simulation_id=sim.id)
        if settings.ai_mode == "live" and settings.openai_moderation and sim.placement_hint:
            if not provider.moderate(sim.placement_hint):
                sim.placement_hint = "contra la pared principal"
                sim.prompt = build_simulation_prompt(sim.product, sim)
        result = provider.edit_image(room, references, sim.prompt, size, settings.image_quality)
        if settings.store_full_output:
            sim.output_full_key = f"customers/{sim.customer_id}/outputs/{sim.id}-full.jpg"
            storage.put(sim.output_full_key, result.data, "image/jpeg")
        output, meta = optimize_output(result.data)
        sim.output_key = f"customers/{sim.customer_id}/outputs/{sim.id}.jpg"
        storage.put(sim.output_key, output, "image/jpeg" if settings.output_format == "JPEG" else "image/webp")
        sim.output_bytes = meta.bytes
        sim.cost_usd = (pricing.estimate_image_edit(settings.openai_image_model, settings.image_quality, size,
                                                     result.usage, input_images=1 + len(references))
                        if settings.ai_mode == "live" else 0)
        sim.status, sim.completed_at, sim.error_message = "completed", now_utc(), None
        sim.customer.simulations_used = (sim.customer.simulations_used or 0) + 1
        emit(db, "simulation.completed", "simulation", sim.id, sim.customer_id, {"reused": False})
        db.commit()
        return SimulationResult(sim, sim.status, output)
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        sim = db.get(Simulation, simulation_id)
        sim.status, sim.error_message = "failed", str(exc)[:1000]
        log_error(db, "simulation", exc.__class__.__name__, str(exc), {"simulation_id": simulation_id},
                  customer_id=sim.customer_id, commit=False)
        emit(db, "simulation.failed", "simulation", sim.id, sim.customer_id,
             {"error_type": exc.__class__.__name__})
        db.commit()
        return SimulationResult(sim, sim.status, reason="failed")


def rate(db: Session, simulation_id: int, score: int, customer: Customer) -> SimulationRating:
    if score not in range(1, 6):
        raise ValueError("La calificación debe estar entre 1 y 5")
    sim = db.get(Simulation, simulation_id)
    if sim is None or sim.customer_id != customer.id or sim.status != "completed":
        raise ValueError("Simulación no encontrada")
    rating = sim.rating or SimulationRating(simulation_id=sim.id)
    rating.score = score
    db.add(rating)
    db.flush()
    emit(db, "simulation.rated", "simulation", sim.id, customer.id, {"score": score})
    db.commit()
    return rating
