"""Telegram inline-keyboard builders."""


def _button(text: str, data: str) -> dict:
    return {"text": text, "callback_data": data}


def main_menu() -> dict:
    return {"inline_keyboard": [[_button("Ver catálogo", "catalog"), _button("Recomiéndame", "recommend")],
                                [_button("Simular en mi ambiente", "simulate:selected"),
                                 _button("Cotizar", "quote:selected")]]}


def categories(items: list[dict]) -> dict:
    rows = [[_button(c["name"], f"category:{c['slug']}")] for c in items]
    return {"inline_keyboard": rows}


def products(items) -> dict:
    return {"inline_keyboard": [[_button(p.name, f"product:{p.id}")] for p in items]}


def product_actions(product_id: int) -> dict:
    return {"inline_keyboard": [[_button("Simular", f"simulate:{product_id}"),
                                 _button("Cotizar", f"quote:{product_id}")],
                                [_button("Ver más", f"product:{product_id}")]]}


def product_card_actions(product_id: int) -> dict:
    """Botones de la tarjeta de producto en listados (doc 04 v0.2, sección Telegram)."""
    return {"inline_keyboard": [[_button("Ver detalle", f"product:{product_id}"),
                                 _button("Simular", f"simulate:{product_id}"),
                                 _button("Cotizar", f"quote:{product_id}")]]}


def consent() -> dict:
    return {"inline_keyboard": [[_button("Acepto", "consent:yes"), _button("Cancelar", "sim:cancel")]]}


def confirm_simulation(simulation_id: int) -> dict:
    return {"inline_keyboard": [[_button("Generar", f"sim:go:{simulation_id}"),
                                 _button("Cancelar", "sim:cancel")]]}


def stars(simulation_id: int) -> dict:
    return {"inline_keyboard": [[_button(f"⭐{n}", f"rate:{simulation_id}:{n}") for n in range(1, 6)],
                                [_button("Generar otra versión", f"sim:again:{simulation_id}")]]}


def order_from_quote(code: str) -> dict:
    return {"inline_keyboard": [[_button("Crear pedido demo", f"order:{code}")]]}
