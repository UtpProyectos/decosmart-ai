"""Interchangeable AI provider contracts and factory."""

from dataclasses import dataclass, field
from typing import Any, Protocol

from sqlalchemy.orm import Session

from app.core.config import get_settings


@dataclass
class ChatResult:
    output_items: list[dict[str, Any]] = field(default_factory=list)
    text: str = ""
    usage: dict[str, int] = field(default_factory=dict)


@dataclass
class ImageResult:
    data: bytes
    usage: dict[str, int] = field(default_factory=dict)


class AIProvider(Protocol):
    def chat(self, instructions: str, input_items: list[dict], tools: list[dict]) -> ChatResult: ...

    def edit_image(
        self, room: bytes, references: list[bytes], prompt: str, size: str, quality: str
    ) -> ImageResult:
        """Edita `room` usando `references` (0..N fotos del mueble, en orden de prioridad)."""
        ...

    def moderate(self, text: str) -> bool: ...


def get_provider(
    db: Session | None = None, *, customer_id: int | None = None, simulation_id: int | None = None
) -> AIProvider:
    if get_settings().ai_mode == "live":
        from app.ai.openai_provider import OpenAIProvider

        return OpenAIProvider(db=db, customer_id=customer_id, simulation_id=simulation_id)
    from app.ai.mock_provider import MockProvider

    return MockProvider(db=db, customer_id=customer_id, simulation_id=simulation_id)
