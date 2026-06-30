from __future__ import annotations

import time
from typing import Optional
from pathlib import Path
import urllib.parse

from .base import Engine
from ..extractors import (
    ExtractedItem,
    keyword_filter,
    dedupe_texts,
    texts_to_items,
)


class DOMEngine(Engine):
    """DOM-based collection engine using Playwright."""

    def __init__(
        self,
        selector: str = "a",
        user_data_dir: Optional[Path] = None,
        scroll_pause_s: float = 2.0,
    ):
        self.selector = selector
        self.user_data_dir = user_data_dir or Path.home() / ".xhs_playwright_profile"
        self.scroll_pause_s = scroll_pause_s

    @property
    def name(self) -> str:
        return "dom"

    def _build_url(self, keyword: str) -> str:
        """Build search URL for the keyword."""
        q = urllib.parse.quote(keyword)
        return f"https://www.xiaohongshu.com/search_result?keyword={q}"

    def collect(
        self,
        keyword: str,
        limit: int,
        pages: int,
        **kwargs,
    ) -> list[ExtractedItem]:
        """Collect items by scrolling and extracting DOM text."""
        from datetime import datetime, timezone

        try:
            from playwright.sync_api import sync_playwright
        except Exception as e:
            raise RuntimeError(
                "未安装 playwright。请先 pip install playwright && playwright install chromium"
            ) from e

        collected: list[str] = []
        self.user_data_dir.mkdir(parents=True, exist_ok=True)

        with sync_playwright() as p:
            try:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=str(self.user_data_dir),
                    headless=False,
                    viewport={"width": 1280, "height": 900},
                )
            except Exception as e:
                raise RuntimeError(
                    "Playwright 浏览器运行时未安装。请先运行：playwright install chromium"
                ) from e

            page = context.pages[0] if context.pages else context.new_page()
            page.goto("https://www.xiaohongshu.com", wait_until="domcontentloaded")
            print("已打开小红书。请在弹出的浏览器窗口里完成登录。")
            input("登录完成后回到终端按 Enter 继续打开搜索页 ...")

            page.goto(self._build_url(keyword), wait_until="domcontentloaded")
            time.sleep(max(0.0, self.scroll_pause_s))

            for _ in range(pages):
                try:
                    texts = page.locator(self.selector).all_inner_texts()
                except Exception:
                    texts = []
                texts = [t.strip() for t in texts if isinstance(t, str)]
                texts = keyword_filter(texts, keyword)
                collected.extend(texts)

                if len(dedupe_texts(collected)) >= limit:
                    break

                page.mouse.wheel(0, 1200)
                time.sleep(max(0.0, self.scroll_pause_s))

            context.close()

        deduped = dedupe_texts(collected)[:limit]
        return texts_to_items(
            deduped,
            keyword=keyword,
            captured_at=datetime.now(timezone.utc),
            meta={"engine": "dom", "pages": pages, "selector": self.selector},
        )

    def calibrate(self) -> tuple[int, int, int, int]:
        """DOM engine doesn't need calibration."""
        return (0, 0, 1280, 900)