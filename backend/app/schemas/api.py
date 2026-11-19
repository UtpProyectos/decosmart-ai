"""Modelos Pydantic de entrada/salida (doc 04). Dinero como string con 2 decimales."""

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, model_validator

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
    id: int | None = None
    url: str
    alt: str | None = None
    is_primary: bool = False
    is_reference: bool = False
    sort_order: int = 0
    width: int | None = None
    height: int | None = None


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
    images: list[ImageOut] = []


class ProductDetailOut(ProductOut):
    description: str
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


SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]


class ProductWrite(BaseModel):
    """Alta de producto (doc 04 v0.2). `slug` opcional: se genera desde `name`."""

    sku: str = Field(min_length=1, max_length=30, pattern=r"^[A-Za-z0-9][A-Za-z0-9_\-]*$")
    category_slug: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=150)
    slug: str | None = Field(default=None, max_length=160, pattern=SLUG_PATTERN)
    description: str = Field(min_length=1, max_length=5000)
    price: Money = Field(gt=Decimal("0"), max_digits=10, decimal_places=2)
    stock: int = Field(ge=0)
    width_cm: int = Field(gt=0, le=10000)
    height_cm: int = Field(gt=0, le=10000)
    depth_cm: int = Field(gt=0, le=10000)
    colors: list[ShortText] = Field(max_length=20)
    material: str | None = Field(default=None, max_length=100)
    style: str | None = Field(default=None, max_length=50)
    room_types: list[ShortText] = Field(default_factory=list, max_length=10)
    active: bool = True


_REQUIRED_ON_PATCH = ("sku", "category_slug", "name", "slug", "description", "price", "stock", "width_cm",
                      "height_cm", "depth_cm", "colors", "room_types", "active")


class ProductPatch(BaseModel):
    """`ProductWrite` parcial. Compatible con el PATCH v0.1 (stock/price/active)."""

    sku: str | None = Field(default=None, min_length=1, max_length=30, pattern=r"^[A-Za-z0-9][A-Za-z0-9_\-]*$")
    category_slug: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=150)
    slug: str | None = Field(default=None, max_length=160, pattern=SLUG_PATTERN)
    description: str | None = Field(default=None, min_length=1, max_length=5000)
    price: Money | None = Field(default=None, gt=Decimal("0"), max_digits=10, decimal_places=2)
    stock: int | None = Field(default=None, ge=0)
    width_cm: int | None = Field(default=None, gt=0, le=10000)
    height_cm: int | None = Field(default=None, gt=0, le=10000)
    depth_cm: int | None = Field(default=None, gt=0, le=10000)
    colors: list[ShortText] | None = Field(default=None, max_length=20)
    material: str | None = Field(default=None, max_length=100)
    style: str | None = Field(default=None, max_length=50)
    room_types: list[ShortText] | None = Field(default=None, max_length=10)
    active: bool | None = None

    @model_validator(mode="after")
    def _no_null_required(self) -> "ProductPatch":
        nulls = [f for f in _REQUIRED_ON_PATCH if f in self.model_fields_set and getattr(self, f) is None]
        if nulls:
            raise ValueError(f"Campos que no admiten null: {', '.join(nulls)}")
        return self


class ImagePatch(BaseModel):
    alt: str | None = Field(default=None, max_length=200)
    is_primary: bool | None = None
    is_reference: bool | None = None
    sort_order: int | None = Field(default=None, ge=0, le=10000)


class ImageOrder(BaseModel):
    image_ids: list[int] = Field(min_length=1, max_length=100)


class CustomerPatch(BaseModel):
    simulations_used: int = Field(ge=0)
