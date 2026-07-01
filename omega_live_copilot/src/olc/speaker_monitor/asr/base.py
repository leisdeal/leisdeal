"""ASR engine interface (PRD §7.8.4). Swappable so FunASR (primary, realtime) and
Whisper (offline fallback) share one contract; the pipeline is engine-agnostic.

The ONLY hard ASR metric is red-line-phrase recall, not overall CER (§7.8.12
ASR 口径) — engines are judged by whether the phrase survives to text, so the
primary engine injects the redline vocab as hotwords.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterator


@dataclass
class TranscriptSegment:
    text: str
    t_start: float          # seconds into the session
    t_end: float
    is_final: bool = True
    asr_latency_ms: float | None = None   # engine-reported, if available


class ASREngine(ABC):
    """Streams transcript segments from an audio source."""

    name: str = "base"
    realtime: bool = True

    def __init__(self, hotwords: list[str] | None = None):
        self.hotwords = hotwords or []

    @abstractmethod
    def stream(self, audio_source) -> Iterator[TranscriptSegment]:
        """Yield TranscriptSegments. `audio_source` meaning is engine-specific
        (device id / file path / iterable of PCM chunks / iterable of texts)."""
        raise NotImplementedError
