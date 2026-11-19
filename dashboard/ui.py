"""Interfaz compartida: estilos, cabecera, acceso, componentes HTML y formato.

Los componentes ``kpi_card``, ``status_pill``, ``progress_bar`` y ``empty_state_html``
devuelven HTML (puro, testeable); ``kpi_grid``, ``section_header``, ``empty_state`` y
``definitions`` lo dibujan. Todo texto dinámico pasa por ``html.escape``.
"""

from __future__ import annotations

import hmac
import json
import os
from collections.abc import Iterable
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

import api
from icons import icon

# Paleta compartida con la tienda.
INK = "#111111"
MUTED = "#6b6b6b"
BORDER = "#e6e6e3"
SURFACE = "#f5f5f3"
OLIVE = "#6f7d4f"
SAND = "#c9b26b"
RED = "#b5483b"

TONES = ("neutral", "positive", "warning", "error")

SERIES_LABELS = {
    "conversations": "Conversaciones",
    "inquiries": "Consultas",
    "quotes": "Cotizaciones",
    "orders": "Pedidos demo",
    "simulations": "Simulaciones",
}

DEFINITIONS = [
    (
        "search",
        "Consulta",
        "Pregunta concreta sobre un producto o categoría (precio, medidas, stock). "
        "Incluye vistas de detalle en la web.",
    ),
    ("file-text", "Cotización", "Documento con productos, cantidades y precios congelados, con fecha de validez."),
    ("shopping-bag", "Pedido demo", "Intención de compra registrada. No es una venta: no hay pago."),
    (
        "check-circle",
        "Venta concretada",
        "Pedido marcado como completed por un administrador (entregado/pagado fuera del sistema).",
    ),
]

# Tipo de evento → (icono, etiqueta, tono).
EVENT_META: dict[str, tuple[str, str, str]] = {
    "conversation.started": ("chat", "Conversación iniciada", "neutral"),
    "inquiry.created": ("search", "Consulta", "neutral"),
    "quote.created": ("file-text", "Cotización creada", "neutral"),
    "quote.status_changed": ("file-text", "Cotización actualizada", "neutral"),
    "order.created": ("shopping-bag", "Pedido demo", "positive"),
    "order.status_changed": ("shopping-bag", "Pedido actualizado", "neutral"),
    "simulation.completed": ("image", "Simulación completada", "positive"),
    "simulation.failed": ("alert-triangle", "Simulación fallida", "error"),
    "simulation.rated": ("star", "Simulación calificada", "neutral"),
    "product.low_stock": ("box", "Stock bajo", "warning"),
    "budget.warning": ("coins", "Aviso de presupuesto", "warning"),
    "summary.daily": ("list", "Resumen diario", "neutral"),
}

CSS_PATH = Path(__file__).resolve().parent / "styles.css"


# ---------------------------------------------------------------------------
# Página: configuración, acceso, cabecera y barra lateral
# ---------------------------------------------------------------------------


@st.cache_resource(show_spinner=False)
def _css() -> str:
    try:
        return CSS_PATH.read_text(encoding="utf-8")
    except OSError:
        return ""


def inject_css() -> None:
    """Inyecta la hoja de estilos global (solo ``<style>``: no ocupa espacio en la página)."""
    st.html(f"<style>{_css()}</style>")


def setup_page(title: str, subtitle: str | None = None) -> None:
    """Configura la página, aplica el control de acceso, la barra lateral y la cabecera."""
    st.set_page_config(page_title=f"{title} · DecoSmart Panel", page_icon=":material/space_dashboard:", layout="wide")
    inject_css()
    require_password()
    st.session_state["_ds_api_banner"] = False  # el banner de API caída se muestra una vez por ejecución
    _sidebar()
    page_header(title, subtitle)


def is_authenticated() -> bool:
    return not os.getenv("DASHBOARD_PASSWORD", "") or bool(st.session_state.get("authenticated"))


def require_password() -> None:
    """Si DASHBOARD_PASSWORD está definido, pide la contraseña antes de mostrar nada."""
    expected = os.getenv("DASHBOARD_PASSWORD", "")
    if not expected or st.session_state.get("authenticated"):
        return
    _, center, _ = st.columns([1, 1.2, 1])
    with center:
        st.markdown(
            '<div class="ds-header" style="margin-top:12vh;margin-bottom:12px">'
            '<div class="ds-brand"><span class="ds-mark">DS</span>DecoSmart · Panel</div>'
            '<div class="ds-title">Ingresar</div>'
            '<div class="ds-subtitle">Panel de operación de solo lectura.</div></div>',
            unsafe_allow_html=True,
        )
        with st.form("login", border=True):
            password = st.text_input("Contraseña del dashboard", type="password")
            submitted = st.form_submit_button("Ingresar", type="primary", width="stretch")
        if submitted:
            if hmac.compare_digest(password.encode(), expected.encode()):
                st.session_state["authenticated"] = True
                st.rerun()
            st.error("Contraseña incorrecta.")
    st.stop()


@st.cache_data(ttl=30, show_spinner=False)
def _fetched_at() -> datetime:
    """Momento de la última carga; comparte el TTL de 30 s de los datos y se limpia con ellos."""
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo(os.getenv("TIMEZONE", "America/Lima")))
    except Exception:
        return datetime.now()


def page_header(title: str, subtitle: str | None = None) -> None:
    health = api.get_health()
    mode = str((health.data or {}).get("ai_mode") or "—") if health.ok else "—"
    left, right = st.columns([3, 2], vertical_alignment="bottom")
    with left:
        sub = f'<div class="ds-subtitle">{escape(subtitle)}</div>' if subtitle else ""
        st.markdown(
            '<div class="ds-header"><div class="ds-brand"><span class="ds-mark">DS</span>DecoSmart · Panel</div>'
            f'<div class="ds-title" role="heading" aria-level="1">{escape(title)}</div>{sub}</div>',
            unsafe_allow_html=True,
        )
    with right, st.container(horizontal=True, horizontal_alignment="right", vertical_alignment="center", gap="small"):
        mode_tone = "positive" if mode == "live" else ("neutral" if mode != "—" else "error")
        mode_text = f"IA {mode}" if mode != "—" else "API sin conexión"
        st.markdown(
            f'<div class="ds-meta">{icon("clock", 15)} Actualizado {_fetched_at():%H:%M:%S}'
            f"{status_pill(mode_text, mode_tone)}</div>",
            unsafe_allow_html=True,
            width="content",
        )
        if st.button("Actualizar", icon=":material/refresh:", key="ds_refresh", help="Limpia la caché (30 s)"):
            api.clear_cache()
            st.rerun()
    st.markdown('<div class="ds-rule"></div>', unsafe_allow_html=True)


def _sidebar() -> None:
    with st.sidebar:
        health = api.get_health()
        if health.ok:
            h = health.data or {}
            db_ok = str(h.get("db", "?")) == "ok"
            status = (
                f"{status_pill('API en línea', 'positive')} "
                f"{status_pill('BD ' + str(h.get('db', '?')), 'positive' if db_ok else 'warning')}"
            )
        else:
            status = status_pill("API no disponible", "error")
        st.markdown(
            '<div class="ds-side-block"><div class="ds-side-title">Estado</div>'
            f"<div>{status}</div>"
            f"<div>API <code>{escape(api.api_base_url())}</code></div>"
            "<div>Datos cacheados 30 s · solo lectura</div></div>",
            unsafe_allow_html=True,
        )
        if os.getenv("DASHBOARD_PASSWORD") and st.button(
            "Cerrar sesión", icon=":material/logout:", width="stretch", key="ds_logout"
        ):
            st.session_state["authenticated"] = False
            st.rerun()


CONNECTION_MARKERS = ("No se pudo conectar", "no respondió")


def is_connection_error(message: str | None) -> bool:
    return bool(message) and any(m in message for m in CONNECTION_MARKERS)


def _api_down_banner(messages: list[str]) -> None:
    """Un único aviso por ejecución cuando la API no responde, con botón para reintentar."""
    if st.session_state.get("_ds_api_banner"):
        return
    st.session_state["_ds_api_banner"] = True
    if any("No se pudo conectar" in m for m in messages):
        text = f"No se pudo conectar con la API ({api.api_base_url()})."
    else:
        text = "La API no respondió a tiempo."
    text += " Si el backend está despertando (Render free), reintenta en unos segundos."
    left, right = st.columns([6, 1], vertical_alignment="center")
    left.warning(text, icon=":material/cloud_off:")
    if right.button("Reintentar", icon=":material/refresh:", key="ds_retry", width="stretch"):
        api.clear_cache()
        st.rerun()


def show_errors(*results: api.ApiResult) -> None:
    """Avisos de error sin detener la página.

    Los errores de conexión (API caída o dormida) se agrupan en un único banner por
    ejecución con "Reintentar"; el resto (404, 500, formato) se muestra uno por mensaje.
    """
    connection = [r.error for r in results if r.error and is_connection_error(r.error)]
    if connection:
        _api_down_banner(connection)
    seen: set[str] = set()
    for result in results:
        if result.error and not is_connection_error(result.error) and result.error not in seen:
            seen.add(result.error)
            st.warning(result.error, icon=":material/error:")


# ---------------------------------------------------------------------------
# Componentes HTML
# ---------------------------------------------------------------------------


def _tone(tone: str | None) -> str:
    return tone if tone in TONES else "neutral"


def html(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


def kpi_card(
    icon_name: str,
    label: str,
    value: Any,
    delta: str | None = None,
    hint: str | None = None,
    tone: str = "neutral",
) -> str:
    tone = _tone(tone)
    delta_html = f'<span class="ds-delta {tone}">{escape(str(delta))}</span>' if delta else ""
    hint_html = f'<div class="ds-kpi-hint">{escape(str(hint))}</div>' if hint else ""
    return (
        '<div class="ds-card ds-kpi">'
        f'<div class="ds-kpi-top"><span class="ds-ico {tone}">{icon(icon_name, 18)}</span>{delta_html}</div>'
        f'<div><div class="ds-kpi-value">{escape(str(value))}</div>'
        f'<div class="ds-kpi-label">{escape(str(label))}</div></div>{hint_html}</div>'
    )


def kpi_grid(cards: Iterable[str], columns: int = 4) -> None:
    cols = max(1, int(columns))
    html(f'<div class="ds-grid" style="--ds-cols:{cols}">{"".join(cards)}</div>')


def section_header(icon_name: str, title: str, subtitle: str | None = None) -> None:
    sub = f'<div class="ds-section-sub">{escape(subtitle)}</div>' if subtitle else ""
    html(
        f'<div class="ds-section"><span class="ds-ico">{icon(icon_name, 16)}</span>'
        f'<div><div class="ds-section-title" role="heading" aria-level="3">{escape(title)}</div>{sub}</div></div>'
    )


def status_pill(text: str, tone: str = "neutral") -> str:
    return f'<span class="ds-pill {_tone(tone)}">{escape(str(text))}</span>'


def empty_state_html(icon_name: str, title: str, text: str = "") -> str:
    body = f'<div class="ds-empty-text">{escape(text)}</div>' if text else ""
    return (
        f'<div class="ds-empty"><span class="ds-ico">{icon(icon_name, 18)}</span>'
        f'<div><div class="ds-empty-title">{escape(title)}</div>{body}</div></div>'
    )


def empty_state(icon_name: str = "info", title: str = "Sin datos todavía", text: str = "") -> None:
    html(empty_state_html(icon_name, title, text))


def budget_tone(pct: Any) -> str:
    """Tono del presupuesto: ``warning`` desde 80 %, ``error`` desde 100 %."""
    value = api.to_float(pct)
    if value >= 100:
        return "error"
    if value >= 80:
        return "warning"
    return "neutral"


def progress_bar(pct: Any, tone: str | None = None, label: str | None = None) -> str:
    """Barra de progreso HTML; sin ``tone`` explícito se deriva de los umbrales del presupuesto."""
    value = api.to_float(pct)
    width = max(0.0, min(value, 100.0))
    tone = _tone(tone) if tone else budget_tone(value)
    head = (
        f'<div class="ds-progress-head"><span class="ds-progress-label">{label}</span>'
        f'<span class="ds-delta {tone}">{escape(fmt_pct(value))}</span></div>'
        if label is not None
        else ""
    )
    return (
        f'<div class="ds-progress">{head}<div class="ds-track" role="progressbar" aria-valuenow="{width:.1f}" '
        f'aria-valuemin="0" aria-valuemax="100">'
        f'<div class="ds-fill {tone}" style="width:{width:.2f}%"></div></div></div>'
    )


def budget_progress(used_pct: float, spent: float, budget: float) -> None:
    label = f"<b>{escape(fmt_usd(spent, 4))}</b> de {escape(fmt_usd(budget))} del presupuesto de IA"
    html(f'<div class="ds-card ds-block">{progress_bar(used_pct, label=label)}</div>')
    tone = budget_tone(used_pct)
    if tone == "error":
        empty_state("alert-triangle", "Presupuesto agotado", "Las llamadas reales a OpenAI están bloqueadas.")
    elif tone == "warning":
        empty_state("alert-triangle", "Se superó el 80 % del presupuesto de IA", "Revisa el consumo en Costos API.")


def stars(score: Any) -> str:
    n = max(0, min(api.to_int(score), 5))
    return f'<span class="ds-stars" aria-label="{n} de 5">{"★" * n}<span class="off">{"★" * (5 - n)}</span></span>'


def event_meta(type_: Any) -> tuple[str, str, str]:
    key = str(type_ or "")
    return EVENT_META.get(key, ("activity", key or "Evento", "neutral"))


def entity_label(ev: dict[str, Any]) -> str:
    """``simulation #2``; sin id (eventos de sistema) solo el tipo de entidad."""
    entity = str(ev.get("entity_type") or "—")
    return f"{entity} #{ev['entity_id']}" if ev.get("entity_id") is not None else entity


def event_list(events: Iterable[dict[str, Any]]) -> str:
    rows = []
    for ev in events:
        ico, label, tone = event_meta(ev.get("type"))
        sub = entity_label(ev) if ev.get("entity_type") else str(ev.get("type") or "")
        rows.append(
            f'<div class="ds-row"><span class="ds-ico {tone}">{icon(ico, 16)}</span>'
            f'<div class="ds-row-main"><div class="ds-row-title">{escape(label)}</div>'
            f'<div class="ds-row-sub">{escape(sub)}</div></div>'
            f'<span class="ds-row-time">{escape(fmt_datetime(ev.get("created_at")))}</span></div>'
        )
    return f'<div class="ds-card ds-block" style="padding:4px 16px">{"".join(rows)}</div>'


def definitions(expanded: bool = False) -> None:
    """Consulta ≠ Cotización ≠ Pedido demo ≠ Venta concretada, como 4 tarjetas pequeñas."""
    with st.expander(
        "Definiciones · Consulta ≠ Cotización ≠ Pedido demo ≠ Venta concretada",
        expanded=expanded,
        icon=":material/info:",
    ):
        cards = [
            f'<div class="ds-card ds-def"><span class="ds-ico">{icon(ico, 18)}</span>'
            f'<div class="ds-def-title">{escape(title)}</div><div class="ds-def-text">{escape(text)}</div></div>'
            for ico, title, text in DEFINITIONS
        ]
        kpi_grid(cards, columns=4)
        html(
            '<div class="ds-note">Conversación: sesión de chat en Telegram '
            "(nueva si pasan &gt; 6 h sin actividad o cambia "
            "el día). Gasto API: costo <b>estimado</b> de llamadas reales a OpenAI (modo live).</div>"
        )


# Compatibilidad con el nombre anterior.
definitions_expander = definitions


def html_table(columns: list[tuple[str, str]], rows: Iterable[dict[str, str]], numeric: Iterable[str] = ()) -> str:
    """Tabla HTML; ``rows`` ya contiene HTML seguro (escapado por quien llama)."""
    num = set(numeric)
    head = "".join(f'<th class="{"num" if k in num else ""}">{escape(label)}</th>' for k, label in columns)
    body = "".join(
        "<tr>" + "".join(f'<td class="{"num" if k in num else ""}">{row.get(k, "")}</td>' for k, _ in columns) + "</tr>"
        for row in rows
    )
    return (
        f'<div class="ds-table-wrap"><table class="ds-table"><thead><tr>{head}</tr></thead>'
        f"<tbody>{body}</tbody></table></div>"
    )


# ---------------------------------------------------------------------------
# Formato
# ---------------------------------------------------------------------------


def fmt_int(value: Any) -> str:
    return f"{api.to_int(value):,}".replace(",", ".")


def fmt_usd(value: Any, decimals: int = 2) -> str:
    return f"US$ {api.to_float(value):,.{decimals}f}"


def fmt_pct(value: Any) -> str:
    return f"{api.to_float(value):.1f} %"


def fmt_rating(value: Any) -> str:
    return "—" if value is None else f"{api.to_float(value):.1f} / 5"


def fmt_datetime(value: Any) -> str:
    """ISO 8601 → ``18 nov 10:00`` (hora local del panel); devuelve el texto original si no se puede leer."""
    if not value:
        return "—"
    try:
        ts = pd.Timestamp(str(value))
        try:
            from zoneinfo import ZoneInfo

            if ts.tzinfo is not None:
                ts = ts.tz_convert(ZoneInfo(os.getenv("TIMEZONE", "America/Lima")))
        except Exception:
            pass
        months = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
        return f"{ts.day:02d} {months[ts.month - 1]} {ts:%H:%M}"
    except Exception:
        return str(value)


def table_frame(items: list[dict[str, Any]]) -> pd.DataFrame:
    """DataFrame apto para st.dataframe: listas/dicts anidados se serializan como JSON."""
    df = pd.DataFrame(items)
    for col in df.columns:
        if df[col].map(lambda v: isinstance(v, (dict, list))).any():
            df[col] = df[col].map(lambda v: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v)
    return df
