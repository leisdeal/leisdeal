"""Whisper-family OFFLINE fallback (PRD decision: offline-only).

Used ONLY for No-Go 离线复盘 mode (§7.8.13): recorded file -> transcript ->
redline scan. Never on the realtime path. Deps imported lazily.
"""
from __future__ import annotations

from typing import Iterator

from .base import ASREngine, TranscriptSegment


class WhisperOfflineEngine(ASREngine):
    name = "whisper_offline"
    realtime = False

    def __init__(
        self,
        hotwords: list[str] | None = None,
        *,
        model: str = "large-v3",
        compute_type: str = "int8",
        language: str = "zh",
    ):
        super().__init__(hotwords)
        self.model = model
        self.compute_type = compute_type
        self.language = language
        self._model = None

    def _lazy_model(self):
        if self._model is not None:
            return self._model
        try:
            from faster_whisper import WhisperModel  # type: ignore
        except ImportError as e:  # pragma: no cover - env-dependent
            raise RuntimeError(
                "faster-whisper not installed. This is the OFFLINE 复盘 fallback: "
                "pip install '.[asr_offline]'. Do not use it for realtime."
            ) from e
        self._model = WhisperModel(self.model, compute_type=self.compute_type)
        return self._model

    def stream(self, audio_source) -> Iterator[TranscriptSegment]:  # pragma: no cover - needs audio+model
        """`audio_source` = path to a recorded audio file."""
        model = self._lazy_model()
        segments, _ = model.transcribe(str(audio_source), language=self.language)
        for s in segments:
            text = (s.text or "").strip()
            if text:
                yield TranscriptSegment(
                    text=text, t_start=float(s.start), t_end=float(s.end), is_final=True
                )
