from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional
from app.services.xhs_extractors import ExtractedItem


class Engine(ABC):
    """Abstract base class for collection engines."""

    @abstractmethod
    def collect(
        self,
        keyword: str,
        limit: int,
        pages: int,
        **kwargs,
    ) -> list[ExtractedItem]:
        """Collect items matching the keyword."""
        ...

    @abstractmethod
    def calibrate(self) -> tuple[int, int, int, int]:
        """Calibrate the screen region for OCR extraction."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Engine name."""
        ...