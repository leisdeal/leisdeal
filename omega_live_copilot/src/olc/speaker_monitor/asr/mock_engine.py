"""Transcript-injection ASR (no audio deps).

Used for unit tests and the logic-level self-test: it turns a list of known
utterances into TranscriptSegments as if streamed. This validates the whole
detection -> classify -> alert -> log -> recap chain deterministically.

NOTE: this exercises detection logic ONLY. The acoustic loop (real audio ->
FunASR) and the 98% S2/S3 recall acceptance require real recorded host audio in
a real environment (PRD §7.8.12) — see scripts/synth_speaker_testset.py.
"""
from __future__ import annotations

from typing import Iterable, Iterator

from .base import ASREngine, TranscriptSegment


class MockStreamingASR(ASREngine):
    name = "mock"
    realtime = True

    def __init__(self, hotwords: list[str] | None = None, seg_seconds: float = 3.0):
        super().__init__(hotwords)
        self.seg_seconds = seg_seconds

    def stream(self, audio_source: Iterable[str]) -> Iterator[TranscriptSegment]:
        """`audio_source` = iterable of utterance strings."""
        t = 0.0
        for utterance in audio_source:
            seg = TranscriptSegment(
                text=utterance,
                t_start=t,
                t_end=t + self.seg_seconds,
                is_final=True,
                asr_latency_ms=0.0,
            )
            t += self.seg_seconds
            yield seg
