"""speaker_redline_events persistence (PRD §7.8.10). 100% of detections must be
logged with walk-back status (§7.8.12 ⑤)."""
from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass, field


@dataclass
class RedlineEvent:
    session_id: str
    timestamp: str
    raw_transcript: str
    normalized_text: str
    matched_phrase: str
    risk_level: str
    category: str
    suggested_walkback: str = ""
    walkback_status: str = "NONE"
    match_type: str = "rule"
    alert_channel: str = ""
    operator_action: str = ""
    speaker_corrected: int = 0
    correction_text: str = ""
    include_in_recap: int = 1
    forbid_reclip: int = 0
    notes: str = ""
    event_id: int | None = field(default=None)


_COLUMNS = [
    "session_id", "timestamp", "raw_transcript", "normalized_text", "matched_phrase",
    "risk_level", "category", "suggested_walkback", "walkback_status", "match_type",
    "alert_channel", "operator_action", "speaker_corrected", "correction_text",
    "include_in_recap", "forbid_reclip", "notes",
]


def write_event(conn: sqlite3.Connection, event: RedlineEvent) -> int:
    d = asdict(event)
    placeholders = ",".join("?" for _ in _COLUMNS)
    cols = ",".join(_COLUMNS)
    cur = conn.execute(
        f"INSERT INTO speaker_redline_events ({cols}) VALUES ({placeholders})",
        [d[c] for c in _COLUMNS],
    )
    conn.commit()
    event.event_id = cur.lastrowid
    return cur.lastrowid


def fetch_session_events(conn: sqlite3.Connection, session_id: str) -> list[sqlite3.Row]:
    return list(
        conn.execute(
            "SELECT * FROM speaker_redline_events WHERE session_id = ? ORDER BY event_id",
            (session_id,),
        )
    )


def mark_corrected(conn: sqlite3.Connection, event_id: int, correction_text: str = "") -> None:
    """Operator/host confirms a walk-back happened (§7.8.9)."""
    conn.execute(
        "UPDATE speaker_redline_events SET speaker_corrected = 1, correction_text = ? "
        "WHERE event_id = ?",
        (correction_text, event_id),
    )
    conn.commit()
