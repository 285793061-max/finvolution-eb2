from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ProxyConfig:
    """Proxy configuration for the collector."""
    url: str
    enabled: bool = True


@dataclass
class CacheConfig:
    """Cache configuration."""
    enabled: bool = True
    ttl_seconds: int = 3600  # 1 hour default
    data_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent / "data" / ".xhs_collector")


@dataclass
class LimitsConfig:
    """Crawl limits configuration."""
    max_items: int = 50
    max_pages: int = 8
    max_retries: int = 3
    retry_delay_s: float = 2.0


@dataclass
class CollectorConfig:
    """Main collector configuration."""
    keyword: str
    limit: int = 50
    pages: int = 8
    scroll_amount: int = 900
    scroll_pause_s: float = 2.0
    open_wait_s: float = 4.0
    extractor: str = "ocr"  # "ocr" or "dom"
    dom_selector: str = "a"
    dom_profile_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent / "data" / ".xhs_playwright_profile")

    # Proxy
    proxy_url: Optional[str] = None
    proxy_enabled: bool = False

    # Cache
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600

    # Output
    output_path: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent / "data" / "xiaohongshu_latest.json")
    region_file: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent / "data" / "xhs_screen_region.json")

    @classmethod
    def from_args(cls, args) -> "CollectorConfig":
        """Create config from parsed CLI args."""
        return cls(
            keyword=args.keyword,
            limit=int(args.limit) if hasattr(args, 'limit') else 50,
            pages=int(args.pages) if hasattr(args, 'pages') else 8,
            scroll_amount=int(args.scroll_amount) if hasattr(args, 'scroll_amount') else 900,
            scroll_pause_s=float(args.scroll_pause) if hasattr(args, 'scroll_pause') else 2.0,
            open_wait_s=float(args.open_wait) if hasattr(args, 'open_wait') else 4.0,
            extractor=args.extractor if hasattr(args, 'extractor') else "ocr",
            dom_selector=str(args.dom_selector) if hasattr(args, 'dom_selector') else "a",
            dom_profile_dir=Path(args.dom_profile_dir) if hasattr(args, 'dom_profile_dir') else Path(__file__).resolve().parent.parent.parent / "data" / ".xhs_playwright_profile",
            proxy_url=getattr(args, 'proxy_url', None),
            proxy_enabled=getattr(args, 'proxy', False),
            cache_enabled=True,
            cache_ttl_seconds=3600,
            output_path=Path(args.out) if hasattr(args, 'out') else Path(__file__).resolve().parent.parent.parent / "data" / "xiaohongshu_latest.json",
            region_file=Path(args.region_file) if hasattr(args, 'region_file') else Path(__file__).resolve().parent.parent.parent / "data" / "xhs_screen_region.json",
        )