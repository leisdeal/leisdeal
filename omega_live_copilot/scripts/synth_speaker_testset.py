#!/usr/bin/env python3
"""Synthesize speaker test audio from the eval cases (PRD §7.8.12 self-test).

Best-effort TTS: tries available engines and reports what's missing. In a real
environment (中控 machine) this produces WAVs you can feed through FunASR to
validate the ACOUSTIC path; the resulting transcripts become real eval cases.

⚠️ TTS validates the detection LOGIC through synthetic audio only. The 98% S2/S3
acceptance still requires REAL recorded host voice (real acoustics/noise/中英夹杂).

Engines tried, in order:
  1. piper       (offline neural TTS; best quality)   — `pip install piper-tts`
  2. edge-tts    (online MS neural)                    — `pip install edge-tts`
  3. espeak-ng   (offline, robotic; CLI)               — system package

This script does NOT run FunASR — it only makes the audio. Closing the loop
(audio -> FunASR -> transcript -> eval) happens on a machine with `.[asr]`.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import yaml  # noqa: E402


def _load_texts(cases_path: Path) -> list[tuple[str, str]]:
    data = yaml.safe_load(cases_path.read_text(encoding="utf-8")) or {}
    out = []
    for i, c in enumerate(data.get("cases", [])):
        out.append((f"case_{i:03d}_{c.get('expected_level','none')}", c["text"]))
    return out


def _engine_available() -> str | None:
    try:
        import piper  # noqa: F401

        return "piper"
    except Exception:
        pass
    try:
        import edge_tts  # noqa: F401

        return "edge-tts"
    except Exception:
        pass
    if shutil.which("espeak-ng"):
        return "espeak-ng"
    return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default=None)
    ap.add_argument("--out", default="data/audio/speaker_testset")
    args = ap.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    cases_path = Path(args.cases) if args.cases else root / "data/eval/speaker_redline_cases.yaml"
    out_dir = root / args.out
    texts = _load_texts(cases_path)

    engine = _engine_available()
    if engine is None:
        print(
            "[synth] No TTS engine available in this environment.\n"
            "        Install one on the 中控 machine to synthesize audio:\n"
            "          pip install piper-tts        # offline neural (recommended)\n"
            "          pip install edge-tts         # online neural\n"
            "          apt-get install espeak-ng    # offline robotic\n"
            f"[synth] Would synthesize {len(texts)} utterances -> {out_dir}\n"
            "[synth] For logic validation without audio, run: scripts/run_speaker_eval.py"
        )
        return 2

    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[synth] engine={engine}  cases={len(texts)}  out={out_dir}")
    if engine == "espeak-ng":
        import subprocess

        for name, text in texts:
            wav = out_dir / f"{name}.wav"
            subprocess.run(
                ["espeak-ng", "-v", "cmn", "-w", str(wav), text],
                check=False,
            )
        print(f"[synth] wrote {len(texts)} WAVs (espeak-ng, robotic — logic check only).")
    else:
        print(
            f"[synth] engine '{engine}' detected but adapter is a stub here; wire the "
            "concrete call on the target machine. Texts loaded and ready."
        )
    print("[synth] NEXT: feed WAVs through FunASR (.[asr]) -> transcripts -> real eval cases.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
