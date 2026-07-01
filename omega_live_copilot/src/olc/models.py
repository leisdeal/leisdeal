"""Model capability-tier resolver (PRD §7.6/§11).

Tiers (haiku/sonnet/opus) are capability SLOTS, not fixed versions. Concrete IDs
come from config, which is populated from Omega's currently-available models.
Nothing here hard-codes a model ID. The speaker monitor does NOT call this — the
safety path never depends on an LLM (§7.8.4).
"""
from __future__ import annotations

from .config import Config

TIERS = ("haiku", "sonnet", "opus")


def resolve_model(cfg: Config, tier: str) -> str:
    if tier not in TIERS:
        raise ValueError(f"Unknown model tier {tier!r}; expected one of {TIERS}")
    model_id = cfg.get(f"models.{tier}", "")
    if not model_id:
        raise RuntimeError(
            f"Model tier '{tier}' has no ID configured. Set models.{tier} in "
            f"config/default.yaml from Omega's available models (do not hard-code)."
        )
    return model_id
