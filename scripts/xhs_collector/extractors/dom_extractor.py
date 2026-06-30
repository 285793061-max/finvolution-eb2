from __future__ import annotations

from typing import Optional
from pathlib import Path
from datetime import datetime, timezone
import time

from .text_utils import (
    keyword_filter,
    dedupe_texts,
    texts_to_items,
    ExtractedItem,
)


class DOMExtractor:
    """DOM-based text extractor using Playwright."""

    def __init__(
        self,
        selector: str = "a",
        user_data_dir: Optional[Path] = None,
    ):
        self.selector = selector
        self.user_data_dir = user_data_dir or Path.home() / ".xhs_playwright_profile"

    def collect(
        self,
        keyword: str,
        limit: int,
        pages: int,
        scroll_pause_s: float = 2.0,
        url: Optional[str] = None,
    ) -> list[ExtractedItem]:
        """Collect items by scrolling and extracting DOM text."""
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

            if url:
                page.goto(url, wait_until="domcontentloaded")
                time.sleep(max(0.0, scroll_pause_s))

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
                time.sleep(max(0.0, scroll_pause_s))

            context.close()

        deduped = dedupe_texts(collected)[:limit]
        return texts_to_items(
            deduped,
            keyword=keyword,
            captured_at=datetime.now(timezone.utc),
            meta={"extractor": "dom", "pages": pages, "selector": self.selector},
        )