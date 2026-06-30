from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class ChallengePlugin(ABC):
    """Abstract base class for challenge handlers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name."""
        ...

    def on_pre_navigation(self, context: dict) -> None:
        """Hook called before navigation."""
        pass

    def on_post_navigation(self, context: dict) -> None:
        """Hook called after navigation."""
        pass

    def enrich_payload(self, context: dict, payload: dict) -> dict:
        """Enrich the payload with challenge information."""
        return payload