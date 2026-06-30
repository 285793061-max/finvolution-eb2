from __future__ import annotations

from pathlib import Path
from typing import List

from ..storage import SqliteStore


class OutputWriter:
    """脉脉数据输出写入器"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.store = SqliteStore(db_path)

    def write_posts(self, posts: List[dict]) -> int:
        """写入帖子到数据库"""
        return self.store.save_posts(posts)

    def get_count(self) -> int:
        """获取已保存的帖子数"""
        return self.store.count()