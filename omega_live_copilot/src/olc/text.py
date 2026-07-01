"""Text normalization for redline matching.

The rule layer owns the hard recall metric, so normalization must be aggressive
about the noise ASR introduces (spacing, full/half width, emoji, punctuation)
WITHOUT dropping compliance-bearing characters (PRD §7.2 验收: 关键合规词不被误删).

Two views are produced:
  - ``normalized``: cleaned, lowercased, punctuation/emoji stripped, but spaces
    between tokens preserved as single spaces (for regex / word logic).
  - ``squashed``:   normalized with ALL whitespace removed, so phrase matching
    survives ASR inserting spaces inside a Chinese phrase ("包 清关" -> "包清关").
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# Emoji + pictographs + variation selectors (no external dep).
_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0001F1E6-\U0001F1FF"
    "\U0000FE00-\U0000FE0F"
    "\U00002190-\U000021FF"
    "]+",
    flags=re.UNICODE,
)

# Keep CJK, ASCII letters/digits, and whitespace. Drop everything else
# (punctuation, symbols) — none of it carries a redline claim.
_KEEP_RE = re.compile(r"[^\w一-鿿\s]", flags=re.UNICODE)
_WS_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class NormalizedText:
    original: str
    normalized: str   # spaces collapsed to single, lowercased
    squashed: str     # all whitespace removed


def normalize(text: str) -> NormalizedText:
    if text is None:
        text = ""
    # Full-width -> half-width, compatibility fold.
    nf = unicodedata.normalize("NFKC", text)
    nf = _EMOJI_RE.sub(" ", nf)
    nf = _KEEP_RE.sub(" ", nf)
    nf = nf.lower()
    normalized = _WS_RE.sub(" ", nf).strip()
    squashed = re.sub(r"\s+", "", normalized)
    return NormalizedText(original=text, normalized=normalized, squashed=squashed)


def char_ngrams(s: str, n: int) -> list[str]:
    """Char n-grams over the squashed form; used by the ngram embedding fallback."""
    s = re.sub(r"\s+", "", s)
    if len(s) < n:
        return [s] if s else []
    return [s[i : i + n] for i in range(len(s) - n + 1)]
