"""Assemble a SpeakerMonitor from config — single wiring point for CLI/tests."""
from __future__ import annotations

from ..config import Config
from ..db import Database
from .alert.base import AlertChannel
from .alert.console import ConsoleAlert
from .detector import RedlineDetector
from .embedding import build_provider
from .pipeline import SpeakerMonitor
from .walkback import WalkbackLibrary
from .wordlist import WordList


def build_wordlist(cfg: Config) -> WordList:
    return WordList.load(cfg.resolve_path("speaker_monitor.detector.wordlist_path"))


def build_detector(cfg: Config, wordlist: WordList) -> RedlineDetector:
    sem = cfg.get("speaker_monitor.detector.semantic", {}) or {}
    provider = build_provider(sem.get("provider", "ngram"), sem.get("char_ngram", 3))
    return RedlineDetector(
        wordlist,
        semantic_provider=provider,
        semantic_enabled=bool(sem.get("enabled", True)),
        similarity_threshold=float(sem.get("similarity_threshold", 0.62)),
    )


def build_walkback(cfg: Config) -> WalkbackLibrary:
    return WalkbackLibrary.load(
        cfg.resolve_path("speaker_monitor.walkback.path"),
        require_approval=bool(cfg.get("speaker_monitor.walkback.require_lei_approval", True)),
    )


def build_alerts(cfg: Config, color: bool = True) -> list[AlertChannel]:
    channels: list[AlertChannel] = []
    for name in cfg.get("speaker_monitor.alert.channels", ["console"]):
        if name == "console":
            channels.append(ConsoleAlert(color=color))
        # 'earpiece' (channel B) intentionally not wired in V1 (§7.8.7).
    return channels or [ConsoleAlert(color=color)]


def build_monitor(cfg: Config, conn, session_id: str, *, color: bool = True):
    wordlist = build_wordlist(cfg)
    detector = build_detector(cfg, wordlist)
    walkback = build_walkback(cfg)
    alerts = build_alerts(cfg, color=color)
    monitor = SpeakerMonitor(cfg, conn, detector, walkback, alerts, session_id)
    return monitor, wordlist


def open_db(cfg: Config) -> Database:
    db = Database(cfg.resolve_path("storage.sqlite_path"))
    db.init_schema()
    return db
