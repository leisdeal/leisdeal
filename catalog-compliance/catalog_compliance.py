"""LEISDEAL catalog compliance engine.

Implements the per-category compliance gate (Rule 4, revised):

    A SKU must have ALL "required checks" for its category == PASS before its
    ``catalog_status`` may be set to ``live``. Otherwise the SKU does not enter
    the procurement catalog and distributors cannot see it.

Two product categories are supported:

    * fashion_necklace
    * designer_toy

See README.md for the full specification and the decisions encoded here.

This module is stdlib-only. Run ``python3 catalog_compliance.py <skus.json>``
to evaluate a batch of SKUs.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class Category(str, Enum):
    FASHION_NECKLACE = "fashion_necklace"
    DESIGNER_TOY = "designer_toy"


class CheckStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NA = "NA"


class CatalogStatus(str, Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    LIVE = "live"
    BLOCKED = "blocked"


class Exclusivity(str, Enum):
    EXCLUSIVE = "exclusive"
    SHARED = "shared"


# IP ownership is an enumerated value (not PASS/FAIL/NA).
ACCEPTABLE_IP = {"owned_exclusive", "factory_original_nonexclusive"}
BLOCKING_IP = {"branded", "replica"}


# ---------------------------------------------------------------------------
# Per-category required checks
# ---------------------------------------------------------------------------

# ip_ownership is handled with bespoke logic (it carries a value, not a status),
# but it is still a required check for designer_toy.
REQUIRED_CHECKS: dict[Category, list[str]] = {
    Category.FASHION_NECKLACE: ["ca_metal_compliance", "ftc_labeling", "prop65"],
    Category.DESIGNER_TOY: ["ip_ownership", "design_clearance", "adult_positioning", "prop65"],
}

# Checks whose PASS is meaningless without a supporting document. A test report
# (lead/cadmium) is legally mandatory, so we refuse to count PASS without it.
EVIDENCE_REQUIRED_FOR_PASS = {"ca_metal_compliance"}

# The CPSIA sub-process steps that must all be complete for a child-facing
# designer_toy SKU.
CPSIA_STEPS = ["third_party_test", "tracking_label", "cpc"]


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class CheckOutcome:
    check: str
    satisfied: bool
    detail: str


@dataclass
class Merchandising:
    exclusivity: str
    treat_as_commodity: bool
    price_floor_factor: float
    scarcity_expectation: str


@dataclass
class EvaluationResult:
    sku_id: str
    category: str
    resolved_status: str
    live_eligible: bool
    distributor_visible: bool
    blocks: list[str] = field(default_factory=list)
    failures: list[CheckOutcome] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    merchandising: Merchandising | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

def _check_entry(sku: dict, name: str) -> dict:
    return (sku.get("compliance_checks") or {}).get(name) or {}


def _evaluate_status_check(sku: dict, name: str) -> CheckOutcome:
    """Evaluate a PASS/FAIL/NA-style required check."""
    entry = _check_entry(sku, name)
    raw_status = entry.get("status")
    evidence = entry.get("evidence_url")

    if raw_status is None:
        return CheckOutcome(name, False, "missing: no status recorded")

    try:
        status = CheckStatus(raw_status)
    except ValueError:
        return CheckOutcome(name, False, f"invalid status {raw_status!r}")

    if status is CheckStatus.FAIL:
        # FAIL is surfaced here but is escalated to a hard block by the caller.
        return CheckOutcome(name, False, "FAIL recorded (affirmatively non-compliant)")

    if status is CheckStatus.NA:
        return CheckOutcome(name, False, "NA is not acceptable for a required check (needs PASS)")

    # status is PASS
    if name in EVIDENCE_REQUIRED_FOR_PASS and not evidence:
        return CheckOutcome(name, False, "PASS but missing required evidence_url")

    return CheckOutcome(name, True, "PASS")


def _evaluate_ip_ownership(sku: dict) -> tuple[CheckOutcome, bool, list[str]]:
    """Returns (outcome, is_hard_block, warnings)."""
    entry = _check_entry(sku, "ip_ownership")
    value = entry.get("value")
    evidence = entry.get("evidence_url")
    warnings: list[str] = []

    if value in BLOCKING_IP:
        return (
            CheckOutcome("ip_ownership", False, f"ip_ownership={value!r} is prohibited"),
            True,
            warnings,
        )

    if value not in ACCEPTABLE_IP:
        return (
            CheckOutcome(
                "ip_ownership",
                False,
                f"ip_ownership={value!r} not in {sorted(ACCEPTABLE_IP)}",
            ),
            False,
            warnings,
        )

    if not evidence:
        warnings.append("ip_ownership accepted but no evidence_url provided (recommended)")

    return (CheckOutcome("ip_ownership", True, f"{value}"), False, warnings)


def _evaluate_merchandising(sku: dict) -> Merchandising:
    raw = sku.get("exclusivity", Exclusivity.EXCLUSIVE.value)
    try:
        exclusivity = Exclusivity(raw)
    except ValueError:
        exclusivity = Exclusivity.EXCLUSIVE

    if exclusivity is Exclusivity.SHARED:
        # Treated as a commodity: floor and scarcity expectation auto-lowered.
        return Merchandising(
            exclusivity=exclusivity.value,
            treat_as_commodity=True,
            price_floor_factor=0.85,
            scarcity_expectation="low",
        )
    return Merchandising(
        exclusivity=exclusivity.value,
        treat_as_commodity=False,
        price_floor_factor=1.0,
        scarcity_expectation="high",
    )


def _cpsia_block(sku: dict) -> str | None:
    """For child-facing designer toys, the CPSIA sub-process must be complete."""
    if not sku.get("child_facing"):
        return None
    cpsia = sku.get("cpsia") or {}
    missing = [step for step in CPSIA_STEPS if not cpsia.get(step)]
    if missing:
        return f"child-facing SKU: CPSIA sub-process incomplete ({', '.join(missing)})"
    return None


def evaluate(sku: dict) -> EvaluationResult:
    """Evaluate a single SKU and return its authoritative catalog status."""
    sku_id = sku.get("sku_id", "<unknown>")
    raw_category = sku.get("category")
    try:
        category = Category(raw_category)
    except ValueError as exc:
        raise ValueError(
            f"SKU {sku_id!r}: unknown/missing category {raw_category!r}"
        ) from exc

    blocks: list[str] = []
    failures: list[CheckOutcome] = []
    warnings: list[str] = []

    for name in REQUIRED_CHECKS[category]:
        if name == "ip_ownership":
            outcome, hard_block, ip_warnings = _evaluate_ip_ownership(sku)
            warnings.extend(ip_warnings)
            if hard_block:
                blocks.append(outcome.detail)
            elif not outcome.satisfied:
                failures.append(outcome)
            continue

        outcome = _evaluate_status_check(sku, name)
        if not outcome.satisfied:
            # An affirmative FAIL is a hard block; everything else is a remediable
            # failure that simply keeps the SKU out of "live".
            if "FAIL recorded" in outcome.detail:
                blocks.append(f"{name}: {outcome.detail}")
            else:
                failures.append(outcome)

    # CPSIA sub-process for child-facing designer toys.
    if category is Category.DESIGNER_TOY:
        cpsia_reason = _cpsia_block(sku)
        if cpsia_reason:
            blocks.append(cpsia_reason)

    merchandising = _evaluate_merchandising(sku)

    if blocks:
        resolved = CatalogStatus.BLOCKED
        live_eligible = False
    elif not failures:
        resolved = CatalogStatus.LIVE
        live_eligible = True
    else:
        resolved = CatalogStatus.PENDING_REVIEW
        live_eligible = False

    # If the seller requested "live" but it is not attainable, make that explicit.
    requested = sku.get("requested_status")
    if requested == CatalogStatus.LIVE.value and not live_eligible:
        warnings.append(
            f"requested catalog_status=live denied; resolved to {resolved.value}"
        )

    return EvaluationResult(
        sku_id=sku_id,
        category=category.value,
        resolved_status=resolved.value,
        live_eligible=live_eligible,
        distributor_visible=(resolved is CatalogStatus.LIVE),
        blocks=blocks,
        failures=failures,
        warnings=warnings,
        merchandising=merchandising,
    )


def can_go_live(sku: dict) -> bool:
    """Convenience guard: True only when the SKU may be set to ``live``."""
    return evaluate(sku).live_eligible


def evaluate_batch(skus: list[dict]) -> list[EvaluationResult]:
    return [evaluate(sku) for sku in skus]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python3 catalog_compliance.py <skus.json>", file=sys.stderr)
        return 2

    with open(argv[1], encoding="utf-8") as fh:
        data = json.load(fh)
    skus = data if isinstance(data, list) else [data]

    results = []
    for sku in skus:
        try:
            results.append(evaluate(sku).to_dict())
        except ValueError as exc:
            results.append({"sku_id": sku.get("sku_id", "<unknown>"), "error": str(exc)})

    print(json.dumps(results, indent=2, ensure_ascii=False))

    summary: dict[str, int] = {}
    for r in results:
        key = r.get("resolved_status", "error")
        summary[key] = summary.get(key, 0) + 1
    print("\n# summary:", json.dumps(summary, ensure_ascii=False), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
