"""DB-level invariants for the daily-drop core."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from app.enums import Platform, PlatformScope
from app.models import DailySkuDrop
from tests.factories import make_listed_sku, today


def _drop(sku_id, scope, platform=None, drop_qty=10, sold_qty=0):
    return DailySkuDrop(
        sku_id=sku_id,
        drop_date=today(),
        platform_scope=scope,
        platform=platform,
        drop_qty=drop_qty,
        sold_qty=sold_qty,
    )


def test_global_drop_unique_per_sku_per_day(session):
    sku = make_listed_sku(session)
    session.add(_drop(sku.id, PlatformScope.global_))
    session.flush()
    session.add(_drop(sku.id, PlatformScope.global_))
    with pytest.raises(IntegrityError):
        session.flush()


def test_per_platform_allows_one_per_platform_but_not_duplicate(session):
    sku = make_listed_sku(session)
    session.add(_drop(sku.id, PlatformScope.per_platform, Platform.tiktok))
    session.add(_drop(sku.id, PlatformScope.per_platform, Platform.whatnot))
    session.flush()  # two different platforms -> OK
    session.add(_drop(sku.id, PlatformScope.per_platform, Platform.tiktok))
    with pytest.raises(IntegrityError):
        session.flush()


def test_scope_platform_consistency_global_must_have_null_platform(session):
    sku = make_listed_sku(session)
    session.add(_drop(sku.id, PlatformScope.global_, Platform.tiktok))
    with pytest.raises(IntegrityError):
        session.flush()


def test_scope_platform_consistency_per_platform_requires_platform(session):
    sku = make_listed_sku(session)
    session.add(_drop(sku.id, PlatformScope.per_platform, None))
    with pytest.raises(IntegrityError):
        session.flush()


def test_oversell_check_rejects_sold_above_drop(session):
    sku = make_listed_sku(session)
    session.add(_drop(sku.id, PlatformScope.global_, drop_qty=5, sold_qty=6))
    with pytest.raises(IntegrityError):
        session.flush()
