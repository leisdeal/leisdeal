# Phase 2 Ingestion Sidecar Contract (v1) — PAPER

> **Status: paper contract only.** This defines the Node↔Python wire format for
> comment ingestion (PRD §7.1, Gate 1). It does **not** implement 抓包 / OCR /
> WebSocket / any capture logic — that is **blocked** on Lei's real 中控 machine
> and Lei's **explicit ToS risk acceptance** (§2, §12②). The capture method is a
> black box behind this format; this document only fixes the boundary so Phase 2
> can start without re-litigating the interface.
>
> Machine-readable schema: [`comment_event.schema.json`](./comment_event.schema.json)
> (authoritative for field names/types). This doc is the rationale + semantics.

## 1. Why a sidecar + wire contract

The 抓包 layer may be a **Node sidecar** (per the confirmed Phase-1 decision) so
it need not be rewritten in Python. The core **never imports the sidecar**. The
only coupling is this message format + transport + delivery semantics. Benefits:

- The capture method can change (直播伴侣 local link / OBS track / OCR / manual
  副屏) without touching the core — all of them emit the same `comment` frame.
- The **manual 副屏 degrade path** (§7.1 failure降级) is not a special case: the
  operator UI is just another emitter of `comment` frames with
  `capture_source="manual"`. Identical downstream — FAQ / redline / recap.
- The core stays language-agnostic about capture and enforces its safety/privacy
  invariants at one boundary (own-room-only, no raw PII, dedup, gap marking).

## 2. Design invariants (non-negotiable)

| # | Invariant | Source |
|---|-----------|--------|
| 1 | **Localhost only.** Loopback bind (127.0.0.1); core rejects non-loopback peers. No external exposure. | §2, §12 |
| 2 | **Own room only.** Core MUST drop any `comment` whose `room_id` ≠ configured own room. Defense in depth. | §2, §12② |
| 3 | **No raw PII across IPC / at rest.** Sidecar sends `username_hash`; if it can't hash, `username_display` is hashed at the boundary and the raw value is never persisted. | §12③ |
| 4 | **Sidecar fills capture-time fields only.** Processing fields (matched_faq_id, risk_level, card_type, …) are core-owned; sidecar MUST NOT send them. | §6 |
| 5 | **Capture method is out of contract.** How comments are obtained is a black box; gated on Lei ToS acceptance. | §2, Gate 1 |
| 6 | **No backfill fiction.** Unrecoverable gaps are declared, marked in recap, and never assumed recoverable. | §7.1④ |

## 3. Transports (config `ingestion.mode`)

| mode | How | Delivery | When |
|------|-----|----------|------|
| `jsonl` | Sidecar appends one JSON object per line to `storage.jsonl_raw_comments`; core tails. | At-least-once, durable, replayable. | PoC default; survives core restart. |
| `websocket` | Loopback ws at `ingestion.websocket.{host,port}`; one JSON object per text frame. | Best-effort; resync on reconnect. | Lower latency once stable. |
| `manual` | Operator UI emits identical `comment` frames directly to the core. | Synchronous. | 副屏 degrade path; always available. |

All three carry **the same message objects**. Switching transport does not change
the schema.

## 4. Envelope & versioning

Every message is a single JSON object with two envelope fields:

- `v` — contract major version (currently `1`). Core rejects an unknown major
  with a clear error; **additive** fields are backward-compatible within a major.
- `type` — discriminator: `comment` | `session_start` | `session_end` |
  `heartbeat` | `gap`.

## 5. Message types

### 5.1 `comment` (the payload)
Capture-time fields the sidecar provides:

| field | req | meaning |
|-------|-----|---------|
| `v`, `type` | ✓ | envelope |
| `session_id` | ✓ | groups to a live session (matches `session_start`) |
| `capture_seq` | ✓ | per-session monotonic, +1 per comment → ordering + loss estimation |
| `captured_at` | ✓ | ISO-8601 ms+tz; core measures e2e latency from here |
| `platform` | ✓ | `douyin` (V1) |
| `room_id` | ✓ | own room; core rejects mismatches |
| `comment_text` | ✓ | raw text; core normalizes |
| `username_hash` | rec | preferred hashed identity (see §7) |
| `username_display` | ✗ | discouraged fallback; hashed + dropped at boundary |
| `platform_msg_id` | ✗ | native id if available → primary dedup key |
| `capture_source` | ✗ | `live_companion`\|`obs`\|`ocr`\|`manual` |

### 5.2 `session_start` / `session_end`
Lifecycle. `session_start` carries `session_id, platform, room_id, started_at`
and optional `resume:true` for reconnect continuation. `session_end` carries
`ended_at` and sidecar `stats` (captured_count / last_capture_seq / declared_gaps)
for dup/loss reconciliation against the core's own counts.

### 5.3 `heartbeat`
Liveness at cadence ≤ `reconnect_max_seconds`/2. Carries `seq` = highest
`capture_seq` emitted, so the core can spot silent loss even when no comments
flow. Missing heartbeats > `reconnect_max_seconds` (5s, §7.1④) → core marks the
link down.

### 5.4 `gap`
Sidecar's honest "I lost some" signal (§7.1④). Carries `from/to` seq and/or ts
and a `reason` (`reconnect|buffer_overflow|capture_error|unknown`). Core marks a
data gap in recap; **does not** backfill.

## 6. Delivery semantics

- **Ordering.** `capture_seq` is strictly monotonic (+1) per session. Core
  processes in seq order within a small reorder window.
- **Loss estimation (§7.1⑤⑥).** Missing `capture_seq` values = lost messages;
  combined with `heartbeat.seq` and `session_end.stats`, the core estimates loss
  without a副屏 sample. (副屏 sampling remains the ground-truth cross-check.)
- **Dedup (target dup ≤3%, §7.1⑤).** Core dedup key precedence:
  1. `platform_msg_id` when present;
  2. else `sha256(session_id + capture_seq)` (catches exact re-delivery on jsonl replay);
  3. else content key `sha256(room_id + username_hash + comment_text)` within a
     short time window (catches platform re-emits without a stable id).
- **At-least-once** on `jsonl` (replay may re-deliver) → dedup is mandatory.

## 7. Username hashing (privacy, §12③)

Preferred: sidecar computes `username_hash = sha256(lower(trim(username)) +
session_salt)` truncated to 16 hex, where `session_salt` is per-session and never
logged. Raw username never crosses IPC. If source-side hashing is infeasible, the
sidecar may send `username_display`; the core hashes it at the ingestion boundary
with the same rule and discards the raw value (never persisted, never logged).

## 8. Latency & reconnect (§7.1②③④)

- Core stamps `ingest_at` on receipt; `ingest_latency_ms = ingest_at −
  captured_at` (§7.1② ingest P95<500ms). Card end-to-end (§7.1③ <1s) is measured
  from `captured_at` to card render.
- Reconnect ≤5s (§7.1④): heartbeat gap > 5s → link-down; on resume the sidecar
  sends `session_start{resume:true}` and continues the `capture_seq` series; any
  unrecoverable window is declared via `gap`.

## 9. Backpressure

`jsonl` is naturally buffered by the file. On `websocket`, if the core lags the
sidecar buffers locally up to a bounded cap, then emits a `gap{reason:
buffer_overflow}` rather than blocking capture or growing unbounded. Capture
never stalls waiting on the core.

## 10. Mapping to Phase 1 `comment_log` (validated, not applied)

Checked by `tests/test_ingestion_contract.py` against `src/olc/db/schema.sql`:

- **Sidecar → existing column:** `captured_at→ts`, `platform`, `room_id`,
  `username_hash`, `comment_text`.
- **Core-populated existing columns:** `normalized_text, matched_faq_id,
  risk_level, match_score, card_type, operator_action, speaker_response, result,
  notes`.
- **Requires a Phase 2 *additive* migration (PROPOSED, NOT APPLIED):**
  `session_id, capture_seq, platform_msg_id, capture_source, ingest_latency_ms`.
  These have no column in the Phase 1 `comment_log` yet. Do **not** alter the
  Phase 1 schema until Gate 1 is greenlit — the migration is additive and lands
  with the ingestion implementation.

## 11. Blocked / open items (owned by Lei, Phase 2 kickoff)

- [ ] **ToS risk acceptance** for the chosen capture method (blocks all capture code).
- [ ] Real 中控 machine to validate the 直播伴侣 local link (§7.1, Gate 1).
- [ ] Confirm whether the capture source exposes a stable `platform_msg_id`
      (decides dedup precedence in §6).
- [ ] `session_salt` management (where generated/stored; §7).
- [ ] Apply the additive `comment_log` migration (§10) when implementation starts.

## 12. Explicitly NOT in this contract

抓包 / reverse-engineering / OCR / WebSocket server or client code, the capture
method, any live network behavior. This is the interface only. Implementation is
Phase 2 and starts after Gate 1 + Lei's ToS acceptance.
