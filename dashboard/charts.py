"""Gráficos Plotly con una plantilla mínima compartida.

Los constructores son funciones puras (listas de dicts → ``go.Figure``) y toleran datos
vacíos, por lo que se prueban sin el runtime de Streamlit. ``show()`` los dibuja.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import plotly.graph_objects as go

INK = "#111111"
MUTED = "#6b6b6b"
BORDER = "#e6e6e3"
GRID = "#eeeeec"
OLIVE = "#6f7d4f"
SAND = "#c9b26b"
GREY = "#9a9a96"
RED = "#b5483b"
SERIES = [INK, OLIVE, SAND, GREY, RED]
FONT = 'Inter, "Helvetica Neue", Helvetica, Arial, sans-serif'

PLOTLY_CONFIG = {"displayModeBar": False, "displaylogo": False, "responsive": True}

TEMPLATE = go.layout.Template(
    layout=go.Layout(
        font=dict(family=FONT, size=12, color=INK),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        colorway=SERIES,
        margin=dict(l=8, r=12, t=8, b=8),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#ffffff", bordercolor=BORDER, font=dict(family=FONT, size=12, color=INK)),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(size=12, color=MUTED),
            bgcolor="rgba(0,0,0,0)",
            itemsizing="constant",
        ),
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            showline=False,
            ticks="",
            tickfont=dict(size=11, color=MUTED),
            title=dict(font=dict(size=11, color=MUTED)),
            automargin=True,
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor=GRID,
            gridwidth=1,
            zeroline=False,
            showline=False,
            ticks="",
            tickfont=dict(size=11, color=MUTED),
            title=dict(font=dict(size=11, color=MUTED)),
            rangemode="tozero",
            automargin=True,
            ticklabelstandoff=6,
        ),
        bargap=0.35,
        barcornerradius=4,
    )
)


def _base(height: int) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(template=TEMPLATE, height=height)
    return fig


def _count_axis(fig: go.Figure, values: Iterable[Any]) -> None:
    """Eje Y de conteos: enteros (sin 0.5) cuando los valores son pequeños."""
    peak = max((float(v or 0) for v in values), default=0)
    if peak <= 6:
        fig.update_yaxes(dtick=1, tickformat="d", range=[0, max(peak, 1) * 1.1])


def _col(rows: Iterable[Mapping[str, Any]], key: str) -> list[Any]:
    return [r.get(key) for r in rows]


def daily_activity(rows: list[dict[str, Any]], series: Mapping[str, str], height: int = 320) -> go.Figure:
    """Líneas finas, una por serie (``series`` = clave → etiqueta)."""
    fig = _base(height)
    dates = _col(rows, "date")
    for i, (key, label) in enumerate(series.items()):
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=[r.get(key, 0) for r in rows],
                name=label,
                mode="lines",
                line=dict(color=SERIES[i % len(SERIES)], width=2 if i == 0 else 1.5, shape="spline", smoothing=0.4),
                hovertemplate="%{y}",
            )
        )
    fig.update_xaxes(type="date", tickformat="%d %b")
    _count_axis(fig, [r.get(k, 0) for r in rows for k in series])
    return fig


def grouped_bars(rows: list[dict[str, Any]], series: Mapping[str, str], height: int = 300) -> go.Figure:
    """Barras agrupadas por fecha (p. ej. conversaciones vs consultas)."""
    fig = _base(height)
    dates = _col(rows, "date")
    for i, (key, label) in enumerate(series.items()):
        fig.add_trace(
            go.Bar(x=dates, y=[r.get(key, 0) for r in rows], name=label, marker_color=SERIES[i % len(SERIES)])
        )
    fig.update_layout(barmode="group", bargroupgap=0.1)
    fig.update_xaxes(type="date", tickformat="%d %b")
    _count_axis(fig, [r.get(k, 0) for r in rows for k in series])
    return fig


def top_products(rows: list[dict[str, Any]], color: str = INK, height: int | None = None) -> go.Figure:
    """Barras horizontales (mayor arriba) con el valor al final de la barra; alto según las filas."""
    fig = _base(height or max(72, 36 + 36 * len(rows)))
    ordered = sorted(rows, key=lambda r: r.get("count", 0))
    fig.add_trace(
        go.Bar(
            x=_col(ordered, "count"),
            y=_col(ordered, "name"),
            orientation="h",
            marker_color=color,
            text=_col(ordered, "count"),
            textposition="outside",
            textfont=dict(size=11, color=MUTED),
            cliponaxis=False,
            hovertemplate="%{y}: %{x}<extra></extra>",
        )
    )
    fig.update_layout(hovermode="closest", bargap=0.5, margin=dict(l=8, r=28, t=4, b=4))
    fig.update_xaxes(showgrid=False, showticklabels=False, rangemode="tozero")
    fig.update_yaxes(showgrid=False, tickfont=dict(size=12, color=INK), automargin=True)
    return fig


def ratings_distribution(scores: Iterable[Any], height: int = 260) -> go.Figure:
    """Barras 1–5 con el conteo de cada puntuación."""
    counts = {n: 0 for n in range(1, 6)}
    for score in scores:
        try:
            value = int(float(score))
        except (TypeError, ValueError):
            continue
        if value in counts:
            counts[value] += 1
    fig = _base(height)
    colors = [RED, SAND, GREY, OLIVE, INK]
    fig.add_trace(
        go.Bar(
            x=[f"{n} ★" for n in counts],
            y=list(counts.values()),
            marker_color=colors,
            text=list(counts.values()),
            textposition="outside",
            textfont=dict(size=11, color=MUTED),
            cliponaxis=False,
            hovertemplate="%{x}: %{y}<extra></extra>",
        )
    )
    fig.update_layout(hovermode="closest", bargap=0.5)
    fig.update_yaxes(showticklabels=False, showgrid=False)
    return fig


def spend_by_day(rows: list[dict[str, Any]], budget: float | None = None, height: int = 300) -> go.Figure:
    """Área suave del gasto diario + línea del acumulado (y presupuesto como referencia)."""
    fig = _base(height)
    dates = _col(rows, "date")
    daily = [float(r.get("cost_usd") or 0) for r in rows]
    cumulative: list[float] = []
    total = 0.0
    for value in daily:
        total += value
        cumulative.append(total)
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=daily,
            name="Gasto diario",
            mode="lines",
            fill="tozeroy",
            line=dict(color=OLIVE, width=1.5),
            fillcolor="rgba(111,125,79,0.12)",
            hovertemplate="US$ %{y:.4f}",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=cumulative,
            name="Acumulado del rango",
            mode="lines",
            line=dict(color=INK, width=2),
            hovertemplate="US$ %{y:.4f}",
        )
    )
    # La línea de presupuesto solo se dibuja si el gasto se le acerca (si no, aplana la serie).
    if budget and total >= budget * 0.5:
        fig.add_hline(
            y=budget,
            line_dash="dot",
            line_width=1,
            line_color=RED,
            annotation_text="Presupuesto",
            annotation_font=dict(size=11, color=RED),
            annotation_position="top left",
        )
    fig.update_xaxes(type="date", tickformat="%d %b")
    fig.update_yaxes(tickprefix="US$ ")
    return fig


def spend_by_operation(
    rows: list[dict[str, Any]], labels: Mapping[str, str] | None = None, height: int = 280
) -> go.Figure:
    """Dona con el total en el centro."""
    labels = labels or {}
    fig = _base(height)
    names = [labels.get(str(r.get("operation")), str(r.get("operation"))) for r in rows]
    values = [float(r.get("cost_usd") or 0) for r in rows]
    calls = [r.get("calls", 0) for r in rows]
    total = sum(values)
    if rows:
        fig.add_trace(
            go.Pie(
                labels=names,
                values=values if total > 0 else calls,
                hole=0.78,
                sort=False,
                marker=dict(colors=SERIES[: len(rows)] or SERIES, line=dict(color="#ffffff", width=2)),
                textinfo="none",
                customdata=calls,
                hovertemplate="%{label}<br>US$ %{value:.4f}<br>%{customdata} llamadas<extra></extra>",
            )
        )
    fig.update_layout(
        hovermode="closest",
        showlegend=bool(rows),
        legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.0),
        annotations=[
            dict(
                text=f"<b>US$ {total:.4f}</b><br><span style='font-size:11px;color:{MUTED}'>total</span>",
                x=0.5,
                y=0.5,
                xref="paper",
                yref="paper",
                showarrow=False,
                font=dict(size=16, color=INK),
            )
        ],
    )
    return fig


def show(fig: go.Figure, alt: str | None = None) -> None:
    """Dibuja la figura en Streamlit con la plantilla propia (sin el tema de Streamlit ni modebar)."""
    import streamlit as st

    st.plotly_chart(fig, theme=None, config=PLOTLY_CONFIG, width="stretch", alt=alt)
