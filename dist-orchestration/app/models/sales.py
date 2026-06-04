"""Sales orders ingested from TikTok Shop API or Whatnot CSV."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, IdMixin, TimestampMixin
from app.enums import SalesOrderSource, SalesOrderStatus
from app.models._types import sales_order_source_type, sales_order_status_type

if TYPE_CHECKING:
    from app.models.distributor import Distributor
    from app.models.drop import DailySkuDrop
    from app.models.fulfillment import Fulfillment


class SalesOrder(IdMixin, TimestampMixin, Base):
    __tablename__ = "sales_order"

    distributor_id: Mapped[int] = mapped_column(
        ForeignKey("distributor.id"), nullable=False
    )
    # Associated to the daily drop (replaces the old allocation link).
    daily_sku_drop_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("daily_sku_drop.id")
    )
    sku_id: Mapped[int] = mapped_column(ForeignKey("sku.id"), nullable=False)

    source: Mapped[SalesOrderSource] = mapped_column(
        sales_order_source_type, nullable=False
    )
    external_order_id: Mapped[str] = mapped_column(String(128), nullable=False)

    qty: Mapped[int] = mapped_column(nullable=False)
    sale_unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    # Snapshot so later tier/price changes don't rewrite history.
    wholesale_unit_price_snapshot: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(14, 2)
    )
    below_floor_flag: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    status: Mapped[SalesOrderStatus] = mapped_column(
        sales_order_status_type,
        nullable=False,
        default=SalesOrderStatus.ingested,
    )
    wallet_txn_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("wallet_transaction.id")
    )

    distributor: Mapped["Distributor"] = relationship(
        back_populates="sales_orders"
    )
    drop: Mapped[Optional["DailySkuDrop"]] = relationship(
        back_populates="sales_orders"
    )
    fulfillment: Mapped[Optional["Fulfillment"]] = relationship(
        back_populates="sales_order", uselist=False
    )

    __table_args__ = (
        UniqueConstraint(
            "source", "external_order_id", name="uq_sales_order_source_external"
        ),
    )
