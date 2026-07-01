"""Walk-back script resolution with the Lei-approval gate ENFORCED in code
(PRD §7.8.9).

Contract: the host must always have a safe, non-committal line to read, but an
UNAPPROVED AI-written script is never presented as ready-to-read — because a
correction that bends the compliance boundary is itself a new live liability.

resolve() therefore returns:
  - ready_text: an APPROVED string only (category script if approved, else the
    approved non-committal fallback).
  - draft_text: the unapproved category draft, surfaced for Lei review, or "".
  - status:     APPROVED | DRAFT_PENDING_LEI | NONE
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

STATUS_APPROVED = "APPROVED"
STATUS_DRAFT = "DRAFT_PENDING_LEI"
STATUS_NONE = "NONE"


@dataclass
class WalkbackResult:
    category: str
    ready_text: str
    draft_text: str
    status: str

    @property
    def is_approved(self) -> bool:
        return self.status == STATUS_APPROVED


class WalkbackLibrary:
    def __init__(self, scripts: dict, fallback: dict, *, require_approval: bool = True):
        self._scripts = scripts or {}
        self._fallback = fallback or {}
        self.require_approval = require_approval

    @classmethod
    def load(cls, path: str | Path, *, require_approval: bool = True) -> "WalkbackLibrary":
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        return cls(
            scripts=data.get("scripts", {}),
            fallback=data.get("fallback", {}),
            require_approval=require_approval,
        )

    def _fallback_text(self) -> str:
        fb = self._fallback
        if fb.get("approved_by_lei") and fb.get("text"):
            return fb["text"]
        return ""  # even the fallback unapproved -> nothing ready to read

    def resolve(self, category: str) -> WalkbackResult:
        script = self._scripts.get(category, {}) or {}
        text = (script.get("text") or "").strip()
        approved = bool(script.get("approved_by_lei"))

        if text and (approved or not self.require_approval):
            return WalkbackResult(category, text, "", STATUS_APPROVED)

        # Category script exists but is not approved -> show fallback as ready,
        # carry the draft for Lei to review.
        if text:
            return WalkbackResult(category, self._fallback_text(), text, STATUS_DRAFT)

        # No category script at all.
        fb = self._fallback_text()
        return WalkbackResult(category, fb, "", STATUS_APPROVED if fb else STATUS_NONE)

    def pending_categories(self) -> list[str]:
        out = []
        for cat, s in self._scripts.items():
            if not bool((s or {}).get("approved_by_lei")):
                out.append(cat)
        return out
