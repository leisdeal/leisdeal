"""Daily-drop scheduling core (replaces the old InventoryAllocation).

DailySkuDrop is the unit of daily exposure for one SKU. DropAssignment ties
a drop to exactly one distributor's show (per platform-scope row).

Uniqueness (two partial unique indexes):
  - global       : one drop per (sku, drop_date) when platform IS NULL
  - per_platform : one drop per (sku, drop_date, platform) when platform set

Inventory hard constraint (enforced by the planning engine in a tx, not by a
single column): for a given (sku, drop_date),
    SUM(drop_qty) <= sku.total_on_hand_at_planning
"""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, IdMixin, TimestampMixin
from app.enums import DropStatus, Platform, PlatformScope
from app.models._types import drop_status_type, platform_scope_type, platform_type

if TYPE_CHECKING:
    from app.models.catalog import SKU
    from app.models.distributor import Distributor
    from app.models.sales import SalesOrder
    from app.models.show import Show


class DailySkuDrop(IdMixin, TimestampMixin, Base):
    __tablename__ = "daily_sku_drop"

    sku_id: Mapped[int] = mapped_column(ForeignKey("sku.id"), nullable=False)
    drop_date: Mapped[dt.date] = mapped_column(Date, nullable=False)

    platform_scope: Mapped[PlatformScope] = mapped_column(
        platform_scope_type, nullable=False
    )
    # NULL when global; required when per_platform (enforced by check below).
    platform: Mapped[Optional[Platform]] = mapped_column(platform_type)

    drop_qty: Mapped[int] = mapped_column(nullable=False)
    sold_qty: Mapped[int] = mapped_column(nullable=False, default=0)

    status: Mapped[DropStatus] = mapped_column(
        drop_status_type,
        nullable=False,
        default=DropStatus.planned,
    )

    sku: Mapped["SKU"] = relationship(back_populates="drops")
    assignments: Mapped[list["DropAssignment"]] = relationship(
        back_populates="drop"
    )
    sales_orders: Mapped[list["SalesOrder"]] = relationship(back_populates="drop")

    __table_args__ = (
        CheckConstraint("drop_qty >= 0", name="drop_qty_non_negative"),
        CheckConstraint("sold_qty >= 0", name="sold_qty_non_negative"),
        # Oversell guard at the row level; the sale path uses a conditional
        # UPDATE (sold_qty + q <= drop_qty) so this can never be violated.
        CheckConstraint("sold_qty <= drop_qty", name="sold_within_drop"),
        # scope/platform consistency
        CheckConstraint(
            "(platform_scope = 'global' AND platform IS NULL) "
            "OR (platform_scope = 'per_platform' AND platform IS NOT NULL)",
            name="scope_platform_consistency",
        ),
        # global: at most one drop per sku/day
        Index(
            "uq_drop_global",
            "sku_id",
            "drop_date",
            "platform_scope",
            unique=True,
            postgresql_where=text("platform IS NULL"),
        ),
        # per_platform: at most one drop per sku/day/platform
        Index(
            "uq_drop_per_platform",
            "sku_id",
            "drop_date",
            "platform_scope",
            "platform",
            unique=True,
            postgresql_where=text("platform IS NOT NULL"),
        ),
    )


class DropAssignment(IdMixin, Base):
    """One drop -> one (distributor, show). UNIQUE(drop) covers both scopes:
    a per_platform drop is already a distinct row per platform."""

    __tablename__ = "drop_assignment"

    daily_sku_drop_id: Mapped[int] = mapped_column(
        ForeignKey("daily_sku_drop.id"), nullable=False
    )
    distributor_id: Mapped[int] = mapped_column(
        ForeignKey("distributor.id"), nullable=False
    )
    show_id: Mapped[int] = mapped_column(ForeignKey("show.id"), nullable=False)
    assigned_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    score_snapshot: Mapped[Optional[dict]] = mapped_column(JSONB)

    drop: Mapped["DailySkuDrop"] = relationship(back_populates="assignments")
    distributor: Mapped["Distributor"] = relationship()
    show: Mapped["Show"] = relationship(back_populates="assignments")

    __table_args__ = (
        UniqueConstraint(
            "daily_sku_drop_id", name="uq_drop_assignment_daily_sku_drop_id"
        ),
        Index("ix_drop_assignment_distributor_id", "distributor_id"),
        Index("ix_drop_assignment_show_id", "show_id"),
    )
