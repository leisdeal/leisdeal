"""Redline word list loader (PRD §7.8.5).

Compiles each entry for fast matching and exposes the union of surface forms as
ASR hotwords — feeding them to FunASR maximizes red-line-phrase recall, the only
hard ASR metric (§7.8.12 ASR 口径).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from ..text import normalize

VALID_LEVELS = ("S1", "S2", "S3")


@dataclass
class RedlineEntry:
    id: str
    category: str
    level: str
    phrases: list[str]
    aliases: list[str] = field(default_factory=list)
    regex: str | None = None
    semantic: list[str] = field(default_factory=list)
    approved_by_lei: bool = False

    # compiled/normalized (filled in __post_init__)
    _squashed_surfaces: list[str] = field(default_factory=list, repr=False)
    _squashed_semantic: list[str] = field(default_factory=list, repr=False)
    _regex: re.Pattern | None = field(default=None, repr=False)

    def __post_init__(self):
        if self.level not in VALID_LEVELS:
            raise ValueError(f"Entry {self.id}: bad level {self.level!r}")
        surfaces = list(self.phrases) + list(self.aliases)
        # Match against the space-stripped ("squashed") transcript form.
        self._squashed_surfaces = [normalize(s).squashed for s in surfaces if s.strip()]
        # Semantic examples MUST be normalized the same way as the transcript
        # (lowercase, no spaces) or n-gram overlap breaks on case/spacing —
        # e.g. "FDA" vs "fda". A miss here on an S3 example is a fatal gap.
        self._squashed_semantic = [normalize(s).squashed for s in self.semantic if s.strip()]
        self._regex = re.compile(self.regex) if self.regex else None

    def surfaces(self) -> list[str]:
        return list(self.phrases) + list(self.aliases)


class WordList:
    def __init__(self, entries: list[RedlineEntry], meta: dict | None = None):
        self.entries = entries
        self.meta = meta or {}

    @classmethod
    def load(cls, path: str | Path) -> "WordList":
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        entries = []
        for raw in data.get("entries", []):
            entries.append(
                RedlineEntry(
                    id=raw["id"],
                    category=raw.get("category", "uncategorized"),
                    level=raw["level"],
                    phrases=raw.get("phrases", []),
                    aliases=raw.get("aliases", []),
                    regex=raw.get("regex"),
                    semantic=raw.get("semantic", []),
                    approved_by_lei=bool(raw.get("approved_by_lei", False)),
                )
            )
        if not entries:
            raise ValueError(f"No redline entries loaded from {path}")
        return cls(entries, meta=data.get("meta", {}))

    def hotwords(self) -> list[str]:
        """De-duplicated surface forms for ASR hotword boosting (§7.8 asr)."""
        seen: dict[str, None] = {}
        for e in self.entries:
            for s in e.surfaces():
                s = s.strip()
                if s:
                    seen.setdefault(s, None)
        return list(seen.keys())

    def unapproved(self) -> list[RedlineEntry]:
        return [e for e in self.entries if not e.approved_by_lei]
