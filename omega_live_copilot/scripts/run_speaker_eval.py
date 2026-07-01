#!/usr/bin/env python3
"""Run the speaker redline detector eval and print the report (PRD §7.8.12).

    python scripts/run_speaker_eval.py [--cases data/eval/speaker_redline_cases.yaml]

Logic-level only: the 98% S2/S3 acceptance is PENDING real recorded host audio.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from olc.config import Config  # noqa: E402
from olc.eval.speaker_eval import evaluate_speaker_detector, load_cases, render_report  # noqa: E402
from olc.speaker_monitor.build import build_detector, build_wordlist  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--cases", default=None)
    args = ap.parse_args(argv)

    cfg = Config.load(args.config)
    cases_path = args.cases or (cfg.root / "data/eval/speaker_redline_cases.yaml")
    wordlist = build_wordlist(cfg)
    detector = build_detector(cfg, wordlist)
    cases = load_cases(cases_path)

    targets = {
        "recall_s2_s3_target": cfg.get("speaker_monitor.thresholds.recall_s2_s3_target", 0.98),
        "recall_s1_target": cfg.get("speaker_monitor.thresholds.recall_s1_target", 0.90),
    }
    result = evaluate_speaker_detector(detector, cases, targets=targets)
    print(render_report(result))
    # Non-zero exit if logic verdict fails, so CI/self-test can gate on it.
    return 0 if result.passes_logic() else 1


if __name__ == "__main__":
    sys.exit(main())
