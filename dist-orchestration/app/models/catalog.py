"""Product catalog with mandatory compliance + pricing fields.

A SKU may not reach catalog_status=listed until it passes the compliance
gate (CPSIA for toys; CA metals + FTC labeling for jewelry). See the
compliance service (increment 2).
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, IdMixin, TimestampMixin
from app.enums import CatalogStatus, CpsiaStatus, DistributorTier
from app.models._types import (
    catalog_status_type,
    cpsia_status_type,
    distributor_tier_type,
)

if TYPE_CHECKING:
    from app.models.drop import DailySkuDrop


class Product(IdMixin, TimestampMixin, Base):
    __tablename__ = "product"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    brand: Mapped[Optional[str]] = mapped_column(String(128))

    skus: Mapped[list["SKU"]] = relationship(back_populates="product")


class SKU(IdMixin, TimestampMixin, Base):
    __tablename__ = "sku"

    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), nullable=False)
    sku_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    # --- Compliance / customs (mandatory) ---
    hts_code: Mapped[str] = mapped_column(String(20), nullable=False)
    duty_rate: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    landed_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    cpsia_status: Mapped[CpsiaStatus] = mapped_column(
        cpsia_status_type,
        nullable=False,
        default=CpsiaStatus.not_required,
    )
    ca_metals_compliant: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    prop65_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ftc_jewelry_labeled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    # --- Pricing ---
    price_floor: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    # --- Daily-drop scheduling ---
    # Per-SKU default daily exposure, tuned by cash cycle (NOT a global knob).
    daily_drop_qty: Mapped[int] = mapped_column(nullable=False, default=0)

    # Physical on-hand mirrored from the OMS/3PL inventory feed. `version` is
    # used for optimistic-lock / tx-validation when generating the next-day
    # plan (read version -> validate -> write).
    total_on_hand: Mapped[int] = mapped_column(nullable=False, default=0)
    version: Mapped[int] = mapped_column(nullable=False, default=0)

    catalog_status: Mapped[CatalogStatus] = mapped_column(
        catalog_status_type,
        nullable=False,
        default=CatalogStatus.draft,
    )

    product: Mapped["Product"] = relationship(back_populates="skus")
    wholesale_prices: Mapped[list["WholesalePrice"]] = relationship(
        back_populates="sku"
    )
    drops: Mapped[list["DailySkuDrop"]] = relationship(back_populates="sku")

    __table_args__ = (
        CheckConstraint("daily_drop_qty >= 0", name="daily_drop_qty_non_negative"),
        CheckConstraint("total_on_hand >= 0", name="total_on_hand_non_negative"),
        CheckConstraint("duty_rate >= 0", name="duty_rate_non_negative"),
        CheckConstraint("price_floor >= 0", name="price_floor_non_negative"),
    )


class WholesalePrice(IdMixin, Base):
    """Tier-layered wholesale price for a SKU."""

    __tablename__ = "wholesale_price"

    sku_id: Mapped[int] = mapped_column(ForeignKey("sku.id"), nullable=False)
    tier: Mapped[DistributorTier] = mapped_column(
        distributor_tier_type, nullable=False
    )
    wholesale_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    sku: Mapped["SKU"] = relationship(back_populates="wholesale_prices")

    __table_args__ = (
        UniqueConstraint("sku_id", "tier", name="uq_wholesale_price_sku_tier"),
        CheckConstraint("wholesale_price >= 0", name="wholesale_price_non_negative"),
    )


class ComplianceRecord(IdMixin, Base):
    """Audit trail of each compliance evaluation run for a SKU."""

    __tablename__ = "compliance_record"

    sku_id: Mapped[int] = mapped_column(ForeignKey("sku.id"), nullable=False)
    check_type: Mapped[str] = mapped_column(String(64), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    details: Mapped[Optional[dict]] = mapped_column(JSONB)
    evaluated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_compliance_record_sku_id", "sku_id"),)
