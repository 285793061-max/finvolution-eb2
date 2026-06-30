from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List

from app.config import settings
from .xiaohongshu_adapter import XiaohongshuSourceAdapter
from .types import RawItem, SourceAdapter


class LocalJsonSourceAdapter:
    def __init__(self, file_path: Path, source_type: str | None = None) -> None:
        self.file_path = file_path
        self.source_type = source_type

    def fetch(self, keyword: str, limit: int = 100) -> List[RawItem]:
        if not self.file_path.exists():
            return []

        with self.file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        keyword_lower = keyword.lower()
        items: List[RawItem] = []

        for row in data:
            text = str(row.get("text", ""))
            if keyword_lower not in text.lower():
                continue

            created_at_raw = row.get("created_at")
            created_at: datetime | None = None
            if isinstance(created_at_raw, str):
                try:
                    created_at = datetime.fromisoformat(created_at_raw)
                except ValueError:
                    created_at = None

            item_source_type = self.source_type or str(row.get("source_type", "unknown"))

            items.append(
                RawItem(
                    id=str(row.get("id", "")),
                    text=text,
                    source_type=item_source_type,
                    created_at=created_at,
                    meta={k: v for k, v in row.items() if k not in {"id", "text", "source_type", "created_at"}},
                )
            )

            if len(items) >= limit:
                break

        return items


def _get_adapters() -> list[SourceAdapter]:
    data_dir = settings.data_dir
    return [
        # 1. 小红书“最新数据”优先（如果有 xiaohongshu_latest.json）
        XiaohongshuSourceAdapter(),
        # 2. 其他本地示例数据
        LocalJsonSourceAdapter(data_dir / "sample_social.json", source_type="social"),
        LocalJsonSourceAdapter(data_dir / "sample_job_reviews.json", source_type="job"),
        LocalJsonSourceAdapter(data_dir / "sample_xiaohongshu.json", source_type="xiaohongshu"),
    ]


def fetch_texts(keyword: str, limit: int = 100) -> List[RawItem]:
    adapters = _get_adapters()
    collected: List[RawItem] = []

    for adapter in adapters:
        remaining = max(0, limit - len(collected))
        if remaining <= 0:
            break
        collected.extend(adapter.fetch(keyword=keyword, limit=remaining))

    return collected[:limit]

