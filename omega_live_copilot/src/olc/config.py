"""Config loader — all tunables live in YAML, never hard-coded (PRD §7.6/§11).

Resolves ``config/default.yaml`` relative to the project root, supports a
dotted-path getter, and locates sibling files (wordlist, walkback) relative to
the same project root so scripts work from any CWD.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


def project_root() -> Path:
    """Repo dir that holds config/ and data/ (…/omega_live_copilot)."""
    # src/olc/config.py -> src/olc -> src -> omega_live_copilot
    return Path(__file__).resolve().parents[2]


class Config:
    """Thin dotted-path view over the merged YAML config."""

    def __init__(self, data: dict[str, Any], root: Path):
        self._data = data
        self.root = root

    @classmethod
    def load(cls, path: str | os.PathLike | None = None) -> "Config":
        root = project_root()
        cfg_path = Path(path) if path else root / "config" / "default.yaml"
        with open(cfg_path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        return cls(data, root)

    def get(self, dotted: str, default: Any = None) -> Any:
        node: Any = self._data
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def require(self, dotted: str) -> Any:
        sentinel = object()
        val = self.get(dotted, sentinel)
        if val is sentinel:
            raise KeyError(f"Missing required config key: {dotted}")
        return val

    def resolve_path(self, dotted_or_path: str) -> Path:
        """Resolve a config value (or literal path) against the project root."""
        raw = self.get(dotted_or_path, dotted_or_path)
        p = Path(raw)
        return p if p.is_absolute() else (self.root / p)

    @property
    def data(self) -> dict[str, Any]:
        return self._data
