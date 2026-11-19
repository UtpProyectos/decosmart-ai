"""Simulaciones de ambientes con IA: estados, calificaciones y últimos resultados."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import api
import ui

STATUS_LABELS = {
    "completed": "Completada",
    "failed": "Fallida",
    "cancelled": "Cancelada",
    "blocked_quota": "Bloqueada por cuota",
    "processing": "Procesando",
    "awaiting_photo": "Esperando foto",
    "awaiting_dimensions": "Esperando medidas",
    "awaiting_confirmation": "Esperando confirmación",
}

ui.setup_page("Simulaciones con IA", "🖼️")

summary_res = api.get_summary()
sims_res = api.get_simulations(50)
ui.show_errors(summary_res, sims_res)

s = summary_res.data
items = sims_res.data["items"]
df = pd.DataFrame(items) if items else pd.DataFrame(columns=list(api.SIMULATION_KEYS))
completed = int((df["status"] == "completed").sum()) if not df.empty else 0

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Simulaciones (total)", ui.fmt_int(s["simulations_total"]))
c2.metric("Completadas (últimas 50)", ui.fmt_int(completed))
c3.metric("Fallidas", ui.fmt_int(s["simulations_failed"]))
c4.metric("Reutilizadas (caché, costo 0)", ui.fmt_int(s["simulations_reused"]))
c5.metric("Rating promedio", ui.fmt_rating(s["avg_rating"]), help=f"Calificaciones: {s['ratings_count']}")
st.caption("Las simulaciones son orientativas: la IA puede alterar proporciones o detalles del mueble.")

left, right = st.columns(2)
with left:
    st.subheader("Distribución de calificaciones")
    scores = pd.to_numeric(df["score"], errors="coerce").dropna().astype(int) if not df.empty else pd.Series(dtype=int)
    if not scores.empty:
        counts = scores.value_counts().reindex(range(1, 6), fill_value=0)
        fig = go.Figure(
            go.Bar(
                x=[f"{'⭐' * n}" for n in counts.index],
                y=counts.values,
                marker_color=[ui.DANGER, ui.SAND, ui.MUTED, ui.SAGE, ui.PRIMARY],
                text=counts.values,
            )
        )
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_layout(hovermode="closest")
        st.plotly_chart(ui.style_fig(fig, height=300), config={"displayModeBar": False})
    else:
        ui.empty_state("Sin calificaciones todavía.")
with right:
    st.subheader("Estados")
    if not df.empty:
        status = df["status"].map(lambda v: STATUS_LABELS.get(v, v)).value_counts().reset_index()
        status.columns = ["Estado", "Cantidad"]
        st.dataframe(status, hide_index=True)
        cost = df.loc[df["status"] == "completed", "cost_usd"]
        if not cost.empty:
            st.metric("Costo promedio por simulación completada", ui.fmt_usd(cost.mean(), 4))
    else:
        ui.empty_state("Sin simulaciones todavía.")

st.subheader("Últimos resultados")
with_output = [i for i in items if i.get("output_url") and i.get("status") == "completed"][:6]
if with_output:
    cols = st.columns(3)
    for idx, sim in enumerate(with_output):
        with cols[idx % 3]:
            image = api.get_image_bytes(sim["output_url"])
            score = f" · {'⭐' * api.to_int(sim['score'])}" if sim.get("score") else ""
            reused = " · reutilizada" if sim.get("reused") else ""
            caption = f"#{sim['id']} · {sim.get('product_name') or 'Producto'}{score}{reused}"
            if image:
                st.image(image, caption=caption, width="stretch")
            else:
                st.info(f"{caption}\n\nImagen no disponible (URL expirada o inaccesible).")
else:
    ui.empty_state("Aún no hay resultados de simulación para mostrar.")

with st.expander("Detalle de las últimas simulaciones"):
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
        ui.empty_state()
