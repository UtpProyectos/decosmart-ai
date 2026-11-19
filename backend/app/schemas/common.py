"""Tipos comunes: dinero como string decimal ("649.00")."""

from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, PlainSerializer


def fmt_money(value: Decimal | float | int | str | None, places: int = 2) -> str:
    q = Decimal(1).scaleb(-places)
    return str(Decimal(str(value if value is not None else 0)).quantize(q, rounding=ROUND_HALF_UP))


Money = Annotated[Decimal, PlainSerializer(lambda v: fmt_money(v, 2), return_type=str, when_used="always")]
MoneyCost = Annotated[Decimal, PlainSerializer(lambda v: fmt_money(v, 4), return_type=str, when_used="always")]


class Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
