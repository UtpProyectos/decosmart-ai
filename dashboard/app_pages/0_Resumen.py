"""Resumen: KPIs principales, actividad diaria, presupuesto de IA y últimos eventos."""

import streamlit as st

import api
import charts
import ui

ui.setup_page("Resumen", "Embudo comercial, uso de la IA y actividad reciente.")

summary_res = api.get_summary()
daily_res = api.get_daily(14)
events_res = api.get_events(None, 6, 0)
ui.show_errors(summary_res, daily_res, events_res)

s = summary_res.data


def rate(num: int, den: int) -> str | None:
    return f"{num / den * 100:.0f} %" if den else None


generated = max(s["simulations_total"] - s["simulations_reused"], 0)
ui.kpi_grid(
    [
        ui.kpi_card(
            "chat",
            "Conversaciones",
            ui.fmt_int(s["conversations_total"]),
            hint=f"{ui.fmt_int(s['unique_customers'])} clientes únicos",
        ),
        ui.kpi_card(
            "search", "Consultas", ui.fmt_int(s["inquiries_total"]), hint="Preguntas concretas sobre productos"
        ),
        ui.kpi_card(
            "file-text",
            "Cotizaciones",
            ui.fmt_int(s["quotes_total"]),
            delta=rate(s["quotes_total"], s["inquiries_total"]),
            hint=f"{ui.fmt_int(s['quotes_accepted'])} aceptadas · tasa vs consultas",
        ),
        ui.kpi_card(
            "shopping-bag",
            "Pedidos demo",
            ui.fmt_int(s["orders_total"]),
            delta=rate(s["orders_total"], s["quotes_total"]),
            hint="Intención de compra, sin pago",
        ),
        ui.kpi_card(
            "check-circle",
            "Ventas concretadas",
            ui.fmt_int(s["orders_completed"]),
            delta=rate(s["orders_completed"], s["orders_total"]),
            tone="positive",
            hint="Pedidos marcados como completed",
        ),
        ui.kpi_card(
            "image",
            "Simulaciones",
            ui.fmt_int(s["simulations_total"]),
            tone="error" if s["simulations_failed"] else "neutral",
            hint=f"{ui.fmt_int(generated)} generadas · {ui.fmt_int(s['simulations_reused'])} reutilizadas · "
            f"{ui.fmt_int(s['simulations_failed'])} fallidas",
        ),
        ui.kpi_card(
            "star",
            "Rating promedio IA",
            ui.fmt_rating(s["avg_rating"]),
            hint=f"{ui.fmt_int(s['ratings_count'])} calificaciones",
        ),
        ui.kpi_card(
            "coins",
            "Gasto API estimado",
            ui.fmt_usd(s["api_cost_usd"], 4),
            delta=ui.fmt_pct(s["budget_used_pct"]),
            tone=ui.budget_tone(s["budget_used_pct"]),
            hint=f"del presupuesto de {ui.fmt_usd(s['budget_usd'])} · modo {s['ai_mode']}",
        ),
    ],
    columns=4,
)

ui.definitions()

left, right = st.columns([3, 2], gap="large")
with left:
    ui.section_header("activity", "Actividad diaria", "Últimos 14 días")
    if daily_res.data:
        charts.show(
            charts.daily_activity(daily_res.data, ui.SERIES_LABELS), alt="Actividad diaria de los últimos 14 días"
        )
    else:
        ui.empty_state(
            "activity",
            "Sin actividad en los últimos 14 días",
            "Las conversaciones, consultas y pedidos aparecerán aquí en cuanto se registren.",
        )
with right:
    ui.section_header("coins", "Presupuesto de IA", f"Modo actual: {s['ai_mode']}")
    ui.budget_progress(s["budget_used_pct"], s["api_cost_usd"], s["budget_usd"])
    if s["errors_total"]:
        errors_text = f"{ui.fmt_int(s['errors_total'])} errores de procesamiento"
        ui.html(f'<div class="ds-meta" style="justify-content:flex-start">{ui.status_pill(errors_text, "error")}</div>')

    ui.section_header("list", "Últimos eventos")
    if events_res.data["items"]:
        ui.html(ui.event_list(events_res.data["items"][:6]))
    else:
        ui.empty_state("list", "Sin eventos recientes", "Los eventos de automatización se listarán aquí.")
