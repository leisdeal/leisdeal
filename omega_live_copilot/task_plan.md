# Task Plan: Leisdeal Live Copilot (V1)

> Source of truth: `PRD_v1.3.md` (this dir). Re-read PRD §7 acceptance criteria before building any module.
> One-line scope: **合规雷达 + 高频问题雷达，不是自动主播.**

## Current Phase
Phase 0 — Foundations (not started). **Blocked on operational deliverables (see Blockers).**

## Guiding Constraints (locked, do not soften)
- 红线召回 **≥98%** (comment L3 + speaker S2/S3).漏拦 = fatal. Lei may raise, never lower.
- Speaker S3 漏报 = fatal, no 5% tolerance.
- ASR hard metric = **红线短语召回**, not overall CER/readability.
- Safety-critical path never relies on LLM alone (rule → embedding → LLM fallback).
- LLM output never auto-broadcasts, never auto-writes FAQ. Lei审核 gate on all standard answers, redline word lists, and walk-back scripts.
- V1 platform = 抖音, self-room + own machine + 直播伴侣 local link only. No scraping others' rooms.
- Model tiers (Haiku/Sonnet/Opus) are capability slots via config — never hard-code model IDs.
- Speaker audio: local ASR + local storage; store only redline hit segment + context window, never full-session audio by default.

## Gates (progress is gated, not day-counted — PRD §10)
- **Gate 1 · Ingestion** — stable comments in + latency OK + reconnect + acceptable risk. No-Go → manual副屏 input (still a shipped V1 path, not a failure).
- **Gate 2 · 红线** — recall ≥98% + no dangerous misses + operator understands red card. No-Go → pause long-tail gen, keep rules + human judgment.
- **Gate 3 · 真实直播** — operator keeps using + recap valuable + hit rate improvable + fewer dangerous speaker claims. No-Go → downgrade to post-live recap tool.

## Phases

### Phase 0 — Foundations
- [ ] Repo skeleton per PRD §11 (`ingestion/ normalizer/ retrieval/ redline/ ui_api/ recap/ eval/ speaker_monitor/{asr,redline_audio,alert,recap_hooks}`)
- [ ] Config layer: model-tier config (Haiku/Sonnet/Opus → configurable IDs), ASR engine config, thresholds
- [ ] SQLite schema: FAQ table (§6), comment log (§6), `speaker_redline_events` (§7.8.10)
- [ ] Vector store choice + local JSONL raw-comment sink
- [ ] Redline seed word list scaffold (marked "pending Lei review")
- **Status:** pending

### Phase 1 — Speaker Redline Monitor (§7.8) — *IMPLEMENTED (logic), acoustic PENDING*
Rationale (PRD §7.8.1): cheapest (own mic, local ASR, zero ToS) + guards the heaviest liability + fully independent of comment ingestion. Can ship before Gate 1.
- [x] Streaming ASR interface + FunASR Paraformer engine (hotwords from redline vocab), engine via config
- [x] Text normalize → rule match (seed words) → embedding/intent (ngram) fallback
- [x] S1/S2/S3 classifier (§7.8.6), S3 priority over S2
- [x] Alert channel A: 中控屏 red bar (hit word / S-level / walk-back / ts / recap / 禁剪 flag)
- [x] Walk-back script library (§7.8.9) — **Lei-gated: unapproved never served as ready-to-read**
- [x] `speaker_redline_events` logging + walk-back state (100% logging even if alert fails)
- [x] Recap section "主播红线表达监控" (§7.8.11)
- [x] Offline fallback engine (Whisper) wired for 录播 → ASR → redline scan (No-Go 离线复盘)
- [x] Walk-back echo guard (§7.8.9): suppresses ONLY the self-trigger from the host reading back an approved walk-back (3 conditions); spontaneous 否定壳+承诺核 still fires; echo auto-marks origin `speaker_corrected=1` so recap 自我纠偏 data stays clean
- [x] Eval harness + synthetic seed set + `unittest` suite (32 tests green)
- [ ] **PENDING (needs real env):** FunASR live run over real recorded host voice; ≥2h soak; e2e P95 <1.2s on real audio; **98% S2/S3 acceptance on real acoustics** (sandbox has no FunASR/TTS)
- [ ] **PENDING (Lei):** approve/curate redline word list + walk-back scripts (all start `approved_by_lei: false`)
- **Self-test (logic-level, sandbox):** S1/S2/S3 recall 100% on 35-case synthetic set, 0 FP, detect P95 0.24ms. Acoustic recall = PENDING real audio.
- **Status:** implemented (logic verified) · acoustic acceptance PENDING real host-voice stream

### Phase 2 — Ingestion (§7.1, Gate 1)
- [ ] 直播伴侣 local-link comment capture PoC (2–4 day timebox for reverse-eng path)
- [ ] Ingest → SQLite (P95 <500ms) + JSONL sink
- [ ] Reconnect ≤5s + gap-marking for unrecoverable windows
- [ ] **Degrade path = shipped V1**: manual副屏 copy → input box → same downstream chain
- **Acceptance (§7.1):** ≥2h no drop, e2e <1s, reconnect ≤5s, dup ≤3%, own-room only.
- **Status:** pending (Gate 1)

### Phase 3 — Comment pipeline (§7.2–7.4)
- [ ] Cleaning: de-emoji/dedup/merge-similar/high-freq tag (don't drop compliance words)
- [ ] FAQ retrieval: SQLite + vector semantic + high-risk keyword boost → top-1 ≥85%, unknown routing
- [ ] L3 redline detect (rule → embedding → Haiku fallback), recall ≥98%, priority over FAQ
- **Status:** pending (Gate 2)

### Phase 4 — 中控屏 UI (§7.5)
- [ ] Four zones: A comment stream / B cards (green L1 / yellow L2 / red L3 / gray unknown) / C Top10 / D leads
- [ ] Operator ≤2s comprehension; L3 red card never covered; one-click mark actions
- **Status:** pending

### Phase 5 — LLM long-tail assist (§7.6) + Recap (§7.7)
- [ ] Long-tail: "仅供中控参考" tag, no auto-broadcast, no auto-FAQ, no promise sentences
- [ ] Recap (Sonnet tier, offline): 5-min generation, accurate freq stats, unknown export, FAQ review queue
- [ ] Push via Omega Telegram
- **Status:** pending

### Phase 6 — Eval + real-live trial (Gate 3)
- [ ] Eval harness: FAQ top-1, redline recall (comment + speaker), latency P95s
- [ ] Real live trial with test set (needs Lei deliverable ⑤)
- **Status:** pending (Gate 3)

## Blockers (operational deliverables owned by Lei — PRD §13)
Dev spins idle without ①②⑤:
- [ ] ① 高频问题 100 条 (FAQ starter set)
- [ ] ② L3 红线清单
- [ ] ③ 标准答案
- [ ] ④ 禁止说法 (forbidden_claims)
- [ ] ⑤ 一场真实直播测试集
- [ ] ⑥ 中控人选 · ⑦ 谁盯屏
- **Note:** Phase 1 (speaker monitor) can proceed on *seed* word lists (§7.8.5) independent of the full FAQ set — this is why it's the candidate first mover.

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| Speaker Redline Monitor (§7.8) as candidate Phase 1 first-mover | Cheapest, zero-ToS, guards heaviest liability, independent of ingestion (PRD §7.8.1) |
| Copilot lives in `omega_live_copilot/`, separate from content/marketing planning files | Different project, don't clobber existing packaging/XHS plans |
| Model IDs via config, not hard-coded | PRD §7.6 / §11 frozen constraint #3 |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| (none yet) | - | - |

## Confirmed Decisions (locked)
| Decision | Value |
|----------|-------|
| First build | **Speaker Monitor (§7.8), Phase 1.** Ingestion = Phase 2 |
| Runtime | Python for core + Phase 1. Config/IPC boundary designed so a **Node ingestion sidecar** can plug in for Phase 2 — 抓包 layer not forced into Python |
| ASR primary | **FunASR streaming Paraformer**, behind swappable `ASREngine` interface. Redline vocab used as **hotwords** to maximize red-line-phrase recall (the one hard metric) |
| ASR fallback | Whisper-family = **offline-only** (No-Go 离线复盘 mode), never real-time |
| Vector store | **sqlite-vec** (same SQLite, no extra service). Revisit only if FAQ grows to thousands |
| Walk-back scripts | **Lei-gated config file** (`config/walkback_scripts.yaml`), not hardcoded. Mechanism built, content slots left `approved_by_lei: false` |
| Self-test | speaker_monitor tested on simulated streamed transcripts (+ TTS synth script for real envs). **98% S2/S3 recall acceptance = PENDING real recorded host-voice stream** — TTS/logic tests validate detection logic only |

## Scaffold scope (this build)
- IMPLEMENT: shared layer (config, SQLite schemas incl. `speaker_redline_events`, eval harness) + `speaker_monitor/` end-to-end.
- STUB: `ingestion/ normalizer/ retrieval/ redline/ ui_api/ recap/` (FAQ/redline retrieval blocked on ops material — no FAQ answers, no eval set yet).

## Environment notes (sandbox)
- Python 3.11, PyYAML present; numpy + sqlite-vec installable. **No TTS binary / no FunASR** in sandbox → acoustic loop not runnable here; detection logic + eval run dependency-free via `unittest`.
