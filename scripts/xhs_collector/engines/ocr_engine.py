from __future__ import annotations

import pyautogui
import time
from typing import Optional, Any
from pathlib import Path

from .base import Engine
from ..extractors import (
    ExtractedItem,
    ocr_extract_lines,
    keyword_filter,
    dedupe_texts,
    texts_to_items,
)


class OCREngine(Engine):
    """OCR-based collection engine using pyautogui + EasyOCR."""

    def __init__(
        self,
        region: Optional[tuple[int, int, int, int]] = None,
        scroll_amount: int = 900,
        scroll_pause_s: float = 2.0,
    ):
        self.region = region
        self.scroll_amount = scroll_amount
        self.scroll_pause_s = scroll_pause_s

    @property
    def name(self) -> str:
        return "ocr"

    def screenshot(self, region: Optional[tuple[int, int, int, int]] = None) -> Any:
        """Take a screenshot of the region or full screen."""
        r = region if region is not None else self.region
        if r is None:
            return pyautogui.screenshot()
        return pyautogui.screenshot(region=r)

    def collect(
        self,
        keyword: str,
        limit: int,
        pages: int,
        **kwargs,
    ) -> list[ExtractedItem]:
        """Collect items by scrolling and extracting text via OCR."""
        from datetime import datetime, timezone

        collected: list[str] = []

        for _ in range(pages):
            img = self.screenshot()
            lines = ocr_extract_lines(img)
            lines = keyword_filter(lines, keyword)
            collected.extend(lines)

            if len(dedupe_texts(collected)) >= limit:
                break

            pyautogui.scroll(-abs(self.scroll_amount))
            time.sleep(max(0.0, self.scroll_pause_s))

        deduped = dedupe_texts(collected)[:limit]
        return texts_to_items(
            deduped,
            keyword=keyword,
            captured_at=datetime.now(timezone.utc),
            meta={"engine": "ocr", "pages": pages},
        )

    def calibrate(self) -> tuple[int, int, int, int]:
        """Calibrate the screen region using user input."""
        print("将浏览器置于前台，并把搜索结果列表区域完整显示出来。")
        input("把鼠标移动到【结果区域左上角】后按 Enter ...")
        p1 = pyautogui.position()
        input("把鼠标移动到【结果区域右下角】后按 Enter ...")
        p2 = pyautogui.position()

        x1, y1 = int(min(p1.x, p2.x)), int(min(p1.y, p2.y))
        x2, y2 = int(max(p1.x, p2.x)), int(max(p1.y, p2.y))
        region = (x1, y1, max(1, x2 - x1), max(1, y2 - y1))
        return region