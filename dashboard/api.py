"""Cliente HTTP del dashboard contra la API admin de DECOSMART AI.

Estructura en tres capas (todo lo que dependa de la forma exacta del JSON vive aquí):

1. ``fetch_json``: GET con ``X-Admin-Key`` y timeout; nunca lanza excepciones.
2. ``parse_*``: adaptadores puros que normalizan la respuesta (claves faltantes,
   dinero como string, listas envueltas en ``{"items": [...]}``) a estructuras
   estables que consumen las páginas.
3. ``get_*``: envoltorios con ``st.cache_data(ttl=30)`` para las páginas.

Las capas 1 y 2 no requieren el runtime de Streamlit, por lo que se prueban con pytest.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import requests

try:  # Streamlit es opcional para los tests de los adaptadores.
    import streamlit as st

    _cache = st.cache_data(ttl=30, show_spinner=False)
except Exception:  # pragma: no cover - solo si streamlit no está instalado
    st = None

    def _cache(func):  # type: ignore[no-redef]
        return func


TIMEOUT_SECONDS = 10
DEFAULT_API_URL = "http://localhost:8000"


@dataclass
class ApiResult:
    """Resultado de una llamada: datos ya normalizados + error legible (o None)."""

    data: Any = None
    error: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.error is None


# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------


def api_base_url() -> str:
    return (os.getenv("DASHBOARD_API_URL") or DEFAULT_API_URL).rstrip("/")


def admin_key() -> str:
    return os.getenv("DASHBOARD_ADMIN_KEY", "")


# ---------------------------------------------------------------------------
# Transporte
# ---------------------------------------------------------------------------


def fetch_json(path: str, params: dict[str, Any] | None = None, admin: bool = True) -> tuple[Any, str | None]:
    """GET ``path`` y devuelve ``(json, error)``. Nunca lanza excepciones."""
    url = f"{api_base_url()}{path}"
    headers = {"Accept": "application/json"}
    if admin:
        headers["X-Admin-Key"] = admin_key()
    clean_params = {k: v for k, v in (params or {}).items() if v not in (None, "")}
    try:
        resp = requests.get(url, params=clean_params, headers=headers, timeout=TIMEOUT_SECONDS)
    except requests.Timeout:
        return None, f"La API no respondió a tiempo ({TIMEOUT_SECONDS} s): {path}"
    except requests.RequestException as exc:
        return None, f"No se pudo conectar con la API ({api_base_url()}): {exc.__class__.__name__}"

    if resp.status_code == 401:
        return None, "La API rechazó la clave de administrador (401). Revisa DASHBOARD_ADMIN_KEY."
    if resp.status_code == 404:
        return None, f"Endpoint no disponible todavía (404): {path}"
    if resp.status_code >= 400:
        message = ""
        try:
            message = resp.json().get("error", {}).get("message", "")
        except Exception:
            pass
        return None, f"Error {resp.status_code} en {path}" + (f": {message}" if message else "")
    try:
        return resp.json(), None
    except ValueError:
        return None, f"Respuesta no JSON en {path}"


# ---------------------------------------------------------------------------
# Utilidades de normalización
# ---------------------------------------------------------------------------


def to_float(value: Any, default: float = 0.0) -> float:
    """Convierte números o strings decimales (``"0.4123"``) a float."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def to_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def as_items(raw: Any) -> tuple[list[dict[str, Any]], int]:
    """Acepta ``[...]`` o ``{"items": [...], "total": n}`` y devuelve ``(items, total)``."""
    if isinstance(raw, list):
        items = raw
        total = len(raw)
    elif isinstance(raw, dict):
        items = raw.get("items") or raw.get("data") or []
        total = to_int(raw.get("total"), len(items)) if isinstance(items, list) else 0
    else:
        return [], 0
    if not isinstance(items, list):
        return [], 0
    return [i for i in items if isinstance(i, dict)], total


# ---------------------------------------------------------------------------
# Adaptadores puros (una función por endpoint)
# ---------------------------------------------------------------------------

SUMMARY_INT_KEYS = (
    "conversations_total",
    "unique_customers",
    "inquiries_total",
    "quotes_total",
    "quotes_accepted",
    "orders_total",
    "orders_completed",
    "simulations_total",
    "simulations_failed",
    "simulations_reused",
    "ratings_count",
    "errors_total",
)


def empty_summary() -> dict[str, Any]:
    data: dict[str, Any] = {k: 0 for k in SUMMARY_INT_KEYS}
    data.update({"avg_rating": None, "api_cost_usd": 0.0, "budget_usd": 0.0, "budget_used_pct": 0.0, "ai_mode": "—"})
    return data


def parse_summary(raw: Any) -> dict[str, Any]:
    data = empty_summary()
    if not isinstance(raw, dict):
        return data
    for key in SUMMARY_INT_KEYS:
        data[key] = to_int(raw.get(key))
    rating = raw.get("avg_rating")
    data["avg_rating"] = None if rating is None else round(to_float(rating), 2)
    data["api_cost_usd"] = to_float(raw.get("api_cost_usd"))
    data["budget_usd"] = to_float(raw.get("budget_usd"))
    pct = raw.get("budget_used_pct")
    if pct is None and data["budget_usd"] > 0:
        pct = data["api_cost_usd"] / data["budget_usd"] * 100
    data["budget_used_pct"] = round(to_float(pct), 2)
    data["ai_mode"] = str(raw.get("ai_mode") or "—")
    return data


DAILY_KEYS = ("conversations", "inquiries", "quotes", "orders", "simulations")


def parse_daily(raw: Any) -> list[dict[str, Any]]:
    items, _ = as_items(raw)
    rows = []
    for item in items:
        date = item.get("date") or item.get("day")
        if not date:
            continue
        row: dict[str, Any] = {"date": str(date)[:10]}
        for key in DAILY_KEYS:
            row[key] = to_int(item.get(key))
        rows.append(row)
    rows.sort(key=lambda r: r["date"])
    return rows


def parse_top_products(raw: Any) -> list[dict[str, Any]]:
    items, _ = as_items(raw)
    rows = []
    for item in items:
        rows.append(
            {
                "product_id": item.get("product_id", item.get("id")),
                "sku": item.get("sku") or "",
                "name": item.get("name") or item.get("product_name") or f"Producto {item.get('product_id', '?')}",
                "count": to_int(item.get("count", item.get("total", item.get("quantity")))),
            }
        )
    rows.sort(key=lambda r: r["count"], reverse=True)
    return rows


def _breakdown(raw: Any, label: str) -> list[dict[str, Any]]:
    items, _ = as_items(raw)
    return [
        {
            label: str(i.get(label) or "desconocido"),
            "cost_usd": to_float(i.get("cost_usd")),
            "calls": to_int(i.get("calls")),
        }
        for i in items
    ]


def empty_usage() -> dict[str, Any]:
    return {
        "total_usd": 0.0,
        "budget_usd": 0.0,
        "budget_used_pct": 0.0,
        "by_operation": [],
        "by_model": [],
        "by_day": [],
        "pricing_verified_at": None,
        "ai_mode": "—",
    }


def parse_usage(raw: Any) -> dict[str, Any]:
    data = empty_usage()
    if not isinstance(raw, dict):
        return data
    data["total_usd"] = to_float(raw.get("total_usd", raw.get("api_cost_usd")))
    data["budget_usd"] = to_float(raw.get("budget_usd"))
    pct = raw.get("budget_used_pct")
    if pct is None and data["budget_usd"] > 0:
        pct = data["total_usd"] / data["budget_usd"] * 100
    data["budget_used_pct"] = round(to_float(pct), 2)
    data["by_operation"] = _breakdown(raw.get("by_operation"), "operation")
    data["by_model"] = _breakdown(raw.get("by_model"), "model")
    by_day, _ = as_items(raw.get("by_day"))
    data["by_day"] = sorted(
        ({"date": str(d.get("date"))[:10], "cost_usd": to_float(d.get("cost_usd"))} for d in by_day if d.get("date")),
        key=lambda r: r["date"],
    )
    data["pricing_verified_at"] = raw.get("pricing_verified_at")
    data["ai_mode"] = str(raw.get("ai_mode") or "—")
    return data


def _pick(item: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {k: item.get(k) for k in keys}


EVENT_KEYS = ("id", "type", "entity_type", "entity_id", "customer_id", "payload", "created_at", "notified")
ERROR_KEYS = ("id", "source", "error_type", "message", "created_at")
SIMULATION_KEYS = ("id", "product_name", "status", "score", "cost_usd", "reused", "output_url", "created_at")


def parse_events(raw: Any) -> dict[str, Any]:
    items, total = as_items(raw)
    return {"items": [_pick(i, EVENT_KEYS) for i in items], "total": total}


def parse_errors(raw: Any) -> dict[str, Any]:
    items, total = as_items(raw)
    return {"items": [_pick(i, ERROR_KEYS) for i in items], "total": total}


def parse_simulations(raw: Any) -> dict[str, Any]:
    items, total = as_items(raw)
    rows = []
    for item in items:
        row = _pick(item, SIMULATION_KEYS)
        if row["product_name"] is None and isinstance(item.get("product"), dict):
            row["product_name"] = item["product"].get("name")
        if row["score"] is None and isinstance(item.get("rating"), dict):
            row["score"] = item["rating"].get("score")
        row["cost_usd"] = to_float(row["cost_usd"])
        row["reused"] = bool(row["reused"] or item.get("reused_from_id"))
        row["status"] = row["status"] or "desconocido"
        rows.append(row)
    return {"items": rows, "total": total}


def parse_listing(raw: Any) -> dict[str, Any]:
    """Listados genéricos (/admin/quotes, /admin/orders): se respetan las claves recibidas."""
    items, total = as_items(raw)
    return {"items": items, "total": total}


def parse_products(raw: Any) -> list[dict[str, Any]]:
    items, _ = as_items(raw)
    rows = []
    for item in items:
        category = item.get("category")
        rows.append(
            {
                "id": item.get("id"),
                "sku": item.get("sku") or "",
                "name": item.get("name") or "",
                "category": category.get("name") if isinstance(category, dict) else (category or ""),
                "price": to_float(item.get("price")),
                "stock": to_int(item.get("stock")),
                "low_stock": bool(item.get("low_stock")),
            }
        )
    return rows


# ---------------------------------------------------------------------------
# Carga (transporte + adaptador) — puras, testeables
# ---------------------------------------------------------------------------


def load(path: str, parser, default, params: dict[str, Any] | None = None, admin: bool = True) -> ApiResult:
    raw, error = fetch_json(path, params=params, admin=admin)
    if error:
        return ApiResult(data=default() if callable(default) else default, error=error)
    try:
        return ApiResult(data=parser(raw))
    except Exception as exc:  # adaptador defensivo: nunca romper la página
        return ApiResult(data=default() if callable(default) else default, error=f"Formato inesperado en {path}: {exc}")


def load_summary() -> ApiResult:
    return load("/admin/metrics/summary", parse_summary, empty_summary)


def load_daily(days: int = 14) -> ApiResult:
    return load("/admin/metrics/daily", parse_daily, list, {"days": days})


def load_top_products(kind: str = "inquired", limit: int = 5) -> ApiResult:
    return load("/admin/metrics/top-products", parse_top_products, list, {"kind": kind, "limit": limit})


def load_usage(days: int = 30) -> ApiResult:
    return load("/admin/usage", parse_usage, empty_usage, {"days": days})


def _empty_listing() -> dict[str, Any]:
    return {"items": [], "total": 0}


def load_events(type_: str | None = None, limit: int = 50, offset: int = 0) -> ApiResult:
    return load("/admin/events", parse_events, _empty_listing, {"type": type_, "limit": limit, "offset": offset})


def load_errors(limit: int = 50) -> ApiResult:
    return load("/admin/errors", parse_errors, _empty_listing, {"limit": limit})


def load_simulations(limit: int = 50) -> ApiResult:
    return load("/admin/simulations", parse_simulations, _empty_listing, {"limit": limit})


def load_orders(status: str | None = None) -> ApiResult:
    return load("/admin/orders", parse_listing, _empty_listing, {"status": status})


def load_quotes(status: str | None = None) -> ApiResult:
    return load("/admin/quotes", parse_listing, _empty_listing, {"status": status})


def load_products() -> ApiResult:
    return load("/api/products", parse_products, list, {"limit": 50}, admin=False)


def load_health() -> ApiResult:
    return load("/health", lambda raw: raw if isinstance(raw, dict) else {}, dict, admin=False)


# ---------------------------------------------------------------------------
# Envoltorios cacheados para las páginas (ttl=30 s)
# ---------------------------------------------------------------------------


@_cache
def get_summary() -> ApiResult:
    return load_summary()


@_cache
def get_daily(days: int = 14) -> ApiResult:
    return load_daily(days)


@_cache
def get_top_products(kind: str = "inquired", limit: int = 5) -> ApiResult:
    return load_top_products(kind, limit)


@_cache
def get_usage(days: int = 30) -> ApiResult:
    return load_usage(days)


@_cache
def get_events(type_: str | None = None, limit: int = 50, offset: int = 0) -> ApiResult:
    return load_events(type_, limit, offset)


@_cache
def get_errors(limit: int = 50) -> ApiResult:
    return load_errors(limit)


@_cache
def get_simulations(limit: int = 50) -> ApiResult:
    return load_simulations(limit)


@_cache
def get_orders(status: str | None = None) -> ApiResult:
    return load_orders(status)


@_cache
def get_quotes(status: str | None = None) -> ApiResult:
    return load_quotes(status)


@_cache
def get_products() -> ApiResult:
    return load_products()


@_cache
def get_health() -> ApiResult:
    return load_health()


def resolve_url(url: str | None) -> str | None:
    """Antepone la URL base de la API a rutas relativas (``/media/...``)."""
    if not url:
        return None
    if url.startswith(("http://", "https://")):
        return url
    return f"{api_base_url()}/{url.lstrip('/')}"


def load_image_bytes(url: str | None) -> bytes | None:
    """Descarga la imagen desde el servidor del dashboard (el navegador puede no ver la red interna)."""
    full = resolve_url(url)
    if not full:
        return None
    headers = {"X-Admin-Key": admin_key()} if full.startswith(api_base_url()) else {}
    try:
        resp = requests.get(full, headers=headers, timeout=TIMEOUT_SECONDS)
    except requests.RequestException:
        return None
    if resp.status_code != 200 or not resp.headers.get("content-type", "").startswith("image/"):
        return None
    return resp.content


@_cache
def get_image_bytes(url: str | None) -> bytes | None:
    return load_image_bytes(url)


def clear_cache() -> None:
    if st is not None:
        st.cache_data.clear()
