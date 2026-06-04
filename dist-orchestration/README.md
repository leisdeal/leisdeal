# NewCo Distribution Orchestration (MVP)

A thin orchestration layer over external WMS/OMS/3PL. NewCo supplies inventory
from a CA warehouse and drop-ships under each distributor's white label;
distributors self-operate their own TikTok Shop / Whatnot accounts.

**This layer does NOT reimplement WMS/OMS.** Inventory pick/pack/ship lives in
the external provider (Cin7 or Shopify+ShipStation). We integrate via
API/webhook. `SKU.total_on_hand` is a mirror of the provider's inventory feed.

See `DESIGN.md` for the data model, state machines, and the daily-drop
scheduling flow.

## Status — increment 1

Data model + initial Alembic migration + invariant tests. The allocation
core is the **daily-drop** model (`DailySkuDrop` + `DropAssignment`); there is
no `InventoryAllocation`.

Next increments: allocation engine, wallet/sample services, sales ingest +
oversell CAS, EOD reconcile, integration adapters, FastAPI routes.

## Setup

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

# Postgres
createdb newco
export DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/newco

alembic upgrade head
pytest -q
```

## Layout

```
app/
  enums.py          # all enums (no recruiting/downline types)
  db.py             # Base, mixins, Money type
  config.py         # DATABASE_URL
  models/
    _types.py       # shared PG enum type objects (value-based labels)
    distributor.py  # CategorySeat, Distributor, WalletTransaction
    catalog.py      # Product, SKU, WholesalePrice, ComplianceRecord
    show.py         # Show
    drop.py         # DailySkuDrop, DropAssignment  (allocation core)
    sales.py        # SalesOrder
    fulfillment.py  # Fulfillment, Return
migrations/         # Alembic
tests/              # DB invariant + anti-pyramid tests
```

## Guarantees enforced at the DB level

- **Oversell guard**: `CHECK (sold_qty <= drop_qty)` on every drop.
- **Drop uniqueness**: partial unique indexes — one global drop per
  `(sku, date)`, one per-platform drop per `(sku, date, platform)`.
- **Scope/platform consistency**: global ⇒ platform NULL; per_platform ⇒
  platform set.
- **Idempotent wallet**: `wallet_transaction.idempotency_key` is unique.
- **Anti-pyramid**: `tests/test_anti_pyramid.py` fails if any column name
  encodes sponsor/upline/downline/referral/commission.
