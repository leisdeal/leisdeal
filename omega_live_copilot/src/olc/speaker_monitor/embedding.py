"""Semantic fallback for the redline detector (PRD §7.8.4 layer 2).

Catches paraphrases the rule layer misses ("肯定能过" ≈ "包过"). The default
provider is a dependency-free char-n-gram matcher, so the safety path never
requires a heavyweight embedding model to function. A real embedding model can
be slotted in via config (detector.semantic.provider) without touching callers.

Similarity here is intentionally asymmetric and recall-biased: it measures how
much of a short redline EXAMPLE's n-grams appear in the (possibly longer)
transcript — i.e. "does the host's sentence contain something like this".
"""
from __future__ import annotations

from typing import Protocol

from ..text import char_ngrams


class EmbeddingProvider(Protocol):
    def similarity(self, example: str, text: str) -> float:  # pragma: no cover - protocol
        ...


class NgramEmbedding:
    """Char n-gram coverage. No external dependency."""

    def __init__(self, n: int = 3):
        self.n = n

    def similarity(self, example: str, text: str) -> float:
        ex = set(char_ngrams(example, self.n))
        if not ex:
            return 0.0
        tx = set(char_ngrams(text, self.n))
        if not tx:
            return 0.0
        return len(ex & tx) / len(ex)


def build_provider(name: str, char_ngram: int = 3) -> EmbeddingProvider:
    name = (name or "ngram").lower()
    if name == "ngram":
        return NgramEmbedding(n=char_ngram)
    # Slot for a real model (e.g. sentence-transformers / FunASR embedding).
    # Kept explicit so an unconfigured model name fails loudly rather than
    # silently degrading the safety path.
    raise NotImplementedError(
        f"Semantic provider {name!r} not wired yet. Use 'ngram' (default) or add "
        f"the model adapter in olc/speaker_monitor/embedding.py."
    )
