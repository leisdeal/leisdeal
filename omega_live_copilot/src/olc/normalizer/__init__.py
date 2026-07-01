"""normalizer/ — Phase 3 (STUB). PRD §7.2 评论清洗.

De-emoji / dedup / drop-noise / merge-similar / high-freq tagging for the COMMENT
stream. Must not delete compliance-bearing words (§7.2 验收).

Note: the speaker monitor has its own text normalization (olc/text.py) tuned for
ASR noise; this module is the comment-side analogue and can reuse olc.text.
Blocked on ingestion (Phase 2) + a real comment sample.
"""

__all__: list[str] = []
