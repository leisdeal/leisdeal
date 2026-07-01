# Omega Live Copilot (V1)

Leisdeal 直播间的**合规雷达 + 高频问题雷达**——不是自动主播。挂载于 Leisdeal Omega。

- **Spec (source of truth):** [`PRD_v1.3.md`](./PRD_v1.3.md)
- **Roadmap:** [`task_plan.md`](./task_plan.md)
- **Status:** Phase 1 (§7.8 Speaker Redline Monitor) **implemented + tested** (logic-level);
  acoustic 98% acceptance PENDING real host-voice audio. Shared layer (config, DB, eval)
  implemented. Phases 2–5 (comment ingestion/FAQ/UI/recap) are stubs — see `src/olc/*/__init__.py`.

## Quickstart
```bash
pip install -e '.[dev]'            # PyYAML + numpy + sqlite-vec (core needs only PyYAML)
python -m unittest discover -s tests    # 26 tests
python scripts/run_speaker_eval.py      # detector eval report
# Speaker monitor over injected transcript (no audio deps):
python -m olc.speaker_monitor.cli --engine mock --transcript utterances.txt --recap
```
See [`src/olc/speaker_monitor/README.md`](./src/olc/speaker_monitor/README.md) for realtime/offline modes.

## What V1 does

```
评论进入 → FAQ / 红线命中 → 中控屏出卡片 → 人工决定是否上播 → 散场复盘
        ‖  (并行、独立)
主播说话 → 本地 ASR → 红线命中 → 报警 + walk-back → 复盘
```

Core value = ① 红线拦截 ② 标准答案命中 ③ 高频问题识别 ④ 线索捕获 ⑤ 直播复盘.
Generative answers are long-tail assist only, operator-eyes only, never auto-broadcast.

## Module tree → PRD map (§11)

| Path | PRD | Responsibility | Key acceptance |
| --- | --- | --- | --- |
| `ingestion/` | §7.1 | 直播伴侣 local-link comment capture (+ manual副屏 degrade path) | ≥2h no drop, e2e <1s, reconnect ≤5s |
| `normalizer/` | §7.2 | de-emoji / dedup / merge-similar / high-freq tag | no compliance words dropped |
| `retrieval/` | §7.3 | SQLite + vector + keyword-boost FAQ search | top-1 ≥85%, unknown routing |
| `redline/` | §7.4 | L3 detect: rule → embedding → Haiku fallback | **recall ≥98%**, priority over FAQ |
| `ui_api/` | §7.5 | 中控屏 four-zone API | operator ≤2s, red card never covered |
| `recap/` | §7.7 | post-live report (Sonnet tier, offline) | ≤5min, FAQ review queue |
| `eval/` | §8/§9 | metrics harness (recall, top-1, latency) | gates measurable |
| `speaker_monitor/` | §7.8 | **realtime speaker redline monitor (independent)** | S2/S3 recall ≥98%, e2e P95 <1.2s |
| `speaker_monitor/asr/` | §7.8.4 | local streaming ASR (config-driven engine) | 红线短语召回 is the only hard metric |
| `speaker_monitor/redline_audio/` | §7.8.6 | S1/S2/S3 classify on transcript | S3 miss = fatal |
| `speaker_monitor/alert/` | §7.8.7 | 中控屏 red bar (A) + optional 耳返 (B) | no rhythm break |
| `speaker_monitor/recap_hooks/` | §7.8.11 | "主播红线表达监控" recap section | 100% events logged w/ walk-back |

## Data layer (§11)
SQLite (FAQ / logs / recap) + Vector Store (semantic) + CSV/Google Sheet (human review) + local JSONL (raw comments).

Tables: FAQ (§6) · comment log (§6) · `speaker_redline_events` (§7.8.10).

## Model tiers (§11 — capability slots, IDs via config, never hard-coded)
- **Haiku 档** — batch classify / recap draft
- **Sonnet 档** — long-tail reference / recap
- **Opus 档** — high-risk script review / redline escalation

## Non-negotiables (frozen)
- 红线召回 **≥98%**; speaker S3 miss = fatal. Lei may raise thresholds, never lower.
- Lei审核 gate on: all standard answers, redline word lists, walk-back scripts.
- No LLM-alone on safety path. No auto-broadcast. No auto-FAQ writes.
- Own room + own machine only. No scraping others' rooms / no public-data-collection product.
- Speaker audio: local only, store redline segments + context, not full sessions.

## Not in V1
成交率 / GMV / 剪辑 / 全平台覆盖 / TikTok US 评论 / CRM / 多平台中控 (Phase 2 backlog, §14).
