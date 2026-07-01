"""Build the configured ASR engine (PRD §7.8.4: engine via config, not hard-coded)."""
from __future__ import annotations

from ...config import Config
from .base import ASREngine
from .mock_engine import MockStreamingASR


def build_engine(cfg: Config, hotwords: list[str] | None = None) -> ASREngine:
    engine = cfg.get("speaker_monitor.asr.engine", "funasr")
    use_hotwords = cfg.get("speaker_monitor.asr.use_redline_hotwords", True)
    hw = list(hotwords or []) if use_hotwords else []

    if engine == "mock":
        return MockStreamingASR(hotwords=hw)

    if engine == "funasr":
        from .funasr_engine import FunASRStreamingEngine

        f = cfg.get("speaker_monitor.asr.funasr", {}) or {}
        return FunASRStreamingEngine(
            hotwords=hw,
            model=f.get("model", "paraformer-zh-streaming"),
            vad_model=f.get("vad_model", "fsmn-vad"),
            device=f.get("device", "cpu"),
            sample_rate=cfg.get("speaker_monitor.asr.sample_rate", 16000),
            chunk_ms=cfg.get("speaker_monitor.asr.chunk_ms", 300),
            hotword_weight=cfg.get("speaker_monitor.asr.hotword_weight", 20.0),
        )

    if engine == "whisper_offline":
        from .whisper_engine import WhisperOfflineEngine

        w = cfg.get("speaker_monitor.asr.whisper_offline", {}) or {}
        return WhisperOfflineEngine(
            hotwords=hw,
            model=w.get("model", "large-v3"),
            compute_type=w.get("compute_type", "int8"),
            language=cfg.get("speaker_monitor.asr.language", "zh"),
        )

    raise ValueError(f"Unknown ASR engine {engine!r} (funasr | whisper_offline | mock)")
