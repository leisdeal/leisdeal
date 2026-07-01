"""Speaker Redline Monitor (PRD §7.8) — the implemented Phase 1 module.

Listens ONLY to the host's own speech. Independent of comment ingestion (§7.8.2):
runs even with all comment capture off. Safety path is rule -> semantic, never
LLM-only (§7.8.4). Detection owns the one hard metric: red-line-phrase recall.
"""
from .detector import Detection, RedlineDetector
from .pipeline import SpeakerMonitor
from .wordlist import RedlineEntry, WordList

__all__ = ["RedlineDetector", "Detection", "SpeakerMonitor", "WordList", "RedlineEntry"]
