"""Historial de eventos de automatización y errores de procesamiento."""

import json
from html import escape

import pandas as pd
import streamlit as st

import api
import ui
from icons import icon

EVENT_TYPES = [
    "conversation.started",
    "inquiry.created",
    "quote.created",
    "quote.status_changed",
    "order.created",
    "order.status_changed",
    "simulation.completed",
    "simulation.failed",
    "simulation.rated",
    "product.low_stock",
    "budget.warning",
    "summary.daily",
]
PAGE_SIZE = 50

ui.setup_page("Eventos y errores", "Automatización, errores de procesamiento y documentos comerciales.")

tab_events, tab_errors, tab_commerce = st.tabs(["Eventos", "Errores", "Cotizaciones y pedidos"])

with tab_events:
    c1, c2, c3 = st.columns([2, 2, 1], vertical_alignment="bottom")
    selected = c1.selectbox(
        "Tipo de evento",
        ["Todos", *EVENT_TYPES],
        format_func=lambda t: t if t == "Todos" else f"{ui.event_meta(t)[1]} · {t}",
    )
    text = c2.text_input("Buscar en la página", placeholder="Tipo, entidad o payload", key="event_search")
    page = c3.number_input("Página", min_value=1, value=1, step=1)
    type_filter = None if selected == "Todos" else selected
    events_res = api.get_events(type_filter, PAGE_SIZE, (int(page) - 1) * PAGE_SIZE)
    ui.show_errors(events_res)
    events = events_res.data
    st.caption(f"{ui.fmt_int(events['total'])} eventos en total · {PAGE_SIZE} por página")
    items = events["items"]
    if text:
        needle = text.lower()
        items = [e for e in items if needle in json.dumps(e, ensure_ascii=False, default=str).lower()]
    if items:
        rows = []
        for ev in items:
            ico, label, tone = ui.event_meta(ev.get("type"))
            payload = ev.get("payload")
            payload_text = json.dumps(payload, ensure_ascii=False) if payload not in (None, {}) else ""
            entity = ui.entity_label(ev) if ev.get("entity_type") else "—"
            rows.append(
                {
                    "id": ui.fmt_int(ev.get("id")),
                    "date": escape(ui.fmt_datetime(ev.get("created_at"))),
                    "type": f'<span class="ds-type">{icon(ico, 16)}{ui.status_pill(label, tone)}</span>',
                    "entity": escape(entity),
                    "customer": escape(str(ev.get("customer_id") or "—")),
                    "notified": ui.status_pill("Sí", "positive") if ev.get("notified") else ui.status_pill("No"),
                    "payload": f"<code>{escape(payload_text[:160])}</code>",
                }
            )
        ui.html(
            ui.html_table(
                [
                    ("id", "ID"),
                    ("date", "Fecha"),
                    ("type", "Tipo"),
                    ("entity", "Entidad"),
                    ("customer", "Cliente"),
                    ("notified", "Notificado"),
                    ("payload", "Payload"),
                ],
                rows,
                numeric=("id",),
            )
        )
    else:
        ui.empty_state("list", "Sin eventos para el filtro elegido", "Cambia el tipo, la búsqueda o la página.")

with tab_errors:
    errors_res = api.get_errors(200)
    ui.show_errors(errors_res)
    errors = errors_res.data
    st.caption(f"{ui.fmt_int(errors['total'])} errores registrados (se muestran los últimos 200)")
    if errors["items"]:
        df = pd.DataFrame(errors["items"])
        sources = sorted(str(v) for v in df["source"].dropna().unique())
        chosen = st.pills("Origen", sources, default=sources, selection_mode="multi", key="error_sources")
        df = df[df["source"].astype(str).isin(chosen or [])]
        counts = df["source"].value_counts()
        if not counts.empty:
            ui.html(
                '<div class="ds-meta" style="justify-content:flex-start">'
                + "".join(ui.status_pill(f"{src} · {n}", "error") for src, n in counts.items())
                + "</div>"
            )
        if not df.empty:
            st.dataframe(
                df.rename(
                    columns={
                        "id": "ID",
                        "created_at": "Fecha",
                        "source": "Origen",
                        "error_type": "Tipo",
                        "message": "Mensaje",
                    }
                )[["ID", "Fecha", "Origen", "Tipo", "Mensaje"]],
                hide_index=True,
            )
        else:
            ui.empty_state("alert-triangle", "Ningún origen seleccionado", "Elige al menos un origen para ver errores.")
    elif errors_res.ok:
        ui.empty_state(
            "check-circle", "Sin errores de procesamiento", "El bot, el agente y el simulador no registran fallas."
        )
    else:
        ui.empty_state(
            "alert-triangle", "No se pudieron cargar los errores", "La API no respondió; intenta actualizar."
        )

with tab_commerce:
    ui.definitions()
    quotes_res = api.get_quotes()
    orders_res = api.get_orders()
    ui.show_errors(quotes_res, orders_res)
    left, right = st.columns(2, gap="large")
    with left:
        ui.section_header("file-text", "Cotizaciones", f"{ui.fmt_int(quotes_res.data['total'])} en total")
        if quotes_res.data["items"]:
            st.dataframe(ui.table_frame(quotes_res.data["items"]), hide_index=True)
        else:
            ui.empty_state("file-text", "Sin cotizaciones", "El bot las genera con precios congelados del catálogo.")
    with right:
        ui.section_header("shopping-bag", "Pedidos demo", f"{ui.fmt_int(orders_res.data['total'])} en total")
        if orders_res.data["items"]:
            st.dataframe(ui.table_frame(orders_res.data["items"]), hide_index=True)
        else:
            ui.empty_state("shopping-bag", "Sin pedidos demo", "Un pedido demo es una intención de compra, sin pago.")
