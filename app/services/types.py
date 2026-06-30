from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Protocol


@dataclass
class RawItem:
    id: str
    text: str
    source_type: str
    created_at: datetime | None = None
    meta: dict[str, Any] | None = None


class SourceAdapter(Protocol):
    def fetch(self, keyword: str, limit: int = 100) -> List[RawItem]:
        ...

