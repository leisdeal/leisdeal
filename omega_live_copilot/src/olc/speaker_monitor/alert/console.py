"""中控屏 red-bar alert (PRD §7.8.7 channel A). Shows hit phrase / S-level /
walk-back (or DRAFT/none) / timestamp / recap flag — the operator must parse it
fast, so the highest severity gets the loudest treatment."""
from __future__ import annotations

import sys

from .base import AlertChannel, AlertPayload

_ANSI = {
    "S1": "\033[43m\033[30m",  # yellow bg — 黄灯 (§7.8.6)
    "S2": "\033[41m\033[97m",  # red bg   — 红卡
    "S3": "\033[45m\033[97m",  # magenta bg — 强红卡
}
_RESET = "\033[0m"
_LEVEL_TAG = {"S1": "S1 轻微", "S2": "S2 危险", "S3": "S3 严重"}


class ConsoleAlert(AlertChannel):
    name = "console"

    def __init__(self, stream=None, color: bool = True):
        self.stream = stream or sys.stdout
        self.color = color

    def emit(self, payload: AlertPayload) -> None:
        ev = payload.event
        wb = payload.walkback
        col = _ANSI.get(ev.risk_level, "") if self.color else ""
        reset = _RESET if self.color else ""
        bar = f"{col} ▌红线 {_LEVEL_TAG.get(ev.risk_level, ev.risk_level)} {reset}"

        wb_line = _walkback_line(wb)
        reclip = "  ⛔禁剪" if ev.forbid_reclip else ""
        recap = "  📋入复盘" if ev.include_in_recap else ""

        lines = [
            "",
            f"{bar}  [{ev.timestamp}]{reclip}{recap}",
            f"    命中: 「{ev.matched_phrase}」  ({ev.match_type}/{ev.category})",
            f"    原话: {ev.raw_transcript}",
            f"    {wb_line}",
        ]
        self.stream.write("\n".join(lines) + "\n")
        self.stream.flush()


def _walkback_line(wb) -> str:
    if wb.status == "APPROVED":
        return f"纠偏(可照读): {wb.ready_text}"
    if wb.status == "DRAFT_PENDING_LEI":
        safe = f"纠偏(可照读): {wb.ready_text}" if wb.ready_text else "纠偏: (无已审话术)"
        return f"{safe}\n    ⚠️ 该类目专用话术为草稿，待 Lei 审核，勿逐字照读: 「{wb.draft_text}」"
    return "纠偏: ⚠️ 无可用话术，按通用边界口径处理，勿承诺"
