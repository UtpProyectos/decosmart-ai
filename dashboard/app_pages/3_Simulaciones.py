"""Simulaciones de ambientes con IA: estados, calificaciones y últimos resultados."""

import base64
from html import escape

import pandas as pd
import streamlit as st

import api
import charts
import ui
from icons import icon

STATUS_LABELS = {
    "completed": ("Completada", "positive"),
    "failed": ("Fallida", "error"),
    "cancelled": ("Cancelada", "neutral"),
    "blocked_quota": ("Bloqueada por cuota", "warning"),
    "processing": ("Procesando", "neutral"),
    "awaiting_photo": ("Esperando foto", "neutral"),
    "awaiting_dimensions": ("Esperando medidas", "neutral"),
    "awaiting_confirmation": ("Esperando confirmación", "neutral"),
}
GALLERY_SIZE = 8

ui.setup_page("Simulaciones", "Ambientes generados con IA a partir de la foto del cliente.")

summary_res = api.get_summary()
sims_res = api.get_simulations(50)
ui.show_errors(summary_res, sims_res)

s = summary_res.data
items = sims_res.data["items"]
df = pd.DataFrame(items) if items else pd.DataFrame(columns=list(api.SIMULATION_KEYS))
completed = int((df["status"] == "completed").sum()) if not df.empty else 0
failed_recent = int((df["status"] == "failed").sum()) if not df.empty else 0
success = completed / (completed + failed_recent) * 100 if (completed + failed_recent) else None
cost = df.loc[df["status"] == "completed", "cost_usd"] if not df.empty else pd.Series(dtype=float)
generated = max(s["simulations_total"] - s["simulations_reused"], 0)

ui.kpi_grid(
    [
        ui.kpi_card(
            "image",
            "Simulaciones (total)",
            ui.fmt_int(s["simulations_total"]),
            hint=f"{ui.fmt_int(generated)} generadas con el modelo",
        ),
        ui.kpi_card(
            "check-circle",
            "Tasa de éxito",
            "—" if success is None else f"{success:.0f} %",
            tone="positive",
            hint=f"{completed} completadas de las últimas {len(df)}",
        ),
        ui.kpi_card(
            "alert-triangle",
            "Fallidas",
            ui.fmt_int(s["simulations_failed"]),
            tone="error" if s["simulations_failed"] else "neutral",
        ),
        ui.kpi_card("refresh", "Reutilizadas (caché)", ui.fmt_int(s["simulations_reused"]), hint="Costo 0"),
        ui.kpi_card(
            "star",
            "Rating promedio",
            ui.fmt_rating(s["avg_rating"]),
            hint=f"{ui.fmt_int(s['ratings_count'])} calificaciones",
        ),
        ui.kpi_card(
            "coins",
            "Costo promedio",
            ui.fmt_usd(cost.mean(), 4) if not cost.empty else "—",
            hint="Por simulación completada (últimas 50)",
        ),
    ],
    columns=3,
)
st.caption("Las simulaciones son orientativas: la IA puede alterar proporciones o detalles del mueble.")

left, right = st.columns(2, gap="large")
with left:
    ui.section_header("star", "Distribución de calificaciones", "Puntuaciones de 1 a 5")
    scores = pd.to_numeric(df["score"], errors="coerce").dropna() if not df.empty else pd.Series(dtype=float)
    if not scores.empty:
        charts.show(charts.ratings_distribution(scores.tolist()), alt="Distribución de calificaciones de 1 a 5")
    else:
        ui.empty_state("star", "Sin calificaciones todavía", "Los clientes califican cada resultado en Telegram.")
with right:
    ui.section_header("list", "Estados", "Últimas 50 simulaciones")
    if not df.empty:
        counts = df["status"].value_counts()
        rows = []
        for status, n in counts.items():
            label, tone = STATUS_LABELS.get(str(status), (str(status), "neutral"))
            rows.append(
                {"estado": ui.status_pill(label, tone), "n": ui.fmt_int(n), "pct": f"{n / len(df) * 100:.0f} %"}
            )
        ui.html(
            ui.html_table(
                [("estado", "Estado"), ("n", "Cantidad"), ("pct", "Participación")], rows, numeric=("n", "pct")
            )
        )
    else:
        ui.empty_state("image", "Sin simulaciones todavía", "Se crean desde el bot cuando el cliente envía una foto.")


def sim_card(sim: dict) -> str:
    image = api.get_image_bytes(sim["output_url"]) if sim.get("output_url") else None
    if image:
        mime = "image/png" if image[:4] == b"\x89PNG" else "image/jpeg"
        media = f'<img src="data:{mime};base64,{base64.b64encode(image).decode()}" alt="Resultado de la simulación">'
    else:
        media = icon("image", 32)
    label, tone = STATUS_LABELS.get(str(sim.get("status")), (str(sim.get("status")), "neutral"))
    rating = ui.stars(sim["score"]) if sim.get("score") else "<span>Sin calificar</span>"
    reused = " · reutilizada" if sim.get("reused") else ""
    return (
        f'<div class="ds-card ds-sim"><div class="ds-sim-img">{media}</div><div class="ds-sim-body">'
        f'<div class="ds-sim-name">{escape(str(sim.get("product_name") or "Producto"))}</div>'
        f'<div class="ds-sim-meta">{ui.status_pill(label, tone)}<span>{escape(ui.fmt_datetime(sim.get("created_at")))}'
        f"</span></div>"
        f'<div class="ds-sim-meta">{rating}<span>{escape(ui.fmt_usd(sim.get("cost_usd"), 4))}{reused}</span></div>'
        f"</div></div>"
    )


ui.section_header("image", "Últimos resultados", f"Las {GALLERY_SIZE} simulaciones más recientes")
latest = items[:GALLERY_SIZE]
if latest:
    ui.html(f'<div class="ds-gallery">{"".join(sim_card(sim) for sim in latest)}</div>')
else:
    ui.empty_state(
        "image",
        "Aún no hay resultados para mostrar",
        "Cuando el bot genere una simulación, la imagen aparecerá en esta galería.",
    )

with st.expander("Detalle de las últimas simulaciones", icon=":material/table_rows:"):
    if not df.empty:
        view = df[["id", "created_at", "product_name", "status", "score", "cost_usd", "reused"]].rename(
            columns={
                "id": "ID",
                "created_at": "Fecha",
                "product_name": "Producto",
                "status": "Estado",
                "score": "Rating",
                "cost_usd": "Costo (US$)",
                "reused": "Reutilizada",
            }
        )
        st.dataframe(view, hide_index=True, column_config={"Costo (US$)": st.column_config.NumberColumn(format="%.4f")})
    else:
        ui.empty_state("list", "Sin simulaciones registradas")
