"""Structural guarantee: nothing in the schema encodes recruiting/downline.

Distributor earnings are wholesale spread + own-GMV rebate only. If anyone
ever adds a sponsor/upline/downline/referral column, this test fails.
"""

from __future__ import annotations

from app.enums import WalletTxnType
from app.models import Base

FORBIDDEN_SUBSTRINGS = (
    "sponsor",
    "upline",
    "downline",
    "referral",
    "referrer",
    "recruit",
    "commission",  # spread + rebate are the only earnings; no commission field
)


def test_no_recruiting_columns_anywhere():
    offenders = []
    for table in Base.metadata.tables.values():
        for column in table.columns:
            name = column.name.lower()
            if any(bad in name for bad in FORBIDDEN_SUBSTRINGS):
                offenders.append(f"{table.name}.{column.name}")
    assert not offenders, f"recruiting-style columns found: {offenders}"


def test_wallet_txn_types_are_non_recruiting():
    allowed = {"topup", "sample_debit", "wholesale_debit", "refund", "rebate"}
    assert {t.value for t in WalletTxnType} == allowed
