# NewCo Distribution Orchestration — Design (locked baseline)

Scope: a thin orchestration layer above external WMS/OMS/3PL. NewCo is the
upstream supplier + warehouse drop-shipper; distributors are the merchant of
record on their own TikTok Shop / Whatnot accounts. Funds flow through a
pre-funded wallet. Earnings = wholesale spread + own-GMV rebate (no downline).

Allocation core = **daily-drop scheduling** (`DailySkuDrop` + `DropAssignment`).
The earlier per-show `InventoryAllocation` model is removed.

## Boundaries

```
        NewCo Orchestration (this repo)
  distributor • wallet • catalog/compliance • daily-drop engine
  • sales ingest • price-floor • white-label fulfillment routing
            │ Stripe   │ TikTok API  │ Whatnot CSV │ OMS/3PL (Cin7/ShipStation)
```

`SKU.total_on_hand` is a one-way mirror of the OMS inventory feed. NewCo never
writes physical stock; it plans daily exposure on top of the mirror.

## Data model

13 tables: `category_seat`, `distributor`, `wallet_transaction`, `product`,
`sku`, `wholesale_price`, `compliance_record`, `show`, `daily_sku_drop`,
`drop_assignment`, `sales_order`, `fulfillment`, `product_return`.

Key fields per the locked spec live in `app/models/`. Highlights:

- **CategorySeat** `category, max_seats, current_seats, waitlist_count` —
  onboarding scarcity gate.
- **SKU** mandatory compliance/pricing: `hts_code, duty_rate, landed_cost,
  cpsia_status, ca_metals_compliant, prop65_flag, ftc_jewelry_labeled,
  price_floor`; scheduling: `daily_drop_qty, total_on_hand, version`.
- **DailySkuDrop** `sku_id, drop_date, platform_scope(global|per_platform),
  platform(null|tiktok|whatnot), drop_qty, sold_qty, status`.
- **DropAssignment** `daily_sku_drop_id, distributor_id, show_id,
  assigned_at, score_snapshot(jsonb)`.

### Uniqueness & invariants (enforced in DB)

```
daily_sku_drop:
  UNIQUE(sku_id, drop_date, platform_scope) WHERE platform IS NULL      -- global once/day
  UNIQUE(sku_id, drop_date, platform_scope, platform) WHERE platform IS NOT NULL
  CHECK sold_qty <= drop_qty                                            -- oversell guard
  CHECK (scope=global AND platform IS NULL) OR (scope=per_platform AND platform IS NOT NULL)
drop_assignment:
  UNIQUE(daily_sku_drop_id)        -- one assignment per (platform-)drop, both scopes
wallet_transaction:
  UNIQUE(idempotency_key)          -- re-ingest never double-charges
sales_order:
  UNIQUE(source, external_order_id)
```

### Inventory hard constraint (planning time, in a tx)

For each `(sku, drop_date)`:  `SUM(drop_qty) <= SKU.total_on_hand`.
Generation reads `total_on_hand + version`, sums existing planned/assigned/live
drop_qty, validates, then writes. `available_for_drop = total_on_hand −
future_planned_drop_qty` is a derived planning view, not a WMS.

## CategorySeat onboarding

```mermaid
flowchart TD
    A[Distributor onboarding] --> B[pick primary_category]
    B --> C{current_seats < max_seats?}
    C -- yes --> D[status=active; current_seats += 1]
    C -- no --> E[status=waitlisted; waitlist_count += 1]
```

## Daily allocation engine (cron, generates next-day plan)

```mermaid
flowchart TD
    A[daily cron] --> B[eligible SKUs: compliance-listed + active + has stock]
    B --> C[build DailySkuDrop per SKU.daily_drop_qty]
    C --> H{SUM drop_qty <= total_on_hand?}
    H -- no --> CL[clamp/drop by priority]
    H -- yes --> D[candidates: active distributors w/ next-day Show, platform match]
    CL --> D
    D --> E[score = perf + tier + rotation + availability]
    E --> F{platform_scope}
    F -- global --> G[assign drop to 1 show]
    F -- per_platform --> P[assign 1 show per platform]
    G --> I[create DropAssignment; status=assigned]
    P --> I
```

Scoring (pluggable `AssignmentStrategy`):
```
score = w_perf*recent_sell_through + w_tier*tier_score
      + w_rotation*under_served_score + w_avail*has_show_for_platform
```
Floor rotation: tail distributors who went long without a drop get a rising
`under_served_score`, preventing head monopoly.

## DailySkuDrop state machine

```mermaid
stateDiagram-v2
    [*] --> planned
    planned --> assigned: DropAssignment created
    assigned --> live: drop_date / show goes live
    live --> sold_out: sold_qty >= drop_qty
    live --> closed: end-of-day reconcile
    sold_out --> closed: end-of-day reconcile
    closed --> [*]
```

## Sales ingest + oversell + wallet debit

```mermaid
flowchart TD
    A[TikTok API / Whatnot CSV] --> B[match distributor+show+sku+date+platform -> DailySkuDrop]
    B --> C{CAS: sold_qty + qty <= drop_qty?}
    C -- no --> R[reject/alert: over daily cap -> sold_out]
    C -- yes --> D{sale_price < price_floor?}
    D -- yes --> E[below_floor_flag + alert]
    D -- no --> F
    E --> F[wallet debit wholesale: SELECT FOR UPDATE + idempotency_key]
    F --> G[cumulative_gmv += ; reassess tier]
    G --> K[route to OMS/3PL with white-label; webhook writes Fulfillment]
```

Oversell guard (the new hot path, replaces the old request-time lock):
```sql
UPDATE daily_sku_drop SET sold_qty = sold_qty + :q
 WHERE id = :id AND sold_qty + :q <= drop_qty;   -- rowcount 0 => sold_out
```

## End-of-day reconcile

1. Sum confirmed `SalesOrder.qty` per drop → write back `sold_qty`.
2. Unsold (`drop_qty − sold_qty`) was never physically removed → returns to the
   available pool for future dates.
3. `sold_qty == drop_qty` → sold_out; then closed.
4. Update `distributor.cumulative_gmv` and tier from final GMV.

## Two MVP critical paths

- (a) topup → sample → wholesale unlock → seat check → active/waitlist.
- (b) daily drop → assign to show → ingest → cap + price-floor check → wallet
  wholesale debit → fulfillment routing.

## Anti-pyramid

Earnings = wholesale spread + own-GMV rebate. No `sponsor/upline/downline/
referral/commission` columns anywhere; `tests/test_anti_pyramid.py` enforces it.
