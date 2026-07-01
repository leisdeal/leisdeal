# speaker_monitor — Speaker Redline Monitor (PRD §7.8)

Realtime monitor of the **host's own speech**. Independent of comment ingestion
(§7.8.2): runs even with all comment capture off. Safety path is **rule →
semantic, never LLM-only** (§7.8.4). Owns the one hard metric: red-line-phrase
recall.

## Flow
```
host speaks → ASR (FunASR streaming Paraformer) → normalize → rule match
            → semantic (ngram) fallback → S1/S2/S3 → alert + walk-back → log event → recap
```

## Layout
| File | Role |
| --- | --- |
| `wordlist.py` | loads `config/redline_words.yaml`; exposes ASR hotwords |
| `embedding.py` | dependency-free char-ngram semantic fallback (pluggable) |
| `detector.py` | rule + semantic, S1/S2/S3, S3-priority |
| `walkback.py` | **Lei-approval gate enforced in code**; unapproved = never ready-to-read |
| `events.py` | `speaker_redline_events` persistence (100% logging) |
| `alert/` | channel A 中控屏 red bar (`console.py`); channel B 耳返 = not-in-V1 |
| `asr/` | `base` interface · `funasr_engine` (primary, realtime) · `whisper_engine` (offline-only) · `mock_engine` (transcript injection for tests) · `factory` |
| `recap_hooks/` | 「主播红线表达监控」 recap section (§7.8.11) |
| `pipeline.py` | orchestrator (`SpeakerMonitor`) |
| `build.py` | config → wired monitor |
| `cli.py` | `olc-speaker-monitor` |

## Run

Logic self-test / 副屏 (no audio deps — works anywhere):
```bash
python -m olc.speaker_monitor.cli --engine mock --transcript utterances.txt --recap --no-color
```

Eval (measures recall by level, FP, detect P95):
```bash
python scripts/run_speaker_eval.py
```

Realtime (中控 machine, needs `pip install '.[asr]'` = FunASR + torch):
```bash
python -m olc.speaker_monitor.cli --engine funasr --session-id live-2026-07-01
```

Offline 复盘 fallback (No-Go mode, needs `.[asr_offline]`):
```bash
python -m olc.speaker_monitor.cli --engine whisper_offline --audio recording.wav --recap
```

## Acceptance status
- **Logic (sandbox):** ✅ 26 unittests green; synthetic eval S1/S2/S3 recall 100%, 0 FP, detect P95 0.24 ms.
- **Acoustic:** ⏳ **PENDING** — the 98% S2/S3 recall (§7.8.12) requires a real
  recorded host-voice stream through FunASR (real acoustics, 中英夹杂, noise).
  TTS/text validates detection logic only. See `scripts/synth_speaker_testset.py`.

## Known limitation (tracked)
The rule layer matches phrases regardless of negation/quotation — e.g. a host
reading a walk-back that *contains* a banned phrase ("我们不能承诺**包过**") will
re-trigger. This is intentional (safety-first: re-alert beats miss), but a
negation/quotation guard is a candidate refinement once real-audio FP data exists.
