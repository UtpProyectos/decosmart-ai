from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin, UpdatedMixin
from app.models.catalog import Product
from app.models.customers import Customer


class Simulation(UpdatedMixin, Base):
    __tablename__ = "simulations"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="awaiting_photo")
    room_width_cm: Mapped[int | None] = mapped_column(Integer)
    room_height_cm: Mapped[int | None] = mapped_column(Integer)
    room_depth_cm: Mapped[int | None] = mapped_column(Integer)
    placement_hint: Mapped[str | None] = mapped_column(String(120))
    input_key: Mapped[str | None] = mapped_column(String(255))
    input_hash: Mapped[str | None] = mapped_column(String(64))
    cache_key: Mapped[str | None] = mapped_column(String(64), index=True)
    output_key: Mapped[str | None] = mapped_column(String(255))
    output_full_key: Mapped[str | None] = mapped_column(String(255))
    prompt: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(String(50))
    size: Mapped[str | None] = mapped_column(String(20))
    quality: Mapped[str | None] = mapped_column(String(10))
    input_bytes: Mapped[int | None] = mapped_column(Integer)
    output_bytes: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=0)
    reused_from_id: Mapped[int | None] = mapped_column(ForeignKey("simulations.id"))
    error_message: Mapped[str | None] = mapped_column(Text)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    customer: Mapped[Customer] = relationship()
    product: Mapped[Product] = relationship()
    rating: Mapped["SimulationRating | None"] = relationship(back_populates="simulation", uselist=False)


class SimulationRating(TimestampMixin, Base):
    __tablename__ = "simulation_ratings"
    __table_args__ = (CheckConstraint("score BETWEEN 1 AND 5", name="ck_rating_score"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    simulation_id: Mapped[int] = mapped_column(ForeignKey("simulations.id"), unique=True)
    score: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str | None] = mapped_column(Text)

    simulation: Mapped[Simulation] = relationship(back_populates="rating")
