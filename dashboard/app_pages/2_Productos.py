"""Productos: más consultados vs. más solicitados y stock actual."""

import os
from html import escape

import streamlit as st

import api
import charts
import ui

ui.setup_page("Productos", "Interés por producto y stock disponible.")

LOW_STOCK_THRESHOLD = api.to_int(os.getenv("LOW_STOCK_THRESHOLD"), 5)

limit = (
    st.segmented_control(
        "Productos en el ranking", options=[3, 5, 10], default=5, format_func=lambda n: f"Top {n}", key="top_limit"
    )
    or 5
)
inquired_res = api.get_top_products("inquired", limit)
requested_res = api.get_top_products("requested", limit)
products_res = api.get_products()
ui.show_errors(inquired_res, requested_res, products_res)

left, right = st.columns(2, gap="large")
with left:
    ui.section_header("search", "Más consultados", "Número de consultas")
    if inquired_res.data:
        charts.show(charts.top_products(inquired_res.data, charts.INK), alt="Productos más consultados")
    else:
        ui.empty_state("search", "Sin consultas todavía", "Aparecerán cuando los clientes pregunten por productos.")
with right:
    ui.section_header("shopping-bag", "Más solicitados", "Unidades en cotizaciones + pedidos demo")
    if requested_res.data:
        charts.show(charts.top_products(requested_res.data, charts.OLIVE), alt="Productos más solicitados")
    else:
        ui.empty_state(
            "shopping-bag",
            "Sin cotizaciones ni pedidos todavía",
            "Se cuentan las unidades incluidas en cotizaciones y pedidos demo.",
        )

ui.section_header("box", "Stock actual", f"Stock bajo: ≤ {LOW_STOCK_THRESHOLD} unidades o marcado por el backend")
products = products_res.data
if products:
    for p in products:
        p["is_low"] = bool(p["low_stock"] or p["stock"] <= LOW_STOCK_THRESHOLD)
    low = sum(1 for p in products if p["is_low"])
    ui.kpi_grid(
        [
            ui.kpi_card("box", "Productos activos", ui.fmt_int(len(products))),
            ui.kpi_card("list", "Unidades en stock", ui.fmt_int(sum(p["stock"] for p in products))),
            ui.kpi_card(
                "alert-triangle",
                "Con stock bajo",
                ui.fmt_int(low),
                tone="warning" if low else "positive",
                hint=f"Umbral ≤ {LOW_STOCK_THRESHOLD} unidades",
            ),
        ],
        columns=3,
    )
    ordered = sorted(products, key=lambda p: (not p["is_low"], p["stock"]))
    rows = []
    for p in ordered:
        if p["stock"] <= 0:
            pill = ui.status_pill("Agotado", "error")
        elif p["is_low"]:
            pill = ui.status_pill("Stock bajo", "warning")
        else:
            pill = ui.status_pill("Disponible", "positive")
        rows.append(
            {
                "sku": f"<code>{escape(str(p['sku']))}</code>",
                "name": escape(str(p["name"])),
                "category": f'<span style="color:{ui.MUTED}">{escape(str(p["category"]))}</span>',
                "price": escape(ui.fmt_usd(p["price"])),
                "stock": ui.fmt_int(p["stock"]),
                "status": pill,
            }
        )
    ui.html(
        ui.html_table(
            [
                ("sku", "SKU"),
                ("name", "Producto"),
                ("category", "Categoría"),
                ("price", "Precio"),
                ("stock", "Stock"),
                ("status", "Estado"),
            ],
            rows,
            numeric=("price", "stock"),
        )
    )
else:
    ui.empty_state("box", "No se pudo obtener el catálogo", "Revisa que la API pública /api/products esté disponible.")
