"""Distributor, category seats, and the wallet ledger.

ANTI-PYRAMID GUARANTEE
----------------------
Distributor has NO sponsor_id / upline_id / referral_* / downline_* fields.
WalletTransaction has exactly five types (topup, sample_debit,
wholesale_debit, refund, rebate); none of them is recruiting-based.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, IdMixin, TimestampMixin
from app.enums import DistributorStatus, DistributorTier, WalletTxnType
from app.models._types import (
    distributor_status_type,
    distributor_tier_type,
    wallet_txn_type_type,
)

if TYPE_CHECKING:
    from app.models.sales import SalesOrder
    from app.models.show import Show


class CategorySeat(IdMixin, TimestampMixin, Base):
    """Scarcity gate: how many active distributors a category may hold."""

    __tablename__ = "category_seat"

    category: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    max_seats: Mapped[int] = mapped_column(nullable=False)
    current_seats: Mapped[int] = mapped_column(nullable=False, default=0)
    waitlist_count: Mapped[int] = mapped_column(nullable=False, default=0)

    __table_args__ = (
        CheckConstraint("current_seats >= 0", name="current_seats_non_negative"),
        CheckConstraint("waitlist_count >= 0", name="waitlist_non_negative"),
        CheckConstraint(
            "current_seats <= max_seats", name="current_seats_within_max"
        ),
    )


class Distributor(IdMixin, TimestampMixin, Base):
    __tablename__ = "distributor"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    primary_category: Mapped[str] = mapped_column(String(64), nullable=False)

    status: Mapped[DistributorStatus] = mapped_column(
        distributor_status_type,
        nullable=False,
        default=DistributorStatus.pending,
    )
    tier: Mapped[DistributorTier] = mapped_column(
        distributor_tier_type,
        nullable=False,
        default=DistributorTier.tier1,
    )

    cumulative_gmv: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    wallet_balance: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    low_balance_threshold: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )

    # White-label per distributor.
    platform_accounts: Mapped[Optional[dict]] = mapped_column(JSONB)
    return_address: Mapped[Optional[dict]] = mapped_column(JSONB)
    packing_slip_template_id: Mapped[Optional[str]] = mapped_column(String(128))

    # Set once a paid sample order clears; unlocks wholesale catalog actions.
    sample_unlocked: Mapped[bool] = mapped_column(nullable=False, default=False)

    wallet_transactions: Mapped[list["WalletTransaction"]] = relationship(
        back_populates="distributor"
    )
    shows: Mapped[list["Show"]] = relationship(back_populates="distributor")
    sales_orders: Mapped[list["SalesOrder"]] = relationship(
        back_populates="distributor"
    )


class WalletTransaction(IdMixin, Base):
    """Append-only ledger. wallet_balance is a cache of the running sum."""

    __tablename__ = "wallet_transaction"

    distributor_id: Mapped[int] = mapped_column(
        ForeignKey("distributor.id"), nullable=False
    )
    type: Mapped[WalletTxnType] = mapped_column(
        wallet_txn_type_type, nullable=False
    )
    # Signed: credits (topup/refund/rebate) positive, debits negative.
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")

    ref_type: Mapped[Optional[str]] = mapped_column(String(64))
    ref_id: Mapped[Optional[str]] = mapped_column(String(128))
    # Dedupe key (e.g. external order id) so re-ingest never double-charges.
    idempotency_key: Mapped[str] = mapped_column(
        String(200), unique=True, nullable=False
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    distributor: Mapped["Distributor"] = relationship(
        back_populates="wallet_transactions"
    )

    __table_args__ = (
        Index("ix_wallet_transaction_distributor_id", "distributor_id"),
    )
