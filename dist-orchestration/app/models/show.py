"""A distributor's scheduled livestream on a platform."""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, IdMixin, TimestampMixin
from app.enums import Platform, ShowStatus
from app.models._types import platform_type, show_status_type

if TYPE_CHECKING:
    from app.models.distributor import Distributor
    from app.models.drop import DropAssignment


class Show(IdMixin, TimestampMixin, Base):
    __tablename__ = "show"

    distributor_id: Mapped[int] = mapped_column(
        ForeignKey("distributor.id"), nullable=False
    )
    platform: Mapped[Platform] = mapped_column(platform_type, nullable=False)
    scheduled_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    status: Mapped[ShowStatus] = mapped_column(
        show_status_type,
        nullable=False,
        default=ShowStatus.scheduled,
    )

    distributor: Mapped["Distributor"] = relationship(back_populates="shows")
    assignments: Mapped[list["DropAssignment"]] = relationship(
        back_populates="show"
    )

    __table_args__ = (
        Index("ix_show_distributor_scheduled", "distributor_id", "scheduled_at"),
    )
