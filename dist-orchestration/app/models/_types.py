"""Shared SQLAlchemy enum type objects.

All PG ENUMs use the Python enum's *value* (not member name) as the label,
so DB labels match the canonical strings used in check constraints and
external integrations (e.g. 'global', 'per_platform'). Defining each type
once here also guarantees a single CREATE TYPE per enum.
"""

from __future__ import annotations

from sqlalchemy import Enum as SAEnum

from app import enums


def pg_enum(py_enum, name: str) -> SAEnum:
    return SAEnum(
        py_enum,
        name=name,
        values_callable=lambda e: [m.value for m in e],
    )


distributor_status_type = pg_enum(enums.DistributorStatus, "distributor_status")
distributor_tier_type = pg_enum(enums.DistributorTier, "distributor_tier")
wallet_txn_type_type = pg_enum(enums.WalletTxnType, "wallet_txn_type")

cpsia_status_type = pg_enum(enums.CpsiaStatus, "cpsia_status")
catalog_status_type = pg_enum(enums.CatalogStatus, "catalog_status")

platform_type = pg_enum(enums.Platform, "platform")
platform_scope_type = pg_enum(enums.PlatformScope, "platform_scope")
show_status_type = pg_enum(enums.ShowStatus, "show_status")
drop_status_type = pg_enum(enums.DropStatus, "drop_status")

sales_order_source_type = pg_enum(enums.SalesOrderSource, "sales_order_source")
sales_order_status_type = pg_enum(enums.SalesOrderStatus, "sales_order_status")

fulfillment_status_type = pg_enum(enums.FulfillmentStatus, "fulfillment_status")
return_type_type = pg_enum(enums.ReturnType, "return_type")
return_cost_owner_type = pg_enum(enums.ReturnCostOwner, "return_cost_owner")
