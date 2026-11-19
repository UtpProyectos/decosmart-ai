"""DecoSmart AI · Dashboard — Resumen (KPIs principales)."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import api
import ui

ui.setup_page("Resumen", "📊")

summary_res = api.get_summary()
daily_res = api.get_daily(14)
inquired_res = api.get_top_products("inquired", 5)
requested_res = api.get_top_products("requested", 5)
ui.show_errors(summary_res, daily_res, inquired_res, requested_res)

s = summary_res.data
ui.definitions_expander()

st.subheader("Embudo comercial")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Conversaciones", ui.fmt_int(s["conversations_total"]), help=f"Clientes únicos: {s['unique_customers']}")
c2.metric("Consultas", ui.fmt_int(s["inquiries_total"]), help="Preguntas concretas sobre productos/categorías.")
c3.metric("Cotizaciones", ui.fmt_int(s["quotes_total"]), help=f"Aceptadas: {s['quotes_accepted']}")
c4.metric("Pedidos demo", ui.fmt_int(s["orders_total"]), help="Intenciones de compra sin pago.")
c5.metric("Ventas concretadas", ui.fmt_int(s["orders_completed"]), help="Pedidos marcados como completed por un admin.")

st.subheader("IA y operación")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric(
    "Simulaciones",
    ui.fmt_int(s["simulations_total"]),
    help=f"Fallidas: {s['simulations_failed']} · Reutilizadas (caché): {s['simulations_reused']}",
)
c2.metric("Rating promedio IA", ui.fmt_rating(s["avg_rating"]), help=f"Calificaciones: {s['ratings_count']}")
c3.metric("Gasto API estimado", ui.fmt_usd(s["api_cost_usd"], 4), help="Solo llamadas reales (modo live).")
c4.metric("% del presupuesto", ui.fmt_pct(s["budget_used_pct"]), help=f"Límite: {ui.fmt_usd(s['budget_usd'])}")
c5.metric("Errores de procesamiento", ui.fmt_int(s["errors_total"]))

ui.budget_progress(s["budget_used_pct"], s["api_cost_usd"], s["budget_usd"])
st.caption(f"Modo de IA actual: **{s['ai_mode']}**")

st.subheader("Actividad diaria (últimos 14 días)")
if daily_res.data:
    df = pd.DataFrame(daily_res.data)
    fig = go.Figure()
    for i, (key, label) in enumerate(ui.SERIES_LABELS.items()):
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df[key],
                name=label,
                mode="lines+markers",
                line=dict(color=ui.SERIES_COLORS[i % len(ui.SERIES_COLORS)], width=2),
            )
        )
    st.plotly_chart(ui.style_fig(fig), config={"displayModeBar": False})
else:
    ui.empty_state("Sin actividad registrada en los últimos 14 días.")

st.subheader("Productos destacados")
left, right = st.columns(2)
with left:
    st.markdown("**Más consultados**")
    if inquired_res.data:
        st.dataframe(
            pd.DataFrame(inquired_res.data)[["name", "sku", "count"]].rename(
                columns={"name": "Producto", "sku": "SKU", "count": "Consultas"}
            ),
            hide_index=True,
        )
    else:
        ui.empty_state("Sin consultas todavía.")
with right:
    st.markdown("**Más solicitados** (unidades en cotizaciones + pedidos)")
    if requested_res.data:
        st.dataframe(
            pd.DataFrame(requested_res.data)[["name", "sku", "count"]].rename(
                columns={"name": "Producto", "sku": "SKU", "count": "Unidades"}
            ),
            hide_index=True,
        )
    else:
        ui.empty_state("Sin cotizaciones ni pedidos todavía.")
