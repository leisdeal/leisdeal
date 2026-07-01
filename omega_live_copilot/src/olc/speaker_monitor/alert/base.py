"""Alert channel interface (PRD §7.8.7). V1 ships channel A (中控屏). Channel B
(耳返) is optional and must not block the main module's acceptance."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..events import RedlineEvent
from ..walkback import WalkbackResult


@dataclass
class AlertPayload:
    event: RedlineEvent
    walkback: WalkbackResult


class AlertChannel(ABC):
    name: str = "base"

    @abstractmethod
    def emit(self, payload: AlertPayload) -> None:
        ...
