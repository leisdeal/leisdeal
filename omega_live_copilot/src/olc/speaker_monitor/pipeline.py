"""Speaker monitor orchestrator (PRD §7.8.4 workflow).

    host speaks -> ASR -> normalize -> rule match -> semantic fallback
                -> alert -> (walk back) -> write event

Runs independently of comment ingestion (§7.8.2). No LLM on this path (§7.8.4).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from ..config import Config
from ..text import normalize
from ..timing import LatencyRecorder
from .alert.base import AlertChannel, AlertPayload
from .detector import Detection, RedlineDetector
from .events import RedlineEvent, write_event
from .walkback import WalkbackLibrary


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds")


class SpeakerMonitor:
    def __init__(
        self,
        cfg: Config,
        conn,
        detector: RedlineDetector,
        walkback: WalkbackLibrary,
        alert_channels: list[AlertChannel],
        session_id: str,
        *,
        recorder: LatencyRecorder | None = None,
        now_fn: Callable[[], str] = _now_iso,
    ):
        self.cfg = cfg
        self.conn = conn
        self.detector = detector
        self.walkback = walkback
        self.alert_channels = alert_channels
        self.session_id = session_id
        self.recorder = recorder or LatencyRecorder()
        self.now_fn = now_fn

        self._forbid_levels = set(cfg.get("speaker_monitor.recap.forbid_reclip_levels", ["S3"]))
        self._include_s1 = bool(cfg.get("speaker_monitor.recap.include_s1_in_recap", False))
        self._detect_on_partials = bool(cfg.get("speaker_monitor.detector.detect_on_partials", False))
        self.events: list[RedlineEvent] = []

    def _build_event(self, seg_text: str, primary: Detection, all_hits: list[Detection]) -> tuple[RedlineEvent, "object"]:
        norm = normalize(seg_text)
        wb = self.walkback.resolve(primary.category)
        include = 1 if (primary.level in ("S2", "S3") or self._include_s1) else 0
        forbid = 1 if primary.level in self._forbid_levels else 0
        other = [f"{d.matched_phrase}({d.level})" for d in all_hits[1:]]
        return RedlineEvent(
            session_id=self.session_id,
            timestamp=self.now_fn(),
            raw_transcript=seg_text,
            normalized_text=norm.normalized,
            matched_phrase=primary.matched_phrase,
            risk_level=primary.level,
            category=primary.category,
            suggested_walkback=wb.ready_text,
            walkback_status=wb.status,
            match_type=primary.match_type,
            alert_channel=",".join(c.name for c in self.alert_channels),
            operator_action="",
            speaker_corrected=0,
            correction_text="",
            include_in_recap=include,
            forbid_reclip=forbid,
            notes=("其他命中: " + "; ".join(other)) if other else "",
        ), wb

    def process_segment(self, seg) -> RedlineEvent | None:
        text = getattr(seg, "text", seg)
        is_final = getattr(seg, "is_final", True)
        if not is_final and not self._detect_on_partials:
            return None

        with self.recorder.measure("detect"):
            hits = self.detector.detect(text)
        if seg is not None and getattr(seg, "asr_latency_ms", None) is not None:
            self.recorder.add("asr", seg.asr_latency_ms)
        if not hits:
            return None

        primary = hits[0]
        event, wb = self._build_event(text, primary, hits)

        # Persist FIRST — 100% of detections must be logged (§7.8.12 ⑤),
        # even if an alert channel fails.
        write_event(self.conn, event)
        self.events.append(event)

        payload = AlertPayload(event=event, walkback=wb)
        with self.recorder.measure("display"):
            for ch in self.alert_channels:
                try:
                    ch.emit(payload)
                except Exception as e:  # a broken channel must not drop the event
                    event.notes = (event.notes + f" [alert:{ch.name} failed: {e}]").strip()
        return event

    def run(self, engine, audio_source) -> dict:
        """Consume the engine's transcript stream to completion; return a summary."""
        for seg in engine.stream(audio_source):
            self.process_segment(seg)
        return self.summary()

    def summary(self) -> dict:
        by_level = {"S1": 0, "S2": 0, "S3": 0}
        for e in self.events:
            by_level[e.risk_level] = by_level.get(e.risk_level, 0) + 1
        return {
            "session_id": self.session_id,
            "total_events": len(self.events),
            "by_level": by_level,
            "latency": self.recorder.summary(),
        }
