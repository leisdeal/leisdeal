"""Fulfillment (synced from external OMS/3PL webhooks) and returns."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, IdMixin, TimestampMixin
from app.enums import FulfillmentStatus, ReturnCostOwner, ReturnType
from app.models._types import (
    fulfillment_status_type,
    return_cost_owner_type,
    return_type_type,
)

if TYPE_CHECKING:
    from app.models.sales import SalesOrder


class Fulfillment(IdMixin, TimestampMixin, Base):
    __tablename__ = "fulfillment"

    sales_order_id: Mapped[int] = mapped_column(
        ForeignKey("sales_order.id"), unique=True, nullable=False
    )
    oms_shipment_id: Mapped[Optional[str]] = mapped_column(String(128))
    status: Mapped[FulfillmentStatus] = mapped_column(
        fulfillment_status_type,
        nullable=False,
        default=FulfillmentStatus.created,
    )
    tracking_no: Mapped[Optional[str]] = mapped_column(String(128))
    carrier: Mapped[Optional[str]] = mapped_column(String(64))

    # White-label info captured at routing time.
    return_address_snapshot: Mapped[Optional[dict]] = mapped_column(JSONB)
    packing_slip_url: Mapped[Optional[str]] = mapped_column(String(512))
    last_webhook_at: Mapped[Optional[dt.datetime]] = mapped_column(
        DateTime(timezone=True)
    )

    sales_order: Mapped["SalesOrder"] = relationship(
        back_populates="fulfillment"
    )


class Return(IdMixin, TimestampMixin, Base):
    __tablename__ = "product_return"

    sales_order_id: Mapped[int] = mapped_column(
        ForeignKey("sales_order.id"), nullable=False
    )
    type: Mapped[ReturnType] = mapped_column(return_type_type, nullable=False)
    cost_owner: Mapped[ReturnCostOwner] = mapped_column(
        return_cost_owner_type, nullable=False
    )
    restock_qty: Mapped[int] = mapped_column(nullable=False, default=0)
    refund_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    wallet_txn_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("wallet_transaction.id")
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
