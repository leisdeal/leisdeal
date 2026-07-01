"""`olc-speaker-monitor` — run the speaker redline monitor.

Modes:
  --engine mock --transcript FILE   : feed known utterances (logic self-test / 副屏)
  --engine funasr                   : realtime from mic/stream (needs .[asr])
  --engine whisper_offline --audio F: No-Go 离线复盘 over a recording (needs .[asr_offline])
"""
from __future__ import annotations

import argparse
import json
import sys

from ..config import Config
from .asr.factory import build_engine
from .build import build_monitor, open_db
from .recap_hooks import build_speaker_redline_section, render_markdown


def _read_transcript(path: str) -> list[str]:
    utterances = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            if line.startswith("{"):
                try:
                    utterances.append(json.loads(line).get("text", ""))
                    continue
                except json.JSONDecodeError:
                    pass
            utterances.append(line)
    return [u for u in utterances if u]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Omega Live Copilot — Speaker Redline Monitor")
    ap.add_argument("--config", default=None)
    ap.add_argument("--engine", default=None, help="override speaker_monitor.asr.engine")
    ap.add_argument("--session-id", default="adhoc-session")
    ap.add_argument("--transcript", default=None, help="text/jsonl file (mock engine)")
    ap.add_argument("--audio", default=None, help="audio file (whisper_offline) or device")
    ap.add_argument("--no-color", action="store_true")
    ap.add_argument("--recap", action="store_true", help="print recap section after run")
    args = ap.parse_args(argv)

    cfg = Config.load(args.config)
    if args.engine:
        cfg.data.setdefault("speaker_monitor", {}).setdefault("asr", {})["engine"] = args.engine

    db = open_db(cfg)
    monitor, wordlist = build_monitor(cfg, db.conn, args.session_id, color=not args.no_color)
    engine = build_engine(cfg, hotwords=wordlist.hotwords())

    engine_name = cfg.get("speaker_monitor.asr.engine", "funasr")
    if engine_name == "mock":
        if not args.transcript:
            ap.error("--engine mock requires --transcript FILE")
        source = _read_transcript(args.transcript)
    elif engine_name == "whisper_offline":
        if not args.audio:
            ap.error("--engine whisper_offline requires --audio FILE")
        source = args.audio
    else:  # funasr realtime
        source = args.audio  # device/stream handle; engine-specific

    summary = monitor.run(engine, source)
    print("\n[olc] run summary:", json.dumps(summary, ensure_ascii=False, indent=2))

    if args.recap:
        section = build_speaker_redline_section(db.conn, args.session_id)
        print("\n" + render_markdown(section))
    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
