from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, List

from app.config import settings
from .types import RawItem, SourceAdapter


class XiaohongshuSourceAdapter:
    """
    小红书数据源适配器（MVP 版本）

    当前实现思路：
    - 不直接在这里爬小红书，而是从本地最新数据文件中读取
    - 本地最新数据文件由单独脚本写入，例如：data/xiaohongshu_latest.json

    好处：
    - 线上分析服务和“爬虫/采集逻辑”解耦
    - 你可以按需手动或定时更新本地数据文件，实现“准实时”
    """

    def __init__(self, file_path: Path | None = None) -> None:
        # 默认从 xiaohongshu_latest.json 读取
        self.file_path = file_path or (settings.data_dir / "xiaohongshu_latest.json")

    def fetch(self, keyword: str, limit: int = 100) -> List[RawItem]:
        if not self.file_path.exists():
            # 如果没有“最新文件”，可以选择返回空，让系统退回到示例数据
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

            items.append(
                RawItem(
                    id=str(row.get("id", "")),
                    text=text,
                    source_type=str(row.get("source_type", "xiaohongshu")),
                    created_at=created_at,
                    meta={k: v for k, v in row.items() if k not in {"id", "text", "source_type", "created_at"}},
                )
            )

            if len(items) >= limit:
                break

        return items

