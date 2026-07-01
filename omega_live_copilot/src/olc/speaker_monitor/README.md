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

## Walk-back echo guard (`guard.py`, §7.8.9)
The rule layer fires on a banned phrase **regardless of negation/quotation** —
and that stays, because spontaneous 「这个不用担心，包过」 (否定壳+承诺核) is the
most dangerous pattern. The one exception, handled by `WalkbackEchoGuard`, is the
system biting its own tail: it serves an approved walk-back → the host reads it →
that approved sentence contains a banned phrase → it would alarm at the exact
moment of correct self-correction (alert fatigue → erodes the recall line).

Suppression is narrow — ALL three required:
1. an approved walk-back was served within `guard.walkback_echo.window_seconds`,
2. the segment is a read-back of it (n-gram coverage ≥ threshold), and
3. the matched phrase is contained in that served text.

A fresh promise added in the same breath is not in the served text → it still
fires. Recognizing the echo also auto-marks the originating event
`speaker_corrected=1`, so the recap counts a correct read-back as a walk-back,
**not** a fresh violation (keeps §7.8.11 self-correction data clean). This is a
structural self-trigger (serve A → read A → A contains phrase), fixed on paper —
not something that needed real-audio data to reveal.
