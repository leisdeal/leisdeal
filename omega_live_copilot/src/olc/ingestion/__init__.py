"""ingestion/ — Phase 2 (STUB). PRD §7.1, Gate 1.

Captures 抖音 comments via the 直播伴侣 local link (own room, own machine only).
Degrade path (= shipped V1): manual 副屏 copy -> input box -> same downstream.

IPC BOUNDARY (per confirmed decision): the 抓包 layer may be a **Node sidecar**
so it need not be rewritten in Python. The sidecar feeds the Python core through
one of the config `ingestion.mode` transports, writing this message shape:

    {"ts": ISO8601, "platform": "douyin", "room_id": str,
     "username_hash": str, "comment_text": str}

  - mode: "jsonl"      -> append lines to storage.jsonl_raw_comments (core tails)
  - mode: "websocket"  -> local ws at ingestion.websocket.{host,port} (core reads)
  - mode: "manual"     -> operator pastes into the UI; core ingests directly

The core NEVER imports the sidecar; contract = the message shape + transport.
Acceptance (§7.1): ≥2h no drop, ingest P95<500ms, e2e<1s, reconnect≤5s, dup≤3%,
own-room only.
"""

__all__: list[str] = []


def not_implemented() -> None:
    raise NotImplementedError(
        "ingestion is Phase 2 (Gate 1). Speaker Monitor (§7.8) is Phase 1 and is "
        "fully independent of this module (§7.8.2)."
    )
