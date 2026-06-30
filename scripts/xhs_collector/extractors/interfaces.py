from __future__ import annotations

from typing import Protocol, Iterable
from app.services.xhs_extractors import ExtractedItem


class ExtractorProtocol(Protocol):
    """Protocol for text extractors."""

    def extract(self, **kwargs) -> list[str]:
        """Extract text content from the current state."""
        ...

    def collect(self, keyword: str, limit: int, pages: int, **kwargs) -> list[ExtractedItem]:
        """Collect items matching the keyword."""
        ...