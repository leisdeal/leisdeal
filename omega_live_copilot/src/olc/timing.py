"""Latency helpers — percentile tracking for the P95 acceptance targets (§7.8.8)."""
from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field


def percentile(samples: list[float], pct: float) -> float:
    """Nearest-rank percentile. pct in [0,100]. Returns 0.0 for empty input."""
    if not samples:
        return 0.0
    ordered = sorted(samples)
    k = max(0, min(len(ordered) - 1, int(round((pct / 100.0) * len(ordered) + 0.5)) - 1))
    return ordered[k]


@dataclass
class LatencyRecorder:
    """Collects millisecond samples per named stage."""

    stages: dict[str, list[float]] = field(default_factory=dict)

    def add(self, stage: str, ms: float) -> None:
        self.stages.setdefault(stage, []).append(ms)

    @contextmanager
    def measure(self, stage: str):
        t0 = time.perf_counter()
        try:
            yield
        finally:
            self.add(stage, (time.perf_counter() - t0) * 1000.0)

    def p95(self, stage: str) -> float:
        return percentile(self.stages.get(stage, []), 95)

    def summary(self) -> dict[str, dict[str, float]]:
        out: dict[str, dict[str, float]] = {}
        for stage, samples in self.stages.items():
            out[stage] = {
                "count": len(samples),
                "p50": percentile(samples, 50),
                "p95": percentile(samples, 95),
                "max": max(samples) if samples else 0.0,
            }
        return out
