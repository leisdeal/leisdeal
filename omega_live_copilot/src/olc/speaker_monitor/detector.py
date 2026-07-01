"""Redline detector — rule layer + semantic fallback, S1/S2/S3 (PRD §7.8.4/§7.8.6).

Recall-first by construction: the rule layer is a pure substring/regex match on
the normalized transcript and owns the hard metric. The semantic layer only ADDS
hits (paraphrases); it never suppresses a rule hit. No LLM on this path.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..text import NormalizedText, normalize
from .embedding import EmbeddingProvider, NgramEmbedding
from .wordlist import RedlineEntry, WordList

LEVEL_ORDER = {"S1": 1, "S2": 2, "S3": 3}


@dataclass
class Detection:
    entry_id: str
    category: str
    level: str
    matched_phrase: str
    match_type: str  # "rule" | "semantic"
    score: float

    @property
    def severity(self) -> int:
        return LEVEL_ORDER[self.level]


class RedlineDetector:
    def __init__(
        self,
        wordlist: WordList,
        *,
        semantic_provider: EmbeddingProvider | None = None,
        semantic_enabled: bool = True,
        similarity_threshold: float = 0.62,
    ):
        self.wordlist = wordlist
        self.semantic_enabled = semantic_enabled
        self.similarity_threshold = similarity_threshold
        self.semantic = semantic_provider or NgramEmbedding()

    # ── matching ────────────────────────────────────────────────────────────
    def _rule_match(self, entry: RedlineEntry, norm: NormalizedText) -> str | None:
        for surface, squashed in zip(entry.surfaces(), entry._squashed_surfaces):
            if squashed and squashed in norm.squashed:
                return surface
        if entry._regex and entry._regex.search(norm.normalized):
            return entry.regex or ""
        return None

    def _semantic_match(self, entry: RedlineEntry, norm: NormalizedText) -> tuple[str, float] | None:
        best_phrase, best_score = "", 0.0
        # Compare normalized example n-grams against the normalized transcript.
        for raw_example, squashed_example in zip(entry.semantic, entry._squashed_semantic):
            score = self.semantic.similarity(squashed_example, norm.squashed)
            if score > best_score:
                best_phrase, best_score = raw_example, score
        if best_score >= self.similarity_threshold:
            return best_phrase, best_score
        return None

    def detect(self, text: str) -> list[Detection]:
        norm = normalize(text)
        detections: list[Detection] = []
        for entry in self.wordlist.entries:
            phrase = self._rule_match(entry, norm)
            if phrase is not None:
                detections.append(
                    Detection(entry.id, entry.category, entry.level, phrase, "rule", 1.0)
                )
                continue  # rule hit already covers this entry
            if self.semantic_enabled and entry.semantic:
                sem = self._semantic_match(entry, norm)
                if sem is not None:
                    detections.append(
                        Detection(entry.id, entry.category, entry.level, sem[0], "semantic", sem[1])
                    )
        # highest severity first; rule beats semantic at equal severity
        detections.sort(
            key=lambda d: (d.severity, d.match_type == "rule", d.score), reverse=True
        )
        return detections

    @staticmethod
    def primary(detections: list[Detection]) -> Detection | None:
        return detections[0] if detections else None
