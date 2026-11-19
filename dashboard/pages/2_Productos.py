"""Productos: más consultados vs. más solicitados y stock actual."""

import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import api
import ui

ui.setup_page("Productos", "🛋️")

LOW_STOCK_THRESHOLD = api.to_int(os.getenv("LOW_STOCK_THRESHOLD"), 5)

limit = st.slider("Productos en el ranking", min_value=3, max_value=10, value=5)
inquired_res = api.get_top_products("inquired", limit)
requested_res = api.get_top_products("requested", limit)
products_res = api.get_products()
ui.show_errors(inquired_res, requested_res, products_res)
ui.definitions_expander()


def bar(rows: list[dict], color: str, title: str) -> go.Figure:
    df = pd.DataFrame(rows).sort_values("count")
    fig = go.Figure(go.Bar(x=df["count"], y=df["name"], orientation="h", marker_color=color, text=df["count"]))
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(title=dict(text=title, font=dict(size=14)), hovermode="closest")
    fig = ui.style_fig(fig, height=320)
    fig.update_yaxes(gridcolor="rgba(0,0,0,0)")
    fig.update_xaxes(showgrid=True, gridcolor="rgba(43,38,34,0.08)")
    return fig


left, right = st.columns(2)
with left:
    if inquired_res.data:
        st.plotly_chart(bar(inquired_res.data, ui.SLATE, "Más consultados (consultas)"), config={"displayModeBar": False})
    else:
        ui.empty_state("Sin consultas todavía.")
with right:
    if requested_res.data:
        st.plotly_chart(
            bar(requested_res.data, ui.PRIMARY, "Más solicitados (unidades en cotizaciones + pedidos)"),
            config={"displayModeBar": False},
        )
    else:
        ui.empty_state("Sin cotizaciones ni pedidos todavía.")

st.subheader("Stock actual")
if products_res.data:
    df = pd.DataFrame(products_res.data)
    df["low_stock"] = df["low_stock"] | (df["stock"] <= LOW_STOCK_THRESHOLD)
    low = int(df["low_stock"].sum())
    c1, c2, c3 = st.columns(3)
    c1.metric("Productos activos", ui.fmt_int(len(df)))
    c2.metric("Unidades en stock", ui.fmt_int(df["stock"].sum()))
    c3.metric(f"Con stock bajo (≤ {LOW_STOCK_THRESHOLD})", ui.fmt_int(low))

    view = df[["sku", "name", "category", "price", "stock", "low_stock"]].rename(
        columns={
            "sku": "SKU",
            "name": "Producto",
            "category": "Categoría",
            "price": "Precio (US$)",
            "stock": "Stock",
            "low_stock": "Stock bajo",
        }
    )

    def highlight(row: pd.Series) -> list[str]:
        style = f"background-color: rgba(162,59,42,0.12); color: {ui.DANGER}; font-weight: 600"
        return [style if row["Stock bajo"] else "" for _ in row]

    st.dataframe(
        view.style.apply(highlight, axis=1).format({"Precio (US$)": "{:.2f}"}),
        hide_index=True,
        column_config={"Stock bajo": st.column_config.CheckboxColumn("Stock bajo")},
    )
else:
    ui.empty_state("No se pudo obtener el catálogo.")
