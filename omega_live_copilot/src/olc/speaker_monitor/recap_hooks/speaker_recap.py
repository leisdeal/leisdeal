"""Recap section: 「主播红线表达监控」 (PRD §7.8.11).

Feeds the main recap (§7.7). Produces the structured stats + a markdown block:
hit count, S1/S2/S3 distribution, highest-risk snippets, timely-correction rate,
next must-ban words, pending forbidden_claims, no-reclip segments, next-session
reminders.
"""
from __future__ import annotations

import sqlite3

from ..events import fetch_session_events


def build_speaker_redline_section(conn: sqlite3.Connection, session_id: str) -> dict:
    rows = fetch_session_events(conn, session_id)
    by_level = {"S1": 0, "S2": 0, "S3": 0}
    corrected = 0
    correctable = 0  # S2/S3 — the levels that require a walk-back
    no_reclip = []
    must_ban: dict[str, str] = {}
    highest = []

    for r in rows:
        lvl = r["risk_level"]
        by_level[lvl] = by_level.get(lvl, 0) + 1
        if lvl in ("S2", "S3"):
            correctable += 1
            if r["speaker_corrected"]:
                corrected += 1
        if r["forbid_reclip"]:
            no_reclip.append({"ts": r["timestamp"], "phrase": r["matched_phrase"]})
        if lvl in ("S2", "S3"):
            must_ban[r["matched_phrase"]] = lvl
        if lvl == "S3":
            highest.append(
                {"ts": r["timestamp"], "phrase": r["matched_phrase"], "text": r["raw_transcript"]}
            )

    correction_rate = (corrected / correctable) if correctable else None
    return {
        "session_id": session_id,
        "total_hits": len(rows),
        "by_level": by_level,
        "s2_s3_correction_rate": correction_rate,
        "highest_risk_snippets": highest,
        "no_reclip_segments": no_reclip,
        "next_must_ban": sorted(must_ban.keys()),
        # New dangerous phrases feed the FAQ forbidden_claims review queue (§7.8.11).
        "pending_forbidden_claims_review": sorted(must_ban.items()),
    }


def render_markdown(section: dict) -> str:
    b = section["by_level"]
    rate = section["s2_s3_correction_rate"]
    rate_str = "—" if rate is None else f"{rate * 100:.0f}%"
    lines = [
        "## 主播红线表达监控 (§7.8.11)",
        "",
        f"- 命中总数: **{section['total_hits']}**  ·  S1 {b['S1']} / S2 {b['S2']} / S3 {b['S3']}",
        f"- S2/S3 及时纠偏率: **{rate_str}**",
    ]
    if section["highest_risk_snippets"]:
        lines.append("- 最高风险片段 (S3):")
        for s in section["highest_risk_snippets"]:
            lines.append(f"    - [{s['ts']}] 「{s['phrase']}」 — {s['text']}")
    if section["no_reclip_segments"]:
        lines.append("- ⛔ 禁止二次剪辑片段:")
        for s in section["no_reclip_segments"]:
            lines.append(f"    - [{s['ts']}] 「{s['phrase']}」")
    if section["next_must_ban"]:
        lines.append("- 下场必禁词: " + "、".join(f"「{w}」" for w in section["next_must_ban"]))
    lines.append("- 待入 forbidden_claims (Lei 审核): "
                 + ("、".join(f"{p}({l})" for p, l in section["pending_forbidden_claims_review"]) or "无"))
    return "\n".join(lines)
