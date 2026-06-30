from __future__ import annotations

import pyautogui
from typing import Optional, Any
from datetime import datetime, timezone

from .text_utils import (
    ocr_extract_lines,
    keyword_filter,
    dedupe_texts,
    texts_to_items,
    ExtractedItem,
)


class OCRExtractor:
    """OCR-based text extractor using pyautogui + EasyOCR."""

    def __init__(self, region: Optional[tuple[int, int, int, int]] = None):
        self.region = region

    def screenshot(self) -> Any:
        """Take a screenshot of the region or full screen."""
        if self.region is None:
            return pyautogui.screenshot()
        return pyautogui.screenshot(region=self.region)

    def extract(self) -> list[str]:
        """Extract text lines from current screen using OCR."""
        img = self.screenshot()
        return ocr_extract_lines(img)

    def collect(
        self,
        keyword: str,
        limit: int,
        pages: int,
        scroll_amount: int = 900,
        scroll_pause_s: float = 2.0,
    ) -> list[ExtractedItem]:
        """Collect items by scrolling and extracting text."""
        import time

        collected: list[str] = []

        for _ in range(pages):
            lines = self.extract()
            lines = keyword_filter(lines, keyword)
            collected.extend(lines)

            if len(dedupe_texts(collected)) >= limit:
                break

            pyautogui.scroll(-abs(scroll_amount))
            time.sleep(max(0.0, scroll_pause_s))

        deduped = dedupe_texts(collected)[:limit]
        return texts_to_items(
            deduped,
            keyword=keyword,
            captured_at=datetime.now(timezone.utc),
            meta={"extractor": "ocr", "pages": pages},
        )