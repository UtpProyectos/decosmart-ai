"""Modelos Pydantic de entrada/salida (doc 04). Dinero como string con 2 decimales."""

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import Money, Schema

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


# ---------- Catálogo ----------
class CategoryRef(Schema):
    slug: str
    name: str


class CategoryOut(Schema):
    id: int
    slug: str
    name: str
    product_count: int


class Dimensions(Schema):
    width_cm: int
    height_cm: int
    depth_cm: int


class ImageOut(Schema):
    url: str
    alt: str | None = None


class ProductOut(Schema):
    id: int
    sku: str
    slug: str
    name: str
    category: CategoryRef | None
    price: str
    currency: str = "USD"
    stock: int
    in_stock: bool
    low_stock: bool
    dimensions: Dimensions
    colors: list[str]
    material: str | None
    style: str | None
    room_types: list[str]
    primary_image: str | None


class ProductDetailOut(ProductOut):
    description: str
    images: list[ImageOut]
    active: bool = True


class ProductPage(Schema):
    items: list[ProductOut]
    total: int
    limit: int
    offset: int


# ---------- Cotizaciones / pedidos ----------
class CustomerIn(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    email: str = Field(pattern=EMAIL_PATTERN, max_length=200)
    phone: str | None = Field(default=None, max_length=30)


class ItemIn(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(ge=1, le=99)


class QuoteCreate(BaseModel):
    customer: CustomerIn
    items: list[ItemIn] = Field(min_length=1, max_length=20)
    notes: str | None = Field(default=None, max_length=1000)
    channel: Literal["web", "telegram"] = "web"


class QuoteItemOut(Schema):
    product_id: int
    sku: str | None = None
    name: str | None
    quantity: int
    unit_price: str
    line_total: str


class QuoteOut(Schema):
    code: str
    status: str
    channel: str
    items: list[QuoteItemOut]
    subtotal: str
    total: str
    currency: str = "USD"
    valid_until: date
    notes: str | None = None
    disclaimer: str


class OrderCreate(BaseModel):
    quote_code: str | None = Field(default=None, max_length=20)
    customer: CustomerIn | None = None
    items: list[ItemIn] | None = Field(default=None, max_length=20)
    delivery_address: str | None = Field(default=None, max_length=500)
    channel: Literal["web", "telegram"] = "web"

    @model_validator(mode="after")
    def _need_source(self) -> "OrderCreate":
        if not self.quote_code and not self.items:
            raise ValueError("Debes indicar quote_code o items")
        if not self.quote_code and self.customer is None:
            raise ValueError("customer es obligatorio cuando no hay quote_code")
        return self


class OrderItemOut(Schema):
    product_id: int
    name: str | None
    quantity: int
    unit_price: str
    line_total: str


class OrderOut(Schema):
    code: str
    status: str
    channel: str
    total: str
    currency: str = "USD"
    is_demo: bool
    quote_code: str | None = None
    items: list[OrderItemOut]
    message: str


class PublicConfig(Schema):
    telegram_bot_url: str
    store_name: str
    currency: str


# ---------- Admin ----------
class StatusPatch(BaseModel):
    status: str = Field(min_length=1, max_length=20)


class ProductPatch(BaseModel):
    stock: int | None = Field(default=None, ge=0)
    price: Money | None = Field(default=None, gt=Decimal("0"))
    active: bool | None = None


class CustomerPatch(BaseModel):
    simulations_used: int = Field(ge=0)
