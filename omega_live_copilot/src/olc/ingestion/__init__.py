"""ingestion/ — Phase 2 (STUB). PRD §7.1, Gate 1.

Captures 抖音 comments via the 直播伴侣 local link (own room, own machine only).
Degrade path (= shipped V1): manual 副屏 copy -> input box -> same downstream.

IPC BOUNDARY (per confirmed decision): the 抓包 layer may be a **Node sidecar**
so it need not be rewritten in Python. The core NEVER imports the sidecar; the
coupling is a wire CONTRACT only.

  ► Contract (PAPER, drafted): docs/ingestion_contract.md
  ► Wire schema (authoritative): docs/comment_event.schema.json
  ► Conformance vs Phase 1 comment_log: tests/test_ingestion_contract.py

Transports (config `ingestion.mode`): jsonl | websocket | manual — all carry the
same `comment`/`session_start`/`session_end`/`heartbeat`/`gap` frames.

NOT IMPLEMENTED HERE: 抓包 / OCR / WebSocket / capture logic. Blocked on Lei's
real 中控 machine + explicit ToS risk acceptance (§2, §12②). Acceptance (§7.1):
≥2h no drop, ingest P95<500ms, e2e<1s, reconnect≤5s, dup≤3%, own-room only.
"""

__all__: list[str] = []


def not_implemented() -> None:
    raise NotImplementedError(
        "ingestion is Phase 2 (Gate 1). Speaker Monitor (§7.8) is Phase 1 and is "
        "fully independent of this module (§7.8.2)."
    )
