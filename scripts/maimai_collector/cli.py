from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Ensure project root is in path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from .config import MaimaiConfig
from .engines import GossipEngine
from .output import OutputWriter


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="脉职言采集器")
    p.add_argument("keyword", help="搜索关键词")
    p.add_argument("--max-posts", type=int, default=30, help="最大帖子数")
    p.add_argument("--max-scrolls", type=int, default=5, help="最大滚动次数")
    p.add_argument("--scroll-pause", type=float, default=2.0, help="滚动后等待秒数")
    p.add_argument("--cookie", type=str, help="Cookie 文件路径")
    p.add_argument("--db", type=str, help="数据库路径")
    return p.parse_args()


async def main_async() -> None:
    args = parse_args()
    config = MaimaiConfig.from_args(args)

    print(f"开始爬取脉脉: {config.keyword}")

    # Create engine
    engine = GossipEngine(
        cookie_path=config.cookie_path,
        chrome_path=config.chrome_path,
        user_agent=config.user_agent,
        max_posts=config.max_posts,
        max_scrolls=config.max_scrolls,
        scroll_pause_s=config.scroll_pause_s,
        wait_load_timeout=config.wait_load_timeout,
        login_wait_minutes=config.login_wait_minutes,
    )

    # Collect data
    posts = await engine.collect(config.keyword)

    if posts:
        # Write to database
        writer = OutputWriter(config.db_path)
        saved = writer.write_posts(posts)
        total = writer.get_count()
        print(f"已保存 {saved} 条 (总计: {total} 条)")
    else:
        print("未采集到数据")

    print("完成!")


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()