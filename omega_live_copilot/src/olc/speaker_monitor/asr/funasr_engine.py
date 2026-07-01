"""FunASR streaming Paraformer — PRIMARY realtime engine (PRD §7.8 decision).

Heavy deps (funasr, torch) are imported lazily so the rest of the package — and
all tests — run without them. Redline vocab is passed as hotwords to maximize
red-line-phrase recall (the one hard ASR metric, §7.8.12).

This engine is written for a real environment (mic/PCM stream). It is NOT
exercised in the sandbox (no funasr/torch, no audio). Validate it on the 中控
machine against a real recorded host stream.
"""
from __future__ import annotations

from typing import Iterator

from .base import ASREngine, TranscriptSegment


class FunASRStreamingEngine(ASREngine):
    name = "funasr"
    realtime = True

    def __init__(
        self,
        hotwords: list[str] | None = None,
        *,
        model: str = "paraformer-zh-streaming",
        vad_model: str = "fsmn-vad",
        device: str = "cpu",
        sample_rate: int = 16000,
        chunk_ms: int = 300,
        hotword_weight: float = 20.0,
    ):
        super().__init__(hotwords)
        self.model = model
        self.vad_model = vad_model
        self.device = device
        self.sample_rate = sample_rate
        self.chunk_ms = chunk_ms
        self.hotword_weight = hotword_weight
        self._model = None

    def _lazy_model(self):
        if self._model is not None:
            return self._model
        try:
            from funasr import AutoModel  # type: ignore
        except ImportError as e:  # pragma: no cover - env-dependent
            raise RuntimeError(
                "FunASR not installed. Install the realtime ASR extra on the 中控 "
                "machine:  pip install '.[asr]'  (funasr + torch). For sandbox/test "
                "use engine='mock'; for No-Go offline use engine='whisper_offline'."
            ) from e
        self._model = AutoModel(model=self.model, vad_model=self.vad_model, device=self.device)
        return self._model

    def _hotword_str(self) -> str:
        # FunASR takes space-separated hotwords.
        return " ".join(self.hotwords)

    def stream(self, audio_source) -> Iterator[TranscriptSegment]:  # pragma: no cover - needs audio+model
        """`audio_source` = iterable of PCM float chunks (mic / file reader).

        Streaming Paraformer keeps cache across chunks; on each final segment we
        emit a TranscriptSegment. Chunk framing per FunASR streaming recipe.
        """
        model = self._lazy_model()
        hotword = self._hotword_str()
        cache: dict = {}
        # 600ms lookback / 600ms lookahead is the documented streaming default.
        chunk_size = [0, 10, 5]
        t = 0.0
        step_s = self.chunk_ms / 1000.0
        for i, chunk in enumerate(audio_source):
            is_final = getattr(chunk, "is_final", False)
            res = model.generate(
                input=chunk,
                cache=cache,
                is_final=is_final,
                chunk_size=chunk_size,
                encoder_chunk_look_back=4,
                decoder_chunk_look_back=1,
                hotword=hotword,
            )
            text = (res[0].get("text", "") if res else "").strip()
            t += step_s
            if text:
                yield TranscriptSegment(
                    text=text, t_start=t - step_s, t_end=t, is_final=is_final
                )
