"""Costos de API (OpenAI): gasto estimado vs. presupuesto, por operación, modelo y día."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import api
import ui

OPERATION_LABELS = {"chat": "Chat (agente)", "image_edit": "Edición de imagen", "moderation": "Moderación"}

ui.setup_page("Costos de API", "💵")

days = st.select_slider("Rango", options=[7, 14, 30, 60, 90], value=30, format_func=lambda d: f"{d} días")
usage_res = api.get_usage(days)
summary_res = api.get_summary()
ui.show_errors(usage_res, summary_res)

u = usage_res.data
s = summary_res.data
# El gasto acumulado y el presupuesto vienen del resumen (todo el histórico); el uso por rango, de /admin/usage.
spent = s["api_cost_usd"] if summary_res.ok else u["total_usd"]
budget = s["budget_usd"] or u["budget_usd"]
used_pct = s["budget_used_pct"] if summary_res.ok else u["budget_used_pct"]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Gasto acumulado estimado", ui.fmt_usd(spent, 4))
c2.metric("Presupuesto", ui.fmt_usd(budget))
c3.metric("Usado", ui.fmt_pct(used_pct))
c4.metric("Modo IA", str(u["ai_mode"] if u["ai_mode"] != "—" else s["ai_mode"]).upper())
ui.budget_progress(used_pct, spent, budget)

verified = u.get("pricing_verified_at") or "desconocida"
st.caption(
    f"Precios de referencia verificados el **{verified}**. Los montos son estimaciones; "
    "en modo `mock` no hay gasto real."
)

c1, c2, c3 = st.columns(3)
c1.metric(f"Gasto en {days} días", ui.fmt_usd(u["total_usd"], 4))
sims_done = max(s["simulations_total"] - s["simulations_failed"] - s["simulations_reused"], 0)
image_cost = sum(r["cost_usd"] for r in u["by_operation"] if r["operation"] == "image_edit")
chat_cost = sum(r["cost_usd"] for r in u["by_operation"] if r["operation"] == "chat")
c2.metric(
    "Costo promedio por simulación",
    ui.fmt_usd(image_cost / sims_done, 4) if sims_done else "—",
    help="Costo de edición de imagen del rango / simulaciones generadas (sin reutilizadas).",
)
c3.metric(
    "Costo promedio por conversación",
    ui.fmt_usd(chat_cost / s["conversations_total"], 4) if s["conversations_total"] else "—",
    help="Costo de chat del rango / conversaciones totales.",
)

left, right = st.columns(2)
with left:
    st.subheader("Por operación")
    if u["by_operation"]:
        df = pd.DataFrame(u["by_operation"])
        df["operation"] = df["operation"].map(lambda v: OPERATION_LABELS.get(v, v))
        fig = go.Figure(
            go.Bar(x=df["operation"], y=df["cost_usd"], marker_color=ui.PRIMARY, customdata=df["calls"],
                   hovertemplate="%{x}<br>US$ %{y:.4f}<br>%{customdata} llamadas<extra></extra>")
        )
        fig.update_layout(hovermode="closest")
        st.plotly_chart(ui.style_fig(fig, height=280), config={"displayModeBar": False})
        st.dataframe(
            df.rename(columns={"operation": "Operación", "cost_usd": "Costo (US$)", "calls": "Llamadas"}),
            hide_index=True,
            column_config={"Costo (US$)": st.column_config.NumberColumn(format="%.4f")},
        )
    else:
        ui.empty_state("Sin consumo registrado.")
with right:
    st.subheader("Por modelo")
    if u["by_model"]:
        df = pd.DataFrame(u["by_model"])
        st.dataframe(
            df.rename(columns={"model": "Modelo", "cost_usd": "Costo (US$)", "calls": "Llamadas"}),
            hide_index=True,
            column_config={"Costo (US$)": st.column_config.NumberColumn(format="%.4f")},
        )
    else:
        ui.empty_state("Sin consumo registrado.")

st.subheader("Por día")
if u["by_day"]:
    df = pd.DataFrame(u["by_day"])
    df["acumulado"] = df["cost_usd"].cumsum()
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["date"], y=df["cost_usd"], name="Gasto diario", marker_color=ui.SAND))
    fig.add_trace(go.Scatter(x=df["date"], y=df["acumulado"], name="Acumulado del rango", mode="lines",
                             line=dict(color=ui.PRIMARY, width=2)))
    if budget:
        fig.add_hline(y=budget, line_dash="dot", line_color=ui.DANGER, annotation_text="Presupuesto")
    st.plotly_chart(ui.style_fig(fig), config={"displayModeBar": False})
else:
    ui.empty_state("Sin consumo diario en el rango.")
