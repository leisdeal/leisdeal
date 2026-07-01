"""Speaker redline eval (PRD §7.8.12).

Measures the ONE hard metric — red-line-phrase recall — by level, plus false
positives on safe negatives and detect-stage latency P95.

⚠️ ACCEPTANCE SCOPE: this harness scores DETECTION LOGIC over transcripts. The
98% S2/S3 recall acceptance is only met when run over transcripts produced by
real recorded HOST audio through FunASR in a real environment (real acoustics,
中英夹杂, mic noise). Text/TTS cases validate the logic, not the acoustic path.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from ..speaker_monitor.detector import LEVEL_ORDER, RedlineDetector
from ..timing import percentile


@dataclass
class Case:
    text: str
    expected_level: str   # "S1"|"S2"|"S3"|"none"
    note: str = ""


def load_cases(path: str | Path) -> list[Case]:
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return [
        Case(text=c["text"], expected_level=str(c.get("expected_level", "none")), note=c.get("note", ""))
        for c in data.get("cases", [])
    ]


@dataclass
class SpeakerEvalResult:
    n_cases: int
    recall: dict[str, float]              # per expected level
    recall_hits: dict[str, tuple[int, int]]
    s2_s3_recall: float
    false_positive_rate: float
    n_negatives: int
    n_false_positives: int
    detect_p95_ms: float
    misses: list[dict] = field(default_factory=list)
    false_positives: list[dict] = field(default_factory=list)

    # Acceptance flags (logic-level; acoustic recall PENDING real audio).
    targets: dict = field(default_factory=dict)

    def passes_logic(self) -> bool:
        return (
            self.s2_s3_recall >= self.targets.get("recall_s2_s3_target", 0.98)
            and self.recall.get("S1", 1.0) >= self.targets.get("recall_s1_target", 0.90)
        )


def _detected_level(detector: RedlineDetector, text: str) -> str | None:
    hits = detector.detect(text)
    return hits[0].level if hits else None


def evaluate_speaker_detector(
    detector: RedlineDetector,
    cases: list[Case],
    *,
    targets: dict | None = None,
) -> SpeakerEvalResult:
    import time

    targets = targets or {"recall_s2_s3_target": 0.98, "recall_s1_target": 0.90}
    per_level_total: dict[str, int] = {"S1": 0, "S2": 0, "S3": 0}
    per_level_hit: dict[str, int] = {"S1": 0, "S2": 0, "S3": 0}
    misses: list[dict] = []
    false_positives: list[dict] = []
    n_negatives = 0
    n_fp = 0
    latencies: list[float] = []

    for c in cases:
        t0 = time.perf_counter()
        got = _detected_level(detector, c.text)
        latencies.append((time.perf_counter() - t0) * 1000.0)

        if c.expected_level == "none":
            n_negatives += 1
            if got is not None:
                n_fp += 1
                false_positives.append({"text": c.text, "got": got, "note": c.note})
            continue

        per_level_total[c.expected_level] += 1
        # Recall = caught at the expected severity OR HIGHER (a stricter call is
        # still a catch; only silent misses count against recall).
        caught = got is not None and LEVEL_ORDER[got] >= LEVEL_ORDER[c.expected_level]
        if caught:
            per_level_hit[c.expected_level] += 1
        else:
            misses.append({"text": c.text, "expected": c.expected_level, "got": got, "note": c.note})

    recall = {
        lvl: (per_level_hit[lvl] / per_level_total[lvl]) if per_level_total[lvl] else 1.0
        for lvl in ("S1", "S2", "S3")
    }
    s2_s3_total = per_level_total["S2"] + per_level_total["S3"]
    s2_s3_hit = per_level_hit["S2"] + per_level_hit["S3"]
    s2_s3_recall = (s2_s3_hit / s2_s3_total) if s2_s3_total else 1.0

    return SpeakerEvalResult(
        n_cases=len(cases),
        recall=recall,
        recall_hits={lvl: (per_level_hit[lvl], per_level_total[lvl]) for lvl in ("S1", "S2", "S3")},
        s2_s3_recall=s2_s3_recall,
        false_positive_rate=(n_fp / n_negatives) if n_negatives else 0.0,
        n_negatives=n_negatives,
        n_false_positives=n_fp,
        detect_p95_ms=percentile(latencies, 95),
        misses=misses,
        false_positives=false_positives,
        targets=targets,
    )


def render_report(result: SpeakerEvalResult) -> str:
    lines = [
        "═══ Speaker Redline Detector — Eval (logic-level) ═══",
        f"cases: {result.n_cases}   negatives: {result.n_negatives}",
        "",
        "Recall by level (caught at expected severity or higher):",
    ]
    for lvl in ("S1", "S2", "S3"):
        hit, tot = result.recall_hits[lvl]
        lines.append(f"  {lvl}: {result.recall[lvl]*100:6.2f}%   ({hit}/{tot})")
    lines += [
        f"  S2/S3 combined: {result.s2_s3_recall*100:.2f}%   [target ≥ {result.targets['recall_s2_s3_target']*100:.0f}%]",
        "",
        f"False positives: {result.n_false_positives}/{result.n_negatives} "
        f"({result.false_positive_rate*100:.1f}%)  [no hard gate; soft cap in config]",
        f"Detect latency P95: {result.detect_p95_ms:.2f} ms  [target < 200 ms]",
        "",
        f"LOGIC-LEVEL VERDICT: {'PASS' if result.passes_logic() else 'FAIL'}",
        "ACOUSTIC 98% ACCEPTANCE: PENDING real recorded host-voice stream (§7.8.12).",
    ]
    if result.misses:
        lines.append("\nMISSES (fix before shipping — S3 miss = fatal):")
        for m in result.misses:
            lines.append(f"  expected {m['expected']} got {m['got']}: {m['text']}")
    if result.false_positives:
        lines.append("\nFALSE POSITIVES (tune wordlist/threshold):")
        for f in result.false_positives:
            lines.append(f"  got {f['got']}: {f['text']}")
    return "\n".join(lines)
