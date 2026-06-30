from __future__ import annotations

from .interfaces import ExtractorProtocol
from .text_utils import (
    normalize_text,
    dedupe_texts,
    keyword_filter,
    ocr_extract_lines,
    texts_to_items,
    stable_id,
    ExtractedItem,
)

__all__ = [
    "ExtractorProtocol",
    "normalize_text",
    "dedupe_texts",
    "keyword_filter",
    "ocr_extract_lines",
    "texts_to_items",
    "stable_id",
    "ExtractedItem",
]