"""Minimal helpers to build valid rows for tests."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from app.enums import CatalogStatus, CpsiaStatus
from app.models import Product, SKU


def make_listed_sku(session, *, sku_code="SKU-1", on_hand=100, daily=20) -> SKU:
    product = Product(name="Widget", category="toys")
    session.add(product)
    session.flush()
    sku = SKU(
        product_id=product.id,
        sku_code=sku_code,
        hts_code="9503.00.00",
        duty_rate=Decimal("0.0"),
        landed_cost=Decimal("2.00"),
        cpsia_status=CpsiaStatus.certified,
        ca_metals_compliant=True,
        prop65_flag=False,
        ftc_jewelry_labeled=False,
        price_floor=Decimal("9.99"),
        daily_drop_qty=daily,
        total_on_hand=on_hand,
        catalog_status=CatalogStatus.listed,
    )
    session.add(sku)
    session.flush()
    return sku


def today() -> dt.date:
    return dt.date(2026, 6, 5)
