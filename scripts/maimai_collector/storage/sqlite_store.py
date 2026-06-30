from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional


class SqliteStore:
    """脉脉数据 SQLite 存储 - 使用 Web 应用数据库"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def save_post(self, title: str, content: str, url: str, publish_time: str = "") -> bool:
        """保存一条帖子到 Web 应用数据库"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cur = conn.cursor()

            # 检查是否已存在（根据 URL 去重）
            if url:
                cur.execute("SELECT id FROM sentiment_data WHERE url = ?", (url,))
                if cur.fetchone():
                    conn.close()
                    return False  # 已存在，跳过

            cur.execute("""
                INSERT INTO sentiment_data
                (platform, title, content, url, publish_time, crawl_time, sentiment_label, source_type)
                VALUES ('maimai', ?, ?, ?, ?, ?, 'neutral', 'maimai')
            """, (
                title,
                content,
                url,
                publish_time or "",
                datetime.now().isoformat()
            ))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"保存失败: {e}")
            return False

    def save_posts(self, posts: list[dict]) -> int:
        """批量保存帖子"""
        saved = 0
        for post in posts:
            if self.save_post(
                post.get('title', ''),
                post.get('content', ''),
                post.get('url', ''),
                post.get('publish_time', '')
            ):
                saved += 1
        return saved

    def count(self) -> int:
        """统计已保存的帖子数"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM sentiment_data WHERE platform = 'maimai'")
            count = cur.fetchone()[0]
            conn.close()
            return count
        except:
            return 0