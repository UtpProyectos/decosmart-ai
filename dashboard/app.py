"""DecoSmart AI · Dashboard — punto de entrada: navegación entre páginas (st.navigation)."""

import streamlit as st

import ui

PAGES = [
    st.Page(
        "app_pages/0_Resumen.py",
        title="Resumen",
        icon=":material/space_dashboard:",
        default=True,
        help="KPIs principales del embudo, actividad diaria, presupuesto de IA y últimos eventos.",
    ),
    st.Page(
        "app_pages/1_Conversaciones.py",
        title="Conversaciones",
        icon=":material/forum:",
        help="Serie diaria de conversaciones y consultas, clientes únicos y tipos de consulta.",
    ),
    st.Page(
        "app_pages/2_Productos.py",
        title="Productos",
        icon=":material/chair:",
        help="Productos más consultados y más solicitados, y stock actual con alertas de stock bajo.",
    ),
    st.Page(
        "app_pages/3_Simulaciones.py",
        title="Simulaciones",
        icon=":material/imagesmode:",
        help="Simulaciones de ambientes con IA: estados, calificaciones y galería de resultados.",
    ),
    st.Page(
        "app_pages/4_Costos_API.py",
        title="Costos API",
        icon=":material/payments:",
        help="Gasto estimado de OpenAI frente al presupuesto, por operación, modelo y día.",
    ),
    st.Page(
        "app_pages/5_Eventos_y_Errores.py",
        title="Eventos y errores",
        icon=":material/receipt_long:",
        help="Historial filtrable de eventos de automatización, errores, cotizaciones y pedidos.",
    ),
]

# Sin autenticar no se muestra la navegación: la página activa pide la contraseña.
st.navigation(PAGES, position="sidebar" if ui.is_authenticated() else "hidden").run()
