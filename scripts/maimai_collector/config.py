from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

@dataclass
class MaimaiConfig:
    """脉脉采集器配置"""
    keyword: str
    max_posts: int = 30
    max_scrolls: int = 5
    scroll_pause_s: float = 2.0
    wait_load_timeout: int = 15000
    login_wait_minutes: int = 3

    # Chrome 路径
    chrome_path: str = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

    # Cookie 和数据库路径 - 使用 Web应用的数据库
    cookie_path: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "maimai_cookies.json")
    db_path: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "sentiment.db")

    # 用户代理
    user_agent: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    @classmethod
    def from_args(cls, args) -> "MaimaiConfig":
        # Default paths - 使用 Web应用的数据库
        default_cookie = PROJECT_ROOT / "data" / "maimai_cookies.json"
        default_db = PROJECT_ROOT / "data" / "sentiment.db"

        return cls(
            keyword=args.keyword,
            max_posts=int(args.max_posts) if hasattr(args, 'max_posts') else 30,
            max_scrolls=int(args.max_scrolls) if hasattr(args, 'max_scrolls') else 5,
            scroll_pause_s=float(args.scroll_pause) if hasattr(args, 'scroll_pause') else 2.0,
            cookie_path=Path(args.cookie) if hasattr(args, 'cookie') and args.cookie else default_cookie,
            db_path=Path(args.db) if hasattr(args, 'db') and args.db else default_db,
        )
