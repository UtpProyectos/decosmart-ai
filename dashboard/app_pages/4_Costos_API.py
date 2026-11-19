"""Costos de API (OpenAI): gasto estimado vs. presupuesto, por operación, modelo y día."""

from html import escape

import streamlit as st

import api
import charts
import ui

OPERATION_LABELS = {"chat": "Chat (agente)", "image_edit": "Edición de imagen", "moderation": "Moderación"}

ui.setup_page("Costos API", "Gasto estimado de OpenAI frente al presupuesto.")

days = (
    st.segmented_control(
        "Rango", options=[7, 14, 30, 60, 90], default=30, format_func=lambda d: f"{d} días", key="cost_days"
    )
    or 30
)
usage_res = api.get_usage(days)
summary_res = api.get_summary()
ui.show_errors(usage_res, summary_res)

u = usage_res.data
s = summary_res.data
# El gasto acumulado y el presupuesto vienen del resumen (todo el histórico); el uso por rango, de /admin/usage.
spent = s["api_cost_usd"] if summary_res.ok else u["total_usd"]
budget = s["budget_usd"] or u["budget_usd"]
used_pct = s["budget_used_pct"] if summary_res.ok else u["budget_used_pct"]
mode = str(u["ai_mode"] if u["ai_mode"] != "—" else s["ai_mode"])

sims_done = max(s["simulations_total"] - s["simulations_failed"] - s["simulations_reused"], 0)
image_cost = sum(r["cost_usd"] for r in u["by_operation"] if r["operation"] == "image_edit")
chat_cost = sum(r["cost_usd"] for r in u["by_operation"] if r["operation"] == "chat")

ui.kpi_grid(
    [
        ui.kpi_card(
            "coins",
            "Gasto acumulado estimado",
            ui.fmt_usd(spent, 4),
            delta=ui.fmt_pct(used_pct),
            tone=ui.budget_tone(used_pct),
            hint=f"de {ui.fmt_usd(budget)} de presupuesto",
        ),
        ui.kpi_card("trending-up", f"Gasto en {days} días", ui.fmt_usd(u["total_usd"], 4)),
        ui.kpi_card(
            "image",
            "Costo promedio por simulación",
            ui.fmt_usd(image_cost / sims_done, 4) if sims_done else "—",
            hint="Edición de imagen del rango / simulaciones generadas",
        ),
        ui.kpi_card(
            "chat",
            "Costo promedio por conversación",
            ui.fmt_usd(chat_cost / s["conversations_total"], 4) if s["conversations_total"] else "—",
            hint="Chat del rango / conversaciones totales",
        ),
    ]
)

ui.section_header("coins", "Presupuesto", f"Modo de IA: {mode}")
ui.budget_progress(used_pct, spent, budget)
verified = u.get("pricing_verified_at") or "desconocida"
st.caption(
    f"Precios de referencia verificados el {verified}. Los montos son estimaciones; en modo mock no hay gasto real."
)

left, right = st.columns(2, gap="large")
with left:
    ui.section_header("activity", "Por operación")
    if u["by_operation"]:
        charts.show(charts.spend_by_operation(u["by_operation"], OPERATION_LABELS), alt="Gasto por operación")
    else:
        ui.empty_state("activity", "Sin consumo registrado", "En modo mock las llamadas no generan costo.")
with right:
    ui.section_header("settings", "Por modelo")
    if u["by_model"]:
        rows = [
            {
                "model": f"<code>{escape(str(r['model']))}</code>",
                "calls": ui.fmt_int(r["calls"]),
                "cost": escape(ui.fmt_usd(r["cost_usd"], 4)),
            }
            for r in sorted(u["by_model"], key=lambda r: r["cost_usd"], reverse=True)
        ]
        ui.html(
            ui.html_table(
                [("model", "Modelo"), ("calls", "Llamadas"), ("cost", "Costo")], rows, numeric=("calls", "cost")
            )
        )
    else:
        ui.empty_state("settings", "Sin consumo registrado", "Se listará cada modelo usado y su costo.")
    if u["by_operation"]:
        rows = [
            {
                "op": escape(OPERATION_LABELS.get(r["operation"], r["operation"])),
                "calls": ui.fmt_int(r["calls"]),
                "cost": escape(ui.fmt_usd(r["cost_usd"], 4)),
            }
            for r in u["by_operation"]
        ]
        ui.html(
            ui.html_table(
                [("op", "Operación"), ("calls", "Llamadas"), ("cost", "Costo")], rows, numeric=("calls", "cost")
            )
        )

ui.section_header("clock", "Por día", f"Últimos {days} días")
if u["by_day"]:
    charts.show(charts.spend_by_day(u["by_day"], budget), alt="Gasto diario y acumulado")
else:
    ui.empty_state("clock", "Sin consumo diario en el rango", "Prueba con un rango más amplio.")
