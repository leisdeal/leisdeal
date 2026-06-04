# Catalog Compliance Engine

Per-category compliance gating for the LEISDEAL distributor catalog (货盘目录).
Covers two product lines: **流行项链 fashion_necklace** and **潮玩 designer_toy**.

## Rule 4 (revised) — the core gate

> 按品类分别校验。一个 SKU 必须满足**该品类所有"必检项" = PASS**,
> `catalog_status` 才能置为 `live`;否则不可进货盘目录,分销商看不到。
>
> *Validate per category. A SKU may only be set to `catalog_status = live`
> when **every "required check" for its category is PASS**. Otherwise it does
> not enter the procurement catalog and distributors cannot see it.*

`distributor_visible` is true **only** when `resolved_status == live`.

## Common fields (every SKU)

| Field | Values |
|-------|--------|
| `category` | `fashion_necklace` \| `designer_toy` |
| `compliance_checks` | JSON object; each check records `status` (`PASS`/`FAIL`/`NA`) + `evidence_url` |
| `catalog_status` | `draft` → `pending_review` → `live` \| `blocked` |
| `exclusivity` *(merchandising)* | `exclusive` \| `shared` |

## Required checks by category

### 流行项链 `fashion_necklace`
| Check | PASS means |
|-------|------------|
| `ca_metal_compliance` | Supplier lead/cadmium test report meets the California Metal-Containing Jewelry Law limits. **Evidence (test report) is mandatory** — a PASS without `evidence_url` does not count. |
| `ftc_labeling` | Material/plating description is FTC-compliant (no "gold"/"silver" claim unless it qualifies; plating / base metal disclosed truthfully). |
| `prop65` | Assessed; Prop 65 warning attached where required. |

### 潮玩 `designer_toy`
| Check | PASS / accepted means |
|-------|-----------------------|
| `ip_ownership` *(enumerated value, not PASS/FAIL)* | Accepted: `owned_exclusive` \| `factory_original_nonexclusive`. **`branded` or `replica` → hard `blocked`** (banned from catalog). |
| `design_clearance` | Reverse-image / design dedup passed (avoids unintentionally colliding with someone else's design). |
| `adult_positioning` | Confirmed positioned as an adult collectible. See CPSIA sub-process below. |
| `prop65` | If vinyl/paint contains listed chemicals, a Prop 65 warning is attached. |

#### CPSIA sub-process (child-facing designer toys)
If a SKU is flagged `child_facing: true`, the CPSIA sub-process must be
**fully complete** or the SKU is `blocked`:

- `third_party_test`
- `tracking_label`
- `cpc` (Children's Product Certificate)

Provide these under a `cpsia` object, e.g.
`"cpsia": {"third_party_test": true, "tracking_label": true, "cpc": true}`.

## Merchandising flag (non-compliance)

`exclusivity` does **not** gate `live`; it only shapes scarcity/pricing:

| `exclusivity` | `treat_as_commodity` | `price_floor_factor` | `scarcity_expectation` |
|---------------|----------------------|----------------------|------------------------|
| `exclusive` | false | 1.0 | high |
| `shared` | true | 0.85 *(auto-lowered)* | low |

A `shared` SKU is treated as a commodity: the system auto-lowers its price
floor and scarcity expectation. (The `0.85` factor is a configurable default —
the spec mandates "lower", not a specific number.)

## Resolved status logic

For a SKU under review the engine computes the **authoritative** status:

1. **`blocked`** if any hard block fires:
   - `designer_toy` `ip_ownership` ∈ {`branded`, `replica`}
   - `designer_toy` `child_facing` with an incomplete CPSIA sub-process
   - any required check recorded as `FAIL` (affirmatively non-compliant)
2. **`live`** if not blocked **and** every required check is satisfied
   (`PASS`, plus `evidence_url` where mandatory; `ip_ownership` accepted).
3. **`pending_review`** otherwise — a remediable gap (missing check, `NA`,
   missing mandatory evidence, or an unrecognized `ip_ownership` value).
   The SKU stays out of the catalog until remediated.

### Encoded decisions (beyond the literal spec)
- **`FAIL` on a required check ⇒ `blocked`.** An affirmative FAIL (e.g. metal
  test exceeds limits) is non-compliant to sell, so it is escalated past
  `pending_review` to `blocked`. Missing/`NA`/unverified gaps stay
  `pending_review` because they are remediable.
- **`NA` is not sufficient for a required check** — required checks need `PASS`.
- **`ca_metal_compliance` PASS requires `evidence_url`** (the test report is
  legally mandatory). Other checks treat missing evidence as a warning.
- **Unknown `ip_ownership` value** (not in the accepted or blocking sets) is a
  remediable failure (`pending_review`), not a hard block.

## Usage

```bash
# Evaluate a batch and print per-SKU JSON results (summary to stderr)
python3 catalog_compliance.py sample_skus.json

# Run the test suite (stdlib unittest, no dependencies)
python3 test_catalog_compliance.py
```

```python
from catalog_compliance import evaluate, can_go_live

result = evaluate(sku_dict)      # -> EvaluationResult
if can_go_live(sku_dict):        # convenience bool guard
    set_catalog_status(sku_dict, "live")
```

Stdlib-only; requires Python 3.10+.
