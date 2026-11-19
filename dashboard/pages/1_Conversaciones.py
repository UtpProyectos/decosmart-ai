"""Conversaciones y consultas: series diarias y tipos de consulta."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import api
import ui

INQUIRY_TYPE_LABELS = {
    "product_info": "Información de producto",
    "price": "Precio",
    "dimensions": "Medidas",
    "stock": "Stock",
    "recommendation": "Recomendación",
    "catalog": "Catálogo",
}

ui.setup_page("Conversaciones y consultas", "💬")

days = st.select_slider("Rango", options=[7, 14, 30, 60, 90], value=14, format_func=lambda d: f"{d} días")
summary_res = api.get_summary()
daily_res = api.get_daily(days)
events_res = api.get_events("inquiry.created", 200, 0)
ui.show_errors(summary_res, daily_res, events_res)
ui.definitions_expander()

s = summary_res.data
c1, c2, c3, c4 = st.columns(4)
c1.metric("Conversaciones (total)", ui.fmt_int(s["conversations_total"]))
c2.metric("Clientes únicos", ui.fmt_int(s["unique_customers"]))
c3.metric("Consultas (total)", ui.fmt_int(s["inquiries_total"]))
ratio = s["inquiries_total"] / s["conversations_total"] if s["conversations_total"] else 0
c4.metric("Consultas por conversación", f"{ratio:.1f}")

st.subheader(f"Serie diaria ({days} días)")
if daily_res.data:
    df = pd.DataFrame(daily_res.data)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["date"], y=df["conversations"], name="Conversaciones", marker_color=ui.SLATE))
    fig.add_trace(go.Bar(x=df["date"], y=df["inquiries"], name="Consultas", marker_color=ui.PRIMARY))
    fig.update_layout(barmode="group")
    st.plotly_chart(ui.style_fig(fig), config={"displayModeBar": False})
    c1, c2 = st.columns(2)
    c1.metric(f"Consultas en {days} días", ui.fmt_int(df["inquiries"].sum()))
    c2.metric("Promedio de consultas por día", f"{df['inquiries'].mean():.1f}")
else:
    ui.empty_state("Sin datos diarios para el rango elegido.")

st.subheader("Tipos de consulta")
st.caption("Calculado a partir de los eventos `inquiry.created` más recientes (máx. 200).")
rows = []
for event in events_res.data["items"]:
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    kind = payload.get("type") or payload.get("inquiry_type") or "sin tipo"
    channel = payload.get("channel") or "—"
    rows.append({"Tipo": INQUIRY_TYPE_LABELS.get(kind, kind), "Canal": channel})
if rows:
    table = pd.DataFrame(rows).value_counts().reset_index(name="Consultas").sort_values("Consultas", ascending=False)
    st.dataframe(table, hide_index=True)
else:
    ui.empty_state("Aún no hay eventos de consulta registrados.")
