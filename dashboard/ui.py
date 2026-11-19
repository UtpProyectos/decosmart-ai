"""Utilidades compartidas de interfaz: configuración de página, acceso, formato y gráficos."""

from __future__ import annotations

import hmac
import json
import os
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import api

# Paleta sobria alineada con la tienda (terracota + neutros cálidos).
PRIMARY = "#b5653a"
TEXT = "#2b2622"
BACKGROUND = "#faf7f2"
SAGE = "#6f8a7a"
SAND = "#d8c3a5"
SLATE = "#4f5d75"
MUTED = "#9a8f85"
DANGER = "#a23b2a"
SERIES_COLORS = [PRIMARY, SAGE, SLATE, SAND, MUTED]

SERIES_LABELS = {
    "conversations": "Conversaciones",
    "inquiries": "Consultas",
    "quotes": "Cotizaciones",
    "orders": "Pedidos demo",
    "simulations": "Simulaciones",
}

DEFINITIONS_MD = """
- **Conversación**: sesión de chat de un cliente en Telegram (nueva si pasan >6 h sin actividad o cambia el día).
- **Consulta**: pregunta concreta sobre un producto o categoría (precio, medidas, stock, recomendación).
  Incluye vistas de detalle en la web.
- **Cotización**: documento con productos, cantidades y precios congelados, con fecha de validez.
- **Pedido demo**: intención de compra registrada. **No es una venta**: no hay pago.
- **Venta concretada**: pedido marcado como `completed` por un administrador (entregado/pagado fuera del sistema).

> Consulta ≠ Cotización ≠ Pedido demo ≠ Venta concretada.

- **Gasto API**: costo **estimado** de llamadas reales a OpenAI (modo `live`) según la tabla de precios del backend.
"""


def setup_page(title: str, icon: str = "📊") -> None:
    """Configura la página, aplica el control de acceso y dibuja la barra lateral común."""
    st.set_page_config(page_title=f"{title} · DecoSmart Admin", page_icon=icon, layout="wide")
    require_password()
    _sidebar()
    st.title(title)


def require_password() -> None:
    """Si DASHBOARD_PASSWORD está definido, pide la contraseña antes de mostrar nada."""
    expected = os.getenv("DASHBOARD_PASSWORD", "")
    if not expected or st.session_state.get("authenticated"):
        return
    st.title("DecoSmart · Panel de control")
    with st.form("login"):
        password = st.text_input("Contraseña del dashboard", type="password")
        submitted = st.form_submit_button("Ingresar")
    if submitted:
        if hmac.compare_digest(password.encode(), expected.encode()):
            st.session_state["authenticated"] = True
            st.rerun()
        st.error("Contraseña incorrecta.")
    st.stop()


def _sidebar() -> None:
    with st.sidebar:
        st.markdown("### DecoSmart AI")
        st.caption("Panel de operación (solo lectura)")
        if st.button("🔄 Actualizar datos", width="stretch"):
            api.clear_cache()
            st.rerun()
        health = api.get_health()
        if health.ok:
            h = health.data or {}
            st.success(f"API en línea · BD {h.get('db', '?')} · IA {h.get('ai_mode', '?')}")
        else:
            st.error("API no disponible")
        st.caption(f"API: `{api.api_base_url()}`")
        st.caption("Los datos se cachean 30 s.")
        if os.getenv("DASHBOARD_PASSWORD") and st.button("Cerrar sesión", width="stretch"):
            st.session_state["authenticated"] = False
            st.rerun()


def definitions_expander(expanded: bool = False) -> None:
    with st.expander("ℹ️ Definiciones", expanded=expanded):
        st.markdown(DEFINITIONS_MD)


def show_errors(*results: api.ApiResult) -> None:
    """Muestra un aviso por cada error distinto (sin detener la página)."""
    seen: set[str] = set()
    for result in results:
        if result.error and result.error not in seen:
            seen.add(result.error)
            st.warning(f"⚠️ {result.error}")


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


def budget_progress(used_pct: float, spent: float, budget: float) -> None:
    pct = max(0.0, min(api.to_float(used_pct), 100.0))
    label = f"Presupuesto IA: {fmt_usd(spent, 4)} de {fmt_usd(budget)} ({fmt_pct(used_pct)})"
    st.progress(pct / 100, text=label)
    if used_pct >= 100:
        st.error("Presupuesto agotado: las llamadas reales a OpenAI están bloqueadas.")
    elif used_pct >= 80:
        st.warning("Se superó el 80 % del presupuesto de IA.")


# ---------------------------------------------------------------------------
# Gráficos
# ---------------------------------------------------------------------------


def style_fig(fig: go.Figure, height: int = 340) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT),
        colorway=SERIES_COLORS,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(43,38,34,0.08)", rangemode="tozero")
    return fig


def empty_state(message: str = "Sin datos todavía.") -> None:
    st.info(message)


def table_frame(items: list[dict[str, Any]]) -> pd.DataFrame:
    """DataFrame apto para st.dataframe: listas/dicts anidados se serializan como JSON."""
    df = pd.DataFrame(items)
    for col in df.columns:
        if df[col].map(lambda v: isinstance(v, (dict, list))).any():
            df[col] = df[col].map(lambda v: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v)
    return df
