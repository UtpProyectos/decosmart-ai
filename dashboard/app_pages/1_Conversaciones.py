"""Conversaciones y consultas: series diarias y tipos de consulta."""

from html import escape

import pandas as pd
import streamlit as st

import api
import charts
import ui
from icons import icon

INQUIRY_TYPE_LABELS = {
    "product_info": "Información de producto",
    "price": "Precio",
    "dimensions": "Medidas",
    "stock": "Stock",
    "recommendation": "Recomendación",
    "catalog": "Catálogo",
}

ui.setup_page("Conversaciones", "Sesiones de chat y consultas concretas sobre el catálogo.")

days = (
    st.segmented_control(
        "Rango", options=[7, 14, 30, 60, 90], default=14, format_func=lambda d: f"{d} días", key="conv_days"
    )
    or 14
)
summary_res = api.get_summary()
daily_res = api.get_daily(days)
events_res = api.get_events("inquiry.created", 200, 0)
ui.show_errors(summary_res, daily_res, events_res)

s = summary_res.data
ratio = s["inquiries_total"] / s["conversations_total"] if s["conversations_total"] else 0
period_inquiries = sum(r["inquiries"] for r in daily_res.data)
avg_day = period_inquiries / len(daily_res.data) if daily_res.data else 0
ui.kpi_grid(
    [
        ui.kpi_card("chat", "Conversaciones (total)", ui.fmt_int(s["conversations_total"])),
        ui.kpi_card("users", "Clientes únicos", ui.fmt_int(s["unique_customers"])),
        ui.kpi_card(
            "search",
            "Consultas (total)",
            ui.fmt_int(s["inquiries_total"]),
            hint=f"{ui.fmt_int(period_inquiries)} en {days} días · {avg_day:.1f} por día",
        ),
        ui.kpi_card("trending-up", "Consultas por conversación", f"{ratio:.1f}"),
    ]
)

ui.section_header("activity", "Serie diaria", f"Conversaciones y consultas · últimos {days} días")
if daily_res.data:
    fig = charts.grouped_bars(daily_res.data, {"conversations": "Conversaciones", "inquiries": "Consultas"})
    charts.show(fig, alt="Conversaciones y consultas por día")
else:
    ui.empty_state("activity", "Sin datos diarios para el rango elegido", "Prueba con un rango más amplio.")

ui.section_header("search", "Tipos de consulta", "Según los eventos inquiry.created más recientes (máx. 200)")
rows = []
for event in events_res.data["items"]:
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    kind = payload.get("type") or payload.get("inquiry_type") or "sin tipo"
    channel = payload.get("channel") or "—"
    rows.append({"Tipo": INQUIRY_TYPE_LABELS.get(kind, kind), "Canal": channel})
if rows:
    table = pd.DataFrame(rows).value_counts().reset_index(name="Consultas").sort_values("Consultas", ascending=False)
    total = int(table["Consultas"].sum())
    html_rows = [
        {
            "tipo": f'<span class="ds-type">{icon("search", 15)}{escape(str(r["Tipo"]))}</span>',
            "canal": ui.status_pill(str(r["Canal"]), "neutral"),
            "n": ui.fmt_int(r["Consultas"]),
            "pct": f"{r['Consultas'] / total * 100:.0f} %",
        }
        for r in table.to_dict("records")
    ]
    ui.html(
        ui.html_table(
            [("tipo", "Tipo"), ("canal", "Canal"), ("n", "Consultas"), ("pct", "Participación")],
            html_rows,
            numeric=("n", "pct"),
        )
    )
else:
    ui.empty_state(
        "search",
        "Aún no hay consultas registradas",
        "Cada pregunta sobre precio, medidas o stock respondida con el catálogo se contará aquí.",
    )

ui.definitions()
