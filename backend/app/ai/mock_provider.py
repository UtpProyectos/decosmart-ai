"""Deterministic offline provider used by development and every test/CI run."""

import json
import re
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont
from sqlalchemy.orm import Session

from app.ai.provider import ChatResult, ImageResult
from app.core.config import get_settings
from app.services import budget


class MockProvider:
    def __init__(self, db: Session | None = None, customer_id: int | None = None,
                 simulation_id: int | None = None):
        self.db, self.customer_id, self.simulation_id = db, customer_id, simulation_id

    def _record(self, operation: str) -> None:
        if self.db is not None:
            s = get_settings()
            model = s.openai_chat_model if operation == "chat" else s.openai_image_model
            budget.record_usage(self.db, operation=operation, model=model, mode="mock",
                                customer_id=self.customer_id, simulation_id=self.simulation_id,
                                images=1 if operation == "image_edit" else 0)

    def chat(self, instructions: str, input_items: list[dict], tools: list[dict]) -> ChatResult:
        self._record("chat")
        outputs = [i for i in input_items if i.get("type") == "function_call_output"]
        if outputs:
            data = json.loads(outputs[-1].get("output") or "{}")
            return ChatResult(text=self._render(data), usage={})
        text = " ".join(str(i.get("content", "")) for i in input_items if i.get("role") == "user").lower()
        ref = "DS-SOF-001" if any(x in text for x in ("sofá", "sofa", "oslo")) else None
        call = None
        if any(x in text for x in ("cotiza", "cotización", "cotizacion")) and ref:
            call = ("create_quote", {"items": [{"product_ref": ref, "quantity": 1}], "notes": None})
        elif "simul" in text:
            call = ("start_simulation", {"product_ref": ref})
        elif "recom" in text or "presupuesto" in text:
            amount = re.search(r"\d+(?:[.,]\d+)?", text)
            call = ("recommend_products", {"budget": float(amount.group().replace(",", ".")) if amount else None,
                                            "room": None, "category": None, "max_width_cm": None, "style": None})
        elif any(x in text for x in ("precio", "cuánto", "cuanto", "medida", "stock")):
            if ref:
                call = ("get_product", {"product_ref": ref})
            else:
                call = ("search_products", {"query": text, "category": None, "max_price": None, "room": None})
        else:
            call = ("search_products", {"query": text, "category": None, "max_price": None, "room": None})
        return ChatResult(output_items=[{"type": "function_call", "name": call[0], "arguments": call[1],
                                         "call_id": "mock-call-1"}], usage={})

    @staticmethod
    def _render(data: dict) -> str:
        products = data.get("products", [])
        if data.get("product"):
            products = [data["product"]]
        if products:
            return "\n".join(f"{p['name']}: US$ {p['price_usd']}. Medidas: {p['dims_cm']} cm. Stock: {p['stock']}."
                             for p in products)
        if data.get("quote_code"):
            return f"Listo, preparé la cotización {data['quote_code']}."
        if data.get("order_code"):
            return f"Registré el pedido demo {data['order_code']}, sin cobro."
        if data.get("ok"):
            return "Listo. Continuemos con el siguiente paso."
        return "No encontré un producto real que coincida. Puedo mostrarte el catálogo."

    def edit_image(self, room: bytes, references: list[bytes], prompt: str, size: str, quality: str) -> ImageResult:
        self._record("image_edit")
        image = Image.open(BytesIO(room)).convert("RGB")
        band = max(70, image.height // 9)
        canvas = Image.new("RGB", (image.width, image.height + band), "#1f2937")
        canvas.paste(image, (0, 0))
        if references:
            ref = Image.open(BytesIO(references[0])).convert("RGB")
            ref.thumbnail((max(80, image.width // 4), max(60, image.height // 4)), Image.Resampling.LANCZOS)
            canvas.paste(ref, (image.width - ref.width - 12, image.height - ref.height - 12))
        match = re.search(r"- Producto: ([^(\n]+)", prompt)
        product = match.group(1).strip() if match else "MUEBLE"
        ImageDraw.Draw(canvas).text((16, image.height + band // 3), f"SIMULACIÓN DEMO – {product}",
                                    fill="white", font=ImageFont.load_default())
        output = BytesIO()
        canvas.save(output, "JPEG", quality=88)
        return ImageResult(output.getvalue(), {})

    def moderate(self, text: str) -> bool:
        return True
