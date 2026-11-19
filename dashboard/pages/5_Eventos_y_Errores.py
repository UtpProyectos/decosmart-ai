"""Historial de eventos de automatización y errores de procesamiento."""

import json

import pandas as pd
import streamlit as st

import api
import ui

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

ui.setup_page("Eventos y errores", "🧾")

tab_events, tab_errors, tab_commerce = st.tabs(["Eventos", "Errores", "Cotizaciones y pedidos"])

with tab_events:
    c1, c2 = st.columns([2, 1])
    selected = c1.selectbox("Tipo de evento", ["Todos", *EVENT_TYPES])
    page = c2.number_input("Página", min_value=1, value=1, step=1)
    type_filter = None if selected == "Todos" else selected
    events_res = api.get_events(type_filter, PAGE_SIZE, (int(page) - 1) * PAGE_SIZE)
    ui.show_errors(events_res)
    events = events_res.data
    st.caption(f"{ui.fmt_int(events['total'])} eventos en total")
    if events["items"]:
        df = pd.DataFrame(events["items"])
        df["payload"] = df["payload"].map(lambda p: json.dumps(p, ensure_ascii=False) if p is not None else "")
        text = st.text_input("Buscar en la página (tipo, entidad o payload)", key="event_search")
        if text:
            mask = df.astype(str).apply(lambda col: col.str.contains(text, case=False, regex=False)).any(axis=1)
            df = df[mask]
        st.dataframe(
            df.rename(
                columns={
                    "id": "ID",
                    "created_at": "Fecha",
                    "type": "Tipo",
                    "entity_type": "Entidad",
                    "entity_id": "ID entidad",
                    "customer_id": "Cliente",
                    "notified": "Notificado",
                    "payload": "Payload",
                }
            )[["ID", "Fecha", "Tipo", "Entidad", "ID entidad", "Cliente", "Notificado", "Payload"]],
            hide_index=True,
        )
    else:
        ui.empty_state("Sin eventos para el filtro elegido.")

with tab_errors:
    errors_res = api.get_errors(200)
    ui.show_errors(errors_res)
    errors = errors_res.data
    st.caption(f"{ui.fmt_int(errors['total'])} errores registrados (se muestran los últimos 200)")
    if errors["items"]:
        df = pd.DataFrame(errors["items"])
        sources = sorted(str(v) for v in df["source"].dropna().unique())
        chosen = st.multiselect("Origen", sources, default=sources)
        df = df[df["source"].astype(str).isin(chosen)]
        if not df.empty:
            st.bar_chart(df["source"].value_counts(), color=ui.DANGER, height=200)
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
        st.success("Sin errores de procesamiento registrados.")

with tab_commerce:
    ui.definitions_expander()
    quotes_res = api.get_quotes()
    orders_res = api.get_orders()
    ui.show_errors(quotes_res, orders_res)
    left, right = st.columns(2)
    with left:
        st.markdown(f"**Cotizaciones** ({ui.fmt_int(quotes_res.data['total'])})")
        if quotes_res.data["items"]:
            st.dataframe(ui.table_frame(quotes_res.data["items"]), hide_index=True)
        else:
            ui.empty_state("Sin cotizaciones.")
    with right:
        st.markdown(f"**Pedidos demo** ({ui.fmt_int(orders_res.data['total'])})")
        if orders_res.data["items"]:
            st.dataframe(ui.table_frame(orders_res.data["items"]), hide_index=True)
        else:
            ui.empty_state("Sin pedidos.")
