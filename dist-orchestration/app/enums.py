"""Enumerations for the NewCo distribution-orchestration layer.

Anti-pyramid note: there is deliberately NO enum (or column anywhere) that
encodes recruiting, sponsors, uplines, or downline commission. Distributor
earnings are wholesale spread (kept by the distributor) plus volume rebate
keyed only on the distributor's own GMV. See tests/test_anti_pyramid.py.
"""

from __future__ import annotations

import enum


class DistributorStatus(str, enum.Enum):
    pending = "pending"
    waitlisted = "waitlisted"
    active = "active"
    suspended = "suspended"


class DistributorTier(str, enum.Enum):
    """Driven by cumulative_gmv; never set by hand for recruiting reasons."""

    tier1 = "tier1"
    tier2 = "tier2"
    tier3 = "tier3"


class Platform(str, enum.Enum):
    tiktok = "tiktok"
    whatnot = "whatnot"


class PlatformScope(str, enum.Enum):
    global_ = "global"
    per_platform = "per_platform"


class CatalogStatus(str, enum.Enum):
    draft = "draft"
    compliance_pending = "compliance_pending"
    listed = "listed"
    blocked = "blocked"


class CpsiaStatus(str, enum.Enum):
    not_required = "not_required"
    pending = "pending"
    certified = "certified"
    failed = "failed"


class ShowStatus(str, enum.Enum):
    scheduled = "scheduled"
    live = "live"
    ended = "ended"
    cancelled = "cancelled"


class DropStatus(str, enum.Enum):
    planned = "planned"
    assigned = "assigned"
    live = "live"
    sold_out = "sold_out"
    closed = "closed"


class WalletTxnType(str, enum.Enum):
    topup = "topup"
    sample_debit = "sample_debit"
    wholesale_debit = "wholesale_debit"
    refund = "refund"
    rebate = "rebate"


class SalesOrderSource(str, enum.Enum):
    tiktok_api = "tiktok_api"
    whatnot_csv = "whatnot_csv"


class SalesOrderStatus(str, enum.Enum):
    ingested = "ingested"
    priced = "priced"
    wallet_charged = "wallet_charged"
    routed = "routed"
    fulfilled = "fulfilled"
    rejected = "rejected"
    cancelled = "cancelled"


class FulfillmentStatus(str, enum.Enum):
    created = "created"
    picked = "picked"
    shipped = "shipped"
    delivered = "delivered"
    exception = "exception"


class ReturnType(str, enum.Enum):
    defective = "defective"
    buyer_remorse = "buyer_remorse"


class ReturnCostOwner(str, enum.Enum):
    newco = "newco"
    distributor = "distributor"
    shared = "shared"
