"""Fixed, non-LLM Telegram copy from docs/05 §6."""

from app.services.quotes import format_quote_text

WELCOME = ("¡Hola! Soy Deco 🛋️, tu asistente de DecoSmart. Puedo mostrarte el catálogo, recomendarte muebles "
           "según tu presupuesto, simular cómo quedaría un mueble en tu ambiente y prepararte una cotización. "
           "¿Qué buscas hoy?")
PHOTO_CONSENT = ("Para simular necesito una foto de tu ambiente. La usaremos solo para generar la simulación y "
                 "se eliminará en {days} días. Evita que aparezcan personas o documentos. ¿Aceptas?")
ASK_PHOTO = ("Envíame una foto de la sala o habitación donde iría el {product}. "
             "📷 Toma la foto de frente, con buena luz.")
ASK_DIMENSIONS = ("Indica el ancho y alto aproximado del espacio visible en cm, y la profundidad si la conoces. "
                  "Ejemplo: `300 x 250` o `300 x 250 x 400`.")
CONFIRM_SIMULATION = ("Voy a generar la simulación del {product} ({dims}) en tu ambiente ({room_dims}). Es orientativa "
                      "y no garantiza que el mueble encaje físicamente. Te quedan {left} simulación(es). "
                      "¿Genero la imagen?")
PROCESSING = "Generando tu simulación… puede tardar hasta un minuto ⏳"
RESULT_CAPTION = ("Así podría verse el {product} en tu ambiente. *Simulación orientativa generada con IA.* "
                  "¿Qué tan útil te resultó?")
QUOTA_EXHAUSTED = ("Ya usaste tus {max} simulaciones disponibles. Puedo ayudarte con medidas, recomendaciones o una "
                   "cotización.")
BUDGET_EXHAUSTED = ("La simulación no está disponible en este momento. Puedo ayudarte con el catálogo y cotizaciones.")
AI_UNAVAILABLE = "Ahora mismo no puedo procesar mensajes libres. Usa los botones del menú 👇"
GENERIC_ERROR = "Lo siento, ocurrió un problema. Intenta nuevamente o usa /cancelar para volver al menú."


def product_card(product) -> str:
    colors = ", ".join(product.colors or [])
    return (f"🛋️ {product.name}\nUS$ {product.price:.2f}\n"
            f"Medidas: {product.width_cm} × {product.height_cm} × {product.depth_cm} cm\n"
            f"Colores: {colors}\nStock: {product.stock}")


def stock_text(product) -> str:
    from app.services.catalog import is_low_stock

    if product.stock <= 0:
        return "Agotado"
    if is_low_stock(product):
        return f"Últimas {product.stock} unidades"
    return f"Stock: {product.stock}"


def product_caption(product) -> str:
    """Caption corto para listados con foto."""
    return (f"{product.name}\nUS$ {product.price:.2f} · {product.width_cm}×{product.height_cm}×{product.depth_cm} cm"
            f" · {stock_text(product)}")


def quote_text(quote) -> str:
    return format_quote_text(quote)
