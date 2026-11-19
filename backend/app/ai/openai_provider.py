"""Official OpenAI SDK implementation. Never used by the test configuration."""

import base64
import json
from contextlib import nullcontext

from openai import OpenAI
from sqlalchemy.orm import Session

from app.ai.provider import ChatResult, ImageResult
from app.core import pricing
from app.core.config import get_settings
from app.services import budget


def _value(obj, name: str, default=0):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


class OpenAIProvider:
    def __init__(self, db: Session | None = None, customer_id: int | None = None,
                 simulation_id: int | None = None, client=None):
        self.settings = get_settings()
        self.db = db
        self.customer_id = customer_id
        self.simulation_id = simulation_id
        self.client = client or OpenAI(api_key=self.settings.openai_api_key)

    def _track(self, operation: str, model: str):
        if self.db is None:
            return nullcontext(None)
        return budget.track(self.db, operation=operation, model=model, mode="live",
                            customer_id=self.customer_id, simulation_id=self.simulation_id)

    def chat(self, instructions: str, input_items: list[dict], tools: list[dict]) -> ChatResult:
        kwargs = {
            "model": self.settings.openai_chat_model,
            "instructions": instructions,
            "input": input_items,
            "tools": tools,
            "max_output_tokens": self.settings.openai_chat_max_output_tokens,
        }
        if self.settings.openai_reasoning_effort:
            kwargs["reasoning"] = {"effort": self.settings.openai_reasoning_effort}
        with self._track("chat", self.settings.openai_chat_model) as tracker:
            response = self.client.responses.create(**kwargs)
            usage = response.usage
            parsed = {
                "input_tokens": int(_value(usage, "input_tokens")),
                "output_tokens": int(_value(usage, "output_tokens")),
                "cached_input_tokens": int(_value(_value(usage, "input_tokens_details", {}), "cached_tokens")),
            }
            if tracker is not None:
                tracker.input_tokens = parsed["input_tokens"]
                tracker.output_tokens = parsed["output_tokens"]
                tracker.cached_input_tokens = parsed["cached_input_tokens"]
                tracker.cost_usd = pricing.estimate_chat(self.settings.openai_chat_model, **parsed)
            items = []
            for item in response.output or []:
                if _value(item, "type", "") == "function_call":
                    arguments = _value(item, "arguments", "{}")
                    try:
                        arguments = json.loads(arguments) if isinstance(arguments, str) else arguments
                    except json.JSONDecodeError:
                        arguments = {}
                    items.append({"type": "function_call", "name": _value(item, "name", ""),
                                  "arguments": arguments, "call_id": _value(item, "call_id", "")})
            return ChatResult(items, response.output_text or "", parsed)

    def edit_image(self, room: bytes, reference: bytes | None, prompt: str, size: str, quality: str) -> ImageResult:
        images = [("room.jpg", room, "image/jpeg")]
        if reference is not None:
            images.append(("product.jpg", reference, "image/jpeg"))
        with self._track("image_edit", self.settings.openai_image_model) as tracker:
            response = self.client.images.edit(model=self.settings.openai_image_model, image=images, prompt=prompt,
                                               size=size, quality=quality, n=1)
            usage_obj = getattr(response, "usage", None)
            usage = {
                "input_tokens": int(_value(usage_obj, "input_tokens")),
                "output_tokens": int(_value(usage_obj, "output_tokens")),
                "image_input_tokens": int(_value(usage_obj, "input_images_tokens")),
            }
            if tracker is not None:
                tracker.input_tokens = usage["input_tokens"]
                tracker.output_tokens = usage["output_tokens"]
                tracker.image_input_tokens = usage["image_input_tokens"]
                tracker.images, tracker.quality, tracker.size = 1, quality, size
                tracker.cost_usd = pricing.estimate_image_edit(self.settings.openai_image_model, quality, size, usage)
            return ImageResult(base64.b64decode(response.data[0].b64_json), usage)

    def moderate(self, text: str) -> bool:
        with self._track("moderation", "omni-moderation-latest"):
            response = self.client.moderations.create(model="omni-moderation-latest", input=text)
        return not bool(response.results[0].flagged)
