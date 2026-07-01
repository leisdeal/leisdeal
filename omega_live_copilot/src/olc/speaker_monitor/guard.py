"""Walk-back echo guard (PRD §7.8.9 — self-trigger suppression).

NARROW SCOPE — read this before touching it:

The base detector fires on a banned phrase regardless of negation/quotation, and
that MUST stay: spontaneous "否定壳 + 承诺核" speech (e.g. 「这个不用担心，包过」)
is the most dangerous pattern and must still fire. This guard is NOT a general
negation exemption.

The ONLY thing suppressed here is the system biting its own tail: the system
serves an APPROVED walk-back → the host reads it aloud → that approved compliance
sentence itself contains a banned phrase (e.g. 「我们不能承诺包过」) → it would
re-alarm at the exact moment the host is correctly self-correcting. Left unfixed,
that trains the operator to ignore red cards — alert fatigue erodes the one
recall line we can't compromise, more insidiously than a miss.

Suppression requires ALL of:
  1. an approved walk-back was served recently (within the window), AND
  2. the current segment is highly similar to that served text (host is reading
     it back — not saying something new), AND
  3. the specific matched phrase is contained in that served walk-back text.

If the host reads the walk-back AND tacks on a fresh promise, the new phrase is
not in the served text (condition 3 fails) → it still fires. Everything outside
this exact echo keeps the current negation-agnostic firing.

Bonus: recognizing the echo also confirms the walk-back happened, so the
pipeline marks the originating event speaker_corrected=1 (feeds §7.8.11 without
polluting it — the read-back is not a fresh violation).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..text import char_ngrams, normalize


@dataclass
class ServedWalkback:
    squashed_text: str
    served_at: float           # session seconds (seg.t_end when served)
    origin_event_id: int | None


@dataclass
class EchoMatch:
    served: ServedWalkback
    coverage: float

    def contains_phrase(self, phrase_squashed: str) -> bool:
        return bool(phrase_squashed) and phrase_squashed in self.served.squashed_text


@dataclass
class WalkbackEchoGuard:
    enabled: bool = True
    window_seconds: float = 20.0
    similarity_threshold: float = 0.62
    min_chars: int = 8
    ngram: int = 3
    max_buffer: int = 16
    _buffer: list[ServedWalkback] = field(default_factory=list, repr=False)

    def register(self, ready_text: str, at_time: float, origin_event_id: int | None) -> None:
        """Record an APPROVED walk-back the system just served (and expects the
        host to read). Only approved text ever reaches here (ready_text is always
        an approved string by construction of WalkbackLibrary.resolve)."""
        if not self.enabled or not ready_text:
            return
        sq = normalize(ready_text).squashed
        if not sq:
            return
        self._buffer.append(ServedWalkback(sq, at_time, origin_event_id))
        if len(self._buffer) > self.max_buffer:
            self._buffer = self._buffer[-self.max_buffer :]

    def match_echo(self, seg_text: str, at_time: float) -> EchoMatch | None:
        """Return the best active served walk-back this segment is echoing, else None."""
        if not self.enabled or not self._buffer:
            return None
        seg_sq = normalize(seg_text).squashed
        if len(seg_sq) < self.min_chars:
            return None
        seg_ngrams = set(char_ngrams(seg_sq, self.ngram))
        if not seg_ngrams:
            return None

        best: ServedWalkback | None = None
        best_cov = 0.0
        for sw in self._buffer:
            if at_time - sw.served_at > self.window_seconds:
                continue
            wb_ngrams = set(char_ngrams(sw.squashed_text, self.ngram))
            if not wb_ngrams:
                continue
            # Fraction of what the host just SAID that is covered by the served
            # walk-back — i.e. "is this segment essentially a read-back of it?"
            # A fresh addition drops this below threshold.
            cov = len(seg_ngrams & wb_ngrams) / len(seg_ngrams)
            if cov > best_cov:
                best_cov, best = cov, sw
        if best is not None and best_cov >= self.similarity_threshold:
            return EchoMatch(best, best_cov)
        return None
